"""T14: integración v0.5 en CLI, validate, informe Markdown/HTML y dashboard."""
import json
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

import smc.catalog as catalog
from smc.cli import main
from smc.dashboard import generar
from smc.gap import analyse, render_markdown
from smc.report_html import render_html

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "assessments" / "examples"
ENERGIA = EX / "ejemplo-energia.yaml"
AYTO = EX / "ejemplo-ayuntamiento.yaml"
REG = ROOT / "technologies" / "registry.template.yaml"
HOY = date(2026, 11, 3)
HOY_S = "2026-11-03"


def rc(capsys, *args):
    code = main([str(a) for a in args])
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.mark.parametrize("args", [
    ["validate"],
    ["verticals", ENERGIA], ["verticals", AYTO],
    ["verticals", ROOT / "assessments" / "assessment.template.yaml"],
    ["tech", REG, "--hoy", HOY_S], ["subs", REG, "--hoy", HOY_S, "--days", "120"],
    ["protocols"], ["protocols", "SMB"],
    ["rss"], ["mitre", "--hoy", HOY_S],
])
def test_comandos_rc0(capsys, args):
    code, out, err = rc(capsys, *args)
    assert code == 0, err
    assert out.strip()


def test_validate_incluye_v05(capsys, monkeypatch):
    assert rc(capsys, "validate")[0] == 0
    # contraprueba: un error en cualquiera de los validadores nuevos pone validate en rojo
    monkeypatch.setattr("smc.protocols.validar", lambda *a, **k: ["protocolo roto"])
    code, _, err = rc(capsys, "validate")
    assert code == 1 and "protocolo roto" in err


def test_validar_casos_de_uso_contraprueba(tmp_path):
    assert catalog.validar_casos_uso() == []
    uc = tmp_path / "c.yaml"
    uc.write_text(yaml.safe_dump({"use_cases": [
        {"id": "UC-1", "estado": "activo", "tactica": "x", "mitre": ["XX"], "deteccion": "mala",
         "playbook": "no/existe.md", "vertical": "VRT-NOPE"},
        {"id": "UC-1", "estado": "activo", "tactica": "x", "mitre": ["T1110"]}]}), encoding="utf-8")
    e = " | ".join(catalog.validar_casos_uso(uc, tmp_path))
    for frag in ("duplicado", "técnica ATT&CK no válida", "deteccion no válida", "playbook inexistente", "vertical inexistente"):
        assert frag in e


def test_validar_v05_vertical_de_tecnologia_y_rss(monkeypatch):
    from smc import resources
    rss = resources.cargar_rss()
    rss[0] = {**rss[0], "vertical": "VRT-NOPE"}
    monkeypatch.setattr(resources, "cargar_rss", lambda *a, **k: rss)
    assert any("vertical inexistente VRT-NOPE" in e for e in catalog.validar_v05())


def test_protocols_desconocido_rc2(capsys):
    code, _, err = rc(capsys, "protocols", "NOPE")
    assert code == 2 and "ERROR" in err


def test_rss_opml_a_fichero(capsys, tmp_path):
    out = tmp_path / "f.opml"
    assert rc(capsys, "rss", "--opml", "-o", out)[0] == 0
    assert len(list(ET.parse(out).getroot().iter("outline"))) > 5


def test_mitre_navigator(capsys, tmp_path):
    capa = tmp_path / "capa.json"
    assert rc(capsys, "mitre", "--navigator", "-o", capa, "--hoy", HOY_S)[0] == 0
    d = json.loads(capa.read_text(encoding="utf-8"))
    assert d["techniques"] and all("score" in t for t in d["techniques"])
    # sin --navigator, `smc mitre` sigue igual
    assert "Cobertura MITRE" in rc(capsys, "mitre")[1]


def test_verticals_no_evaluable_sin_motivo_rc2(capsys, tmp_path):
    ev = yaml.safe_load(ENERGIA.read_text(encoding="utf-8"))
    ev["verticales"]["VRT-HUNT"] = {"madurez": "no_evaluable"}
    f = tmp_path / "e.yaml"
    f.write_text(yaml.safe_dump(ev, allow_unicode=True), encoding="utf-8")
    assert rc(capsys, "verticals", f)[0] == 2


# --- informe: verticales, escape y enlaces ---

XSS = '<script>alert("x")</script>'


def _ev(tmp_motivo=XSS):
    ev = yaml.safe_load(ENERGIA.read_text(encoding="utf-8"))
    ev["verticales"]["VRT-HUNT"] = {"madurez": "no_evaluable", "motivo": tmp_motivo}
    return ev


def test_informe_md_y_html_con_verticales():
    an = analyse(yaml.safe_load(ENERGIA.read_text(encoding="utf-8")), HOY)
    md, doc = render_markdown(an), render_html(an)
    for t in (md, doc):
        assert "Verticales" in t and "No evaluables" in t and "Sin telemetría centralizada" in t
    assert 'href="https://pedri77.github.io/edr-visual-app/"' in doc
    assert "(https://pedri77.github.io/edr-visual-app/)" in md


def test_xss_en_motivo_escapado():
    doc = render_html(analyse(_ev(), HOY))
    assert XSS not in doc and "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in doc
    # contraprueba: sin el escape, el payload sí aparecería (el markdown no escapa y lo conserva)
    assert XSS in render_markdown(analyse(_ev(), HOY))


class _Hrefs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        self.hrefs += [v for k, v in attrs if k == "href"]


def test_javascript_url_no_sale_como_href(monkeypatch):
    from smc import verticals
    malo = verticals.Vertical("VRT-EDR", "EDR", ["NIS2-21.2.b"], criterios=["c"],
                              recursos=[{"titulo": "malo", "url": "javascript:alert(1)"},
                                        {"titulo": "http", "url": "http://x.example/"},
                                        {"titulo": "bueno", "url": "https://pedri77.github.io/edr-visual-app/"}])
    real = verticals.cargar_verticales()
    cat = [malo if v.id == "VRT-EDR" else v for v in real]
    monkeypatch.setattr(verticals, "cargar_verticales", lambda *a, **k: cat)
    an = analyse(yaml.safe_load(ENERGIA.read_text(encoding="utf-8")), HOY)
    doc = render_html(an)
    p = _Hrefs()
    p.feed(doc)
    assert "javascript:alert(1)" not in p.hrefs and "http://x.example/" not in p.hrefs
    assert "https://pedri77.github.io/edr-visual-app/" in p.hrefs
    assert "malo" in doc   # el texto se conserva, sin enlace
    assert "javascript:" not in render_markdown(an)
    assert all(h.startswith("https://") or h.endswith(".html") or h == "" for h in p.hrefs)


def test_dashboard_madurez_verticales(tmp_path):
    d = tmp_path / "ev"
    d.mkdir()
    shutil.copy(ENERGIA, d / "e.yaml")
    ay = yaml.safe_load(AYTO.read_text(encoding="utf-8"))
    ay.pop("verticales", None)
    (d / "a.yaml").write_text(yaml.safe_dump(ay, allow_unicode=True), encoding="utf-8")
    out = tmp_path / "out"
    res = generar(d, out, HOY)
    idx = (out / "index.html").read_text(encoding="utf-8")
    assert "Madurez verticales" in idx
    media = {f.fichero: f.vert_media for f in res.filas}
    assert media["a.yaml"] is None and media["e.yaml"] is not None
    assert f"{media['e.yaml']} / 5" in idx
    assert re.search(r"<td>—</td>", idx)
