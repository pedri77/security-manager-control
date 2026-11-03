from datetime import date
from decimal import Decimal as D
from pathlib import Path

import yaml

from smc.pmo import analizar, cargar_proyecto, eventos_ics, exportar_ics, render_markdown

RAIZ = Path(__file__).resolve().parent.parent
EJ = RAIZ / "pmo" / "examples" / "ejemplo-energia.yaml"
EVAL = RAIZ / "assessments" / "examples" / "ejemplo-energia.yaml"
HOY = date(2026, 11, 3)


def base(**extra):
    d = {
        "proyecto": {"id": "P", "nombre": "N", "cliente": "C", "inicio": "2026-01-01", "fin": "2026-12-31",
                     "presupuesto": {"horas": 1000, "licencias": 100, "servicios": 0, "formacion": 0}},
        "tarifas": {"Consultor": 100, "Analista": 50},
        "tareas": [
            {"id": "A", "titulo": "A", "controles": ["X"], "responsable": "Consultor", "presupuesto": 1000,
             "avance": 50, "inicio": "2026-01-10", "fin": "2026-01-20"},
            {"id": "B", "titulo": "B", "controles": ["X"], "responsable": "Analista", "presupuesto": 500,
             "avance": 20, "inicio": "2026-01-15", "fin": "2026-01-25"},
        ],
        "imputaciones": [
            {"fecha": "2026-01-12", "rol": "Consultor", "tarea": "A", "horas": 3},
            {"fecha": "2026-01-13", "rol": "Analista", "tarea": "B", "horas": 2},
        ],
        "costes": [{"proveedor": "P", "concepto": "lic", "importe": 50, "fecha": "2026-01-14",
                    "partida": "licencias", "tarea": "B"}],
    }
    d.update(extra)
    return d


# Caso a mano, hoy = 2026-01-15:
#   PV: A planificada 5/10 = 0,5 -> 500; B empieza hoy -> 0.          PV = 500
#   EV: A 1000*0,5 = 500; B 500*0,2 = 100.                              EV = 600
#   AC: A 3 h * 100 = 300; B 2 h * 50 = 100 + licencia 50 = 150.       AC = 450
#   CPI = 600/450 = 1,33 ; SPI = 600/500 = 1,20
def test_evm_a_mano():
    a = analizar(cargar_proyecto(base()), date(2026, 1, 15))
    e = a.evm
    assert (e.pv, e.ev, e.ac, e.bac) == (D("500.00"), D("600.00"), D("450.00"), D("1500.00"))
    assert (e.cpi, e.spi) == (D("1.33"), D("1.20"))


def test_evm_contraprueba_cambia_con_la_fecha_y_el_avance():
    a = analizar(cargar_proyecto(base()), date(2026, 1, 20))
    # A completa (1000) + B 5/10 (250): PV 1250; ya no es 500
    assert a.evm.pv == D("1250.00") and a.evm.spi == D("0.48")
    d = base()
    d["tareas"][0]["avance"] = 0
    assert analizar(cargar_proyecto(d), date(2026, 1, 15)).evm.ev == D("100.00")


def test_cpi_spi_division_por_cero():
    d = base(imputaciones=[], costes=[])
    a = analizar(cargar_proyecto(d), date(2026, 1, 15))
    assert a.evm.cpi is None and any("CPI" in x for x in a.avisos)
    a = analizar(cargar_proyecto(d), date(2026, 1, 1))     # PV = 0
    assert a.evm.spi is None and any("SPI" in x for x in a.avisos)


def test_decimales_sin_deriva():
    d = base(imputaciones=[{"fecha": "2026-01-12", "rol": "Consultor", "tarea": "A", "horas": "0.1"}] * 30,
             costes=[])
    d["tarifas"]["Consultor"] = "0.1"
    a = analizar(cargar_proyecto(d), date(2026, 1, 15))
    assert a.por_partida["horas"]["real"] == D("0.30")       # con floats saldría 0.30000000000000004
    assert a.evm.ac == D("0.30")


def test_redondeo_half_up():
    d = base(costes=[{"proveedor": "P", "concepto": "c", "importe": "10.005", "fecha": "2026-01-14", "partida": "servicios"}])
    assert analizar(cargar_proyecto(d), HOY).por_partida["servicios"]["real"] == D("10.01")


