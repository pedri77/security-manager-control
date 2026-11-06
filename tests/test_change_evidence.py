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


def _ultimos(runs):
    """Lo que devuelve la API de check-runs sin `filter=all` (por defecto `latest`): un run por (nombre, app)."""
    best: dict = {}
    for r in runs:
        k = (r["name"], (r.get("app") or {}).get("id"))
        if k not in best or (r.get("started_at") or "", r["id"]) > (best[k].get("started_at") or "", best[k]["id"]):
            best[k] = r
    return sorted(best.values(), key=lambda r: r["id"])


class FakeGh:
    """gh_json simulado: sirve cada lista troceada según per_page y page de la ruta.

    Imita a la API en check-runs: sin `filter=all` solo sirve el último run de cada (nombre, app);
    con `filter=all`, todos. Con `todo=True` ignora el filtro (simulador ingenuo, solo para la contraprueba).
    """

    def __init__(self, lists, fail=None, todo=False):
        self.lists = lists  # sufijo de ruta -> lista completa
        self.todo = todo
        self.paths: list[str] = []
        self.fail = fail or (lambda path, page: False)
        self.pr = {"head": {"sha": "H", "ref": "feat", "repo": {"full_name": "o/r"}}, "base": {"ref": "main"},
                   "user": {"login": "x"}, "title": "t", "html_url": "u", "body": ""}

    def __call__(self, path):
        from urllib.parse import parse_qs, urlparse
        self.paths.append(path)
        u = urlparse(path)
        q = parse_qs(u.query)
        per, page = int(q.get("per_page", ["30"])[0]), int(q.get("page", ["1"])[0])
        if self.fail(u.path, page):
            raise subprocess.CalledProcessError(1, "gh", stderr="gh: Server Error (HTTP 502)")
        if u.path.endswith("/pulls/7"):
            return self.pr
        for suf, lst in self.lists.items():
            if u.path.endswith(suf):
                if suf.endswith("check-runs") and not self.todo and q.get("filter") != ["all"]:
                    lst = _ultimos(lst)
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


# ───────────── cierre del FAIL de revisión ciega del PR #19 (SMC-005, T44) ─────────────
@pytest.mark.parametrize("orden", ORDENES)
def test_fallo_concluido_sin_started_at_supera_al_verde(ce, monkeypatch, orden):
    runs = _ordena([_run(1, "ci", "success", "2026-11-04T20:41:00Z"), _run(2, "ci", "failure", None)], orden)
    assert _conclusiones(_collect_runs(ce, monkeypatch, runs)) == [("ci", "failure")]


@pytest.mark.parametrize("orden", ORDENES)
def test_verde_sin_started_at_e_id_1_no_tapa_fallo_con_started_at_e_id_2(ce, monkeypatch, orden):
    runs = _ordena([_run(1, "ci", "success", None), _run(2, "ci", "failure", "2026-11-04T20:41:00Z")], orden)
    assert _conclusiones(_collect_runs(ce, monkeypatch, runs)) == [("ci", "failure")]


@pytest.mark.parametrize("orden", ORDENES)
def test_verde_sin_started_at_con_id_mayor_supera_al_fallo_anterior(ce, monkeypatch, orden):
    runs = _ordena([_run(1, "ci", "failure", "2026-11-04T20:41:00Z"), _run(2, "ci", "success", None)], orden)
    assert _conclusiones(_collect_runs(ce, monkeypatch, runs)) == [("ci", "success")]


@pytest.mark.parametrize("orden", ORDENES)
def test_run_en_cola_antiguo_con_id_menor_no_tapa_al_verde_mas_nuevo(ce, monkeypatch, orden):
    runs = _ordena([_run(1, "ci", None, None, status="queued"),
                    _run(2, "ci", "success", "2026-11-04T20:43:00Z")], orden)
    assert _conclusiones(_collect_runs(ce, monkeypatch, runs)) == [("ci", "success")]


