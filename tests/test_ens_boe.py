"""T21: el catálogo ENS coincide con la tabla del Anexo II del RD 311/2022 (BOE-A-2022-7191, consulta 2026-11-03).

TABLA es una copia independiente de la tabla del BOE (aplicabilidad BÁSICA/MEDIA/ALTA, «n.a.» = no aplica).
"""
import csv
import warnings
from pathlib import Path

import pytest

from smc import ens
from smc.catalog import load_catalog

ROOT = Path(__file__).resolve().parent.parent
N = "n.a."
# id: (dimensiones o "", BÁSICA, MEDIA, ALTA)  — «Categoría» = ""
TABLA = {
 "org.1": ("", "a", "a", "a"), "org.2": ("", "a", "a", "a"), "org.3": ("", "a", "a", "a"), "org.4": ("", "a", "a", "a"),
 "op.pl.1": ("", "a", "+R1", "+R2"), "op.pl.2": ("", "a", "+R1", "+R1+R2+R3"), "op.pl.3": ("", "a", "a", "a"),
 "op.pl.4": ("D", "a", "+R1", "+R1"), "op.pl.5": ("", N, "a", "a"),
 "op.acc.1": ("TA", "a", "+R1", "+R1"), "op.acc.2": ("CITA", "a", "a", "+R1"), "op.acc.3": ("CITA", N, "a", "+R1"),
 "op.acc.4": ("CITA", "a", "a", "a"),
 "op.acc.5": ("CITA", "+[R1 o R2 o R3 o R4]", "+[R2 o R3 o R4]+R5", "+[R2 o R3 o R4]+R5"),
 "op.acc.6": ("CITA", "+[R1 o R2 o R3 o R4]+R8+R9", "+[R1 o R2 o R3 o R4]+R5+R8+R9", "+[R1 o R2 o R3 o R4]+R5+R6+R7+R8+R9"),
 "op.exp.1": ("", "a", "a", "a"), "op.exp.2": ("", "a", "a", "a"), "op.exp.3": ("", "a", "+R1", "+R1+R2+R3"),
 "op.exp.4": ("", "a", "+R1", "+R1+R2"), "op.exp.5": ("", N, "a", "+R1"),
 "op.exp.6": ("", "a", "+R1+R2", "+R1+R2+R3+R4"), "op.exp.7": ("", "a", "+R1+R2", "+R1+R2+R3"),
 "op.exp.8": ("T", "a", "+R1+R2+R3+R4", "+R1+R2+R3+R4+R5"), "op.exp.9": ("", "a", "a", "a"),
 "op.exp.10": ("", "a", "+R1", "+R1"),
 "op.ext.1": ("", N, "a", "a"), "op.ext.2": ("", N, "a", "a"), "op.ext.3": ("", N, N, "a"), "op.ext.4": ("", N, "a", "+R1"),
 "op.nub.1": ("", "a", "+R1", "+R1+R2"),
 "op.cont.1": ("D", N, "a", "a"), "op.cont.2": ("D", N, N, "a"), "op.cont.3": ("D", N, N, "a"), "op.cont.4": ("D", N, N, "a"),
 "op.mon.1": ("", "a", "+R1", "+R1+R2"), "op.mon.2": ("", "a", "+R1+R2", "+R1+R2"),
 "op.mon.3": ("", "a", "+R1+R2", "+R1+R2+R3+R4+R5+R6"),
 "mp.if.1": ("", "a", "a", "a"), "mp.if.2": ("", "a", "a", "a"), "mp.if.3": ("", "a", "a", "a"),
 "mp.if.4": ("D", "a", "+R1", "+R1"), "mp.if.5": ("D", "a", "a", "a"), "mp.if.6": ("D", N, "a", "a"),
 "mp.if.7": ("", "a", "a", "a"),
 "mp.per.1": ("", N, "a", "a"), "mp.per.2": ("", "a", "+R1", "+R1"), "mp.per.3": ("", "a", "a", "a"), "mp.per.4": ("", "a", "a", "a"),
 "mp.eq.1": ("", "a", "+R1", "+R1"), "mp.eq.2": ("A", N, "a", "+R1"), "mp.eq.3": ("", "a", "a", "+R1+R2"),
 "mp.eq.4": ("C", "a", "+R1", "+R1"),
 "mp.com.1": ("", "a", "a", "a"), "mp.com.2": ("C", "a", "+R1", "+R1+R2+R3"), "mp.com.3": ("IA", "a", "+R1+R2", "+R1+R2+R3+R4"),
 "mp.com.4": ("", N, "+[R1 o R2 o R3]", "+[R2 o R3]+R4"),
 "mp.si.1": ("C", N, "a", "a"), "mp.si.2": ("CI", N, "a", "+R1+R2"), "mp.si.3": ("", "a", "a", "a"),
 "mp.si.4": ("", "a", "a", "a"), "mp.si.5": ("C", "a", "+R1", "+R1"),
 "mp.sw.1": ("", N, "+R1+R2+R3+R4", "+R1+R2+R3+R4"), "mp.sw.2": ("", "a", "+R1", "+R1"),
 "mp.info.1": ("", "a", "a", "a"), "mp.info.2": ("C", N, "a", "a"), "mp.info.3": ("IA", "a", "+R1+R2+R3", "+R1+R2+R3+R4"),
 "mp.info.4": ("T", N, N, "a"), "mp.info.5": ("C", "a", "a", "a"), "mp.info.6": ("D", "a", "+R1", "+R1+R2"),
 "mp.s.1": ("", "a", "a", "a"), "mp.s.2": ("", "+[R1 o R2]", "+[R1 o R2]", "+R2+R3"),
 "mp.s.3": ("", "a", "a", "+R1"), "mp.s.4": ("D", N, "a", "+R1"),
}


