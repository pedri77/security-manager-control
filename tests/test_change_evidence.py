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


# ───────────── salida de `gh api -i` (gh 2.89.0), medida el 2026-11-06 contra un servidor local ─────────────
# En bytes, `gh` termina la línea de estado con «\n», cada cabecera con «\r\n» y separa cabeceras y cuerpo con
# «\r\n\r\n». `subprocess.run(text=True)` traduce todo «\r\n» a «\n»: el script lee «\n\n». Con cuerpo vacío la salida
# termina en «\n\n», y `run()` la deja sin separador por su `.strip()`. En un fallo (código >= 400) el estado va en
# stdout, junto al cuerpo (vacío si `gh` no lo pudo leer como JSON); stderr lleva el mensaje.
RAZON = {200: "OK", 403: "Forbidden", 404: "Not Found", 500: "Internal Server Error", 502: "Bad Gateway",
         503: "Service Unavailable", 504: "Gateway Timeout"}
FECHA_Y_SERVIDOR = "Date: Fri, 06 Nov 2026 05:41:16 GMT\nServer: BaseHTTP Python/3.15.0\n"
# tipo de cuerpo -> (Content-Type, cuerpo servido, cuerpo que `gh` deja en stdout, stderr medido; {c} = código)
CUERPOS = {
    "json": ("application/json", '{"message":"Server Error"}', '{"message":"Server Error"}', "gh: Server Error (HTTP {c})\n"),
    "objeto": ("application/json", "{}", "{}", "gh: HTTP {c}\n"),
    "errors": ("application/json", '{"errors":[]}', '{"errors":[]}', "gh: HTTP {c}\n"),
    "html": ("text/html", "<html>Unicorn</html>", "<html>Unicorn</html>", "gh: HTTP {c}\n"),
    "vacio_texto": ("text/plain", "", "", "gh: HTTP {c}\n"),
    "vacio_json": ("application/json", "", "", "unexpected end of JSON input\n"),
    "no_json": ("application/json", "not json at all", "",
                "invalid character 'o' in literal null (expecting 'u')\n"),
    "truncado": ("application/json", '{"message":"Ser', "", "unexpected end of JSON input\n"),
    "espacios": ("application/json", "   ", "", "unexpected end of JSON input\n"),
}
ESTADOS_5XX = [500, 502, 503]
ESTADOS_NO_5XX = [403, 404]


def gh_i(codigo, tipo="json"):
    """(stdout, stderr) de `gh api -i` con ese estado y ese cuerpo, como los lee subprocess con text=True."""
    ct, servido, eco, stderr = CUERPOS[tipo]
    cab = f"HTTP/1.1 {codigo} {RAZON[codigo]}\nContent-Length: {len(servido)}\nContent-Type: {ct}\n{FECHA_Y_SERVIDOR}\n"
    return cab + eco, stderr.format(c=codigo)


def exito(cuerpo):
    """stdout de un 200 tal como lo devuelve `run()` (con `.strip()`)."""
    cab = f"HTTP/1.1 200 OK\nContent-Length: {len(cuerpo)}\nContent-Type: application/json\n{FECHA_Y_SERVIDOR}\n"
    return (cab + cuerpo).strip()


def fallo(codigo, tipo="json", cmd="gh"):
    out, err = gh_i(codigo, tipo)
    return subprocess.CalledProcessError(1, cmd, output=out, stderr=err)


def fallo_red(cmd="gh"):
    """Sin respuesta HTTP (conexión rechazada): stdout vacío y el error de red en stderr (medido)."""
    return subprocess.CalledProcessError(
        1, cmd, output="", stderr='Get "http://127.0.0.1:1/refused": dial tcp 127.0.0.1:1: connect: connection refused\n')


def _falla_api(mod, monkeypatch, error):
    def gh_json(path):
        raise error
    monkeypatch.setattr(mod, "gh_json", gh_json)


def test_comentario_sin_cerrar_no_declara_issue(ce):
    assert ce.extract_issues("Closes #2\n<!-- Closes #1") == [2]
    assert ce.extract_tasks("<!-- Task: SMC-001") == []


def test_config_ausente_deja_solo_los_ficheros_fijos(ce, monkeypatch):
    _falla_api(ce, monkeypatch, fallo(404))
    assert ce.allowed_release_files("o/r", "main") == ce.RELEASE_FILES


@pytest.mark.parametrize("stderr", ["gh: Forbidden (HTTP 403)\n", "gh: API rate limit exceeded for ID 74045. (HTTP 403)\n"])
def test_error_de_api_no_se_confunde_con_config_ausente(ce, monkeypatch, stderr):
    out, _ = gh_i(403)
    _falla_api(ce, monkeypatch, subprocess.CalledProcessError(1, "gh", output=out, stderr=stderr))
    with pytest.raises(subprocess.CalledProcessError):
        ce.allowed_release_files("o/r", "main")


