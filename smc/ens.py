"""Aplicabilidad de medidas ENS por categoría del sistema (RD 311/2022, Anexo II)."""
from __future__ import annotations

import warnings

# Orden creciente de exigencia. No reordenar: la comparación usa el índice.
CATEGORIAS = ("BASICA", "MEDIA", "ALTA")
DEFECTO = "ALTA"        # categoría del cliente vacía/desconocida (conservador: exige más)
MINIMA_DEFECTO = "BASICA"   # categoria_minima de la medida desconocida (conservador: aplica en todas)


def _extra(control) -> dict:
    return control.extra if hasattr(control, "extra") else control


def normalizar(categoria: str | None) -> str:
    """Devuelve la categoría en mayúsculas sin tildes; vacía/desconocida = ALTA con aviso."""
    c = (categoria or "").strip().upper().replace("Á", "A")
    if c in CATEGORIAS:
        return c
    warnings.warn(f"Categoría ENS '{categoria}' vacía o desconocida: se asume {DEFECTO}", stacklevel=3)
    return DEFECTO


def aplica(control, categoria: str | None) -> bool:
    """True si la medida aplica en la categoría dada (control: Control o dict)."""
    cat = normalizar(categoria)
    minima = _extra(control).get("categoria_minima") or "BASICA"
    if minima not in CATEGORIAS:
        minima = MINIMA_DEFECTO
    return CATEGORIAS.index(cat) >= CATEGORIAS.index(minima)


def refuerzos(control, categoria: str | None) -> list[str]:
    """Refuerzos (R1..Rn) exigibles en la categoría; [] si la medida no aplica o no tiene."""
    if not aplica(control, categoria):
        return []
    cat = normalizar(categoria)
    return list((_extra(control).get("refuerzos_por_categoria") or {}).get(cat, []) or [])
