"""Informe HTML autocontenido (CSS en línea, sin JS, sin recursos externos).

API:
- `render_html(analisis) -> str`: documento completo.
- `render_body(analisis, nivel=2) -> str`: solo el contenido (secciones), reutilizable por el dashboard.
- `CSS`: hoja de estilos en línea que necesita el cuerpo.
- `run_html(path, hoy=None, registry=None) -> str`: carga una evaluación y devuelve el documento.
- v0.6: `registry` (ruta o dict) añade tecnologías, reglas y suscripciones (cálculo en `smc.tech`); la madurez
  MITRE (`smc.mitre`) se añade siempre. `render_mitre`, `cargar_registry` y `es_registry` los reutiliza el dashboard.
- v0.7: secciones opcionales de pentest, purple team, IA (RIA y agentes) y PMO. `run_html(..., pentest=, purple=,
  ai=, pmo=)` (rutas o dicts) las calcula con `smc.offensive`, `smc.ai_act` y `smc.pmo`; `render_html`/`render_body`
  reciben los resultados ya calculados en `extras` (claves `pentest`, `purple`, `ai`, `pmo`). Con `purple` la madurez
  MITRE cuenta los ejercicios detectados (ver `smc.mitre`). Sin esos ficheros el informe no cambia.
Todo texto procedente de la evaluación o de los catálogos pasa por `html.escape`.
"""
from __future__ import annotations

import math
from datetime import date
from html import escape
from pathlib import Path

import yaml

from .gap import ETIQUETA_MITRE, NOTA_VERIFICAR, Analisis, analyse, _load, estado_vertical, url_https
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
        out.append(f'<p class="aviso"><strong>Aviso ENS:</strong> {_e(len(an.ens_verificar))} medidas ENS '
                   + _e(NOTA_VERIFICAR) + " (<code>verificar</code>): «no aplica» y los refuerzos por categoría pueden "
                   "variar según esas dimensiones. Se marcan con (verificar).</p>")
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
    if r.evidencia_caducada:
        out.append(f"<h{h + 1}>Evidencia caducada ({len(r.evidencia_caducada)})</h{h + 1}>")
        out.append('<p class="nota">Todas las evidencias de estos controles han caducado; renovarlas. '
                   'No afecta a la puntuación de cumplimiento.</p>')
        out.append('<ul class="cols">' + "".join(f"<li>{_e(c.id)} · {_e(c.titulo)}</li>" for c in r.evidencia_caducada) + "</ul>")
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


def _enlace(titulo, url) -> str:
    """Enlace solo con https://; si no, texto escapado sin href."""
    if url_https(url):
        return f'<a href="{_e(url)}" rel="noopener noreferrer">{_e(titulo)}</a>'
    return _e(titulo)


def _verticales(an: Analisis, h: int) -> str:
    from .verticals import cargar_verticales
    res = an.verticales
    cat = {v.id: v for v in cargar_verticales()}
    media = "—" if res.madurez_media is None else f"{res.madurez_media} / 5"
    out = [f"<h{h}>Verticales</h{h}>", f"<p>Madurez media de las verticales evaluadas: <strong>{_e(media)}</strong></p>"]
    filas = []
    for r in res.verticales:
        if r.madurez is None or not r.puntua:
            mad, barra = "—", ""
        else:
            mad, barra = _e(r.madurez), _barra(r.madurez * 20)
        filas.append([_e(r.id), _e(r.nombre), _e(estado_vertical(r)), mad, barra, _e(r.producto or "—")])
    out.append(_tabla(["ID", "Vertical", "Estado", "Madurez (0-5)", "", "Producto"], filas))
    if res.no_evaluables:
        out.append(f"<h{h + 1}>No evaluables ({len(res.no_evaluables)})</h{h + 1}>")
        out.append("<ul>" + "".join(f"<li><strong>{_e(r.id)}</strong> {_e(r.nombre)}: {_e(r.motivo)}</li>"
                                    for r in res.no_evaluables) + "</ul>")
    items = []
    for r in res.verticales:
        v = cat.get(r.id)
        if not v or r.estado == "sin_evaluar":
            continue
        for x in v.recursos:
            items.append(f"<li>{_e(r.id)}: {_enlace(x.get('titulo', ''), x.get('url'))}</li>")
        for e in v.estado_recursos:
            items.append(f"<li>{_e(r.id)}: {_e(e.get('proyecto', ''))} (pendiente)</li>")
    if items:
        out.append(f"<h{h + 1}>Recursos públicos</h{h + 1}><ul>" + "".join(items) + "</ul>")
    return "\n".join(out)


