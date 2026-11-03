"""T29: endurecimiento de v0.7 (hallazgos 1-6 y 9 de la revisión de las olas 12-13)."""
import re
from datetime import date
from pathlib import Path

import yaml

from smc import ai_act, mitre, offensive as o
from smc.pmo import analizar, cargar_proyecto

ROOT = Path(__file__).resolve().parent.parent
HOY = date(2026, 11, 3)
PB = "vulnerabilities/playbooks/caso-uso/PB-UC-900.md"


# --------------------------------------------------------------- hallazgos 1 y 2: madurez MITRE con purple

def _caso(**kw):
    base = {"id": "UC-X", "nombre": "x", "tactica": "execution", "mitre": ["T1059"], "deteccion": "regla",
            "playbook": PB, "estado": "activo", "ultima_prueba": ""}
    base.update(kw)
    return base


def _root(tmp_path, casos):
    d = tmp_path / "vulnerabilities/playbooks/caso-uso"
    d.mkdir(parents=True, exist_ok=True)
    (d / "PB-UC-900.md").write_text("# pb", encoding="utf-8")
    f = tmp_path / "catalog.yaml"
    f.write_text(yaml.safe_dump({"use_cases": casos}), encoding="utf-8")
    return f, tmp_path


def _purple(*ej):
    return o.Purple([o.Ejercicio(id=f"PP-{i}", fecha=date.fromisoformat(f), tecnica=t, caso_uso=uc, resultado=r)
                     for i, (uc, t, r, f) in enumerate(ej, 1)])


def _nivel(tmp_path, casos, purple, uc="UC-X"):
    f, r = _root(tmp_path, casos)
    return mitre.madurez(f, HOY, r, purple)["casos"][uc]


def test_h1_purple_de_otra_tecnica_no_sube_el_caso(tmp_path):
    # Escenario del revisor: UC con T1566 + ejercicio detectado de T1003 (que no es de ese caso).
    casos = [_caso(mitre=["T1566.001"])]
    ajeno = _purple(("UC-X", "T1003", "detectado", "2026-10-30"))
    assert _nivel(tmp_path, casos, ajeno) == 3                       # antes del arreglo: 5
    propio = _purple(("UC-X", "T1566.001", "detectado", "2026-10-30"))
    assert _nivel(tmp_path, casos, propio) == 5                      # contraprueba: con su técnica sí sube


def test_h2_un_no_detectado_posterior_anula_el_detectado(tmp_path):
    casos = [_caso()]
    anulado = _purple(("UC-X", "T1059", "detectado", "2026-09-01"), ("UC-X", "T1059", "no_detectado", "2026-10-01"))
    assert _nivel(tmp_path, casos, anulado) == 3                     # antes del arreglo: 5
    parcial = _purple(("UC-X", "T1059", "detectado", "2026-09-01"), ("UC-X", "T1059", "parcial", "2026-10-01"))
    assert _nivel(tmp_path, casos, parcial) == 3
    # Contraprueba: si el detectado es el más reciente, sube.
    vigente = _purple(("UC-X", "T1059", "no_detectado", "2026-09-01"), ("UC-X", "T1059", "detectado", "2026-10-01"))
    assert _nivel(tmp_path, casos, vigente) == 5


def test_h2_mismo_dia_manda_el_no_detectado_y_el_futuro_no_cuenta(tmp_path):
    casos = [_caso(mitre=["T1059", "T1027"])]
    mismo_dia = _purple(("UC-X", "T1059", "detectado", "2026-10-01"), ("UC-X", "T1059", "no_detectado", "2026-10-01"))
    assert _nivel(tmp_path, casos, mismo_dia) == 3
    futuro = _purple(("UC-X", "T1059", "detectado", "2026-10-01"), ("UC-X", "T1059", "no_detectado", "2027-01-01"))
    assert _nivel(tmp_path, casos, futuro) == 5                      # el no_detectado de 2027 aún no ha ocurrido
    # otra técnica del caso sigue detectada aunque la primera falle
    dos = _purple(("UC-X", "T1059", "no_detectado", "2026-10-02"), ("UC-X", "T1027", "detectado", "2026-10-01"))
    assert _nivel(tmp_path, casos, dos) == 5


def test_h1_h2_la_madurez_nunca_baja_del_catalogo(tmp_path):
    casos = [_caso(deteccion="probada", ultima_prueba="2026-10-01")]  # declarado: 5
    malo = _purple(("UC-X", "T1059", "no_detectado", "2026-10-20"))
    assert _nivel(tmp_path, casos, malo) == 5
    # contraprueba: sin ese suelo el caso sin prueba declarada se queda en 3
    assert _nivel(tmp_path, [_caso()], malo) == 3


