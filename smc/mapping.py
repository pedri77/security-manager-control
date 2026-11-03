"""Mapeos entre marcos (NIS2 <-> ENS <-> ISO 27001:2022 Anexo A) desde el CSV."""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from .catalog import ROOT

MAPPING_CSV = ROOT / "mappings" / "nis2-ens-iso27001.csv"


def _split(v: str) -> list[str]:
    return [x.strip() for x in (v or "").split(";") if x.strip()]


@lru_cache(maxsize=8)
def _cargar(path: Path) -> tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]:
    with open(path, encoding="utf-8", newline="") as f:
        return tuple(
            (r["nis2_id"].strip(), tuple(_split(r["ens_medidas"])), tuple(_split(r["iso27001_2022_anexo_a"])))
            for r in csv.DictReader(f)
        )


def cargar(path: Path = MAPPING_CSV) -> list[tuple[str, set[str], set[str]]]:
    """Filas del CSV como (nis2_id, {ens_ids}, {iso_ids})."""
    return [(n, set(e), set(i)) for n, e, i in _cargar(Path(path))]


def equivalentes(control_id: str, path: Path = MAPPING_CSV) -> set[str]:
    """Controles equivalentes en el otro marco (NIS2 -> ENS y ENS -> NIS2)."""
    out: set[str] = set()
    for nis2, ens, _ in cargar(path):
        if control_id == nis2:
            out |= ens
        elif control_id in ens:
            out.add(nis2)
    return out


def normas_cubiertas(control_id: str, path: Path = MAPPING_CSV) -> set[str]:
    """Normas que cubre el control vía mapeo, incluida la propia: subconjunto de {NIS2, ENS, ISO27001}."""
    normas: set[str] = set()
    for nis2, ens, iso in cargar(path):
        if control_id == nis2 or control_id in ens:
            normas |= {"NIS2"} if nis2 else set()
            if ens:
                normas.add("ENS")
            if iso:
                normas.add("ISO27001")
    return normas


def nis2_sin_fila(nis2_ids, path: Path = MAPPING_CSV) -> list[str]:
    """IDs NIS2 del catálogo que no tienen fila en el CSV."""
    presentes = {n for n, _, _ in cargar(path)}
    return [i for i in nis2_ids if i not in presentes]
