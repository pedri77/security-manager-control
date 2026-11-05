"""change_evidence.py: comentarios HTML, errores de API al leer la configuración e identidad de cosign."""
import importlib.util
import json
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
        if "/statuses?" in path:
            return []
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


# ───────────── paginación de collect_pr (SMC-003) ─────────────
def _commit(i, msg):
    return {"sha": f"sha{i}", "commit": {"message": msg}}


class FakeGh:
    """gh_json simulado: sirve cada lista troceada según per_page y page de la ruta."""

    def __init__(self, lists, fail=None):
        self.lists = lists  # sufijo de ruta -> lista completa
        self.fail = fail or (lambda path, page: False)
        self.pr = {"head": {"sha": "H", "ref": "feat", "repo": {"full_name": "o/r"}}, "base": {"ref": "main"},
                   "user": {"login": "x"}, "title": "t", "html_url": "u", "body": ""}

    def __call__(self, path):
        from urllib.parse import parse_qs, urlparse
        u = urlparse(path)
        q = parse_qs(u.query)
        per, page = int(q.get("per_page", ["30"])[0]), int(q.get("page", ["1"])[0])
        if self.fail(u.path, page):
            raise subprocess.CalledProcessError(1, "gh", stderr="gh: Server Error (HTTP 502)")
        if u.path.endswith("/pulls/7"):
            return self.pr
        for suf, lst in self.lists.items():
            if u.path.endswith(suf):
                trozo = lst[(page - 1) * per: page * per]
                return {"total_count": len(lst), "check_runs": trozo} if suf.endswith("check-runs") else trozo
        if u.path.endswith("/check-runs"):
            return {"total_count": 0, "check_runs": []}
        if u.path.endswith(("/commits", "/reviews", "/statuses")):
            return []
        raise subprocess.CalledProcessError(1, "gh", stderr="gh: Not Found (HTTP 404)")


def _collect(ce, monkeypatch, lists, fail=None, per=2):
    monkeypatch.setattr(ce, "PER_PAGE", per)
    monkeypatch.setattr(ce, "gh_json", FakeGh(lists, fail))
    return ce.collect_pr("o/r", 7)


def test_task_solo_en_commit_de_segunda_pagina(ce, monkeypatch):
    commits = [_commit(1, "a"), _commit(2, "b"), _commit(3, "c\n\nTask: SMC-009")]
    p = _collect(ce, monkeypatch, {"/pulls/7/commits": commits})
    assert p["tasks"] == ["SMC-009"] and p["commits"] == ["sha1", "sha2", "sha3"]


def test_aprobacion_solo_en_segunda_pagina_de_reviews(ce, monkeypatch):
    reviews = [{"user": {"login": "a"}, "state": "COMMENTED"}, {"user": {"login": "b"}, "state": "COMMENTED"},
               {"user": {"login": "c"}, "state": "APPROVED"}]
    p = _collect(ce, monkeypatch, {"/pulls/7/reviews": reviews})
    assert p["approved_by"] == ["c"]


def test_check_solo_en_segunda_pagina_de_check_runs(ce, monkeypatch):
    runs = [{"name": "a", "conclusion": "success"}, {"name": "b", "conclusion": "success"},
            {"name": "c", "conclusion": "failure"}]
    p = _collect(ce, monkeypatch, {"/commits/H/check-runs": runs})
    assert [c["name"] for c in p["checks"]] == ["a", "b", "c"] and p["gaps"] == []


def test_blind_review_fuera_de_la_primera_pagina_de_estados(ce, monkeypatch):
    sts = [{"id": 3, "context": "ci", "state": "success"}, {"id": 2, "context": "ci", "state": "success"},
           {"id": 1, "context": ce.BLIND_REVIEW_CONTEXT, "state": "success", "description": "d", "target_url": "t"}]
    p = _collect(ce, monkeypatch, {"/commits/H/statuses": sts})
    assert p["blind_review"] == {"state": "success", "description": "d", "url": "t"}


@pytest.mark.parametrize("orden", ["nuevo_primero", "viejo_primero"])
def test_blind_review_repetido_cuenta_el_mas_reciente(ce, monkeypatch, orden):
    ctx = ce.BLIND_REVIEW_CONTEXT
    viejo = {"id": 1, "context": ctx, "state": "failure", "created_at": "2026-11-01T10:00:00Z"}
    nuevo = {"id": 9, "context": ctx, "state": "success", "created_at": "2026-11-02T10:00:00Z"}
    otro = {"id": 5, "context": "ci", "state": "success", "created_at": "2026-11-01T12:00:00Z"}
    sts = [nuevo, otro, viejo] if orden == "nuevo_primero" else [viejo, otro, nuevo]
    p = _collect(ce, monkeypatch, {"/commits/H/statuses": sts})
    assert p["blind_review"]["state"] == "success"


