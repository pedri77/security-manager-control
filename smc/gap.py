"""Análisis de brechas a partir de una evaluación de cliente."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .catalog import Control, load_all

SCORES = {"implementado": 1.0, "parcial": 0.5, "no_implementado": 0.0}
VALID_STATES = set(SCORES) | {"no_aplica"}


from datetime import date
from typing import NamedTuple
import warnings as _warnings

from . import ens as _ens
from . import mapping as _mapping
from . import plan as _plan
from .priority import prioridad


class Brecha(NamedTuple):
    """Brecha evaluada. Los 3 primeros campos coinciden con la tupla histórica (control, estado, notas)."""
    control: Control
    estado: str
    notas: str
    puntuacion: float = 0.0
    nivel: str = "P3"
    refuerzos: tuple = ()


@dataclass
class SinEvaluar:
    control: Control
    puntuacion: float
    nivel: str
    heredado_de: list[tuple[str, str]]   # [(id_equivalente, estado)] ya evaluados; sugerencia, no puntúa
    refuerzos: tuple = ()


@dataclass
class FrameworkResult:
    framework: str
    total: int
    aplicables: int
    puntuacion: float          # 0-100
    sin_evaluar: list[Control]
    brechas: list[Brecha]      # ordenadas por puntuación descendente
    sin_evidencia: list[Control]
    no_aplican: list[Control] = field(default_factory=list)       # ENS: no aplican a la categoría
    sin_evaluar_detalle: list[SinEvaluar] = field(default_factory=list)  # misma lista que sin_evaluar, con prioridad


@dataclass
class Analisis:
    """Resultado estructurado de `analyse`. Iterable como (cliente, results, warnings) por compatibilidad."""
    cliente: dict
    results: list[FrameworkResult]
    warnings: list[str]
    hoy: date
    categoria_ens: str | None          # normalizada; None si ENS fuera de alcance
    plan: list[_plan.Accion]
    vencidas: list[_plan.Accion]
    p1_sin_accion: list[str]           # IDs de brechas P1 que ninguna acción abierta cubre
    brechas_sin_accion: list[str]      # IDs de todas las brechas sin acción

    def __iter__(self):
        return iter((self.cliente, self.results, self.warnings))


def frameworks_in_scope(cliente: dict) -> list[str]:
    fws = ["NIS2"]
    if cliente.get("sector_publico") or cliente.get("proveedor_sector_publico"):
        fws.append("ENS")
    fws += ["TRANSVERSAL", "RED"]
    return fws


def _heredado(control: Control, evals: dict) -> list[tuple[str, str]]:
    out = []
    for eq in sorted(_mapping.equivalentes(control.id)):
        estado = (evals.get(eq) or {}).get("estado")
        if estado in SCORES:
            out.append((eq, estado))
    return out


def analyse(assessment: dict, hoy: date | None = None) -> Analisis:
    hoy = hoy or date.today()
    cliente = assessment.get("cliente", {})
    evals = assessment.get("evaluaciones", {}) or {}
    catalogs = load_all()
    known = {c.id for cs in catalogs.values() for c in cs}
    warnings = [f"Control desconocido en la evaluación: {cid}" for cid in evals if cid not in known]

    scope = frameworks_in_scope(cliente)
    categoria = None
    if "ENS" in scope:
        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always")
            categoria = _ens.normalizar(cliente.get("categoria_ens"))
        warnings += [str(w.message) for w in caught]

    results = []
    for fw in scope:
        controls = catalogs[fw]
        sin_evaluar, brechas, sin_evidencia, no_aplican, detalle = [], [], [], [], []
        score_sum, aplicables = 0.0, 0
        for c in controls:
            if fw == "ENS" and not _ens.aplica(c, categoria):
                no_aplican.append(c)
                continue
            ref = tuple(_ens.refuerzos(c, categoria)) if fw == "ENS" else ()
            ev = evals.get(c.id)
            if ev is None:
                sin_evaluar.append(c)
                aplicables += 1
                p, n = prioridad(c, None, cliente)
                detalle.append(SinEvaluar(c, p, n, _heredado(c, evals), ref))
                continue
            estado = ev.get("estado")
            if estado not in VALID_STATES:
                warnings.append(f"{c.id}: estado no válido '{estado}'")
                continue
            if estado == "no_aplica":
                continue
            aplicables += 1
            score_sum += SCORES[estado]
            if estado != "implementado":
                p, n = prioridad(c, estado, cliente)
                brechas.append(Brecha(c, estado, ev.get("notas", "") or "", p, n, ref))
            elif not ev.get("evidencias"):
                sin_evidencia.append(c)
        puntuacion = round(100 * score_sum / aplicables, 1) if aplicables else 100.0
        brechas.sort(key=lambda b: (-b.puntuacion, b.control.id))
        detalle.sort(key=lambda d: (-d.puntuacion, d.control.id))
        results.append(FrameworkResult(fw, len(controls), aplicables, puntuacion, sin_evaluar, brechas,
                                       sin_evidencia, no_aplican, detalle))

    plan = _plan.cargar_plan(assessment)
    todas = [b for r in results for b in r.brechas]
    sin_accion = _plan.brechas_sin_accion(todas, plan)
    p1 = [b.control.id for b in todas if b.nivel == "P1" and b.control.id in set(sin_accion)]
    p1.sort(key=lambda i: next(-b.puntuacion for b in todas if b.control.id == i))
    return Analisis(cliente, results, warnings, hoy, categoria, plan, _plan.vencidas(plan, hoy), p1, sin_accion)


def _plan_section(an: Analisis) -> str:
    todas = [b for r in an.results for b in r.brechas]
    md = _plan.render_plan_md(an.plan, an.hoy, todas)
    if an.p1_sin_accion:
        md += (f"\n**AVISO: {len(an.p1_sin_accion)} brecha(s) P1 sin acción:** "
               + ", ".join(an.p1_sin_accion) + "\n")
    return md


def render_markdown(an: Analisis | dict, results=None, warnings=None) -> str:
    if not isinstance(an, Analisis):   # compatibilidad con la firma antigua (cliente, results, warnings)
        an = Analisis(an, results, warnings or [], date.today(), None, [], [], [], [])
    cliente, results, warnings = an.cliente, an.results, an.warnings
    out = [f"# Informe de brechas — {cliente.get('nombre', 'cliente')}", ""]
    out.append(
        f"- Sector: {cliente.get('sector', '—')} · Entidad NIS2: {cliente.get('tipo_entidad_nis2', '—')}"
        f" · Sector público: {'sí' if cliente.get('sector_publico') else 'no'}"
        + (f" · Categoría ENS: {an.categoria_ens or cliente.get('categoria_ens')}" if cliente.get("sector_publico") else "")
    )
    out.append(f"- Fecha: {cliente.get('fecha', '—')}")
    out += ["", "## Resumen", "", "| Marco | Controles | Aplicables | Cumplimiento | Brechas | Sin evaluar | No aplican |",
            "|---|---|---|---|---|---|---|"]
    for r in results:
        out.append(f"| {r.framework} | {r.total} | {r.aplicables} | {r.puntuacion}% | {len(r.brechas)} | "
                   f"{len(r.sin_evaluar)} | {len(r.no_aplican)} |")
    for r in results:
        out += ["", f"## {r.framework}"]
        if r.brechas:
            out += ["", "### Brechas (por prioridad)", "", "| P | Control | Título | Estado | Refuerzos ENS | Notas |",
                    "|---|---|---|---|---|---|"]
            for b in r.brechas:
                out.append(f"| {b.nivel} | {b.control.id} | {b.control.titulo} | {b.estado} | "
                           f"{', '.join(b.refuerzos) or '—'} | {b.notas} |")
        if r.sin_evidencia:
            out += ["", "### Implementados sin evidencia (revisar)", ""]
            out += [f"- {c.id} — {c.titulo}" for c in r.sin_evidencia]
        if r.sin_evaluar_detalle:
            out += ["", f"### Sin evaluar ({len(r.sin_evaluar)})", ""]
            for d in r.sin_evaluar_detalle:
                line = f"- {d.nivel} · {d.control.id} — {d.control.titulo}"
                if d.refuerzos:
                    line += f" · refuerzos: {', '.join(d.refuerzos)}"
                if d.heredado_de:
                    line += " · heredado (sugerencia, no puntúa): " + ", ".join(f"{i} {e}" for i, e in d.heredado_de)
                out.append(line)
        if r.no_aplican:
            out += ["", f"### No aplican a la categoría {an.categoria_ens} ({len(r.no_aplican)})", ""]
            out += [f"- {c.id} — {c.titulo} (mínima {c.extra.get('categoria_minima', '—')})" for c in r.no_aplican]
    out += ["", _plan_section(an).rstrip("\n")]
    if warnings:
        out += ["", "## Avisos", ""] + [f"- {w}" for w in warnings]
    return "\n".join(out) + "\n"


def _load(path: Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def run(path: Path, hoy: date | None = None) -> str:
    return render_markdown(analyse(_load(path), hoy))


def run_plan(path: Path, hoy: date | None = None) -> str:
    return _plan_section(analyse(_load(path), hoy))
