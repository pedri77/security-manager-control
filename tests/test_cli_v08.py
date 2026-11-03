"""T35: smc compare, soa, evidencias; sección Evolución; evidencia caducada en el dashboard; régimen transitorio
en el informe HTML (render_ia); documentación y versión 0.8.1. Cada bloque lleva su contraprueba."""
import copy
import re
import zipfile
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import pytest
import yaml

from smc import ai_act, report_html, resources
from smc.cli import main
from smc.dashboard import generar, recopilar

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "assessments" / "examples"
ENERGIA = EX / "ejemplo-energia.yaml"
Q1 = EX / "historico" / "ejemplo-energia-2026-q1.yaml"
AYTO = EX / "ejemplo-ayuntamiento.yaml"
HOY = "2026-11-03"


def rc(capsys, *args):
    capsys.readouterr()
    code = main(list(args))
    out = capsys.readouterr()
    return code, out.out, out.err


# ------------------------------------------------------------------ smc compare

def test_compare_stdout_y_fichero(capsys, tmp_path):
    code, out, _ = rc(capsys, "compare", str(Q1), str(ENERGIA), "--hoy", HOY)
    assert code == 0 and "# Evolución entre evaluaciones" in out and "+3.3" in out and "+5.0" in out
    f = tmp_path / "c.md"
    code, out, _ = rc(capsys, "compare", str(Q1), str(ENERGIA), "--hoy", HOY, "-o", str(f))
    assert code == 0 and f.read_text(encoding="utf-8").startswith("# Evolución") and str(f) in out


def test_compare_contraprueba_invertido_avisa_y_error_rc2(capsys, tmp_path):
    code, out, _ = rc(capsys, "compare", str(ENERGIA), str(Q1), "--hoy", HOY)
    assert code == 0 and "más antigua" in out and "-3.3" in out          # signo invertido
    code, _, err = rc(capsys, "compare", str(tmp_path / "no.yaml"), str(ENERGIA))
    assert code == 2 and "ERROR" in err
    (tmp_path / "x.yaml").write_text("- 1\n- 2\n", encoding="utf-8")
    assert rc(capsys, "compare", str(tmp_path / "x.yaml"), str(ENERGIA))[0] == 2


def test_compare_no_toca_los_ficheros_de_entrada(capsys, tmp_path):
    antes = (Q1.read_bytes(), ENERGIA.read_bytes())
    rc(capsys, "compare", str(Q1), str(ENERGIA), "-o", str(tmp_path / "c.md"))
    assert (Q1.read_bytes(), ENERGIA.read_bytes()) == antes


# ------------------------------------------------------------------ smc soa

def test_soa_tres_formatos(capsys, tmp_path):
    csv_, xlsx, html = tmp_path / "s.csv", tmp_path / "s.xlsx", tmp_path / "s.html"
    for fmt, f in (("csv", csv_), ("xlsx", xlsx), ("html", html)):
        code, out, _ = rc(capsys, "soa", str(ENERGIA), "--formato", fmt, "-o", str(f), "--hoy", HOY)
        assert code == 0 and str(f) in out and f.stat().st_size > 0
    raw = csv_.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") and b"\r\n" in raw and b"\r\r" not in raw
    with zipfile.ZipFile(xlsx) as z:
        for n in z.namelist():
            if n.endswith(".xml") or n.endswith(".rels"):
                ElementTree.fromstring(z.read(n))
        wb = z.read("xl/workbook.xml").decode("utf-8")
    assert "Aplicabilidad" in wb and "Evidencias" in wb
    h = html.read_text(encoding="utf-8")
    assert "@media print" in h and "<script" not in h and "https://" not in h.replace("https://pedri77", "")


def test_soa_ens_media_73_filas(capsys, tmp_path):
    ass = yaml.safe_load(ENERGIA.read_text(encoding="utf-8"))
    ass["cliente"]["sector_publico"] = True
    ass["cliente"]["categoria_ens"] = "MEDIA"
    f = tmp_path / "ens.yaml"
    f.write_text(yaml.safe_dump(ass, allow_unicode=True), encoding="utf-8")
    out = tmp_path / "ens.csv"
    assert rc(capsys, "soa", str(f), "--formato", "csv", "-o", str(out))[0] == 0
    assert out.read_text(encoding="utf-8-sig").count("\r\nENS,") + out.read_text(encoding="utf-8-sig").count("\nENS,") >= 73