# --- v0.6: tecnologías, reglas, suscripciones y MITRE (cálculo en smc.tech y smc.mitre) ---

def es_registry(d) -> bool:
    """Forma de registro de tecnologías: mapa con lista `technologies` (y sin `evaluaciones`)."""
    return isinstance(d, dict) and isinstance(d.get("technologies"), list) and "evaluaciones" not in d


def cargar_registry(registry) -> dict:
    """Ruta o dict -> dict de registro. ValueError si no tiene la forma de un registro."""
    if isinstance(registry, (str, Path)):
        try:
            registry = yaml.safe_load(Path(registry).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"registro no legible ({type(exc).__name__})") from exc
    if not es_registry(registry):
        raise ValueError("no es un registro de tecnologías (falta la lista 'technologies')")
    return registry


def _n(x, dec: int = 0) -> str:
    """Número finito formateado; cualquier otra cosa («abc», NaN, inf) sale como «—». Nunca rompe."""
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        return "—"
    return f"{x:.{dec}f}"


def _pct(x) -> str:
    return "—" if _n(x) == "—" else f"{_n(x)} %"


def _tecnologias(registry: dict, h: int) -> str:
    from . import tech
    filas = tech.evaluar_tecnologias(registry)
    out = [f"<h{h}>Tecnologías evaluadas ({len(filas)})</h{h}>"]
    if not filas:
        out.append("<p>El registro no tiene tecnologías.</p>")
        return "\n".join(out)
    cel = []
    for f in filas:
        mad = f["madurez"]
        cel.append([_e(f["id"]), _e(f["nombre"]), _e(f["vertical"] or "—"), _pct(f["cobertura_pct"]),
                    _e(f["configuracion"]), _e(_n(mad, 0) if isinstance(mad, int) else _n(mad, 1)),
                    _barra(mad * 20) if _n(mad) != "—" else "", _e("; ".join(f["avisos"]) or "—")])
    out.append(_tabla(["ID", "Tecnología", "Vertical", "Cobertura", "Configuración", "Madurez (0-5)", "", "Avisos"], cel))
    return "\n".join(out)


def _reglas(registry: dict, hoy: date, h: int) -> str:
    from . import tech
    r = tech.reglas(registry, hoy)
    out = [f"<h{h}>Estado de las reglas</h{h}>",
           f"<p>Revisadas: <strong>{len(r['revisadas'])}</strong> · Sin revisar o con revisión caducada "
           f"(más de {tech.UMBRAL_REGLAS_DIAS} días): <strong>{len(r['sin_revisar'])}</strong> · "
           f"No evaluables: <strong>{len(r['no_evaluables'])}</strong> · Con reglas any-any: "
           f"<strong>{len(r['any_any'])}</strong></p>"]
    if r["any_any"]:
        out.append(f'<div class="alerta"><strong>Reglas any-any ({len(r["any_any"])} dispositivo(s)):</strong> una '
                   "revisión reciente no las hace aceptables.<ul>"
                   + "".join(f"<li><strong>{_e(f['id'])}</strong> {_e(f['nombre'])}: {_e(f['reglas_any_any'])} "
                             f"regla(s) any-any (estado: {_e(f['estado'])})</li>" for f in r["any_any"]) + "</ul></div>")
    cab = ["Dispositivo", "Última revisión", "Días", "Reglas", "any-any", "Sin uso"]

    def fila(f):
        dias = f["dias_sin_revisar"]
        return [_e(f"{f['id']} {f['nombre']}"), _e(_fecha(f["ultima_revision"]) if f["ultima_revision"] else "nunca"),
                _e("—" if dias is None else dias), _e("—" if f["n_reglas"] is None else f["n_reglas"]),
                f'<span class="venc">{_e(f["reglas_any_any"])}</span>' if f["reglas_any_any"] else "0",
                _e(f["reglas_sin_uso"])]
    out.append(f"<h{h + 1}>Sin revisar o revisión caducada ({len(r['sin_revisar'])})</h{h + 1}>")
    out.append(_tabla(cab, [fila(f) for f in r["sin_revisar"]]) if r["sin_revisar"] else "<p>Ninguno.</p>")
    out.append(f"<h{h + 1}>No evaluables ({len(r['no_evaluables'])})</h{h + 1}>")
    if r["no_evaluables"]:
        out.append('<p class="nota">No se puede decir si sus reglas son correctas. No cuentan como revisadas.</p><ul>'
                   + "".join(f"<li><strong>{_e(f['id'])}</strong> {_e(f['nombre'])}: {_e(f['motivo'])}</li>"
                             for f in r["no_evaluables"]) + "</ul>")
    else:
        out.append("<p>Ninguno.</p>")
    out.append(f"<h{h + 1}>Revisadas ({len(r['revisadas'])})</h{h + 1}>")
    out.append(_tabla(cab, [fila(f) for f in r["revisadas"]]) if r["revisadas"] else "<p>Ninguna.</p>")
    if r["avisos"]:
        out.append('<div class="aviso"><ul>' + "".join(f"<li>{_e(a)}</li>" for a in r["avisos"]) + "</ul></div>")
    return "\n".join(out)


