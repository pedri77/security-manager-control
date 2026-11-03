"""T24: pentesting y purple team (hoy inyectado, datos ficticios)."""
from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
import yaml

from smc import offensive as o
from smc import tech

ROOT = Path(__file__).resolve().parent.parent
EJ_PT = ROOT / "offensive" / "examples" / "ejemplo-pentest.yaml"
EJ_PP = ROOT / "offensive" / "examples" / "ejemplo-purple.yaml"
HOY = date(2026, 11, 3)


def pt():
    return yaml.safe_load(EJ_PT.read_text(encoding="utf-8"))


def pp():
    return yaml.safe_load(EJ_PP.read_text(encoding="utf-8"))


def test_plantillas_y_ejemplos_cargan_sin_errores():
    for f in ("pentest.template.yaml", "examples/ejemplo-pentest.yaml"):
        assert o.validar_pentest(ROOT / "offensive" / f) == []
    for f in ("purple.template.yaml", "examples/ejemplo-purple.yaml"):
        assert o.validar_purple(ROOT / "offensive" / f) == []


def test_sla_se_toma_de_la_politica_y_no_se_duplica():
    pol = yaml.safe_load(tech.POLICY_FILE.read_text(encoding="utf-8"))["sla_remediacion_dias"]
    assert o.sla_politica() == pol
    fuente = (ROOT / "smc" / "offensive.py").read_text(encoding="utf-8")
    assert "severidad_efectiva" in fuente and "POLICY_FILE" in fuente
    assert "7," not in fuente.split("sla_politica")[0]  # sin tabla de SLA literal


def test_critico_abierto_mas_alla_del_sla_esta_fuera_de_sla():
    e = o.estado_hallazgos(EJ_PT, HOY)
    ids = [f.hallazgo.id for f in e.fuera_sla]
    assert ids[0] == "H-001"                        # crítica, 49 días > 7
    f = e.fuera_sla[0]
    assert (f.severidad_efectiva, f.dias, f.sla_dias) == ("critica", 49, 7)


def test_alta_dentro_de_sla_no_aparece():
    e = o.estado_hallazgos(EJ_PT, HOY)
    assert [f.hallazgo.id for f in e.fuera_sla] == ["H-001"]


def test_sla_estricto_y_dia_limite():
    d = pt()
    d["hallazgos"] = [{"id": "X", "titulo": "t", "severidad": "critica", "estado": "abierto", "fecha_deteccion": "2026-10-27"}]
    assert o.estado_hallazgos(d, HOY).fuera_sla == []                       # 7 días exactos: dentro
    assert len(o.estado_hallazgos(d, date(2026, 11, 4)).fuera_sla) == 1     # 8 días: fuera


def test_severidad_con_tildes_desconocida_y_kev():
    d = pt()
    base = {"titulo": "t", "estado": "abierto", "fecha_deteccion": "2026-10-01"}
    d["hallazgos"] = [{**base, "id": "A", "severidad": " CRÍTICA "}, {**base, "id": "B", "severidad": "media", "kev": True}]
    e = o.estado_hallazgos(d, HOY)
    assert {f.hallazgo.id: f.severidad_efectiva for f in e.fuera_sla} == {"A": "critica", "B": "critica"}
    assert any("KEV" in a for a in e.avisos)
    d["hallazgos"] = [{**base, "id": "C", "severidad": "grave"}]
    with pytest.raises(o.OffensiveError):                                   # severidad fuera de política en hallazgo = error
        o.estado_hallazgos(d, HOY)


def test_pendientes_de_retest_y_aceptados_sin_revision():
    e = o.estado_hallazgos(EJ_PT, HOY)
    assert [h.id for h in e.pendientes_retest] == ["H-005"]                 # H-002 ya tiene retest
    assert [h.id for h in e.aceptados_sin_revision] == ["H-004"]
    d = pt()
    for h in d["hallazgos"]:
        if h["id"] == "H-004":
            h["fecha_revision"] = "2027-04-01"
        if h["id"] == "H-005":
            h["fecha_retest"] = "2026-10-30"
    e = o.estado_hallazgos(d, HOY)
    assert e.pendientes_retest == [] and e.aceptados_sin_revision == []


def test_abiertos_y_por_severidad():
    e = o.estado_hallazgos(EJ_PT, HOY)
    assert sorted(h.id for h in e.abiertos) == ["H-001", "H-003"]
    assert e.por_severidad == {"critica": 1, "alta": 1, "media": 0, "baja": 0}
    assert e.total == 5


def test_hoy_distinto_cambia_el_resultado():
    assert o.estado_hallazgos(EJ_PT, date(2026, 9, 20)).fuera_sla == []     # 5 días: dentro
    ids = [f.hallazgo.id for f in o.estado_hallazgos(EJ_PT, date(2026, 12, 20)).fuera_sla]
    assert "H-003" in ids                                                   # 65 días > 30


def test_datos_mal_formados_dan_avisos_no_excepciones():
    d = pt()
    h = d["hallazgos"][0]
    h.update(fecha_deteccion="ayer", cvss=11, cwe="89", control="NOPE-1")
    e = o.estado_hallazgos(d, HOY)
    texto = "\n".join(e.avisos)
    for pista in ("fecha_deteccion", "CVSS", "CWE", "NOPE-1"):
        assert pista in texto
    assert "H-001" not in [f.hallazgo.id for f in e.fuera_sla]              # sin fecha válida no se evalúa


