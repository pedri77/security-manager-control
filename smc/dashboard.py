"""Dashboard estático multicliente (v0.4).

v0.6: los registros de tecnologías del directorio (mapa con lista `technologies`) no son avisos. Se asocian a
una evaluación por nombre: `<stem>.<algo>.yaml`, `<stem>-<algo>.yaml` o `<stem>_<algo>.yaml` (p. ej.
`ejemplo-energia.registry.yaml`); un registro se asocia a una sola evaluación (orden alfabético). Con registro asociado el cliente
suma las columnas «Reglas no evaluables», «any-any» y «Suscripciones que vencen» y su página las 3 secciones
de tecnologías; sin registro, «—». `mitre.html` es la página común de madurez MITRE (siempre se genera).

`smc dashboard <dir_evaluaciones> -o <dir_salida> [--hoy AAAA-MM-DD]` recorre los `*.yaml` del directorio
(no recursivo), genera `index.html` y una página `<slug>.html` por evaluación válida (reutiliza
`report_html.render_html`). Todo estático: CSS en línea, sin JS, sin recursos externos, enlaces relativos.

Semáforo (se evalúa en este orden; la cifra de cumplimiento es la media simple de los marcos en alcance):
- ROJO:   cumplimiento medio < 50 %, o al menos una brecha P1 evaluada sin acción abierta que la cubra.
- ÁMBAR:  cumplimiento medio < 80 %, o alguna brecha P1 evaluada (con acción), o alguna acción vencida.
- VERDE:  el resto.
Los controles sin evaluar puntúan como no cumplidos (igual que en el informe), por lo que una evaluación
incompleta tiende a rojo/ámbar. Un YAML ilegible o que no sea una evaluación (sin `cliente` y `evaluaciones`
como mapas) no rompe el resto: se lista como aviso en el índice.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from .gap import Analisis, analyse
from .report_html import CSS, _e, datos_mitre, es_registry, render_html, render_mitre

EXTRA_CSS = """
.sem{display:inline-block;border-radius:10px;padding:1px 10px;font-weight:600;color:#fff;font-size:12px}
.sem.verde{background:var(--ok)}.sem.ambar{background:var(--mid);color:#1d2433}.sem.rojo{background:var(--bad)}
.volver{margin:0 0 12px}.num{text-align:right}
td .bar{min-width:70px;height:8px}
"""

SEMAFORO_TXT = {"verde": "Verde", "ambar": "Ámbar", "rojo": "Rojo"}


@dataclass
class Fila:
    slug: str
    fichero: str
    analisis: Analisis
    cumplimiento: dict[str, float]
    p1: int
    vencidas: int
    p1_sin_accion: int
    semaforo: str
    media: float
    vert_media: float | None = None   # madurez media de verticales (0-5); None si no hay sección o nada evaluado
    registry: dict | None = None      # registro de tecnologías asociado (v0.6)
    reglas_no_eval: int | None = None
    any_any: int | None = None
    subs_vencen: int | None = None


@dataclass
class Aviso:
    fichero: str
    motivo: str


@dataclass
class Resultado:
    filas: list[Fila] = field(default_factory=list)
    avisos: list[Aviso] = field(default_factory=list)
    registros_sin_cliente: list[str] = field(default_factory=list)   # ficheros de registro sin evaluación asociada


def slugify(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t or "cliente"


def semaforo(media: float, p1: int, p1_sin_accion: int, vencidas: int) -> str:
    if media < 50 or p1_sin_accion > 0:
        return "rojo"
    if media < 80 or p1 > 0 or vencidas > 0:
        return "ambar"
    return "verde"


def _es_evaluacion(d) -> bool:
    return isinstance(d, dict) and isinstance(d.get("cliente"), dict) and isinstance(d.get("evaluaciones"), dict)


def _asociar(stem: str, registros: dict[str, dict], usados: set[str]) -> str | None:
    """Fichero de registro asociado a la evaluación `stem` (prefijo + separador); None si no hay."""
    cands = [n for n in registros if n not in usados and len(n) > len(stem) and n.startswith(stem)
             and n[len(stem)] in ".-_"]
    return sorted(cands)[0] if cands else None


def recopilar(directorio: Path, hoy: date | None = None) -> Resultado:
    from . import tech
    hoy = hoy or date.today()
    res = Resultado()
    usados: set[str] = set()
    cargados: list[tuple[Path, object]] = []
    registros: dict[str, dict] = {}
    for f in sorted(Path(directorio).glob("*.yaml")):
        if f.name.endswith(".template.yaml"):   # plantillas: no son clientes
            continue
        try:
            datos = yaml.safe_load(f.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError, OSError) as exc:
            res.avisos.append(Aviso(f.name, f"YAML no legible ({type(exc).__name__})"))
            continue
        if es_registry(datos):
            registros[f.name] = datos
        else:
            cargados.append((f, datos))
    registros_usados: set[str] = set()
    for f, datos in cargados:
        if not _es_evaluacion(datos):
            res.avisos.append(Aviso(f.name, "no es una evaluación (faltan 'cliente' y 'evaluaciones')"))
            continue
        try:
            an = analyse(datos, hoy)
        except Exception as exc:  # una evaluación rota no debe tumbar el dashboard
            res.avisos.append(Aviso(f.name, f"no se pudo analizar ({type(exc).__name__}: {exc})"))
            continue
        base = slugify(f.stem)
        slug, n = base, 2
        while slug in usados or slug in ("index", "mitre"):
            slug, n = f"{base}-{n}", n + 1
        usados.add(slug)
        reg = None
        nom = _asociar(f.stem, registros, registros_usados)
        if nom:
            registros_usados.add(nom)
            reg = registros[nom]
        cumpl = {r.framework: r.puntuacion for r in an.results}
        media = round(sum(cumpl.values()) / len(cumpl), 1) if cumpl else 0.0
        p1 = sum(1 for r in an.results for b in r.brechas if b.nivel == "P1")
        res.filas.append(Fila(slug, f.name, an, cumpl, p1, len(an.vencidas), len(an.p1_sin_accion),
                              semaforo(media, p1, len(an.p1_sin_accion), len(an.vencidas)), media,
                              an.verticales.madurez_media if an.verticales is not None else None))
        if reg is not None:
            fila = res.filas[-1]
            fila.registry = reg
            r = tech.reglas(reg, hoy)
            fila.reglas_no_eval, fila.any_any = len(r["no_evaluables"]), len(r["any_any"])
            fila.subs_vencen = len(tech.suscripciones(reg, hoy)["renovaciones"])
    res.registros_sin_cliente = sorted(set(registros) - registros_usados)
    return res


def _doc(titulo: str, cuerpo: str) -> str:
    return ('<!DOCTYPE html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{_e(titulo)}</title>\n<style>{CSS}{EXTRA_CSS}</style>\n</head>\n"
            f'<body>\n<main class="smc">\n{cuerpo}\n</main>\n</body>\n</html>\n')


def render_index(res: Resultado, hoy: date) -> str:
    marcos = sorted({m for f in res.filas for m in f.cumplimiento}, key=lambda m: ("NIS2", "ENS", "TRANSVERSAL", "RED").index(m)
                    if m in ("NIS2", "ENS", "TRANSVERSAL", "RED") else 99)
    cab = ["Cliente", "Sector", "Entidad NIS2", "Categoría ENS"] + [f"{m} %" for m in marcos] + \
          ["Madurez verticales", "Reglas no evaluables", "Reglas any-any", "Suscripciones que vencen", "Brechas P1", "Acciones vencidas", "Fecha de evaluación", "Semáforo"]
    h = "".join(f"<th>{_e(c)}</th>" for c in cab)
    filas = []
    for f in res.filas:
        c = f.analisis.cliente
        celdas = [f'<a href="{_e(f.slug)}.html">{_e(c.get("nombre", f.fichero))}</a>', _e(c.get("sector", "—")),
                  _e(c.get("tipo_entidad_nis2", "—")), _e(f.analisis.categoria_ens or "—")]
        for m in marcos:
            celdas.append(f"{_e(f.cumplimiento[m])} %" if m in f.cumplimiento else "—")
        celdas += [("—" if f.vert_media is None else f"{_e(f.vert_media)} / 5"),
                   "—" if f.reglas_no_eval is None else _e(f.reglas_no_eval),
                   "—" if f.any_any is None else (f'<span class="venc">{_e(f.any_any)}</span>' if f.any_any else "0"),
                   "—" if f.subs_vencen is None else _e(f.subs_vencen), _e(f.p1), f'<span class="venc">{_e(f.vencidas)}</span>' if f.vencidas else "0",
                   _e(c.get("fecha", "—")),
                   f'<span class="sem {f.semaforo}">{SEMAFORO_TXT[f.semaforo]}</span>']
        filas.append("<tr>" + "".join(f"<td>{x}</td>" for x in celdas) + "</tr>")
    out = ["<h1>Security Manager Control · Panel de clientes</h1>",
           f'<p class="meta">{len(res.filas)} evaluación(es) · Datos a {_e(hoy.isoformat())}</p>']
    if res.avisos:
        out.append('<div class="alerta"><strong>Avisos:</strong> ficheros ignorados.<ul>'
                   + "".join(f"<li><code>{_e(a.fichero)}</code>: {_e(a.motivo)}</li>" for a in res.avisos)
                   + "</ul></div>")
    if res.registros_sin_cliente:
        out.append('<p class="nota">Registros de tecnologías sin evaluación asociada (nómbralos '
                   "<code>&lt;evaluación&gt;.registry.yaml</code>): "
                   + ", ".join(f"<code>{_e(n)}</code>" for n in res.registros_sin_cliente) + ".</p>")
    out.append('<p><a href="mitre.html">Madurez MITRE ATT&amp;CK (común a todos los clientes)</a></p>')
    if res.filas:
        out.append(f"<table><thead><tr>{h}</tr></thead><tbody>\n" + "\n".join(filas) + "\n</tbody></table>")
    else:
        out.append("<p>Ninguna evaluación válida en el directorio.</p>")
    out.append('<p class="nota"><strong>Semáforo.</strong> Rojo: cumplimiento medio de los marcos &lt; 50 % o alguna brecha P1 '
               "evaluada sin acción abierta. Ámbar: cumplimiento medio &lt; 80 %, alguna brecha P1 evaluada (con acción) o "
               "alguna acción vencida. Verde: el resto. Los controles sin evaluar puntúan como no cumplidos.</p>")
    return _doc("SMC · Panel de clientes", "\n".join(out))


def render_mitre_pagina(hoy: date, mitre: dict | None = None) -> str:
    volver = '<p class="volver"><a href="index.html">&larr; Volver al panel de clientes</a></p>'
    return _doc("SMC · Madurez MITRE ATT&CK",
                f'{volver}\n<h1>Madurez MITRE ATT&amp;CK</h1><p class="meta">Datos a {_e(hoy.isoformat())}</p>\n'
                + render_mitre(mitre if mitre is not None else datos_mitre(hoy), 2))


def render_cliente(f: Fila, mitre: dict | None = None) -> str:
    doc = render_html(f.analisis, f.registry, mitre)
    volver = '<p class="volver"><a href="index.html">&larr; Volver al panel de clientes</a></p>\n'
    doc = doc.replace('<main class="smc">\n', '<main class="smc">\n' + volver, 1)
    return doc.replace("</style>", EXTRA_CSS + "</style>", 1)


def generar(directorio: Path, salida: Path, hoy: date | None = None) -> Resultado:
    hoy = hoy or date.today()
    res = recopilar(directorio, hoy)
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    mitre = datos_mitre(hoy)   # una sola vez para todos los clientes
    for f in res.filas:
        (salida / f"{f.slug}.html").write_text(render_cliente(f, mitre), encoding="utf-8")
    (salida / "mitre.html").write_text(render_mitre_pagina(hoy, mitre), encoding="utf-8")
    (salida / "index.html").write_text(render_index(res, hoy), encoding="utf-8")
    return res
