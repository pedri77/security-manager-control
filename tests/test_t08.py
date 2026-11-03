"""T08: endurecimiento de v0.4 (hallazgos 1-12 de ola-3-revisor-ola)."""
import copy
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest
import yaml

import smc.ens as ens
from smc import __version__
from smc.catalog import load_catalog, validate
from smc.cli import main
from smc.dashboard import recopilar
from smc.gap import analyse, render_markdown
from smc.plan import brechas_sin_accion, cargar_plan
from smc.priority import prioridad
from smc.report_html import render_html

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "assessments" / "examples"
HOY = date(2026, 11, 3)
NIS2 = {c.id: c for c in load_catalog("NIS2")}


@pytest.fixture
def ass():
    return yaml.safe_load((EX / "ejemplo-energia.yaml").read_text(encoding="utf-8"))


def nis2(an):
    return next(r for r in an.results if r.framework == "NIS2")


# 1. estado no válido = sin evaluar (aplicable, 0), con aviso
def test_h1_estado_invalido_cuenta_como_sin_evaluar(ass):
    base = nis2(analyse(ass, HOY))
    cid = next(i for i, e in ass["evaluaciones"].items() if i.startswith("NIS2-") and e["estado"] == "implementado")
    ass["evaluaciones"][cid]["estado"] = "implementdo"   # errata
    an = analyse(ass, HOY)
    r = nis2(an)
    assert r.aplicables == base.aplicables                      # no sale del denominador
    assert r.puntuacion < base.puntuacion                       # puntúa 0, no se infla
    assert cid in [c.id for c in r.sin_evaluar]
    assert any(cid in w and "no válido" in w for w in an.warnings)


# 2. verificar señalado en informes y aviso en el resumen
def test_h2_verificar_marcado_en_md_y_html():
    a = yaml.safe_load((EX / "ejemplo-ayuntamiento.yaml").read_text(encoding="utf-8"))
    an = analyse(a, HOY)
    assert len(an.ens_verificar) == 28   # tras T21 (BOE): solo las dependientes de dimensión
    md, html = render_markdown(an), render_html(an)
    for doc in (md, html):
        assert "contrastadas con el Anexo II" in doc and "(verificar)" in doc
    assert "ENS-op.cont.2 (verificar)" in md       # marca en la lista de «no aplican» / sin evaluar
    # contraprueba: sin ENS en alcance no hay aviso
    a["cliente"]["sector_publico"] = False
    a["cliente"]["proveedor_sector_publico"] = False
    an2 = analyse(a, HOY)
    assert an2.ens_verificar == [] and "contrastadas con el Anexo II" not in render_markdown(an2)


# 3. .gitignore
def test_h3_gitignore_ignora_html_y_dashboard():
    if shutil.which("git") is None:
        pytest.skip("git no disponible")
    for ruta in ("informe.html", "dashboard/index.html", "sub/x.html"):
        r = subprocess.run(["git", "check-ignore", "-q", ruta], cwd=ROOT)
        assert r.returncode == 0, ruta
    r = subprocess.run(["git", "check-ignore", "-q", "README.md"], cwd=ROOT)   # contraprueba
    assert r.returncode == 1


# 4. recalibración de prioridad
def _c(crit):
    c = copy.deepcopy(NIS2["NIS2-21.2.d"])
    c.extra["criticidad"] = crit
    return c


def test_h4_media_no_esencial_sin_cobertura_es_p2(monkeypatch):
    import smc.priority as pr
    monkeypatch.setattr(pr, "normas_cubiertas", lambda _id: {"NIS2"})
    for ent in ("importante", "no_obligada", ""):
        assert prioridad(_c("media"), "no_implementado", {"tipo_entidad_nis2": ent})[1] == "P2", ent
    # contraprueba: esencial sí es P1; alta en esencial P1
    assert prioridad(_c("media"), "no_implementado", {"tipo_entidad_nis2": "esencial"})[1] == "P1"
    assert prioridad(_c("alta"), "no_implementado", {"tipo_entidad_nis2": "esencial"})[1] == "P1"
    # contraprueba: con la fórmula antigua (60/20/10/10, P1>=70) media/importante sería P1
    assert 60 + 20 * 0.5 + 10 * 0.5 >= 70


# 5 y 6. op.cont.2/3 con verificar; cifra
def test_h5_h6_cont_verificar_y_cifra():
    ens_c = {c.id: c for c in load_catalog("ENS")}
    assert ens_c["ENS-op.cont.2"].extra.get("verificar") and ens_c["ENS-op.cont.3"].extra.get("verificar")
    assert sum(1 for c in ens_c.values() if c.extra.get("verificar")) == 28   # T21; README/PRD los actualiza T22


