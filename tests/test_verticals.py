"""T09: verticales y madurez por vertical."""
import copy
from pathlib import Path

import pytest
import yaml

from smc import verticals as V
from smc.catalog import load_all

ROOT = Path(__file__).resolve().parent.parent
ANTIGUOS = ["VRT-EDR", "VRT-IAM", "VRT-NET", "VRT-MAIL", "VRT-CLOUD", "VRT-APP", "VRT-DATA",
            "VRT-BCK", "VRT-VULN", "VRT-OT", "VRT-TPRM", "VRT-AWARE"]
NUEVOS = ["VRT-HUNT", "VRT-MDM", "VRT-ENDUSER", "VRT-FW", "VRT-SASE", "VRT-ZTNA", "VRT-OSI"]
# Copia literal de la lista pública del PLAN (contexto v0.5); independiente de la constante del módulo.
LISTA_PUBLICA = {
    "https://pedri77.github.io/edr-visual-app/", "https://pedri77.github.io/sase-visual-app/",
    "https://pedri77.github.io/Basic_Firewalls/", "https://pedri77.github.io/Basicos_Proteccion_Capas_OSI/",
    "https://pedri77.github.io/modelo_OSI/", "https://pedri77.github.io/ics-security-studio/",
    "https://pedri77.github.io/wafforge/", "https://pedri77.github.io/Basicos_email/",
    "https://github.com/pedri77/kev_dash_project", "https://github.com/pedri77/threat-intelligence-feeds",
}


def test_catalogo_ids_conservados_y_nuevos():
    ids = [v.id for v in V.cargar_verticales()]
    assert len(ids) == len(set(ids))
    assert set(ANTIGUOS) <= set(ids) and set(NUEVOS) <= set(ids)
    assert len(ids) == 19


def test_catalogo_valido():
    assert V.validar_catalogo() == []


def test_todo_controles_existe_en_catalogos():
    conocidos = {c.id for cs in load_all().values() for c in cs}
    for v in V.cargar_verticales():
        assert v.controles, v.id
        assert set(v.controles) <= conocidos, v.id


def test_urls_dentro_de_la_lista_publica():
    assert V.URLS_PUBLICAS == LISTA_PUBLICA
    usadas = [r["url"] for v in V.cargar_verticales() for r in v.recursos]
    assert usadas and set(usadas) <= LISTA_PUBLICA


def test_url_fuera_de_la_lista_pone_rojo():
    """Contraprueba: una URL de repo privado o ajena se detecta."""
    vs = V.cargar_verticales()
    vs[0].recursos.append({"titulo": "x", "url": "https://github.com/pedri77/sase-evaluation-pack"})
    assert any("fuera de la lista pública" in e for e in V.validar_catalogo(vs))
    assert V.validar_catalogo() == []   # el YAML real sigue limpio


def test_control_inexistente_se_detecta():
    vs = V.cargar_verticales()
    vs[0].controles.append("ENS-no.existe")
    assert any("control inexistente" in e for e in V.validar_catalogo(vs))


def test_pendientes_sin_url():
    pend = [e for v in V.cargar_verticales() for e in v.estado_recursos]
    textos = " ".join(e["proyecto"] for e in pend)
    for clave in ("ZTNA", "capa OSI", "3D"):
        assert clave in textos
    assert all(e["estado"] == "pendiente" and "url" not in e for e in pend)


def test_net_agrupa_los_cuatro_subverticales():
    net = next(v for v in V.cargar_verticales() if v.id == "VRT-NET")
    assert net.agrupa == ["VRT-FW", "VRT-SASE", "VRT-ZTNA", "VRT-OSI"]


def test_sin_seccion_todo_sin_evaluar():
    r = V.evaluar({"cliente": {}})
    assert r.madurez_media is None and r.warnings == []
    assert len(r.sin_evaluar) == 19 and not r.no_evaluables


def test_agregacion_nis2_caso_conocido():
    ass = {"verticales": {"VRT-EDR": {"madurez": 4}, "VRT-MAIL": {"madurez": 2},
                          "VRT-BCK": {"madurez": 5}, "VRT-AWARE": {"madurez": 1}}}
    r = V.evaluar(ass)
    g = r.por_nis2["NIS2-21.2.g"]   # EDR 4, MAIL 2, AWARE 1 -> 7/3
    assert g.madurez == 2.33 and g.verticales == ["VRT-EDR", "VRT-MAIL", "VRT-AWARE"]
    assert r.por_nis2["NIS2-21.2.b"].madurez == 4        # solo EDR (HUNT sin evaluar)
    assert r.por_nis2["NIS2-21.2.c"].madurez == 5        # BCK
    assert r.por_nis2["NIS2-21.2.h"].madurez is None     # DATA sin evaluar
    assert r.madurez_media == 3.0                        # (4+2+5+1)/4


