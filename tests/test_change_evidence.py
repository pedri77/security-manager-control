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
    items[0]["context"] = ce.BLIND_REVIEW_CONTEXT  # blind-review en success en la primera página
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
    items = _llena(6)
    items[0]["context"] = ce.BLIND_REVIEW_CONTEXT  # blind-review en success que debe descartarse
    p = _collect(ce, monkeypatch, {f"/commits/H/{suf}": items})  # 3 páginas llenas de 2: sin página corta
    assert len(p["gaps"]) == 1
    g = p["gaps"][0]
    assert "más de 3 páginas" in g and "lectura incompleta" in g and "PR #7" in g  # dice qué pasó sin stderr
    assert (p["checks"] == [] if que == "checks" else p["blind_review"] is None)


def test_justo_en_el_tope_con_pagina_corta_no_es_hueco(ce, monkeypatch):
    monkeypatch.setattr(ce, "MAX_PAGES", 3)
    p = _collect(ce, monkeypatch, {"/commits/H/check-runs": _llena(5)})  # páginas 2+2+1
    assert p["gaps"] == [] and len(p["checks"]) == 5


@pytest.mark.parametrize("suf", ["commits", "reviews"])
def test_tope_en_commits_y_reviews_sigue_propagando_en_modo_pr(ce, monkeypatch, tmp_path, suf):
    import argparse
    monkeypatch.setattr(ce, "MAX_PAGES", 3)
    monkeypatch.setattr(ce, "PER_PAGE", 2)
    monkeypatch.setattr(ce, "repo_slug", lambda: "o/r")
    items = [_commit(i, "x") if suf == "commits" else {"user": {"login": "a"}, "state": "COMMENTED"}
             for i in range(6)]
    monkeypatch.setattr(ce, "gh_json", FakeGh({f"/pulls/7/{suf}": items}))
    with pytest.raises(ce.PagesLimitError):
        ce.mode_pr(argparse.Namespace(pr=7, out=str(tmp_path)))
    assert not (tmp_path / "change-record.json").exists()


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


# ───────────── huecos fiables (SMC-005, T43) ─────────────
def _run(i, name, concl, started, app=1, **kw):
    r = {"id": i, "name": name, "conclusion": concl, "status": "completed" if concl else "in_progress",
         "started_at": started, "app": {"id": app}}
    r.update(kw)
    return r


def _collect_runs(ce, monkeypatch, runs):
    return _collect(ce, monkeypatch, {"/commits/H/check-runs": runs}, per=100)


def _conclusiones(p):
    return [(c["name"], c["conclusion"]) for c in p["checks"]]  # lista: un duplicado no se esconde


def _con_commits_totales(ce, monkeypatch, total, leidos, **extra):
    commits = [_commit(i, "x") for i in range(leidos)]
    gh = FakeGh({"/pulls/7/commits": commits})
    if total is not None:
        gh.pr["commits"] = total
    monkeypatch.setattr(ce, "gh_json", gh)
    monkeypatch.setattr(ce, "PER_PAGE", 100)
    return ce.collect_pr("o/r", 7)


def test_commits_truncados_dejan_hueco_con_leidos_y_totales(ce, monkeypatch):
    p = _con_commits_totales(ce, monkeypatch, 300, 250)
    assert len(p["gaps"]) == 1
    g = p["gaps"][0]
    assert "PR #7" in g and "250" in g and "300" in g


@pytest.mark.parametrize("total", [250, 3, None])
def test_commits_completos_o_sin_total_no_dejan_hueco(ce, monkeypatch, total):
    leidos = 250 if total == 250 else 3
    p = _con_commits_totales(ce, monkeypatch, total, leidos)
    assert p["gaps"] == []


ORDENES = ["nuevo_primero", "viejo_primero"]


def _ordena(lst, orden):
    return lst if orden == "viejo_primero" else list(reversed(lst))