# 7. categoria_minima desconocida
def test_h7_minima_desconocida_es_basica_y_validate_la_detecta(tmp_path, monkeypatch):
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for cat in ens.CATEGORIAS:
            assert ens.aplica({"categoria_minima": "RARA"}, cat)       # BASICA: aplica en todas
    # contraprueba: antes se trataba como ALTA, no aplicaba en BASICA
    assert not ens.aplica({"categoria_minima": "ALTA"}, "BASICA")
    import smc.catalog as cat_mod
    malo = tmp_path / "ens.yaml"
    malo.write_text("controls:\n  - {id: ENS-x.1, titulo: t, categoria_minima: RARA}\n", encoding="utf-8")
    monkeypatch.setitem(cat_mod.CATALOG_FILES, "ENS", malo)
    errs = validate()
    assert any("categoria_minima no válida 'RARA'" in e for e in errs)
    monkeypatch.undo()
    assert validate() == []
    assert cat_mod.CATEGORIAS_ENS == ens.CATEGORIAS


# 8. entradas mal formadas
def test_h8_entradas_mal_formadas_dan_aviso(ass):
    ass["plan_accion"] = ["arreglar todo", {"id": "A", "controles": 5, "estado": "hecha", "fecha_objetivo": "2026-12-01"}]
    ass["evaluaciones"]["NIS2-20.1"] = "implementado"
    ass["cliente"] = None
    an = analyse(ass, HOY)
    md = render_markdown(an)
    assert "mal formada" in md and "entrada mal formada" in md
    assert any("NIS2-20.1" in w for w in an.warnings)
    render_html(an)
    ass["plan_accion"] = "texto suelto"
    ass["evaluaciones"] = "texto"
    an = analyse(ass, HOY)
    assert any("plan_accion" in w for w in an.warnings) and any("evaluaciones" in w for w in an.warnings)
    assert analyse(None, HOY).warnings          # evaluación vacía: aviso, sin excepción
    assert cargar_plan({"plan_accion": "x"}) == []


def test_h8_contraprueba_entrada_valida_sin_avisos_de_forma(ass):
    an = analyse(ass, HOY)
    assert not any("mal formada" in w or "no es un mapa" in w for w in an.warnings)


# 9. dashboard ignora plantillas
def test_h9_dashboard_ignora_template(tmp_path):
    shutil.copy(EX / "ejemplo-energia.yaml", tmp_path / "a.yaml")
    shutil.copy(ROOT / "assessments" / "assessment.template.yaml", tmp_path / "assessment.template.yaml")
    res = recopilar(tmp_path, HOY)
    assert [f.fichero for f in res.filas] == ["a.yaml"] and res.avisos == []
    # contraprueba: con otro nombre, la plantilla sí se procesa o se avisa
    shutil.copy(ROOT / "assessments" / "assessment.template.yaml", tmp_path / "plantilla.yaml")
    res = recopilar(tmp_path, HOY)
    assert len(res.filas) + len(res.avisos) == 2


# 10. categoría ENS con proveedor_sector_publico
def test_h10_categoria_en_cabecera_con_proveedor(ass):
    ass["cliente"].update({"sector_publico": False, "proveedor_sector_publico": True, "categoria_ens": "media"})
    an = analyse(ass, HOY)
    assert an.categoria_ens == "MEDIA"
    assert "Categoría ENS: MEDIA" in render_markdown(an)
    assert "Categoría ENS: MEDIA" in render_html(an)
    ass["cliente"]["proveedor_sector_publico"] = False       # contraprueba
    an = analyse(ass, HOY)
    assert "Categoría ENS" not in render_markdown(an)


# 11. bloqueada no cubre
def test_h11_accion_bloqueada_no_cubre():
    def a(estado):
        return cargar_plan({"plan_accion": [{"id": "A", "controles": ["X-1"], "accion": "x", "responsable": "r",
                                             "fecha_objetivo": "2026-12-01", "estado": estado}]})
    assert brechas_sin_accion(["X-1"], a("bloqueada")) == ["X-1"]
    assert brechas_sin_accion(["X-1"], a("hecha")) == ["X-1"]
    for ok in ("pendiente", "en_curso"):                      # contraprueba
        assert brechas_sin_accion(["X-1"], a(ok)) == []


def test_h11_p1_con_accion_bloqueada_sale_sin_accion(ass):
    base = analyse(ass, HOY)
    cid = base.p1_sin_accion[0]
    ass["plan_accion"] = [{"id": "B", "controles": [cid], "accion": "x", "responsable": "r",
                           "fecha_objetivo": "2027-01-01", "estado": "en_curso"}]
    assert cid not in analyse(ass, HOY).p1_sin_accion
    ass["plan_accion"][0]["estado"] = "bloqueada"
    assert cid in analyse(ass, HOY).p1_sin_accion


# versión
def test_version_060():
    assert __version__ == "0.7.0"
    assert 'version = "0.7.0"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "## 0.7.0" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