def test_partidas_y_desviacion():
    a = analizar(cargar_proyecto(base()), date(2026, 1, 15))
    assert a.por_partida["horas"] == {"presupuesto": D("1000.00"), "real": D("400.00"), "desviacion": D("600.00")}
    assert a.por_partida["licencias"]["real"] == D("50.00")
    assert a.total["real"] == D("450.00") and a.total["desviacion"] == D("650.00")


def test_sobrecoste_da_aviso():
    d = base()
    d["proyecto"]["presupuesto"]["licencias"] = 10
    a = analizar(cargar_proyecto(d), date(2026, 1, 15))
    assert a.por_partida["licencias"]["desviacion"] == D("-40.00")
    assert any("licencias" in x and "por encima" in x for x in a.avisos)


def test_imputacion_a_tarea_inexistente_avisa_y_no_cuenta():
    d = base()
    d["imputaciones"].append({"fecha": "2026-01-13", "rol": "Consultor", "tarea": "ZZZ", "horas": 99})
    p = cargar_proyecto(d)
    assert any("ZZZ" in x for x in p.avisos)
    assert analizar(p, date(2026, 1, 15)).evm.ac == D("450.00")


def test_importes_no_numericos_no_rompen():
    d = base()
    d["costes"] += [{"proveedor": "P", "concepto": "c", "importe": "mucho", "fecha": "2026-01-14", "partida": "servicios"},
                    {"proveedor": "P", "concepto": "c", "importe": float("nan"), "fecha": "2026-01-14", "partida": "servicios"},
                    {"proveedor": "P", "concepto": "c", "importe": True, "fecha": "2026-01-14", "partida": "servicios"}]
    d["imputaciones"].append({"fecha": "2026-01-13", "rol": "Consultor", "tarea": "A", "horas": "x"})
    d["tarifas"]["Analista"] = "gratis"
    d["tareas"][0]["avance"] = "casi"
    d["proyecto"]["presupuesto"]["horas"] = "mil"
    p = cargar_proyecto(d)
    a = analizar(p, date(2026, 1, 15))
    assert len(p.avisos) >= 7
    assert a.por_partida["servicios"]["real"] == D("0.00")
    assert a.evm.ev == D("100.00")
    render_markdown(a)


def test_entradas_mal_formadas_no_rompen():
    for raw in (None, [], {"proyecto": "x"}, {"tareas": "no", "costes": [1, None], "eventos": [3], "riesgos": ["x"],
                                   "imputaciones": 5, "tarifas": []}):
        a = analizar(cargar_proyecto(raw), HOY)
        assert a.avisos
        render_markdown(a)
        eventos_ics(cargar_proyecto(raw), HOY)


def test_futuro_no_cuenta():
    d = base()
    d["imputaciones"].append({"fecha": "2026-02-01", "rol": "Consultor", "tarea": "A", "horas": 10})
    a = analizar(cargar_proyecto(d), date(2026, 1, 15))
    assert a.evm.ac == D("450.00") and any("posterior a hoy" in x for x in a.avisos)
    assert analizar(cargar_proyecto(d), date(2026, 2, 1)).evm.ac == D("1450.00")   # el mismo día cuenta


def test_retrasadas_estricto():
    p = cargar_proyecto(base())
    assert [t.id for t in analizar(p, date(2026, 1, 21)).tareas_retrasadas] == ["A"]
    assert analizar(p, date(2026, 1, 20)).tareas_retrasadas == []      # fin == hoy no es retraso
    d = base()
    d["tareas"][0]["avance"] = 100
    assert analizar(cargar_proyecto(d), date(2026, 1, 21)).tareas_retrasadas == []


def test_sin_control_y_accion_hereda_controles():
    d = base()
    d["tareas"][0]["controles"] = []
    d["tareas"][1]["controles"] = []
    p = cargar_proyecto(d)
    assert [t.id for t in analizar(p, HOY).tareas_sin_control] == ["A", "B"]
    d["tareas"][0]["accion"] = "ENE-01"
    d["tareas"][1]["accion"] = "NO-EXISTE"
    a = analizar(cargar_proyecto(d), HOY, assessment=yaml.safe_load(EVAL.read_text(encoding="utf-8")))
    assert [t.id for t in a.tareas_sin_control] == ["B"]
    assert any("NO-EXISTE" in x for x in a.avisos)