def _release_con_runs(ce, monkeypatch, tmp_path, runs):
    import argparse
    monkeypatch.setattr(ce, "PER_PAGE", 100)
    monkeypatch.setattr(ce, "previous_tag", lambda tag: "v0")
    monkeypatch.setattr(ce, "repo_slug", lambda: "o/r")
    monkeypatch.setattr(ce, "git_range_commits", lambda rng: [
        {"sha": "a" * 40, "subject": "feat: algo (#7)", "author": "x", "tasks": []}])
    monkeypatch.setattr(ce, "gh_json", FakeGh({"/commits/H/check-runs": runs}))
    assert ce.mode_release(argparse.Namespace(tag="v1", out=str(tmp_path), offline=False)) == 0
    rec = json.loads((tmp_path / "change-record.json").read_text(encoding="utf-8"))
    return rec, [g for g in rec["gaps"] if "checks no exitosos" in g]


@pytest.mark.parametrize("orden", ORDENES)
def test_release_fallo_superado_por_verde_no_deja_hueco_de_checks(ce, monkeypatch, tmp_path, orden):
    # caso real del PR #11: el check falló y se relanzó en verde
    runs = _ordena([_run(1, "ci", "failure", "2026-11-04T20:41:00Z"),
                    _run(2, "ci", "success", "2026-11-04T20:43:00Z")], orden)
    rec, huecos = _release_con_runs(ce, monkeypatch, tmp_path, runs)
    assert huecos == []
    assert rec["changes"][0]["ci_status"] == "✅"


@pytest.mark.parametrize("orden", ORDENES)
def test_release_verde_superado_por_fallo_deja_hueco_de_checks(ce, monkeypatch, tmp_path, orden):
    runs = _ordena([_run(1, "ci", "success", "2026-11-04T20:41:00Z"),
                    _run(2, "ci", "failure", "2026-11-04T20:43:00Z")], orden)
    rec, huecos = _release_con_runs(ce, monkeypatch, tmp_path, runs)
    assert huecos == ["PR #7 con checks no exitosos: ci"]
    assert rec["changes"][0]["ci_status"] == "❌ ci"


@pytest.mark.parametrize("orden", ORDENES)
def test_release_fallo_sin_started_at_tras_verde_deja_hueco(ce, monkeypatch, tmp_path, orden):
    runs = _ordena([_run(1, "ci", "success", "2026-11-04T20:41:00Z"), _run(2, "ci", "failure", None)], orden)
    _, huecos = _release_con_runs(ce, monkeypatch, tmp_path, runs)
    assert huecos == ["PR #7 con checks no exitosos: ci"]


# ───────────── elección de check-run, corte en merged_at y reintento ante 5xx (SMC-007, T46) ─────────────
T41, T43, T45, MERGE = ("2026-11-04T20:41:00Z", "2026-11-04T20:43:00Z", "2026-11-04T20:45:00Z",
                        "2026-11-04T20:44:00Z")


def _elige(ce, runs):
    return [(r["name"], r["conclusion"]) for r in ce.latest_check_runs(runs)]


def _todos_los_ordenes(runs):
    import itertools
    return list(itertools.permutations(runs))


def test_caso_de_la_issue_run_sin_fecha_ajeno_no_cambia_la_eleccion(ce):
    # id 9 success 20:41, id 2 failure 20:43, id 1 sin started_at: gana el failure, en los 6 órdenes
    runs = [_run(9, "ci", "success", T41), _run(2, "ci", "failure", T43), _run(1, "ci", "success", None)]
    for orden in _todos_los_ordenes(runs):
        assert _elige(ce, list(orden)) == [("ci", "failure")]
    # y sin el tercero da lo mismo
    for orden in _todos_los_ordenes(runs[:2]):
        assert _elige(ce, list(orden)) == [("ci", "failure")]


def test_run_sin_fecha_con_id_mayor_que_algunos_pero_no_que_todos_no_gana(ce):
    # fechado id 9 viejo, fechado id 2 nuevo (ganador), sin fecha id 5: 5 > 2 pero < 9
    runs = [_run(9, "ci", "success", T41), _run(2, "ci", "failure", T43), _run(5, "ci", "success", None)]
    for orden in _todos_los_ordenes(runs):
        assert _elige(ce, list(orden)) == [("ci", "failure")]