def test_errores_de_pentest():
    d = pt()
    d["hallazgos"][0]["estado"] = "cerrado"
    d["hallazgos"][1]["campania"] = "PT-9"
    d["campanias"][0]["tipo"] = "físico"
    d["hallazgos"][2]["id"] = "H-001"
    err = "\n".join(o.validar_pentest(d))
    for pista in ("cerrado", "PT-9", "físico", "repetido"):
        assert pista in err
    with pytest.raises(o.OffensiveError):
        o.cargar_pentest(d)


def test_purple_cobertura_por_tactica_y_listas():
    r = o.purple(EJ_PP, HOY)
    c = r.cobertura_por_tactica
    assert c["credential-access"]["cobertura_pct"] == 50.0                  # T1110.003 detectado + T1003.001 no
    assert c["credential-access"]["tecnicas"] == 2 and c["credential-access"]["tiempo_medio_min"] == 12.0
    assert c["initial-access"]["cobertura_pct"] == 75.0                     # T1566.001 parcial + T1190 detectado
    assert [e.tecnica for e in r.no_detectadas] == ["T1003.001", "T1566.001"]
    assert sorted(e.id for e in r.mejoras_abiertas) == ["PP-002", "PP-003"]  # PP-001 hecha
    assert [e.id for e in r.ejercicios_caducados] == ["PP-004"]


def test_ejercicio_de_mas_de_12_meses_es_estricto():
    d = pp()
    d["ejercicios"] = [{**d["ejercicios"][3], "fecha": "2025-11-03"}]
    assert o.purple(d, HOY).ejercicios_caducados == []                      # 365 días exactos
    assert len(o.purple(d, date(2026, 11, 4)).ejercicios_caducados) == 1


def test_ultimo_ejercicio_de_una_tecnica_manda():
    d = pp()
    d["ejercicios"].append({"id": "PP-005", "fecha": "2026-10-20", "tecnica": "T1003.001", "caso_uso": "UC-004",
                            "resultado": "detectado", "tiempo_deteccion_min": 20})
    r = o.purple(d, HOY)
    assert r.cobertura_por_tactica["credential-access"]["cobertura_pct"] == 100.0
    assert "T1003.001" not in [e.tecnica for e in r.no_detectadas]


def test_caso_de_uso_inexistente_en_purple_da_error():
    d = pp()
    d["ejercicios"][0]["caso_uso"] = "UC-999"
    assert any("UC-999" in e for e in o.validar_purple(d))
    with pytest.raises(o.OffensiveError, match="UC-999"):
        o.purple(d, HOY)


def test_caso_de_uso_retirado_cuenta_como_inexistente(tmp_path):
    cat = yaml.safe_load((ROOT / "soc" / "use-cases" / "catalog.yaml").read_text(encoding="utf-8"))
    cat["use_cases"][0]["estado"] = "retirado"
    f = tmp_path / "cat.yaml"
    f.write_text(yaml.safe_dump(cat), encoding="utf-8")
    assert any("UC-001" in e for e in o.validar_purple(EJ_PP, uc_path=f))


@pytest.mark.parametrize("tec", ["T123", "t1110", "T1110.3", "X1110", "T1110.0031", "", "T1110 "])
def test_ids_attack_mal_formados_dan_error(tec):
    d = pp()
    d["ejercicios"][0]["tecnica"] = tec
    if tec == "T1110 ":                       # el espacio final se recorta: es válido
        assert o.validar_purple(d) == []
    else:
        assert any("ATT&CK" in e for e in o.validar_purple(d))


@pytest.mark.parametrize("tec", ["T1110", "T1110.003", "T1692.001", "T1692.002"])
def test_ids_attack_validos_incluida_la_renumeracion_ics(tec):
    assert o.RE_ATTACK.match(tec)


def test_resultado_y_estado_de_mejora_invalidos():
    d = pp()
    d["ejercicios"][0]["resultado"] = "ok"
    d["ejercicios"][1]["mejora"]["estado"] = "cerrada"
    err = "\n".join(o.validar_purple(d))
    assert "ok" in err and "cerrada" in err


def test_avisos_purple():
    d = pp()
    d["ejercicios"][0].update(fecha="nunca", tecnica="T1059.001", tiempo_deteccion_min=-3)
    d["ejercicios"][2]["tiempo_deteccion_min"] = 5
    r = o.purple(d, HOY)
    texto = "\n".join(r.avisos)
    assert "fecha" in texto and "no figura entre las del caso de uso" in texto and "no_detectado con tiempo" in texto and "-3" in texto


def test_render_markdown_escapa_y_muestra_secciones():
    d = pt()
    d["hallazgos"][0]["titulo"] = "XSS <script>alert(1)</script> | extra\nlinea"
    md = o.render_markdown(o.estado_hallazgos(d, HOY), o.purple(EJ_PP, HOY))
    assert "<script>" not in md and "&lt;script&gt;" in md and "\\|" in md
    assert "Fuera de SLA" in md and "Pendientes de retest" in md and "Aceptados sin fecha de revisión" in md
    assert "credential-access" in md and "Mejoras abiertas" in md and "más de 12 meses" in md


def test_render_vacio_y_solo_una_parte():
    assert "Sin datos" in o.render_markdown()
    assert "Ejercicios purple" not in o.render_markdown(o.estado_hallazgos(EJ_PT, HOY))
    assert "Hallazgos de pentest" not in o.render_markdown(None, o.purple(EJ_PP, HOY))


def test_sin_doble_guion_como_puntuacion_en_ficheros_nuevos():
    for f in [*(ROOT / "offensive").rglob("*.yaml"), ROOT / "smc" / "offensive.py"]:
        t = f.read_text(encoding="utf-8")
        assert " -- " not in t, f
        assert "\u2014" not in t.replace("\"—\"", "").replace("'—'", "").replace("— |", "").replace("| —", ""), f
