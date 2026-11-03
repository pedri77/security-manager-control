"""Evidencias con fecha, caducidad y huella (T33).

Formato de cada elemento de `evidencias`: texto, o un mapa
`{ref, fecha: AAAA-MM-DD, caduca: AAAA-MM-DD | vigencia_dias: int, sha256: 64 hex opcional}`.
Si hay `vigencia_dias`, caduca = fecha + días (y `caduca` explícita manda si están las dos).
Una evidencia caducada avisa y se lista; no cambia la puntuación.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from pathlib import Path

VIGENTE, CADUCA_PRONTO, CADUCADA, SIN_FECHA = "vigente", "caduca_pronto", "caducada", "sin_fecha"
UMBRAL_DIAS = 30
_SHA = re.compile(r"[0-9a-fA-F]{64}")
BLOQUE = 65536


def _fecha(v):
    if isinstance(v, date):  # datetime es subclase de date
        return v if type(v) is date else v.date()
    if isinstance(v, str):
        try:
            return date.fromisoformat(v.strip())
        except ValueError:
            return None
    return None


def normalizar(e) -> dict:
    """Devuelve {ref, fecha, caduca, sha256, avisos}; el texto plano queda con fechas None."""
    avisos: list[str] = []
    if not isinstance(e, dict):
        return {"ref": "" if e is None else str(e), "fecha": None, "caduca": None, "sha256": None, "avisos": avisos}
    ref = "" if e.get("ref") is None else str(e.get("ref"))
    if not ref:
        avisos.append("evidencia sin 'ref'")
    fecha = _fecha(e.get("fecha"))
    if e.get("fecha") is not None and fecha is None:
        avisos.append(f"fecha no válida: {e.get('fecha')!r}")
    caduca = _fecha(e.get("caduca"))
    if e.get("caduca") is not None and caduca is None:
        avisos.append(f"caduca no válida: {e.get('caduca')!r}")
    if caduca is None and e.get("vigencia_dias") is not None:
        v = e.get("vigencia_dias")
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            avisos.append(f"vigencia_dias no válida: {v!r}")
        elif fecha is None:
            avisos.append("vigencia_dias sin fecha: no se puede calcular la caducidad")
        else:
            try:
                caduca = fecha + timedelta(days=v)
            except OverflowError:
                avisos.append(f"vigencia_dias fuera de rango: {v!r}")
    sha = e.get("sha256")
    if sha is not None:
        if isinstance(sha, str) and _SHA.fullmatch(sha.strip()):
            sha = sha.strip().lower()
        else:
            avisos.append("sha256 no válido (64 hex): se ignora")
            sha = None
    return {"ref": ref, "fecha": fecha, "caduca": caduca, "sha256": sha, "avisos": avisos}


def estado(e, hoy: date | None = None) -> str:
    hoy = hoy or date.today()
    c = normalizar(e)["caduca"]
    if c is None:
        return SIN_FECHA
    if c < hoy:
        return CADUCADA
    return CADUCA_PRONTO if (c - hoy).days <= UMBRAL_DIAS else VIGENTE


def todas_caducadas(evidencias, hoy: date | None = None) -> bool:
    """True si hay evidencias y todas están caducadas (el texto plano nunca caduca)."""
    if not isinstance(evidencias, list) or not evidencias:
        return False
    return all(estado(e, hoy) == CADUCADA for e in evidencias)


def _iter(assessment):
    evals = assessment.get("evaluaciones") if isinstance(assessment, dict) else None
    if not isinstance(evals, dict):
        return
    for cid, ev in evals.items():
        if isinstance(ev, dict) and isinstance(ev.get("evidencias"), list):
            for e in ev["evidencias"]:
                yield cid, e


def _ruta_segura(ref: str, base: Path):
    """(ruta, None) si `ref` es una ruta relativa que, resuelta, queda dentro de base; si no (None, motivo)."""
    if not ref or "\x00" in ref:
        return None, "ref vacía o con carácter nulo"
    if ref.startswith(("/", "\\", "~")) or re.match(r"^[A-Za-z]:", ref) or Path(ref).is_absolute():
        return None, "ruta absoluta no permitida"
    if ".." in re.split(r"[\\/]", ref):
        return None, "ruta con '..' no permitida"
    try:
        raiz = Path(base).resolve()
        p = (raiz / ref).resolve()
    except (OSError, RuntimeError, ValueError):
        return None, "ruta no resoluble"
    if not p.is_relative_to(raiz):
        return None, "la ruta sale de la base (enlace simbólico)"
    return p, None


def sha256_fichero(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while bloque := f.read(BLOQUE):
            h.update(bloque)
    return h.hexdigest()


def verificar_huellas(assessment: dict, base: Path) -> list[dict]:
    """Comprueba el sha256 de las evidencias dict que lo declaran. Cada resultado:
    {control, ref, resultado: ok | discrepancia | no_encontrada | rechazada | error, aviso}."""
    out = []
    for cid, e in _iter(assessment):
        n = normalizar(e)
        if n["sha256"] is None:
            continue
        r = {"control": cid, "ref": n["ref"], "resultado": "ok", "aviso": ""}
        p, motivo = _ruta_segura(n["ref"], base)
        if p is None:
            r.update(resultado="rechazada", aviso=f"{motivo}; no se lee")
        elif not p.is_file():
            r.update(resultado="no_encontrada", aviso="el fichero no existe en la base")
        else:
            try:
                real = sha256_fichero(p)
            except OSError as ex:
                r.update(resultado="error", aviso=f"no se pudo leer: {ex.__class__.__name__}")
            else:
                if real != n["sha256"]:
                    r.update(resultado="discrepancia", aviso="la huella no coincide con el fichero")
        out.append(r)
    return out


def _md(v) -> str:
    t = " ".join(str(v if v is not None else "").split())
    return t.replace("<", "&lt;").replace(">", "&gt;").replace("|", "\\|")


def render_markdown(assessment: dict, hoy: date | None = None, base: Path | None = None) -> str:
    """Tabla de evidencias con fecha, caducidad y estado; con `base`, añade la comprobación de huellas."""
    hoy = hoy or date.today()
    out = ["## Evidencias", "", "| Control | Evidencia | Fecha | Caduca | Estado |", "|---|---|---|---|---|"]
    filas = 0
    for cid, e in _iter(assessment):
        n = normalizar(e)
        out.append(f"| {_md(cid)} | {_md(n['ref'])} | {n['fecha'] or '—'} | {n['caduca'] or '—'} | {estado(e, hoy)} |")
        filas += 1
    if not filas:
        out.append("| — | — | — | — | — |")
    avisos = [f"{_md(c)}: {_md(a)}" for c, e in _iter(assessment) for a in normalizar(e)["avisos"]]
    if base is not None:
        avisos += [f"{_md(r['control'])} {_md(r['ref'])}: {r['resultado']}, {_md(r['aviso'])}"
                   for r in verificar_huellas(assessment, base) if r["resultado"] != "ok"]
    if avisos:
        out += ["", "### Avisos de evidencias", ""] + [f"- {a}" for a in avisos]
    return "\n".join(out) + "\n"
