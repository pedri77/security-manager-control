"""T25: VRT-AI y VRT-OFF nuevas; VRT-IAM y VRT-DATA ampliadas (22 en total)."""
from pathlib import Path

import yaml

from smc import verticals as V
from smc.catalog import load_all

ROOT = Path(__file__).resolve().parent.parent
NUEVAS = ["VRT-IAM", "VRT-DATA", "VRT-AI", "VRT-OFF"]
EJEMPLOS = sorted((ROOT / "assessments" / "examples").glob("*.yaml"))


def _v(vid):
    return next(v for v in V.cargar_verticales() if v.id == vid)


def test_hay_22_y_las_cuatro():
    ids = [v.id for v in V.cargar_verticales()]
    assert len(ids) == len(set(ids)) == 22
    assert set(NUEVAS) <= set(ids)
    assert V.validar_catalogo() == []


def test_baremo_6_niveles_distintos_y_controles_existen():
    conocidos = {c.id for cs in load_all().values() for c in cs}
    for vid in NUEVAS:
        v = _v(vid)
        assert sorted(v.niveles) == [0, 1, 2, 3, 4, 5], vid
        assert len(set(v.niveles.values())) == 6, vid
        assert v.criterios and v.nis2, vid
        assert set(v.controles) <= conocidos, vid
        assert not v.recursos, vid


def test_no_hay_verticales_duplicadas_idsec_dspm():
    ids = {v.id for v in V.cargar_verticales()}
    assert not ids & {"VRT-IDSEC", "VRT-DSPM"}
    assert {"ENS-op.acc.1", "TRV-ID-02"} <= set(_v("VRT-IAM").controles)
    assert {"ENS-mp.info.1", "TRV-DATA-01"} <= set(_v("VRT-DATA").controles)


def test_mapeos_clave():
    assert {"NIS2-21.2.i", "NIS2-21.2.j"} <= set(_v("VRT-IAM").nis2)
    assert any(c.startswith("ENS-op.acc.") for c in _v("VRT-IAM").controles)
    assert any(c.startswith("ENS-mp.info.") for c in _v("VRT-DATA").controles)
    assert {"NIS2-21.2.a", "NIS2-21.2.e"} <= set(_v("VRT-AI").nis2)
    assert "TRV-VUL-02" in _v("VRT-OFF").controles


def test_vrt_ai_no_referencia_catalogo_ria():
    assert not any("AI-ACT" in c or "RIA" in c for c in _v("VRT-AI").controles)
    assert "inventario" in _v("VRT-AI").niveles[0].lower()
    n5 = _v("VRT-AI").niveles[5].lower()
    for k in ("inventario completo", "ria", "owasp llm", "atlas", "mínimo privilegio", "supervisión humana", "adversariales"):
        assert k in n5


def test_plantilla_y_ejemplos_incluyen_las_cuatro_y_se_evaluan():
    for f in [ROOT / "assessments" / "assessment.template.yaml", *EJEMPLOS]:
        ass = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert set(NUEVAS) <= set(ass["verticales"]), f.name
        r = V.evaluar(ass)
        assert r.warnings == [], f.name
    ayto = yaml.safe_load(EJEMPLOS[0].read_text(encoding="utf-8"))
    assert ayto["verticales"]["VRT-AI"]["madurez"] == "no_evaluable" and ayto["verticales"]["VRT-AI"]["motivo"]


def test_contraprueba_control_inexistente_en_vrt_ai_falla():
    vs = V.cargar_verticales()
    next(v for v in vs if v.id == "VRT-AI").controles.append("TRV-AI-99")
    assert any("VRT-AI" in e and "TRV-AI-99" in e for e in V.validar_catalogo(vs))


def test_contraprueba_recurso_fuera_de_lista_en_vrt_off_falla():
    vs = V.cargar_verticales()
    next(v for v in vs if v.id == "VRT-OFF").recursos.append({"titulo": "x", "url": "https://ejemplo.invalid/"})
    assert any("VRT-OFF" in e for e in V.validar_catalogo(vs))
