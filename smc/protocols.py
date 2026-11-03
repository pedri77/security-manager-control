"""Vulnerabilidades por protocolo con fuentes oficiales (T11, v0.5).

API (para T14):
  cargar(path=None) -> dict                      protocols.yaml completo
  cargar_fuentes(path=None) -> list[dict]        sources.yaml (lista de fuentes)
  protocolos(data=None) -> list[dict]
  obtener(id, data=None) -> dict | None          búsqueda sin distinguir mayúsculas
  por_capa(data=None) -> dict[int, list[dict]]   capa OSI -> protocolos (claves ordenadas)
  render_protocolo(id, data=None) -> str         Markdown; ValueError si no existe
  dominios_permitidos(fuentes=None) -> set[str]  dominios de sources.yaml + pedri77.github.io
  validar(data=None, fuentes=None, controles=None) -> list[str]   errores (vacía = OK)

Sin red: las URLs de `consulta` son de búsqueda y no se comprueban en línea.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROTOCOLS_FILE = ROOT / "vulnerabilities" / "protocols.yaml"
SOURCES_FILE = ROOT / "vulnerabilities" / "sources.yaml"

DOMINIO_PAGES = "pedri77.github.io"
CAMPOS = ("id", "nombre", "capa_osi", "riesgos", "cwe", "mitigaciones", "controles", "attack", "consulta")
CONSULTA_MIN = ("nvd", "euvd", "cisa_kev", "cvedetails", "incibe_cert", "ccn_cert")
RE_CWE = re.compile(r"^CWE-\d+$")
RE_ATTACK = re.compile(r"^T\d{4}(\.\d{3})?$")


def cargar(path: Path | None = None) -> dict:
    return yaml.safe_load((path or PROTOCOLS_FILE).read_text(encoding="utf-8"))


def cargar_fuentes(path: Path | None = None) -> list[dict]:
    return yaml.safe_load((path or SOURCES_FILE).read_text(encoding="utf-8")).get("fuentes", [])


def protocolos(data: dict | None = None) -> list[dict]:
    return list((data or cargar()).get("protocolos", []))


def obtener(pid: str, data: dict | None = None) -> dict | None:
    for p in protocolos(data):
        if str(p.get("id", "")).lower() == str(pid).lower():
            return p
    return None


def por_capa(data: dict | None = None) -> dict[int, list[dict]]:
    capas: dict[int, list[dict]] = {}
    for p in protocolos(data):
        capas.setdefault(p["capa_osi"], []).append(p)
    return dict(sorted(capas.items()))


def dominios_permitidos(fuentes: list[dict] | None = None) -> set[str]:
    fuentes = cargar_fuentes() if fuentes is None else fuentes
    doms = {urlparse(f.get("url", "")).hostname for f in fuentes}
    doms.discard(None)
    doms.add(DOMINIO_PAGES)
    return doms


def _ids_controles() -> set[str]:
    from smc.catalog import load_all   # import local: evita ciclo si T14 enlaza catalog con protocols
    return {c.id for lista in load_all().values() for c in lista}


def _comprobar_url(url, dominios: set[str], donde: str, errores: list[str]) -> None:
    u = urlparse(str(url))
    if u.scheme != "https":
        errores.append(f"{donde}: la URL debe ser https ({url})")
    elif u.hostname not in dominios:
        errores.append(f"{donde}: dominio no permitido '{u.hostname}'")


def validar(data: dict | None = None, fuentes: list[dict] | None = None,
            controles: set[str] | None = None) -> list[str]:
    data = cargar() if data is None else data
    dominios = dominios_permitidos(fuentes)
    controles = _ids_controles() if controles is None else controles
    aprendizaje = data.get("aprendizaje") or {}
    errores: list[str] = []
    for k, v in aprendizaje.items():
        _comprobar_url((v or {}).get("url"), dominios, f"aprendizaje.{k}", errores)
    vistos: set[str] = set()
    for i, p in enumerate(data.get("protocolos") or []):
        pid = p.get("id") or f"#{i}"
        for c in CAMPOS:
            if p.get(c) in (None, "", [], {}):
                errores.append(f"{pid}: falta '{c}'")
        if pid in vistos:
            errores.append(f"{pid}: ID duplicado")
        vistos.add(pid)
        capa = p.get("capa_osi")
        if not isinstance(capa, int) or isinstance(capa, bool) or not 1 <= capa <= 7:
            errores.append(f"{pid}: capa_osi debe ser un entero 1-7 ({capa!r})")
        for c in p.get("controles") or []:
            if c not in controles:
                errores.append(f"{pid}: control inexistente {c}")
        for c in p.get("cwe") or []:
            if not RE_CWE.match(str(c)):
                errores.append(f"{pid}: CWE con formato no válido {c}")
        for t in p.get("attack") or []:
            if not RE_ATTACK.match(str(t)):
                errores.append(f"{pid}: técnica ATT&CK con formato no válido {t}")
        consulta = p.get("consulta") or {}
        for k in CONSULTA_MIN:
            if k not in consulta:
                errores.append(f"{pid}: consulta sin fuente '{k}'")
        for k, url in consulta.items():
            _comprobar_url(url, dominios, f"{pid}.consulta.{k}", errores)
        for a in p.get("aprendizaje") or []:
            if a not in aprendizaje:
                errores.append(f"{pid}: aprendizaje desconocido '{a}'")
    return errores


def render_protocolo(pid: str, data: dict | None = None) -> str:
    data = cargar() if data is None else data
    p = obtener(pid, data)
    if p is None:
        raise ValueError(f"Protocolo desconocido: {pid}")
    puertos = ", ".join(p.get("puertos") or []) or "sin puerto (capa 2/3)"
    out = [f"# {p['nombre']} (capa OSI {p['capa_osi']})", "", f"Puertos: {puertos}", ""]
    for titulo, clave in (("Riesgos típicos", "riesgos"), ("Mitigaciones", "mitigaciones")):
        out += [f"## {titulo}", ""] + [f"- {x}" for x in p.get(clave, [])] + [""]
    out += ["## Referencias", "",
            f"- CWE representativos: {', '.join(p.get('cwe', []))}",
            f"- Técnicas ATT&CK: {', '.join(p.get('attack', []))}",
            f"- Controles SMC: {', '.join(p.get('controles', []))}", "",
            "## Consultar en fuentes oficiales (URLs de búsqueda, sin CVEs concretos)", ""]
    out += [f"- {k}: {url}" for k, url in (p.get("consulta") or {}).items()]
    apr = data.get("aprendizaje") or {}
    enlaces = [apr[a] for a in p.get("aprendizaje") or [] if a in apr]
    if enlaces:
        out += ["", "## Aprender más", ""] + [f"- [{e['titulo']}]({e['url']})" for e in enlaces]
    return "\n".join(out) + "\n"
