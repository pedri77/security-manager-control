"""T28: integración v0.7 (pentest, purple, IA, PMO), madurez MITRE con purple, secciones del informe y dashboard,
.gitignore, ecosistema y cifras del README/PRD. Cada bloque lleva su contraprueba."""
import copy
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest
import yaml

import smc.catalog as catalog
from smc import __version__, mitre, offensive
from smc.cli import main
from smc.dashboard import generar

ROOT = Path(__file__).resolve().parent.parent
PENTEST = ROOT / "offensive" / "examples" / "ejemplo-pentest.yaml"
PURPLE = ROOT / "offensive" / "examples" / "ejemplo-purple.yaml"
IA = ROOT / "ai" / "inventario.template.yaml"
PMO = ROOT / "pmo" / "examples" / "ejemplo-energia.yaml"
ENERGIA = ROOT / "assessments" / "examples" / "ejemplo-energia.yaml"
AYTO = ROOT / "assessments" / "examples" / "ejemplo-ayuntamiento.yaml"
REG = ROOT / "technologies" / "registry.template.yaml"
HOY = "2026-11-03"
XSS = "<script>alert(1)</script>"


def rc(capsys, *args):
    code = main([str(a) for a in args])
    out = capsys.readouterr()
    return code, out.out, out.err


def escribir(tmp_path, nombre, datos):
    ruta = tmp_path / nombre
    ruta.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    return ruta


# ------------------------------------------------------------------ comandos nuevos

def test_pentest(capsys):
    code, out, err = rc(capsys, "pentest", PENTEST, "--hoy", HOY)
    assert code == 0, err
    assert "Hallazgos de pentest a 2026-11-03" in out and "H-001" in out and "Fuera de SLA" in out


def test_purple(capsys):
    code, out, err = rc(capsys, "purple", PURPLE, "--hoy", HOY)
    assert code == 0, err
    assert "Ejercicios purple team" in out and "credential-access" in out


def test_ai(capsys):
    code, out, err = rc(capsys, "ai", IA, "--hoy", HOY)
    assert code == 0, err
    assert "no es asesoramiento jurídico" in out and "IA-001" in out and "AGT-" in out


def test_ai_fechas_del_omnibus(capsys):
    _, antes, _ = rc(capsys, "ai", IA, "--hoy", "2027-12-01")
    _, despues, _ = rc(capsys, "ai", IA, "--hoy", "2027-12-02")
    assert "aplicable desde 2027-12-02" in antes
    assert antes != despues      # a partir de esa fecha las obligaciones del Anexo III pasan a vigentes


def test_pmo_con_ics_registry_y_assessment(capsys, tmp_path):
    ics = tmp_path / "e.ics"
    code, out, err = rc(capsys, "pmo", PMO, "--hoy", HOY, "--ics", ics, "--registry", REG, "--assessment", ENERGIA)
    assert code == 0, err
    assert "Valor ganado (EVM)" in out and "Suscripciones del registro" in out
    datos = ics.read_bytes()
    assert datos.startswith(b"BEGIN:VCALENDAR\r\n") and datos.count(b"BEGIN:VEVENT") == 4
    assert b"\n" not in datos.replace(b"\r\n", b"")


@pytest.mark.parametrize("args", [
    ("pentest", "no-existe.yaml"), ("purple", "no-existe.yaml"), ("ai", "no-existe.yaml"), ("pmo", "no-existe.yaml"),
    ("mitre", "--purple", "no-existe.yaml"),
])
def test_ficheros_inexistentes_rc2_sin_traceback(capsys, args):
    code, out, err = rc(capsys, *args)
    assert code == 2 and err.startswith("ERROR:") and "Traceback" not in err


def test_pmo_registry_o_assessment_inexistente_rc2(capsys):
    assert rc(capsys, "pmo", PMO, "--registry", "nada.yaml")[0] == 2
    assert rc(capsys, "pmo", PMO, "--assessment", "nada.yaml")[0] == 2


def test_pentest_con_datos_no_validos_rc2(capsys, tmp_path):
    datos = yaml.safe_load(PENTEST.read_text(encoding="utf-8"))
    datos["hallazgos"][0]["estado"] = "inventado"
    code, _, err = rc(capsys, "pentest", escribir(tmp_path, "mal.yaml", datos))
    assert code == 2 and "estado" in err


