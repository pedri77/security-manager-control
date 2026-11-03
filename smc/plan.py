"""Plan de acción de una evaluación (RF-08)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

ESTADOS = ("pendiente", "en_curso", "hecha", "bloqueada")


@dataclass
class Accion:
    id: str
    controles: list[str]
    accion: str
    responsable: str
    fecha_objetivo: date | None
    estado: str = "pendiente"
    avisos: list[str] = field(default_factory=list)


def _fecha(valor) -> date | None:
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        try:
            return date.fromisoformat(valor.strip())
        except ValueError:
            return None
    return None


def cargar_plan(assessment: dict) -> list[Accion]:
    """Lee `plan_accion` de la evaluación. Tolera datos incompletos con avisos en cada Accion."""
    out: list[Accion] = []
    for i, raw in enumerate((assessment or {}).get("plan_accion") or [], 1):
        avisos = []
        estado = raw.get("estado", "pendiente")
        if estado not in ESTADOS:
            avisos.append(f"estado no válido '{estado}'")
            estado = "pendiente"
        fecha = _fecha(raw.get("fecha_objetivo"))
        if fecha is None:
            avisos.append("fecha_objetivo ausente o no válida")
        controles = raw.get("controles") or []
        if isinstance(controles, str):
            controles = [controles]
        out.append(Accion(
            id=str(raw.get("id") or f"ACC-{i:02d}"),
            controles=[str(c) for c in controles],
            accion=str(raw.get("accion") or ""),
            responsable=str(raw.get("responsable") or ""),
            fecha_objetivo=fecha,
            estado=estado,
            avisos=avisos,
        ))
    return out


def vencidas(plan: list[Accion], hoy: date) -> list[Accion]:
    """Acciones no hechas con fecha_objetivo estrictamente anterior a `hoy`."""
    return [a for a in plan if a.estado != "hecha" and a.fecha_objetivo is not None and a.fecha_objetivo < hoy]


def _id(b) -> str:
    return b if isinstance(b, str) else b[0].id


def brechas_sin_accion(brechas, plan: list[Accion]) -> list[str]:
    """IDs de control en brecha que ninguna acción no-hecha cubre.

    `brechas`: IDs (str) o tuplas (Control, estado, notas) como devuelve gap.
    Una acción `hecha` no cuenta: si el control sigue en brecha, falta acción.
    """
    cubiertos = {c for a in plan if a.estado != "hecha" for c in a.controles}
    return [i for i in (_id(b) for b in brechas) if i not in cubiertos]


def render_plan_md(plan: list[Accion], hoy: date, brechas=None) -> str:
    venc = {a.id for a in vencidas(plan, hoy)}
    out = ["## Plan de acción", ""]
    if not plan:
        out.append("Sin acciones definidas.")
    else:
        out += ["| ID | Controles | Acción | Responsable | Fecha objetivo | Estado |", "|---|---|---|---|---|---|"]
        for a in sorted(plan, key=lambda x: (x.fecha_objetivo or date.max, x.id)):
            f = a.fecha_objetivo.isoformat() if a.fecha_objetivo else "—"
            est = a.estado + (" (VENCIDA)" if a.id in venc else "")
            out.append(f"| {a.id} | {', '.join(a.controles)} | {a.accion} | {a.responsable} | {f} | {est} |")
        if venc:
            out += ["", f"Acciones vencidas a {hoy.isoformat()}: {len(venc)}"]
        avisos = [f"{a.id}: {m}" for a in plan for m in a.avisos]
        if avisos:
            out += ["", "Avisos del plan:"] + [f"- {m}" for m in avisos]
    if brechas is not None:
        sin = brechas_sin_accion(brechas, plan)
        out += ["", f"### Brechas sin acción ({len(sin)})", ""]
        out += [f"- {i}" for i in sin] if sin else ["Todas las brechas tienen acción."]
    return "\n".join(out) + "\n"
