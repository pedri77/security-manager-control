import io
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from pathlib import Path

import yaml

from smc import soa

HOY = date(2026, 11, 3)
EJEMPLO = Path(__file__).resolve().parent.parent / "assessments" / "examples" / "ejemplo-energia.yaml"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _ejemplo():
    return yaml.safe_load(EJEMPLO.read_text(encoding="utf-8"))


def _ens_media():
    a = _ejemplo()
    a["cliente"].update(sector_publico=True, categoria_ens="MEDIA")
    return a


def test_ens_media_73_filas_no_aplicables_justificadas():
    d = soa.declaracion(_ens_media(), HOY)
    ens = [f for f in d["aplicabilidad"] if f["marco"] == "ENS"]
    assert len(ens) == 73
    no = [f for f in ens if f["aplica"] == "no"]
    assert no and all("MEDIA" in f["justificacion"] and "ALTA" in f["justificacion"] for f in no)
    assert all(f["justificacion"] == "" for f in ens if f["aplica"] == "sí")
    assert d["aviso"].startswith("Documento de trabajo generado por SMC")


def test_ejemplo_sin_ens_y_filas_basicas():
    d = soa.declaracion(_ejemplo(), HOY)
    assert not [f for f in d["aplicabilidad"] if f["marco"] == "ENS"]
    f = {x["id"]: x for x in d["aplicabilidad"]}
    assert f["NIS2-21.2.d"]["estado"] == "no_implementado" and f["NIS2-21.2.d"]["prioridad"] in ("P1", "P2", "P3")
    assert f["NIS2-20.1"]["estado"] == "implementado" and f["NIS2-20.1"]["prioridad"] == ""
    assert "Acta del consejo" in f["NIS2-20.1"]["evidencias"]
    assert f["NIS2-20.1"]["mapeo"].startswith("ENS-") or "ISO27001:" in f["NIS2-20.1"]["mapeo"]
    assert any(x["estado"] == "sin evaluar" for x in d["aplicabilidad"])


def test_no_aplica_explicito_usa_notas():
    a = _ejemplo()
    a["evaluaciones"]["NET-WIFI-01"] = {"estado": "no_aplica", "notas": "Sin WiFi en planta"}
    f = {x["id"]: x for x in soa.declaracion(a, HOY)["aplicabilidad"]}["NET-WIFI-01"]
    assert f["aplica"] == "no" and f["justificacion"] == "Sin WiFi en planta"


def test_evidencias_dict_y_texto():
    a = _ejemplo()
    a["evaluaciones"]["NIS2-20.1"]["evidencias"] = [
        "Texto plano",
        {"ref": "doc/a.pdf", "fecha": "2026-01-01", "vigencia_dias": 100},
        {"ref": "doc/b.pdf", "fecha": "2025-01-01", "caduca": "2026-01-01"},
        {"ref": "doc/c.pdf", "fecha": "2026-10-01", "caduca": "2026-11-20"},
    ]
    d = soa.declaracion(a, HOY)
    h = {e["evidencia"]: e for e in d["evidencias"] if e["control"] == "NIS2-20.1"}
    assert h["Texto plano"]["estado"] == "sin_fecha" and h["Texto plano"]["caduca"] == ""
    assert h["doc/a.pdf"]["caduca"] == "2026-04-11" and h["doc/a.pdf"]["estado"] == "caducada"
    assert h["doc/b.pdf"]["estado"] == "caducada"
    assert h["doc/c.pdf"]["estado"] == "caduca_pronto"


def test_contraprueba_formula_en_csv_xlsx_y_script_en_html():
    a = _ejemplo()
    a["evaluaciones"]["NIS2-20.1"]["evidencias"] = ['=HYPERLINK("http://x","y")', "<script>alert(1)</script>"]
    a["evaluaciones"]["NIS2-20.2"]["notas"] = "-1+1"
    d = soa.declaracion(a, HOY)
    csv_txt = soa.a_csv(d)
    assert csv_txt.startswith("﻿")
    assert "'=HYPERLINK" in csv_txt and ",=HYPERLINK" not in csv_txt
    # hoja de evidencias: la celda de evidencia sale prefijada en el XLSX
    z = zipfile.ZipFile(io.BytesIO(soa.a_xlsx(d)))
    s2 = z.read("xl/worksheets/sheet2.xml").decode()
    assert "'=HYPERLINK" in s2 and ">=HYPERLINK" not in s2
    assert "<script>" not in s2 and "&lt;script&gt;" in s2
    h = soa.a_html(d)
    assert "<script" not in h and "&lt;script&gt;" in h
    assert "@media print" in h


def test_seguro_prefijos():
    for c in ("=1", "+1", "-1", "@a", "\tx"):
        assert soa._seguro(c) == "'" + c
    assert soa._seguro("normal") == "normal" and soa._seguro("") == ""


def test_xlsx_estructura_y_dos_hojas():
    d = soa.declaracion(_ejemplo(), HOY)
    z = zipfile.ZipFile(io.BytesIO(soa.a_xlsx(d)))
    assert z.testzip() is None
    for n in ("[Content_Types].xml", "_rels/.rels", "xl/workbook.xml", "xl/_rels/workbook.xml.rels",
              "xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"):
        ET.fromstring(z.read(n))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    assert [s.get("name") for s in wb.find("m:sheets", NS)] == ["Aplicabilidad", "Evidencias"]
    filas = ET.fromstring(z.read("xl/worksheets/sheet1.xml")).findall(".//m:row", NS)
    assert len(filas) == len(d["aplicabilidad"]) + 1


def test_xlsx_nombres_de_hoja_validos_y_caracteres_xml():
    b = soa.a_xlsx({"a/b:c*[x]?" + "z" * 40: [["<&>\x01", "ñ"]], "a/b:c*[x]?" + "z" * 40 + "2": [["x"]]})
    z = zipfile.ZipFile(io.BytesIO(b))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    nombres = [s.get("name") for s in wb.find("m:sheets", NS)]
    assert all(len(n) <= 31 and not set(n) & set("[]:*?/\\") for n in nombres)
    assert len({n.lower() for n in nombres}) == 2
    t = ET.fromstring(z.read("xl/worksheets/sheet1.xml")).findall(".//m:t", NS)
    assert t[0].text == "<&>" and t[1].text == "ñ"


def test_csv_parsea_de_vuelta():
    import csv
    d = soa.declaracion(_ens_media(), HOY)
    filas = list(csv.reader(io.StringIO(soa.a_csv(d).lstrip("﻿"))))
    assert len(filas) == len(d["aplicabilidad"]) + 1 and len(filas[0]) == 10