def test_purple_caso_de_uso_inexistente_rc2(capsys, tmp_path):
    datos = yaml.safe_load(PURPLE.read_text(encoding="utf-8"))
    datos["ejercicios"][0]["caso_uso"] = "UC-999"
    code, _, err = rc(capsys, "purple", escribir(tmp_path, "mal.yaml", datos))
    assert code == 2 and "UC-999" in err


def test_ai_nivel_inexistente_no_rompe(capsys, tmp_path):
    datos = yaml.safe_load(IA.read_text(encoding="utf-8"))
    datos["sistemas"][0]["nivel_riesgo"] = "inventado"
    code, out, _ = rc(capsys, "ai", escribir(tmp_path, "ia.yaml", datos), "--hoy", HOY)
    assert code == 0 and "no clasificados" in out.lower()


# ------------------------------------------------------------------ validate

def test_validate_incluye_ria_y_plantillas(capsys):
    assert rc(capsys, "validate")[0] == 0
    assert catalog.validar_v07() == []


def test_validate_contraprueba_catalogo_ria_roto(capsys, monkeypatch):
    from smc import ai_act
    obligs = ai_act.cargar_obligaciones()
    obligs[0].roles = ["rol-inexistente"]
    monkeypatch.setattr(ai_act, "cargar_obligaciones", lambda path=None: obligs)
    code, _, err = rc(capsys, "validate")
    assert code == 1 and "ERROR: ia:" in err


def test_validate_contraprueba_plantilla_pentest_rota(monkeypatch, tmp_path):
    datos = yaml.safe_load((ROOT / "offensive" / "pentest.template.yaml").read_text(encoding="utf-8"))
    datos["hallazgos"][0]["estado"] = "inventado"
    falso = tmp_path / "offensive"
    (falso / "examples").mkdir(parents=True)
    escribir(falso, "pentest.template.yaml", datos)
    for n in ("purple.template.yaml",):
        shutil.copy(ROOT / "offensive" / n, falso / n)
    for n in ("ejemplo-pentest.yaml", "ejemplo-purple.yaml"):
        shutil.copy(ROOT / "offensive" / "examples" / n, falso / "examples" / n)
    monkeypatch.setattr(offensive, "OFFENSIVE_DIR", falso)
    assert any("pentest: plantilla" in e for e in catalog.validar_v07())


# ------------------------------------------------------------------ madurez MITRE con purple

def nivel(tec, **kw):
    return mitre.madurez(hoy=date(2026, 11, 3), **kw)["tecnicas"][tec]


def test_purple_detectado_sube_a_probada():
    # UC-007 (T1190): regla + playbook; ejercicio detectado de 2025-08-20 (hace más de 90 días) -> 4
    assert nivel("T1190") == 3
    assert nivel("T1190", purple=PURPLE) == 4


def test_purple_reciente_sube_a_5():
    assert nivel("T1110.003", purple=PURPLE) == 5      # UC-001 ya probada el 2026-09-15


def test_purple_reciente_en_caso_con_regla_da_5(tmp_path):
    datos = yaml.safe_load(PURPLE.read_text(encoding="utf-8"))
    datos["ejercicios"].append({"id": "PP-009", "fecha": "2026-10-20", "tecnica": "T1190", "caso_uso": "UC-007",
                                "resultado": "detectado"})
    assert nivel("T1190", purple=escribir(tmp_path, "p.yaml", datos)) == 5


def test_contraprueba_sin_fichero_purple_la_madurez_no_cambia():
    assert mitre.madurez(hoy=date(2026, 11, 3)) == mitre.madurez(hoy=date(2026, 11, 3), purple=None)
    assert nivel("T1190") == 3


def test_contraprueba_parcial_y_no_detectado_no_suben():
    # UC-002 (parcial) y UC-004 (no_detectado) se quedan como están
    base = mitre.madurez(hoy=date(2026, 11, 3))["casos"]
    con = mitre.madurez(hoy=date(2026, 11, 3), purple=PURPLE)["casos"]
    assert con["UC-002"] == base["UC-002"] and con["UC-004"] == base["UC-004"]
    assert all(con[k] >= base[k] for k in base)       # nunca baja


def test_purple_futuro_o_sin_fecha_no_cuenta(tmp_path):
    datos = {"version": "v1", "ejercicios": [
        {"id": "PP-1", "fecha": "2027-01-01", "tecnica": "T1190", "caso_uso": "UC-007", "resultado": "detectado"}]}
    assert nivel("T1190", purple=escribir(tmp_path, "f.yaml", datos)) == 3
    datos["ejercicios"][0].pop("fecha")
    assert nivel("T1190", purple=escribir(tmp_path, "s.yaml", datos)) == 3


