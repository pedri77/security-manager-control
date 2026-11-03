"""T36: endurecimiento de v0.8 (hallazgos 2-9 de la revisión de las olas 15-16). Cada bloque lleva su contraprueba."""
import copy
import csv
import io
import re
import zipfile
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree

import yaml

from smc import compare, evidencias, report_html, soa
from smc.cli import main

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "assessments" / "examples"
HOY = date(2026, 11, 3)


def _l(p):
    return yaml.safe_load(Path(p).read_text(encoding="utf-8"))


def _energia(evid=None):
    a = _l(EX / "ejemplo-energia.yaml")
    if evid is not None:
        a["evaluaciones"]["NIS2-20.1"]["evidencias"] = [evid]
    return a


def _fila(d, cid="NIS2-20.1"):
    return next(f for f in d["aplicabilidad"] if f["id"] == cid)


def rc(capsys, *args):
    capsys.readouterr()
    code = main(list(args))
    out = capsys.readouterr()
    return code, out.out, out.err


# ------------------------------------------------------------------ hallazgo 2: soa no rompe con fechas raras

def test_h2_caduca_con_hora_no_da_typeerror_y_cuenta_como_caducada():
    d = soa.declaracion(_energia({"ref": "x", "fecha": "2026-01-01", "caduca": datetime(2026, 1, 1, 10, 0)}), HOY)
    e = [e for e in d["evidencias"] if e["evidencia"] == "x"][0]
    assert e["caduca"] == "2026-01-01" and e["estado"] == "caducada"
    soa.a_csv(d), soa.a_xlsx(d), soa.a_html(d)


def test_h2_vigencia_dias_enorme_da_aviso_no_overflow():
    d = soa.declaracion(_energia({"ref": "x", "fecha": "2026-01-01", "vigencia_dias": 10 ** 9}), HOY)
    assert any("vigencia_dias fuera de rango" in a for a in d["avisos"])
    assert [e for e in d["evidencias"] if e["evidencia"] == "x"][0]["estado"] == "sin_fecha"


def test_h2_contraprueba_vigencia_normal_calcula_la_caducidad():
    d = soa.declaracion(_energia({"ref": "x", "fecha": "2026-10-20", "vigencia_dias": 30}), HOY)
    e = [e for e in d["evidencias"] if e["evidencia"] == "x"][0]
    assert e["caduca"] == "2026-11-19" and e["estado"] == "caduca_pronto"
    assert not any("vigencia_dias" in a for a in d["avisos"])


def test_h2_cli_soa_con_datos_raros_rc0_o_rc2_sin_traceback(capsys, tmp_path):
    a = _energia({"ref": "x", "fecha": "2026-01-01", "caduca": datetime(2026, 1, 1, 10, 0)})
    f = tmp_path / "a.yaml"
    f.write_text(yaml.safe_dump(a, allow_unicode=True), encoding="utf-8")
    for fmt in ("csv", "xlsx", "html"):
        code, _, err = rc(capsys, "soa", str(f), "--formato", fmt, "-o", str(tmp_path / f"s.{fmt}"), "--hoy", "2026-11-03")
        assert code == 0 and "Traceback" not in err
    # contraprueba: un YAML que no es un mapa sigue dando rc=2
    f.write_text("- 1\n- 2\n", encoding="utf-8")
    code, _, err = rc(capsys, "soa", str(f), "--formato", "csv", "-o", str(tmp_path / "x.csv"))
    assert code == 2 and "Traceback" not in err


def test_h2_cli_captura_typeerror_y_overflow_de_datos(capsys, tmp_path, monkeypatch):
    f = tmp_path / "a.yaml"
    f.write_text(yaml.safe_dump(_energia(), allow_unicode=True), encoding="utf-8")
    for exc in (TypeError("raro"), OverflowError("grande")):
        monkeypatch.setattr(soa, "declaracion", lambda *a, _e=exc, **k: (_ for _ in ()).throw(_e))
        code, _, err = rc(capsys, "soa", str(f), "--formato", "csv", "-o", str(tmp_path / "x.csv"))
        assert code == 2 and "ERROR" in err and "Traceback" not in err


# ------------------------------------------------------------------ hallazgo 3: XLSX bien formado

def _xml_ok(xlsx: bytes):
    with zipfile.ZipFile(io.BytesIO(xlsx)) as z:
        for n in z.namelist():
            if n.endswith(".xml") or n.endswith(".rels"):
                ElementTree.fromstring(z.read(n))


def test_h3_xlsx_con_caracteres_no_validos_en_xml_es_bien_formado():
    malos = "a￾b￿c\x00d\x0be\ud800f\udfffg\x7fh"
    d = soa.declaracion(_energia({"ref": malos}), HOY)
    _xml_ok(soa.a_xlsx(d))
    with zipfile.ZipFile(io.BytesIO(soa.a_xlsx(d))) as z:
        hoja = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "abcdefg\x7fh" in hoja            # solo se quita lo que XML 1.0 no admite