def _refs(cell):
    return _split(cell[1:]) if cell.startswith("+") else None


def _split(s):
    out, cur, depth = [], "", 0
    for ch in s:
        depth += ch == "["
        depth -= ch == "]"
        if ch == "+" and depth == 0:
            out.append(cur.strip()); cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return [x for x in out if x]


@pytest.fixture(scope="module")
def ctl():
    return {c.id: c for c in load_catalog("ENS")}


def test_tabla_cubre_las_73(ctl):
    assert len(TABLA) == 73
    assert set(ctl) == {"ENS-" + k for k in TABLA}


@pytest.mark.parametrize("rid", sorted(TABLA))
def test_medida_coincide_con_el_boe(ctl, rid):
    dims, *cols = TABLA[rid]
    c = ctl["ENS-" + rid]
    minima = next(ens.CATEGORIAS[i] for i, v in enumerate(cols) if v != N)
    assert c.extra["categoria_minima"] == minima
    esperado = {cat: _refs(v) for cat, v in zip(ens.CATEGORIAS, cols) if _refs(v)}
    assert (c.extra.get("refuerzos_por_categoria") or {}) == esperado
    assert list(c.extra.get("dimensiones") or []) == list(dims)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for cat, v in zip(ens.CATEGORIAS, cols):
            assert ens.aplica(c, cat) == (v != N)
            assert ens.refuerzos(c, cat) == (esperado.get(cat, []) if v != N else [])


def test_verificar_solo_en_las_que_dependen_de_dimensiones(ctl):
    for c in ctl.values():
        dep = bool(c.extra.get("dimensiones"))
        assert bool(c.extra.get("verificar")) == dep, c.id
        if dep:
            assert c.extra.get("nota"), c.id


def test_campo_dimensiones_no_rompe_el_codigo(ctl):
    c = ctl["ENS-op.cont.2"]
    assert c.extra["dimensiones"] == ["D"]
    assert ens.aplica(c, "ALTA") and not ens.aplica(c, "MEDIA")


def test_cabecera_cita_boe_y_fecha():
    cab = (ROOT / "frameworks/ens/controls.yaml").read_text(encoding="utf-8").split("framework:")[0]
    assert "https://www.boe.es/buscar/act.php?id=BOE-A-2022-7191" in cab and "2026-11-03" in cab
    assert "TODO" not in cab


def test_mapeos_apuntan_a_ids_ens_existentes(ctl):
    with (ROOT / "mappings/nis2-ens-iso27001.csv").open(encoding="utf-8") as f:
        usados = {m for r in csv.DictReader(f) for m in r["ens_medidas"].split(";") if m}
    assert usados and usados <= set(ctl), usados - set(ctl)