def _suscripciones(registry: dict, hoy: date, h: int) -> str:
    from . import tech
    dias, umbral = 90, tech.UMBRAL_INFRAUSO
    r = tech.suscripciones(registry, hoy, dias, umbral)
    totales: dict[str, float] = {}
    for (_prov, mon), c in r["coste_por_proveedor"].items():
        totales[mon] = totales.get(mon, 0.0) + (c if isinstance(c, (int, float)) and math.isfinite(c) else 0.0)
    total = " + ".join(f"{_n(v)} {_e(m)}" for m, v in sorted(totales.items(), key=lambda kv: str(kv[0]))) or "—"
    out = [f"<h{h}>Suscripciones</h{h}>", f"<p>Coste anual total: <strong>{total}</strong></p>"]
    out.append(f"<h{h + 1}>Vencen en {dias} días ({len(r['renovaciones'])})</h{h + 1}>")
    if r["renovaciones"]:
        out.append(_tabla(["Fecha", "Días", "Tecnología", "Proveedor", "Coste anual", "Propietario", "Autorrenovación"],
                          [[_e(x["fecha"].isoformat()),
                            '<span class="venc">VENCIDA</span>' if x["dias"] < 0 else _e(x["dias"]),
                            _e(f"{x['id']} {x['nombre']}"), _e(x["proveedor"]), f"{_n(x['coste_anual'])} {_e(x['moneda'])}",
                            _e(x["propietario"] or "—"), "sí" if x["autorrenovacion"] else "no"]
                           for x in r["renovaciones"]]))
    else:
        out.append("<p>Ninguna.</p>")
    out.append(f"<h{h + 1}>Uso bajo el umbral del {_e(_n(umbral * 100))} % ({len(r['infrautilizadas'])})</h{h + 1}>")
    if r["infrautilizadas"]:
        out.append(_tabla(["Tecnología", "Proveedor", "En uso / contratadas", "Uso", "Coste ocioso"],
                          [[_e(f"{x['id']} {x['nombre']}"), _e(x["proveedor"]),
                            f"{_n(x['en_uso'])} / {_n(x['contratadas'])}", f"{_n(x['uso_pct'], 1)} %",
                            f"{_n(x['coste_ocioso'])} {_e(x['moneda'])}"] for x in r["infrautilizadas"]]))
    else:
        out.append("<p>Ninguna.</p>")
    if r["sobredespliegue"]:
        out.append(f"<h{h + 1}>Sobredespliegue ({len(r['sobredespliegue'])})</h{h + 1}>")
        out.append(_tabla(["Tecnología", "Proveedor", "En uso / contratadas", "Exceso"],
                          [[_e(f"{x['id']} {x['nombre']}"), _e(x["proveedor"]),
                            f"{_n(x['en_uso'])} / {_n(x['contratadas'])}", _n(x["exceso"])] for x in r["sobredespliegue"]]))
    out.append(f"<h{h + 1}>Coste anual por proveedor</h{h + 1}>")
    if r["coste_por_proveedor"]:
        out.append(_tabla(["Proveedor", "Coste anual"],
                          [[_e(p), f"{_n(c)} {_e(m)}"] for (p, m), c in sorted(r["coste_por_proveedor"].items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1])))]))
    else:
        out.append("<p>Sin suscripciones.</p>")
    if r["avisos"]:
        out.append('<div class="aviso"><ul>' + "".join(f"<li>{_e(a)}</li>" for a in r["avisos"]) + "</ul></div>")
    return "\n".join(out)


