"""T31: comparación entre evaluaciones (deltas calculados a mano sobre el par de ejemplos)."""
import copy
from datetime import date
from pathlib import Path

import yaml

from smc.compare import comparar, render_markdown

EX = Path(__file__).resolve().parent.parent / "assessments" / "examples"
HOY = date(2026, 11, 3)


def _l(p):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def par():
    return _l(EX / "historico" / "ejemplo-energia-2026-q1.yaml"), _l(EX / "ejemplo-energia.yaml")


def ids(lst):
    return [c.id for c in lst]


def test_marcos_a_mano():
    # NIS2 (15 aplicables): antes 7,5/15 = 50,0; después 8/15 = 53,3. RED (20): 3/20 = 15,0 -> 4/20 = 20,0
    c = comparar(*par(), hoy=HOY)
    m = {x.framework: x for x in c.marcos}
    assert (m["NIS2"].antes, m["NIS2"].despues, m["NIS2"].delta) == (50.0, 53.3, 3.3)
    assert (m["RED"].antes, m["RED"].despues, m["RED"].delta) == (15.0, 20.0, 5.0)
    assert m["TRANSVERSAL"].delta == 0.0
    assert "ENS" not in m


def test_controles_a_mano():
    c = comparar(*par(), hoy=HOY)
    assert ids(c.cerrados) == ["NIS2-21.2.j"]
    assert ids(c.mejoran) == ["NET-ACC-01", "NIS2-20.2", "TRV-EDR-01"]
    assert ids(c.empeoran) == ["TRV-TI-01"]
    assert ids(c.nuevas_brechas) == ["NIS2-23.notificacion"]
    assert len(c.sin_cambio) == 19
    assert (c.cerrados[0].antes, c.cerrados[0].despues) == ("parcial", "implementado")


def test_p1_madurez_y_acciones():
    c = comparar(*par(), hoy=HOY)
    assert c.p1_antes == ["NET-SEG-02", "NIS2-20.2", "NIS2-21.2.c", "NIS2-21.2.d", "NIS2-21.2.j", "TRV-EDR-01"]
    assert c.p1_despues == ["NET-SEG-02", "NIS2-21.2.c", "NIS2-21.2.d", "NIS2-23.notificacion", "TRV-TI-01"]
    # medias 21/8 = 2,62 (antes, 8 puntúan) y 27/9 = 3,00 (después, 9 puntúan)
    assert (c.madurez_antes, c.madurez_despues, c.madurez_delta) == (2.62, 3.0, 0.38)
    v = {x.id: x for x in c.verticales}
    assert v["VRT-EDR"].delta == 2 and v["VRT-FW"].delta == 0 and v["VRT-ZTNA"].antes is None
    assert c.acciones_cerradas == ["ENE-04"]
    assert c.avisos == []


def test_contraprueba_intercambio_invierte_signo_y_avisa_fechas():
    a, b = par()
    c = comparar(b, a, hoy=HOY)
    m = {x.framework: x for x in c.marcos}
    assert m["NIS2"].delta == -3.3 and m["RED"].delta == -5.0
    assert ids(c.cerrados) == ["NIS2-23.notificacion"]
    assert ids(c.nuevas_brechas) == ["NIS2-21.2.j"]
    assert ids(c.mejoran) == ["TRV-TI-01"] and set(ids(c.empeoran)) == {"NIS2-20.2", "TRV-EDR-01"}
    assert ids(c.dejan_de_evaluarse) == ["NET-ACC-01"]            # T36: antes se contaba como «empeora»
    assert c.madurez_delta == -0.38
    assert c.acciones_cerradas == []
    assert any("más antigua" in w for w in c.avisos)


def test_clientes_distintos_avisan():
    a, b = par()
    b = copy.deepcopy(b)
    b["cliente"]["nombre"] = "Otra Empresa Ejemplo, S.L."
    assert any("clientes no coinciden" in w for w in comparar(a, b, hoy=HOY).avisos)


def test_sin_fecha_avisa():
    a, b = par()
    a = copy.deepcopy(a)
    del a["cliente"]["fecha"]
    assert any("Falta la fecha en la evaluación anterior" in w for w in comparar(a, b, hoy=HOY).avisos)


def test_categoria_ens_cambia_no_comparable():
    a, b = par()
    for d, cat in ((a, "media"), (b, "alta")):
        d["cliente"]["sector_publico"] = True
        d["cliente"]["categoria_ens"] = cat
    c = comparar(a, b, hoy=HOY)
    ens = next(m for m in c.marcos if m.framework == "ENS")
    assert ens.comparable is False and "no comparable" in ens.nota
    assert any("categoría ENS cambia" in w for w in c.avisos)
    # contraprueba: misma categoría, comparable y sin aviso
    b["cliente"]["categoria_ens"] = "media"
    c2 = comparar(a, b, hoy=HOY)
    assert next(m for m in c2.marcos if m.framework == "ENS").comparable is True
    assert not any("ENS" in w for w in c2.avisos)


def test_sin_verticales_en_una_avisa_y_no_falla():
    a, b = par()
    a = copy.deepcopy(a)
    del a["verticales"]
    c = comparar(a, b, hoy=HOY)
    assert c.madurez_delta is None and any("verticales" in w for w in c.avisos)


def test_entradas_vacias_no_fallan():
    c = comparar({}, {}, hoy=HOY)
    assert c.cerrados == [] and any("Falta la fecha" in w for w in c.avisos)


def test_markdown():
    md = render_markdown(comparar(*par(), hoy=HOY))
    assert "| NIS2 | 50.0 | 53.3 | +3.3 |" in md and "NIS2-21.2.j: parcial → implementado" in md
    assert "ENE-04" in md and "2.62 → 3.00 (+0.38)" in md
    # un nombre con HTML se escapa
    a, b = par()
    b["cliente"]["nombre"] = "<script>x</script>"
    assert "<script>" not in render_markdown(comparar(a, b, hoy=HOY))


def test_historico_no_altera_dashboard():
    # el dashboard solo lee *.yaml del directorio de ejemplos, no de subcarpetas
    assert sorted(p.name for p in EX.glob("*.yaml")) == [p.name for p in sorted(EX.glob("*.yaml"))]
    assert "ejemplo-energia-2026-q1.yaml" not in [p.name for p in EX.glob("*.yaml")]
