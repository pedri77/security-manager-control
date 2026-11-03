"""T18: vertical VRT-GRC (gobierno, riesgo y cumplimiento)."""
import copy
from pathlib import Path

import yaml

from smc import verticals as V
from smc.catalog import load_all

ROOT = Path(__file__).resolve().parent.parent
EJEMPLOS = sorted((ROOT / "assessments" / "examples").glob("*.yaml"))


def _grc():
    return next(v for v in V.cargar_verticales() if v.id == "VRT-GRC")


def test_grc_existe_con_nis2_20_y_21():
    v = _grc()
    assert {"NIS2-20.1", "NIS2-20.2", "NIS2-21.2.a", "NIS2-21.2.f"} <= set(v.nis2)
    assert {"ENS-org.1", "ENS-op.pl.1", "TRV-RGPD-01", "TRV-GOB-02"} <= set(v.controles)


def test_grc_baremo_completo_y_sin_recursos():
    v = _grc()
    assert sorted(v.niveles) == [0, 1, 2, 3, 4, 5]
    assert len(set(v.niveles.values())) == 6
    assert not v.recursos
    assert V.validar_catalogo() == []


def test_grc_controles_existen_en_catalogos():
    conocidos = {c.id for cs in load_all().values() for c in cs}
    assert set(_grc().controles) <= conocidos


def test_contraprueba_control_inexistente_en_grc_falla():
    vs = V.cargar_verticales()
    next(v for v in vs if v.id == "VRT-GRC").controles.append("ENS-org.99")
    assert any("VRT-GRC" in e and "ENS-org.99" in e for e in V.validar_catalogo(vs))


def test_contraprueba_medida_nis2_inexistente_en_grc_falla():
    vs = V.cargar_verticales()
    next(v for v in vs if v.id == "VRT-GRC").nis2.append("NIS2-20.9")
    assert any("NIS2-20.9" in e for e in V.validar_catalogo(vs))


def test_ejemplos_y_plantilla_incluyen_grc_y_agregan_a_nis2_20():
    plantilla = yaml.safe_load((ROOT / "assessments" / "assessment.template.yaml").read_text(encoding="utf-8"))
    assert "VRT-GRC" in plantilla["verticales"]
    assert EJEMPLOS
    for f in EJEMPLOS:
        ass = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert "VRT-GRC" in ass["verticales"], f.name
        r = V.evaluar(ass)
        assert r.warnings == []
        assert "VRT-GRC" in r.por_nis2["NIS2-20.1"].verticales
        assert "VRT-GRC" in r.por_nis2["NIS2-21.2.a"].verticales


def test_contraprueba_sin_grc_no_hay_agregacion_en_20():
    f = EJEMPLOS[0]
    ass = copy.deepcopy(yaml.safe_load(f.read_text(encoding="utf-8")))
    del ass["verticales"]["VRT-GRC"]
    r = V.evaluar(ass)
    assert "NIS2-20.1" not in r.por_nis2 or "VRT-GRC" not in r.por_nis2["NIS2-20.1"].verticales


def test_informes_sin_nombres_de_repos_privados():
    for t in ("T09", "T12"):
        txt = (ROOT / "docs" / "plan" / "informes" / f"{t}-dev-proyecto.md").read_text(encoding="utf-8")
        from smc.resources import urls_no_publicas
        assert urls_no_publicas(txt) == []
        assert "un repo privado" in txt
