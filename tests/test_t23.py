"""T23: endurecimiento v0.6.1 (hallazgos 1-6 y 8 de informes/ola-9-revisor-ola.md). Cada test lleva su contraprueba."""
import base64
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

import smc.dashboard as db
import smc.visor as visor
from smc.cli import main
from smc.dashboard import generar, recopilar
from smc.gap import analyse, render_markdown, render_v06_md
from smc.mapa import construir_mapa
from smc.report_html import render_html, run_html
from smc.visor import generar_visor

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "assessments" / "examples"
REG = ROOT / "technologies" / "registry.template.yaml"
HOY = date(2026, 11, 3)
PWN = "<img src=x onerror=window.__pwn=1>"


@pytest.fixture(scope="module")
def mapa():
    return construir_mapa(REG, hoy=HOY)


# --- 1. emparejamiento registro-evaluación (decisión a) ---
def _dir_acme(tmp_path, extra_sur=True):
    d = tmp_path / "ev"
    d.mkdir()
    base = yaml.safe_load((EX / "ejemplo-energia.yaml").read_text(encoding="utf-8"))
    for stem, nombre in (("acme", "ACME Norte"), ("acme_sur", "ACME Sur")):
        c = copy.deepcopy(base)
        c["cliente"]["nombre"] = nombre
        (d / f"{stem}.yaml").write_text(yaml.safe_dump(c, allow_unicode=True), encoding="utf-8")
    reg = yaml.safe_load(REG.read_text(encoding="utf-8"))
    for t in reg["technologies"]:
        t["suscripcion"]["proveedor"] = "ProveedorSoloDeSur"
    (d / "acme_sur.registry.yaml").write_text(yaml.safe_dump(reg, allow_unicode=True), encoding="utf-8")
    return d


def test_h1_registro_va_a_la_evaluacion_de_stem_mas_largo(tmp_path):
    d = _dir_acme(tmp_path)
    out = tmp_path / "out"
    generar(d, out, HOY)
    assert "ProveedorSoloDeSur" in (out / "acme-sur.html").read_text(encoding="utf-8")
    assert "ProveedorSoloDeSur" not in (out / "acme.html").read_text(encoding="utf-8")
    res = recopilar(d, HOY)
    por = {f.fichero: f.registry is not None for f in res.filas}
    assert por == {"acme.yaml": False, "acme_sur.yaml": True}


def test_h1_empate_exacto_avisa_y_no_asocia(tmp_path):
    d = _dir_acme(tmp_path)
    (d / "acme_sur.registry.yaml").rename(d / "acme.registry.yaml")
    shutil.copy(d / "acme.registry.yaml", d / "acme-otro.yaml")      # dos registros casan igual con 'acme'
    res = recopilar(d, HOY)
    assert all(f.registry is None for f in res.filas if f.fichero == "acme.yaml")
    assert any("ambiguo" in a.motivo and a.fichero == "acme.yaml" for a in res.avisos)
    assert sorted(res.registros_sin_cliente) == ["acme-otro.yaml", "acme.registry.yaml"]


def test_h1_contraprueba_sin_empate_se_asocia(tmp_path):
    d = _dir_acme(tmp_path)
    (d / "acme_sur.registry.yaml").rename(d / "acme.registry.yaml")
    res = recopilar(d, HOY)
    assert next(f for f in res.filas if f.fichero == "acme.yaml").registry is not None and not res.avisos


# --- 2. visor: validación, escape, CSP con hash ---
def test_h2_resumen_mal_formado_da_valueerror(mapa):
    for mod in (lambda m: m["resumen"].pop("por_semaforo"),
                lambda m: m["resumen"]["por_semaforo"].__setitem__("rojo", PWN),
                lambda m: m["resumen"]["por_semaforo"].__setitem__("verde", -1),
                lambda m: m["resumen"]["por_semaforo"].__setitem__("gris", True),
                lambda m: m["resumen"]["por_semaforo"].__setitem__("ambar", 1.5),
                lambda m: m["resumen"].__setitem__("dispositivos", PWN),
                lambda m: m["resumen"].pop("dispositivos")):
        m = copy.deepcopy(mapa)
        mod(m)
        with pytest.raises(ValueError):
            generar_visor(m)


def test_h2_cli_resumen_roto_rc2_sin_traceback(tmp_path, mapa):
    m = copy.deepcopy(mapa)
    m["resumen"]["por_semaforo"]["rojo"] = PWN
    j = tmp_path / "m.json"
    j.write_text(json.dumps(m), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "smc.visor", str(j)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 2 and r.stderr.startswith("error:") and "Traceback" not in r.stderr
    m["resumen"]["por_semaforo"].pop("rojo")
    j.write_text(json.dumps(m), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "smc.visor", str(j)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 2 and "Traceback" not in r.stderr


def test_h2_cabecera_escapa(mapa):
    m = copy.deepcopy(mapa)
    m["generado_para"] = PWN
    p = generar_visor(m)
    assert PWN not in p and "&lt;img src=x" in p


def test_h2_csp_con_hash_del_script_del_modulo(mapa):
    p = generar_visor(mapa)
    csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]*)"', p).group(1)
    assert "unsafe-inline" not in csp.split("style-src")[0]       # script-src sin unsafe-inline
    scr = re.search(r"script-src ([^;]*)", csp).group(1)
    assert scr.startswith("'sha256-") and "unsafe" not in scr
    cuerpo = re.search(r'<script type="module">(.*?)</script>', p, re.S).group(1)
    h = "sha256-" + base64.b64encode(hashlib.sha256(cuerpo.encode("utf-8")).digest()).decode()
    assert f"'{h}'" in scr
    # el script constante: el hash no depende del mapa
    m2 = copy.deepcopy(mapa)
    m2["generado_para"] = "otro"
    assert re.search(r"script-src ([^;]*)", generar_visor(m2)).group(1) == scr


