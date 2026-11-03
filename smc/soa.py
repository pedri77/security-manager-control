"""Salida para auditor: declaración de aplicabilidad y registro de evidencias (CSV, XLSX, HTML).

Parte de `smc.gap.analyse` (no reimplementa el análisis). Solo stdlib y PyYAML (vía gap).
Las evidencias son texto o un dict {ref, fecha, caduca | vigencia_dias, sha256}; se leen aquí sin
depender de `smc/evidencias.py`.
"""
from __future__ import annotations

import csv
import html as _html
import io
import re
import zipfile
from datetime import date, timedelta
from xml.sax.saxutils import escape as _xml_escape

from . import gap as _gap
from . import mapping as _mapping

AVISO = "Documento de trabajo generado por SMC; la declaración formal la firma el responsable de seguridad"

COLUMNAS_APLICABILIDAD = ("marco", "id", "titulo", "aplica", "justificacion", "estado", "evidencias",
                          "prioridad", "refuerzos_ens", "mapeo")
CABECERA_APLICABILIDAD = ("Marco", "Control", "Título", "Aplica", "Justificación de no aplicación", "Estado",
                          "Evidencias", "Prioridad", "Refuerzos ENS", "Mapeo a otros marcos")
COLUMNAS_EVIDENCIAS = ("control", "evidencia", "fecha", "caduca", "estado")
CABECERA_EVIDENCIAS = ("Control", "Evidencia", "Fecha", "Caduca", "Estado de la evidencia")

_ISO_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _fecha(v) -> date | None:
    if isinstance(v, date):
        return v
    if isinstance(v, str) and _ISO_FECHA.match(v.strip()):
        try:
            return date.fromisoformat(v.strip())
        except ValueError:
            return None
    return None


def _evidencia(e, hoy: date) -> dict:
    """Normaliza una evidencia (texto o dict) a {ref, fecha, caduca, estado}."""
    if isinstance(e, dict):
        ref = str(e.get("ref", "") if e.get("ref") is not None else "")
        f = _fecha(e.get("fecha"))
        c = _fecha(e.get("caduca"))
        vig = e.get("vigencia_dias")
        if c is None and f is not None and isinstance(vig, int) and not isinstance(vig, bool):
            c = f + timedelta(days=vig)
    else:
        ref, f, c = str(e if e is not None else ""), None, None
    if c is None:
        estado = "sin_fecha"
    elif c < hoy:
        estado = "caducada"
    elif (c - hoy).days <= 30:
        estado = "caduca_pronto"
    else:
        estado = "vigente"
    return {"ref": ref, "fecha": f.isoformat() if f else "", "caduca": c.isoformat() if c else "", "estado": estado}


def _evidencias_de(ev) -> list:
    lst = ev.get("evidencias") if isinstance(ev, dict) else None
    if lst is None or lst == "":
        return []
    return lst if isinstance(lst, list) else [lst]


def _mapeo(control) -> str:
    partes = sorted(_mapping.equivalentes(control.id))
    iso: set[str] = set()
    for nis2, ens, i in _mapping.cargar():
        if control.id == nis2 or control.id in ens or any(eq == nis2 for eq in partes):
            iso |= i
    partes += [f"ISO27001:{x}" for x in sorted(iso)]
    return "; ".join(partes)


def _texto_ev(e: dict) -> str:
    extra = []
    if e["fecha"]:
        extra.append(e["fecha"])
    if e["caduca"]:
        extra.append(f"caduca {e['caduca']}")
    return e["ref"] + (f" ({', '.join(extra)})" if extra else "")


def declaracion(assessment: dict, hoy: date | None = None) -> dict:
    """Devuelve {'aplicabilidad': [filas], 'evidencias': [filas], 'avisos': [str], 'aviso': AVISO, ...}.

    Una fila por control de cada marco en alcance. Los dicts usan las claves de COLUMNAS_*.
    """
    hoy = hoy or date.today()
    an = _gap.analyse(assessment, hoy)
    evals = assessment.get("evaluaciones") if isinstance(assessment, dict) else None
    evals = evals if isinstance(evals, dict) else {}
    from .catalog import load_all
    catalogos = load_all()
    filas, hoja = [], []
    for r in an.results:
        brecha = {b.control.id: b for b in r.brechas}
        no_aplica_cat = {c.id for c in r.no_aplican}
        for c in catalogos[r.framework]:
            ev = evals.get(c.id)
            ev = ev if isinstance(ev, dict) else None
            estado = ev.get("estado") if ev else None
            refuerzos = ""
            prioridad = ""
            if c.id in no_aplica_cat:
                aplica, estado_txt = "no", "no aplica"
                just = (f"No aplica a la categoría ENS {an.categoria_ens}: la medida exige como mínima "
                        f"{c.extra.get('categoria_minima', 'BASICA')}")
            elif estado == "no_aplica":
                aplica, estado_txt = "no", "no aplica"
                just = (ev.get("notas") or "") or "Sin justificación en la evaluación (completar antes de firmar)"
            else:
                aplica = "sí"
                just = ""
                estado_txt = estado if estado in _gap.SCORES else "sin evaluar"
                if c.id in brecha:
                    prioridad = brecha[c.id].nivel
                    refuerzos = ", ".join(brecha[c.id].refuerzos)
                elif r.framework == "ENS":
                    from . import ens as _ens
                    refuerzos = ", ".join(_ens.refuerzos(c, an.categoria_ens))
                if estado is None:
                    for d in r.sin_evaluar_detalle:
                        if d.control.id == c.id:
                            prioridad = d.nivel
                            refuerzos = ", ".join(d.refuerzos)
            evs = [_evidencia(e, hoy) for e in _evidencias_de(ev)] if aplica == "sí" else []
            for e in evs:
                hoja.append({"control": c.id, "evidencia": e["ref"], "fecha": e["fecha"],
                             "caduca": e["caduca"], "estado": e["estado"]})
            filas.append({"marco": r.framework, "id": c.id, "titulo": c.titulo, "aplica": aplica,
                          "justificacion": just, "estado": estado_txt,
                          "evidencias": "; ".join(_texto_ev(e) for e in evs), "prioridad": prioridad,
                          "refuerzos_ens": refuerzos, "mapeo": _mapeo(c)})
    return {"aplicabilidad": filas, "evidencias": hoja, "avisos": list(an.warnings), "aviso": AVISO,
            "cliente": an.cliente, "fecha": hoy.isoformat()}


