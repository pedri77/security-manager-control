"""Catálogo de feeds RSS y ecosistema de recursos (v0.5, T12).

API para T14:
    cargar_rss() -> list[dict]; cargar_ecosistema() -> list[dict]
    validar() -> list[str]            (vacía = correcto)
    a_opml(feeds=None, titulo=...) -> str   (OPML 2.0; solo feeds con url_feed)
    render_markdown() -> str
Sin red. Los feeds con url_feed null no entran en el OPML.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from .catalog import ROOT

RSS_FILE = ROOT / "resources" / "rss.yaml"
ECO_FILE = ROOT / "resources" / "ecosistema.yaml"
CATEGORIAS = ("avisos", "noticias", "vulnerabilidades", "normativa")
ESTADOS_ECO = ("publicado", "pendiente")
TIPOS_ECO = ("pages", "repo", "pendiente")
# Nunca enlazar estos repos privados (ni en feeds ni en ecosistema).
PROHIBIDOS = ("repo-privado", "repo-privado")


def _load(path: Path, clave: str) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get(clave) or [])


def cargar_rss(path: Path = RSS_FILE) -> list[dict]:
    return _load(path, "feeds")


def cargar_ecosistema(path: Path = ECO_FILE) -> list[dict]:
    return _load(path, "proyectos")


def _url_errores(etiqueta: str, url) -> list[str]:
    if url is None:
        return []
    if not isinstance(url, str) or not re.match(r"^https://[^\s]+$", url):
        return [f"{etiqueta}: URL no https válida {url!r}"]
    low = url.lower()
    return [f"{etiqueta}: enlace a repo privado ({p})" for p in PROHIBIDOS if p in low]


def validar(rss: list[dict] | None = None, eco: list[dict] | None = None) -> list[str]:
    rss = cargar_rss() if rss is None else rss
    eco = cargar_ecosistema() if eco is None else eco
    err: list[str] = []
    ids: set[str] = set()
    for f in rss:
        fid = f.get("id")
        for campo in ("id", "nombre", "organismo", "url_web", "idioma", "categoria"):
            if not f.get(campo):
                err.append(f"rss {fid or '?'}: falta '{campo}'")
        if fid in ids:
            err.append(f"rss: ID duplicado {fid}")
        ids.add(fid)
        if f.get("categoria") and f["categoria"] not in CATEGORIAS:
            err.append(f"rss {fid}: categoria no válida {f['categoria']!r}")
        if "url_feed" not in f:
            err.append(f"rss {fid}: falta 'url_feed' (null si se desconoce)")
        if not isinstance(f.get("verificado"), bool):
            err.append(f"rss {fid}: 'verificado' debe ser booleano")
        err += _url_errores(f"rss {fid} url_feed", f.get("url_feed"))
        err += _url_errores(f"rss {fid} url_web", f.get("url_web"))
    eids: set[str] = set()
    for p in eco:
        pid = p.get("id")
        for campo in ("id", "nombre", "tipo", "estado"):
            if not p.get(campo):
                err.append(f"ecosistema {pid or '?'}: falta '{campo}'")
        if pid in eids:
            err.append(f"ecosistema: ID duplicado {pid}")
        eids.add(pid)
        if p.get("tipo") and p["tipo"] not in TIPOS_ECO:
            err.append(f"ecosistema {pid}: tipo no válido {p['tipo']!r}")
        if p.get("estado") and p["estado"] not in ESTADOS_ECO:
            err.append(f"ecosistema {pid}: estado no válido {p['estado']!r}")
        if p.get("estado") == "pendiente" and p.get("url"):
            err.append(f"ecosistema {pid}: un pendiente no lleva URL")
        if p.get("estado") == "publicado" and not p.get("url"):
            err.append(f"ecosistema {pid}: publicado sin URL")
        err += _url_errores(f"ecosistema {pid}", p.get("url"))
    return err


def a_opml(feeds: list[dict] | None = None, titulo: str = "SMC - fuentes de seguridad") -> str:
    """OPML 2.0 con un outline por feed que tenga url_feed. ElementTree escapa los atributos."""
    feeds = cargar_rss() if feeds is None else feeds
    opml = ET.Element("opml", version="2.0")
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = titulo
    body = ET.SubElement(opml, "body")
    for f in feeds:
        if not f.get("url_feed"):
            continue
        ET.SubElement(body, "outline", {
            "type": "rss", "text": str(f["nombre"]), "title": str(f["nombre"]),
            "xmlUrl": str(f["url_feed"]), "htmlUrl": str(f.get("url_web") or ""),
            "category": str(f.get("categoria") or ""), "language": str(f.get("idioma") or ""),
        })
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(opml, encoding="unicode") + "\n"


def render_markdown(rss: list[dict] | None = None, eco: list[dict] | None = None) -> str:
    rss = cargar_rss() if rss is None else rss
    eco = cargar_ecosistema() if eco is None else eco
    out = ["# Recursos", "", "## Fuentes RSS", "",
           "| ID | Fuente | Organismo | Categoría | Feed | Verificado |", "|---|---|---|---|---|---|"]
    for f in rss:
        feed = f.get("url_feed") or "sin feed conocido"
        out.append(f"| {f['id']} | [{f['nombre']}]({f['url_web']}) | {f['organismo']} | {f['categoria']} | {feed} | {'sí' if f.get('verificado') else 'no'} |")
    out += ["", "## Ecosistema", ""]
    for p in eco:
        if p.get("url"):
            out.append(f"- [{p['nombre']}]({p['url']}) ({p['tipo']})")
        else:
            out.append(f"- {p['nombre']} (pendiente)")
    return "\n".join(out) + "\n"