def test_run_sin_fecha_con_id_mayor_que_todos_los_fechados_gana(ce):
    runs = [_run(9, "ci", "failure", T41), _run(2, "ci", "failure", T43), _run(10, "ci", "success", None)]
    for orden in _todos_los_ordenes(runs):
        assert _elige(ce, list(orden)) == [("ci", "success")]


def test_si_ninguno_tiene_fecha_gana_el_mayor_id(ce):
    runs = [_run(3, "ci", "failure", None), _run(7, "ci", "success", None), _run(5, "ci", "failure", None)]
    for orden in _todos_los_ordenes(runs):
        assert _elige(ce, list(orden)) == [("ci", "success")]


def test_varios_sin_fecha_con_id_mayor_gana_el_mayor_de_ellos(ce):
    runs = [_run(1, "ci", "failure", T43), _run(4, "ci", "failure", None), _run(6, "ci", "success", None)]
    for orden in _todos_los_ordenes(runs):
        assert _elige(ce, list(orden)) == [("ci", "success")]


def test_run_sin_fecha_de_otro_grupo_no_afecta(ce):
    runs = [_run(1, "a", "success", T41), _run(2, "a", "failure", T43), _run(99, "b", None, None, status="queued")]
    assert sorted(_elige(ce, runs)) == [("a", "failure"), ("b", None)]


# --- corte en merged_at ---
def _collect_merged(ce, monkeypatch, runs, merged_at=MERGE):
    gh = FakeGh({"/commits/H/check-runs": runs})
    if merged_at:
        gh.pr["merged_at"] = merged_at
    monkeypatch.setattr(ce, "gh_json", gh)
    monkeypatch.setattr(ce, "PER_PAGE", 100)
    return ce.collect_pr("o/r", 7)


@pytest.mark.parametrize("orden", ORDENES)
def test_pr_fusionado_la_repeticion_verde_posterior_no_sustituye_al_rojo(ce, monkeypatch, orden):
    runs = _ordena([_run(1, "ci", "failure", T41), _run(2, "ci", "success", T45)], orden)
    p = _collect_merged(ce, monkeypatch, runs)
    assert _conclusiones(p) == [("ci", "failure")] and p["gaps"] == []


@pytest.mark.parametrize("orden", ORDENES)
def test_pr_sin_fusionar_la_misma_repeticion_gana(ce, monkeypatch, orden):
    runs = _ordena([_run(1, "ci", "failure", T41), _run(2, "ci", "success", T45)], orden)
    p = _collect_merged(ce, monkeypatch, runs, merged_at=None)
    assert _conclusiones(p) == [("ci", "success")] and p["gaps"] == []


def test_run_iniciado_justo_en_merged_at_se_queda(ce, monkeypatch):
    runs = [_run(1, "ci", "failure", T41), _run(2, "ci", "success", MERGE)]
    assert _conclusiones(_collect_merged(ce, monkeypatch, runs)) == [("ci", "success")]


def test_run_sin_started_at_se_queda_en_pr_fusionado(ce, monkeypatch):
    runs = [_run(1, "ci", "success", T41), _run(2, "ci", "failure", None)]
    assert _conclusiones(_collect_merged(ce, monkeypatch, runs)) == [("ci", "failure")]


def test_check_solo_posterior_al_merge_sale_de_checks_y_deja_hueco(ce, monkeypatch):
    runs = [_run(1, "ci", "success", T41), _run(2, "tardio", "success", T45)]
    p = _collect_merged(ce, monkeypatch, runs)
    assert _conclusiones(p) == [("ci", "success")]
    assert len(p["gaps"]) == 1 and "PR #7" in p["gaps"][0] and "tardio" in p["gaps"][0]


