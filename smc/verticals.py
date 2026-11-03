"""Verticales de seguridad: catálogo (soc/verticals.yaml) y madurez 0-5 por evaluación.

API para integradores (T14):
    cargar_verticales(path=None) -> list[Vertical]
    validar_catalogo(verticales=None) -> list[str]            # errores; vacía si todo correcto
    evaluar(assessment, estricto=True) -> ResultadoVerticales
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .catalog import ROOT, load_all

VERTICALS_FILE = ROOT / "soc" / "verticals.yaml"
NO_EVALUABLE = "no_evaluable"
MADUREZ_MIN, MADUREZ_MAX = 0, 5

# Única lista de URLs permitidas en `recursos` (solo páginas públicas verificadas; nada de repos privados).
URLS_PUBLICAS = frozenset({
    "https://pedri77.github.io/edr-visual-app/",
    "https://pedri77.github.io/sase-visual-app/",
    "https://pedri77.github.io/Basic_Firewalls/",
    "https://pedri77.github.io/Basicos_Proteccion_Capas_OSI/",
    "https://pedri77.github.io/modelo_OSI/",
    "https://pedri77.github.io/ics-security-studio/",
    "https://pedri77.github.io/wafforge/",
    "https://pedri77.github.io/Basicos_email/",
    "https://github.com/pedri77/kev_dash_project",
    "https://github.com/pedri77/threat-intelligence-feeds",
})


class VerticalesError(ValueError):
    """Sección `verticales:` inválida (p. ej. `no_evaluable` sin `motivo`)."""


@dataclass
class Vertical:
    id: str
    nombre: str
    nis2: list[str]
    controles: list[str] = field(default_factory=list)
    criterios: list[str] = field(default_factory=list)
    recursos: list[dict] = field(default_factory=list)          # [{titulo, url}]
    estado_recursos: list[dict] = field(default_factory=list)   # [{proyecto, estado: pendiente}]
    agrupa: list[str] = field(default_factory=list)             # IDs de subverticales (solo VRT-NET)
    niveles: dict[int, str] = field(default_factory=dict)       # baremo: descriptor comprobable por nivel 0-5


@dataclass
class ResultadoVertical:
    id: str
    nombre: str
    nis2: list[str]
    estado: str                    # "evaluada" | "no_evaluable" | "sin_evaluar"
    madurez: int | None = None     # solo si estado == "evaluada"
    motivo: str = ""
    producto: str = ""
    notas: str = ""
    puntua: bool = True            # False: evaluada pero fuera de la media (paraguas con subverticales evaluadas)
    detallada_en: list[str] = field(default_factory=list)   # IDs de las subverticales (si no puntúa)


@dataclass
class MedidaNIS2:
    medida: str
    madurez: float | None          # media de las verticales evaluadas; None si ninguna
    verticales: list[str]          # IDs que puntúan en esta medida
    no_evaluables: list[str]       # IDs no evaluables (no puntúan)
    sin_evaluar: list[str]         # IDs sin dato


@dataclass
class ResultadoVerticales:
    verticales: list[ResultadoVertical]
    por_nis2: dict[str, MedidaNIS2]
    madurez_media: float | None    # media de las verticales que puntúan
    no_evaluables: list[ResultadoVertical]
    sin_evaluar: list[ResultadoVertical]
    warnings: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)   # solo con estricto=False


def cargar_verticales(path: Path | None = None) -> list[Vertical]:
    data = yaml.safe_load(Path(path or VERTICALS_FILE).read_text(encoding="utf-8"))
    out = []
    for raw in data["verticals"]:
        out.append(Vertical(
            id=raw["id"], nombre=raw["nombre"], nis2=list(raw.get("nis2") or []),
            controles=list(raw.get("controles") or []), criterios=list(raw.get("criterios") or []),
            recursos=[dict(r) for r in raw.get("recursos") or []],
            estado_recursos=[dict(r) for r in raw.get("estado_recursos") or []],
            agrupa=list(raw.get("agrupa") or []),
            niveles={(int(k) if str(k).isdigit() else -1): str(x) for k, x in (raw.get("niveles") or {}).items()},
        ))
    return out


def validar_catalogo(verticales: list[Vertical] | None = None) -> list[str]:
    """Errores del catálogo: IDs duplicados, medidas NIS2 o controles inexistentes, URLs fuera de la lista pública."""
    verticales = verticales if verticales is not None else cargar_verticales()
    catalogos = load_all()
    conocidos = {c.id for cs in catalogos.values() for c in cs}
    nis2 = {c.id for c in catalogos["NIS2"]}
    ids = [v.id for v in verticales]
    errores = []
    for v in verticales:
        if ids.count(v.id) > 1:
            errores.append(f"{v.id}: ID de vertical duplicado")
        if not v.criterios:
            errores.append(f"{v.id}: sin criterios")
        if sorted(v.niveles) != list(range(MADUREZ_MIN, MADUREZ_MAX + 1)):
            errores.append(f"{v.id}: el baremo debe tener 6 niveles (0-5), tiene {sorted(v.niveles)}")
        elif any(not d.strip() for d in v.niveles.values()):
            errores.append(f"{v.id}: hay niveles del baremo sin descriptor")
        for m in v.nis2:
            if m not in nis2:
                errores.append(f"{v.id}: medida NIS2 inexistente {m}")
        for c in v.controles:
            if c not in conocidos:
                errores.append(f"{v.id}: control inexistente {c}")
        for h in v.agrupa:
            if h not in ids:
                errores.append(f"{v.id}: agrupa una vertical inexistente {h}")
        for r in v.recursos:
            if not isinstance(r, dict) or not r.get("titulo") or r.get("url") not in URLS_PUBLICAS:
                url = r.get("url") if isinstance(r, dict) else r
                errores.append(f"{v.id}: recurso con URL fuera de la lista pública: {url}")
        for e in v.estado_recursos:
            if not isinstance(e, dict) or not e.get("proyecto") or e.get("estado") != "pendiente" or "url" in e:
                errores.append(f"{v.id}: estado_recursos debe ser {{proyecto, estado: pendiente}} sin URL")
    return errores


def _parse(vid: str, ent, errores: list[str]) -> tuple[str, int | None, str, str, str]:
    """Devuelve (estado, madurez, motivo, producto, notas); si es inválida registra el error y queda sin evaluar."""
    if not isinstance(ent, dict):
        errores.append(f"{vid}: la entrada no es un mapa")
        return "sin_evaluar", None, "", "", ""
    producto = str(ent.get("producto") or "")
    notas = str(ent.get("notas") or "")
    motivo = str(ent.get("motivo") or "").strip()
    m = ent.get("madurez")
    if m == NO_EVALUABLE:
        if not motivo:
            errores.append(f"{vid}: no_evaluable exige 'motivo'")
            return "sin_evaluar", None, "", producto, notas
        return "no_evaluable", None, motivo, producto, notas
    if isinstance(m, bool) or not isinstance(m, int) or not MADUREZ_MIN <= m <= MADUREZ_MAX:
        errores.append(f"{vid}: madurez no válida {m!r} (entero 0-5 o 'no_evaluable')")
        return "sin_evaluar", None, "", producto, notas
    return "evaluada", m, motivo, producto, notas


def evaluar(assessment: dict, estricto: bool = True, verticales: list[Vertical] | None = None) -> ResultadoVerticales:
    """Lee la sección opcional `verticales:` y agrega la madurez por medida NIS2 21.2.

    estricto=True lanza VerticalesError ante entradas inválidas (p. ej. no_evaluable sin motivo);
    estricto=False las deja en `errores` y esa vertical cuenta como sin evaluar.
    Sección ausente = todo sin evaluar, sin avisos. VRT-ID desconocido = aviso, se ignora.
    """
    verticales = verticales if verticales is not None else cargar_verticales()
    warnings: list[str] = []
    errores: list[str] = []
    seccion = assessment.get("verticales") if isinstance(assessment, dict) else None
    if seccion is not None and not isinstance(seccion, dict):
        warnings.append("'verticales' no es un mapa: se ignora")
        seccion = None
    seccion = seccion or {}
    conocidos = {v.id for v in verticales}
    warnings += [f"Vertical desconocida en la evaluación: {k}" for k in seccion if k not in conocidos]

    res: list[ResultadoVertical] = []
    for v in verticales:
        if v.id in seccion:
            estado, madurez, motivo, producto, notas = _parse(v.id, seccion[v.id], errores)
        else:
            estado, madurez, motivo, producto, notas = "sin_evaluar", None, "", "", ""
        res.append(ResultadoVertical(v.id, v.nombre, list(v.nis2), estado, madurez, motivo, producto, notas))
    if errores and estricto:
        raise VerticalesError("; ".join(errores))

    por_id = {r.id: r for r in res}
    # VRT-NET (paraguas) no puntúa si alguno de sus subverticales sí: evita doble cómputo
    excluidas = {
        v.id for v in verticales
        if v.agrupa and any(por_id[h].estado == "evaluada" for h in v.agrupa if h in por_id)
    }

    medidas: dict[str, MedidaNIS2] = {}
    for r in res:
        for m in r.nis2:
            med = medidas.setdefault(m, MedidaNIS2(m, None, [], [], []))
            if r.id in excluidas:
                continue
            destino = {"evaluada": med.verticales, "no_evaluable": med.no_evaluables, "sin_evaluar": med.sin_evaluar}
            destino[r.estado].append(r.id)
    for med in medidas.values():
        if med.verticales:
            med.madurez = round(sum(por_id[i].madurez for i in med.verticales) / len(med.verticales), 2)
    for v in verticales:
        if v.id in excluidas:
            r = por_id[v.id]
            r.puntua = False
            r.detallada_en = [h for h in v.agrupa if h in por_id]
    puntuan = [r for r in res if r.estado == "evaluada" and r.id not in excluidas]
    media = round(sum(r.madurez for r in puntuan) / len(puntuan), 2) if puntuan else None
    return ResultadoVerticales(
        verticales=res, por_nis2=dict(sorted(medidas.items())), madurez_media=media,
        no_evaluables=[r for r in res if r.estado == "no_evaluable"],
        sin_evaluar=[r for r in res if r.estado == "sin_evaluar"],
        warnings=warnings, errores=errores,
    )
