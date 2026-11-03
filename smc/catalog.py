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
CATEGORIAS_ENS = ("BASICA", "MEDIA", "ALTA")   # igual que smc.ens.CATEGORIAS (un test lo comprueba)


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
            if fw == "ENS":
                minima = raw.get("categoria_minima")
                if minima is not None and minima not in CATEGORIAS_ENS:
                    errors.append(f"{cid}: categoria_minima no válida '{minima}' (BASICA, MEDIA o ALTA)")
                for cat in (raw.get("refuerzos_por_categoria") or {}):
                    if cat not in CATEGORIAS_ENS:
                        errors.append(f"{cid}: refuerzos_por_categoria con categoría no válida '{cat}'")
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


UC_ESTADOS = ("activo", "en_desarrollo", "propuesto", "retirado")
UC_DETECCION = ("sin", "regla", "probada")


def validar_casos_uso(uc_path: Path | None = None, root: Path | None = None,
                      verticales: set[str] | None = None) -> list[str]:
    """Casos de uso: IDs únicos, técnicas Txxxx, deteccion válida, playbook existente, vertical existente."""
    import re
    from . import mitre
    from .verticals import cargar_verticales
    uc_path = uc_path or mitre.UC_FILE
    root = root or ROOT
    if verticales is None:
        verticales = {v.id for v in cargar_verticales()}
    data = yaml.safe_load(Path(uc_path).read_text(encoding="utf-8")) or {}
    errores, vistos = [], set()
    for i, u in enumerate(data.get("use_cases") or []):
        uid = u.get("id") if isinstance(u, dict) else None
        if not uid:
            errores.append(f"use_cases[{i}]: falta 'id'")
            continue
        if uid in vistos:
            errores.append(f"{uid}: ID de caso de uso duplicado")
        vistos.add(uid)
        if u.get("estado") not in UC_ESTADOS:
            errores.append(f"{uid}: estado no válido '{u.get('estado')}'")
        if u.get("deteccion", "sin") not in UC_DETECCION:
            errores.append(f"{uid}: deteccion no válida '{u.get('deteccion')}'")
        tecnicas = u.get("mitre")
        if not tecnicas or not isinstance(tecnicas, list):
            errores.append(f"{uid}: sin técnicas ATT&CK")
        else:
            errores += [f"{uid}: técnica ATT&CK no válida '{t}'" for t in tecnicas
                        if not re.fullmatch(r"T\d{4}(\.\d{3})?", str(t))]
        if not u.get("tactica"):
            errores.append(f"{uid}: sin táctica")
        pb = u.get("playbook")
        if u.get("estado") != "retirado" and not (pb and (Path(root) / pb).is_file()):
            errores.append(f"{uid}: playbook inexistente '{pb}'")
        if u.get("vertical") and u["vertical"] not in verticales:
            errores.append(f"{uid}: vertical inexistente {u['vertical']}")
    return errores


def validar_v05() -> list[str]:
    """Validaciones de la ola 5: verticales, protocolos/fuentes, RSS/ecosistema, casos de uso y verticales referenciadas."""
    from . import protocols, resources
    from .verticals import cargar_verticales, validar_catalogo
    vs = cargar_verticales()
    ids = {v.id for v in vs}
    errores = [f"verticales: {e}" for e in validar_catalogo(vs)]
    errores += [f"protocolos: {e}" for e in protocols.validar()]
    errores += [f"recursos: {e}" for e in resources.validar()]
    errores += [f"casos de uso: {e}" for e in validar_casos_uso(verticales=ids)]
    errores += [f"RSS {f.get('id')}: vertical inexistente {f['vertical']}"
                for f in resources.cargar_rss() if f.get("vertical") and f["vertical"] not in ids]
    reg = ROOT / "technologies" / "registry.template.yaml"
    if reg.is_file():
        from .tech import _tecnologias
        errores += [f"tecnologías {t.get('id')}: vertical inexistente {t['vertical']}"
                    for t in _tecnologias(reg) if t.get("vertical") and t["vertical"] not in ids]
    return errores


def validar_v07() -> list[str]:
    """Validaciones de la ola 13: catálogo RIA (`frameworks/ai-act/`) y plantillas de IA, pentest, purple team y PMO."""
    from . import ai_act, offensive, pmo
    errores = [f"ia: {e}" for e in ai_act.validar_catalogo()]
    errores += [f"ia: plantilla de inventario: {e}" for e in ai_act.validar_inventario(ai_act.INVENTARIO_TEMPLATE)]
    ofe = offensive.OFFENSIVE_DIR
    errores += [f"pentest: plantilla: {e}" for e in offensive.validar_pentest(ofe / "pentest.template.yaml")]
    errores += [f"purple: plantilla: {e}" for e in offensive.validar_purple(ofe / "purple.template.yaml")]
    for ej, validar in ((ofe / "examples" / "ejemplo-pentest.yaml", offensive.validar_pentest),
                        (ofe / "examples" / "ejemplo-purple.yaml", offensive.validar_purple)):
        errores += [f"{ej.name}: {e}" for e in validar(ej)]
    plantilla = ROOT / "pmo" / "proyecto.template.yaml"
    errores += [f"pmo: plantilla: {a}" for a in pmo.cargar_proyecto(plantilla).avisos]
    return errores