def test_h2_contraprueba_script_alterado_cambia_el_hash(mapa, monkeypatch):
    p = generar_visor(mapa)
    cuerpo = re.search(r'<script type="module">(.*?)</script>', p, re.S).group(1)
    h = base64.b64encode(hashlib.sha256((cuerpo + " ").encode("utf-8")).digest()).decode()
    assert f"'sha256-{h}'" not in p


# --- 3. aviso ENS (decisión c) ---
def test_h3_aviso_ens_dice_la_verdad():
    a = yaml.safe_load((EX / "ejemplo-ayuntamiento.yaml").read_text(encoding="utf-8"))
    an = analyse(a, HOY)
    for doc in (render_markdown(an), render_html(an)):
        assert "pendiente de contrastar" not in doc
        assert "contrastadas con el Anexo II" in doc
        assert "C/I/T/A/D" in doc and "CCN-STIC" in doc
        assert "(verificar)" in doc


# --- 4. tipos no str en el registro (decisión d) ---
@pytest.mark.parametrize("campo,valor", [("proveedor", 123), ("moneda", 5), ("proveedor", None), ("moneda", 2.5)])
def test_h4_proveedor_y_moneda_no_str(tmp_path, capsys, campo, valor):
    d = yaml.safe_load(REG.read_text(encoding="utf-8"))
    d["technologies"][0]["suscripcion"][campo] = valor
    p = tmp_path / "r.yaml"
    p.write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    html = run_html(EX / "ejemplo-energia.yaml", HOY, p)
    assert "Suscripciones" in html
    assert "Suscripciones" in render_v06_md(p, HOY)
    out = tmp_path / "o.html"
    rc = main(["report", str(EX / "ejemplo-energia.yaml"), "--registry", str(p), "--hoy", "2026-11-03", "-o", str(out)])
    assert rc == 0 and out.is_file()


# --- 5. licencia MIT completa en el visor (decisión e) ---
def test_h5_licencia_mit_completa_en_el_html(mapa):
    p = generar_visor(mapa)
    lic = (visor.ASSETS / "THREE-LICENSE").read_text(encoding="utf-8").strip()
    assert lic in p
    assert 'THE SOFTWARE IS PROVIDED "AS IS"' in p and "Permission is hereby granted" in p


# --- 6. tabla accesible completa (decisión f) ---
def test_h6_tabla_incluye_todo_el_panel(mapa):
    mapa = copy.deepcopy(mapa)
    v = next(d for z in mapa["zonas"] for d in z["dispositivos"])["vulnerabilidades"]
    v["abiertas"], v["fuera_sla"], v["cves_fuera_sla"] = 2, 2, ["CVE-2099-0001", "CVE-2099-0002"]
    cves = v["cves_fuera_sla"]
    p = generar_visor(mapa)
    seccion = p.split('aria-label="Alternativa en texto"')[1].split("<script")[0]
    for c in cves:
        assert c in seccion
    todos = [d for z in mapa["zonas"] for d in z["dispositivos"]] + mapa["sin_zona"]
    fila = next(f for f in re.findall(r"<tr>.*?</tr>", seccion) if f"<td>{todos[0]['id']}</td>" in f)
    for cab in ("Reglas (total)", "Reglas sin uso", "CVE fuera de SLA"):
        assert cab in seccion
    assert fila
    for z in mapa["zonas"]:
        assert z["nombre"] in seccion and "Semáforo de zona" in seccion
    r = mapa["resumen"]
    assert f"Reglas no evaluables: {r['reglas_no_evaluables']}" in seccion
    assert f"Vulnerabilidades abiertas: {r['vulnerabilidades_abiertas']}" in seccion
    assert f"fuera de SLA: {r['vulnerabilidades_fuera_sla']}" in seccion.replace("Fuera", "fuera")
    assert "Madurez media de verticales" in seccion
    for a in mapa["avisos"]:
        assert visor._e(a) in seccion


def test_h6_contraprueba_aviso_hostil_escapado(mapa):
    m = copy.deepcopy(mapa)
    m["avisos"] = list(m["avisos"]) + [PWN]
    p = generar_visor(m)
    assert PWN not in p and "&lt;img src=x" in p


# --- 8. etiqueta MITRE (decisión g) ---
ETIQUETA = "Catálogo de casos de uso del SOC (común a todos los clientes)"


def test_h8_mitre_etiquetado_en_html_y_markdown():
    assert ETIQUETA in run_html(EX / "ejemplo-energia.yaml", HOY)
    assert ETIQUETA in render_markdown(analyse(yaml.safe_load((EX / "ejemplo-energia.yaml").read_text(encoding="utf-8")), HOY))