def datos_mitre(hoy: date, purple=None) -> dict:
    """Madurez y casos sin playbook desde `smc.mitre` (no se recalcula aquí). `purple`: ejercicios que cuentan como prueba."""
    from . import mitre
    return {"madurez": mitre.madurez(hoy=hoy, purple=purple), "sin_playbook": mitre.sin_playbook()}


def render_mitre(datos: dict, h: int = 2) -> str:
    m = datos["madurez"]
    out = [f"<h{h}>Madurez MITRE ATT&amp;CK</h{h}>",
           f'<p class="nota"><strong>{_e(ETIQUETA_MITRE)}.</strong> No describe al cliente: es la cobertura del SOC.</p>',
           '<p class="nota">Niveles: 0 sin caso · 1 caso sin regla · 2 regla · 3 regla con playbook · 4 probada · '
           "5 probada en los últimos 90 días. La táctica toma el mínimo de sus casos activos.</p>",
           f"<p>Técnicas con caso de uso: <strong>{len(m['tecnicas'])}</strong> · Casos de uso: "
           f"<strong>{len(m['casos'])}</strong></p>"]
    if m["tacticas"]:
        out.append(_tabla(["Táctica", "Madurez (0-5)", ""],
                          [[_e(t), _e(n), _barra(n * 20)] for t, n in m["tacticas"].items()]))
    else:
        out.append("<p>Sin casos de uso activos.</p>")
    sp = datos["sin_playbook"]
    out.append(f"<h{h + 1}>Casos sin playbook ({len(sp)})</h{h + 1}>")
    out.append('<ul class="cols">' + "".join(f"<li>{_e(i)}</li>" for i in sp) + "</ul>" if sp
               else "<p>Todos los casos tienen playbook.</p>")
    return "\n".join(out)


# --- v0.7: pentest, purple team, IA y PMO (cálculo en smc.offensive, smc.ai_act y smc.pmo) ---

def _f(d) -> str:
    return d.isoformat() if hasattr(d, "isoformat") else "—"


