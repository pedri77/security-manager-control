import copy
import re
from datetime import date

import pytest
import yaml

from smc import ai_act
from smc.ai_act import AIActError

INV = ai_act.INVENTARIO_TEMPLATE
ANTES = date(2027, 12, 1)
DESPUES = date(2027, 12, 2)


def _inv():
    return yaml.safe_load(INV.read_text(encoding="utf-8"))


def _sistema(**kw):
    base = {"id": "IA-T", "nombre": "Prueba", "rol": "responsable_despliegue", "nivel_riesgo": "alto_riesgo_anexo_iii",
            "supervision_humana": True, "registro": True, "alfabetizacion": True}
    base.update(kw)
    return {"organizacion": "Ficticia", "sistemas": [base]}


def _por_id(res, sid="IA-T"):
    s = next(x for x in res.sistemas if x.id == sid)
    return s, {o.id: o for o in s.obligaciones}


# --- Catálogo ---

def test_catalogo_valido_y_fuentes_https():
    assert ai_act.validar_catalogo() == []
    data = yaml.safe_load(ai_act.OBLIGACIONES_FILE.read_text(encoding="utf-8"))
    assert all(f["url"].startswith("https://") and f["consulta"] == date(2026, 11, 3) for f in data["fuentes"])
    assert tuple(data["roles"]) == ai_act.ROLES and tuple(data["niveles"]) == ai_act.NIVELES


def test_fechas_del_omnibus_en_el_catalogo():
    obl = {o.id: o for o in ai_act.cargar_obligaciones()}
    assert obl["AIA-041"].fecha("alto_riesgo_anexo_iii") == date(2027, 12, 2)
    assert obl["AIA-041"].fecha("alto_riesgo_anexo_i") == date(2028, 8, 2)
    assert obl["AIA-001"].fecha("minimo") == date(2025, 2, 2)
    assert obl["AIA-002"].fecha("prohibido") == date(2025, 2, 2)
    assert obl["AIA-003"].fecha("prohibido") == date(2026, 12, 2)
    assert obl["AIA-050"].fecha("transparencia") == date(2026, 8, 2)
    assert obl["AIA-051"].transitorio == {"en_mercado_antes_de": date(2026, 8, 2), "aplica_desde": date(2026, 12, 2)}
    assert obl["AIA-060"].fecha("uso_general") == date(2025, 8, 2)


def test_verificar_lleva_nota():
    verif = [o for o in ai_act.cargar_obligaciones() if o.verificar]
    assert {o.id for o in verif} == {"AIA-018", "AIA-019", "AIA-020", "AIA-046"}
    assert all(o.nota for o in verif)


def test_validar_catalogo_detecta_errores():
    obl = ai_act.cargar_obligaciones()
    malo = copy.deepcopy(obl[0])
    malo.niveles = ["riesgo_inventado"]
    malo.verificar, malo.nota = True, ""
    errores = ai_act.validar_catalogo(obl + [malo])
    assert any("ID duplicado" in e for e in errores)
    assert any("niveles no válidos" in e for e in errores)
    assert any("verificar sin nota" in e for e in errores)


# --- Clasificación ---

def test_clasificar_valida_nivel_y_rol():
    c = ai_act.clasificar({"id": "X", "nivel_riesgo": "minimo", "rol": ["proveedor", "responsable_despliegue"]})
    assert c.nivel == "minimo" and c.roles == ["proveedor", "responsable_despliegue"]
    with pytest.raises(AIActError, match="nivel de riesgo inexistente"):
        ai_act.clasificar({"id": "X", "nivel_riesgo": "riesgo_medio", "rol": "proveedor"})
    with pytest.raises(AIActError, match="rol inexistente"):
        ai_act.clasificar({"id": "X", "nivel_riesgo": "minimo", "rol": "usuario"})
    with pytest.raises(AIActError, match="sin rol"):
        ai_act.clasificar({"id": "X", "nivel_riesgo": "minimo"})
    with pytest.raises(AIActError, match="uso general"):
        ai_act.clasificar({"id": "X", "nivel_riesgo": "uso_general", "rol": "responsable_despliegue"})


def test_nivel_inexistente_da_error_en_obligaciones():
    inv = _sistema(nivel_riesgo="riesgo_inventado")
    with pytest.raises(AIActError, match="nivel de riesgo inexistente"):
        ai_act.obligaciones(inv, hoy=ANTES)
    res = ai_act.obligaciones(inv, hoy=ANTES, estricto=False)
    assert res.sistemas == [] and res.no_clasificados[0]["id"] == "IA-T" and res.errores
    assert ai_act.validar_inventario(inv)


def test_plantilla_carga_sin_errores():
    assert ai_act.validar_inventario(INV) == []
    res = ai_act.obligaciones(INV, hoy=date(2026, 11, 3))
    assert [s.id for s in res.sistemas] == ["IA-001", "IA-002", "IA-003"]
    assert res.errores == []