def test_hueco_por_corte_aparece_en_el_pack_de_release(ce, monkeypatch, tmp_path):
    runs = [_run(2, "tardio", "success", T45)]
    gh = FakeGh({"/commits/H/check-runs": runs})
    gh.pr["merged_at"] = MERGE
    import argparse
    monkeypatch.setattr(ce, "PER_PAGE", 100)
    monkeypatch.setattr(ce, "previous_tag", lambda tag: "v0")
    monkeypatch.setattr(ce, "repo_slug", lambda: "o/r")
    monkeypatch.setattr(ce, "git_range_commits", lambda rng: [
        {"sha": "a" * 40, "subject": "feat: algo (#7)", "author": "x", "tasks": []}])
    monkeypatch.setattr(ce, "gh_json", gh)
    ce.mode_release(argparse.Namespace(tag="v1", out=str(tmp_path), offline=False))
    rec = json.loads((tmp_path / "change-record.json").read_text(encoding="utf-8"))
    assert any("tardio" in g and "PR #7" in g for g in rec["gaps"])


def test_pr_fusionado_sin_checks_no_inventa_hueco(ce, monkeypatch):
    p = _collect_merged(ce, monkeypatch, [])
    assert p["checks"] == [] and p["gaps"] == []


# --- reintento ante 5xx en gh_json ---
def _gh_simulado(ce, monkeypatch, resultados):
    """Parchea run(): cada llamada consume un resultado (str = salida, str 'gh: ...' en Exception = fallo)."""
    llamadas, esperas = [], []

    def run(cmd):
        llamadas.append(cmd)
        r = resultados[len(llamadas) - 1]
        if isinstance(r, str):
            return r
        raise subprocess.CalledProcessError(1, cmd, stderr=r.args[0])
    monkeypatch.setattr(ce, "run", run)
    monkeypatch.setattr(ce.time, "sleep", lambda s: esperas.append(s))
    return llamadas, esperas


def _err(msg):
    return Exception(msg)


def test_500_y_luego_exito_reintenta_una_vez(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err("gh: Server Error (HTTP 500)"), '{"ok": 1}'])
    assert ce.gh_json("x") == {"ok": 1}
    assert len(llamadas) == 2 and len(esperas) == 1 and 0 < esperas[0] <= 5


def test_dos_500_y_luego_exito(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err("gh: Bad Gateway (HTTP 502)"),
                                                       _err("gh: Unavailable (HTTP 503)"), '[1]'])
    assert ce.gh_json("x") == [1] and len(llamadas) == 3 and len(esperas) == 2


def test_tres_500_son_tres_llamadas_y_propaga_el_ultimo_error(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err("gh: a (HTTP 500)"), _err("gh: b (HTTP 502)"),
                                                       _err("gh: c (HTTP 503)"), '{"no": 0}'])
    with pytest.raises(subprocess.CalledProcessError) as ei:
        ce.gh_json("x")
    assert len(llamadas) == 3 and len(esperas) == 2 and "(HTTP 503)" in ei.value.stderr


def test_tres_500_en_collect_pr_dejan_hueco(ce, monkeypatch):
    esperas = []
    monkeypatch.setattr(ce.time, "sleep", lambda s: esperas.append(s))
    fake = FakeGh({})

    def run(cmd):
        path = cmd[-1]
        if "/check-runs" in path:
            raise subprocess.CalledProcessError(1, cmd, stderr="gh: Server Error (HTTP 500)")
        return json.dumps(fake(path))
    monkeypatch.setattr(ce, "run", run)
    p = ce.collect_pr("o/r", 7)
    assert any("no se pudieron leer los checks" in g and "HTTP 500" in g for g in p["gaps"])
    assert len(esperas) == 2


@pytest.mark.parametrize("msg", ["gh: Forbidden (HTTP 403)", "gh: Not Found (HTTP 404)", "gh: Gone (HTTP 410)"])
def test_403_y_404_fallan_a_la_primera_sin_sleep(ce, monkeypatch, msg):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err(msg), '{"ok": 1}'])
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("x")
    assert len(llamadas) == 1 and esperas == []


def test_403_cuyo_mensaje_contiene_http_500_no_se_reintenta(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err("gh: upstream said HTTP 500 earlier (HTTP 403)"),
                                                       '{"ok": 1}'])
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("x")
    assert len(llamadas) == 1 and esperas == []


def test_error_sin_codigo_http_no_se_reintenta(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err("gh: connection reset"), '{"ok": 1}'])
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("x")
    assert len(llamadas) == 1 and esperas == []