def test_proximos_eventos_30_dias():
    d = base(eventos=[{"id": "e1", "titulo": "ayer", "fecha": "2026-01-14"},
                      {"id": "e2", "titulo": "hoy", "fecha": "2026-01-15"},
                      {"id": "e3", "titulo": "limite", "fecha": "2026-02-14"},
                      {"id": "e4", "titulo": "fuera", "fecha": "2026-02-15"}])
    a = analizar(cargar_proyecto(d), date(2026, 1, 15))
    assert [e.id for e in a.proximos_eventos] == ["e2", "e3"]


def test_horas_por_rol_y_mes():
    d = base()
    d["imputaciones"] += [{"fecha": "2026-02-02", "rol": "Consultor", "tarea": "A", "horas": "1.5"},
                          {"fecha": "2026-02-20", "rol": "Consultor", "tarea": "A", "horas": 2}]
    a = analizar(cargar_proyecto(d), date(2026, 3, 1))
    assert a.horas_rol_mes["Consultor"] == {"2026-01": D("3"), "2026-02": D("3.5")}
    assert a.horas_rol_mes["Analista"] == {"2026-01": D("2")}


def test_suscripciones_del_registry_sin_recalcular():
    reg = {"technologies": [
        {"id": "T1", "nombre": "a", "suscripcion": {"proveedor": "X", "coste_anual": 1200.5, "moneda": "EUR"}},
        {"id": "T2", "nombre": "b", "suscripcion": {"proveedor": "Y", "coste_anual": 100, "moneda": "USD"}},
        {"id": "T3", "nombre": "c", "suscripcion": {"proveedor": "X", "coste_anual": "n/a"}}]}
    a = analizar(cargar_proyecto(base()), HOY, registry=reg)
    assert a.suscripciones["coste_anual_eur"] == D("1200.50")
    assert a.suscripciones["otras_monedas"] == {"USD": D("100.00")}
    assert any("USD" in x for x in a.avisos) and any("n/a" in x for x in a.avisos)
    assert analizar(cargar_proyecto(base()), HOY).suscripciones is None
    assert a.evm.ac == analizar(cargar_proyecto(base()), HOY).evm.ac      # no entra en AC


def test_ejemplo_carga_y_enlaza_con_la_evaluacion():
    p = cargar_proyecto(EJ)
    assert p.avisos == []
    ev = yaml.safe_load(EVAL.read_text(encoding="utf-8"))
    acciones = {x["id"]: x for x in ev["plan_accion"]}
    for t in p.tareas:
        if t.accion:
            assert t.accion in acciones
            assert set(t.controles) == set(acciones[t.accion]["controles"])
            for c in t.controles:
                assert c in ev["evaluaciones"]
    a = analizar(p, HOY, assessment=ev)
    # T29: el ejemplo tiene costes no laborales en T-03 y T-04 sin `presupuesto` explícito: solo esos avisos.
    assert [x.split(":")[0] for x in a.avisos] == ["T-03", "T-04"]
    assert all("costes no laborales" in x for x in a.avisos)
    assert [t.id for t in a.tareas_sin_control] == ["T-05"]
    assert [t.id for t in a.tareas_retrasadas] == ["T-02"]
    assert a.evm.cpi is not None and a.evm.spi is not None


def test_markdown_escapa_xss_y_pipes():
    d = base()
    d["tareas"][0]["titulo"] = "<script>alert(1)</script> | x"
    d["tareas"][0]["fin"] = "2026-01-12"          # retrasada, sale en la lista
    d["tareas"][1]["controles"] = []
    d["tareas"][1]["titulo"] = "<img src=x onerror=1>"
    d["proyecto"]["nombre"] = "<b>n</b>"
    d["riesgos"] = [{"id": "R", "descripcion": "a|b <i>", "estado": "x"}]
    d["eventos"] = [{"id": "e", "titulo": "<u>e</u>|", "fecha": "2026-01-16"}]
    md = render_markdown(analizar(cargar_proyecto(d), date(2026, 1, 15)))
    assert "<script" not in md and "<img" not in md and "<b>" not in md and "<i>" not in md and "<u>" not in md
    assert "&lt;script&gt;" in md and "\\|" in md