@pytest.mark.parametrize("que,suf", [("checks", "check-runs"), ("estados", "statuses")])
def test_fallo_en_pagina_posterior_queda_como_hueco(ce, monkeypatch, que, suf):
    items = [{"name": str(i), "context": str(i), "id": i, "state": "success"} for i in range(5)]
    fail = lambda path, page: path.endswith(suf) and page == 2
    p = _collect(ce, monkeypatch, {f"/commits/H/{suf}": items}, fail)
    assert any("HTTP 502" in g for g in p["gaps"])
    assert (p["checks"] == [] if que == "checks" else p["blind_review"] is None)


def test_pagina_exacta_y_pagina_vacia_terminan(ce, monkeypatch):
    commits = [_commit(1, "Task: SMC-001"), _commit(2, "b")]  # justo una página llena
    p = _collect(ce, monkeypatch, {"/pulls/7/commits": commits})
    assert p["commits"] == ["sha1", "sha2"]


# ───────────── tope de páginas como hueco (SMC-003, T38) ─────────────
def _llena(n=6):
    return [{"name": str(i), "context": str(i), "id": i, "state": "success", "conclusion": "success"}
            for i in range(n)]


@pytest.mark.parametrize("que,suf", [("checks", "check-runs"), ("estados", "statuses")])
def test_tope_de_paginas_en_checks_y_estados_es_hueco(ce, monkeypatch, que, suf):
    monkeypatch.setattr(ce, "MAX_PAGES", 3)
    p = _collect(ce, monkeypatch, {f"/commits/H/{suf}": _llena(6)})  # 3 páginas llenas de 2: sin página corta
    assert len(p["gaps"]) == 1
    g = p["gaps"][0]
    assert "más de 3 páginas" in g and "lectura incompleta" in g and "PR #7" in g  # dice qué pasó sin stderr
    assert (p["checks"] == [] if que == "checks" else p["blind_review"] is None)


def test_justo_en_el_tope_con_pagina_corta_no_es_hueco(ce, monkeypatch):
    monkeypatch.setattr(ce, "MAX_PAGES", 3)
    p = _collect(ce, monkeypatch, {"/commits/H/check-runs": _llena(5)})  # páginas 2+2+1
    assert p["gaps"] == [] and len(p["checks"]) == 5


@pytest.mark.parametrize("suf", ["commits", "reviews"])
def test_tope_en_commits_y_reviews_sigue_propagando_en_modo_pr(ce, monkeypatch, suf):
    monkeypatch.setattr(ce, "MAX_PAGES", 3)
    items = [_commit(i, "x") if suf == "commits" else {"user": {"login": "a"}, "state": "COMMENTED"}
             for i in range(6)]
    with pytest.raises(ce.PagesLimitError):
        _collect(ce, monkeypatch, {f"/pulls/7/{suf}": items})


def test_mensaje_de_hueco_sin_stderr(ce, monkeypatch):
    def gh_json(path):
        if "/check-runs" in path:
            raise subprocess.CalledProcessError(1, ["gh", "api"], stderr=None)
        return FakeGh({})(path)
    monkeypatch.setattr(ce, "gh_json", gh_json)
    p = ce.collect_pr("o/r", 7)
    assert "no se pudieron leer los checks" in p["gaps"][0] and "gh" in p["gaps"][0]


@pytest.mark.parametrize("suf", ["commits", "reviews", "check-runs", "statuses"])
def test_release_con_tope_escribe_el_pack_con_hueco(ce, monkeypatch, tmp_path, suf):
    import argparse
    monkeypatch.setattr(ce, "MAX_PAGES", 3)
    monkeypatch.setattr(ce, "PER_PAGE", 2)
    monkeypatch.setattr(ce, "previous_tag", lambda tag: "v0")
    monkeypatch.setattr(ce, "repo_slug", lambda: "o/r")
    monkeypatch.setattr(ce, "git_range_commits", lambda rng: [
        {"sha": "a" * 40, "subject": "feat: algo (#7)", "author": "x", "tasks": []}])
    key = ("/pulls/7/" if suf in ("commits", "reviews") else "/commits/H/") + suf
    items = ([_commit(i, "x") for i in range(6)] if suf == "commits" else
             [{"user": {"login": "a"}, "state": "COMMENTED"}] * 6 if suf == "reviews" else _llena(6))
    monkeypatch.setattr(ce, "gh_json", FakeGh({key: items}))
    rc = ce.mode_release(argparse.Namespace(tag="v1", out=str(tmp_path), offline=False))
    assert rc == 0
    rec = json.loads((tmp_path / "change-record.json").read_text(encoding="utf-8"))
    assert any("más de 3 páginas" in g for g in rec["gaps"])
    assert (tmp_path / "change-record.md").exists()


def test_desempate_de_latest_status_por_id_con_mismo_created_at(ce):
    ctx = ce.BLIND_REVIEW_CONTEXT
    t = "2026-11-02T10:00:00Z"
    a = {"id": 10, "context": ctx, "state": "failure", "created_at": t}
    b = {"id": 11, "context": ctx, "state": "success", "created_at": t}
    assert ce.latest_status([a, b], ctx)["state"] == "success"
    assert ce.latest_status([b, a], ctx)["state"] == "success"
