"""T39 (SMC-004): smc gap y smc plan dan ERROR limpio con fichero inexistente o YAML roto."""
from pathlib import Path

import pytest

from smc.cli import main

ROOT = Path(__file__).resolve().parent.parent
EJEMPLO = ROOT / "assessments" / "examples" / "ejemplo-energia.yaml"
HOY = "2026-11-03"


def _roto(tmp_path):
    p = tmp_path / "roto.yaml"
    p.write_text("a: [sin cerrar\n  b: : :\n", encoding="utf-8")
    return p


def _inexistente(tmp_path):
    return tmp_path / "no-existe.yaml"


def _profundo(tmp_path):
    p = tmp_path / "profundo.yaml"
    p.write_text("[" * 500, encoding="utf-8")   # PyYAML lanza RecursionError
    return p


def _tag(contenido, nombre):
    def fabrica(tmp_path):
        p = tmp_path / nombre
        p.write_text(contenido, encoding="utf-8")
        return p
    return fabrica


MALAS = [
    pytest.param(_inexistente, id="inexistente"),
    pytest.param(_roto, id="yaml-roto"),
    pytest.param(_profundo, id="yaml-profundo"),
    pytest.param(_tag("a: !!bool abc\n", "t1.yaml"), id="tag-bool"),
    pytest.param(_tag('a: !!int ""\n', "t2.yaml"), id="tag-int-vacio"),
    pytest.param(_tag('a: !!float ""\n', "t3.yaml"), id="tag-float-vacio"),
    pytest.param(_tag("a: !!timestamp abc\n", "t4.yaml"), id="tag-timestamp"),
    pytest.param(_tag("a: !!timestamp {=}\n", "t5.yaml"), id="tag-timestamp-mapa"),
]
GOLDEN = Path(__file__).resolve().parent / "golden"


@pytest.mark.parametrize("cmd", ["gap", "plan"])
@pytest.mark.parametrize("fabrica", MALAS)
def test_fichero_malo_da_error_limpio(cmd, fabrica, tmp_path, capsys):
    ruta = fabrica(tmp_path)
    rc = main([cmd, str(ruta)])
    out = capsys.readouterr()
    assert rc == 2
    assert out.err.startswith(f"ERROR: {ruta}:")
    assert "Traceback" not in out.err and "Traceback" not in out.out
    assert out.out == ""


@pytest.mark.parametrize("fabrica", MALAS)
def test_gap_con_salida_no_crea_fichero(fabrica, tmp_path, capsys):
    salida = tmp_path / "salida.md"
    rc = main(["gap", str(fabrica(tmp_path)), "-o", str(salida)])
    assert rc == 2
    assert not salida.exists()
    assert capsys.readouterr().err.startswith("ERROR: ")


def _golden(nombre):
    # Referencias generadas con el codigo de 0c1a5be (anterior a SMC-004), nunca con el nuevo.
    return (GOLDEN / nombre).read_bytes().decode("utf-8")


def test_gap_valido_igual_que_referencia(capsys):
    assert main(["gap", str(EJEMPLO), "--hoy", HOY]) == 0
    out = capsys.readouterr()
    assert out.err == ""
    assert out.out == _golden("gap.md")


def test_plan_valido_igual_que_referencia(capsys):
    assert main(["plan", str(EJEMPLO), "--hoy", HOY]) == 0
    out = capsys.readouterr()
    assert out.err == ""
    assert out.out == _golden("plan.md")


def test_gap_con_salida_valida_igual_que_referencia(tmp_path, capsys):
    salida = tmp_path / "salida.md"
    assert main(["gap", str(EJEMPLO), "--hoy", HOY, "-o", str(salida)]) == 0
    out = capsys.readouterr()
    assert out.err == ""
    assert out.out == f"Informe escrito en {salida}\n"
    assert salida.read_bytes().decode("utf-8") == _golden("gap_o.md")


def test_tag_roto_mensaje_una_linea(tmp_path, capsys):
    ruta = _tag("a: !!bool abc\n", "t.yaml")(tmp_path)
    assert main(["gap", str(ruta)]) == 2
    err = capsys.readouterr().err
    assert err.count("\n") == 1 and "no es válido" in err


# T45 (SMC-006): estado que no es escalar y YAML válido que no es un mapa.
def _eval_con_estado(tmp_path, linea):
    p = tmp_path / "eval.yaml"
    p.write_text(
        "cliente: {nombre: Cliente ejemplo, sector: energia}\n"
        "evaluaciones:\n"
        f"  NIS2-20.1: {linea}\n",
        encoding="utf-8",
    )
    return p


@pytest.mark.parametrize("cmd", ["gap", "plan"])
@pytest.mark.parametrize("valor", ["[]", "{}"])
def test_estado_no_escalar_no_da_traceback(cmd, valor, tmp_path, capsys):
    ruta = _eval_con_estado(tmp_path, "{estado: %s, evidencias: []}" % valor)
    rc = main([cmd, str(ruta)])
    out = capsys.readouterr()
    assert rc == 0
    assert "Traceback" not in out.err and "Traceback" not in out.out
    assert out.err == ""


@pytest.mark.parametrize("valor", ["[]", "{}"])
def test_gap_estado_no_escalar_avisa_y_cuenta_sin_evaluar(valor, tmp_path):
    from smc.gap import analyse, _load

    an = analyse(_load(_eval_con_estado(tmp_path, "{estado: %s, evidencias: []}" % valor)))
    assert any(w.startswith("NIS2-20.1: estado no válido") and "cuenta como sin evaluar" in w
               for w in an.warnings)
    nis2 = next(r for r in an.results if r.framework == "NIS2")
    assert "NIS2-20.1" in {c.id for c in nis2.sin_evaluar}
    assert "NIS2-20.1" not in {b.control.id for b in nis2.brechas}


def test_gap_estado_no_escalar_en_equivalente_no_da_traceback(tmp_path, capsys):
    # NIS2-20.1 sin evaluar hereda de ENS-org.1, cuyo estado es una lista.
    p = tmp_path / "eq.yaml"
    p.write_text("evaluaciones:\n  ENS-org.1: {estado: []}\n", encoding="utf-8")
    assert main(["gap", str(p)]) == 0
    assert "Traceback" not in capsys.readouterr().err


@pytest.mark.parametrize("contenido", ["42\n", "- a\n", "hola\n", ""], ids=["entero", "lista", "texto", "vacio"])
def test_yaml_valido_no_mapa_da_rc0_con_aviso(contenido, tmp_path, capsys):
    p = tmp_path / "nomapa.yaml"
    p.write_text(contenido, encoding="utf-8")
    rc = main(["gap", str(p)])
    out = capsys.readouterr()
    assert rc == 0
    assert "La evaluación no es un mapa YAML: se trata como vacía" in out.out
    assert "Traceback" not in out.err and "Traceback" not in out.out