# --- Fechas (hoy inyectado) ---

def test_alto_riesgo_anexo_iii_antes_y_despues_de_2027_12_02():
    inv = _sistema()
    _, antes = _por_id(ai_act.obligaciones(inv, hoy=ANTES))
    _, despues = _por_id(ai_act.obligaciones(inv, hoy=DESPUES))
    assert antes["AIA-041"].estado == ai_act.APLICABLE_DESDE and antes["AIA-041"].aplica_desde == date(2027, 12, 2)
    assert despues["AIA-041"].estado == ai_act.VIGENTE
    assert antes["AIA-001"].estado == ai_act.VIGENTE           # art. 4 desde 2025-02-02


def test_anexo_i_sigue_pendiente_tras_2027_12_02():
    _, o = _por_id(ai_act.obligaciones(_sistema(nivel_riesgo="alto_riesgo_anexo_i"), hoy=DESPUES))
    assert o["AIA-041"].estado == ai_act.APLICABLE_DESDE and o["AIA-041"].aplica_desde == date(2028, 8, 2)
    assert "AIA-045" not in o                                  # art. 27 solo Anexo III


def test_contraprueba_alto_riesgo_sin_supervision_humana_queda_pendiente():
    s, o = _por_id(ai_act.obligaciones(_sistema(supervision_humana=False), hoy=DESPUES))
    assert o["AIA-041"].cumplimiento == ai_act.PENDIENTE
    assert "AIA-041" in [x.id for x in s.incumplidas]
    s2, o2 = _por_id(ai_act.obligaciones(_sistema(supervision_humana={"existe": True}), hoy=DESPUES))
    assert o2["AIA-041"].cumplimiento == ai_act.CUMPLIDA and "AIA-041" not in [x.id for x in s2.pendientes]
    # ausente cuenta como pendiente, nunca como cumplida
    inv = _sistema()
    del inv["sistemas"][0]["supervision_humana"]
    _, o3 = _por_id(ai_act.obligaciones(inv, hoy=ANTES))
    assert o3["AIA-041"].cumplimiento == ai_act.PENDIENTE and o3["AIA-041"].estado == ai_act.APLICABLE_DESDE


def test_roles_filtran_obligaciones():
    _, prov = _por_id(ai_act.obligaciones(_sistema(rol="proveedor"), hoy=DESPUES))
    _, desp = _por_id(ai_act.obligaciones(_sistema(), hoy=DESPUES))
    _, imp = _por_id(ai_act.obligaciones(_sistema(rol="importador"), hoy=DESPUES))
    assert "AIA-015" in prov and "AIA-041" not in prov
    assert "AIA-041" in desp and "AIA-015" not in desp
    assert set(imp) == {"AIA-030"}


def test_supuestos_y_transitorio_art_50_2():
    base = dict(rol="proveedor", nivel_riesgo="minimo", supuestos=["contenido_sintetico"])
    _, sin_fecha = _por_id(ai_act.obligaciones(_sistema(**base), hoy=date(2026, 11, 3)))
    _, antiguo = _por_id(ai_act.obligaciones(_sistema(**base, en_mercado_desde="2026-07-01"), hoy=date(2026, 11, 3)))
    _, nuevo = _por_id(ai_act.obligaciones(_sistema(**base, en_mercado_desde="2026-09-01"), hoy=date(2026, 11, 3)))
    assert sin_fecha["AIA-051"].aplica_desde == date(2026, 8, 2)          # sin dato: la fecha más temprana
    assert antiguo["AIA-051"].aplica_desde == date(2026, 12, 2) and antiguo["AIA-051"].estado == ai_act.APLICABLE_DESDE
    assert nuevo["AIA-051"].aplica_desde == date(2026, 8, 2) and nuevo["AIA-051"].estado == ai_act.VIGENTE
    _, sin_supuesto = _por_id(ai_act.obligaciones(_sistema(rol="proveedor", nivel_riesgo="minimo"), hoy=DESPUES))
    assert "AIA-051" not in sin_supuesto


def test_transparencia_sin_supuestos_aplica_todo_el_art_50_con_aviso():
    res = ai_act.obligaciones(_sistema(rol=["proveedor", "responsable_despliegue"], nivel_riesgo="transparencia"), hoy=DESPUES)
    _, o = _por_id(res)
    assert {"AIA-050", "AIA-051", "AIA-052", "AIA-053"} <= set(o)
    assert any("sin supuestos" in w for w in res.warnings)


def test_prohibido_y_nuevas_prohibiciones_del_omnibus():
    _, gen = _por_id(ai_act.obligaciones(_sistema(nivel_riesgo="prohibido"), hoy=date(2026, 11, 3)))
    assert set(gen) == {"AIA-002"} and gen["AIA-002"].estado == ai_act.VIGENTE
    _, nuevo = _por_id(ai_act.obligaciones(
        _sistema(nivel_riesgo="prohibido", supuestos=["contenido_intimo_no_consentido"]), hoy=date(2026, 11, 3)))
    assert set(nuevo) == {"AIA-003"} and nuevo["AIA-003"].aplica_desde == date(2026, 12, 2)


