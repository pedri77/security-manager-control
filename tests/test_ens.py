import warnings

import pytest

from smc import ens
from smc.catalog import load_catalog, validate


@pytest.fixture(scope="module")
def ctl():
    return {c.id: c for c in load_catalog("ENS")}


def test_73_medidas_con_categoria(ctl):
    assert len(ctl) == 73
    for c in ctl.values():
        assert c.extra["categoria_minima"] in ens.CATEGORIAS, c.id


def test_refuerzos_validos(ctl):
    for c in ctl.values():
        for cat, rs in (c.extra.get("refuerzos_por_categoria") or {}).items():
            assert cat in ens.CATEGORIAS and all(r.startswith(("R", "[R")) for r in rs), c.id


def test_solo_alta(ctl):
    c = ctl["ENS-op.cont.4"]
    assert not ens.aplica(c, "BASICA")
    assert not ens.aplica(c, "MEDIA")
    assert ens.aplica(c, "ALTA")


def test_media(ctl):
    c = ctl["ENS-op.cont.1"]
    assert not ens.aplica(c, "BASICA")
    assert ens.aplica(c, "MEDIA") and ens.aplica(c, "ALTA")


def test_basica_aplica_en_todas(ctl):
    for cat in ens.CATEGORIAS:
        assert ens.aplica(ctl["ENS-org.1"], cat)


def test_categoria_vacia_o_desconocida_es_alta_con_aviso(ctl):
    c = ctl["ENS-op.cont.4"]
    for v in ("", None, "XYZ"):
        with pytest.warns(UserWarning):
            assert ens.aplica(c, v)


def test_categoria_valida_sin_aviso(ctl):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ens.aplica(ctl["ENS-org.1"], "media")


def test_refuerzos(ctl):
    c = ctl["ENS-op.pl.1"]
    assert ens.refuerzos(c, "BASICA") == []
    assert ens.refuerzos(c, "MEDIA") == ["R1"]
    assert ens.refuerzos(c, "ALTA") == ["R2"]   # celda ALTA del BOE: «+ R2» (T21)
    assert ens.refuerzos(ctl["ENS-op.cont.4"], "BASICA") == []


def test_orden_categorias():
    assert ens.CATEGORIAS == ("BASICA", "MEDIA", "ALTA")


def test_validate_ok():
    assert validate() == []