def test_error_con_stderr_none_no_rompe_ni_se_reintenta(ce, monkeypatch):
    llamadas = []

    def run(cmd):
        llamadas.append(cmd)
        raise subprocess.CalledProcessError(1, cmd, stderr=None)
    monkeypatch.setattr(ce, "run", run)
    monkeypatch.setattr(ce.time, "sleep", lambda s: pytest.fail("no debe esperar"))
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("x")
    assert len(llamadas) == 1


def test_exito_a_la_primera_no_espera(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, ['{"ok": 1}'])
    assert ce.gh_json("x") == {"ok": 1} and len(llamadas) == 1 and esperas == []


# --- T47: formatos reales de stderr de gh 2.89.0 (copiados de la salida medida contra un servidor local) ---
# Con cuerpo JSON con `message`: «gh: Server Error (HTTP 500)». Con HTML, vacío o JSON sin `message`: «gh: HTTP 502».
@pytest.mark.parametrize("stderr,esperado", [
    ("gh: Server Error (HTTP 500)\n", 500),
    ("gh: HTTP 500\n", 500),   # cuerpo JSON `{}` sin message
    ("gh: HTTP 502\n", 502),   # cuerpo HTML
    ("gh: HTTP 503\n", 503),   # cuerpo HTML
    ("gh: HTTP 504\n", 504),   # cuerpo vacío
    ("gh: HTTP 404\n", 404),
    ("gh: HTTP 403\n", 403),
    ("gh: connection reset", None),
    ("", None),
])
def test_http_status_reconoce_los_dos_formatos_de_gh(ce, stderr, esperado):
    e = subprocess.CalledProcessError(1, "gh", stderr=stderr)
    assert ce.http_status(e) == esperado


@pytest.mark.parametrize("stderr", ["gh: HTTP 502\n", "gh: HTTP 503\n", "gh: HTTP 504\n", "gh: HTTP 500\n"])
def test_5xx_sin_parentesis_se_reintenta_hasta_tres_llamadas(ce, monkeypatch, stderr):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err(stderr), _err(stderr), _err(stderr), '{"no": 0}'])
    with pytest.raises(subprocess.CalledProcessError) as ei:
        ce.gh_json("x")
    assert len(llamadas) == 3 and len(esperas) == 2 and ei.value.stderr == stderr


def test_502_sin_parentesis_y_luego_exito(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err("gh: HTTP 502\n"), '{"ok": 1}'])
    assert ce.gh_json("x") == {"ok": 1} and len(llamadas) == 2 and len(esperas) == 1


def test_503_sin_parentesis_y_luego_502_y_exito(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err("gh: HTTP 503\n"), _err("gh: HTTP 502\n"), '[1]'])
    assert ce.gh_json("x") == [1] and len(llamadas) == 3 and len(esperas) == 2


@pytest.mark.parametrize("stderr", ["gh: HTTP 404\n", "gh: HTTP 403\n"])
def test_404_y_403_sin_parentesis_fallan_a_la_primera(ce, monkeypatch, stderr):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err(stderr), '{"ok": 1}'])
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("x")
    assert len(llamadas) == 1 and esperas == []


def test_dos_codigos_en_stderr_cuenta_el_ultimo(ce, monkeypatch):
    e = subprocess.CalledProcessError(1, "gh", stderr="gh: HTTP 500\ngh: Not Found (HTTP 404)\n")
    assert ce.http_status(e) == 404
    e = subprocess.CalledProcessError(1, "gh", stderr="gh: Not Found (HTTP 404)\ngh: HTTP 502\n")
    assert ce.http_status(e) == 502
    e = subprocess.CalledProcessError(1, "gh", stderr="gh: cita HTTP 500 antes (HTTP 403)\n")
    assert ce.http_status(e) == 403


def test_dos_codigos_el_ultimo_404_no_se_reintenta_aunque_el_primero_sea_5xx(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err("gh: HTTP 500\ngh: Not Found (HTTP 404)\n"), '{"ok": 1}'])
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("x")
    assert len(llamadas) == 1 and esperas == []


