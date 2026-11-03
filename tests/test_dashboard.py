import re
import shutil
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

import smc.dashboard as db
from smc.cli import main
from smc.dashboard import generar, recopilar, semaforo, slugify

EX = Path(__file__).resolve().parent.parent / "assessments" / "examples"
HOY = date(2026, 11, 3)


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.tags, self.rows = [], [], 0

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.rows += tag == "tr"
        self.hrefs += [v for k, v in attrs if k in ("href", "src")]


def _parse(texto):
    p = _Links()
    p.feed(texto)
    return p


@pytest.fixture
def dir_ej(tmp_path):
    d = tmp_path / "ev"
    d.mkdir()
    for f in EX.glob("*.yaml"):
        shutil.copy(f, d / f.name)
    return d


def test_dashboard_dos_filas_y_enlaces(dir_ej, tmp_path):
    out = tmp_path / "out"
    res = generar(EX, out, HOY)
    assert len(res.filas) == 2 and not res.avisos
    idx = (out / "index.html").read_text(encoding="utf-8")
    p = _parse(idx)
    assert p.rows == 3  # cabecera + 2 clientes
    enlaces = [h for h in p.hrefs if h.endswith(".html")]
    assert len(enlaces) == 2
    for h in enlaces:
        assert "/" not in h and ":" not in h          # relativos
        assert (out / h).is_file()
        pag = (out / h).read_text(encoding="utf-8")
        assert 'href="index.html"' in pag and "Resumen ejecutivo" in pag
    assert "Ayuntamiento de Ejemplo" in idx and "Distribuidora Eléctrica Ejemplo" in idx
    assert "Semáforo" in idx and 'class="sem ' in idx


def test_sin_recursos_externos_ni_js(dir_ej, tmp_path):
    out = tmp_path / "out"
    generar(dir_ej, out, HOY)
    for f in out.glob("*.html"):
        t = f.read_text(encoding="utf-8")
        p = _parse(t)
        assert "script" not in p.tags and "link" not in p.tags and "img" not in p.tags
        assert not re.search(r"https?://", t)


def test_escape_de_nombres(dir_ej, tmp_path):
    d = yaml.safe_load((EX / "ejemplo-energia.yaml").read_text(encoding="utf-8"))
    d["cliente"]["nombre"] = '<script>alert("x")</script>'
    d["cliente"]["sector"] = "<b>s</b>"
    (dir_ej / "mal<nombre>.yaml").write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    out = tmp_path / "out"
    res = generar(dir_ej, out, HOY)
    assert len(res.filas) == 3
    idx = (out / "index.html").read_text(encoding="utf-8")
    assert "<script>" not in idx and "&lt;script&gt;" in idx and "<b>s</b>" not in idx
    # el fichero de salida usa slug seguro
    assert all(re.fullmatch(r"[a-z0-9-]+\.html", f.name) for f in out.glob("*.html"))
    assert (out / "mal-nombre.html").is_file()


def test_yaml_roto_no_rompe(dir_ej, tmp_path):
    (dir_ej / "roto.yaml").write_text("cliente: [sin cerrar\n  : :", encoding="utf-8")
    (dir_ej / "otra-cosa.yaml").write_text("foo: bar\n", encoding="utf-8")
    (dir_ej / "lista.yaml").write_text("- 1\n- 2\n", encoding="utf-8")
    out = tmp_path / "out"
    res = generar(dir_ej, out, HOY)
    assert len(res.filas) == 2
    assert {a.fichero for a in res.avisos} == {"roto.yaml", "otra-cosa.yaml", "lista.yaml"}
    idx = (out / "index.html").read_text(encoding="utf-8")
    assert "roto.yaml" in idx and "otra-cosa.yaml" in idx and "Avisos" in idx
    assert _parse(idx).rows == 3
    assert not (out / "roto.html").exists()


def test_fallo_en_analyse_es_aviso(dir_ej, monkeypatch):
    """Un error inesperado en el análisis de un cliente se informa como aviso y no tumba el resto."""
    orig = db.analyse

    def falla_energia(datos, hoy=None):
        if "Distribuidora" in datos["cliente"]["nombre"]:
            raise RuntimeError("boom")
        return orig(datos, hoy)
    monkeypatch.setattr(db, "analyse", falla_energia)
    res = recopilar(dir_ej, HOY)
    assert [f.fichero for f in res.filas] == ["ejemplo-ayuntamiento.yaml"]
    assert [a.fichero for a in res.avisos] == ["ejemplo-energia.yaml"] and "boom" in res.avisos[0].motivo


def test_semaforo_reglas():
    assert semaforo(90, 0, 0, 0) == "verde"
    assert semaforo(79.9, 0, 0, 0) == "ambar"
    assert semaforo(90, 1, 0, 0) == "ambar"
    assert semaforo(90, 0, 0, 1) == "ambar"
    assert semaforo(90, 1, 1, 0) == "rojo"
    assert semaforo(49.9, 0, 0, 0) == "rojo"


def test_ayuntamiento_datos(tmp_path):
    res = recopilar(EX, HOY)
    f = {x.fichero: x for x in res.filas}
    ay, en = f["ejemplo-ayuntamiento.yaml"], f["ejemplo-energia.yaml"]
    assert "ENS" in ay.cumplimiento and "ENS" not in en.cumplimiento
    assert ay.vencidas == 1 and ay.semaforo == "rojo"
    assert en.analisis.cliente["tipo_entidad_nis2"] == "esencial" and not en.analisis.cliente["sector_publico"]
    assert en.vencidas == 1 and en.p1 >= 1 and en.p1_sin_accion >= 0


def test_slugs_unicos_y_seguros():
    assert slugify("Ayuntamiento Ñandú / 2026") == "ayuntamiento-nandu-2026"
    assert slugify("../../etc") == "etc"
    assert slugify("???") == "cliente"


def test_colision_de_slug(dir_ej, tmp_path):
    shutil.copy(dir_ej / "ejemplo-energia.yaml", dir_ej / "Ejemplo Energia.yaml")
    res = recopilar(dir_ej, HOY)
    slugs = [f.slug for f in res.filas]
    assert len(slugs) == len(set(slugs)) == 3
    assert "index" not in slugs


def test_cli_dashboard(dir_ej, tmp_path, capsys):
    out = tmp_path / "o"
    assert main(["dashboard", str(dir_ej), "-o", str(out), "--hoy", "2026-11-03"]) == 0
    assert (out / "index.html").is_file()
    assert "2 cliente(s)" in capsys.readouterr().out
    assert main(["dashboard", str(tmp_path / "noexiste"), "-o", str(out)]) == 2
    with pytest.raises(SystemExit):
        main(["dashboard", str(dir_ej), "-o", str(out), "--hoy", "mañana"])
