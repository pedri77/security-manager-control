"""T34: art. 111.2 del RIA (régimen transitorio del capítulo III) y retest fallido en el informe HTML."""
from datetime import date

import pytest

from smc import ai_act, offensive as o, report_html

HOY = date(2026, 11, 3)


def _inv(**kw):
    base = {"id": "IA-T", "nombre": "Prueba", "rol": ["proveedor", "responsable_despliegue"],
            "nivel_riesgo": "alto_riesgo_anexo_iii", "en_mercado_desde": "2026-01-01",
            "cambios_significativos": False}
    base.update(kw)
    return {"organizacion": "Ficticia", "sistemas": [base]}


def _sis(hoy=HOY, catalogo=None, **kw):
    return ai_act.obligaciones(_inv(**kw), hoy, catalogo=catalogo).sistemas[0]


def _ids(lista):
    return {x.id for x in lista}


def _cap3():
    return {x.id for x in ai_act.cargar_obligaciones() if ai_act.es_capitulo_iii(x.articulo)}


# --------------------------------------------------------------- criterio del capítulo III

def test_es_capitulo_iii_por_campo_articulo():
    for a in ("art. 9", "art. 26.1", "arts. 16 y 17", "arts. 43, 47 y 48", "art. 49.3", "art. 6"):
        assert ai_act.es_capitulo_iii(a), a
    for a in ("art. 4", "art. 5", "art. 5.1 b bis) y b ter)", "art. 50.1", "art. 53", "arts. 72 y 73", "art. 111.2",
              "art. 50", "", "sin número", "arts. 48 y 50"):                      # los límites 5/50 y la cita mixta quedan fuera
        assert not ai_act.es_capitulo_iii(a), a


def test_catalogo_real_capitulo_iii_incluye_lo_esperado_y_no_72_73():
    c = _cap3()
    assert {"AIA-010", "AIA-015", "AIA-017", "AIA-018", "AIA-019", "AIA-030", "AIA-031", "AIA-040", "AIA-045", "AIA-046"} <= c
    assert not ({"AIA-001", "AIA-002", "AIA-020", "AIA-050", "AIA-060", "AIA-070"} & c)


# --------------------------------------------------------------- (a) alto riesgo preexistente sin cambios

def test_anexo_iii_en_mercado_sin_cambios_no_emite_capitulo_iii_y_lo_pasa_a_regimen_transitorio():
    s = _sis(cambios_significativos=False)
    emitidas = _ids(s.obligaciones)
    assert not (emitidas & _cap3())
    assert _ids(s.regimen_transitorio) == {x for x in _cap3()
                                           if any(x == c.id and set(c.roles) & {"proveedor", "responsable_despliegue"}
                                                  and "alto_riesgo_anexo_iii" in c.niveles and not c.supuesto
                                                  for c in ai_act.cargar_obligaciones())}
    assert all(t.aplica_desde is None and "cambios significativos" in t.condicion for t in s.regimen_transitorio)
    # AIA-070 sigue como aviso; art. 4 y 72/73 no se recortan
    assert {"AIA-070", "AIA-001", "AIA-020"} <= emitidas
    assert not any(p.id in _cap3() for p in s.pendientes)


def test_sin_campo_cambios_significativos_no_recorta_y_avisa():
    # T36: dato ausente = «no consta»; antes recortaba en silencio
    inv = _inv()
    del inv["sistemas"][0]["cambios_significativos"]
    r = ai_act.obligaciones(inv, HOY)
    s = r.sistemas[0]
    assert s.regimen_transitorio == [] and _cap3() & {"AIA-010", "AIA-015"} <= _ids(s.obligaciones)
    assert any("no consta si hay cambios" in w for w in r.warnings)


def test_contraprueba_con_cambios_significativos_vuelven_todas():
    s = _sis(cambios_significativos=True)
    assert s.regimen_transitorio == []
    assert _cap3() & {"AIA-010", "AIA-015", "AIA-017", "AIA-040"} <= _ids(s.obligaciones)
    sin = _sis(en_mercado_desde="2028-01-01")                                   # contraprueba: nuevo en el mercado
    assert sin.regimen_transitorio == [] and "AIA-010" in _ids(sin.obligaciones)
    assert _ids(sin.obligaciones) == _ids(s.obligaciones) - {"AIA-070"}   # mismas (AIA-070 solo en preexistentes)
    sin_dato = _sis(en_mercado_desde=None)
    assert sin_dato.regimen_transitorio == [] and "AIA-010" in _ids(sin_dato.obligaciones)


def test_anexo_i_usa_su_propia_fecha():
    # en el mercado en 2028-01-01: antes del corte del Anexo I (2028-08-02) pero después del del Anexo III
    a1 = _sis(nivel_riesgo="alto_riesgo_anexo_i", en_mercado_desde="2028-01-01")
    a3 = _sis(en_mercado_desde="2028-01-01")
    assert a1.regimen_transitorio and not (_ids(a1.obligaciones) & _cap3())
    assert a3.regimen_transitorio == [] and "AIA-010" in _ids(a3.obligaciones)


def test_niveles_que_no_son_alto_riesgo_no_se_recortan():
    s = _sis(nivel_riesgo="transparencia", supuestos=["interaccion"])
    assert s.regimen_transitorio == [] and "AIA-050" in _ids(s.obligaciones)


# --------------------------------------------------------------- autoridad pública

def test_autoridad_publica_antes_de_2030_va_a_regimen_con_fecha():
    s = _sis(autoridad_publica=True, cambios_significativos=False, hoy=date(2030, 8, 1))
    assert s.regimen_transitorio and not (_ids(s.obligaciones) & _cap3())
    assert all(t.aplica_desde == date(2030, 8, 2) for t in s.regimen_transitorio)


