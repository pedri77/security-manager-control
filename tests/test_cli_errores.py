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


MALAS = [
    pytest.param(_inexistente, id="inexistente"),
    pytest.param(_roto, id="yaml-roto"),
    pytest.param(_profundo, id="yaml-profundo"),
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