def test_h1_navigator_tambien_filtra_por_tecnica(tmp_path):
    f, r = _root(tmp_path, [_caso(mitre=["T1566.001"])])
    cap = mitre.a_navigator(f, HOY, r, _purple(("UC-X", "T1003", "detectado", "2026-10-30")))
    assert [t["score"] for t in cap["techniques"]] == [3]


def test_h1_catalogo_real_uc002_no_sube_con_t1003():
    p = _purple(("UC-002", "T1003", "detectado", "2026-10-30"))
    assert mitre.madurez(hoy=HOY, purple=p)["casos"]["UC-002"] == mitre.madurez(hoy=HOY)["casos"]["UC-002"]


# --------------------------------------------------------------- hallazgo 3: retest fallido

def _pentest(**h):
    base = {"id": "H-9", "titulo": "Fallo", "severidad": "alta", "estado": "corregido", "fecha_deteccion": "2026-09-01",
            "fecha_retest": "2026-10-20", "resultado_retest": "persiste"}
    base.update(h)
    return {"hallazgos": [base]}


def test_h3_corregido_con_retest_persiste_cuenta_como_abierto_y_fuera_de_sla():
    e = o.estado_hallazgos(_pentest(), HOY)                          # 63 días > SLA de alta
    assert [h.id for h in e.abiertos] == ["H-9"] and [h.id for h in e.retest_fallido] == ["H-9"]
    assert [f.hallazgo.id for f in e.fuera_sla] == ["H-9"] and e.fuera_sla[0].dias == 63   # SLA desde fecha_deteccion
    assert e.por_severidad["alta"] == 1
    assert any("H-9" in a and "persiste" in a for a in e.avisos)
    assert "Retest fallido" in o.render_markdown(e)


def test_h3_parcial_igual_y_corregido_de_verdad_no():
    e = o.estado_hallazgos(_pentest(resultado_retest="parcial"), HOY)
    assert [h.id for h in e.retest_fallido] == ["H-9"]
    # contraprueba: retest `corregido` (o sin resultado) no es abierto ni fallido
    for res in ("corregido", ""):
        e = o.estado_hallazgos(_pentest(resultado_retest=res), HOY)
        assert e.abiertos == [] and e.retest_fallido == [] and e.fuera_sla == []
    # un cerrado con retest `persiste` solo cuenta si su estado es `corregido`
    e = o.estado_hallazgos(_pentest(estado="aceptado", fecha_revision="2027-01-01"), HOY)
    assert e.retest_fallido == [] and e.abiertos == []


# --------------------------------------------------------------- hallazgo 4: art. 111.2

def _sist(**kw):
    base = {"id": "IA-T", "nombre": "Prueba", "rol": "proveedor", "nivel_riesgo": "alto_riesgo_anexo_iii",
            "en_mercado_desde": "2026-03-01"}
    base.update(kw)
    return {"organizacion": "Ficticia", "sistemas": [base]}


def _aia070(**kw):
    res = ai_act.obligaciones(_sist(**kw), HOY)
    s = res.sistemas[0]
    return {x.id: x for x in s.obligaciones}.get("AIA-070"), res


def test_h4_catalogo_tiene_el_art_111_2():
    o70 = next(x for x in ai_act.cargar_obligaciones() if x.id == "AIA-070")
    assert o70.articulo == "art. 111.2" and o70.fuente == "OMNIBUS" and o70.preexistente
    assert set(o70.roles) == {"proveedor", "responsable_despliegue"}
    assert ai_act.validar_catalogo() == []


def test_h4_sistema_preexistente_sin_cambios_no_esta_obligado_y_aviso():
    a, res = _aia070()
    assert a is not None and a.aplica_desde == date(2027, 12, 2)
    assert "Sin cambios significativos de diseño no está obligado" in a.nota
    assert any("cambios_significativos" in w for w in res.warnings)


def test_h4_autoridad_publica_sin_cambios_2030_08_02_y_con_cambios_fecha_del_capitulo():
    a, _ = _aia070(autoridad_publica=True, cambios_significativos=False)
    assert a.aplica_desde == date(2030, 8, 2) and a.estado == "aplicable_desde"
    a, _ = _aia070(autoridad_publica=True, cambios_significativos=True)
    assert a.aplica_desde == date(2027, 12, 2) and "cambios significativos" in a.nota
    a, _ = _aia070(nivel_riesgo="alto_riesgo_anexo_i", autoridad_publica=True, cambios_significativos=False)
    assert a.aplica_desde == date(2030, 8, 2)


def test_h4_contraprueba_no_se_emite_si_no_es_preexistente():
    assert _aia070(en_mercado_desde="2028-01-01")[0] is None          # después de la fecha del capítulo III
    assert _aia070(en_mercado_desde="2027-12-02")[0] is None          # el mismo día: no es anterior
    assert _aia070(en_mercado_desde=None)[0] is None                  # sin dato
    assert _aia070(nivel_riesgo="transparencia", supuestos=["interaccion"])[0] is None


