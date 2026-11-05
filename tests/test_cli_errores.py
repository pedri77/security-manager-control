"""T37 (SMC-004): smc gap y smc plan dan ERROR limpio con fichero inexistente o YAML roto."""
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


MALAS = [pytest.param(_inexistente, id="inexistente"), pytest.param(_roto, id="yaml-roto")]


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


@pytest.mark.parametrize("cmd", ["gap", "plan"])
def test_evaluacion_valida_sigue_igual(cmd, capsys):
    assert main([cmd, str(EJEMPLO), "--hoy", HOY]) == 0
    out = capsys.readouterr()
    assert out.err == "" and out.out.strip()
    assert main([cmd, str(EJEMPLO), "--hoy", HOY]) == 0
    assert capsys.readouterr().out == out.out


def test_gap_con_salida_valida_escribe(tmp_path, capsys):
    salida = tmp_path / "salida.md"
    assert main(["gap", str(EJEMPLO), "--hoy", HOY, "-o", str(salida)]) == 0
    assert salida.read_text(encoding="utf-8").strip()
