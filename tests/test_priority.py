import csv

from smc.catalog import load_catalog
from smc.mapping import MAPPING_CSV, equivalentes, nis2_sin_fila, normas_cubiertas
from smc.priority import prioridad

NIS2 = {c.id: c for c in load_catalog("NIS2")}
ENS_IDS = {c.id for c in load_catalog("ENS")}


def test_todo_nis2_tiene_fila():
    assert nis2_sin_fila(NIS2) == []


def test_contraprueba_fila_borrada_pone_en_rojo(tmp_path):
    rows = list(csv.reader(open(MAPPING_CSV, encoding="utf-8")))
    quitada = [r for r in rows if r[0] != "NIS2-21.2.c"]
    p = tmp_path / "m.csv"
    csv.writer(open(p, "w", encoding="utf-8", newline="")).writerows(quitada)
    assert nis2_sin_fila(NIS2, p) == ["NIS2-21.2.c"]


def test_ens_del_csv_existen_en_catalogo():
    with open(MAPPING_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for m in r["ens_medidas"].split(";"):
                assert m in ENS_IDS, m
            assert r["iso27001_2022_anexo_a"]


def test_equivalentes_ambos_sentidos():
    assert "ENS-org.1" in equivalentes("NIS2-20.1")
    assert "NIS2-20.1" in equivalentes("ENS-org.1")
    assert "NIS2-21.2.a" in equivalentes("ENS-org.1")
    assert equivalentes("NO-EXISTE") == set()


def test_normas_cubiertas():
    assert normas_cubiertas("NIS2-20.1") == {"NIS2", "ENS", "ISO27001"}
    assert normas_cubiertas("NO-EXISTE") == set()


def test_orden_prioridad():
    alta, baja = NIS2["NIS2-20.1"], NIS2["NIS2-21.2.f"]
    p1, n1 = prioridad(alta, "no_implementado", {"tipo_entidad_nis2": "esencial"})
    p2, n2 = prioridad(baja, "parcial", {"tipo_entidad_nis2": "importante"})
    assert p1 > p2 and n1 == "P1" and n2 != "P1"
    assert 0 <= p2 <= p1 <= 100


def test_estado_y_entidad_pesan():
    c = NIS2["NIS2-21.2.d"]
    esc = {"tipo_entidad_nis2": "esencial"}
    assert prioridad(c, "no_implementado", esc)[0] > prioridad(c, "parcial", esc)[0]
    assert prioridad(c, "parcial", esc)[0] > prioridad(c, "parcial", {"tipo_entidad_nis2": "importante"})[0]
    assert prioridad(c, "implementado", esc) == (0.0, "P3")


def test_criticidad_por_defecto_media():
    c = NIS2["NIS2-21.2.d"]
    import copy
    sin = copy.deepcopy(c)
    sin.extra.pop("criticidad", None)
    assert prioridad(sin, "parcial", {}) == prioridad(
        type(c)(**{**c.__dict__, "extra": {**c.extra, "criticidad": "media"}}), "parcial", {}
    )
