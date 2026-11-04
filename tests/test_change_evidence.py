"""change_evidence.py: comentarios HTML, errores de API al leer la configuración e identidad de cosign."""
import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts/change_evidence.py"


@pytest.fixture
def ce():
    spec = importlib.util.spec_from_file_location("change_evidence", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _falla_api(mod, monkeypatch, stderr):
    def gh_json(path):
        raise subprocess.CalledProcessError(1, "gh", stderr=stderr)
    monkeypatch.setattr(mod, "gh_json", gh_json)


def test_comentario_sin_cerrar_no_declara_issue(ce):
    assert ce.extract_issues("Closes #2\n<!-- Closes #1") == [2]
    assert ce.extract_tasks("<!-- Task: SMC-001") == []


def test_config_ausente_deja_solo_los_ficheros_fijos(ce, monkeypatch):
    _falla_api(ce, monkeypatch, "gh: Not Found (HTTP 404)")
    assert ce.allowed_release_files("o/r", "main") == ce.RELEASE_FILES


@pytest.mark.parametrize("stderr", ["gh: Forbidden (HTTP 403)", "gh: API rate limit exceeded for ID 74045. (HTTP 403)"])
def test_error_de_api_no_se_confunde_con_config_ausente(ce, monkeypatch, stderr):
    _falla_api(ce, monkeypatch, stderr)
    with pytest.raises(subprocess.CalledProcessError):
        ce.allowed_release_files("o/r", "main")


def test_error_al_detectar_pr_de_release_queda_como_hueco(ce, monkeypatch):
    pr = {"head": {"sha": "abc", "ref": "release-please--branches--main", "repo": {"full_name": "o/r"}},
          "base": {"ref": "main"}, "user": {"login": "x"}, "title": "t", "html_url": "u", "body": ""}

    def gh_json(path):
        if path.endswith("/files?per_page=100"):
            raise subprocess.CalledProcessError(1, "gh", stderr="gh: Server Error (HTTP 502)")
        if "check-runs" in path:
            return {"check_runs": []}
        if path.endswith("/status"):
            return {"statuses": []}
        return pr if path.endswith("/pulls/7") else []
    monkeypatch.setattr(ce, "gh_json", gh_json)
    p = ce.collect_pr("o/r", 7)
    assert p["maint"] is False
    assert any("HTTP 502" in g for g in p["gaps"])


@pytest.mark.parametrize("n,esperado", [(99, True), (100, False), (101, False)])
def test_pr_de_release_con_pagina_llena_no_cuenta(ce, monkeypatch, n, esperado):
    def gh_json(path):
        if "/files?" in path:
            return [{"filename": "CHANGELOG.md"}] * min(n, ce.FILES_PAGE)
        raise subprocess.CalledProcessError(1, "gh", stderr="gh: Not Found (HTTP 404)")
    monkeypatch.setattr(ce, "gh_json", gh_json)
    assert ce.is_release_pr("o/r", 7, "release-please--branches--main", "main", True) is esperado


def test_identidad_cosign_anclada_por_los_dos_lados(ce):
    md = ce.release_markdown({"repo": "o/r", "tag": "v1", "range": "a..b", "generated_at": "", "review_model": "",
                              "changes": [], "gaps": [], "controls": {"_nota": ""}})
    assert "'^https://github.com/o/r/.github/workflows/release.yml@refs/heads/(main|master)$'" in md