def test_purple_en_cli_mitre_y_navigator(capsys, tmp_path):
    _, sin, _ = rc(capsys, "mitre", "--hoy", HOY)
    _, con, _ = rc(capsys, "mitre", "--purple", PURPLE, "--hoy", HOY)
    assert re.search(r"\| T1190 \| 3 \|", sin) and re.search(r"\| T1190 \| 4 \|", con)
    capa = tmp_path / "capa.json"
    assert rc(capsys, "mitre", "--navigator", "--purple", PURPLE, "-o", capa, "--hoy", HOY)[0] == 0
    assert '"techniqueID": "T1190",\n      "score": 4' in capa.read_text(encoding="utf-8")


# ------------------------------------------------------------------ informe HTML

def test_informe_sin_ficheros_no_cambia(capsys, tmp_path):
    out = tmp_path / "i.html"
    assert rc(capsys, "report", ENERGIA, "-o", out, "--hoy", HOY)[0] == 0
    html = out.read_text(encoding="utf-8")
    for titulo in ("Pentesting: hallazgos", "Purple team: ejercicios", "IA: RIA", "PMO:"):
        assert titulo not in html


def test_informe_con_las_cuatro_secciones(capsys, tmp_path):
    out = tmp_path / "i.html"
    code, _, err = rc(capsys, "report", ENERGIA, "-o", out, "--hoy", HOY, "--registry", REG, "--pentest", PENTEST,
                      "--purple", PURPLE, "--ai", IA, "--pmo", PMO)
    assert code == 0, err
    html = out.read_text(encoding="utf-8")
    for titulo in ("Pentesting: hallazgos", "Purple team: ejercicios", "IA: RIA", "PMO:", "Valor ganado (EVM)",
                   "no es asesoramiento jurídico"):
        assert titulo in html
    # el purple cuenta en la madurez MITRE del informe
    assert "<script" not in html.lower()
    hrefs = re.findall(r'href="([^"]*)"', html)
    assert hrefs and all(h.startswith("https://") for h in hrefs)


def test_informe_pmo_usa_la_evaluacion_y_el_registro(capsys, tmp_path):
    out = tmp_path / "i.html"
    assert rc(capsys, "report", ENERGIA, "-o", out, "--hoy", HOY, "--registry", REG, "--pmo", PMO)[0] == 0
    assert "Suscripciones del registro" in out.read_text(encoding="utf-8")


def test_informe_fichero_roto_rc2_sin_escribir(capsys, tmp_path):
    out = tmp_path / "i.html"
    code, _, err = rc(capsys, "report", ENERGIA, "-o", out, "--pentest", tmp_path / "no.yaml")
    assert code == 2 and err.startswith("ERROR:") and not out.exists()


def _pentest_xss(tmp_path):
    datos = yaml.safe_load(PENTEST.read_text(encoding="utf-8"))
    datos["hallazgos"][0]["titulo"] = XSS
    datos["hallazgos"][0]["activo"] = '"><img src=x onerror=alert(2)>'
    return escribir(tmp_path, "pt.yaml", datos)


def _pmo_xss(tmp_path):
    datos = yaml.safe_load(PMO.read_text(encoding="utf-8"))
    for t in datos["tareas"]:
        if t["id"] in ("T-02", "T-05"):          # T-02 retrasada, T-05 sin control
            t["titulo"] = XSS
    datos["proyecto"]["nombre"] = XSS
    return escribir(tmp_path, "pmo.yaml", datos)


def test_xss_en_hallazgo_y_en_tarea_pmo_sale_escapado(capsys, tmp_path):
    out = tmp_path / "i.html"
    code, _, err = rc(capsys, "report", ENERGIA, "-o", out, "--hoy", HOY, "--pentest", _pentest_xss(tmp_path),
                      "--pmo", _pmo_xss(tmp_path))
    assert code == 0, err
    html = out.read_text(encoding="utf-8")
    assert XSS not in html and "<img src=x" not in html
    assert html.count("&lt;script&gt;alert(1)&lt;/script&gt;") >= 4      # hallazgo, tarea retrasada, sin control, nombre
    assert "&quot;&gt;&lt;img src=x onerror=alert(2)&gt;" in html