def test_markdown_ejemplo_tiene_secciones():
    md = render_markdown(analizar(cargar_proyecto(EJ), HOY))
    for s in ("Presupuesto por partida", "Valor ganado", "Tareas retrasadas", "Próximos eventos", "Horas por rol"):
        assert s in md


# ---------------------------------------------------------------- iCalendar
def ev_ics(**kw):
    e = {"id": "E1", "titulo": "t", "fecha": "2026-11-10"}
    e.update(kw)
    return cargar_proyecto(base(eventos=[e]))


def lineas(ics):
    assert ics.endswith("\r\n")
    assert "\n" not in ics.replace("\r\n", "")
    return ics.split("\r\n")[:-1]


def test_ics_estructura_y_crlf():
    ics = eventos_ics(ev_ics(), HOY)
    ls = lineas(ics)
    assert ls[0] == "BEGIN:VCALENDAR" and ls[-1] == "END:VCALENDAR" and "VERSION:2.0" in ls
    assert "DTSTAMP:20261103T000000Z" in ls
    assert "DTSTART;VALUE=DATE:20261110" in ls and "DTEND;VALUE=DATE:20261111" in ls
    assert "UID:P-E1@smc.pmo" in ls


def test_ics_fecha_fin_y_uid_estable():
    p = ev_ics(fecha_fin="2026-11-12")
    assert "DTEND;VALUE=DATE:20261113" in lineas(eventos_ics(p, HOY))
    assert eventos_ics(p, HOY) == eventos_ics(p, HOY)
    otro = eventos_ics(p, date(2027, 1, 1))
    uid = lambda s: [x for x in lineas(s) if x.startswith("UID:")]
    assert uid(otro) == uid(eventos_ics(p, HOY))                 # el UID no depende de hoy
    assert "DTSTAMP:20270101T000000Z" in lineas(otro)
    sin_id = cargar_proyecto(base(eventos=[{"titulo": "x", "fecha": "2026-11-10"}]))
    assert uid(eventos_ics(sin_id, HOY)) == uid(eventos_ics(sin_id, date(2030, 1, 1)))


def test_ics_escapado():
    p = ev_ics(titulo="a,b;c\\d", descripcion="l1\nl2\r\nl3\rl4", lugar="Sala 1, planta 2")
    ls = lineas(eventos_ics(p, HOY))
    assert "SUMMARY:a\\,b\\;c\\\\d" in ls
    assert "DESCRIPTION:l1\\nl2\\nl3\\nl4" in ls
    assert "LOCATION:Sala 1\\, planta 2" in ls


def test_ics_no_se_puede_inyectar_lineas():
    p = ev_ics(titulo="x\r\nEND:VEVENT\r\nBEGIN:VEVENT")
    ls = lineas(eventos_ics(p, HOY))
    assert ls.count("END:VEVENT") == 1 and ls.count("BEGIN:VEVENT") == 1


def test_ics_plegado_75_octetos_sin_partir_utf8():
    largo = "ñ€ " * 80 + "x" * 200
    ics = eventos_ics(ev_ics(descripcion=largo), HOY)
    ls = lineas(ics)
    assert any(x.startswith(" ") for x in ls)
    for x in ls:
        assert len(x.encode("utf-8")) <= 75
    ics.encode("utf-8").decode("utf-8")
    # desplegar y comparar con el original
    desplegado = ics.replace("\r\n ", "")
    assert "DESCRIPTION:" + largo.replace(",", "\\,") in desplegado


def test_ics_plegado_exacto_en_75():
    ics = eventos_ics(ev_ics(descripcion="a" * 200), HOY)
    ls = [x for x in lineas(ics) if x.startswith("DESCRIPTION") or x.startswith(" ")]
    assert len(ls[0].encode()) == 75 and len(ls[1].encode()) == 75     # 1 espacio + 74


def test_ics_exportar_escribe_crlf(tmp_path):
    ruta = exportar_ics(ev_ics(), tmp_path / "e.ics", HOY)
    b = ruta.read_bytes()
    assert b.count(b"\r\n") == b.count(b"\n") and b.endswith(b"\r\n")


def test_ejemplo_proximos_eventos():
    a = analizar(cargar_proyecto(EJ), HOY)
    assert [e.id for e in a.proximos_eventos] == ["EV-01", "EV-02"]