def test_h4_plantilla_documenta_los_campos_nuevos():
    t = (ROOT / "ai" / "inventario.template.yaml").read_text(encoding="utf-8")
    assert "cambios_significativos" in t and "autoridad_publica" in t
    assert ai_act.validar_inventario(ai_act.INVENTARIO_TEMPLATE) == []


# --------------------------------------------------------------- hallazgo 5: *.ics

def test_h5_ics_en_gitignore():
    lineas = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "*.ics" in lineas
    assert not (ROOT / "tests" / "_x.ics").exists()


# --------------------------------------------------------------- hallazgo 6: aviso PMO

def _pmo(presupuesto_tarea=None, con_coste=True):
    t = {"id": "A", "titulo": "A", "controles": ["X"], "responsable": "Consultor", "horas_estimadas": 10, "avance": 50,
         "inicio": "2026-01-10", "fin": "2026-01-20"}
    if presupuesto_tarea is not None:
        t["presupuesto"] = presupuesto_tarea
    d = {"proyecto": {"id": "P", "nombre": "N", "cliente": "C", "inicio": "2026-01-01", "fin": "2026-12-31",
                      "presupuesto": {"horas": 1000, "licencias": 100, "servicios": 0, "formacion": 0}},
         "tarifas": {"Consultor": 100}, "tareas": [t],
         "imputaciones": [{"fecha": "2026-01-12", "rol": "Consultor", "tarea": "A", "horas": 3}],
         "costes": [{"proveedor": "P", "concepto": "lic", "importe": 50, "fecha": "2026-01-14",
                     "partida": "licencias", "tarea": "A"}] if con_coste else []}
    return cargar_proyecto(d)


def test_h6_aviso_con_costes_no_laborales_y_sin_presupuesto_explicito():
    a = analizar(_pmo(), date(2026, 1, 15))
    assert any(x.startswith("A: tiene costes no laborales y no tiene 'presupuesto' explícito") for x in a.avisos)


def test_h6_contrapruebas_sin_aviso():
    hoy = date(2026, 1, 15)
    assert not any("costes no laborales" in x for x in analizar(_pmo(presupuesto_tarea=2000), hoy).avisos)   # explícito
    assert not any("costes no laborales" in x for x in analizar(_pmo(con_coste=False), hoy).avisos)          # sin costes
    # un coste futuro no cuenta, tampoco el aviso
    assert not any("costes no laborales" in x for x in analizar(_pmo(), date(2026, 1, 13)).avisos)


# --------------------------------------------------------------- hallazgo 9: ids de MITRE ATLAS

# Comprobados el 2026-11-03 contra ATLAS 2026.10 (mitre-atlas/atlas-data, dist/v6/ATLAS-2026.10.yaml).
# El ATLAS.yaml de la raíz de dist/ está obsoleto (5.6.0) y no los contiene.
ATLAS_2026_10 = {
    "AML.T0029": "Denial of AI Service", "AML.T0034": "Cost Harvesting", "AML.T0034.002": "Agentic Resource Consumption",
    "AML.T0051": "LLM Prompt Injection", "AML.T0051.001": "Indirect", "AML.T0053": "AI Agent Tool Invocation",
    "AML.T0086": "Exfiltration via AI Agent Tool Invocation", "AML.T0101": "Data Destruction via AI Agent Tool Invocation",
    "AML.M0004": "Limit AI Service Query Volume and Rate", "AML.M0020": "Generative AI Guardrails",
    "AML.M0024": "AI Telemetry Logging and Monitoring", "AML.M0026": "Manage AI Agent Service Access",
    "AML.M0028": "Enforce Access Controls for AI Agent Tools", "AML.M0029": "Human In-the-Loop for AI Agent Actions",
    "AML.M0030": "Restrict AI Agent Tool Invocation on Untrusted Data",
    "AML.M0033": "Input and Output Validation for AI Agent Components", "AML.M0036": "Limit AI Workload Resource Consumption",
    "AML.M0037": "AI Agent Authority Expansion Controls",
}


def test_h9_ids_atlas_usados_existen_en_atlas_2026_10():
    usados = {i for c in ai_act.COMPROBACIONES.values() for lista in c[3:5] for i in lista}
    assert usados <= set(ATLAS_2026_10), sorted(usados - set(ATLAS_2026_10))
    assert {"AML.T0101", "AML.M0036", "AML.M0037"} <= usados
    assert all(re.fullmatch(r"AML\.[TM]\d{4}(\.\d{3})?", i) for i in usados)


def test_h9_contraprueba_un_id_inventado_no_pasa():
    inventado = {"AML.T9999"}
    assert not inventado <= set(ATLAS_2026_10)
