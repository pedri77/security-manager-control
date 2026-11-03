"""Informe HTML autocontenido (CSS en línea, sin JS, sin recursos externos).

API:
- `render_html(analisis) -> str`: documento completo.
- `render_body(analisis, nivel=2) -> str`: solo el contenido (secciones), reutilizable por el dashboard.
- `CSS`: hoja de estilos en línea que necesita el cuerpo.
- `run_html(path, hoy=None) -> str`: carga una evaluación y devuelve el documento.
Todo texto procedente de la evaluación o de los catálogos pasa por `html.escape`.
"""
from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path

from .gap import Analisis, analyse, _load
from .plan import Accion

CSS = """
:root{--ink:#1d2433;--mut:#5b6577;--line:#d9dee7;--bg:#f5f7fa;--ok:#2e7d32;--mid:#f9a825;--bad:#c62828}
*{box-sizing:border-box}
body{font:15px/1.5 system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg);margin:0}
.smc{max-width:1000px;margin:0 auto;padding:24px;background:#fff}
.smc h1{font-size:26px;margin:0 0 4px}.smc h2{font-size:20px;margin:32px 0 8px;border-bottom:2px solid var(--line);padding-bottom:4px}
.smc h3{font-size:16px;margin:20px 0 6px}
.smc table{border-collapse:collapse;width:100%;margin:8px 0;font-size:13.5px}
.smc th,.smc td{border:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}
.smc th{background:var(--bg)}
.meta{color:var(--mut);margin:0 0 12px}
.bar{background:#e8ebf0;border-radius:4px;height:14px;min-width:120px;overflow:hidden}
.bar>span{display:block;height:100%}
.ok{background:var(--ok)}.mid{background:var(--mid)}.bad{background:var(--bad)}
.aviso{border-left:4px solid var(--mid);background:#fff8e1;padding:8px 12px;margin:10px 0}
.alerta{border-left:4px solid var(--bad);background:#fdecea;padding:8px 12px;margin:10px 0}
.nota{border-left:4px solid var(--line);background:var(--bg);padding:8px 12px;margin:10px 0;color:var(--mut)}
.tag{display:inline-block;border-radius:3px;padding:0 6px;font-weight:600;color:#fff;font-size:12px}
.P1{background:var(--bad)}.P2{background:#ef6c00}.P3{background:var(--mut)}
.venc{color:var(--bad);font-weight:600}
ul.cols{columns:2;column-gap:24px;padding-left:18px;margin:6px 0}
.smc li{break-inside:avoid}
@media print{body{background:#fff;font-size:11pt}.smc{max-width:none;padding:0}
.smc h2{break-after:avoid}.smc table,.smc tr{break-inside:avoid}
.bar,.tag,.bar>span{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def _e(x) -> str:
    return escape("" if x is None else str(x), quote=True)


def _color(p: float) -> str:
    return "ok" if p >= 80 else "mid" if p >= 50 else "bad"


def _barra(p: float) -> str:
    w = max(0.0, min(100.0, float(p)))
    return f'<div class="bar"><span class="{_color(w)}" style="width:{w:.1f}%"></span></div>'


def _tag(n: str) -> str:
    n = n if n in ("P1", "P2", "P3") else "P3"
    return f'<span class="tag {n}">{n}</span>'


def _tabla(cab: list[str], filas: list[list[str]]) -> str:
    """Las celdas ya vienen escapadas/construidas por el llamador."""
    h = "".join(f"<th>{_e(c)}</th>" for c in cab)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in f) + "</tr>" for f in filas)
    return f"<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


def _m(c) -> str:
    return ' <span class="venc">(verificar)</span>' if c.extra.get("verificar") else ""


def _fecha(d: date | None) -> str:
    return d.isoformat() if d else "—"


def _resumen(an: Analisis, h: int) -> str:
    out = [f"<h{h}>Resumen ejecutivo</h{h}>"]
    filas = [[_e(r.framework), f"{_e(r.puntuacion)} %", _barra(r.puntuacion),
              _e(r.aplicables), _e(len(r.brechas)), _e(len(r.sin_evaluar))] for r in an.results]
    out.append(_tabla(["Marco", "Cumplimiento", "", "Aplicables", "Brechas evaluadas", "Sin evaluar"], filas))
    if an.ens_verificar:
        out.append(f'<p class="aviso"><strong>Aviso ENS:</strong> {_e(len(an.ens_verificar))} medidas ENS tienen '
                   "aplicabilidad pendiente de contrastar con el Anexo II del RD 311/2022 (<code>verificar</code>): "
                   "«no aplica» y los refuerzos por categoría no son definitivos. Se marcan con (verificar).</p>")
    sin_eval = sum(len(r.sin_evaluar) for r in an.results)
    if sin_eval:
        out.append(f'<p class="nota">El cumplimiento incluye {sin_eval} controles sin evaluar, que puntúan como '
                   "no cumplidos. En una evaluación incompleta es lo esperado: se muestran aparte de las brechas "
                   "evaluadas y no entran en el top ni en el aviso de brechas P1.</p>")
    if an.p1_sin_accion:
        out.append('<p class="alerta"><strong>' + _e(len(an.p1_sin_accion)) + " brecha(s) P1 sin acción:</strong> "
                   + ", ".join(_e(i) for i in an.p1_sin_accion) + "</p>")
    p1 = sorted((b for r in an.results for b in r.brechas if b.nivel == "P1"),
                key=lambda b: (-b.puntuacion, b.control.id))[:10]
    out.append(f"<h{h + 1}>Top 10 brechas P1 (evaluadas)</h{h + 1}>")
    if p1:
        out.append(_tabla(["Control", "Título", "Estado", "Notas"],
                          [[_e(b.control.id) + _m(b.control), _e(b.control.titulo), _e(b.estado), _e(b.notas)] for b in p1]))
    else:
        out.append("<p>Ninguna brecha P1 evaluada.</p>")
    out.append(f"<h{h + 1}>Acciones vencidas a {_e(an.hoy.isoformat())}</h{h + 1}>")
    if an.vencidas:
        out.append(_tabla(["ID", "Acción", "Responsable", "Fecha objetivo"],
                          [[_e(a.id), _e(a.accion), _e(a.responsable), _e(_fecha(a.fecha_objetivo))]
                           for a in an.vencidas]))
    else:
        out.append("<p>Ninguna acción vencida.</p>")
    return "\n".join(out)


def _marco(an: Analisis, r, h: int) -> str:
    out = [f"<h{h}>{_e(r.framework)} · {_e(r.puntuacion)} %</h{h}>", _barra(r.puntuacion)]
    out.append(f"<h{h + 1}>Brechas evaluadas ({len(r.brechas)})</h{h + 1}>")
    if r.brechas:
        out.append(_tabla(["P", "Control", "Título", "Estado", "Refuerzos ENS", "Notas"],
                          [[_tag(b.nivel), _e(b.control.id) + _m(b.control), _e(b.control.titulo), _e(b.estado),
                            _e(", ".join(b.refuerzos) or "—"), _e(b.notas)] for b in r.brechas]))
    else:
        out.append("<p>Sin brechas evaluadas.</p>")
    if r.sin_evidencia:
        out.append(f"<h{h + 1}>Implementados sin evidencia ({len(r.sin_evidencia)})</h{h + 1}><ul class=\"cols\">"
                   + "".join(f"<li>{_e(c.id)} · {_e(c.titulo)}</li>" for c in r.sin_evidencia) + "</ul>")
    if r.sin_evaluar_detalle:
        out.append(f"<h{h + 1}>Sin evaluar ({len(r.sin_evaluar_detalle)})</h{h + 1}>")
        out.append('<p class="nota">Controles aplicables sin evaluación. No son brechas confirmadas.</p>')
        filas = []
        for d in r.sin_evaluar_detalle:
            her = ", ".join(f"{i} ({e})" for i, e in d.heredado_de)
            filas.append([_tag(d.nivel), _e(d.control.id) + _m(d.control), _e(d.control.titulo),
                          _e(", ".join(d.refuerzos) or "—"), _e(her + " (sugerencia, no puntúa)" if her else "—")])
        out.append(_tabla(["P", "Control", "Título", "Refuerzos ENS", "Heredado de"], filas))
    if r.no_aplican:
        out.append(f"<h{h + 1}>Medidas que no aplican a la categoría {_e(an.categoria_ens)} "
                   f"({len(r.no_aplican)})</h{h + 1}>")
        agrup: dict[str, list] = {}
        for c in r.no_aplican:
            agrup.setdefault(str(c.extra.get("categoria_minima", "—")), []).append(c)
        for cat in sorted(agrup):
            out.append(f"<p><strong>Exigibles desde {_e(cat)}:</strong></p><ul class=\"cols\">"
                       + "".join(f"<li>{_e(c.id)}{_m(c)} · {_e(c.titulo)}</li>" for c in agrup[cat]) + "</ul>")
    return "\n".join(out)


def _plan(an: Analisis, h: int) -> str:
    out = [f"<h{h}>Plan de acción</h{h}>"]
    if not an.plan:
        out.append("<p>Sin acciones definidas.</p>")
    else:
        venc = {a.id for a in an.vencidas}

        def fila(a: Accion):
            est = _e(a.estado) + (' <span class="venc">VENCIDA</span>' if a.id in venc else "")
            return [_e(a.id), _e(", ".join(a.controles)), _e(a.accion), _e(a.responsable),
                    _e(_fecha(a.fecha_objetivo)), est]
        plan = sorted(an.plan, key=lambda x: (x.fecha_objetivo or date.max, x.id))
        out.append(_tabla(["ID", "Controles", "Acción", "Responsable", "Fecha objetivo", "Estado"],
                          [fila(a) for a in plan]))
        avisos = [f"{a.id}: {m}" for a in an.plan for m in a.avisos]
        if avisos:
            out.append('<div class="aviso"><ul>' + "".join(f"<li>{_e(m)}</li>" for m in avisos) + "</ul></div>")
    out.append(f"<h{h + 1}>Brechas sin acción ({len(an.brechas_sin_accion)})</h{h + 1}>")
    if an.brechas_sin_accion:
        out.append('<ul class="cols">' + "".join(f"<li>{_e(i)}</li>" for i in an.brechas_sin_accion) + "</ul>")
    else:
        out.append("<p>Todas las brechas tienen acción.</p>")
    return "\n".join(out)


def render_body(an: Analisis, nivel: int = 2) -> str:
    """Secciones del informe sin cabecera ni <html>. `nivel` = nivel del primer encabezado (h2 por defecto)."""
    h = max(1, min(nivel, 4))
    partes = [_resumen(an, h), f"<h{h}>Detalle por marco</h{h}>"]
    partes += [_marco(an, r, h + 1) for r in an.results]
    partes.append(_plan(an, h))
    if an.warnings:
        partes.append(f"<h{h}>Avisos</h{h}><div class=\"aviso\"><ul>"
                      + "".join(f"<li>{_e(w)}</li>" for w in an.warnings) + "</ul></div>")
    return '<div class="smc-cuerpo">\n' + "\n".join(partes) + "\n</div>"


def _cabecera(an: Analisis) -> str:
    c = an.cliente
    cat = f" · Categoría ENS: {_e(an.categoria_ens)}" if an.categoria_ens else ""
    return (f"<h1>Informe de brechas · {_e(c.get('nombre', 'cliente'))}</h1>"
            f'<p class="meta">Sector: {_e(c.get("sector", "—"))} · Entidad NIS2: {_e(c.get("tipo_entidad_nis2", "—"))}'
            f" · Sector público: {'sí' if c.get('sector_publico') else 'no'}{cat}"
            f" · Fecha de evaluación: {_e(c.get('fecha', '—'))} · Informe a {_e(an.hoy.isoformat())}</p>")


def render_html(an: Analisis) -> str:
    nombre = _e(an.cliente.get("nombre", "cliente"))
    return ('<!DOCTYPE html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>Informe de brechas · {nombre}</title>\n<style>{CSS}</style>\n</head>\n"
            f'<body>\n<main class="smc">\n{_cabecera(an)}\n{render_body(an)}\n</main>\n</body>\n</html>\n')


def run_html(path: Path, hoy: date | None = None) -> str:
    return render_html(analyse(_load(path), hoy))