def test_soa_contrapruebas(capsys, tmp_path):
    with pytest.raises(SystemExit) as e:                                               # falta --formato (argparse)
        main(["soa", str(ENERGIA), "-o", str(tmp_path / "x")])
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        main(["soa", str(ENERGIA), "--formato", "pdf", "-o", str(tmp_path / "x")])
    assert e.value.code == 2
    code, _, err = rc(capsys, "soa", str(tmp_path / "no.yaml"), "--formato", "csv", "-o", str(tmp_path / "x"))
    assert code == 2 and "ERROR" in err and not (tmp_path / "x").exists()


def test_soa_inyeccion_de_formulas_y_escape(capsys, tmp_path):
    ass = yaml.safe_load(ENERGIA.read_text(encoding="utf-8"))
    ass["evaluaciones"]["NIS2-21.2.b"]["evidencias"] = ["=HYPERLINK(\"https://x.example\",\"a\")", "<script>alert(1)</script>"]
    f = tmp_path / "e.yaml"
    f.write_text(yaml.safe_dump(ass, allow_unicode=True), encoding="utf-8")
    c, h = tmp_path / "e.csv", tmp_path / "e.html"
    rc(capsys, "soa", str(f), "--formato", "csv", "-o", str(c))
    rc(capsys, "soa", str(f), "--formato", "html", "-o", str(h))
    assert "'=HYPERLINK" in c.read_text(encoding="utf-8") and ",=HYPERLINK" not in c.read_text(encoding="utf-8")
    assert "<script>alert" not in h.read_text(encoding="utf-8") and "&lt;script&gt;" in h.read_text(encoding="utf-8")


# ------------------------------------------------------------------ smc evidencias

def test_evidencias_estados_y_huellas(capsys, tmp_path):
    code, out, _ = rc(capsys, "evidencias", str(ENERGIA), "--hoy", HOY)
    assert code == 0 and "caducada" in out and "vigente" in out and "sin_fecha" in out
    # con una huella declarada: coincide / no coincide
    ass = yaml.safe_load(ENERGIA.read_text(encoding="utf-8"))
    (tmp_path / "doc.txt").write_text("contenido ficticio", encoding="utf-8")
    import hashlib
    h = hashlib.sha256(b"contenido ficticio").hexdigest()
    ass["evaluaciones"]["NIS2-21.2.b"]["evidencias"] = [{"ref": "doc.txt", "fecha": "2026-10-01", "vigencia_dias": 365, "sha256": h}]
    f = tmp_path / "h.yaml"
    f.write_text(yaml.safe_dump(ass, allow_unicode=True), encoding="utf-8")
    code, out, _ = rc(capsys, "evidencias", str(f), "--base", str(tmp_path), "--hoy", HOY)
    assert code == 0 and "no coincide" not in out
    ass["evaluaciones"]["NIS2-21.2.b"]["evidencias"][0]["sha256"] = "0" * 64
    f.write_text(yaml.safe_dump(ass, allow_unicode=True), encoding="utf-8")
    code, out, _ = rc(capsys, "evidencias", str(f), "--base", str(tmp_path), "--hoy", HOY)
    assert code == 0 and "no coincide" in out                                          # contraprueba


def test_evidencias_errores_rc2(capsys, tmp_path):
    assert rc(capsys, "evidencias", str(tmp_path / "no.yaml"))[0] == 2
    assert rc(capsys, "evidencias", str(ENERGIA), "--base", str(tmp_path / "nada"))[0] == 2


def test_evidencias_ruta_fuera_de_base_no_se_lee(capsys, tmp_path):
    ass = yaml.safe_load(ENERGIA.read_text(encoding="utf-8"))
    ass["evaluaciones"]["NIS2-21.2.b"]["evidencias"] = [{"ref": "../../etc/passwd", "fecha": "2026-10-01", "vigencia_dias": 30, "sha256": "0" * 64}]
    f = tmp_path / "p.yaml"
    f.write_text(yaml.safe_dump(ass, allow_unicode=True), encoding="utf-8")
    code, out, _ = rc(capsys, "evidencias", str(f), "--base", str(tmp_path), "--hoy", HOY)
    assert code == 0 and "rechazada" in out and "no se lee" in out


# ------------------------------------------------------------------ report --anterior

