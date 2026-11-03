"""T30: coherencia de versión y forma del workflow de CI."""
import re
from pathlib import Path

import yaml

import smc

RAIZ = Path(__file__).resolve().parent.parent


def _version_pyproject():
    m = re.search(r'^version\s*=\s*"([^"]+)"', (RAIZ / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    assert m, "pyproject.toml sin version"
    return m.group(1)


def _version_changelog():
    m = re.search(r"^## (\d+\.\d+\.\d+)\b", (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
    assert m, "CHANGELOG sin entrada de versión"
    return m.group(1)


def test_versiones_coinciden():
    assert _version_pyproject() == smc.__version__ == _version_changelog()


def test_version_es_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", smc.__version__)


def _workflow():
    return yaml.safe_load((RAIZ / ".github/workflows/tests.yml").read_text(encoding="utf-8"))


def test_workflow_permisos_minimos():
    wf = _workflow()
    assert wf["permissions"] == {"contents": "read"}


def test_workflow_triggers_y_matriz():
    wf = _workflow()
    on = wf.get("on", wf.get(True))  # PyYAML lee `on` como True
    assert on["push"]["branches"] == ["main"]
    assert on["pull_request"]["branches"] == ["main"]
    job = wf["jobs"]["tests"]
    assert job["strategy"]["matrix"]["python-version"] == ["3.10", "3.11", "3.12"]


def test_workflow_acciones_fijadas_por_sha():
    wf = _workflow()
    usos = [s["uses"] for j in wf["jobs"].values() for s in j["steps"] if "uses" in s]
    assert usos
    for u in usos:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", u), u


def test_workflow_ejecuta_tests_y_validate():
    wf = _workflow()
    runs = "\n".join(s.get("run", "") for s in wf["jobs"]["tests"]["steps"])
    assert "uv run --extra dev pytest -q" in runs
    assert "smc validate" in runs


def test_t36_workflow_ejecuta_los_comandos_de_v08():
    runs = "\n".join(s.get("run", "") for s in _workflow()["jobs"]["tests"]["steps"])
    for frag in ("smc compare ", "smc soa ", "--formato csv", "--formato xlsx", "--formato html", "smc evidencias ",
                 "--anterior "):
        assert frag in runs, frag
    assert "3.10" in _workflow()["jobs"]["tests"]["strategy"]["matrix"]["python-version"]   # requires-python >=3.10
    assert 'requires-python = ">=3.10"' in (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