def test_xss_en_inventario_ia_y_en_purple(capsys, tmp_path):
    ia = yaml.safe_load(IA.read_text(encoding="utf-8"))
    ia["sistemas"][0]["nombre"] = XSS
    ia["organizacion"] = XSS
    pu = yaml.safe_load(PURPLE.read_text(encoding="utf-8"))
    pu["ejercicios"][2]["mejora"]["descripcion"] = XSS
    out = tmp_path / "i.html"
    assert rc(capsys, "report", ENERGIA, "-o", out, "--hoy", HOY, "--ai", escribir(tmp_path, "ia.yaml", ia),
              "--purple", escribir(tmp_path, "pu.yaml", pu))[0] == 0
    html = out.read_text(encoding="utf-8")
    assert XSS not in html and html.count("&lt;script&gt;") >= 3


def test_contraprueba_sin_escape_el_xss_pasaria(monkeypatch, tmp_path):
    """Si `_e` no escapara, el HTML contendría el script: el test anterior detecta justo eso."""
    from smc import report_html
    monkeypatch.setattr(report_html, "_e", lambda x: "" if x is None else str(x))
    html = report_html.run_html(ENERGIA, date(2026, 11, 3), pentest=_pentest_xss(tmp_path))
    assert XSS in html


def test_markdown_de_los_comandos_escapa(capsys, tmp_path):
    code, out, _ = rc(capsys, "pentest", _pentest_xss(tmp_path), "--hoy", HOY)
    assert code == 0 and XSS not in out and "&lt;script&gt;" in out
    code, out, _ = rc(capsys, "pmo", _pmo_xss(tmp_path), "--hoy", HOY)
    assert code == 0 and XSS not in out and "&lt;script&gt;" in out


def test_enlaces_de_fuentes_ia_solo_https():
    from smc import ai_act, report_html
    res = ai_act.obligaciones(IA, date(2026, 11, 3), estricto=False)
    html = report_html.render_ia(res, [])
    assert 'href="https://eur-lex.europa.eu/eli/reg/2024/1689/oj"' in html
    assert not re.search(r'href="(?!https://)', html)


# ------------------------------------------------------------------ dashboard

def test_dashboard_con_acompanantes(tmp_path):
    d = tmp_path / "ev"
    d.mkdir()
    shutil.copy(ENERGIA, d / "ejemplo-energia.yaml")
    shutil.copy(REG, d / "ejemplo-energia.registry.yaml")
    shutil.copy(PENTEST, d / "ejemplo-energia.pentest.yaml")
    shutil.copy(PURPLE, d / "ejemplo-energia.purple.yaml")
    shutil.copy(IA, d / "ejemplo-energia.ai.yaml")
    shutil.copy(PMO, d / "ejemplo-energia.pmo.yaml")
    shutil.copy(PENTEST, d / "otro.pentest.yaml")        # sin evaluación: aviso
    res = generar(d, tmp_path / "out", date(2026, 11, 3))
    assert len(res.filas) == 1
    assert [a.fichero for a in res.avisos] == ["otro.pentest.yaml"]
    html = (tmp_path / "out" / "ejemplo-energia.html").read_text(encoding="utf-8")
    for titulo in ("Pentesting: hallazgos", "Purple team: ejercicios", "IA: RIA", "PMO:"):
        assert titulo in html
    # el purple del cliente solo cuenta en su página; mitre.html (común) no cambia
    comun = (tmp_path / "out" / "mitre.html").read_text(encoding="utf-8")
    assert "Pentesting" not in comun


def test_dashboard_acompanante_roto_es_aviso_y_no_rompe(tmp_path):
    d = tmp_path / "ev"
    d.mkdir()
    shutil.copy(ENERGIA, d / "ejemplo-energia.yaml")
    datos = yaml.safe_load(PENTEST.read_text(encoding="utf-8"))
    datos["hallazgos"][0]["estado"] = "inventado"
    escribir(d, "ejemplo-energia.pentest.yaml", datos)
    res = generar(d, tmp_path / "out", date(2026, 11, 3))
    assert len(res.filas) == 1 and len(res.avisos) == 1 and "ignoradas" in res.avisos[0].motivo
    assert "Pentesting" not in (tmp_path / "out" / "ejemplo-energia.html").read_text(encoding="utf-8")


