"""Registro de tecnologías (caducidades) y seguimiento de vulnerabilidades."""
from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import yaml

from .catalog import ROOT

POLICY_FILE = ROOT / "vulnerabilities" / "policy.yaml"


def _d(v) -> date | None:
    if not v:
        return None
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def expiring(registry: Path, days: int = 90, today: date | None = None) -> list[tuple[date, str, str, str]]:
    today = today or date.today()
    limit = today + timedelta(days=days)
    data = yaml.safe_load(Path(registry).read_text(encoding="utf-8"))
    items = []
    for t in data["technologies"]:
        cands = [
            ("Licencia", _d((t.get("licencia") or {}).get("vence"))),
            ("Fin de soporte", _d((t.get("soporte_fabricante") or {}).get("fin_soporte"))),
            ("Fin de vida", _d((t.get("soporte_fabricante") or {}).get("fin_vida"))),
        ]
        cands += [(f"Certificado {c.get('cn')}", _d(c.get("vence"))) for c in t.get("certificados") or []]
        for tipo, d in cands:
            if d and d <= limit:
                items.append((d, t["id"], t["nombre"], tipo))
        lic = t.get("licencia") or {}
        if lic.get("contratadas") and lic.get("desplegadas", 0) > lic["contratadas"]:
            items.append((today, t["id"], t["nombre"], "Sobredespliegue de licencias"))
    return sorted(items)


def render_expiring(items, days: int, today: date | None = None) -> str:
    today = today or date.today()
    out = [f"# Caducidades en los próximos {days} días", "", "| Fecha | Días | Tecnología | Elemento |", "|---|---|---|---|"]
    for d, tid, name, tipo in items:
        delta = (d - today).days
        flag = "VENCIDO" if delta < 0 else str(delta)
        out.append(f"| {d} | {flag} | {tid} {name} | {tipo} |")
    if not items:
        out.append("| — | — | Sin caducidades | — |")
    return "\n".join(out) + "\n"


def vulns(tracker: Path, today: date | None = None) -> str:
    today = today or date.today()
    policy = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    sla = policy["sla_remediacion_dias"]
    rows = list(csv.DictReader(Path(tracker).open(encoding="utf-8")))
    abiertas = [r for r in rows if r["estado"] != "remediada"]
    out = ["# Vulnerabilidades", "", f"Total: {len(rows)} · Abiertas: {len(abiertas)}", "",
           "| CVE | Tecnología | Sev. | KEV | Expuesta | Días abierta | SLA | Estado |", "|---|---|---|---|---|---|---|---|"]
    vencidas = 0
    for r in sorted(abiertas, key=lambda r: list(sla).index(r["severidad"]) if r["severidad"] in sla else 99):
        dias = (today - date.fromisoformat(r["detectado"])).days
        limite = sla.get(r["severidad"])
        estado_sla = "VENCIDO" if limite is not None and dias > limite else "ok"
        vencidas += estado_sla == "VENCIDO"
        out.append(f"| {r['cve']} | {r['tecnologia_id']} | {r['severidad']} | {r['kev']} | {r['expuesto_internet']} | {dias} | {estado_sla} ({limite} d) | {r['estado']} |")
    out += ["", f"Fuera de SLA: {vencidas}"]
    return "\n".join(out) + "\n"