def test_report_anterior_anade_evolucion(capsys, tmp_path):
    f = tmp_path / "r.html"
    code, _, _ = rc(capsys, "report", str(ENERGIA), "--anterior", str(Q1), "-o", str(f), "--hoy", HOY)
    html = f.read_text(encoding="utf-8")
    assert code == 0 and "Evolución respecto a la evaluación anterior" in html and "+3.3" in html
    f2 = tmp_path / "r2.html"
    rc(capsys, "report", str(ENERGIA), "-o", str(f2), "--hoy", HOY)
    assert "Evolución respecto" not in f2.read_text(encoding="utf-8")                  # contraprueba: sin --anterior no hay sección
    assert rc(capsys, "report", str(ENERGIA), "--anterior", str(tmp_path / "no.yaml"), "-o", str(tmp_path / "z.html"))[0] == 2


def test_evolucion_escapa_html():
    from smc import compare
    a = yaml.safe_load(Q1.read_text(encoding="utf-8"))
    b = copy.deepcopy(yaml.safe_load(ENERGIA.read_text(encoding="utf-8")))
    b["cliente"]["nombre"] = "<script>alert(1)</script>"
    html = report_html.render_evolucion(compare.comparar(a, b, date(2026, 11, 3)))
    assert "<script>" not in html and "&lt;script&gt;" in html and "no coinciden" in html


# ------------------------------------------------------------------ dashboard: evidencia caducada

def test_dashboard_muestra_evidencia_caducada(tmp_path):
    res = recopilar(EX, date(2026, 11, 3))
    fila = next(f for f in res.filas if "energ" in f.fichero)
    assert fila.evid_caducadas == 1
    assert next(f for f in res.filas if "ayuntamiento" in f.fichero).evid_caducadas == 0   # contraprueba
    generar(EX, tmp_path / "p", date(2026, 11, 3))
    idx = (tmp_path / "p" / "index.html").read_text(encoding="utf-8")
    assert "Evidencia caducada" in idx and '<span class="venc">1</span>' in idx


# ------------------------------------------------------------------ render_ia: régimen transitorio

def _inv(**kw):
    s = {"id": "IA-T", "nombre": "Sistema <b>ficticio</b>", "rol": ["proveedor"],
         "nivel_riesgo": "alto_riesgo_anexo_iii", "en_mercado_desde": "2026-01-01",
         "cambios_significativos": False}
    s.update(kw)
    return {"organizacion": "Ficticia", "sistemas": [s]}


def test_render_ia_muestra_regimen_transitorio():
    res = ai_act.obligaciones(_inv(), date(2026, 11, 3), estricto=False)
    html = report_html.render_ia(res, None)
    assert "Régimen transitorio (art. 111.2 RIA)" in html and "solo con cambios significativos" in html
    assert "<b>ficticio</b>" not in html and "&lt;b&gt;" in html
    pub = ai_act.obligaciones(_inv(autoridad_publica=True), date(2026, 11, 3), estricto=False)
    assert "2030-08-02" in report_html.render_ia(pub, None)


def test_render_ia_contraprueba_con_cambios_significativos_no_hay_tabla():
    res = ai_act.obligaciones(_inv(cambios_significativos=True), date(2026, 11, 3), estricto=False)
    assert "Régimen transitorio" not in report_html.render_ia(res, None)


# ------------------------------------------------------------------ documentación y versión

def _readme():
    return (ROOT / "README.md").read_text(encoding="utf-8")


def test_version_080_y_badge_ci():
    from smc import __version__
    assert __version__ == "0.8.1" and "versión-0.8.1" in _readme()
    assert "## 0.8.1" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "https://github.com/pedri77/security-manager-control/actions/workflows/tests.yml/badge.svg" in _readme()
    assert "versión-0.7.1" not in _readme()                                             # contraprueba


def test_readme_documenta_comandos_nuevos_y_sin_repos_privados():
    r = _readme()
    for t in ("smc compare", "smc soa", "smc evidencias", "--anterior"):
        assert t in r
    assert resources.urls_no_publicas(r.replace(".git", "")) == []


def test_prd_y_changelog_recogen_v08():
    prd = (ROOT / "docs" / "prd" / "PRD-SMC-001-v1.md").read_text(encoding="utf-8")
    cl = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for t in ("smc compare", "smc soa", "smc evidencias"):
        assert t in prd and t in cl
    assert "RF-40" in prd


def test_comandos_nuevos_en_el_bloque_empezar():
    bloque = re.search(r"## Empezar en 1 minuto\n\n```bash\n(.*?)```", _readme(), re.S).group(1)
    for c in ("smc compare", "smc soa", "smc evidencias"):
        assert c in bloque