@pytest.mark.parametrize("orden", ORDENES)
def test_fallo_superado_por_verde_no_deja_check_fallido(ce, monkeypatch, orden):
    runs = _ordena([_run(1, "ci", "failure", "2026-11-04T20:41:00Z"),
                    _run(2, "ci", "success", "2026-11-04T20:43:00Z")], orden)
    assert _conclusiones(_collect_runs(ce, monkeypatch, runs)) == [("ci", "success")]


@pytest.mark.parametrize("orden", ORDENES)
def test_verde_superado_por_fallo_cuenta_el_fallo(ce, monkeypatch, orden):
    runs = _ordena([_run(1, "ci", "success", "2026-11-04T20:41:00Z"),
                    _run(2, "ci", "failure", "2026-11-04T20:43:00Z")], orden)
    assert _conclusiones(_collect_runs(ce, monkeypatch, runs)) == [("ci", "failure")]


@pytest.mark.parametrize("orden", ORDENES)
def test_verde_superado_por_check_en_curso_no_se_da_por_bueno(ce, monkeypatch, orden):
    runs = _ordena([_run(1, "ci", "success", "2026-11-04T20:41:00Z"),
                    _run(2, "ci", None, "2026-11-04T20:43:00Z")], orden)
    assert _conclusiones(_collect_runs(ce, monkeypatch, runs)) == [("ci", "in_progress")]


def test_started_at_manda_sobre_id(ce, monkeypatch):
    # el id mayor es el más antiguo: solo started_at lo distingue
    runs = [_run(9, "ci", "failure", "2026-11-04T20:41:00Z"), _run(2, "ci", "success", "2026-11-04T20:43:00Z")]
    assert _conclusiones(_collect_runs(ce, monkeypatch, runs)) == [("ci", "success")]


def test_id_desempata_con_mismo_started_at(ce, monkeypatch):
    t = "2026-11-04T20:41:00Z"
    for runs in ([_run(1, "ci", "failure", t), _run(2, "ci", "success", t)],
                 [_run(2, "ci", "success", t), _run(1, "ci", "failure", t)]):
        assert _conclusiones(_collect_runs(ce, monkeypatch, runs)) == [("ci", "success")]


def test_dos_apps_con_el_mismo_nombre_cuentan_por_separado(ce, monkeypatch):
    runs = [_run(1, "ci", "failure", "2026-11-04T20:41:00Z", app=10),
            _run(2, "ci", "success", "2026-11-04T20:43:00Z", app=20)]
    p = _collect_runs(ce, monkeypatch, runs)
    assert sorted((c["name"], c["conclusion"]) for c in p["checks"]) == [("ci", "failure"), ("ci", "success")]


def test_check_run_sin_app_no_rompe_y_se_deduplica(ce, monkeypatch):
    a = _run(1, "ci", "failure", "2026-11-04T20:41:00Z")
    b = _run(2, "ci", "success", "2026-11-04T20:43:00Z")
    del a["app"]
    b["app"] = None
    assert _conclusiones(_collect_runs(ce, monkeypatch, [a, b])) == [("ci", "success")]


def test_formato_de_checks_sin_campos_nuevos_y_ordenado_por_nombre(ce, monkeypatch):
    runs = [_run(1, "b", "success", "2026-11-04T20:41:00Z"), _run(2, "a", "failure", "2026-11-04T20:41:00Z")]
    p = _collect_runs(ce, monkeypatch, runs)
    assert p["checks"] == [{"name": "a", "conclusion": "failure"}, {"name": "b", "conclusion": "success"}]


@pytest.mark.parametrize("orden", ORDENES)
def test_check_en_curso_sin_started_at_supera_al_verde(ce, monkeypatch, orden):
    runs = _ordena([_run(1, "ci", "success", "2026-11-04T20:41:00Z"), _run(2, "ci", None, None)], orden)
    assert _conclusiones(_collect_runs(ce, monkeypatch, runs)) == [("ci", "in_progress")]
