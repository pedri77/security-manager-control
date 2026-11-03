from datetime import date
from pathlib import Path

import pytest
import yaml

from smc import tech

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "technologies" / "registry.template.yaml"
HOY = date(2026, 11, 3)


def test_plantilla_carga_y_evalua():
    filas = {f["id"]: f for f in tech.evaluar_tecnologias(REG)}
    assert len(filas) >= 5
    assert filas["TEC-0003"]["configuracion"] == "bastionada"
    assert filas["TEC-0002"]["madurez"] == 2
    assert all(not f["avisos"] for f in filas.values())
    assert "TEC-0005" in tech.render_evaluacion(list(filas.values()))


def test_reglas_clasificacion():
    r = tech.reglas(REG, HOY)
    assert [f["id"] for f in r["revisadas"]] == ["TEC-0003", "TEC-0004"]
    sr = {f["id"]: f for f in r["sin_revisar"]}
    assert sr["TEC-0002"]["dias_sin_revisar"] == 367 and sr["TEC-0002"]["reglas_any_any"] == 6
    assert sr["TEC-0005"]["dias_sin_revisar"] == 167  # sin_revisar por estado, no por edad
    ne = r["no_evaluables"]
    assert [f["id"] for f in ne] == ["TEC-0001"] and "consola" in ne[0]["motivo"]
    assert r["avisos"] == []
    md = tech.render_reglas(r, HOY)
    assert "**6**" in md and "No evaluables" in md and "sin acceso a la consola" in md


def test_umbral_180_dias_contraprueba():
    assert "TEC-0004" in [f["id"] for f in tech.reglas(REG, HOY)["revisadas"]]  # 94 días
    r = tech.reglas(REG, HOY, dias=30)
    assert "TEC-0004" in [f["id"] for f in r["sin_revisar"]]
    assert "TEC-0003" in [f["id"] for f in r["sin_revisar"]]  # 49 días


def test_hoy_inyectado_caduca_revision():
    r = tech.reglas(REG, date(2027, 6, 1))
    assert "TEC-0003" in [f["id"] for f in r["sin_revisar"]]


def test_no_evaluable_sin_motivo_da_aviso():
    reg = {"technologies": [{"id": "T1", "nombre": "X", "reglas": {"estado": "no_evaluable"}}]}
    r = tech.reglas(reg, HOY)
    assert r["no_evaluables"][0]["motivo"] == "SIN MOTIVO"
    assert any("sin motivo" in a for a in r["avisos"])


def test_estado_invalido_y_fecha_mala_no_rompen():
    reg = {"technologies": [{"id": "T1", "reglas": {"estado": "raro", "ultima_revision": "ayer"}}, "texto", {"id": "T2", "reglas": "x"}]}
    r = tech.reglas(reg, HOY)
    assert len(r["sin_revisar"]) == 1 and len(r["avisos"]) == 2


def test_suscripciones_plantilla():
    s = tech.suscripciones(REG, HOY, 90)
    ren = [r["id"] for r in s["renovaciones"]]
    assert ren == ["TEC-0005", "TEC-0002", "TEC-0001"]
    assert s["renovaciones"][0]["dias"] == 28
    assert [r["id"] for r in s["infrautilizadas"]] == ["TEC-0005"]
    assert s["infrautilizadas"][0]["uso_pct"] == 40.0 and s["infrautilizadas"][0]["coste_ocioso"] == 18000
    assert [r["id"] for r in s["sobredespliegue"]] == ["TEC-0004"]
    assert s["coste_por_proveedor"][("Proveedor B", "EUR")] == 13700
    md = tech.render_suscripciones(s, HOY, 90)
    assert "Infrautilizadas" in md and "Proveedor D" in md


def test_umbral_70_contraprueba():
    assert [r["id"] for r in tech.suscripciones(REG, HOY)["infrautilizadas"]] == ["TEC-0005"]
    # con umbral 95 % también entra TEC-0001 (462/500 = 92,4 %)
    ids = [r["id"] for r in tech.suscripciones(REG, HOY, umbral=0.95)["infrautilizadas"]]
    assert ids == ["TEC-0001", "TEC-0005"]
    assert tech.suscripciones(REG, HOY, umbral=0.30)["infrautilizadas"] == []


def test_ventana_renovaciones():
    assert [r["id"] for r in tech.suscripciones(REG, HOY, 30)["renovaciones"]] == ["TEC-0005"]


def test_registro_dict_y_vacio():
    assert tech.suscripciones({}, HOY)["renovaciones"] == []
    assert tech.reglas({"technologies": None}, HOY)["revisadas"] == []


def test_plantilla_sin_datos_reales_y_compatible():
    data = yaml.safe_load(REG.read_text(encoding="utf-8"))
    assert all("Proveedor" in t["suscripcion"]["proveedor"] for t in data["technologies"])
    items = tech.expiring(REG, 60, today=date(2026, 11, 2))
    assert ("TEC-0002", "Licencia") in {(i[1], i[3]) for i in items}