# --- Exportadores -------------------------------------------------------------------------------

def _seguro(v) -> str:
    """Neutraliza inyección de fórmulas: celdas que empiezan por = + - @ o tabulador (o CR) se prefijan con '."""
    s = "" if v is None else str(v)
    return "'" + s if s and s[0] in "=+-@\t\r" else s


def _filas_de(filas) -> list[dict]:
    return filas["aplicabilidad"] if isinstance(filas, dict) else list(filas)


def a_csv(filas) -> str:
    """CSV UTF-8 con BOM (Excel) de la hoja de aplicabilidad. Acepta la salida de `declaracion` o su lista de filas."""
    filas = _filas_de(filas)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow([_seguro(h) for h in CABECERA_APLICABILIDAD])
    for f in filas:
        w.writerow([_seguro(f.get(k, "")) for k in COLUMNAS_APLICABILIDAD])
    return "﻿" + buf.getvalue()


_NOMBRE_HOJA_MAL = re.compile(r"[\[\]:*?/\\]")
_CONTROL_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _nombre_hoja(n: str, usados: set) -> str:
    n = _NOMBRE_HOJA_MAL.sub("_", str(n)).strip("'") or "Hoja"
    n = n[:31]
    base, i = n, 2
    while n.lower() in usados:
        n = f"{base[:28]}_{i}"
        i += 1
    usados.add(n.lower())
    return n


def _col(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _hoja_xml(filas: list[list[str]]) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
    for n, fila in enumerate(filas, 1):
        out.append(f'<row r="{n}">')
        for j, v in enumerate(fila):
            t = _xml_escape(_CONTROL_XML.sub("", _seguro(v)))
            out.append(f'<c r="{_col(j)}{n}" t="inlineStr"><is><t xml:space="preserve">{t}</t></is></c>')
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def a_xlsx(hojas) -> bytes:
    """XLSX mínimo con `zipfile`. `hojas`: salida de `declaracion` (hojas «Aplicabilidad» y «Evidencias») o un
    dict {nombre_hoja: [fila(lista de celdas), ...]}."""
    if isinstance(hojas, dict) and "aplicabilidad" in hojas:
        hojas = {
            "Aplicabilidad": [list(CABECERA_APLICABILIDAD)] + [[f.get(k, "") for k in COLUMNAS_APLICABILIDAD]
                                                               for f in hojas["aplicabilidad"]],
            "Evidencias": [list(CABECERA_EVIDENCIAS)] + [[f.get(k, "") for k in COLUMNAS_EVIDENCIAS]
                                                         for f in hojas["evidencias"]],
        }
    usados: set = set()
    nombres = [_nombre_hoja(n, usados) for n in hojas]
    contenidos = [list(v) for v in hojas.values()]
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                    for i in range(1, len(nombres) + 1))
          + "</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
          + "".join(f'<sheet name="{_xml_escape(n, {chr(34): "&quot;"})}" sheetId="{i}" r:id="rId{i}"/>'
                    for i, n in enumerate(nombres, 1))
          + "</sheets></workbook>")
    wbrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
              + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                        for i in range(1, len(nombres) + 1))
              + "</Relationships>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wbrels)
        for i, filas in enumerate(contenidos, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _hoja_xml(filas))
    return buf.getvalue()


_CSS = ("body{font-family:Arial,Helvetica,sans-serif;font-size:12px;margin:1.5em}h1{font-size:18px}"
        ".aviso{border:1px solid #888;padding:.5em;margin:1em 0}table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #999;padding:3px 5px;text-align:left;vertical-align:top}th{background:#eee}"
        "@media print{body{margin:0}thead{display:table-header-group}tr{page-break-inside:avoid}"
        "@page{size:A4 landscape;margin:12mm}}")


def a_html(filas) -> str:
    """HTML imprimible (Ctrl+P a PDF): sin JS, sin CDN, todo escapado."""
    cliente = ""
    if isinstance(filas, dict):
        cliente = str((filas.get("cliente") or {}).get("nombre", "")) if isinstance(filas.get("cliente"), dict) else ""
    filas = _filas_de(filas)
    e = lambda v: _html.escape("" if v is None else str(v), quote=True)  # noqa: E731
    out = ["<!DOCTYPE html>", '<html lang="es"><head><meta charset="utf-8">',
           "<title>Declaración de aplicabilidad</title>", f"<style>{_CSS}</style></head><body>",
           f"<h1>Declaración de aplicabilidad{(' — ' + e(cliente)) if cliente else ''}</h1>",
           f'<p class="aviso">{e(AVISO)}.</p>', "<table><thead><tr>"
           + "".join(f"<th>{e(h)}</th>" for h in CABECERA_APLICABILIDAD) + "</tr></thead><tbody>"]
    for f in filas:
        out.append("<tr>" + "".join(f"<td>{e(f.get(k, ''))}</td>" for k in COLUMNAS_APLICABILIDAD) + "</tr>")
    out.append("</tbody></table></body></html>")
    return "\n".join(out) + "\n"
