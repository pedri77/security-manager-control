from datetime import date
from pathlib import Path

import yaml

from smc.catalog import load_all
from smc.gap import analyse
from smc.plan import Accion, brechas_sin_accion, cargar_plan, render_plan_md, vencidas

EX = Path(__file__).resolve().parent.parent / "assessments" / "examples" / "ejemplo-ayuntamiento.yaml"
HOY = date(2026, 11, 3)


def plan_de(*acciones):
    return cargar_plan({"plan_accion": list(acciones)})


def acc(id, fecha, estado="pendiente", controles=("NIS2-21.2.a",)):
    return {"id": id, "controles": list(controles), "accion": "x", "responsable": "RSI",
            "fecha_objetivo": fecha, "estado": estado}


def test_vencidas_basico():
    p = plan_de(acc("A", "2026-11-02"), acc("B", "2026-11-04"))
    assert [a.id for a in vencidas(p, HOY)] == ["A"]


def test_fecha_igual_a_hoy_no_vence():
    p = plan_de(acc("A", "2026-11-03"))
    assert vencidas(p, HOY) == []


def test_hecha_no_vence():
    p = plan_de(acc("A", "2020-01-01", "hecha"), acc("B", "2020-01-01", "bloqueada"))
    assert [a.id for a in vencidas(p, HOY)] == ["B"]


def test_fecha_yaml_nativa_y_invalida():
    p = plan_de(acc("A", date(2026, 1, 1)), acc("B", "no-fecha"), acc("C", "2026-01-01", "raro"))
    assert p[0].fecha_objetivo == date(2026, 1, 1)
    assert p[1].fecha_objetivo is None and p[1].avisos
    assert p[2].estado == "pendiente" and p[2].avisos
    assert [a.id for a in vencidas(p, HOY)] == ["A", "C"]


def test_brechas_sin_accion_ids_y_tuplas():
    p = plan_de(acc("A", "2027-01-01", controles=("X-1",)), acc("B", "2027-01-01", "hecha", ("X-3",)))
    assert brechas_sin_accion(["X-1", "X-2", "X-3"], p) == ["X-2", "X-3"]
    ctl = [c for c in load_all()["NIS2"]][:2]
    tup = [(c, "parcial", "") for c in ctl]
    p2 = plan_de(acc("A", "2027-01-01", controles=(ctl[0].id,)))
    assert brechas_sin_accion(tup, p2) == [ctl[1].id]


def test_ejemplo_carga_y_es_coherente():
    assessment = yaml.safe_load(EX.read_text(encoding="utf-8"))
    plan = cargar_plan(assessment)
    assert len(plan) >= 3 and all(isinstance(a, Accion) and not a.avisos for a in plan)
    known = {c.id for cs in load_all().values() for c in cs}
    assert all(c in known for a in plan for c in a.controles)
    assert {"ACC-02"} == {a.id for a in vencidas(plan, HOY)}
    _, results, _ = analyse(assessment)
    sin = brechas_sin_accion([b for r in results for b in r.brechas], plan)
    assert "NIS2-21.2.c" not in sin and "NIS2-21.2.d" in sin


def test_render_md():
    p = plan_de(acc("A", "2026-11-02"), acc("B", "2027-01-01", controles=("X-1",)))
    md = render_plan_md(p, HOY, brechas=["X-1", "X-9"])
    assert "A" in md and "(VENCIDA)" in md and "Brechas sin acción (1)" in md and "- X-9" in md
    assert "Sin acciones" in render_plan_md([], HOY)


def test_sin_plan_en_assessment():
    assert cargar_plan({}) == [] and cargar_plan({"plan_accion": None}) == []
