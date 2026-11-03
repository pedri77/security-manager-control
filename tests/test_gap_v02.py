import copy
from datetime import date
from pathlib import Path

import pytest
import yaml

from smc.cli import main
from smc.gap import Analisis, analyse, render_markdown, run

EX = Path(__file__).resolve().parent.parent / "assessments" / "examples" / "ejemplo-ayuntamiento.yaml"
HOY = date(2026, 11, 3)


@pytest.fixture
def ass():
    return yaml.safe_load(EX.read_text(encoding="utf-8"))


def ens(an):
    return next(r for r in an.results if r.framework == "ENS")


def test_media_excluye_medidas_solo_alta(ass):
    r = ens(analyse(ass, HOY))
    assert r.no_aplican and all(c.extra["categoria_minima"] == "ALTA" for c in r.no_aplican)
    # ENS-mp.if.6 está evaluada como no_aplica en el ejemplo: tampoco es aplicable
    assert r.aplicables + len(r.no_aplican) + 1 == r.total
    # no cuentan ni como aplicables ni como sin evaluar
    assert not {c.id for c in r.sin_evaluar} & {c.id for c in r.no_aplican}


def test_contraprueba_forzar_alta_cambia_aplicables(ass):
    media = ens(analyse(ass, HOY))
    ass2 = copy.deepcopy(ass)
    ass2["cliente"]["categoria_ens"] = "ALTA"
    alta = ens(analyse(ass2, HOY))
    assert alta.aplicables > media.aplicables and alta.no_aplican == []
    assert alta.aplicables + 1 == alta.total   # solo ENS-mp.if.6 (no_aplica evaluada)


def test_categoria_vacia_es_alta_con_aviso(ass):
    ass["cliente"]["categoria_ens"] = ""
    an = analyse(ass, HOY)
    assert an.categoria_ens == "ALTA" and any("Categoría ENS" in w for w in an.warnings)


def test_brecha_p1_sale_primero_y_orden(ass):
    an = analyse(ass, HOY)
    for r in an.results:
        pts = [b.puntuacion for b in r.brechas]
        assert pts == sorted(pts, reverse=True)
    assert an.results[0].brechas[0].nivel == "P1"
    tabla = run(EX, HOY).split("### Brechas (por prioridad)")[1]
    assert tabla.index("| P1 |") < tabla.index("| P2 |")


def test_refuerzos_ens_en_alta(ass):
    ass["cliente"]["categoria_ens"] = "ALTA"
    ass["evaluaciones"]["ENS-mp.com.2"] = {"estado": "parcial"}
    an = analyse(ass, HOY)
    b = next(b for b in ens(an).brechas if b.control.id == "ENS-mp.com.2")
    assert b.refuerzos
    assert ", ".join(b.refuerzos) in render_markdown(an)


def test_heredado_sugiere_y_no_puntua(ass):
    an = analyse(ass, HOY)
    d = next(d for r in an.results for d in r.sin_evaluar_detalle if d.control.id == "NIS2-21.2.i")
    assert ("ENS-op.exp.1", "parcial") in d.heredado_de
    assert "heredado" in run(EX, HOY)
    nis2 = an.results[0]
    assert d.control in nis2.sin_evaluar and all(b.control.id != "NIS2-21.2.i" for b in nis2.brechas)
    base = nis2.puntuacion
    ass["evaluaciones"].pop("ENS-op.exp.1")   # quitar el equivalente no cambia NIS2
    assert analyse(ass, HOY).results[0].puntuacion == base


def test_aviso_p1_sin_accion(ass):
    an = analyse(ass, HOY)
    assert "NIS2-21.2.d" in an.p1_sin_accion and "NIS2-21.2.c" not in an.p1_sin_accion
    assert "P1 sin acción" in run(EX, HOY)
    ass["plan_accion"].append({"id": "X", "controles": an.p1_sin_accion, "accion": "a",
                               "responsable": "r", "fecha_objetivo": "2027-01-01", "estado": "pendiente"})
    assert analyse(ass, HOY).p1_sin_accion == []


def test_api_estructurada_compatible(ass):
    an = analyse(ass, HOY)
    assert isinstance(an, Analisis)
    cliente, results, warnings = an
    assert cliente["nombre"] and results and warnings == []
    assert [a.id for a in an.vencidas] == ["ACC-02"]
    assert "## Plan de acción" in run(EX, HOY)


def test_cli_plan_vencidas_con_hoy(capsys):
    assert main(["plan", str(EX), "--hoy", "2026-11-03"]) == 0
    out = capsys.readouterr().out
    assert "ACC-02" in out and "(VENCIDA)" in out and "P1 sin acción" in out
    main(["plan", str(EX), "--hoy", "2026-01-01"])
    assert "(VENCIDA)" not in capsys.readouterr().out


def test_cli_gap_hoy_e_invalida(capsys):
    assert main(["gap", str(EX), "--hoy", "2026-11-03"]) == 0
    assert "## Plan de acción" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["plan", str(EX), "--hoy", "mañana"])