def test_dashboard_xss_en_acompanante(tmp_path):
    d = tmp_path / "ev"
    d.mkdir()
    shutil.copy(ENERGIA, d / "ejemplo-energia.yaml")
    shutil.copy(_pentest_xss(tmp_path), d / "ejemplo-energia.pentest.yaml")
    generar(d, tmp_path / "out", date(2026, 11, 3))
    html = (tmp_path / "out" / "ejemplo-energia.html").read_text(encoding="utf-8")
    assert XSS not in html and "&lt;script&gt;" in html


# ------------------------------------------------------------------ gitignore, ecosistema, soberanía

@pytest.mark.parametrize("ruta,ignorado", [
    ("offensive/cliente.yaml", True), ("ai/cliente.yaml", True), ("pmo/cliente.yaml", True),
    ("offensive/pentest.template.yaml", False), ("offensive/purple.template.yaml", False),
    ("offensive/examples/ejemplo-pentest.yaml", False), ("ai/inventario.template.yaml", False),
])
def test_gitignore_de_datos_de_cliente(ruta, ignorado):
    r = subprocess.run(["git", "check-ignore", "-q", ruta], cwd=ROOT)
    assert (r.returncode == 0) is ignorado


def test_ztna_privado_sin_url_y_sin_nombrar_el_repo():
    from smc import resources
    z = next(p for p in resources.cargar_ecosistema() if p["id"] == "ECO-ZTNA")
    assert z["estado"] == "privado" and z["url"] is None
    texto = (ROOT / "README.md").read_text(encoding="utf-8") + (ROOT / "resources" / "ecosistema.yaml").read_text(encoding="utf-8")
    assert "disponible bajo petición" in texto and "En preparación" not in texto
    assert resources.urls_no_publicas(texto.replace(".git", "")) == []   # el .git del clone es del repo público


# ------------------------------------------------------------------ versión y documentación

def test_version_070():
    assert f"message={__version__}&" in (ROOT / "README.md").read_text(encoding="utf-8")


def _readme():
    return (ROOT / "README.md").read_text(encoding="utf-8")


def test_cifras_del_readme_son_las_reales():
    from smc.ai_act import cargar_obligaciones
    from smc.verticals import cargar_verticales
    readme = _readme()
    assert len(cargar_verticales()) == 22 and "verticales-22-" in readme
    assert len(cargar_obligaciones()) == 31 and "RIA-31%20obligaciones" in readme
    n_tests = len(re.findall(r"^\s*def test_", "".join(p.read_text(encoding="utf-8") for p in (ROOT / "tests").glob("test_*.py")), re.M))
    badge = int(re.search(r"tests-(\d+)%20en%20verde", readme).group(1))
    assert badge >= n_tests
    # contraprueba: las cifras de la versión anterior ya no figuran
    assert "verticales-20-" not in readme and "message=0.6.1&" not in readme


def test_readme_fechas_del_omnibus_y_aviso():
    r = _readme()
    for t in ("2026/1744", "2027-12-02", "2028-08-02", "2026-08-02", "no es asesoramiento jurídico"):
        assert t in r


def _comandos_del_readme(tmp_path):
    """Líneas `smc ...` del bloque «Empezar en 1 minuto»; /tmp/ pasa a un directorio temporal."""
    bloque = re.search(r"## Empezar en 1 minuto\n\n```bash\n(.*?)```", _readme(), re.S).group(1)
    cmds = []
    for linea in bloque.splitlines():
        linea = linea.split("  #")[0].strip()
        if linea.startswith("smc "):
            cmds.append(linea.replace("/tmp/", f"{tmp_path}/").split())
    return cmds


def test_comandos_del_readme_rc0(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    cmds = _comandos_del_readme(tmp_path)
    assert len(cmds) >= 12
    nuevos = {c[1] for c in cmds}
    assert {"pentest", "purple", "ai", "pmo"} <= nuevos
    for c in cmds:
        code, _, err = rc(capsys, *c[1:])
        assert code == 0, (c, err)


def test_contraprueba_comando_del_readme_roto_da_rc2(capsys):
    assert rc(capsys, "pentest", "offensive/no-existe.yaml")[0] == 2


def test_prd_y_changelog_recogen_v07():
    prd = (ROOT / "docs" / "prd" / "PRD-SMC-001-v1.md").read_text(encoding="utf-8")
    cl = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for rf in ("smc pentest", "smc purple", "smc ai", "smc pmo"):
        assert rf in prd and rf in cl