def test_h3_contraprueba_texto_valido_se_conserva():
    d = soa.declaracion(_energia({"ref": "Ñandú 😀 日本 tab\tnl\n"}), HOY)
    x = soa.a_xlsx(d)
    _xml_ok(x)
    with zipfile.ZipFile(io.BytesIO(x)) as z:
        assert "Ñandú 😀 日本" in z.read("xl/worksheets/sheet1.xml").decode("utf-8")


# ------------------------------------------------------------------ hallazgo 4: una sola lógica de caducidad

CASOS = [{"ref": "a", "fecha": "2026-01-01", "vigencia_dias": -1},
         {"ref": "b", "fecha": "2026-01-01", "caduca": "20260101"},
         {"ref": "c", "fecha": "2026-01-01", "caduca": "2026-01-01"},
         {"ref": "d", "fecha": "2026-10-20", "vigencia_dias": 20},
         {"ref": "e", "fecha": "2026-10-20", "vigencia_dias": True},
         {"ref": "f", "caduca": datetime(2027, 1, 1, 23, 59)},
         {"ref": "g", "fecha": "2026-01-01", "caduca": "2026-W01-1"},
         "texto plano"]


def test_h4_soa_y_evidencias_coinciden_en_el_estado_de_cada_caso():
    for caso in CASOS:
        d = soa.declaracion(_energia(caso), HOY)
        ref = caso["ref"] if isinstance(caso, dict) else caso
        e = [e for e in d["evidencias"] if e["evidencia"] == ref][0]
        assert e["estado"] == evidencias.estado(caso, HOY), caso


def test_h4_casos_concretos_del_revisor():
    assert evidencias.estado(CASOS[0], HOY) == "sin_fecha"        # vigencia negativa: aviso, sin caducidad
    assert evidencias.estado(CASOS[1], HOY) == "sin_fecha"        # AAAAMMDD no es el formato (igual en 3.10 y 3.12)
    assert evidencias.estado(CASOS[6], HOY) == "sin_fecha"        # ni la semana ISO
    assert any("caduca no válida" in a for a in evidencias.normalizar(CASOS[1])["avisos"])
    d = soa.declaracion(_energia(CASOS[1]), HOY)
    assert any("caduca no válida" in a for a in d["avisos"])


def test_h4_contraprueba_formato_correcto_si_caduca():
    assert evidencias.estado({"ref": "x", "caduca": "2026-01-01"}, HOY) == "caducada"
    assert evidencias.estado({"ref": "x", "caduca": " 2027-01-01 "}, HOY) == "vigente"


# ------------------------------------------------------------------ hallazgo 5: compare

def _ayto():
    return _l(EX / "ejemplo-ayuntamiento.yaml")


def _brecha(a):
    return next(c for c, e in a["evaluaciones"].items() if e.get("estado") in ("parcial", "no_implementado"))


def test_h5_quitar_una_brecha_sale_en_dejan_de_evaluarse_no_en_sin_cambio():
    ay = _ayto()
    b = copy.deepcopy(ay)
    k = _brecha(ay)
    del b["evaluaciones"][k]
    c = compare.comparar(ay, b, HOY)
    assert [x.id for x in c.dejan_de_evaluarse] == [k]
    assert k not in [x.id for x in c.sin_cambio + c.mejoran + c.empeoran + c.cerrados + c.nuevas_brechas]
    assert "### Dejan de evaluarse (1)" in compare.render_markdown(c)
    assert "Dejan de evaluarse" in report_html.render_evolucion(c)


def test_h5_id_inexistente_no_es_nueva_brecha_y_avisa():
    ay = _ayto()
    b = copy.deepcopy(ay)
    b["evaluaciones"]["NOEXISTE-1"] = {"estado": "no_implementado"}
    c = compare.comparar(ay, b, HOY)
    assert c.nuevas_brechas == [] and c.sin_catalogo == ["NOEXISTE-1"]
    assert any("NOEXISTE-1" in a for a in c.avisos)


def test_h5_control_ens_no_aplicable_por_categoria_no_cuenta():
    ay = _ayto()
    assert ay["cliente"].get("categoria_ens")
    b = copy.deepcopy(ay)
    b["evaluaciones"]["ENS-op.cont.2"] = {"estado": "no_implementado"}
    c = compare.comparar(ay, b, HOY)
    assert "ENS-op.cont.2" not in [x.id for x in c.nuevas_brechas]
    assert "ENS-op.cont.2" not in c.p1_despues


def test_h5_cambio_de_categoria_ens_no_genera_brechas_nuevas_de_medidas_que_dejan_de_aplicar():
    ay = _ayto()
    b = copy.deepcopy(ay)
    b["cliente"]["categoria_ens"] = "BASICA"
    c = compare.comparar(ay, b, HOY)
    assert c.nuevas_brechas == [] and c.cerrados == []


