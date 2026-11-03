"""Carga y validación de catálogos de controles."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

CATALOG_FILES = {
    "NIS2": ROOT / "frameworks" / "nis2" / "controls.yaml",
    "ENS": ROOT / "frameworks" / "ens" / "controls.yaml",
    "TRANSVERSAL": ROOT / "frameworks" / "transversal" / "controls.yaml",
    "RED": ROOT / "network" / "controls.yaml",
}

REQUIRED_FIELDS = ("id", "titulo")


@dataclass
class Control:
    id: str
    titulo: str
    framework: str
    grupo: str = ""
    extra: dict = field(default_factory=dict)


def load_catalog(framework: str) -> list[Control]:
    data = yaml.safe_load(CATALOG_FILES[framework].read_text(encoding="utf-8"))
    controls = []
    for raw in data["controls"]:
        raw = dict(raw)
        grupo = raw.pop("grupo", None) or raw.pop("dominio", "")
        controls.append(
            Control(id=raw.pop("id"), titulo=raw.pop("titulo"), framework=framework, grupo=grupo, extra=raw)
        )
    return controls


def load_all() -> dict[str, list[Control]]:
    return {fw: load_catalog(fw) for fw in CATALOG_FILES}


def validate() -> list[str]:
    """Devuelve una lista de errores (vacía si todo es correcto)."""
    errors: list[str] = []
    seen: set[str] = set()
    for fw, path in CATALOG_FILES.items():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path}: YAML inválido: {exc}")
            continue
        for i, raw in enumerate(data.get("controls", [])):
            for f in REQUIRED_FIELDS:
                if not raw.get(f):
                    errors.append(f"{fw}[{i}]: falta '{f}'")
            cid = raw.get("id")
            if cid in seen:
                errors.append(f"{fw}: ID duplicado {cid}")
            seen.add(cid)
    # Las relaciones del módulo de red deben apuntar a controles existentes
    for fw in ("RED",):
        for c in load_catalog(fw):
            for ref in c.extra.get("relacion", []) or []:
                if ref not in seen:
                    errors.append(f"{c.id}: relación a control inexistente {ref}")
    return errors
