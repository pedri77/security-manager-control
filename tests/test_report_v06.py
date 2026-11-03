"""T19: tecnologías, reglas, suscripciones y MITRE en el informe HTML, el Markdown y el dashboard."""
import re
import shutil
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

from smc.cli import main
from smc.dashboard import generar, recopilar
from smc.gap import analyse, render_markdown, render_v06_md
from smc.report_html import cargar_registry, render_body, render_html, render_mitre, run_html

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "assessments" / "examples"
ENERGIA = EX / "ejemplo-energia.yaml"
REG = ROOT / "technologies" / "registry.template.yaml"
HOY = date(2026, 11, 3)
SECCIONES = ("Tecnologías evaluadas", "Estado de las reglas", "Suscripciones", "Madurez MITRE")


class _Etiquetas(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.hrefs = [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.hrefs += [v for k, v in attrs if k == "href"]


def _reg(tmp_path, mod=None, name="registry.yaml"):
    d = yaml.safe_load(REG.read_text(encoding="utf-8"))
    if mod:
        mod(d)
    p = tmp_path / name
    p.write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    return p


def test_con_registry_las_cuatro_secciones():
    html = run_html(ENERGIA, HOY, REG)
    for s in SECCIONES:
        assert s in html
    assert "no evaluable" not in html.lower() or "No evaluables" in html
    assert "Exclusiones y políticas gestionadas por el MSSP" in html   # motivo de no evaluable
    assert "Reglas any-any" in html and "Coste anual total" in html


def test_sin_registry_solo_mitre():
    html = run_html(ENERGIA, HOY)
    assert "Madurez MITRE" in html
    for s in SECCIONES[:3]:
        assert s not in html


def test_cli_report_con_y_sin_registry(tmp_path, capsys):
    a, b = tmp_path / "a.html", tmp_path / "b.html"
    assert main(["report", str(ENERGIA), "-o", str(a), "--hoy", "2026-11-03"]) == 0
    assert main(["report", str(ENERGIA), "-o", str(b), "--registry", str(REG), "--hoy", "2026-11-03"]) == 0
    assert "Estado de las reglas" not in a.read_text(encoding="utf-8")
    assert "Estado de las reglas" in b.read_text(encoding="utf-8")


def test_cli_registry_invalido_rc2(tmp_path, capsys):
    malo = tmp_path / "x.yaml"
    malo.write_text("a: 1\n", encoding="utf-8")
    assert main(["report", str(ENERGIA), "-o", str(tmp_path / "o.html"), "--registry", str(malo)]) == 2
    assert main(["report", str(ENERGIA), "-o", str(tmp_path / "o.html"), "--registry", str(tmp_path / "no.yaml")]) == 2
    assert "ERROR" in capsys.readouterr().err
    assert not (tmp_path / "o.html").exists()


def test_motivo_con_script_escapado(tmp_path):
    def mod(d):
        d["technologies"][0]["reglas"]["motivo"] = "<script>alert(1)</script>"
        d["technologies"][0]["nombre"] = "<img src=x onerror=alert(2)>"
    html = run_html(ENERGIA, HOY, _reg(tmp_path, mod))
    assert "<script>alert(1)" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<img src=x" not in html
    assert "script" not in _Etiquetas_tags(html)


def _Etiquetas_tags(html):
    p = _Etiquetas()
    p.feed(html)
    return p.tags


@pytest.mark.parametrize("valor", ["abc", None, float("nan"), float("inf"), [1], {"a": 1}, True])
def test_coste_no_numerico_no_rompe(tmp_path, valor):
    def mod(d):
        d["technologies"][0]["suscripcion"]["coste_anual"] = valor
    p = tmp_path / "r.yaml"
    d = yaml.safe_load(REG.read_text(encoding="utf-8"))
    mod(d)
    p.write_text(yaml.dump(d, allow_unicode=True), encoding="utf-8")
    html = run_html(ENERGIA, HOY, p)
    assert "Suscripciones" in html and "nan EUR" not in html and "inf EUR" not in html
    md = render_v06_md(p, HOY)
    assert "Suscripciones" in md


def test_any_any_destacado_aunque_este_revisada(tmp_path):
    def mod(d):
        t = d["technologies"][2]
        t["reglas"].update(estado="revisadas", ultima_revision="2026-10-30", reglas_any_any=3)
    html = run_html(ENERGIA, HOY, _reg(tmp_path, mod))
    assert 'class="alerta"' in html and "3 regla(s) any-any (estado: revisadas)" in html


def test_enlaces_solo_https(tmp_path):
    p = _Etiquetas()
    p.feed(run_html(ENERGIA, HOY, REG))
    assert all(h.startswith("https://") for h in p.hrefs)
    assert not {"script", "link", "img", "iframe"} & set(p.tags)


def test_fechas_y_hoy_inyectable(tmp_path):
    uno = run_html(ENERGIA, date(2026, 11, 3), REG)
    otro = run_html(ENERGIA, date(2027, 6, 1), REG)
    assert uno != otro and "VENCIDA" in otro


def test_mitre_siempre_y_coincide_con_modulo():
    from smc import mitre
    an = analyse(yaml.safe_load(ENERGIA.read_text(encoding="utf-8")), HOY)
    body = render_body(an)
    m = mitre.madurez(hoy=HOY)
    for tac in m["tacticas"]:
        assert tac in body
    for uc in mitre.sin_playbook():
        assert uc in body
    assert render_mitre({"madurez": m, "sin_playbook": []}).count("<tr>") == len(m["tacticas"]) + 1


def test_markdown_con_registry(tmp_path):
    an = analyse(yaml.safe_load(ENERGIA.read_text(encoding="utf-8")), HOY)
    sin = render_markdown(an)
    con = render_markdown(an, registry=REG)
    assert "## Madurez MITRE" in sin and "## Estado de las reglas" not in sin
    for s in ("## Tecnologías evaluadas", "## Estado de las reglas", "## Suscripciones", "## Madurez MITRE"):
        assert s in con
    def mod(d):
        d["technologies"][0]["reglas"]["motivo"] = "<b>x</b> | y"
    md = render_v06_md(_reg(tmp_path, mod), HOY)
    assert "<b>" not in md and "&lt;b&gt;" in md and "\\|" in md


def test_registry_dict_y_mal_formado():
    assert cargar_registry({"technologies": []}) == {"technologies": []}
    with pytest.raises(ValueError):
        cargar_registry({"technologies": "no"})
    html = render_html(analyse(yaml.safe_load(ENERGIA.read_text(encoding="utf-8")), HOY), {"technologies": [{}, "x", {"id": "T"}]})
    assert "Tecnologías evaluadas" in html


# --- dashboard ---

@pytest.fixture
def dir_ev(tmp_path):
    d = tmp_path / "ev"
    d.mkdir()
    for f in EX.glob("*.yaml"):
        shutil.copy(f, d / f.name)
    return d


def test_dashboard_sin_registros_guiones_y_mitre(dir_ev, tmp_path):
    out = tmp_path / "out"
    res = generar(dir_ev, out, HOY)
    assert not res.avisos and (out / "mitre.html").is_file()
    idx = (out / "index.html").read_text(encoding="utf-8")
    assert "Reglas no evaluables" in idx and "Suscripciones que vencen" in idx and 'href="mitre.html"' in idx
    assert "Madurez MITRE" in (out / "mitre.html").read_text(encoding="utf-8")
    assert all(f.reglas_no_eval is None for f in res.filas)


def test_dashboard_con_registro_asociado(dir_ev, tmp_path):
    shutil.copy(REG, dir_ev / "ejemplo-energia.registry.yaml")
    shutil.copy(REG, dir_ev / "suelto.yaml")
    out = tmp_path / "out"
    res = generar(dir_ev, out, HOY)
    assert not res.avisos                                  # los registros no son avisos
    assert res.registros_sin_cliente == ["suelto.yaml"]
    f = next(x for x in res.filas if x.fichero == "ejemplo-energia.yaml")
    assert f.reglas_no_eval >= 1 and f.any_any >= 1 and f.subs_vencen >= 1
    assert "Estado de las reglas" in (out / f"{f.slug}.html").read_text(encoding="utf-8")
    otro = next(x for x in res.filas if x is not f)
    assert otro.reglas_no_eval is None
    assert "suelto.yaml" in (out / "index.html").read_text(encoding="utf-8")


def test_dashboard_registro_con_xss_escapado(dir_ev, tmp_path):
    def mod(d):
        d["technologies"][0]["reglas"]["motivo"] = "<script>x</script>"
    shutil.copy(_reg(tmp_path, mod), dir_ev / "ejemplo-energia.registry.yaml")
    out = tmp_path / "out"
    generar(dir_ev, out, HOY)
    for h in out.glob("*.html"):
        assert "<script" not in h.read_text(encoding="utf-8")


def test_dashboard_cli_rc0(dir_ev, tmp_path):
    shutil.copy(REG, dir_ev / "ejemplo-energia.registry.yaml")
    assert main(["dashboard", str(dir_ev), "-o", str(tmp_path / "o"), "--hoy", "2026-11-03"]) == 0