def test_contraprueba_autoridad_publica_2030_08_03_vuelven_como_vigentes():
    s = _sis(autoridad_publica=True, cambios_significativos=False, hoy=date(2030, 8, 3))
    assert s.regimen_transitorio == []
    volvieron = [x for x in s.obligaciones if x.id in _cap3()]
    assert {"AIA-010", "AIA-015"} <= _ids(volvieron)
    assert all(x.aplica_desde == date(2030, 8, 2) and x.estado == ai_act.VIGENTE for x in volvieron)
    # el mismo día 2030-08-02 ya aplica
    assert _sis(autoridad_publica=True, hoy=date(2030, 8, 2)).regimen_transitorio == []
    # sin autoridad pública no vuelven nunca por fecha
    assert _sis(hoy=date(2031, 1, 1)).regimen_transitorio


def test_catalogo_inyectado_sin_cap_iii_no_rompe():
    cat = [x for x in ai_act.cargar_obligaciones() if x.id in ("AIA-001", "AIA-070")]
    s = _sis(catalogo=cat)
    assert _ids(s.obligaciones) == {"AIA-001", "AIA-070"} and s.regimen_transitorio == []


def test_nota_aia070_documenta_el_alcance():
    n = next(x for x in ai_act.cargar_obligaciones() if x.id == "AIA-070").nota
    assert "regimen_transitorio" in n and "capítulo III" in n and "2030-08-02" in n
    assert ai_act.validar_catalogo() == []


def test_render_markdown_muestra_el_regimen_transitorio_escapado():
    res = ai_act.obligaciones(_inv(nombre="<b>x</b>"), HOY)
    md = ai_act.render_markdown(res)
    assert "Régimen transitorio (art. 111.2 RIA)" in md and "<b>" not in md
    assert "Régimen transitorio" not in ai_act.render_markdown(ai_act.obligaciones(_inv(cambios_significativos=True), HOY))


def test_plantilla_sigue_valida():
    assert ai_act.validar_inventario(ai_act.INVENTARIO_TEMPLATE) == []


# --------------------------------------------------------------- (b) informe HTML

def _pt(*extra):
    h = {"id": "H-9", "titulo": "Fallo <script>alert(1)</script>", "severidad": "alta", "estado": "corregido",
         "fecha_deteccion": "2026-09-01", "fecha_retest": "2026-10-20", "resultado_retest": "persiste",
         "activo": "srv<img src=x>", "control": "A.8"}
    h.update(extra[0] if extra else {})
    return {"hallazgos": [h]}


def test_html_retest_fallido_tabla_propia_y_escapada():
    html = report_html.render_pentest(o.estado_hallazgos(_pt(), HOY))
    assert "Retest fallido" in html and "Resultado del retest" in html and "persiste" in html and "2026-10-20" in html
    assert "<script>" not in html and "&lt;script&gt;" in html and "<img" not in html


def test_html_contraprueba_sin_retest_fallido_no_hay_tabla():
    for extra in ({"resultado_retest": "corregido"}, {"resultado_retest": ""}, {"estado": "abierto"}):
        html = report_html.render_pentest(o.estado_hallazgos(_pt(extra), HOY))
        assert "Retest fallido" not in html and "Resultado del retest" not in html


def test_html_retest_fallido_en_el_informe_completo_con_extras():
    extras = report_html.calcular_extras(HOY, pentest=_pt())
    assert "Retest fallido" in report_html.render_pentest(extras["pentest"])


# --------------------------------------------------------------- T36 hallazgo 1: banderas del art. 111.2

def _inv_sin(campo=None, **kw):
    inv = _inv(**kw)
    if campo:
        inv["sistemas"][0].pop(campo, None)
    return inv


@pytest.mark.parametrize("valor", ["sí", "true", "no", 1, 0, {"existe": True}, [True]])
def test_t36_h1_cambios_significativos_que_no_es_bool_es_error_y_no_recorta(valor):
    inv = _inv(cambios_significativos=valor)
    assert any("cambios_significativos debe ser true o false" in e for e in ai_act.validar_inventario(inv))
    r = ai_act.obligaciones(inv, HOY)
    assert r.sistemas[0].regimen_transitorio == [] and any("cambios_significativos" in w for w in r.warnings)


def test_t36_h1_autoridad_publica_que_no_es_bool_es_error():
    errs = ai_act.validar_inventario(_inv(autoridad_publica="sí"))
    assert any("autoridad_publica debe ser true o false" in e for e in errs)


@pytest.mark.parametrize("valor", ["mañana", 20260301, True, [1]])
def test_t36_h1_en_mercado_desde_invalido_es_error(valor):
    assert any("en_mercado_desde" in e for e in ai_act.validar_inventario(_inv(en_mercado_desde=valor)))


def test_t36_h1_en_mercado_desde_con_hora_no_rompe():
    from datetime import datetime
    s = _sis(en_mercado_desde=datetime(2026, 1, 1, 10, 0))
    assert s.regimen_transitorio
    assert ai_act.validar_inventario(_inv(en_mercado_desde=datetime(2026, 1, 1, 10, 0))) == []


def test_t36_h1_contraprueba_bool_validos_y_ausente_sin_errores():
    for v in (True, False):
        assert ai_act.validar_inventario(_inv(cambios_significativos=v, autoridad_publica=v)) == []
    assert ai_act.validar_inventario(_inv_sin("cambios_significativos")) == []


def test_t36_h1_plantilla_nota_sin_jerga_del_plan():
    t = (ai_act.OBLIGACIONES_FILE).read_text(encoding="utf-8")
    assert "Desde T34" not in t and "criterio del plan" not in t