def _lista(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def _avisos(avisos: list[str]) -> str:
    return '<div class="aviso">' + _lista([_e(a) for a in avisos]) + "</div>" if avisos else ""


def render_pentest(e, h: int = 2) -> str:
    """`e`: `offensive.EstadoHallazgos`."""
    out = [f"<h{h}>Pentesting: hallazgos</h{h}>",
           f"<p>Total: <strong>{_e(e.total)}</strong> · Abiertos: <strong>{len(e.abiertos)}</strong> · Fuera de SLA: "
           f"<strong>{len(e.fuera_sla)}</strong> · Pendientes de retest: <strong>{len(e.pendientes_retest)}</strong> · "
           f"Aceptados sin revisión: <strong>{len(e.aceptados_sin_revision)}</strong></p>",
           _tabla(["Severidad efectiva", "Abiertos"], [[_e(s), _e(n)] for s, n in e.por_severidad.items()])]
    if e.fuera_sla:
        out.append(f"<h{h + 1}>Fuera de SLA</h{h + 1}>")
        out.append(_tabla(["ID", "Título", "Sev. efectiva", "Días", "SLA", "Activo", "Control"],
                          [[_e(f.hallazgo.id), _e(f.hallazgo.titulo), _e(f.severidad_efectiva), _e(f.dias), _e(f.sla_dias),
                            _e(f.hallazgo.activo or "—"), _e(f.hallazgo.control or "—")] for f in e.fuera_sla]))
    if e.retest_fallido:
        out.append(f"<h{h + 1}>Retest fallido</h{h + 1}>")
        out.append(_tabla(["ID", "Título", "Resultado del retest", "Fecha de retest", "Detección", "Activo", "Control"],
                          [[_e(x.id), _e(x.titulo), _e(x.resultado_retest), _e(_f(x.fecha_retest)), _e(_f(x.fecha_deteccion)),
                            _e(x.activo or "—"), _e(x.control or "—")] for x in e.retest_fallido]))
    for titulo, lista in (("Pendientes de retest", e.pendientes_retest), ("Aceptados sin fecha de revisión", e.aceptados_sin_revision)):
        if lista:
            out.append(f"<h{h + 1}>{_e(titulo)}</h{h + 1}>" + _lista([f"<strong>{_e(x.id)}</strong> {_e(x.titulo)}" for x in lista]))
    out.append(_avisos(e.avisos))
    return "\n".join(x for x in out if x)


def render_purple(r, h: int = 2) -> str:
    """`r`: `offensive.ResultadoPurple`."""
    out = [f"<h{h}>Purple team: ejercicios</h{h}>", f"<p>Ejercicios: <strong>{_e(r.total)}</strong></p>"]
    if r.cobertura_por_tactica:
        filas = []
        for t, c in r.cobertura_por_tactica.items():
            tm = "—" if c["tiempo_medio_min"] is None else _e(c["tiempo_medio_min"])
            filas.append([_e(t), _e(c["tecnicas"]), _e(c["detectado"]), _e(c["parcial"]), _e(c["no_detectado"]),
                          f'{_e(c["cobertura_pct"])} %' + _barra(c["cobertura_pct"]), tm])
        out.append(_tabla(["Táctica", "Técnicas", "Detectado", "Parcial", "No detectado", "Cobertura", "Tiempo medio (min)"], filas))
    if r.no_detectadas:
        out.append(f"<h{h + 1}>Técnicas no detectadas del todo</h{h + 1}>"
                   + _lista([f"{_e(x.tecnica)} ({_e(x.caso_uso)}, {_e(x.resultado)}, {_f(x.fecha)})" for x in r.no_detectadas]))
    if r.mejoras_abiertas:
        out.append(f"<h{h + 1}>Mejoras abiertas</h{h + 1}>"
                   + _lista([f"<strong>{_e(x.id)}</strong> ({_e(x.mejora.estado)}): {_e(x.mejora.descripcion)}" for x in r.mejoras_abiertas]))
    if r.ejercicios_caducados:
        out.append(f"<h{h + 1}>Ejercicios de más de 12 meses</h{h + 1}>"
                   + _lista([f"{_e(x.id)} ({_f(x.fecha)}, {_e(x.tecnica)})" for x in r.ejercicios_caducados]))
    out.append(_avisos(r.avisos))
    return "\n".join(x for x in out if x)


def render_ia(res, hallazgos, h: int = 2) -> str:
    """`res`: `ai_act.ResultadoIA`; `hallazgos`: lista de `ai_act.HallazgoAgente` (o None)."""
    from . import ai_act
    out = [f"<h{h}>IA: RIA (Reglamento (UE) 2024/1689) y seguridad de agentes</h{h}>",
           f'<div class="alerta"><strong>Aviso.</strong> {_e(ai_act.AVISO_JURIDICO)}</div>',
           '<p class="nota">Fechas vigentes tras el Ómnibus digital sobre IA (Reglamento (UE) 2026/1744). Las obligaciones '
           "marcadas «verificar» tienen fecha o alcance pendientes de contrastar.</p>"]
    if res.organizacion:
        out.append(f"<p>Organización: {_e(res.organizacion)}</p>")
    filas = [[_e(s.id), _e(s.nombre), _e(s.nivel), _e(", ".join(s.roles)), _e(len(s.obligaciones)),
              _e(len(s.pendientes)), f'<span class="venc">{len(s.incumplidas)}</span>' if s.incumplidas else "0"]
             for s in res.sistemas]
    if filas:
        out.append(_tabla(["ID", "Sistema", "Nivel", "Rol", "Obligaciones", "Pendientes", "Pendientes ya vigentes"], filas))
    else:
        out.append("<p>El inventario no tiene sistemas.</p>")
    for s in res.sistemas:
        transitorio = getattr(s, "regimen_transitorio", None) or []
        if not s.obligaciones and not transitorio:
            continue
        out.append(f"<h{h + 1}>{_e(s.id)} {_e(s.nombre)}</h{h + 1}>")
        if s.obligaciones:
            out.append(_tabla(["Obligación", "Artículo", "Rol", "Estado", "Cumplimiento", "Nota"],
                              [[_e(f"{o.id} {o.titulo}"), _e(o.articulo), _e(", ".join(o.roles)),
                                _e("vigente" if o.estado == ai_act.VIGENTE else f"aplicable desde {o.aplica_desde}"),
                                f'<span class="venc">{_e(o.cumplimiento)}</span>' if o.cumplimiento == ai_act.PENDIENTE else _e(o.cumplimiento),
                                ('<span class="venc">verificar</span> ' if o.verificar else "") + _e(o.nota)] for o in s.obligaciones]))
        if transitorio:
            out.append(f"<h{h + 2}>Régimen transitorio (art. 111.2 RIA)</h{h + 2}>")
            out.append('<p class="nota">Obligaciones del capítulo III que no se emiten como pendientes porque el sistema estaba '
                       "en el mercado antes de su fecha de aplicación y no ha tenido cambios significativos de diseño.</p>")
            out.append(_tabla(["Obligación", "Artículo", "Rol", "Pasaría a aplicar", "Condición"],
                              [[_e(f"{t.id} {t.titulo}"), _e(t.articulo), _e(", ".join(t.roles)),
                                _e(t.aplica_desde.isoformat() if t.aplica_desde else "solo con cambios significativos"),
                                _e(t.condicion)] for t in transitorio]))
    if res.no_clasificados:
        out.append(f"<h{h + 1}>Sistemas no clasificados</h{h + 1}>"
                   + _lista([f"{_e(n.get('id'))} {_e(n.get('nombre'))}: {_e(n.get('error'))}" for n in res.no_clasificados]))
    if hallazgos is not None:
        out.append(f"<h{h + 1}>Seguridad de agentes (OWASP Top 10 LLM 2025, MITRE ATLAS)</h{h + 1}>")
        if hallazgos:
            out.append(_tabla(["Sistema", "Agente", "Comprobación", "Severidad", "Detalle", "OWASP", "ATLAS", "Mitigaciones ATLAS"],
                              [[_e(x.sistema), _e(x.agente), _e(f"{x.id} {x.titulo}"), _e(x.severidad), _e(x.detalle),
                                _e(", ".join(x.owasp)), _e(", ".join(x.atlas) or "—"), _e(", ".join(x.mitigaciones))] for x in hallazgos]))
        else:
            out.append("<p>Sin hallazgos.</p>")
    out.append(f"<h{h + 1}>Fuentes</h{h + 1}>" + _lista([_enlace(t, u) for t, u in ai_act.FUENTES]))
    out.append(_avisos(res.warnings + res.errores))
    return "\n".join(x for x in out if x)


def render_evolucion(comp, h: int = 2) -> str:
    """Sección «Evolución» (smc.compare.Comparacion). Todo escapado."""
    def n(x, dec=1, signo=False):
        return "—" if x is None else (f"{x:+.{dec}f}" if signo else f"{x:.{dec}f}")

    def ids(items):
        return ", ".join(_e(c.id) for c in items) or "ninguno"
    out = [f"<h{h}>Evolución respecto a la evaluación anterior</h{h}>",
           f"<p>Anterior: {_e(comp.cliente_antes or 'sin nombre')} ({_e(comp.fecha_antes or 'sin fecha')}). "
           f"Actual: {_e(comp.cliente_despues or 'sin nombre')} ({_e(comp.fecha_despues or 'sin fecha')}).</p>"]
    out.append(_avisos(list(comp.avisos)))
    out.append(_tabla(["Marco", "Antes %", "Después %", "Delta"],
                      [[_e(m.framework), n(m.antes), n(m.despues), n(m.delta, 1, True) if m.comparable else "no comparable"]
                       for m in comp.marcos]))
    out.append(_tabla(["Controles", "Nº", "IDs"],
                      [[t, str(len(l)), ids(l)] for t, l in (("Cerrados", comp.cerrados), ("Mejoran", comp.mejoran),
                                                             ("Empeoran", comp.empeoran), ("Nuevas brechas", comp.nuevas_brechas),
                                                             ("Dejan de evaluarse", comp.dejan_de_evaluarse))]
                      + [["Sin cambio", str(len(comp.sin_cambio)), "—"]]))
    out.append(f"<p>Brechas P1: antes {len(comp.p1_antes)} ({_e(', '.join(comp.p1_antes) or 'ninguna')}), "
               f"después {len(comp.p1_despues)} ({_e(', '.join(comp.p1_despues) or 'ninguna')}).</p>")
    out.append(f"<p>Madurez media de verticales: {n(comp.madurez_antes, 2)} → {n(comp.madurez_despues, 2)} "
               f"({n(comp.madurez_delta, 2, True)}).</p>")
    out.append(f"<p>Acciones del plan cerradas: {_e(', '.join(comp.acciones_cerradas) or 'ninguna')}.</p>")
    return "\n".join(x for x in out if x)


def _eur(d) -> str:
    return "n/d" if d is None else _e(f"{d:,.2f}".replace(",", " ") + " €")


def render_pmo(a, h: int = 2) -> str:
    """`a`: `pmo.Analisis`."""
    p = a.proyecto
    out = [f"<h{h}>PMO: {_e(p.nombre or p.id)}</h{h}>",
           f'<p class="meta">Cliente: {_e(p.cliente)} · Periodo: {_f(p.inicio)} a {_f(p.fin)} · A fecha {_f(a.hoy)}</p>',
           _tabla(["Partida", "Presupuesto", "Real", "Desviación"],
                  [[_e(k), _eur(v["presupuesto"]), _eur(v["real"]), _eur(v["desviacion"])] for k, v in a.por_partida.items()]
                  + [["<strong>Total</strong>", _eur(a.total["presupuesto"]), _eur(a.total["real"]), _eur(a.total["desviacion"])]])]
    e = a.evm
    out.append(f"<h{h + 1}>Valor ganado (EVM)</h{h + 1}>")
    out.append(_tabla(["BAC", "PV", "EV", "AC", "CPI", "SPI"],
                      [[_eur(e.bac), _eur(e.pv), _eur(e.ev), _eur(e.ac), _e(e.cpi if e.cpi is not None else "n/d"),
                        _e(e.spi if e.spi is not None else "n/d")]]))
    out.append(f"<h{h + 1}>Tareas retrasadas ({len(a.tareas_retrasadas)})</h{h + 1}>")
    out.append(_lista([f"<strong>{_e(t.id)}</strong> {_e(t.titulo)}: fin {_f(t.fin)}, avance {_e(t.avance)} %" for t in a.tareas_retrasadas])
               if a.tareas_retrasadas else "<p>Ninguna.</p>")
    out.append(f"<h{h + 1}>Tareas sin control asociado ({len(a.tareas_sin_control)})</h{h + 1}>")
    out.append(_lista([f"<strong>{_e(t.id)}</strong> {_e(t.titulo)}" for t in a.tareas_sin_control])
               if a.tareas_sin_control else "<p>Ninguna.</p>")
    out.append(f"<h{h + 1}>Próximos eventos (30 días)</h{h + 1}>")
    out.append(_tabla(["Fecha", "Tipo", "Evento"], [[_f(x.fecha), _e(x.tipo), _e(x.titulo)] for x in a.proximos_eventos])
               if a.proximos_eventos else "<p>Ninguno.</p>")
    if a.horas_rol_mes:
        out.append(f"<h{h + 1}>Horas por rol y mes</h{h + 1}>")
        out.append(_tabla(["Rol", "Mes", "Horas"], [[_e(r), _e(m), _e(f"{v.normalize():f}")]
                                                     for r, ms in a.horas_rol_mes.items() for m, v in ms.items()]))
    if p.riesgos:
        out.append(f"<h{h + 1}>Riesgos del proyecto</h{h + 1}>")
        out.append(_tabla(["ID", "Riesgo", "Prob.", "Impacto", "Estado"],
                          [[_e(r.id), _e(r.descripcion), _e(r.probabilidad), _e(r.impacto), _e(r.estado)] for r in p.riesgos]))
    if a.suscripciones is not None:
        out.append(f"<p>Suscripciones del registro (fuera del presupuesto del proyecto): coste anual en EUR "
                   f"<strong>{_eur(a.suscripciones['coste_anual_eur'])}</strong></p>")
    out.append(_avisos(a.avisos))
    return "\n".join(x for x in out if x)


def calcular_extras(hoy: date, pentest=None, purple=None, ai=None, pmo=None, assessment: dict | None = None, registry=None) -> dict:
    """Resultados de las secciones v0.7 a partir de ficheros o dicts (None = sin sección).
    Lanza ValueError (OffensiveError, AIActError) si los datos no valen."""
    from . import ai_act, offensive, pmo as pmo_mod
    extras: dict = {}
    if pentest is not None:
        extras["pentest"] = offensive.estado_hallazgos(pentest, hoy)
    if purple is not None:
        pu = purple if isinstance(purple, offensive.Purple) else offensive.cargar_purple(purple)
        extras["purple_datos"] = pu
        extras["purple"] = offensive.purple(pu, hoy)
    if ai is not None:
        extras["ai"] = (ai_act.obligaciones(ai, hoy, estricto=False), ai_act.riesgos_agente(ai))
    if pmo is not None:
        extras["pmo"] = pmo_mod.analizar(pmo_mod.cargar_proyecto(pmo), hoy, assessment, registry)
    return extras


def render_body(an: Analisis, nivel: int = 2, registry=None, mitre: dict | None = None, extras: dict | None = None) -> str:
    """Secciones del informe sin cabecera ni <html>. `nivel` = nivel del primer encabezado (h2 por defecto).
    `registry` (dict o ruta) añade tecnologías, reglas y suscripciones; MITRE se añade siempre.
    `extras` (ver `calcular_extras`) añade pentest, purple team, IA y PMO."""
    extras = extras or {}
    h = max(1, min(nivel, 4))
    partes = [_resumen(an, h), f"<h{h}>Detalle por marco</h{h}>"]
    partes += [_marco(an, r, h + 1) for r in an.results]
    if an.verticales is not None:
        partes.append(_verticales(an, h))
    if "evolucion" in extras:
        partes.append(render_evolucion(extras["evolucion"], h))
    if registry is not None:
        reg = cargar_registry(registry)
        partes += [_tecnologias(reg, h), _reglas(reg, an.hoy, h), _suscripciones(reg, an.hoy, h)]
    if "pentest" in extras:
        partes.append(render_pentest(extras["pentest"], h))
    if "purple" in extras:
        partes.append(render_purple(extras["purple"], h))
    if "ai" in extras:
        partes.append(render_ia(extras["ai"][0], extras["ai"][1], h))
    if "pmo" in extras:
        partes.append(render_pmo(extras["pmo"], h))
    if mitre is None:
        mitre = datos_mitre(an.hoy, extras.get("purple_datos"))
    partes.append(render_mitre(mitre, h))
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


def render_html(an: Analisis, registry=None, mitre: dict | None = None, extras: dict | None = None) -> str:
    nombre = _e(an.cliente.get("nombre", "cliente"))
    return ('<!DOCTYPE html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>Informe de brechas · {nombre}</title>\n<style>{CSS}</style>\n</head>\n"
            f'<body>\n<main class="smc">\n{_cabecera(an)}\n{render_body(an, 2, registry, mitre, extras)}\n</main>\n</body>\n</html>\n')


def run_html(path: Path, hoy: date | None = None, registry=None, pentest=None, purple=None, ai=None, pmo=None,
             anterior=None) -> str:
    if registry is not None:
        registry = cargar_registry(registry)   # falla antes de analizar si el registro no vale
    datos = _load(path)
    an = analyse(datos, hoy)
    extras = calcular_extras(an.hoy, pentest, purple, ai, pmo, datos, registry) if any(
        x is not None for x in (pentest, purple, ai, pmo)) else None
    if anterior is not None:
        from . import compare
        extras = dict(extras or {})
        previo = _load(anterior)
        if not isinstance(previo, dict):
            raise ValueError(f"{anterior}: la evaluación anterior no es un mapa YAML")
        extras["evolucion"] = compare.comparar(previo, datos, an.hoy)
    return render_html(an, registry, None, extras)
