"""Análisis de brechas a partir de una evaluación de cliente."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .catalog import Control, load_all

SCORES = {"implementado": 1.0, "parcial": 0.5, "no_implementado": 0.0}
VALID_STATES = set(SCORES) | {"no_aplica"}


@dataclass
class FrameworkResult:
    framework: str
    total: int
    aplicables: int
    puntuacion: float          # 0-100
    sin_evaluar: list[Control]
    brechas: list[tuple[Control, str, str]]   # (control, estado, notas)
    sin_evidencia: list[Control]


def frameworks_in_scope(cliente: dict) -> list[str]:
    fws = ["NIS2"]
    if cliente.get("sector_publico") or cliente.get("proveedor_sector_publico"):
        fws.append("ENS")
    fws += ["TRANSVERSAL", "RED"]
    return fws


def analyse(assessment: dict) -> tuple[dict, list[FrameworkResult], list[str]]:
    cliente = assessment.get("cliente", {})
    evals = assessment.get("evaluaciones", {}) or {}
    catalogs = load_all()
    known = {c.id for cs in catalogs.values() for c in cs}
    warnings = [f"Control desconocido en la evaluación: {cid}" for cid in evals if cid not in known]

    results = []
    for fw in frameworks_in_scope(cliente):
        controls = catalogs[fw]
        sin_evaluar, brechas, sin_evidencia = [], [], []
        score_sum, aplicables = 0.0, 0
        for c in controls:
            ev = evals.get(c.id)
            if ev is None:
                sin_evaluar.append(c)
                aplicables += 1
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
                brechas.append((c, estado, ev.get("notas", "") or ""))
            elif not ev.get("evidencias"):
                sin_evidencia.append(c)
        puntuacion = round(100 * score_sum / aplicables, 1) if aplicables else 100.0
        results.append(
            FrameworkResult(fw, len(controls), aplicables, puntuacion, sin_evaluar, brechas, sin_evidencia)
        )
    return cliente, results, warnings


def render_markdown(cliente: dict, results: list[FrameworkResult], warnings: list[str]) -> str:
    out = [f"# Informe de brechas — {cliente.get('nombre', 'cliente')}", ""]
    out.append(
        f"- Sector: {cliente.get('sector', '—')} · Entidad NIS2: {cliente.get('tipo_entidad_nis2', '—')}"
        f" · Sector público: {'sí' if cliente.get('sector_publico') else 'no'}"
        + (f" · Categoría ENS: {cliente.get('categoria_ens')}" if cliente.get("sector_publico") else "")
    )
    out.append(f"- Fecha: {cliente.get('fecha', '—')}")
    out += ["", "## Resumen", "", "| Marco | Controles | Aplicables | Cumplimiento | Brechas | Sin evaluar |", "|---|---|---|---|---|---|"]
    for r in results:
        out.append(f"| {r.framework} | {r.total} | {r.aplicables} | {r.puntuacion}% | {len(r.brechas)} | {len(r.sin_evaluar)} |")
    for r in results:
        out += ["", f"## {r.framework}"]
        if r.brechas:
            out += ["", "### Brechas", "", "| Control | Título | Estado | Notas |", "|---|---|---|---|"]
            for c, estado, notas in sorted(r.brechas, key=lambda x: SCORES[x[1]]):
                out.append(f"| {c.id} | {c.titulo} | {estado} | {notas} |")
        if r.sin_evidencia:
            out += ["", "### Implementados sin evidencia (revisar)", ""]
            out += [f"- {c.id} — {c.titulo}" for c in r.sin_evidencia]
        if r.sin_evaluar:
            out += ["", f"### Sin evaluar ({len(r.sin_evaluar)})", ""]
            out += [f"- {c.id} — {c.titulo}" for c in r.sin_evaluar]
    if warnings:
        out += ["", "## Avisos", ""] + [f"- {w}" for w in warnings]
    return "\n".join(out) + "\n"


def run(path: Path) -> str:
    assessment = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return render_markdown(*analyse(assessment))