def test_dos_codigos_el_ultimo_5xx_se_reintenta_aunque_el_primero_sea_404(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err("gh: Not Found (HTTP 404)\ngh: HTTP 502\n"), '{"ok": 1}'])
    assert ce.gh_json("x") == {"ok": 1} and len(llamadas) == 2 and len(esperas) == 1


def test_502_sin_parentesis_en_collect_pr_deja_hueco_tras_tres_llamadas(ce, monkeypatch):
    esperas, llamadas = [], []
    monkeypatch.setattr(ce.time, "sleep", lambda s: esperas.append(s))
    fake = FakeGh({})

    def run(cmd):
        path = cmd[-1]
        if "/check-runs" in path:
            llamadas.append(path)
            raise subprocess.CalledProcessError(1, cmd, stderr="gh: HTTP 502\n")
        return json.dumps(fake(path))
    monkeypatch.setattr(ce, "run", run)
    p = ce.collect_pr("o/r", 7)
    assert any("no se pudieron leer los checks" in g and "HTTP 502" in g for g in p["gaps"])
    assert len(llamadas) == 3 and len(esperas) == 2


# --- T47: corte en merged_at por instante, no por texto ---
def test_corte_con_merged_at_en_otro_huso_cuenta_el_instante(ce, monkeypatch):
    # 20:44+01:00 = 19:44Z. El run de 19:45Z es posterior (como texto «19:45» < «20:44+01:00» se quedaría).
    runs = [_run(1, "ci", "failure", "2026-11-04T19:41:00Z"), _run(2, "ci", "success", "2026-11-04T19:45:00Z")]
    p = _collect_merged(ce, monkeypatch, runs, merged_at="2026-11-04T20:44:00+01:00")
    assert _conclusiones(p) == [("ci", "failure")] and p["gaps"] == []


def test_corte_con_started_at_en_otro_huso_cuenta_el_instante(ce, monkeypatch):
    # started 20:30+01:00 = 19:30Z, anterior al merge 19:44Z; como texto «20:30» > «19:44» se descartaría.
    runs = [_run(1, "ci", "failure", "2026-11-04T20:30:00+01:00"), _run(2, "ci", "success", "2026-11-04T19:50:00Z")]
    p = _collect_merged(ce, monkeypatch, runs, merged_at="2026-11-04T19:44:00Z")
    assert _conclusiones(p) == [("ci", "failure")] and p["gaps"] == []


def test_corte_en_otro_huso_igual_al_merged_at_se_queda(ce, monkeypatch):
    runs = [_run(1, "ci", "failure", "2026-11-04T19:44:00Z"), _run(2, "ci", "success", "2026-11-04T20:44:00+01:00")]
    p = _collect_merged(ce, monkeypatch, runs, merged_at="2026-11-04T19:44:00Z")
    assert _conclusiones(p) == [("ci", "success")]


# --- T47: dos apps con el mismo nombre de check ---
def test_dos_apps_homonimas_solo_la_que_se_queda_sin_runs_deja_hueco(ce, monkeypatch):
    runs = [_run(1, "ci", "success", T41, app=1), _run(2, "ci", "success", T45, app=2)]
    p = _collect_merged(ce, monkeypatch, runs)
    assert _conclusiones(p) == [("ci", "success")]
    assert len(p["gaps"]) == 1 and "PR #7" in p["gaps"][0] and "ci" in p["gaps"][0]


def test_dos_apps_homonimas_ambas_con_runs_previos_no_dejan_hueco(ce, monkeypatch):
    runs = [_run(1, "ci", "success", T41, app=1), _run(2, "ci", "failure", T41, app=2),
            _run(3, "ci", "success", T45, app=2)]
    p = _collect_merged(ce, monkeypatch, runs)
    assert sorted(_conclusiones(p)) == [("ci", "failure"), ("ci", "success")]
    assert p["gaps"] == []


# --- T48: 5xx de cuerpo vacío con Content-Type JSON ---
# `gh` 2.89.0 real (cuerpo vacío + application/json, cualquier estado): stderr «unexpected end of JSON input\n»,
# sin «gh:» ni código, código de salida 1. Con cuerpo no vacío que cita el texto: «gh: <texto> (HTTP 403)\n».
VACIO = "unexpected end of JSON input\n"


