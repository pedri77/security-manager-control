"""Métricas del SOC (MTTD/MTTA/MTTC/MTTR, SLA) y cobertura MITRE."""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

import yaml

from .catalog import ROOT

SLA_FILE = ROOT / "soc" / "sla.yaml"
UC_FILE = ROOT / "soc" / "use-cases" / "catalog.yaml"


def _ts(v: str) -> datetime | None:
    return datetime.fromisoformat(v) if v else None


def _minutes(a: datetime | None, b: datetime | None) -> float | None:
    return (b - a).total_seconds() / 60 if a and b else None


def _fmt(m: float | None) -> str:
    if m is None:
        return "—"
    return f"{m:.0f} min" if m < 120 else f"{m / 60:.1f} h"


def soc_metrics(csv_path: Path) -> dict:
    sla = yaml.safe_load(SLA_FILE.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(Path(csv_path).open(encoding="utf-8")))
    by_sev: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_sev[r["severidad"]].append(r)

    def agg(items):
        d = {"mttd": [], "mtta": [], "mttc": [], "mttr": []}
        for r in items:
            occ, det = _ts(r["occurred_at"]), _ts(r["detected_at"])
            ack, con, res = _ts(r["acknowledged_at"]), _ts(r["contained_at"]), _ts(r["resolved_at"])
            for k, v in (("mttd", _minutes(occ, det)), ("mtta", _minutes(det, ack)),
                         ("mttc", _minutes(det, con)), ("mttr", _minutes(det, res))):
                if v is not None:
                    d[k].append(v)
        return {k: (mean(v) if v else None) for k, v in d.items()}

    per_sev = {}
    for sev, items in by_sev.items():
        target = sla["severidades"].get(sev, {})
        in_sla = 0
        for r in items:
            det = _ts(r["detected_at"])
            ok = True
            for field, key in (("acknowledged_at", "ack"), ("contained_at", "contencion"), ("resolved_at", "resolucion")):
                limit = target.get(key)
                m = _minutes(det, _ts(r[field]))
                if limit is not None and m is not None and m > limit:
                    ok = False
            in_sla += ok
        per_sev[sev] = {"n": len(items), **agg(items), "sla_pct": 100 * in_sla / len(items)}

    fp = sum(r["falso_positivo"].lower() == "true" for r in rows)
    sig = [r for r in rows if r["significativo_nis2"].lower() == "true"]
    limit_h = sla["regulatorio"]["alerta_temprana_h"]
    sig_ok = sum(
        1 for r in sig
        if (m := _minutes(_ts(r["detected_at"]), _ts(r["notificado_24h_at"]))) is not None and m <= limit_h * 60
    )
    return {
        "total": len(rows),
        "global": agg(rows),
        "por_severidad": per_sev,
        "fp_pct": 100 * fp / len(rows) if rows else 0,
        "nis2_significativos": len(sig),
        "nis2_en_plazo": sig_ok,
    }


def render_soc(m: dict) -> str:
    g = m["global"]
    out = ["# Rendimiento del SOC", "",
           f"Incidentes: {m['total']} · Falsos positivos: {m['fp_pct']:.0f}% · "
           f"Notificación NIS2 24 h en plazo: {m['nis2_en_plazo']}/{m['nis2_significativos']}", "",
           f"**Global** — MTTD {_fmt(g['mttd'])} · MTTA {_fmt(g['mtta'])} · MTTC {_fmt(g['mttc'])} · MTTR {_fmt(g['mttr'])}", "",
           "| Severidad | N | MTTD | MTTA | MTTC | MTTR | % en SLA |", "|---|---|---|---|---|---|---|"]
    order = ["critica", "alta", "media", "baja"]
    for sev in sorted(m["por_severidad"], key=lambda s: order.index(s) if s in order else 99):
        s = m["por_severidad"][sev]
        out.append(f"| {sev} | {s['n']} | {_fmt(s['mttd'])} | {_fmt(s['mtta'])} | {_fmt(s['mttc'])} | {_fmt(s['mttr'])} | {s['sla_pct']:.0f}% |")
    return "\n".join(out) + "\n"


def mitre_coverage(uc_path: Path = UC_FILE, hoy=None) -> str:
    data = yaml.safe_load(Path(uc_path).read_text(encoding="utf-8"))
    activos = [u for u in data["use_cases"] if u["estado"] == "activo"]
    tecnicas = sorted({t for u in activos for t in u["mitre"]})
    por_tactica: dict[str, set] = defaultdict(set)
    for u in activos:
        por_tactica[u["tactica"]].update(u["mitre"])
    sin_probar = [u["id"] for u in activos if not u.get("ultima_prueba")]
    from . import mitre
    sin_playbook = [u["id"] for u in activos if not mitre.playbook_existe(u)]
    mad = mitre.madurez(uc_path, hoy)
    out = ["# Cobertura MITRE ATT&CK", "",
           f"Casos de uso activos: {len(activos)}/{len(data['use_cases'])} · Técnicas cubiertas: {len(tecnicas)}", "",
           "| Táctica | Técnicas |", "|---|---|"]
    out += [f"| {t} | {', '.join(sorted(v))} |" for t, v in sorted(por_tactica.items())]
    out += ["", "| Técnica | Madurez (0-5) |", "|---|---|"]
    out += [f"| {t} | {n} |" for t, n in mad["tecnicas"].items()]
    out += ["", "| Táctica | Madurez (mínimo de casos activos, 0-5) |", "|---|---|"]
    out += [f"| {t} | {n} |" for t, n in mad["tacticas"].items()]
    if mad["no_activos"]:
        out += ["", "Casos no activos (no cuentan para la táctica): "
                + ", ".join(f"{k} ({v['estado']}, nivel {v['nivel']}, {v['tactica']})" for k, v in mad["no_activos"].items())]
    out += ["", f"Sin prueba registrada: {', '.join(sin_probar) or '—'}",
            f"Sin playbook: {', '.join(sin_playbook) or '—'}"]
    return "\n".join(out) + "\n"
