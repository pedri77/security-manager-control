import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

import smc.report_html as rh
from smc.cli import main
from smc.gap import analyse
from smc.report_html import render_body, render_html

EX = Path(__file__).resolve().parent.parent / "assessments" / "examples" / "ejemplo-ayuntamiento.yaml"
HOY = date(2026, 11, 3)


@pytest.fixture
def ass():
    return yaml.safe_load(EX.read_text(encoding="utf-8"))


@pytest.fixture
def doc(ass):
    return render_html(analyse(ass, HOY))


def test_secciones(doc):
    for s in ("Resumen ejecutivo", "Top 10 brechas P1", "Acciones vencidas a 2026-11-03", "Detalle por marco",
              "Sin evaluar (", "Plan de acción", "Brechas sin acción", "no aplican a la categoría MEDIA",
              "NIS2", "ENS", "@media print", "ACC-02"):
        assert s in doc, s
    assert doc.startswith("<!DOCTYPE html>") and 'class="bar"' in doc


def test_autocontenido(doc):
    class P(HTMLParser):
        def __init__(s):
            super().__init__(); s.mal = []; s.tags = set()
        def handle_starttag(s, tag, attrs):
            s.tags.add(tag)
            for k, v in attrs:
                if tag in ("link", "script", "img", "iframe") and k in ("href", "src"):
                    s.mal.append((tag, v))
    p = P(); p.feed(doc)
    assert not p.mal and not ({"script", "link", "img", "iframe"} & p.tags)
    assert not re.search(r"https?://|@import|url\(", doc)


def test_xss_escapado(ass):
    ass["evaluaciones"]["NIS2-21.2.c"]["notas"] = "<script>alert(1)</script>"
    ass["cliente"]["nombre"] = '<img src=x onerror=alert(2)>'
    ass["plan_accion"][0]["accion"] = "<b onclick=x>"
    out = render_html(analyse(ass, HOY))
    assert "<script>alert(1)" not in out and "&lt;script&gt;alert(1)&lt;/script&gt;" in out
    assert "<img" not in out and "<b onclick" not in out


def test_contraprueba_sin_escape_rompe(ass, monkeypatch):
    ass["evaluaciones"]["NIS2-21.2.c"]["notas"] = "<script>alert(1)</script>"
    monkeypatch.setattr(rh, "_e", lambda x: "" if x is None else str(x))
    assert "<script>alert(1)</script>" in render_html(analyse(ass, HOY))


def test_sin_evaluar_separado(doc):
    i = doc.index("Brechas evaluadas (")
    j = doc.index("Sin evaluar (", i)
    assert i < j


def test_body_reutilizable(ass):
    b = render_body(analyse(ass, HOY), nivel=3)
    assert "<html" not in b and "<h3>Resumen ejecutivo</h3>" in b


def test_cli_report(tmp_path, capsys):
    out = tmp_path / "i.html"
    assert main(["report", str(EX), "-o", str(out), "--hoy", "2026-11-03"]) == 0
    assert "Informe de brechas" in out.read_text(encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["report", str(EX), "-o", str(out), "--hoy", "mal"])