def test_no_evaluable_con_motivo_no_puntua():
    ass = {"verticales": {"VRT-EDR": {"madurez": 4}, "VRT-HUNT": {"madurez": "no_evaluable", "motivo": "Sin SIEM"}}}
    r = V.evaluar(ass)
    b = r.por_nis2["NIS2-21.2.b"]
    assert b.madurez == 4 and b.no_evaluables == ["VRT-HUNT"]
    assert [x.motivo for x in r.no_evaluables] == ["Sin SIEM"]
    assert r.madurez_media == 4


@pytest.mark.parametrize("motivo", [None, "", "   "])
def test_no_evaluable_sin_motivo_da_error(motivo):
    ent = {"madurez": "no_evaluable"}
    if motivo is not None:
        ent["motivo"] = motivo
    with pytest.raises(V.VerticalesError, match="exige 'motivo'"):
        V.evaluar({"verticales": {"VRT-MDM": ent}})


def test_no_estricto_recoge_errores_sin_puntuar():
    r = V.evaluar({"verticales": {"VRT-MDM": {"madurez": "no_evaluable"}, "VRT-EDR": {"madurez": 3}}}, estricto=False)
    assert len(r.errores) == 1 and "VRT-MDM" in r.errores[0]
    assert r.madurez_media == 3
    assert next(x for x in r.verticales if x.id == "VRT-MDM").estado == "sin_evaluar"


@pytest.mark.parametrize("valor", [6, -1, 2.5, True, "3", None])
def test_madurez_invalida_da_error(valor):
    with pytest.raises(V.VerticalesError, match="madurez no válida"):
        V.evaluar({"verticales": {"VRT-EDR": {"madurez": valor}}})


def test_madurez_cero_cuenta_y_limites():
    r = V.evaluar({"verticales": {"VRT-EDR": {"madurez": 0}, "VRT-MAIL": {"madurez": 5}}})
    assert r.madurez_media == 2.5
    assert next(x for x in r.verticales if x.id == "VRT-EDR").estado == "evaluada"


def test_desconocida_y_seccion_mal_formada_dan_aviso():
    assert any("VRT-XXX" in w for w in V.evaluar({"verticales": {"VRT-XXX": {"madurez": 1}}}).warnings)
    assert any("no es un mapa" in w for w in V.evaluar({"verticales": "texto"}).warnings)
    assert V.evaluar("no es un mapa").madurez_media is None


def test_net_no_puntua_si_un_subvertical_esta_evaluado():
    r = V.evaluar({"verticales": {"VRT-NET": {"madurez": 5}, "VRT-FW": {"madurez": 1}}})
    assert r.por_nis2["NIS2-21.2.a"].madurez == 1 and r.por_nis2["NIS2-21.2.a"].verticales == ["VRT-FW"]
    assert r.madurez_media == 1
    # contraprueba: solo VRT-NET (sin hijos) sí puntúa
    assert V.evaluar({"verticales": {"VRT-NET": {"madurez": 5}}}).por_nis2["NIS2-21.2.a"].madurez == 5


@pytest.mark.parametrize("fichero", sorted((ROOT / "assessments" / "examples").glob("*.yaml")))
def test_ejemplos_tienen_seccion_valida(fichero):
    ass = yaml.safe_load(fichero.read_text(encoding="utf-8"))
    assert ass["verticales"]
    r = V.evaluar(ass)
    assert r.warnings == [] and r.madurez_media is not None and r.no_evaluables


def test_ejemplo_energia_valores():
    ass = yaml.safe_load((ROOT / "assessments/examples/ejemplo-energia.yaml").read_text(encoding="utf-8"))
    r = V.evaluar(ass)
    # VRT-NET=5 queda fuera por haber FW/ZTNA evaluados: 21.2.a = (OT 2 + FW 4)/2
    assert r.por_nis2["NIS2-21.2.a"].madurez == 3.0
    assert r.por_nis2["NIS2-21.2.j"].madurez == 1
    ass2 = copy.deepcopy(ass)
    ass2["verticales"].pop("VRT-FW")
    ass2["verticales"].pop("VRT-ZTNA")
    assert V.evaluar(ass2).por_nis2["NIS2-21.2.a"].madurez == 3.5   # ahora NET (5) y OT (2) puntúan


def test_plantilla_y_ejemplos_pasan_analyse():
    from smc.gap import analyse
    for f in (ROOT / "assessments").rglob("*.yaml"):
        ass = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert "verticales" in ass, f
        analyse(ass)   # la sección nueva no rompe el análisis
    plantilla = yaml.safe_load((ROOT / "assessments/assessment.template.yaml").read_text(encoding="utf-8"))
    assert V.evaluar(plantilla).no_evaluables
