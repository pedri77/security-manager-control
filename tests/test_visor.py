"""T20: visor 3D offline (smc.visor)."""
import copy
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

import smc.visor as visor
from smc.mapa import construir_mapa
from smc.visor import generar_visor, json_embebido

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "technologies" / "registry.template.yaml"
HOY = date(2026, 11, 3)
MALO = '</script><img src=x onerror="alert(1)">'


@pytest.fixture(scope="module")
def mapa():
    return construir_mapa(REG, hoy=HOY)


@pytest.fixture(scope="module")
def pagina(mapa):
    return generar_visor(mapa)


def con_nombre_malo(mapa):
    m = copy.deepcopy(mapa)
    d = next(d for z in m["zonas"] for d in z["dispositivos"])
    d["nombre"] = MALO
    return m, d


def test_autocontenida_sin_red(pagina):
    # nada se carga de fuera: ni src/href, ni fetch/XHR/import dinámico/CSS @import
    assert not re.search(r"\b(src|href|action|poster|srcset)\s*=", pagina, re.I)
    for patron in ("fetch(", "XMLHttpRequest", "import(", "@import", "importScripts", "WebSocket(", "sendBeacon", "EventSource("):
        assert patron not in pagina, patron
    assert "default-src 'none'" in pagina          # CSP: ni aunque se colara algo
    assert '<script type="module">' in pagina and 'type="application/json"' in pagina
    assert len(pagina.encode()) < 1_000_000


def test_incluye_three_y_licencia():
    assert (visor.ASSETS / "THREE-LICENSE").read_text().startswith("The MIT License")
    assert "WebGLRenderer" in (visor.ASSETS / "three.bundle.min.js").read_text()


def test_codigo_del_visor_sin_innerhtml():
    app = (visor.ASSETS / "visor-app.js").read_text()
    for prohibido in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
        assert prohibido not in app, prohibido


def test_json_embebido_escapa_menor(mapa):
    m, _ = con_nombre_malo(mapa)
    s = json_embebido(m)
    assert "<" not in s and "\\u003c/script>" in s
    assert json.loads(s) == m                      # sin pérdida


def test_nombre_malicioso_no_rompe_la_pagina(mapa):
    m, d = con_nombre_malo(mapa)
    p = generar_visor(m)
    assert MALO not in p                           # ni crudo en el JSON ni en la tabla
    assert p.count("</script>") == 2               # solo los dos <script> propios (datos y módulo)
    assert "&lt;/script&gt;&lt;img" in p           # la tabla en texto lo escapa
    # el JSON embebido sigue siendo el mismo dato
    bloque = re.search(r'id="smc-data">(.*?)</script>', p, re.S).group(1)
    assert json.loads(bloque)["zonas"][0]["dispositivos"][0]["nombre"] == d["nombre"]


def test_contraprueba_sin_escape_se_rompe(mapa, monkeypatch):
    """Sin el escape de '<' la página se rompería: el test anterior es sensible."""
    monkeypatch.setattr(visor, "json_embebido", lambda m: json.dumps(m, ensure_ascii=False))
    m, _ = con_nombre_malo(mapa)
    assert generar_visor(m).count("</script>") > 2


def test_tabla_texto_con_todos_los_dispositivos(mapa, pagina):
    ids = [d["id"] for z in mapa["zonas"] for d in z["dispositivos"]] + [d["id"] for d in mapa["sin_zona"]]
    assert ids
    for i in ids:
        assert f"<td>{i}</td>" in pagina
    assert "<caption>" in pagina and 'scope="col"' in pagina
    assert pagina.count("<tr>") == len(ids) + 1


def test_gris_nunca_verde_en_la_pagina(mapa, pagina):
    gris = [d for z in mapa["zonas"] for d in z["dispositivos"] if d["semaforo"] == "gris"]
    assert gris, "la plantilla debe traer un dispositivo gris (no evaluable)"
    fila = next(f for f in re.findall(r"<tr>.*?</tr>", pagina) if f"<td>{gris[0]['id']}</td>" in f)
    assert "GRIS (no se sabe)" in fila and "VERDE" not in fila and "No evaluable:" in fila
    app = (visor.ASSETS / "visor-app.js").read_text()
    assert 'ORDEN.includes(s) ? s : "gris"' in app  # valor desconocido = gris, nunca verde


def test_semaforo_invalido_se_rechaza(mapa):
    m = copy.deepcopy(mapa)
    next(d for z in m["zonas"] for d in z["dispositivos"])["semaforo"] = "azul"
    with pytest.raises(ValueError, match="no válido"):
        generar_visor(m)


def test_reduced_motion_y_visita(pagina):
    app = (visor.ASSETS / "visor-app.js").read_text()
    assert "prefers-reduced-motion: reduce" in app
    assert "if (!REDUCED) iniciarVisita()" in app           # sin visita automática con movimiento reducido
    assert "25000" in app and '"pointerdown", "wheel", "keydown"' in app   # primer gesto cede, 25 s de calma


def test_cli_modulo(tmp_path, mapa):
    j = tmp_path / "mapa.json"
    j.write_text(json.dumps(mapa), encoding="utf-8")
    out = tmp_path / "visor.html"
    r = subprocess.run([sys.executable, "-m", "smc.visor", str(j), "-o", str(out)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")
    r = subprocess.run([sys.executable, "-m", "smc.visor", str(j)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0 and r.stdout.startswith("<!doctype html>")


def test_cli_errores_rc2(tmp_path):
    malo = tmp_path / "x.json"
    malo.write_text("{no es json", encoding="utf-8")
    otro = tmp_path / "y.json"
    otro.write_text(json.dumps({"schema": "otro/1"}), encoding="utf-8")
    for arg in (str(tmp_path / "no-existe.json"), str(malo), str(otro)):
        r = subprocess.run([sys.executable, "-m", "smc.visor", arg], capture_output=True, text=True, cwd=ROOT)
        assert r.returncode == 2 and r.stderr.startswith("error:")


def test_package_data_incluye_assets():
    t = (ROOT / "pyproject.toml").read_text()
    assert "[tool.setuptools.package-data]" in t and "assets/*" in t