@pytest.mark.parametrize("stderr", [VACIO, "unexpected end of JSON input"])
def test_cuerpo_vacio_json_se_reintenta_hasta_tres_llamadas(ce, monkeypatch, stderr):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err(stderr), _err(stderr), _err(stderr), '{"no": 0}'])
    with pytest.raises(subprocess.CalledProcessError) as ei:
        ce.gh_json("x")
    assert len(llamadas) == 3 and len(esperas) == 2 and ei.value.stderr == stderr


def test_cuerpo_vacio_json_y_luego_exito(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err(VACIO), '{"ok": 1}'])
    assert ce.gh_json("x") == {"ok": 1} and len(llamadas) == 2 and len(esperas) == 1 and 0 < esperas[0] <= 5


def test_cuerpo_vacio_json_dos_veces_y_luego_exito(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err(VACIO), _err(VACIO), '[1]'])
    assert ce.gh_json("x") == [1] and len(llamadas) == 3 and len(esperas) == 2


def test_cuerpo_vacio_json_mezclado_con_5xx_con_codigo(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err(VACIO), _err("gh: HTTP 502\n"), '[1]'])
    assert ce.gh_json("x") == [1] and len(llamadas) == 3


@pytest.mark.parametrize("stderr", [
    "gh: unexpected end of JSON input (HTTP 403)\n",   # 403 con cuerpo JSON {"message": "unexpected end of JSON input"}
    "gh: unexpected end of JSON input (HTTP 404)\n",
    "gh: HTTP 404\nunexpected end of JSON input cita\n",
    "gh: HTTP 403\n",
])
def test_con_codigo_no_5xx_y_cita_del_texto_falla_a_la_primera(ce, monkeypatch, stderr):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err(stderr), '{"ok": 1}'])
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("x")
    assert len(llamadas) == 1 and esperas == []


@pytest.mark.parametrize("stderr", [
    "gh: unexpected end of JSON input (HTTP 403)\n",
    "gh: unexpected end of JSON input (HTTP 404)\n",
])
def test_http_status_reconoce_el_codigo_cuando_el_cuerpo_cita_el_texto(ce, stderr):
    e = subprocess.CalledProcessError(1, "gh", stderr=stderr)
    assert ce.http_status(e) in (403, 404)


@pytest.mark.parametrize("stderr", [
    "error: unexpected end of JSON input\n",
    "gh: unexpected end of JSON input.\n",
    "Unexpected end of JSON input\n",
    "unexpected end of JSON input extra\n",
    "x unexpected end of JSON input\n",
    "gh: connection reset\n",
    "",
])
def test_otros_textos_no_se_reintentan(ce, monkeypatch, stderr):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err(stderr), '{"ok": 1}'])
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("x")
    assert len(llamadas) == 1 and esperas == []


def test_linea_exacta_entre_otras_lineas_se_reintenta(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err("aviso previo\nunexpected end of JSON input\n"), '{"ok": 1}'])
    assert ce.gh_json("x") == {"ok": 1} and len(llamadas) == 2


def test_json_loads_que_falla_sobre_salida_correcta_no_se_reintenta(ce, monkeypatch):
    llamadas = []

    def run(cmd):
        llamadas.append(cmd)
        return "no es json"
    monkeypatch.setattr(ce, "run", run)
    monkeypatch.setattr(ce.time, "sleep", lambda s: pytest.fail("no debe esperar"))
    with pytest.raises(json.JSONDecodeError):
        ce.gh_json("x")
    assert len(llamadas) == 1


def test_cuerpo_vacio_json_en_collect_pr_deja_hueco_tras_tres_llamadas(ce, monkeypatch):
    esperas, llamadas = [], []
    monkeypatch.setattr(ce.time, "sleep", lambda s: esperas.append(s))
    fake = FakeGh({})

    def run(cmd):
        path = cmd[-1]
        if "/check-runs" in path:
            llamadas.append(path)
            raise subprocess.CalledProcessError(1, cmd, stderr=VACIO)
        return json.dumps(fake(path))
    monkeypatch.setattr(ce, "run", run)
    p = ce.collect_pr("o/r", 7)
    assert any("no se pudieron leer los checks" in g and "unexpected end of JSON input" in g for g in p["gaps"])
    assert len(llamadas) == 3 and len(esperas) == 2