def test_uso_general_transitorio_art_111_3():
    _, o = _por_id(ai_act.obligaciones(
        _sistema(rol="proveedor", nivel_riesgo="uso_general_riesgo_sistemico", en_mercado_desde=date(2025, 1, 1)),
        hoy=date(2026, 11, 3)))
    assert {"AIA-060", "AIA-062"} <= set(o) and o["AIA-060"].aplica_desde == date(2027, 8, 2)


def test_datos_mal_formados_dan_aviso():
    assert ai_act.obligaciones({"sistemas": "texto"}, hoy=ANTES).warnings
    assert ai_act.obligaciones([], hoy=ANTES).warnings
    res = ai_act.obligaciones(_sistema(supuestos="interaccion", en_mercado_desde="ayer"), hoy=ANTES)
    assert any("no es una lista" in w for w in res.warnings)
    assert any("no es una fecha" in w for w in res.warnings)


# --- Seguridad de agentes ---

def test_riesgos_agente_plantilla():
    h = ai_act.riesgos_agente(INV)
    ids = {(x.agente, x.id) for x in h}
    assert {("AG-002", f"AGT-0{i}") for i in range(1, 6)} <= ids
    assert not [x for x in h if x.agente == "AG-001"]           # agente bien configurado: sin hallazgos


def _agente(**kw):
    ag = {"id": "AG-T", "herramientas": [{"nombre": "leer", "permisos": ["lectura"], "limite_llamadas": 5}],
          "permisos_minimos": True, "supervision_humana": True, "registro": True,
          "entrada_no_confiable": True, "mitigacion_prompt_injection": ["filtro"]}
    ag.update(kw)
    return {"sistemas": [{"id": "IA-T", "nivel_riesgo": "minimo", "rol": "responsable_despliegue",
                          "datos_personales": True, "agentes": [ag]}]}


@pytest.mark.parametrize("cambio, esperado", [
    ({"herramientas": [{"nombre": "leer", "permisos": ["lectura"]}]}, "AGT-01"),
    ({"herramientas": [{"nombre": "borrar", "permisos": ["borrado"], "limite_llamadas": 1}]}, "AGT-02"),
    ({"permisos_minimos": False}, "AGT-02"),
    ({"supervision_humana": False}, "AGT-03"),
    ({"registro": None}, "AGT-04"),
    ({"mitigacion_prompt_injection": []}, "AGT-05"),
    ({"herramientas": [{"nombre": "post", "permisos": ["red"], "limite_llamadas": 3}]}, "AGT-06"),
])
def test_cada_comprobacion(cambio, esperado):
    assert [x.id for x in ai_act.riesgos_agente(_agente())] == []
    assert esperado in [x.id for x in ai_act.riesgos_agente(_agente(**cambio))]


def test_ids_owasp_y_atlas_con_formato_real():
    owasp = {f"LLM{n:02d}:2025" for n in range(1, 11)}
    for titulo, sev, ow, atlas, mit in ai_act.COMPROBACIONES.values():
        assert set(ow) <= owasp and sev in ("alta", "media")
        assert all(re.fullmatch(r"AML\.T\d{4}(\.\d{3})?", t) for t in atlas)
        assert mit and all(re.fullmatch(r"AML\.M\d{4}", m) for m in mit)
    assert ai_act.COMPROBACIONES["AGT-05"][2] == ["LLM01:2025"]
    assert "AML.T0051" in ai_act.COMPROBACIONES["AGT-05"][3]


def test_entrada_no_confiable_false_no_exige_mitigacion():
    assert "AGT-05" not in [x.id for x in ai_act.riesgos_agente(_agente(entrada_no_confiable=False, mitigacion_prompt_injection=[]))]


# --- Render ---

def test_render_aviso_juridico_fuentes_y_escape():
    inv = _sistema(nombre="Bot <script>alert(1)</script> | x")
    md = ai_act.render_markdown(ai_act.obligaciones(inv, hoy=ANTES), ai_act.riesgos_agente(inv))
    assert "no es asesoramiento jurídico" in md
    assert "https://eur-lex.europa.eu/eli/reg/2026/1744/oj" in md and "https://genai.owasp.org/llm-top-10/" in md
    assert "<script>" not in md and "&lt;script&gt;" in md and "\\| x" in md
    assert "Sin hallazgos" in md
    assert "aplicable desde 2027-12-02" in md


def test_render_plantilla_marca_verificar():
    inv = _sistema(rol="proveedor")
    md = ai_act.render_markdown(ai_act.obligaciones(inv, hoy=ANTES))
    assert "**verificar**" in md and "Seguridad de agentes" not in md
