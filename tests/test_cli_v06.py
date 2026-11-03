"""T22: `smc visor`, versión 0.6.0 y cifras de README/PRD (ENS contrastado con el BOE)."""
import json
import re
from pathlib import Path

import pytest

from smc import __version__
from smc.catalog import load_catalog
from smc.cli import main

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "technologies" / "registry.template.yaml"
AYTO = ROOT / "assessments" / "examples" / "ejemplo-ayuntamiento.yaml"


def rc(capsys, *args):
    code = main([str(a) for a in args])
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.fixture
def mapa_json(tmp_path, capsys):
    ruta = tmp_path / "mapa.json"
    assert rc(capsys, "mapa", REG, "-o", ruta)[0] == 0
    return ruta


def test_visor_genera_html(capsys, tmp_path, mapa_json):
    salida = tmp_path / "visor.html"
    code, out, err = rc(capsys, "visor", mapa_json, "-o", salida)
    assert code == 0, err
    html = salida.read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html") and "smc-mapa/1" in html
    assert "Visor escrito en" in out


def test_visor_json_roto_rc2_sin_fichero(capsys, tmp_path):
    malo = tmp_path / "roto.json"
    malo.write_text("{no es json", encoding="utf-8")
    salida = tmp_path / "v.html"
    code, _, err = rc(capsys, "visor", malo, "-o", salida)
    assert code == 2 and err.startswith("ERROR:")
    assert not salida.exists()


@pytest.mark.parametrize("contenido", ["[]", '{"schema": "otro/9"}', "{}"])
def test_visor_esquema_invalido_rc2(capsys, tmp_path, contenido):
    f = tmp_path / "m.json"
    f.write_text(contenido, encoding="utf-8")
    code, _, err = rc(capsys, "visor", f, "-o", tmp_path / "v.html")
    assert code == 2 and "ERROR" in err


def test_visor_fichero_inexistente_rc2(capsys, tmp_path):
    assert rc(capsys, "visor", tmp_path / "no.json", "-o", tmp_path / "v.html")[0] == 2


def test_visor_escapa_nombre_malicioso(capsys, tmp_path, mapa_json):
    m = json.loads(mapa_json.read_text(encoding="utf-8"))
    m["zonas"][0]["dispositivos"][0]["nombre"] = "</script><img src=x onerror=alert(1)>"
    f = tmp_path / "m2.json"
    f.write_text(json.dumps(m), encoding="utf-8")
    assert rc(capsys, "visor", f, "-o", tmp_path / "v.html")[0] == 0
    assert "</script><img" not in (tmp_path / "v.html").read_text(encoding="utf-8")


def test_visor_en_ayuda(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "visor" in capsys.readouterr().out


# versión
def test_version_060():
    assert __version__ == "0.8.1"
    assert 'version = "0.8.1"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "## 0.8.1" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "versión-0.8.1" in (ROOT / "README.md").read_text(encoding="utf-8")


# cifras de README/PRD tras T21 (ENS contrastado con el BOE)
def _verificar_ens() -> int:
    return sum(1 for c in load_catalog("ENS") if c.extra.get("verificar"))


def test_readme_y_prd_cifra_ens_verificar():
    n = _verificar_ens()
    assert n == 28
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    prd = (ROOT / "docs" / "prd" / "PRD-SMC-001-v1.md").read_text(encoding="utf-8")
    assert f"{n} de las 73" in readme and f"{n} de 73" in prd
    # contraprueba: la cifra antigua ya no aparece como estado actual
    assert "39 de las 73 medidas llevan" not in readme
    assert "Estado a v0.4.1" not in prd


def test_readme_comandos_v06_y_cifras():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "smc visor" in readme and "--registry" in readme and "docs/img/visor.png" in readme
    assert (ROOT / "docs" / "img" / "visor.png").is_file()
    assert "THREE-LICENSE" in readme or "three.js" in readme
    m = re.search(r"tests-(\d+)%20en%20verde", readme)
    assert m, "badge de tests"
    n_tests = len(re.findall(r"^\s*def test_", "".join(p.read_text(encoding="utf-8") for p in (ROOT / "tests").glob("test_*.py")), re.M))
    assert int(m.group(1)) >= n_tests   # el badge no se queda por debajo de los tests definidos (la parametrización suma)