def test_h5_contraprueba_brecha_real_nueva_sigue_siendo_nueva():
    ay = _ayto()
    b = copy.deepcopy(ay)
    libre = next(c for c in ("NIS2-21.2.a", "NIS2-21.2.b", "NIS2-21.2.c", "NIS2-21.2.d", "NIS2-21.2.e")
                 if c not in ay["evaluaciones"])
    b["evaluaciones"][libre] = {"estado": "no_implementado"}
    assert [x.id for x in compare.comparar(ay, b, HOY).nuevas_brechas] == [libre]


def test_h5_los_grupos_cubren_cada_control_evaluado_una_sola_vez():
    a, b = _l(EX / "historico" / "ejemplo-energia-2026-q1.yaml"), _l(EX / "ejemplo-energia.yaml")
    c = compare.comparar(a, b, HOY)
    todos = [x.id for g in (c.mejoran, c.empeoran, c.cerrados, c.nuevas_brechas, c.sin_cambio, c.dejan_de_evaluarse) for x in g]
    assert len(todos) == len(set(todos))
    assert set(todos) == set(a["evaluaciones"]) | set(b["evaluaciones"])


# ------------------------------------------------------------------ hallazgo 6: --anterior debe ser un mapa

def test_h6_anterior_que_no_es_un_mapa_da_rc2(capsys, tmp_path):
    for contenido in ("- 1\n- 2\n", "solo texto\n", ""):
        f = tmp_path / "ant.yaml"
        f.write_text(contenido, encoding="utf-8")
        code, _, err = rc(capsys, "report", str(EX / "ejemplo-energia.yaml"), "--anterior", str(f),
                          "-o", str(tmp_path / "i.html"), "--hoy", "2026-11-03")
        assert code == 2 and "mapa" in err and "Traceback" not in err
        assert not (tmp_path / "i.html").exists()


def test_h6_contraprueba_anterior_valido_rc0_con_seccion(capsys, tmp_path):
    code, _, _ = rc(capsys, "report", str(EX / "ejemplo-energia.yaml"), "--anterior",
                    str(EX / "historico" / "ejemplo-energia-2026-q1.yaml"), "-o", str(tmp_path / "i.html"),
                    "--hoy", "2026-11-03")
    assert code == 0 and "Evolución respecto" in (tmp_path / "i.html").read_text(encoding="utf-8")


# ------------------------------------------------------------------ hallazgo 7: CI (ver también test_version.py)

def test_h7_workflow_y_readme_coinciden_en_los_comandos():
    wf = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    for cmd in ("smc compare", "smc soa", "smc evidencias", "--anterior"):
        assert cmd in wf and cmd in (ROOT / "README.md").read_text(encoding="utf-8")


# ------------------------------------------------------------------ hallazgo 8: CSV

def _celda_evidencias(valor):
    a = _energia(valor)
    c = soa.a_csv(soa.declaracion(a, HOY))
    filas = list(csv.reader(io.StringIO(c.lstrip("﻿"))))
    return next(r for r in filas if r[1] == "NIS2-20.1")[6]


def test_h8_celdas_peligrosas_quedan_neutralizadas():
    for v in ("=1+1", " =1+1", "\n=1+1", "\t=1", "\r=1", "＝1+1", "  @SUM(1)", " -2+3", "+1", "　=1", "＋1", "－1", "＠x"):
        r = _celda_evidencias(v)
        assert r.startswith("'"), repr(v)


def test_h8_contraprueba_texto_normal_no_se_toca():
    for v in ("informe de pruebas", "a=b", "x - y", "1 + 1"):
        assert _celda_evidencias(v) == v


# ------------------------------------------------------------------ hallazgo 9: CHANGELOG sin jerga del plan

def test_h9_changelog_y_catalogo_sin_jerga_del_plan():
    ch = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## 0.8.0 (2026-11-03)\n\nOla 14-16" not in ch and re.search(r"^## 0\.8\.0.*\n\nOlas 15-16", ch, re.M)
    assert not re.search(r"\bT3\d\b", (ROOT / "frameworks" / "ai-act" / "obligaciones.yaml").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ hallazgo (h): caducidad en el informe HTML

def test_h_informe_html_muestra_la_evidencia_caducada_escapada():
    a = _energia()
    caducada = [{"ref": "<b>x</b>", "fecha": "2025-01-01", "caduca": "2025-06-01"}]
    for cid, e in a["evaluaciones"].items():
        if e.get("estado") == "implementado":
            e["evidencias"] = caducada
            break
    from smc import gap
    html = report_html.render_html(gap.analyse(a, HOY))
    assert "Evidencia caducada (" in html and "<b>x</b>" not in html
    assert "No afecta a la puntuación" in html


def test_h_contraprueba_sin_evidencia_caducada_no_hay_seccion():
    from smc import gap
    html = report_html.render_html(gap.analyse(_ayto(), HOY))
    assert "Evidencia caducada" not in html
