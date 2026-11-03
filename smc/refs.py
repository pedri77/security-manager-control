"""Biblioteca normativa: NIS2 completa y guías CCN-CERT enlazadas a controles."""
from __future__ import annotations

import yaml

from .catalog import ROOT, load_all

NIS2_FILE = ROOT / "normativa" / "nis2" / "nis2.yaml"
CCN_FILE = ROOT / "normativa" / "ccn-cert" / "guias.yaml"
SOC_METRICS_FILE = ROOT / "soc" / "metrics.yaml"


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def references() -> list[dict]:
    """Lista plana de referencias: {id, titulo, tipo, controles, verificado, nota}."""
    refs: list[dict] = []
    nis2 = _load(NIS2_FILE)
    for a in nis2["articulos"]:
        refs.append({"id": f"NIS2 art. {a['art']}", "titulo": f"{a['tema']} — {a['resumen']}",
                     "tipo": "Directiva 2022/2555", "controles": a.get("controles", []), "verificado": True})
    for s in nis2["reglamento_2690_anexo"]:
        refs.append({"id": f"RE 2024/2690 Anexo §{s['seccion']}", "titulo": s["tema"],
                     "tipo": "Reglamento de Ejecución", "controles": s.get("controles", []), "verificado": True})
    ccn = _load(CCN_FILE)
    for bloque, tipo in (("guias", "CCN-STIC"), ("buenas_practicas", "CCN-CERT BP"), ("instrucciones_tecnicas", "ITS / guía nacional")):
        for g in ccn.get(bloque, []):
            refs.append({"id": g["id"], "titulo": g["titulo"], "tipo": tipo, "controles": g.get("controles", []),
                         "verificado": g.get("verificado", False), "nota": g.get("nota") or g.get("estado")})
    return refs


def _matches(control_id: str, pattern: str) -> bool:
    if pattern.startswith("*"):
        return control_id.startswith(pattern[1:] + "-")
    return pattern == control_id


def refs_for(control_id: str) -> list[dict]:
    return [r for r in references() if any(_matches(control_id, p) for p in r["controles"])]


def render_refs(control_id: str) -> str:
    items = refs_for(control_id)
    out = [f"# Referencias para {control_id}", ""]
    if not items:
        return "\n".join(out + ["Sin referencias registradas."]) + "\n"
    out += ["| Referencia | Tipo | Título | Verificada |", "|---|---|---|---|"]
    for r in items:
        flag = "sí" if r["verificado"] else "pendiente"
        nota = f" ({r['nota']})" if r.get("nota") else ""
        out.append(f"| {r['id']} | {r['tipo']} | {r['titulo']}{nota} | {flag} |")
    return "\n".join(out) + "\n"


def validate_refs() -> list[str]:
    known = {c.id for cs in load_all().values() for c in cs}
    known |= {m["id"] for m in _load(SOC_METRICS_FILE)["metrics"]}
    errors = []
    for r in references():
        for p in r["controles"]:
            if p.startswith("*"):
                if not any(k.startswith(p[1:] + "-") for k in known):
                    errors.append(f"{r['id']}: comodín sin controles {p}")
            elif p not in known:
                errors.append(f"{r['id']}: control inexistente {p}")
    return errors