def test_error_al_detectar_pr_de_release_queda_como_hueco(ce, monkeypatch):
    pr = {"head": {"sha": "abc", "ref": "release-please--branches--main", "repo": {"full_name": "o/r"}},
          "base": {"ref": "main"}, "user": {"login": "x"}, "title": "t", "html_url": "u", "body": ""}

    def gh_json(path):
        if path.endswith("/files?per_page=100"):
            raise fallo(502)
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
        raise fallo(404)
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
    """Lo que devuelve la API de check-runs sin `filter=all` (por defecto `latest`): el último run de cada
    (nombre, check suite). Medido con GET real en cli/cli: 19 suites con el mismo nombre y la misma app dan 19 runs."""
    best: dict = {}
    for r in runs:
        k = (r["name"], (r.get("check_suite") or {}).get("id"))
        if k not in best or (r.get("started_at") or "", r["id"]) > (best[k].get("started_at") or "", best[k]["id"]):
            best[k] = r
    return sorted(best.values(), key=lambda r: r["id"])


class FakeGh:
    """gh_json simulado: sirve cada lista troceada según per_page y page de la ruta.

    Imita a la API en check-runs: sin `filter=all` solo sirve el último run de cada (nombre, check suite);
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
            raise fallo(502)
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
        raise fallo(404)


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
         "started_at": started, "app": {"id": app}, "check_suite": {"id": app * 100}}
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


# --- reintento ante 5xx en gh_json: el estado sale de la línea de estado de `gh api -i` (T50) ---
def _gh_simulado(ce, monkeypatch, resultados):
    """Parchea run(): cada llamada consume un resultado (str = stdout de un 200, CalledProcessError = fallo)."""
    llamadas, esperas = [], []

    def run(cmd):
        llamadas.append(cmd)
        r = resultados[len(llamadas) - 1]
        if isinstance(r, str):
            return r
        raise r
    monkeypatch.setattr(ce, "run", run)
    monkeypatch.setattr(ce.time, "sleep", lambda s: esperas.append(s))
    return llamadas, esperas


def _falla_a_la_primera(ce, monkeypatch, error):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [error, exito('{"ok": 1}')])
    with pytest.raises(subprocess.CalledProcessError) as ei:
        ce.gh_json("x")
    assert len(llamadas) == 1 and esperas == []
    return ei.value


def test_gh_json_llama_a_gh_api_con_i(ce, monkeypatch):
    llamadas, _ = _gh_simulado(ce, monkeypatch, [exito("{}")])
    ce.gh_json("repos/o/r/pulls/7")
    assert llamadas[0][:3] == ["gh", "api", "-i"] and llamadas[0][-1] == "repos/o/r/pulls/7"


@pytest.mark.parametrize("cuerpo", ['{"x": 1}', '[{"a": 1}, {"a": 2}]', '{"total_count": 1, "check_runs": [{"id": 1}]}', "[]"])
def test_200_devuelve_el_json_sin_las_cabeceras(ce, monkeypatch, cuerpo):
    _gh_simulado(ce, monkeypatch, [exito(cuerpo)])
    assert ce.gh_json("x") == json.loads(cuerpo)


def test_200_con_cabecera_link_de_paginacion_devuelve_solo_el_cuerpo(ce, monkeypatch):
    out = ('HTTP/1.1 200 OK\nContent-Length: 17\nContent-Type: application/json\n'
           'Date: Fri, 06 Nov 2026 05:41:16 GMT\nLink: <http://127.0.0.1:18778/200/list?page=2>; rel="next"\n'
           'Server: BaseHTTP Python/3.15.0\n\n[{"a":1},{"a":2}]')
    _gh_simulado(ce, monkeypatch, [out])
    assert ce.gh_json("x") == [{"a": 1}, {"a": 2}]


def test_500_y_luego_exito_reintenta_una_vez(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [fallo(500), exito('{"ok": 1}')])
    assert ce.gh_json("x") == {"ok": 1}
    assert len(llamadas) == 2 and len(esperas) == 1 and 0 < esperas[0] <= 5


def test_dos_5xx_y_luego_exito(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [fallo(502), fallo(503), exito("[1]")])
    assert ce.gh_json("x") == [1] and len(llamadas) == 3 and len(esperas) == 2


def test_tres_5xx_son_tres_llamadas_y_propaga_el_ultimo_error(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [fallo(500), fallo(502), fallo(503), exito('{"no": 0}')])
    with pytest.raises(subprocess.CalledProcessError) as ei:
        ce.gh_json("x")
    assert len(llamadas) == 3 and len(esperas) == 2 and ce.http_status(ei.value) == 503


def test_exito_a_la_primera_no_espera(ce, monkeypatch):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [exito('{"ok": 1}')])
    assert ce.gh_json("x") == {"ok": 1} and len(llamadas) == 1 and esperas == []


@pytest.mark.parametrize("tipo", list(CUERPOS))
@pytest.mark.parametrize("codigo", ESTADOS_5XX)
def test_5xx_se_reintenta_sea_cual_sea_el_cuerpo(ce, monkeypatch, codigo, tipo):
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [fallo(codigo, tipo)] * 3 + [exito("{}")])
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("x")
    assert len(llamadas) == 3 and len(esperas) == 2


@pytest.mark.parametrize("tipo", list(CUERPOS))
@pytest.mark.parametrize("codigo", ESTADOS_NO_5XX)
def test_403_y_404_fallan_a_la_primera_sea_cual_sea_el_cuerpo(ce, monkeypatch, codigo, tipo):
    _falla_a_la_primera(ce, monkeypatch, fallo(codigo, tipo))


@pytest.mark.parametrize("tipo", list(CUERPOS))
@pytest.mark.parametrize("codigo", ESTADOS_5XX + ESTADOS_NO_5XX)
def test_http_status_lee_la_linea_de_estado_con_cualquier_cuerpo(ce, codigo, tipo):
    assert ce.http_status(fallo(codigo, tipo)) == codigo


def test_5xx_vacio_json_y_luego_exito(ce, monkeypatch):
    # antes (T48) se reconocía por el texto de stderr; ahora por el 503 de la línea de estado
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [fallo(503, "vacio_json"), fallo(502, "vacio_json"), exito("[1]")])
    assert ce.gh_json("x") == [1] and len(llamadas) == 3


def test_404_con_stderr_de_cuerpo_vacio_falla_a_la_primera(ce, monkeypatch):
    err = _falla_a_la_primera(ce, monkeypatch, fallo(404, "vacio_json"))
    assert err.stderr == "unexpected end of JSON input\n"


def test_403_que_cita_el_texto_de_cuerpo_vacio_en_su_mensaje_falla_a_la_primera(ce, monkeypatch):
    out, _ = gh_i(403)
    err = subprocess.CalledProcessError(1, "gh", output=out, stderr="gh: unexpected end of JSON input (HTTP 403)\n")
    _falla_a_la_primera(ce, monkeypatch, err)


def test_403_que_cita_http_500_en_su_mensaje_falla_a_la_primera(ce, monkeypatch):
    out, _ = gh_i(403)
    err = subprocess.CalledProcessError(1, "gh", output=out, stderr="gh: upstream said HTTP 500 earlier (HTTP 403)\n")
    _falla_a_la_primera(ce, monkeypatch, err)


def test_403_cuyo_cuerpo_cita_un_estado_5xx_falla_a_la_primera(ce, monkeypatch):
    cuerpo = '{"message":"el servidor dijo HTTP/1.1 502 Bad Gateway"}'
    out = gh_i(403)[0].split("\n\n")[0] + "\n\n" + cuerpo
    err = subprocess.CalledProcessError(1, "gh", output=out, stderr="gh: el servidor dijo HTTP/1.1 502 Bad Gateway (HTTP 403)\n")
    _falla_a_la_primera(ce, monkeypatch, err)


def test_sin_linea_de_estado_fallo_de_red_no_se_reintenta(ce, monkeypatch):
    _falla_a_la_primera(ce, monkeypatch, fallo_red())


def test_stderr_con_5xx_pero_sin_linea_de_estado_no_se_reintenta(ce, monkeypatch):
    # el estado se lee de stdout: un «gh: HTTP 503» en stderr no basta (sería el formato de T47)
    _falla_a_la_primera(ce, monkeypatch, subprocess.CalledProcessError(1, "gh", output="", stderr="gh: HTTP 503\n"))


def test_el_estado_de_stdout_manda_sobre_el_de_stderr(ce, monkeypatch):
    out, _ = gh_i(404)
    _falla_a_la_primera(ce, monkeypatch, subprocess.CalledProcessError(1, "gh", output=out, stderr="gh: HTTP 503\n"))
    out, _ = gh_i(503)
    llamadas, esperas = _gh_simulado(ce, monkeypatch, [subprocess.CalledProcessError(1, "gh", output=out, stderr="gh: Not Found (HTTP 404)\n"), exito("{}")])
    assert ce.gh_json("x") == {} and len(llamadas) == 2


def test_error_con_stdout_y_stderr_none_no_rompe_ni_se_reintenta(ce, monkeypatch):
    llamadas = []

    def run(cmd):
        llamadas.append(cmd)
        raise subprocess.CalledProcessError(1, cmd, output=None, stderr=None)
    monkeypatch.setattr(ce, "run", run)
    monkeypatch.setattr(ce.time, "sleep", lambda s: pytest.fail("no debe esperar"))
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("x")
    assert len(llamadas) == 1


def test_json_loads_que_falla_sobre_salida_correcta_no_se_reintenta(ce, monkeypatch):
    llamadas = []

    def run(cmd):
        llamadas.append(cmd)
        return exito("no es json")
    monkeypatch.setattr(ce, "run", run)
    monkeypatch.setattr(ce.time, "sleep", lambda s: pytest.fail("no debe esperar"))
    with pytest.raises(json.JSONDecodeError):
        ce.gh_json("x")
    assert len(llamadas) == 1


def test_http_status_con_la_salida_real_de_github_http2(ce):
    # `gh api -i repos/pedri77/security-manager-control/contents/nofile` real: estado «HTTP/2.0» (cabeceras recortadas)
    out = ('HTTP/2.0 404 Not Found\nAccess-Control-Allow-Origin: *\nContent-Type: application/json; charset=utf-8\n'
           'X-Ratelimit-Resource: core\nX-Xss-Protection: 0\n\n'
           '{"message":"Not Found","documentation_url":"https://docs.github.com/rest/repos/contents#get-repository-content","status":"404"}')
    e = subprocess.CalledProcessError(1, "gh", output=out, stderr="gh: Not Found (HTTP 404)\n")
    assert ce.http_status(e) == 404


@pytest.mark.parametrize("out,esperado", [
    ("HTTP/2.0 502 Bad Gateway\nServer: x\n\n", 502),
    ("HTTP/1.1 503 Service Unavailable\nServer: x", 503),   # sin separador (run() lo dejó sin él)
    ("HTTP/2 500\nServer: x\n\n", 500),
    ("", None),
    (None, None),
    ("<html>HTTP/1.1 500 x</html>", None),                  # el estado es la primera línea, no una cita
    ("gh: HTTP 500", None),
])
def test_http_status_solo_lee_la_primera_linea_de_stdout(ce, out, esperado):
    assert ce.http_status(subprocess.CalledProcessError(1, "gh", output=out, stderr="")) == esperado


def test_5xx_en_collect_pr_deja_hueco_tras_tres_llamadas(ce, monkeypatch):
    esperas, llamadas = [], []
    monkeypatch.setattr(ce.time, "sleep", lambda s: esperas.append(s))
    fake = FakeGh({})

    def run(cmd):
        path = cmd[-1]
        if "/check-runs" in path:
            llamadas.append(path)
            raise fallo(502, "html")
        return exito(json.dumps(fake(path)))
    monkeypatch.setattr(ce, "run", run)
    p = ce.collect_pr("o/r", 7)
    assert any("no se pudieron leer los checks" in g and "HTTP 502" in g for g in p["gaps"])
    assert len(llamadas) == 3 and len(esperas) == 2


def test_vacio_json_5xx_en_collect_pr_deja_hueco_tras_tres_llamadas(ce, monkeypatch):
    esperas, llamadas = [], []
    monkeypatch.setattr(ce.time, "sleep", lambda s: esperas.append(s))
    fake = FakeGh({})

    def run(cmd):
        path = cmd[-1]
        if "/check-runs" in path:
            llamadas.append(path)
            raise fallo(500, "vacio_json")
        return exito(json.dumps(fake(path)))
    monkeypatch.setattr(ce, "run", run)
    p = ce.collect_pr("o/r", 7)
    assert any("no se pudieron leer los checks" in g and "unexpected end of JSON input" in g for g in p["gaps"])
    assert len(llamadas) == 3 and len(esperas) == 2


# --- con un ejecutable `gh` que imprime los bytes medidos (separador «\r\n\r\n») ---
def _bytes_de_gh(codigo, tipo):
    """Los bytes que `gh` escribe: estado + «\n», cabeceras con «\r\n», «\r\n» y cuerpo."""
    out, err = gh_i(codigo, tipo)
    estado, resto = out.split("\n", 1)
    return (estado + "\n" + resto.replace("\n", "\r\n")).encode(), err


@pytest.fixture
def gh_falso(tmp_path, monkeypatch):
    """Pone un `gh` en el PATH que sirve la respuesta fijada y cuenta las llamadas."""
    import os
    import sys
    d = tmp_path / "bin"
    d.mkdir()
    exe = d / "gh"
    exe.write_text(
        f"#!{sys.executable}\nimport os, sys\nd = os.path.dirname(os.path.abspath(__file__))\n"
        "open(d + '/args', 'a').write(' '.join(sys.argv[1:]) + '\\n')\n"
        "sys.stdout.buffer.write(open(d + '/out', 'rb').read())\n"
        "sys.stderr.write(open(d + '/err').read())\nsys.exit(int(open(d + '/rc').read()))\n")
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{d}{os.pathsep}{os.environ['PATH']}")
    esperas = []
    monkeypatch.setattr("time.sleep", lambda s: esperas.append(s))

    class G:
        def pon(self, salida: bytes, stderr: str = "", rc: int = 0):
            (d / "out").write_bytes(salida)
            (d / "err").write_text(stderr)
            (d / "rc").write_text(str(rc))

        def llamadas(self):
            f = d / "args"
            return f.read_text().splitlines() if f.exists() else []
    g = G()
    g.esperas = esperas
    return g


@pytest.mark.parametrize("tipo", list(CUERPOS))
@pytest.mark.parametrize("codigo", ESTADOS_5XX + ESTADOS_NO_5XX)
def test_matriz_con_gh_falso_5xx_tres_peticiones_403_y_404_una(ce, gh_falso, codigo, tipo):
    salida, err = _bytes_de_gh(codigo, tipo)
    gh_falso.pon(salida, err, rc=1)
    with pytest.raises(subprocess.CalledProcessError) as ei:
        ce.gh_json("repos/o/r/x")
    assert ce.http_status(ei.value) == codigo
    assert len(gh_falso.llamadas()) == (3 if codigo in ESTADOS_5XX else 1)
    assert len(gh_falso.esperas) == (2 if codigo in ESTADOS_5XX else 0)


@pytest.mark.parametrize("cuerpo", ['{"x":1}', '[{"a":1},{"a":2}]', '{"total_count":1,"check_runs":[{"id":1}]}'])
def test_200_con_gh_falso_devuelve_el_json(ce, gh_falso, cuerpo):
    salida = (f"HTTP/1.1 200 OK\nContent-Length: {len(cuerpo)}\r\nContent-Type: application/json\r\n"
              f"Date: Fri, 06 Nov 2026 05:41:16 GMT\r\nLink: <http://127.0.0.1:18778/200/list?page=2>; rel=\"next\"\r\n"
              f"Server: BaseHTTP Python/3.15.0\r\n\r\n{cuerpo}").encode()
    gh_falso.pon(salida)
    assert ce.gh_json("repos/o/r/x") == json.loads(cuerpo)
    assert gh_falso.llamadas() == ["api -i -H Accept: application/vnd.github+json repos/o/r/x"]


def test_fallo_de_red_con_gh_falso_una_peticion(ce, gh_falso):
    gh_falso.pon(b"", fallo_red().stderr, rc=1)
    with pytest.raises(subprocess.CalledProcessError):
        ce.gh_json("repos/o/r/x")
    assert len(gh_falso.llamadas()) == 1


# --- el 404 de allowed_release_files sale del estado, no del texto (T50) ---
@pytest.mark.parametrize("tipo", list(CUERPOS))
def test_config_ausente_404_con_cualquier_cuerpo_deja_los_ficheros_fijos(ce, monkeypatch, tipo):
    _falla_api(ce, monkeypatch, fallo(404, tipo))
    assert ce.allowed_release_files("o/r", "main") == ce.RELEASE_FILES


def test_403_cuyo_mensaje_cita_http_404_no_es_config_ausente(ce, monkeypatch):
    out, _ = gh_i(403)
    err = subprocess.CalledProcessError(1, "gh", output=out, stderr="gh: ver HTTP 404 en la documentacion (HTTP 403)\n")
    _falla_api(ce, monkeypatch, err)
    with pytest.raises(subprocess.CalledProcessError):
        ce.allowed_release_files("o/r", "main")


def test_stderr_con_http_404_pero_estado_de_stdout_500_no_es_config_ausente(ce, monkeypatch):
    out, _ = gh_i(500)
    _falla_api(ce, monkeypatch, subprocess.CalledProcessError(1, "gh", output=out, stderr="gh: Not Found (HTTP 404)\n"))
    with pytest.raises(subprocess.CalledProcessError):
        ce.allowed_release_files("o/r", "main")


def test_stderr_con_http_404_sin_linea_de_estado_no_es_config_ausente(ce, monkeypatch):
    _falla_api(ce, monkeypatch, subprocess.CalledProcessError(1, "gh", output="", stderr="gh: Not Found (HTTP 404)\n"))
    with pytest.raises(subprocess.CalledProcessError):
        ce.allowed_release_files("o/r", "main")

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


# --- T50: simulador de check-runs por check suite ---
def test_simulador_sin_filter_all_sirve_el_ultimo_run_por_check_suite(ce):
    # mismo nombre y misma suite: solo el último; mismo nombre y otra suite: se quedan los dos
    runs = [_run(1, "ci", "failure", T41, app=1), _run(2, "ci", "success", T45, app=1),
            _run(3, "ci", "success", T41, app=2)]
    gh = FakeGh({"/commits/H/check-runs": runs})
    sin = gh("repos/o/r/commits/H/check-runs?per_page=100&page=1")["check_runs"]
    con = gh("repos/o/r/commits/H/check-runs?filter=all&per_page=100&page=1")["check_runs"]
    assert [r["id"] for r in sin] == [2, 3] and [r["id"] for r in con] == [1, 2, 3]


def test_simulador_dos_suites_de_la_misma_app_con_el_mismo_nombre_se_quedan_las_dos(ce):
    a, b = _run(1, "build", "success", T41), _run(2, "build", "failure", T43)
    a["check_suite"], b["check_suite"] = {"id": 7}, {"id": 8}   # medido en cli/cli: 19 suites, mismo nombre y app
    gh = FakeGh({"/commits/H/check-runs": [a, b]})
    sin = gh("repos/o/r/commits/H/check-runs?per_page=100&page=1")["check_runs"]
    assert [r["id"] for r in sin] == [1, 2]


# --- T50: corte en merged_at con completed_at cuando falta started_at ---
def _sin_inicio(i, name, concl, completed, **kw):
    return _run(i, name, concl, None, completed_at=completed, **kw)


@pytest.mark.parametrize("orden", ORDENES)
def test_run_sin_started_at_completado_tras_el_merge_no_sustituye_al_que_habia(ce, monkeypatch, orden):
    # el caso de la issue: failure id 1 a las 20:41 y success id 2 sin started_at, que acabó tras el merge
    runs = _ordena([_run(1, "ci", "failure", T41), _sin_inicio(2, "ci", "success", T45)], orden)
    p = _collect_merged(ce, monkeypatch, runs)
    assert _conclusiones(p) == [("ci", "failure")] and p["gaps"] == []


@pytest.mark.parametrize("orden", ORDENES)
def test_run_sin_started_at_completado_antes_del_merge_se_queda(ce, monkeypatch, orden):
    runs = _ordena([_run(1, "ci", "failure", T41), _sin_inicio(2, "ci", "success", T43)], orden)
    assert _conclusiones(_collect_merged(ce, monkeypatch, runs)) == [("ci", "success")]


def test_run_sin_started_at_completado_justo_en_merged_at_se_queda(ce, monkeypatch):
    runs = [_run(1, "ci", "failure", T41), _sin_inicio(2, "ci", "success", MERGE)]
    assert _conclusiones(_collect_merged(ce, monkeypatch, runs)) == [("ci", "success")]


def test_run_sin_ninguna_fecha_se_queda(ce, monkeypatch):
    runs = [_run(1, "ci", "success", T41), _run(2, "ci", "failure", None, completed_at=None)]
    p = _collect_merged(ce, monkeypatch, runs)
    assert _conclusiones(p) == [("ci", "failure")] and p["gaps"] == []


def test_started_at_manda_sobre_completed_at(ce, monkeypatch):
    # empezó antes del merge y acabó después: se queda; si se mirara completed_at se descartaría
    runs = [_run(1, "ci", "failure", T41), _run(2, "ci", "success", T43, completed_at=T45)]
    assert _conclusiones(_collect_merged(ce, monkeypatch, runs)) == [("ci", "success")]


def test_started_at_posterior_manda_sobre_completed_at_anterior(ce, monkeypatch):
    runs = [_run(1, "ci", "failure", T41), _run(2, "ci", "success", T45, completed_at=T41)]
    assert _conclusiones(_collect_merged(ce, monkeypatch, runs)) == [("ci", "failure")]


def test_check_cuyo_unico_run_sin_started_at_acabo_tras_el_merge_sale_y_deja_hueco(ce, monkeypatch):
    runs = [_run(1, "ci", "success", T41), _sin_inicio(2, "tardio", "success", T45)]
    p = _collect_merged(ce, monkeypatch, runs)
    assert _conclusiones(p) == [("ci", "success")]
    assert len(p["gaps"]) == 1 and "PR #7" in p["gaps"][0] and "tardio" in p["gaps"][0]


def test_completed_at_en_otro_huso_cuenta_el_instante(ce, monkeypatch):
    # 20:50+01:00 = 19:50Z, anterior al merge de 20:44Z: se queda
    runs = [_run(1, "ci", "failure", T41), _sin_inicio(2, "ci", "success", "2026-11-04T20:50:00+01:00")]
    assert _conclusiones(_collect_merged(ce, monkeypatch, runs)) == [("ci", "success")]


def test_completed_at_sin_fusionar_no_corta(ce, monkeypatch):
    runs = [_run(1, "ci", "failure", T41), _sin_inicio(2, "ci", "success", T45)]
    assert _conclusiones(_collect_merged(ce, monkeypatch, runs, merged_at=None)) == [("ci", "success")]


# --- T50: fecha ilegible en el corte = hueco, y ese run no se corta ---
@pytest.mark.parametrize("malo", ["ayer", "2026-13-45T99:00:00Z"])
def test_started_at_ilegible_deja_hueco_con_pr_y_check_y_el_run_se_queda(ce, monkeypatch, malo):
    runs = [_run(1, "ci", "failure", T41), _run(2, "ci", "success", malo)]
    p = _collect_merged(ce, monkeypatch, runs)
    assert _conclusiones(p) == [("ci", "success")]
    assert len(p["gaps"]) == 1 and "PR #7" in p["gaps"][0] and "ci" in p["gaps"][0] and "ilegible" in p["gaps"][0]


def test_completed_at_ilegible_sin_started_at_deja_hueco_y_el_run_se_queda(ce, monkeypatch):
    runs = [_run(1, "ci", "failure", T41), _sin_inicio(2, "ci", "success", "mañana")]
    p = _collect_merged(ce, monkeypatch, runs)
    assert _conclusiones(p) == [("ci", "success")]
    assert len(p["gaps"]) == 1 and "PR #7" in p["gaps"][0] and "ci" in p["gaps"][0]


def test_started_at_ilegible_no_cae_a_completed_at(ce, monkeypatch):
    # completed_at (tras el merge) lo cortaría; la fecha de inicio ilegible deja hueco y el run se queda
    runs = [_run(1, "ci", "failure", T41), _run(2, "ci", "success", "ayer", completed_at=T45)]
    p = _collect_merged(ce, monkeypatch, runs)
    assert _conclusiones(p) == [("ci", "success")] and len(p["gaps"]) == 1


def test_merged_at_ilegible_deja_un_hueco_y_no_corta(ce, monkeypatch):
    runs = [_run(1, "ci", "failure", T41), _run(2, "ci", "success", T45), _run(3, "tardio", "success", T45)]
    p = _collect_merged(ce, monkeypatch, runs, merged_at="no-es-fecha")
    assert _conclusiones(p) == [("ci", "success"), ("tardio", "success")]
    assert len(p["gaps"]) == 1 and "PR #7" in p["gaps"][0] and "merged_at" in p["gaps"][0]


def test_merged_at_ilegible_deja_hueco_aunque_no_haya_checks(ce, monkeypatch):
    p = _collect_merged(ce, monkeypatch, [], merged_at="no-es-fecha")
    assert len(p["gaps"]) == 1 and "merged_at" in p["gaps"][0]


def test_fechas_ilegibles_sin_merged_at_no_dejan_hueco(ce, monkeypatch):
    runs = [_run(1, "ci", "success", "ayer")]
    assert _collect_merged(ce, monkeypatch, runs, merged_at=None)["gaps"] == []


def test_fechas_legibles_no_dejan_hueco(ce, monkeypatch):
    runs = [_run(1, "ci", "success", T41), _sin_inicio(2, "otro", "success", T43)]
    assert _collect_merged(ce, monkeypatch, runs)["gaps"] == []


def test_dos_runs_con_fecha_ilegible_dejan_un_hueco_por_check(ce, monkeypatch):
    runs = [_run(1, "ci", "success", "ayer"), _run(2, "otro", "success", "hoy")]
    p = _collect_merged(ce, monkeypatch, runs)
    assert len(p["gaps"]) == 2 and any("ci" in g for g in p["gaps"]) and any("otro" in g for g in p["gaps"])


@pytest.mark.parametrize("malo", [12345, ["x"], {"a": 1}])
def test_cut_at_merge_con_fecha_que_no_es_texto_deja_hueco_y_se_queda(ce, malo):
    # la rama AttributeError de _utc; la API siempre da texto, pero el corte no debe romperse ni perder el run
    problemas = []
    kept = ce.cut_at_merge([_run(1, "ci", "success", malo)], MERGE, problemas)
    assert [r["id"] for r in kept] == [1] and len(problemas) == 1 and "ci" in problemas[0]
    problemas = []
    kept = ce.cut_at_merge([_run(1, "ci", "success", T41)], malo, problemas)
    assert [r["id"] for r in kept] == [1] and len(problemas) == 1 and "merged_at" in problemas[0]


def test_cut_at_merge_directo_anota_el_problema_en_la_lista(ce):
    problemas = []
    kept = ce.cut_at_merge([_run(1, "ci", "success", "ayer")], MERGE, problemas)
    assert [r["id"] for r in kept] == [1] and len(problemas) == 1 and "ci" in problemas[0]


def test_hueco_de_fecha_ilegible_aparece_en_el_pack_de_release(ce, monkeypatch, tmp_path):
    rec, _ = _release_con_runs(ce, monkeypatch, tmp_path, [_run(1, "ci", "success", T41)])
    assert not any("ilegible" in g for g in rec["gaps"])
    gh = FakeGh({"/commits/H/check-runs": [_run(1, "ci", "success", "ayer")]})
    gh.pr["merged_at"] = MERGE
    import argparse
    monkeypatch.setattr(ce, "gh_json", gh)
    ce.mode_release(argparse.Namespace(tag="v1", out=str(tmp_path / "b"), offline=False))
    rec = json.loads((tmp_path / "b" / "change-record.json").read_text(encoding="utf-8"))
    assert any("PR #7" in g and "ilegible" in g for g in rec["gaps"])


# --- T50: blind-review se corta en merged_at ---
CTX = "blind-review"
ANTES, A_LAS, DESPUES = "2026-11-04T20:40:00Z", MERGE, "2026-11-04T20:50:00Z"


def _estado(i, state, creado, ctx=CTX, **kw):
    return {"id": i, "context": ctx, "state": state, "created_at": creado, "description": "d", "target_url": "t", **kw}


def _collect_estados(ce, monkeypatch, estados, merged_at=MERGE):
    gh = FakeGh({"/commits/H/statuses": estados})
    if merged_at:
        gh.pr["merged_at"] = merged_at
    monkeypatch.setattr(ce, "gh_json", gh)
    monkeypatch.setattr(ce, "PER_PAGE", 100)
    return ce.collect_pr("o/r", 7)


@pytest.mark.parametrize("orden", ORDENES)
def test_blind_review_publicado_tras_el_merge_no_sustituye_al_previo(ce, monkeypatch, orden):
    estados = _ordena([_estado(1, "success", ANTES), _estado(2, "failure", DESPUES)], orden)
    p = _collect_estados(ce, monkeypatch, estados)
    assert p["blind_review"]["state"] == "success" and p["gaps"] == []


@pytest.mark.parametrize("orden", ORDENES)
def test_blind_review_solo_posterior_al_merge_no_cuenta(ce, monkeypatch, orden):
    estados = _ordena([_estado(1, "success", DESPUES), _estado(2, "success", "2026-11-04T21:00:00Z")], orden)
    assert _collect_estados(ce, monkeypatch, estados)["blind_review"] is None


def test_blind_review_publicado_justo_en_merged_at_cuenta(ce, monkeypatch):
    p = _collect_estados(ce, monkeypatch, [_estado(1, "success", A_LAS)])
    assert p["blind_review"]["state"] == "success"


def test_blind_review_un_segundo_despues_no_cuenta(ce, monkeypatch):
    assert _collect_estados(ce, monkeypatch, [_estado(1, "success", "2026-11-04T20:44:01Z")])["blind_review"] is None


def test_blind_review_sin_fusionar_el_posterior_gana(ce, monkeypatch):
    estados = [_estado(1, "success", ANTES), _estado(2, "failure", DESPUES)]
    p = _collect_estados(ce, monkeypatch, estados, merged_at=None)
    assert p["blind_review"]["state"] == "failure"


def test_blind_review_otro_huso_cuenta_el_instante(ce, monkeypatch):
    # 20:50+01:00 = 19:50Z, anterior al merge (20:44Z): cuenta; como texto «20:50» > «20:44» no contaría
    p = _collect_estados(ce, monkeypatch, [_estado(1, "success", "2026-11-04T20:50:00+01:00")])
    assert p["blind_review"]["state"] == "success"


def test_estado_de_otro_contexto_no_se_corta_ni_cambia(ce, monkeypatch):
    estados = [_estado(1, "success", ANTES), _estado(2, "failure", DESPUES, ctx="ci")]
    p = _collect_estados(ce, monkeypatch, estados)
    assert p["blind_review"]["state"] == "success"


def test_blind_review_con_created_at_ilegible_cuenta_y_deja_hueco(ce, monkeypatch):
    p = _collect_estados(ce, monkeypatch, [_estado(1, "success", "ayer")])
    assert p["blind_review"]["state"] == "success"
    assert len(p["gaps"]) == 1 and "PR #7" in p["gaps"][0] and "blind-review" in p["gaps"][0]


def test_merged_at_ilegible_no_corta_blind_review_y_no_duplica_el_hueco(ce, monkeypatch):
    p = _collect_estados(ce, monkeypatch, [_estado(1, "success", ANTES), _estado(2, "failure", DESPUES)],
                         merged_at="no-es-fecha")
    assert p["blind_review"]["state"] == "failure"
    assert len(p["gaps"]) == 1 and "merged_at" in p["gaps"][0]


def test_release_con_blind_review_solo_posterior_al_merge_sale_en_el_hueco_de_hoy(ce, monkeypatch, tmp_path):
    import argparse
    gh = FakeGh({"/commits/H/statuses": [_estado(1, "success", DESPUES)]})
    gh.pr["merged_at"] = MERGE
    monkeypatch.setattr(ce, "PER_PAGE", 100)
    monkeypatch.setattr(ce, "previous_tag", lambda tag: "v0")
    monkeypatch.setattr(ce, "repo_slug", lambda: "o/r")
    monkeypatch.setattr(ce, "git_range_commits", lambda rng: [
        {"sha": "a" * 40, "subject": "feat: algo (#7)", "author": "x", "tasks": []}])
    monkeypatch.setattr(ce, "gh_json", gh)
    ce.mode_release(argparse.Namespace(tag="v1", out=str(tmp_path), offline=False))
    rec = json.loads((tmp_path / "change-record.json").read_text(encoding="utf-8"))
    assert any("PR #7 sin revisión ciega correcta (estado: —)" in g for g in rec["gaps"])