# --- T49: filter=all (la API sin filtro solo devuelve el último run de cada check) ---
def test_simulador_sin_filter_all_sirve_solo_el_ultimo_run(ce):
    runs = [_run(1, "ci", "failure", T41), _run(2, "ci", "success", T45), _run(3, "otro", "success", T41)]
    gh = FakeGh({"/commits/H/check-runs": runs})
    sin = gh("repos/o/r/commits/H/check-runs?per_page=100&page=1")["check_runs"]
    con = gh("repos/o/r/commits/H/check-runs?filter=all&per_page=100&page=1")["check_runs"]
    assert [r["id"] for r in sin] == [2, 3] and [r["id"] for r in con] == [1, 2, 3]


def test_collect_pr_pide_check_runs_con_filter_all_en_cada_pagina(ce, monkeypatch):
    monkeypatch.setattr(ce, "PER_PAGE", 2)
    gh = FakeGh({"/commits/H/check-runs": [_run(i, f"c{i}", "success", T41) for i in range(1, 6)]})
    monkeypatch.setattr(ce, "gh_json", gh)
    p = ce.collect_pr("o/r", 7)
    pedidas = [x for x in gh.paths if "/check-runs" in x]
    assert len(pedidas) == 3 and all("filter=all" in x for x in pedidas)
    assert len(p["checks"]) == 5


def test_pr_fusionado_rojo_al_fusionar_y_repeticion_verde_deja_el_rojo_sin_hueco(ce, monkeypatch):
    p = _collect_merged(ce, monkeypatch, [_run(1, "ci", "failure", T41), _run(2, "ci", "success", T45)])
    assert _conclusiones(p) == [("ci", "failure")] and p["gaps"] == []


def test_pr_fusionado_verde_al_fusionar_y_repeticion_posterior_deja_el_verde_sin_hueco(ce, monkeypatch):
    p = _collect_merged(ce, monkeypatch, [_run(1, "ci", "success", T41), _run(2, "ci", "failure", T45)])
    assert _conclusiones(p) == [("ci", "success")] and p["gaps"] == []


def test_pr_fusionado_check_que_solo_corrio_tras_el_merge_deja_hueco_con_simulador_fiel(ce, monkeypatch):
    p = _collect_merged(ce, monkeypatch, [_run(1, "ci", "success", T41), _run(2, "tardio", "success", T45)])
    assert _conclusiones(p) == [("ci", "success")]
    assert len(p["gaps"]) == 1 and "tardio" in p["gaps"][0]


def test_simulador_ingenuo_no_distingue_el_filtro(ce, monkeypatch):
    # Contraprueba documentada: un simulador que sirve todo sin mirar el filtro da el mismo resultado
    # con y sin `filter=all`, así que el test de rojo al fusionar no detectaría que falta el filtro.
    runs = [_run(1, "ci", "failure", T41), _run(2, "ci", "success", T45)]
    gh = FakeGh({"/commits/H/check-runs": runs}, todo=True)
    a = gh("repos/o/r/commits/H/check-runs?per_page=100&page=1")["check_runs"]
    b = gh("repos/o/r/commits/H/check-runs?filter=all&per_page=100&page=1")["check_runs"]
    assert a == b == runs


# --- T49: el código manda sobre el texto de cuerpo vacío ---
def test_404_seguido_de_cuerpo_vacio_falla_a_la_primera(ce, monkeypatch):
    stderr = "gh: HTTP 404\nunexpected end of JSON input\n"
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err(stderr), '{"ok": 1}'])
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("x")
    assert len(llamadas) == 1 and esperas == []


def test_403_que_cita_http_500_tras_el_codigo_real_falla_a_la_primera(ce, monkeypatch):
    stderr = "gh: Forbidden (HTTP 403)\nel mensaje cita HTTP 500 de otro intento\n"
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [_err(stderr), '{"ok": 1}'])
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("x")
    assert len(llamadas) == 1 and esperas == []
