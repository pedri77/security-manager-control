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
        if u.path.endswith(("/commits", "/reviews", "/statuses", "/files")):
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


# ═════════════ T51 (SMC-009): puerta de seguridad ═════════════
# Formatos medidos con `gh` 2.89.0 contra GitHub real el 2026-11-07 (solo GET):
# - `pulls/N/files`: lista de objetos {sha, filename, status, additions, deletions, changes, blob_url, raw_url,
#   contents_url, patch}; `status` es modified/added; `previous_filename` solo está documentado (renamed), sin medir.
# - `contents/<ruta>?ref=<sha|rama>`: objeto {name, path, sha, size, url, html_url, git_url, download_url, type: "file",
#   content (base64 con «\n» cada 60 caracteres), encoding: "base64", _links}. Sobre una carpeta devuelve una LISTA.
# - Fichero inexistente: HTTP/2.0 404 con cuerpo {"message":"Not Found","documentation_url":...,"status":"404"} y
#   stderr «gh: Not Found (HTTP 404)».
# - `commits/<sha>/statuses`: lista de {url, avatar_url, id, node_id, state, description, target_url, context,
#   created_at, updated_at, creator}.
import base64 as _b64
import re as _re

GITHUB_404 = ('{"message":"Not Found","documentation_url":"https://docs.github.com/rest/repos/contents#'
              'get-repository-content","status":"404"}')
LISTA_PATH = ".github/security-paths.txt"
MODELO_OK = """# Threat model — SMC-777 · algo

**Versión:** v1 · **Fecha:** 2026-11-07 · **Autor:** engineering · **Revisor:** independent-reviewer
**Issue:** #1 · **ADR relacionado:** n/a

## 3. Amenazas (STRIDE)
| ID | Categoría | Amenaza | Componente | Prob. (1-3) | Impacto (1-3) | Riesgo | Mitigación | Test que la verifica | Estado |
|---|---|---|---|---|---|---|---|---|---|
| T1 | Tampering | x | y | 1 | 2 | 2 | z | `tests/test_x.py::test_x` | mitigada |
| T2 | Spoofing | x | y | 1 | 2 | 2 | z | `tests/test_x.py::test_y` | mitigada |
"""


def fallo_404_github():
    out = ("HTTP/2.0 404 Not Found\nContent-Length: %d\nContent-Type: application/json; charset=utf-8\n%s\n%s"
           % (len(GITHUB_404), FECHA_Y_SERVIDOR, GITHUB_404))
    return subprocess.CalledProcessError(1, "gh", output=out, stderr="gh: Not Found (HTTP 404)\n")


def contenido(texto, ruta="x"):
    """Respuesta de `contents/<ruta>` para un fichero, con el base64 partido cada 60 caracteres como GitHub."""
    b64 = _b64.b64encode(texto.encode("utf-8")).decode()
    trozos = "\n".join(b64[i:i + 60] for i in range(0, len(b64), 60)) + "\n"
    return {"name": ruta.rsplit("/", 1)[-1], "path": ruta, "sha": "e3789f7cd60fc619e0b9491bd26550f116e9788f",
            "size": len(texto.encode("utf-8")), "type": "file", "content": trozos, "encoding": "base64"}


class FakeSec:
    """gh_json simulado de un PR con ficheros, commits, contenidos por (ref, ruta) y estados."""

    def __init__(self, files=("README.md",), title="feat: algo", body="Closes #1\nTask: SMC-777", commits=("x\n\nTask: SMC-777",),
                 contents=None, statuses=(), head_ref="feat", same_repo=True, merged_at=None, fail=None, nfiles=None):
        self.files = [f if isinstance(f, dict) else {"filename": f, "status": "modified"} for f in files]
        if nfiles:
            self.files = [{"filename": f"f{i}.txt", "status": "modified"} for i in range(nfiles)]
        self.contents = contents or {}
        self.statuses = list(statuses)
        self.commits = list(commits)
        self.fail = fail or {}
        self.paths: list[str] = []
        self.pr = {"head": {"sha": "H", "ref": head_ref, "repo": {"full_name": "o/r" if same_repo else "fork/r"}},
                   "base": {"ref": "main", "sha": "B"}, "user": {"login": "x"}, "title": title, "html_url": "u",
                   "body": body, "commits": len(self.commits), "merged_at": merged_at}

    def __call__(self, path):
        from urllib.parse import parse_qs, unquote, urlparse
        self.paths.append(path)
        u = urlparse(path)
        q = parse_qs(u.query)
        per, page = int(q.get("per_page", ["30"])[0]), int(q.get("page", ["1"])[0])
        for suf, err in self.fail.items():
            if u.path.endswith(suf) or suf in path:
                raise err
        p = unquote(u.path)
        if "/contents/" in p:
            ruta = p.split("/contents/", 1)[1]
            ref = q.get("ref", [None])[0]
            if (ref, ruta) in self.contents:
                v = self.contents[(ref, ruta)]
                return v if not isinstance(v, str) else contenido(v, ruta)
            raise fallo_404_github()
        if p.endswith("/pulls/7"):
            return self.pr
        if p.endswith("/pulls/7/files"):
            return self.files[(page - 1) * per: page * per]
        if p.endswith("/pulls/7/commits"):
            return [{"sha": f"sha{i}", "commit": {"message": m}} for i, m in enumerate(self.commits)][(page - 1) * per: page * per]
        if p.endswith("/statuses"):
            return self.statuses[(page - 1) * per: page * per]
        if p.endswith("/check-runs"):
            return {"total_count": 0, "check_runs": []}
        if p.endswith("/reviews"):
            return []
        raise fallo_404_github()

    def leyo(self, fragmento):
        return [x for x in self.paths if fragmento in x]


def _sec(ce, monkeypatch, lista="scripts/*\n.github/workflows/*\n", **kw):
    contents = dict(kw.pop("contents", {}))
    if lista is not None:
        contents[("main", LISTA_PATH)] = lista
    gh = FakeSec(contents=contents, **kw)
    monkeypatch.setattr(ce, "gh_json", gh)
    monkeypatch.setattr(ce, "PER_PAGE", 100)
    return gh


def _gate(ce, monkeypatch, **kw):
    gh = _sec(ce, monkeypatch, **kw)
    return gh, ce.evaluate_security("o/r", 7)


def _modo_security(ce, monkeypatch, capsys, head_sha="H", **kw):
    import argparse
    gh = _sec(ce, monkeypatch, **kw)
    monkeypatch.setattr(ce, "repo_slug", lambda: "o/r")
    rc = ce.mode_security(argparse.Namespace(pr=7, head_sha=head_sha))
    cap = capsys.readouterr()
    return rc, cap.out, cap.err, gh


MODELO_PATH = "docs/threat-model/SMC-777.md"


def _modelo(texto=MODELO_OK, tarea="SMC-777", ref="H"):
    return {(ref, f"docs/threat-model/{tarea}.md"): texto}


# Las pruebas van en tablas parametrizadas: el README fija el número de `def test_` del repositorio (insignia de
# tests) y esta tarea no toca el README. Cada caso conserva su id y se puede lanzar con `-k`.
RELEASE = "release-please--branches--main--components--x"
FICHEROS_RELEASE = ["CHANGELOG.md", ".release-please-manifest.json", "pyproject.toml"]
RAIZ = Path(__file__).resolve().parent.parent
TASK = "Closes #1\nTask: SMC-777"
P = pytest.param

CASOS_PUERTA = [
    # (id, kwargs de FakeSec, aplica, fragmento del motivo, avisos esperados)
    P(dict(files=["README.md", "docs/a.md"]), False, "no toca", [], id="pr_normal_no_aplica"),
    P(dict(title="sec(x): algo", files=["README.md"]), True, "sec", [], id="tipo_sec_aplica_sin_rutas"),
    P(dict(title="SEC: algo", files=["README.md"]), True, "sec", [], id="tipo_sec_en_mayusculas"),
    P(dict(title="feat: sec", files=["README.md"]), False, "", [], id="sec_en_el_texto_no_es_el_tipo"),
    P(dict(title="security: x", files=["README.md"]), False, "", [], id="security_no_es_sec"),
    P(dict(files=["README.md", "scripts/change_evidence.py"]), True, "scripts/change_evidence.py", [], id="ruta_sensible_aplica_y_se_nombra"),
    P(dict(files=[".github/workflows/sub/x.yml"]), True, "sub/x.yml", [], id="el_glob_alcanza_subcarpetas"),
    P(dict(files=[{"filename": "docs/otro.py", "previous_filename": "scripts/viejo.py", "status": "renamed"}]), True,
      "scripts/viejo.py", [], id="renombrado_desde_ruta_sensible_aplica"),
    P(dict(files=["scripts/x.py"], contents={("H", LISTA_PATH): "# vacia\n"}), True, "scripts/x.py", [],
      id="lista_de_la_cabeza_vaciada_no_libra"),
    P(dict(files=["docs/a.md"], lista="scripts/*\n", contents={("H", LISTA_PATH): "docs/*\n"}), False, "", [],
      id="lista_ampliada_en_la_cabeza_no_cuenta"),
    P(dict(files=[LISTA_PATH], lista="scripts/*\n"), True, "lista", [], id="tocar_la_lista_activa_la_puerta"),
    P(dict(files=[{"filename": LISTA_PATH, "status": "removed"}], lista="scripts/*\n"), True, "lista", [],
      id="borrar_la_lista_activa_la_puerta"),
    # N1: sin lista en la base la puerta aplica y falla en cerrado; tocar la lista activa la puerta también sin ella
    P(dict(files=["scripts/x.py", LISTA_PATH], lista=None), True, "falta la lista", [LISTA_PATH], id="sin_lista_en_la_base_aplica_y_falla_en_cerrado"),
    P(dict(files=["README.md"], lista=None), True, "falta la lista", [LISTA_PATH], id="sin_lista_en_la_base_aplica_aunque_no_se_toque"),
    P(dict(files=[LISTA_PATH], lista=None), True, "toca la lista de rutas", [LISTA_PATH], id="tocar_la_lista_con_la_lista_ausente_en_la_base"),
    P(dict(files=["README.md"], lista=None, title="sec: x"), True, "sec", [LISTA_PATH], id="sin_lista_en_la_base_y_tipo_sec"),
    P(dict(files=FICHEROS_RELEASE, head_ref=RELEASE, lista="*\n", title="chore(main): release 1.0.0"), False, "release", [],
      id="el_pr_de_release_no_se_ve_afectado"),
    P(dict(files=FICHEROS_RELEASE, head_ref=RELEASE, lista="*\n", title="sec: release"), False, "release", [],
      id="el_pr_de_release_de_tipo_sec_tampoco"),
    P(dict(files=FICHEROS_RELEASE + ["scripts/x.py"], head_ref=RELEASE), True, "scripts/x.py", [], id="rama_de_release_con_otro_fichero_aplica"),
    # B1: la exención mira también de dónde viene cada fichero
    P(dict(files=[{"filename": "version.txt", "previous_filename": "scripts/change_evidence.py", "status": "renamed"}], head_ref=RELEASE,
           lista="scripts/*\n"), True, "scripts/change_evidence.py", [], id="release_renombrado_desde_ruta_sensible_aplica"),
    P(dict(files=[{"filename": "version.txt", "previous_filename": "scripts/change_evidence.py", "status": "copied"}], head_ref=RELEASE,
           lista="scripts/*\n"), True, "scripts/change_evidence.py", [], id="release_copiado_desde_ruta_sensible_aplica"),
    P(dict(files=[{"filename": "version.txt", "previous_filename": "CHANGELOG.md", "status": "renamed"}], head_ref=RELEASE, lista="*\n"),
       False, "release", [], id="release_renombrado_entre_ficheros_de_version_no_aplica"),
    P(dict(files=FICHEROS_RELEASE, head_ref=RELEASE, lista="*\n", same_repo=False), True, "", [], id="rama_de_release_desde_un_fork_aplica"),
    P(dict(files=[f"docs/a{i}.md" for i in range(150)] + ["scripts/x.py"]), True, "scripts/x.py", [], id="lee_todas_las_paginas_de_ficheros"),
]


@pytest.mark.parametrize("kw,aplica,razon,avisos", CASOS_PUERTA)
def test_puerta_decide_si_aplica(ce, monkeypatch, kw, aplica, razon, avisos):
    gh, r = _gate(ce, monkeypatch, **kw)
    assert r["required"] is aplica and razon in r["reason"]
    assert [w for w in r["warnings"] if not any(a in w for a in avisos)] == [] and bool(avisos) == bool(r["warnings"])
    assert all("ref=main" in x for x in gh.leyo(LISTA_PATH))  # la lista sale siempre de la rama base
    if not aplica:
        assert gh.leyo("threat-model") == [] and r["threat_model"] is None


SUCIO = MODELO_OK.replace("mitigada", "abierta")
CASOS_MODELO = [
    # (id, kwargs, ¿hay problemas?, fragmentos en los problemas, threat_model del resultado)
    P(dict(contents=_modelo()), False, [], "docs/threat-model/SMC-777.md", id="threat_model_en_la_cabeza_pasa"),
    P(dict(contents=_modelo(ref="main")), True, ["SMC-777"], None, id="threat_model_solo_en_la_base_no_vale"),
    P(dict(), True, ["docs/threat-model/SMC-777.md"], None, id="sin_threat_model_ni_linea_falla"),
    P(dict(files=["smc/visor.py", MODELO_PATH], lista="~smc/*\nscripts/*\n", body=TASK + "\nThreat model: no aplica: solo renombra una variable"), False, [],
      "no aplica: solo renombra una variable", id="linea_no_aplica_con_motivo_pasa"),
    P(dict(files=["smc/visor.py", MODELO_PATH], lista="~smc/*\nscripts/*\n", body=TASK + "\nThreat model: No Aplica: motivo suficiente"), False, [], "no aplica: motivo suficiente", id="linea_no_aplica_sin_distinguir_mayusculas"),
    P(dict(files=["smc/visor.py", MODELO_PATH], lista="~smc/*\nscripts/*\n", body=TASK + "\n<!-- nota -->\nThreat model: no aplica: motivo real y suficiente"), False, [], "no aplica: motivo real y suficiente",
      id="linea_tras_un_comentario_cerrado_pasa"),
    *[P(dict(body=TASK + f"\n{linea}\n"), True, [], None, id=f"linea_sin_motivo_{i}") for i, linea in enumerate(
        ["Threat model: no aplica:", "Threat model: no aplica:    ", "Threat model: no aplica:\t", "Threat model: no aplica",
         "Threat model: n/a: x", "- [ ] Threat model: no aplica: x"])],
    *[P(dict(body=f"Task: SMC-777\n{c}"), True, [], None, id=f"linea_en_comentario_html_{i}") for i, c in enumerate([
        "<!-- Threat model: no aplica: x -->", "<!--\nThreat model: no aplica: x\n-->", "<!-- Threat model: no aplica: x",
        "<!-- a --><!-- Threat model: no aplica: x -->"])],
    P(dict(body=(RAIZ / ".github/pull_request_template.md").read_text(encoding="utf-8") + "\nTask: SMC-777\n"), True, [], None,
      id="plantilla_del_pr_sin_rellenar_no_pasa"),
    P(dict(contents=_modelo(SUCIO), body="Closes #1\nTask: SMC-777\nThreat model: no aplica: lo digo yo, lo digo yo"), True, ["abierta"], "docs/threat-model/SMC-777.md",
      id="si_existe_el_threat_model_se_juzga_aunque_haya_linea"),
    P(dict(commits=["a\n\nTask: SMC-777", "b\n\nTask: SMC-778"], contents=_modelo()), True, ["SMC-778"], "docs/threat-model/SMC-777.md",
      id="varias_tareas_cada_una_necesita_el_suyo"),
    P(dict(body="Closes #1", commits=["sin pie"]), True, ["TASK_ID"], None, id="sin_task_id_ni_linea_falla"),
    # el modelo debe estar añadido o modificado en pulls/N/files: uno ya existente sin tocar, o de otra tarea, no vale
    P(dict(files=["scripts/x.py"], contents=_modelo()), True, ["SMC-777", "no lo añade ni lo modifica"], None,
      id="modelo_existente_en_la_cabeza_sin_tocar_no_vale"),
    P(dict(files=["smc/visor.py"], lista="~smc/*\nscripts/*\n", contents=_modelo(), body=TASK + "\nThreat model: no aplica: motivo suficiente"), False, [], "no aplica: motivo suficiente",
      id="modelo_sin_tocar_con_linea_no_aplica_pasa_por_la_linea"),
    P(dict(files=["scripts/x.py", "docs/threat-model/SMC-999.md"], contents={**_modelo(), **_modelo(tarea="SMC-999")}), True,
      ["SMC-777", "no lo añade ni lo modifica"], None, id="task_de_otra_tarea_con_modelo_existente_no_vale"),
    P(dict(files=["scripts/x.py", {"filename": MODELO_PATH, "status": "added"}], contents=_modelo()), False, [], MODELO_PATH,
      id="modelo_anadido_pasa"),
    P(dict(files=["scripts/x.py", {"filename": MODELO_PATH, "status": "renamed", "previous_filename": "docs/threat-model/viejo.md"}],
           contents=_modelo()), False, [], MODELO_PATH, id="modelo_renombrado_cuenta_como_tocado"),
    P(dict(files=["scripts/x.py", {"filename": "docs/threat-model/nuevo.md", "status": "renamed", "previous_filename": MODELO_PATH}],
           contents=_modelo()), True, ["SMC-777", "no lo añade ni lo modifica"], None, id="modelo_movido_a_otro_nombre_no_vale_su_ruta_antigua"),
    P(dict(files=["scripts/x.py", {"filename": MODELO_PATH, "status": "removed"}], contents=_modelo()), True, ["SMC-777"], None,
      id="modelo_borrado_no_vale"),
    P(dict(commits=["a\n\nTask: SMC-777", "b\n\nTask: SMC-778"], files=["scripts/x.py", MODELO_PATH, "docs/threat-model/SMC-778.md"],
           contents={**_modelo(), **_modelo(tarea="SMC-778")}), False, [], "docs/threat-model/SMC-777.md, docs/threat-model/SMC-778.md",
      id="varias_tareas_basta_con_que_cada_una_cumpla"),
    P(dict(commits=["a\n\nTask: SMC-777", "b\n\nTask: SMC-778"], files=["scripts/x.py", MODELO_PATH],
           contents={**_modelo(), **_modelo(tarea="SMC-778")}), True, ["SMC-778"], "docs/threat-model/SMC-777.md",
      id="varias_tareas_una_existente_sin_tocar_no_vale"),
    # N1: sin lista en la base falla aunque haya modelo
    P(dict(lista=None, contents=_modelo()), True, ["falta", LISTA_PATH], MODELO_PATH, id="sin_lista_en_la_base_falla_aunque_haya_modelo"),
    # Issue: el modelo declara `**Issue:** #N` y N está entre las que cierra el PR
    P(dict(contents=_modelo(MODELO_OK.replace("**Issue:** #1", "**Issue:** #2"))), True, ["Issue", "#2"], MODELO_PATH,
      id="modelo_de_otra_issue_no_vale"),
    P(dict(contents=_modelo(MODELO_OK.replace("**Issue:** #1 · ", ""))), True, ["Issue"], MODELO_PATH, id="modelo_sin_issue_declarada_no_vale"),
    P(dict(contents=_modelo(MODELO_OK.replace("**Issue:** #1", "<!-- **Issue:** #1 -->"))), True, ["Issue"], MODELO_PATH,
      id="issue_en_comentario_html_no_cuenta"),
    P(dict(contents=_modelo(), body="Task: SMC-777"), True, ["Issue", "#1"], MODELO_PATH, id="pr_que_no_cierra_ninguna_issue_con_modelo_no_vale"),
    P(dict(contents=_modelo(), body="Closes #9\nCloses #1\nTask: SMC-777"), False, [], MODELO_PATH,
      id="basta_con_que_una_de_las_issues_que_cierra_sea_la_del_modelo"),
    P(dict(contents=_modelo(MODELO_OK.replace("**Issue:** #1", "**Issue:** #12"))), True, ["Issue", "#12"], MODELO_PATH, id="issue_12_no_es_la_1"),
    # N9: el motivo de «no aplica» no puede ser un placeholder ni una excusa vacía
    *[P(dict(body=TASK + f"\nThreat model: no aplica: {m}"), True, ["motivo"], None, id=f"motivo_no_valido_{i}") for i, m in enumerate(
        ["<motivo>", ".", "<otro texto>", "<motivo> <motivo> <motivo>", "corto", "x" * 14, "...............", "solo <motivo>",
         "<a>" * 10, "- - - - - - - - - - - -"])],
    P(dict(files=["smc/visor.py", MODELO_PATH], lista="~smc/*\nscripts/*\n", body=TASK + "\nThreat model: no aplica: " + "x" * 15 + " ahora sí"), False, [], "no aplica: " + "x" * 15 + " ahora sí",
      id="motivo_de_quince_o_mas_caracteres_pasa"),
    # T13: «no aplica» no vale en tipo sec ni al tocar la lista, change_evidence.py o un workflow
    *[P(dict(files=fs, title=t, body=TASK + "\nThreat model: no aplica: motivo que no se debe aceptar"), True, ["no aplica"], None, id=i)
      for i, (fs, t) in {
          "no_aplica_no_vale_en_tipo_sec": (["README.md"], "sec: algo"),
          "no_aplica_no_vale_al_tocar_la_lista": ([LISTA_PATH], "feat: algo"),
          "no_aplica_no_vale_al_tocar_change_evidence": (["scripts/change_evidence.py"], "feat: algo"),
          "no_aplica_no_vale_al_tocar_un_workflow": ([".github/workflows/ci.yml"], "feat: algo"),
          "no_aplica_no_vale_al_tocar_un_workflow_en_subcarpeta": ([".github/workflows/sub/x.yml"], "feat: algo"),
          "no_aplica_no_vale_si_el_workflow_se_renombra_desde_fuera": (
              [{"filename": "docs/otro.yml", "previous_filename": ".github/workflows/ci.yml", "status": "renamed"}], "feat: algo"),
      }.items()],
    P(dict(files=["README.md", MODELO_PATH], title="sec: algo", contents=_modelo()), False, [], MODELO_PATH, id="tipo_sec_con_modelo_pasa"),
]


@pytest.mark.parametrize("kw,hay_problemas,fragmentos,threat_model", CASOS_MODELO)
def test_exige_threat_model_o_linea_no_aplica_con_motivo(ce, monkeypatch, kw, hay_problemas, fragmentos, threat_model):
    gh, r = _gate(ce, monkeypatch, **{"files": ["scripts/x.py", MODELO_PATH], **kw})
    assert r["required"] is True and bool(r["problems"]) is hay_problemas and r["threat_model"] == threat_model
    assert all(any(f in p for p in r["problems"]) for f in fragmentos)
    assert all("ref=H" in x for x in gh.leyo("threat-model"))  # el threat model sale de la cabeza


ACEPTADA = MODELO_OK + "| T3 | DoS | x | y | 1 | 1 | 1 | z |  | aceptada |\n"
_S5 = ("\n## 5. Riesgos aceptados\n| ID | Justificación | Aceptado por | Fecha | Revisar en |\n|---|---|---|---|---|\n")
PLANTILLA = (RAIZ / "docs/threat-model/TEMPLATE.md").read_text(encoding="utf-8")
CASOS_CONTENIDO = [
    P(MODELO_OK, [], id="todo_cerrado_pasa"),
    *[P(MODELO_OK.replace("| mitigada", f"| {e}"), ["abierta"], id=f"estado_{i}") for i, e in enumerate(
        ["abierta", "Abierta", "ABIERTA", " abierta ", "`abierta`", "**abierta**"])],
    P(MODELO_OK + "| T3 | DoS | x | y | 1 | 1 | 1 | z | `tests/a.py::t` | abierta |\n", ["T3"], id="una_fila_abierta_entre_cerradas"),
    P(MODELO_OK + "<!-- | T9 | x | y | 1 | 1 | 1 | z | w | abierta | -->\n", [], id="abierta_en_comentario_html_no_cuenta"),
    P(MODELO_OK + "\nLa amenaza T9 quedó abierta en la v0 y se cerró.\n", [], id="abierta_en_prosa_no_cuenta"),
    # N7: `abierta` en cualquier celda de una línea de tabla, con o sin `|` inicial y con cualquier cabecera
    P(MODELO_OK + "T3 | DoS | x | y | 1 | 1 | 1 | z | w | abierta\n", ["abierta"], id="abierta_sin_pipe_inicial_no_pasa"),
    P(MODELO_OK + "T3 | DoS | x | y | 1 | 1 | 1 | z | w | `abierta` |\n", ["abierta"], id="abierta_sin_pipe_inicial_en_negrita_no_pasa"),
    P(MODELO_OK + "\n| ID | Situación |\n|---|---|\n| T9 | abierta |\n", ["abierta"], id="abierta_en_tabla_sin_columna_estado_no_pasa"),
    P(MODELO_OK + "\n| ID | Estado | Estado |\n|---|---|---|\n| T9 | mitigada | abierta |\n", ["abierta"], id="abierta_en_la_segunda_columna_estado_no_pasa"),
    P(MODELO_OK + "\n| ID | Estado | Estado |\n|---|---|---|\n| T9 | mitigada | mitigada |\n", ["dos columnas"], id="dos_columnas_estado_no_pasan"),
    P(MODELO_OK + "\n| ID | Nota |\n|---|---|\n| T9 | La puerta abierta es el riesgo |\n", [], id="abierta_dentro_de_una_frase_de_una_celda_no_cuenta"),
    P(MODELO_OK + "\n| ID | Nota |\n|---|---|\n| T9 | La amenaza está abierta | \n", [], id="abierta_al_final_de_una_frase_de_una_celda_no_cuenta"),
    # N7: `mitigada` exige mitigación y test no vacíos
    P(MODELO_OK.replace("| z | `tests/test_x.py::test_x` | mitigada |", "|  | `tests/test_x.py::test_x` | mitigada |", 1), ["T1", "mitigación"],
      id="mitigada_sin_mitigacion_no_pasa"),
    P(MODELO_OK.replace("| z | `tests/test_x.py::test_x` | mitigada |", "| z |  | mitigada |", 1), ["T1", "test"], id="mitigada_sin_test_no_pasa"),
    P(MODELO_OK.replace("| z | `tests/test_x.py::test_x` | mitigada |", "|  |  | mitigada |", 1), ["T1", "mitigación", "test"],
      id="mitigada_sin_mitigacion_ni_test_no_pasa"),
    P(MODELO_OK.replace("| z | `tests/test_x.py::test_x` | mitigada |", "| z |   | mitigada |", 1), ["T1", "test"], id="mitigada_con_test_en_blanco_no_pasa"),
    P(MODELO_OK + "| T3 | DoS | x | y | 1 | 1 | 1 |  |  | aceptada |\n" + _S5 + "| T3 | porque | David Moya | 2026-11-07 |  |\n", [],
      id="aceptada_no_exige_mitigacion_ni_test"),
    P("| ID | Estado |\n|---|---|\n| T1 | mitigada |\n", ["T1", "mitigación"], id="mitigada_en_tabla_sin_columnas_de_mitigacion_no_pasa"),
    *[P(MODELO_OK + f"\nCampo: {ph}\n", ["placeholder"], id=f"placeholder_{i}") for i, ph in enumerate(
        ["<TASK_ID>", "<feature>", "<n>", "<slug>", "YYYY-MM-DD", "docs/adr/NNNN-x.md", "`tests/...::test_...`", "sí / no"])],
    P(MODELO_OK + "\n<!-- rellenar <TASK_ID> -->\n", [], id="placeholder_en_comentario_html_no_cuenta"),
    P(PLANTILLA, ["abierta", "placeholder"], id="la_plantilla_sin_rellenar_no_pasa"),
    # un modelo sin filas de amenaza no pasa
    *[P(t, ["filas"], id=f"sin_filas_de_amenaza_{i}") for i, t in enumerate([
        "", "# x\n", "# x\n\n## 3. Amenazas (STRIDE)\n", "solo prosa sobre amenazas mitigadas\n",
        "| ID | Estado |\n|---|---|\n", "| ID | Amenaza |\n|---|---|\n| T1 | x |\n",
        "<!-- " + MODELO_OK + " -->\n"])],
    # estado en vocabulario cerrado: solo mitigada o aceptada, la celda entera
    *[P(MODELO_OK.replace("| mitigada", f"| {e}"), ["estado"], id=f"estado_fuera_del_vocabulario_{i}") for i, e in enumerate([
        "abierta (pendiente)", "abierta, ver T3", "abierto", "abierta.", "mitigada (parcial)", "mitigada y aceptada", "no mitigada",
        "pendiente", "mitigado", "", " - ", "n/a"])],
    *[P(MODELO_OK.replace("| mitigada", f"| {e}"), [], id=f"estado_valido_{i}") for i, e in enumerate(
        ["Mitigada", "MITIGADA", " mitigada ", "`mitigada`", "**mitigada**", "_mitigada_"])],
    P(MODELO_OK.replace("T1", "T9").replace("| mitigada", "| abierto"), ["T9", "abierto"], id="el_problema_nombra_la_amenaza_y_el_estado"),
    # una aceptada exige su fila firmada en la sección 5 (columna «Fecha» con fecha)
    P(ACEPTADA, ["T3", "fecha de aceptación"], id="aceptada_sin_seccion_5_no_pasa"),
    P(ACEPTADA + _S5 + "| T3 | porque | David Moya |  |  |\n", ["T3", "fecha de aceptación"], id="aceptada_con_fecha_vacia_no_pasa"),
    *[P(ACEPTADA + _S5 + f"| T3 | porque | David Moya | {f} |  |\n", ["T3", "fecha de aceptación"], id=f"aceptada_con_fecha_ilegible_{i}") for i, f in enumerate(
        ["pendiente", "2026-13-45", "2026-02-30", "07/11/2026", "2026-11-07T10:00", "20261107", "2026-1-7", "YYYY-MM-DD",
         "`tests/test_x.py::test_y`", "tests/test_x.py::test_y", "2026-11-07 y 2026-11-08", "hoy"])],
    P(ACEPTADA + _S5 + "| T3 | porque |  | 2026-11-07 |  |\n", ["T3", "fecha de aceptación"], id="aceptada_sin_nadie_que_acepte_no_pasa"),
    P(ACEPTADA + _S5 + "| T3 | porque | David Moya |  | 2026-11-07 |\n", ["T3", "fecha de aceptación"], id="la_fecha_se_busca_en_su_columna"),
    P(ACEPTADA + _S5 + "| T9 | porque | David Moya | 2026-11-07 |  |\n", ["T3", "fecha de aceptación"], id="la_fila_firmada_es_de_otra_amenaza"),
    P(ACEPTADA + _S5.replace("5. Riesgos aceptados", "6. Otra cosa") + "| T3 | porque | David Moya | 2026-11-07 |  |\n", ["T3", "fecha de aceptación"],
      id="la_tabla_firmada_fuera_de_la_seccion_5_no_vale"),
    P(ACEPTADA + _S5 + "<!-- | T3 | porque | David Moya | 2026-11-07 |  | -->\n", ["T3", "fecha de aceptación"], id="fila_firmada_en_comentario_html_no_vale"),
    P(ACEPTADA + _S5 + "| T3 | porque | David Moya | 2026-11-07 |  |\n", [], id="aceptada_con_fecha_valida_pasa"),
    P(ACEPTADA + _S5 + "| `T3` | porque | David Moya | **2026-11-07** |  |\n", [], id="aceptada_con_fecha_en_negrita_pasa"),
    P(ACEPTADA + "| T4 | DoS | x | y | 1 | 1 | 1 | z | w | aceptada |\n" + _S5 + "| T3 | porque | David Moya | 2026-11-07 |  |\n",
      ["T4", "fecha de aceptación"], id="una_de_dos_aceptadas_sin_firmar_no_pasa"),
    P(MODELO_OK + "\n" + _S5 + "| T7 | sobra | David Moya |  |  |\n", [], id="una_fila_de_aceptacion_sin_aceptada_no_estorba"),
]


@pytest.mark.parametrize("texto,fragmentos", CASOS_CONTENIDO)
def test_contenido_del_threat_model(ce, texto, fragmentos):
    problemas = ce.threat_model_problems(texto)
    assert (problemas == []) is (fragmentos == []) and all(any(f in p for p in problemas) for f in fragmentos)


CASOS_PUROS = [
    P(lambda ce: ce.parse_security_paths("# cab\n\n.github/workflows/*\n  scripts/*   # todo\r\nsmc/visor.py\t# otro\n#solo\n   \n")
      == [".github/workflows/*", "scripts/*", "smc/visor.py"], id="lista_ignora_comentarios_y_vacias"),
    *[P(lambda ce, t=t, e=e: ce.pr_title_type(t) == e, id=f"tipo_del_titulo_{i}") for i, (t, e) in enumerate(
        [("sec: x", "sec"), ("sec(gate): x", "sec"), ("sec!: x", "sec"), ("SEC: x", "sec"), ("feat: sec", None),
         ("security: x", None), ("secure(x): y", None), ("", None)])],
    P(lambda ce: ce.no_aplica_reason("Threat model: no aplica: x") == "x" and ce.no_aplica_reason("Threat model: no aplica:") == ""
      and ce.no_aplica_reason("nada") is None and ce.no_aplica_reason("<!-- Threat model: no aplica: x -->") is None, id="no_aplica_reason"),
    *[P(lambda ce, m=m: ce.no_aplica_invalid(m) is not None, id=f"no_aplica_invalid_rechaza_{i}") for i, m in enumerate(
        ["", "<motivo>", ".", "<x>", "corto", "x" * 14, "a b c d e f g", "<a> <b> <c> <d>", "-" * 20, "<motivo> ya"])],
    *[P(lambda ce, m=m: ce.no_aplica_invalid(m) is None, id=f"no_aplica_invalid_acepta_{i}") for i, m in enumerate(
        ["solo renombra una variable", "x" * 15 + " ok", "texto con <b>etiqueta</b> de más de quince", "añade un comentario de documentación"])],
    *[P(lambda ce, t=t, e=e: ce.safe_text(t) == e, id=f"safe_text_{i}") for i, (t, e) in enumerate(
        [("a\nb", "a b"), ("a\r\n::error::x", "a ::error::x"), ("\x1b[31mrojo\x1b[0m", "[31mrojo[0m"), ("tab\taqui", "tab aqui"),
         ("normal ñ é", "normal ñ é"), ("a\u2028b\u202ec", "a bc"), ("a\x00b", "ab"), ("", "")])],
    P(lambda ce: [s["id"] for s in ce.status_at_merge(
        [_estado(1, "success", DESPUES), _estado(2, "success", DESPUES, ctx="security-review")], MERGE)[0]] == [2],
      id="status_at_merge_por_defecto_corta_solo_blind_review"),
    P(lambda ce: ce.status_at_merge([_estado(1, "success", DESPUES), _estado(2, "success", DESPUES, ctx="security-review")],
                                    MERGE, ("blind-review", "security-review"))[0] == [], id="status_at_merge_corta_los_contextos_pedidos"),
]


@pytest.mark.parametrize("comprobacion", CASOS_PUROS)
def test_funciones_puras_de_la_puerta(ce, comprobacion):
    assert comprobacion(ce)


def _filas_s5(ce, texto):
    sin = ce.HTML_COMMENT_RE.sub("", texto).partition("## 5.")[2]
    return [[c.strip() for c in _re.split(r"(?<!\\)\|", l.strip().strip("|"))] for l in sin.splitlines()
            if _re.match(r"\|\s*T\d+\s*\|", l)]


def test_el_threat_model_de_smc_009_esta_aceptado_por_david_y_cada_mitigacion_tiene_su_test(ce):
    texto = (RAIZ / "docs/threat-model/SMC-009.md").read_text(encoding="utf-8")
    sin_comentarios = ce.HTML_COMMENT_RE.sub("", texto)
    filas = [[c.strip() for c in _re.split(r"(?<!\\)\|", l.strip().strip("|"))] for l in sin_comentarios.partition("## 5.")[0].splitlines()
             if _re.match(r"\|\s*T\d+\s*\|", l)]
    ids = [f[0] for f in filas]
    assert len(ids) == len(set(ids)) and "T12" not in ids
    assert {"T11", "T13", "T18", "T19", "T20", "T21", "T22", "T23", "T24", "T25", "T28", "T29", "T30", "T31", "T32", "T33", "T34"} <= set(ids)
    fuente = "".join((RAIZ / n).read_text(encoding="utf-8") for n in ("tests/test_change_evidence.py", "tests/test_vigilancia.py"))
    aceptadas = []
    for f in filas:
        estado = f[-1].strip("`* ").lower()
        assert estado in ("mitigada", "aceptada"), f
        if estado == "mitigada":
            refs = _re.findall(r"`(tests/[\w./]+)::(\w+)(?:\[(\w+)\])?`", f[-2])
            assert refs and "pendiente" not in f[-2], f
            for fichero, nombre, caso in refs:
                assert (RAIZ / fichero).exists(), (f[0], fichero)
                assert _re.search(rf"^def {nombre}\(", fuente, _re.MULTILINE), (f[0], nombre)
                prefijo = _re.sub(r"_\d+$", "", caso)  # los ids generados (`id=f"nombre_{i}"`) se comprueban por su prefijo
                assert not caso or f'id="{caso}"' in fuente or f'id=f"{prefijo}_{{' in fuente, (f[0], caso)
        else:
            aceptadas.append(f[0])
    # T11 ya no es una aceptación: pull_request_target la mitiga
    por_id = {f[0]: f for f in filas}
    assert por_id["T11"][-1].strip("`* ").lower() == "mitigada" and "T11" not in aceptadas
    # las amenazas de vigilancia (job de T52) son mitigadas, con tests de tests/test_vigilancia.py
    for t in ("T14", "T15", "T16"):
        assert por_id[t][-1].strip("`* ").lower() == "mitigada" and "tests/test_vigilancia.py::" in por_id[t][-2], t
    # la fecha de aceptación es la columna «Fecha» de §5: la rellena David, ningún agente (commit 13a2826, 2026-11-07).
    s5 = _filas_s5(ce, texto)
    assert sorted(f[0] for f in s5) == sorted(aceptadas) == ["T13", "T23", "T24", "T25", "T30", "T31", "T32"], (aceptadas, s5)
    for f in s5:
        assert len(f) == 5 and f[2] == "David Moya" and _re.fullmatch(r"\d{4}-\d{2}-\d{2}", f[3]), f
    # con las fechas puestas, el modelo pasa su propia puerta, y declara la issue del PR
    assert ce.threat_model_problems(texto, [28]) == []
    assert any("Issue" in p for p in ce.threat_model_problems(texto, [27]))


# --- lectura de ficheros de la API ---
CASOS_LECTURA = [
    P(contenido("á" * 200 + "\nfin\n"), "á" * 200 + "\nfin\n", id="decodifica_el_base64_partido_cada_60_caracteres"),
    P(fallo_404_github(), None, id="404_es_ausencia"),
    *[P(fallo(c, t), subprocess.CalledProcessError, id=f"otro_error_{c}_{t}") for c, t in [(403, "json"), (500, "html"), (502, "vacio_json")]],
    *[P(r, ValueError, id=f"no_es_un_fichero_legible_{i}") for i, r in enumerate([
        [{"name": "TEMPLATE.md", "type": "file"}], {"type": "dir"}, {"type": "symlink", "target": "x"}, {"type": "submodule"},
        {"type": "file", "encoding": "none", "content": ""}, {"type": "file", "encoding": "base64"},
        {"type": "file", "encoding": "base64", "content": "@@@no-es-base64@@@"}])],
]


@pytest.mark.parametrize("respuesta,esperado", CASOS_LECTURA)
def test_leer_fichero_distingue_ausencia_de_error(ce, monkeypatch, respuesta, esperado):
    monkeypatch.setattr("time.sleep", lambda s: None)
    if isinstance(respuesta, Exception):
        _falla_api(ce, monkeypatch, respuesta)
    else:
        monkeypatch.setattr(ce, "gh_json", lambda p: respuesta)
    if isinstance(esperado, type):
        with pytest.raises(esperado):
            ce.read_file_at("o/r", "x", "H")
    else:
        assert ce.read_file_at("o/r", "x", "H") == esperado


@pytest.mark.parametrize("ref", ["feat/x", "a&ref=main", "x#y", "x?y=1", "con espacio", "100%", "a+b", "ñ", "x\ny", "-h", "../main", "x;ls"])
def test_leer_fichero_escapa_ref_y_ruta(ce, monkeypatch, ref):
    from urllib.parse import parse_qs, unquote, urlsplit
    vistos = []
    monkeypatch.setattr(ce, "gh_json", lambda p: vistos.append(p) or contenido("hola\n"))
    assert ce.read_file_at("o/r", "docs/a b#c?d.md", ref) == "hola\n"
    u = urlsplit(vistos[0])
    assert u.fragment == "" and not any(c in vistos[0] for c in " \n") and vistos[0].startswith("repos/o/r/contents/")
    assert parse_qs(u.query, keep_blank_values=True) == {"ref": [ref]}      # ni parámetros extra ni ref truncada
    assert unquote(u.path) == "repos/o/r/contents/docs/a b#c?d.md"


def test_leer_fichero_404_con_gh_falso_y_los_bytes_medidos(ce, gh_falso):
    out = ("HTTP/2.0 404 Not Found\r\nContent-Length: %d\r\nContent-Type: application/json; charset=utf-8\r\n\r\n%s"
           % (len(GITHUB_404), GITHUB_404)).encode()
    gh_falso.pon(out, "gh: Not Found (HTTP 404)\n", rc=1)
    assert ce.read_file_at("o/r", ".github/security-paths.txt", "main") is None
    assert gh_falso.llamadas() == ["api -i -H Accept: application/vnd.github+json repos/o/r/contents/.github/security-paths.txt?ref=main"]


# --- el modo security: fallo en cerrado y salida ---
E403, E502, ERED = fallo(403), fallo(502, "html"), fallo_red()
CASOS_MODO = [
    # (kwargs de FakeSec, código de salida, texto en stdout, texto en stderr, texto que NO debe salir en stderr)
    P(dict(files=["scripts/x.py", MODELO_PATH], contents=_modelo()), 0, "docs/threat-model/SMC-777.md", "", "ERROR", id="ok_sale_con_0_y_resume"),
    P(dict(files=["README.md"]), 0, "no aplica la puerta", "", "ERROR", id="sin_puerta_sale_con_0"),
    P(dict(files=["scripts/x.py"]), 1, "", "SMC-777", "", id="incumplido_sale_con_1_y_dice_que_falta"),
    P(dict(files=["scripts/x.py", MODELO_PATH], contents=_modelo(SUCIO)), 1, "", "abierta", "", id="amenaza_abierta_sale_con_1"),
    P(dict(files=["README.md"], lista=None), 1, "", LISTA_PATH, "", id="sin_lista_en_la_base_falla_en_cerrado"),
    P(dict(files=FICHEROS_RELEASE, head_ref=RELEASE, lista="*\n"), 0, "release", "", "ERROR", id="pr_de_release_sale_con_0"),
    P(dict(files=["scripts/x.py"], fail={LISTA_PATH: fallo(403)}), 1, "", "ERROR", "", id="403_en_la_lista_no_es_lista_ausente"),
    P(dict(files=["README.md"], fail={"/pulls/7/files": ValueError("json roto")}), 1, "", "ERROR", "", id="excepcion_inesperada_sale_con_1"),
    P(dict(files=["scripts/x.py"], contents={("H", "docs/threat-model/SMC-777.md"): [{"name": "a"}]}), 1, "", "ERROR", "",
      id="threat_model_que_es_una_carpeta_es_error"),
    P(dict(nfiles=3000), 1, "", "3000", "", id="3000_ficheros_es_lectura_incompleta"),
    P(dict(nfiles=2999), 0, "", "", "ERROR", id="2999_ficheros_se_leen"),
    *[P(dict(files=["scripts/x.py", MODELO_PATH], contents=_modelo(), fail={que: err}), 1, "", "ERROR", "", id=f"api_caida_{n}_{e}")
      for que, n in [("/pulls/7", "pr"), ("/pulls/7/files", "ficheros"), ("/pulls/7/commits", "commits"), (LISTA_PATH, "lista"),
                     ("threat-model", "threat_model")]
      for err, e in [(E403, "403"), (E502, "502"), (ERED, "red")]],
    P(dict(_cli=True), 0, "", "", "ERROR", id="la_linea_de_comandos_acepta_security_pr"),
]


@pytest.mark.parametrize("kw,rc_esperado,en_out,en_err,no_en_err", CASOS_MODO)
def test_modo_security(ce, monkeypatch, capsys, kw, rc_esperado, en_out, en_err, no_en_err):
    import argparse
    monkeypatch.setattr("time.sleep", lambda s: None)
    cli = kw.pop("_cli", False)
    _sec(ce, monkeypatch, **kw)
    monkeypatch.setattr(ce, "repo_slug", lambda: "o/r")
    if cli:
        monkeypatch.setattr("sys.argv", ["change_evidence.py", "security", "--pr", "7", "--head-sha", "H"])
        with pytest.raises(SystemExit) as ei:
            ce.main()
        rc = ei.value.code
    else:
        rc = ce.mode_security(argparse.Namespace(pr=7, head_sha="H"))
    cap = capsys.readouterr()
    assert rc == rc_esperado and en_out in cap.out and en_err in cap.err and (not no_en_err or no_en_err not in cap.err)


# --- el registro: campo security, corte en merged_at, markdown y fallo de API ---
def _reg(ce, monkeypatch, **kw):
    _sec(ce, monkeypatch, **kw)
    return ce.collect_pr("o/r", 7)


def _sr(i, estado, creado):
    return _estado(i, estado, creado, ctx="security-review")


CASOS_REGISTRO = [
    P(dict(files=["README.md"]), lambda p, ce: set(p["security"]) == {"required", "reason", "threat_model", "review"}
      and p["security"]["required"] is False and p["security"]["threat_model"] is None and p["security"]["review"] is None
      and p["gaps"] == [], id="sin_puerta_lleva_el_campo_y_ningun_hueco"),
    P(dict(files=["scripts/x.py", MODELO_PATH], contents=_modelo(), statuses=[_sr(1, "success", ANTES)]),
      lambda p, ce: p["security"]["required"] is True and p["security"]["reason"]
      and p["security"]["threat_model"] == "docs/threat-model/SMC-777.md" and p["security"]["review"] == "success",
      id="recoge_aplica_threat_model_y_security_review"),
    P(dict(files=["smc/visor.py"], lista="~smc/*\nscripts/*\n", body="Task: SMC-777\nThreat model: no aplica: motivo suficiente"),
      lambda p, ce: p["security"]["threat_model"] == "no aplica: motivo suficiente", id="recoge_la_linea_no_aplica"),
    P(dict(files=["scripts/x.py"], statuses=[_estado(1, "success", ANTES)]),
      lambda p, ce: p["security"]["review"] is None and p["blind_review"]["state"] == "success", id="no_confunde_blind_review_con_security_review"),
    P(dict(files=["scripts/x.py"], statuses=[_sr(2, "failure", DESPUES), _sr(1, "success", ANTES)]),
      lambda p, ce: p["security"]["review"] == "failure", id="sin_fusionar_cuenta_el_mas_reciente"),
    P(dict(files=["scripts/x.py"], statuses=[_sr(1, "success", DESPUES)], merged_at=MERGE),
      lambda p, ce: p["security"]["review"] is None, id="security_review_posterior_al_merge_no_cuenta"),
    P(dict(files=["scripts/x.py"], statuses=[_sr(1, "success", ANTES), _sr(2, "failure", DESPUES)], merged_at=MERGE),
      lambda p, ce: p["security"]["review"] == "success", id="el_posterior_no_sustituye_al_previo"),
    P(dict(files=["scripts/x.py"], statuses=[_sr(1, "success", A_LAS)], merged_at=MERGE),
      lambda p, ce: p["security"]["review"] == "success", id="justo_en_merged_at_cuenta"),
    P(dict(files=["scripts/x.py"], statuses=[_estado(1, "success", DESPUES), _sr(2, "success", DESPUES)], merged_at=MERGE),
      lambda p, ce: p["blind_review"] is None and p["security"]["review"] is None, id="el_corte_vale_para_los_dos_contextos"),
    P(dict(files=["scripts/x.py"], statuses=[_sr(1, "success", "ayer")], merged_at=MERGE),
      lambda p, ce: p["security"]["review"] == "success" and any("security-review" in g and "ilegible" in g for g in p["gaps"]),
      id="created_at_ilegible_cuenta_y_deja_hueco"),
    P(dict(files=["scripts/x.py"], fail={"/pulls/7/files": fallo(502)}),
      lambda p, ce: p["security"]["required"] is None and p["security"]["review"] is None
      and any("PR #7" in g and "puerta de seguridad" in g for g in p["gaps"]), id="fallo_de_api_deja_hueco_y_no_aborta"),
    P(dict(files=FICHEROS_RELEASE, head_ref=RELEASE, lista="*\n"),
      lambda p, ce: p["maint"] is True and p["security"]["required"] is False, id="pr_de_release_no_aplica"),
    P(dict(files=["scripts/x.py", MODELO_PATH], contents=_modelo()),
      lambda p, ce: "Puerta de seguridad" in ce.pr_markdown(p) and "docs/threat-model/SMC-777.md"
      in ce.pr_markdown(p), id="el_markdown_muestra_la_puerta"),
]


@pytest.mark.parametrize("kw,comprobacion", CASOS_REGISTRO)
def test_registro_con_campo_security(ce, monkeypatch, kw, comprobacion):
    assert comprobacion(_reg(ce, monkeypatch, **kw), ce)


# --- el pack de release y el modo pr ---
def _pack(ce, monkeypatch, tmp_path, **kw):
    import argparse
    _sec(ce, monkeypatch, **kw)
    monkeypatch.setattr(ce, "previous_tag", lambda tag: "v0")
    monkeypatch.setattr(ce, "repo_slug", lambda: "o/r")
    monkeypatch.setattr(ce, "git_range_commits", lambda rng: [{"sha": "a" * 40, "subject": "feat: algo (#7)", "author": "x", "tasks": []}])
    ce.mode_release(argparse.Namespace(tag="v1", out=str(tmp_path), offline=False))
    return json.loads((tmp_path / "change-record.json").read_text(encoding="utf-8"))["gaps"]


def _hueco(gaps, estado):
    return any("PR #7" in g and "security-review" in g and f"(estado: {estado})" in g for g in gaps)


CASOS_PACK = [
    P(dict(files=["scripts/x.py", MODELO_PATH], contents=_modelo()), lambda g: _hueco(g, "—"), id="aplica_sin_security_review_deja_hueco"),
    *[P(dict(files=["scripts/x.py", MODELO_PATH], contents=_modelo(), statuses=[_sr(1, e, ANTES)]), lambda g, e=e: _hueco(g, e),
        id=f"security_review_{e}_deja_hueco") for e in ["failure", "pending", "error"]],
    P(dict(files=["scripts/x.py", MODELO_PATH], contents=_modelo(), statuses=[_sr(1, "success", ANTES), _estado(2, "success", ANTES)], merged_at=MERGE),
      lambda g: not any("security-review" in x for x in g), id="security_review_correcto_no_deja_hueco"),
    P(dict(files=["README.md"]), lambda g: not any("security-review" in x for x in g), id="sin_puerta_no_deja_hueco"),
    P(dict(files=["scripts/x.py", MODELO_PATH], contents=_modelo(), merged_at=MERGE, statuses=[_sr(1, "success", DESPUES)]),
      lambda g: _hueco(g, "—"), id="security_review_solo_posterior_al_merge_deja_hueco"),
    P(dict(files=FICHEROS_RELEASE, head_ref=RELEASE, lista="*\n"), lambda g: not any("security-review" in x for x in g),
      id="el_pr_de_release_no_deja_hueco"),
]


@pytest.mark.parametrize("kw,comprobacion", CASOS_PACK)
def test_pack_de_release_anota_el_hueco_de_security_review(ce, monkeypatch, tmp_path, kw, comprobacion):
    assert comprobacion(_pack(ce, monkeypatch, tmp_path, **kw))


# --- el workflow y la lista de rutas del repositorio ---
GATE_YML = RAIZ / ".github/workflows/security-gate.yml"


def _yml(ruta):
    import yaml
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


def _gate_doc():
    return _yml(GATE_YML)


def _gate_job():
    return _gate_doc()["jobs"]["security-gate"]


def _sin_comentarios(ruta):
    return _re.sub(r"(?m)^\s*#.*$", "", ruta.read_text(encoding="utf-8"))


def _c_target():
    doc = _gate_doc()
    on = doc.get("on") or doc.get(True)
    return set(on) == {"pull_request_target"} and {"opened", "edited", "synchronize", "reopened"} <= set(on["pull_request_target"]["types"])


def _c_pr_meta_sin_puerta():
    doc = _yml(RAIZ / ".github/workflows/pr-meta.yml")
    texto = _sin_comentarios(RAIZ / ".github/workflows/pr-meta.yml")
    return "security-gate" not in doc["jobs"] and "pull_request_target" not in texto and "change_evidence.py security" not in texto


def _c_checkout_de_la_base():
    pasos = [s for s in _gate_job()["steps"] if "uses" in s]
    checkouts = [s for s in pasos if s["uses"].startswith("actions/checkout@")]
    return (len(checkouts) == 1 and all(not ({"ref", "repository", "path"} & set(s.get("with") or {})) for s in checkouts)
            and all(s["with"]["persist-credentials"] is False for s in checkouts))


def _c_nada_de_la_cabeza_en_with():
    todo = [v for s in _gate_job()["steps"] for v in (s.get("with") or {}).values()]
    return not any("head" in str(v) for v in todo) and not _re.search(r"(?mi)^\s*(ref|repository):.*head", _sin_comentarios(GATE_YML))


def _c_sin_interpolar():
    job = _gate_job()
    runs = [s["run"] for s in job["steps"] if "run" in s]
    env = {k: v for s in job["steps"] for k, v in (s.get("env") or {}).items()}
    return (len(runs) >= 2 and all("${{" not in r for r in runs) and any("python3 scripts/change_evidence.py security --pr \"$PR_NUMBER\"" in r for r in runs)
            and "pull_request.number" in env["PR_NUMBER"] and "GITHUB_TOKEN" in env["GH_TOKEN"])


def _c_actions_fijadas():
    usos = [s for s in _gate_job()["steps"] if "uses" in s]
    return bool(usos) and all(_re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", s["uses"]) for s in usos) \
        and all((s.get("with") or {}).get("persist-credentials") is False for s in usos if s["uses"].startswith("actions/checkout@"))


def _c_permisos():
    doc, job = _gate_doc(), _gate_job()
    assert "permissions" in doc and "permissions" in job
    escrituras = {k: v for k, v in (dict(doc["permissions"]) | dict(job["permissions"])).items() if v != "read"}
    return escrituras == {"statuses": "write"} and "statuses" not in doc["permissions"] and all(v == "read" for v in doc["permissions"].values())


def _c_publica_el_estado_en_la_cabeza():
    job = _gate_job()
    paso = next(s for s in job["steps"] if "statuses/" in s.get("run", ""))
    env = paso["env"]
    return (_re.sub(r"\s+", "", paso.get("if")) == "${{!cancelled()}}" and "head.sha" in job["env"]["HEAD_SHA"] and "steps.gate.outcome" in env["OUTCOME"]
            and "-f context=security-gate" in paso["run"] and "repos/$REPO/statuses/$HEAD_SHA" in paso["run"]
            and _re.search(r"\^\[0-9a-f\]\{40\}\$", paso["run"]) is not None)


def _c_el_job_acaba_en_rojo_si_la_puerta_falla():
    pasos = _gate_job()["steps"]
    gate = next(s for s in pasos if s.get("id") == "gate")
    ultimo = pasos[-1]
    return gate.get("continue-on-error") is True and "steps.gate.outcome" in ultimo.get("if", "") and "exit 1" in ultimo["run"]


def _rutas_lista():
    from importlib import util
    spec = util.spec_from_file_location("ce_lista", SCRIPT)
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.parse_security_paths((RAIZ / LISTA_PATH).read_text(encoding="utf-8"))


def _c_lista_n4():
    import fnmatch
    rutas = _rutas_lista()
    return all(any(fnmatch.fnmatchcase(f, r) for r in rutas) for f in [
        ".github/workflows/ci.yml", ".github/pull_request_template.md", ".github/security-paths.txt", "osv-scanner.toml",
        "release-please-config.json", "docs/threat-model/SMC-009.md", "docs/threat-model/TEMPLATE.md"])


def _c_lista():
    import fnmatch
    rutas = _rutas_lista()
    return (all(e in rutas for e in [".github/*", "scripts/*", "smc/report_html.py", "smc/dashboard.py", "smc/visor.py", "smc/evidencias.py",
                                     "osv-scanner.toml", "release-please-config.json", "docs/threat-model/*"])
            and any(fnmatch.fnmatchcase("scripts/change_evidence.py", r) for r in rutas)
            and any(fnmatch.fnmatchcase(".github/workflows/security-gate.yml", r) for r in rutas))


@pytest.mark.parametrize("comprobacion", [
    P(_c_target, id="usa_pull_request_target_con_los_tipos_de_edicion"),
    P(_c_pr_meta_sin_puerta, id="pr_meta_ya_no_tiene_la_puerta"),
    P(_c_checkout_de_la_base, id="un_solo_checkout_el_de_la_base_sin_ref_ni_repositorio"),
    P(_c_nada_de_la_cabeza_en_with, id="ningun_with_ni_ref_apunta_a_la_cabeza"),
    P(_c_sin_interpolar, id="no_interpola_datos_del_pr_en_el_shell"),
    P(_c_actions_fijadas, id="actions_fijadas_por_sha_y_sin_credenciales_persistidas"),
    P(_c_permisos, id="solo_escribe_statuses_y_solo_en_el_job"),
    P(_c_publica_el_estado_en_la_cabeza, id="publica_el_estado_security_gate_en_la_cabeza_siempre"),
    P(_c_el_job_acaba_en_rojo_si_la_puerta_falla, id="el_job_acaba_en_rojo_si_la_puerta_falla"),
    P(_c_lista, id="la_lista_de_rutas_sensibles_del_repositorio"),
    P(_c_lista_n4, id="la_lista_cubre_toda_la_carpeta_github_osv_release_y_threat_model"),
])
def test_workflow_security_gate_y_lista_de_rutas(comprobacion):
    assert comprobacion()


# --- N8: `ref` de la rama base escapado al leer release-please-config.json ---
@pytest.mark.parametrize("ref", ["main", "feat/x", "a&ref=evil", "x#y", "x?y=1", "con espacio", "100%", "x\ny", "../main"])
def test_allowed_release_files_escapa_ref(ce, monkeypatch, ref):
    from urllib.parse import parse_qs, urlsplit
    vistos = []
    monkeypatch.setattr(ce, "gh_json", lambda p: vistos.append(p) or contenido('{"packages": {".": {"extra-files": ["extra.txt"]}}}'))
    assert "extra.txt" in ce.allowed_release_files("o/r", ref)
    u = urlsplit(vistos[0])
    assert u.fragment == "" and not any(c in vistos[0] for c in " \n")
    assert parse_qs(u.query, keep_blank_values=True) == {"ref": [ref]}


# --- N9: nada de lo que controla el autor llega a la salida como comando de workflow ---
@pytest.mark.parametrize("nombre", [
    "scripts/x\n::error::falso.py", "scripts/x\r::set-output name=a::b.py", "scripts/\x1b]0;titulo\x07x.py", "scripts/a\u2028::debug::x.py",
])
def test_modo_security_no_imprime_lineas_de_comando_con_nombres_de_fichero(ce, monkeypatch, capsys, nombre):
    rc, out, err, _ = _modo_security(ce, monkeypatch, capsys, files=[nombre])
    assert rc == 1 and "scripts/" in out + err
    lineas = (out + err).splitlines()
    assert all(not l.lstrip().startswith("::") for l in lineas), lineas
    assert not any(c in out + err for c in "\x1b\r\x07\u2028")


def test_modo_security_no_imprime_lineas_de_comando_con_el_motivo(ce, monkeypatch, capsys):
    rc, out, err, _ = _modo_security(ce, monkeypatch, capsys, files=["smc/visor.py"], lista="~smc/*\n", title="feat: x",
                                     body="Closes #1\nTask: SMC-777\nThreat model: no aplica: motivo\x1b[0m\r::error::inyectado largo")
    assert rc == 0 and "::error::" in out
    assert all(not l.lstrip().startswith("::") for l in (out + err).splitlines())


# --- T55 · B2: el estado se publica sobre el SHA que se evaluó ---
EVENTO_SHA = "a" * 40
VIVA_SHA = "b" * 40


class _CabezaQueSeMueve(FakeSec):
    """Como FakeSec, pero la cabeza que devuelve `pulls/N` va cambiando en cada lectura: `cabezas[i]`."""

    def __init__(self, cabezas, **kw):
        super().__init__(**kw)
        self.cabezas = list(cabezas)
        self.lecturas = 0

    def __call__(self, path):
        if path.split("?")[0].endswith("/pulls/7"):
            sha = self.cabezas[min(self.lecturas, len(self.cabezas) - 1)]
            self.lecturas += 1
            self.paths.append(path)
            return {**self.pr, "head": {**self.pr["head"], "sha": sha}}
        return super().__call__(path)


def _security_con_cabezas(ce, monkeypatch, capsys, cabezas, head_sha, **kw):
    import argparse
    contents = {("main", LISTA_PATH): "scripts/*\n"}
    gh = _CabezaQueSeMueve(cabezas, contents=contents, **kw)
    monkeypatch.setattr(ce, "gh_json", gh)
    monkeypatch.setattr(ce, "PER_PAGE", 100)
    monkeypatch.setattr(ce, "repo_slug", lambda: "o/r")
    rc = ce.mode_security(argparse.Namespace(pr=7, head_sha=head_sha))
    cap = capsys.readouterr()
    return rc, cap.out, cap.err, gh


def test_b2_la_cabeza_del_evento_no_es_la_actual_falla(ce, monkeypatch, capsys):
    """Reproduce race.py: el evento trae A, el PR ya está en B (inocuo). Antes salía 0 y el workflow publicaba success sobre A."""
    rc, out, err, _ = _security_con_cabezas(ce, monkeypatch, capsys, [VIVA_SHA], EVENTO_SHA)
    assert rc == 1 and "ERROR" in err and EVENTO_SHA[:7] in err and VIVA_SHA[:7] in err
    assert "no aplica la puerta" not in out


def test_b2_la_cabeza_del_evento_es_la_actual_pasa(ce, monkeypatch, capsys):
    rc, out, err, _ = _security_con_cabezas(ce, monkeypatch, capsys, [EVENTO_SHA], EVENTO_SHA)
    assert rc == 0 and "ERROR" not in err and "no aplica la puerta" in out


def test_b2_la_cabeza_que_se_mueve_durante_la_evaluacion_falla(ce, monkeypatch, capsys):
    """Coincide al empezar y deja de ser la cabeza antes de acabar: los ficheros leídos podrían ser de otro commit."""
    rc, out, err, gh = _security_con_cabezas(ce, monkeypatch, capsys, [EVENTO_SHA, VIVA_SHA], EVENTO_SHA)
    assert rc == 1 and "ERROR" in err and gh.lecturas == 2


def test_b2_la_cabeza_que_se_mueve_en_una_puerta_que_no_aplica_tambien_falla(ce, monkeypatch, capsys):
    rc, _, err, _ = _security_con_cabezas(ce, monkeypatch, capsys, [EVENTO_SHA, VIVA_SHA], EVENTO_SHA, files=["README.md"])
    assert rc == 1 and "ERROR" in err


@pytest.mark.parametrize("sha", ["", "H2", "h", "HH"])
def test_b2_cualquier_sha_distinto_de_la_cabeza_falla(ce, monkeypatch, capsys, sha):
    rc, _, err, _ = _modo_security(ce, monkeypatch, capsys, head_sha=sha, files=["README.md"])
    assert rc == 1 and "ERROR" in err


def test_b2_el_modo_security_exige_head_sha(ce, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["change_evidence.py", "security", "--pr", "7"])
    with pytest.raises(SystemExit) as ei:
        ce.main()
    assert ei.value.code == 2 and "--head-sha" in capsys.readouterr().err


def test_b2_el_modo_security_pasa_head_sha_al_modo(ce, monkeypatch):
    visto = {}
    monkeypatch.setattr(ce, "mode_security", lambda a: visto.update(sha=a.head_sha, pr=a.pr) or 0)
    monkeypatch.setattr("sys.argv", ["change_evidence.py", "security", "--pr", "7", "--head-sha", EVENTO_SHA])
    with pytest.raises(SystemExit):
        ce.main()
    assert visto == {"sha": EVENTO_SHA, "pr": 7}


def test_b2_los_otros_modos_no_piden_head_sha(ce, monkeypatch):
    monkeypatch.setattr(ce, "mode_pr", lambda a: 0)
    monkeypatch.setattr("sys.argv", ["change_evidence.py", "pr", "--pr", "7"])
    with pytest.raises(SystemExit) as ei:
        ce.main()
    assert ei.value.code == 0


# --- T55 · N12: «no aplica» no vale en ninguna ruta de la lista salvo las de smc/ ---
LISTA_REAL = (RAIZ / LISTA_PATH).read_text(encoding="utf-8")
MOTIVO_15 = "Threat model: no aplica: " + "x" * 15


@pytest.mark.parametrize("ruta", [
    "osv-scanner.toml", "release-please-config.json", "scripts/vigilancia.py", "scripts/otro.py", "docs/threat-model/SMC-100.md",
    ".github/CODEOWNERS", ".github/pull_request_template.md", ".github/actions/x/action.yml", ".github/dependabot.yml",
])
def test_n12_no_aplica_no_vale_en_las_rutas_de_la_lista_fuera_de_smc(ce, monkeypatch, ruta):
    _, r = _gate(ce, monkeypatch, files=[ruta], lista=LISTA_REAL, body=TASK + "\n" + MOTIVO_15)
    assert r["required"] is True and any("no aplica" in p and "no vale" in p for p in r["problems"])
    assert r["threat_model"] is None


@pytest.mark.parametrize("ruta", ["smc/report_html.py", "smc/dashboard.py", "smc/visor.py", "smc/evidencias.py"])
def test_n12_en_las_rutas_de_smc_no_aplica_sigue_valiendo(ce, monkeypatch, ruta):
    _, r = _gate(ce, monkeypatch, files=[ruta], lista=LISTA_REAL, body=TASK + "\n" + MOTIVO_15)
    assert r["required"] is True and r["problems"] == [] and r["threat_model"] == "no aplica: " + "x" * 15


def test_n12_un_renombrado_desde_una_ruta_sensible_fuera_de_smc_tampoco_vale(ce, monkeypatch):
    f = {"filename": "smc/dashboard.py", "previous_filename": "osv-scanner.toml", "status": "renamed"}
    _, r = _gate(ce, monkeypatch, files=[f], lista=LISTA_REAL, body=TASK + "\n" + MOTIVO_15)
    assert r["problems"] and r["threat_model"] is None


def test_n12_una_ruta_de_smc_junto_a_una_de_scripts_no_vale(ce, monkeypatch):
    _, r = _gate(ce, monkeypatch, files=["smc/visor.py", "scripts/vigilancia.py"], lista=LISTA_REAL, body=TASK + "\n" + MOTIVO_15)
    assert r["problems"]


def test_n12_con_threat_model_las_rutas_de_la_lista_siguen_pasando(ce, monkeypatch):
    _, r = _gate(ce, monkeypatch, files=["osv-scanner.toml", MODELO_PATH], lista=LISTA_REAL, contents=_modelo())
    assert r["problems"] == [] and r["threat_model"] == MODELO_PATH


# --- T55 · el workflow: concurrency, rama por defecto y mismo SHA en el script y en el estado ---
def _c_concurrency():
    c = _gate_doc().get("concurrency") or _gate_job().get("concurrency")
    return (isinstance(c, dict) and c.get("cancel-in-progress") is True and "pull_request.number" in str(c.get("group"))
            and "security-gate" in str(c.get("group")))


def _c_cancel_in_progress_true():
    c = _gate_doc().get("concurrency") or {}
    return c.get("cancel-in-progress") is True


def _c_rama_por_defecto():
    cond = str(_gate_job().get("if", ""))
    return (_re.sub(r"\s+", "", cond).strip("${}") == "github.event.pull_request.base.ref==github.event.repository.default_branch")


def _c_mismo_sha():
    job = _gate_job()
    env = job.get("env") or {}
    pasos = job["steps"]
    script = next(s for s in pasos if "change_evidence.py security" in s.get("run", ""))
    estado = next(s for s in pasos if "statuses/" in s.get("run", ""))
    texto = _sin_comentarios(GATE_YML)
    return (str(env.get("HEAD_SHA")).replace(" ", "") == "${{github.event.pull_request.head.sha}}"
            and texto.count("pull_request.head.sha") == 1
            and '--head-sha "$HEAD_SHA"' in script["run"] and "repos/$REPO/statuses/$HEAD_SHA" in estado["run"]
            and not (script.get("env") or {}).get("HEAD_SHA") and not (estado.get("env") or {}).get("HEAD_SHA")
            and "github.sha" not in texto and "GITHUB_SHA" not in texto)


def _c_no_publica_si_se_cancela():
    estado = next(s for s in _gate_job()["steps"] if "statuses/" in s.get("run", ""))
    cond = _re.sub(r"\s+", "", str(estado.get("if")))
    return "!cancelled()" in cond


@pytest.mark.parametrize("comprobacion", [
    P(_c_concurrency, id="concurrency_por_numero_de_pr_con_cancel_in_progress_true"),
    P(_c_cancel_in_progress_true, id="cancel_in_progress_es_true"),
    P(_c_rama_por_defecto, id="solo_corre_si_la_base_es_la_rama_por_defecto"),
    P(_c_mismo_sha, id="el_sha_del_estado_es_el_que_recibe_el_script"),
    P(_c_no_publica_si_se_cancela, id="una_ejecucion_cancelada_no_publica_estado"),
])
def test_t55_workflow_security_gate(comprobacion):
    assert comprobacion()


# --- T56 · G3: el paso que publica el estado se ejecuta de verdad (el fragmento `run` sale del YAML) ---
SHA40 = "0123456789abcdef0123456789abcdef01234567"


def _paso_publica_estado():
    pasos = [s for s in _gate_job()["steps"] if s.get("name", "").startswith("Publicar el estado security-gate")]
    assert len(pasos) == 1
    return pasos[0]["run"]


def _publica(tmp_path, outcome, head_sha=SHA40):
    """Ejecuta el `run` del YAML con un `gh` falso al principio del PATH. Devuelve (código, argumentos de gh por llamada)."""
    import os
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    registro = tmp_path / "gh.log"
    gh = bin_dir / "gh"
    gh.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$GH_LOG"\n', encoding="utf-8")
    gh.chmod(0o755)
    script = tmp_path / "paso.sh"
    script.write_text(_paso_publica_estado(), encoding="utf-8")
    env = {"PATH": f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin", "GH_LOG": str(registro), "GH_TOKEN": "falso",
           "REPO": "o/r", "HEAD_SHA": head_sha, "OUTCOME": outcome}
    r = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, cwd=tmp_path)
    llamadas = registro.read_text(encoding="utf-8").splitlines() if registro.exists() else []
    return r.returncode, llamadas


def _estado_de(llamada):
    m = _re.search(r"-f state=(\S+)", llamada)
    return m.group(1) if m else None


@pytest.mark.parametrize("outcome,esperado", [
    ("success", "success"), ("failure", "failure"), ("cancelled", "failure"), ("skipped", "failure"),
    ("", "failure"), ("Success", "failure"), ("success ", "failure"),
])
def test_t56_el_paso_publica_success_solo_con_outcome_success(tmp_path, outcome, esperado):
    rc, llamadas = _publica(tmp_path, outcome)
    assert rc == 0 and len(llamadas) == 1
    assert _estado_de(llamadas[0]) == esperado
    assert f"repos/o/r/statuses/{SHA40}" in llamadas[0] and "context=security-gate" in llamadas[0]


@pytest.mark.parametrize("sha", ["", "abc", SHA40.upper(), SHA40 + "0", "x" * 40])
def test_t56_el_paso_no_publica_si_el_sha_no_es_legible(tmp_path, sha):
    rc, llamadas = _publica(tmp_path, "success", head_sha=sha)
    assert rc != 0 and llamadas == []


# --- T56 · M10: motivos de «no aplica» no válidos en un PR no sec que solo toca smc/ ---
LISTA_REAL = (RAIZ / ".github/security-paths.txt").read_text(encoding="utf-8")
PLANTILLA_PR = (RAIZ / ".github/pull_request_template.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("motivo", [".", "<motivo>", "x" * 14, "<a>" * 10, "..............."])
def test_t56_motivo_no_valido_en_pr_no_sec_solo_smc_da_problema(ce, monkeypatch, motivo):
    _, r = _gate(ce, monkeypatch, files=["smc/visor.py"], lista=LISTA_REAL, body=TASK + f"\nThreat model: no aplica: {motivo}")
    assert r["required"] is True and r["threat_model"] is None
    assert any("motivo no válido" in p for p in r["problems"])


def test_t56_plantilla_del_pr_sin_rellenar_solo_smc_da_problema(ce, monkeypatch):
    _, r = _gate(ce, monkeypatch, files=["smc/visor.py"], lista=LISTA_REAL, body=PLANTILLA_PR + "\nTask: SMC-777\n")
    assert r["required"] is True and r["problems"] and r["threat_model"] is None


def test_t56_plantilla_con_la_linea_no_aplica_sin_rellenar_da_motivo_no_valido(ce, monkeypatch):
    cuerpo = PLANTILLA_PR.replace("- [ ] Threat model:", "- [ ] Threat model: no aplica: <motivo>") + "\nTask: SMC-777\n"
    _, r = _gate(ce, monkeypatch, files=["smc/visor.py"], lista=LISTA_REAL, body=cuerpo)
    assert any("motivo no válido" in p for p in r["problems"]) and r["threat_model"] is None


def test_t56_motivo_valido_en_pr_no_sec_solo_smc_pasa(ce, monkeypatch):
    _, r = _gate(ce, monkeypatch, files=["smc/visor.py"], lista=LISTA_REAL, body=TASK + "\nThreat model: no aplica: solo cambia un texto del visor")
    assert r["required"] is True and r["problems"] == [] and r["threat_model"] == "no aplica: solo cambia un texto del visor"


# --- T56 · usabilidad: la casilla de lista de la plantilla del PR ---
@pytest.mark.parametrize("prefijo", ["- [ ] ", "- [x] ", "- [X] ", "* [ ] ", "  - [ ] "])
def test_t56_la_casilla_de_lista_vale_para_no_aplica(ce, monkeypatch, prefijo):
    _, r = _gate(ce, monkeypatch, files=["smc/visor.py"], lista=LISTA_REAL,
                 body=TASK + f"\n{prefijo}Threat model: no aplica: solo cambia un texto del visor")
    assert r["problems"] == [] and r["threat_model"] == "no aplica: solo cambia un texto del visor"


@pytest.mark.parametrize("cuerpo", [
    "<!--\n- [ ] Threat model: no aplica: solo cambia un texto del visor\n-->",
    "<!-- - [x] Threat model: no aplica: solo cambia un texto del visor -->",
    "<!-- a --><!-- - [ ] Threat model: no aplica: solo cambia un texto del visor",
    "<!-- - [ ] Threat model: no aplica: solo cambia un texto del visor -->",
])
def test_t56_la_casilla_dentro_de_un_comentario_html_no_vale(ce, monkeypatch, cuerpo):
    _, r = _gate(ce, monkeypatch, files=["smc/visor.py"], lista=LISTA_REAL, body=TASK + "\n" + cuerpo)
    assert r["problems"] and r["threat_model"] is None


@pytest.mark.parametrize("linea", ["- [] Threat model: no aplica: solo cambia un texto del visor",
                                   "- [ ]Threat model: no aplica: solo cambia un texto del visor",
                                   "- Threat model: no aplica: solo cambia un texto del visor",
                                   "texto - [ ] Threat model: no aplica: solo cambia un texto del visor"])
def test_t56_otras_formas_de_casilla_no_valen(ce, monkeypatch, linea):
    _, r = _gate(ce, monkeypatch, files=["smc/visor.py"], lista=LISTA_REAL, body=TASK + "\n" + linea)
    assert r["problems"] and r["threat_model"] is None


# --- T56: los tests que cita el threat model de SMC-009 existen ---
def test_t56_los_tests_citados_en_el_threat_model_de_smc_009_existen():
    texto = (RAIZ / "docs/threat-model/SMC-009.md").read_text(encoding="utf-8")
    citados = set(_re.findall(r"`(tests/[\w./-]+\.py)::(\w+)", texto))
    assert citados
    for fichero, nombre in citados:
        assert _re.search(rf"^\s*def {nombre}\b", (RAIZ / fichero).read_text(encoding="utf-8"), _re.M), f"{fichero}::{nombre}"


# --- T57 · SMC-011: las rutas que admiten «no aplica» se marcan con `~` en la lista ---
MOTIVO_OK = "Threat model: no aplica: solo cambia un texto del visor"


def _t57(ce, monkeypatch, lista, files, body=None, **kw):
    return _gate(ce, monkeypatch, files=files, lista=lista, body=TASK + "\n" + (MOTIVO_OK if body is None else body), **kw)[1]


def test_t57_el_script_no_nombra_a_smc_ni_guarda_el_prefijo(ce):
    texto = SCRIPT.read_text(encoding="utf-8")
    assert "smc/" not in texto and not hasattr(ce, "NO_APLICA_PREFIX")


def test_t57_una_ruta_marcada_admite_no_aplica(ce, monkeypatch):
    r = _t57(ce, monkeypatch, "~app/*\nscripts/*\n", ["app/x.py"])
    assert r["required"] is True and r["problems"] == [] and r["threat_model"] == "no aplica: solo cambia un texto del visor"


def test_t57_una_ruta_marcada_sigue_siendo_sensible(ce, monkeypatch):
    r = _t57(ce, monkeypatch, "~app/*\n", ["app/x.py"], body=TASK)
    assert r["required"] is True and r["problems"]


@pytest.mark.parametrize("lista", ["app/*\nscripts/*\n", "# ~app/*\napp/*\n", "app/*  # ~app/*\n"])
def test_t57_lista_sin_ruta_marcada_no_admite_no_aplica(ce, monkeypatch, lista):
    r = _t57(ce, monkeypatch, lista, ["app/x.py"])
    assert r["required"] is True and r["threat_model"] is None and any("no vale" in p for p in r["problems"])


def test_t57_una_ruta_marcada_y_otra_sin_marcar_no_valen(ce, monkeypatch):
    r = _t57(ce, monkeypatch, "~app/*\nlib/*\n", ["app/x.py", "lib/y.py"])
    assert r["threat_model"] is None and any("no vale" in p for p in r["problems"])


def test_t57_una_ruta_que_casa_con_una_marcada_y_otra_sin_marcar_no_vale(ce, monkeypatch):
    r = _t57(ce, monkeypatch, "~app/*\napp/secreto.py\n", ["app/secreto.py"])
    assert r["threat_model"] is None and r["problems"]


def test_t57_el_origen_de_un_renombrado_tambien_cuenta(ce, monkeypatch):
    f = {"filename": "app/x.py", "previous_filename": "lib/y.py", "status": "renamed"}
    r = _t57(ce, monkeypatch, "~app/*\nlib/*\n", [f])
    assert r["threat_model"] is None and r["problems"]


def test_t57_en_un_pr_sec_no_aplica_no_vale_aunque_todo_este_marcado(ce, monkeypatch):
    r = _t57(ce, monkeypatch, "~app/*\n", ["app/x.py"], title="sec: cierra algo")
    assert r["threat_model"] is None and any("no vale" in p for p in r["problems"])


def test_t57_tocar_la_lista_sigue_siendo_estricto_aunque_este_marcada(ce, monkeypatch):
    r = _t57(ce, monkeypatch, "~.github/*\n~app/*\n", [LISTA_PATH, "app/x.py"])
    assert r["threat_model"] is None and any("no vale" in p for p in r["problems"])


def test_t57_marcar_una_ruta_en_la_cabeza_no_libra_la_marca_se_lee_de_la_base(ce, monkeypatch):
    r = _t57(ce, monkeypatch, "app/*\n", ["app/x.py"], contents={("H", LISTA_PATH): "~app/*\n"})
    assert r["threat_model"] is None and any("no vale" in p for p in r["problems"])


def test_t57_marcar_una_ruta_sensible_para_librarse_del_modelo_exige_modelo(ce, monkeypatch):
    # el PR marca scripts/* con ~ en la cabeza (la base no tiene marcas) y toca la lista: la puerta es estricta
    r = _t57(ce, monkeypatch, "scripts/*\n", [LISTA_PATH, "scripts/x.py"], contents={("H", LISTA_PATH): "~scripts/*\n"})
    assert r["required"] is True and r["threat_model"] is None and any("no vale" in p for p in r["problems"])


@pytest.mark.parametrize("linea", ["~ app/*", "~~app/*", "~\tapp/*", "~ ~app/*", "~\xa0app/*", "~\u3000app/*", "~\u2003~\xa0app/*"])
def test_t57_una_marca_mal_escrita_no_marca_y_la_ruta_sigue_siendo_sensible(ce, monkeypatch, linea):
    r = _t57(ce, monkeypatch, linea + "\n", ["app/x.py"])
    assert r["required"] is True and r["threat_model"] is None and any("no vale" in p for p in r["problems"])


def test_t57_parse_security_rules(ce):
    texto = "# cab\n~app/*\n  ~ lib/*  # x\n~~dos/*\nplana/*\n~\n~   \n~doc/a.md # c\n"
    assert ce.parse_security_rules(texto) == [("app/*", True), ("lib/*", False), ("dos/*", False), ("plana/*", False), ("doc/a.md", True)]


def test_t57_parse_security_paths_quita_la_marca_y_no_la_trata_como_glob(ce):
    assert ce.parse_security_paths("~app/*\nlib/*\n~ x/*\n") == ["app/*", "lib/*", "x/*"]
    import fnmatch
    assert fnmatch.fnmatchcase("app/x.py", ce.parse_security_paths("~app/*")[0])


def test_t57_la_lista_real_marca_solo_las_cuatro_rutas_de_smc(ce):
    reglas = ce.parse_security_rules(LISTA_REAL)
    assert sorted(g for g, m in reglas if m) == ["smc/dashboard.py", "smc/evidencias.py", "smc/report_html.py", "smc/visor.py"]
    assert all(m or not g.startswith("smc/") for g, m in reglas)


@pytest.mark.parametrize("ruta", ["smc/report_html.py", "smc/dashboard.py", "smc/visor.py", "smc/evidencias.py"])
def test_t57_en_smc_el_comportamiento_no_cambia_con_la_lista_real(ce, monkeypatch, ruta):
    r = _t57(ce, monkeypatch, LISTA_REAL, [ruta])
    assert r["problems"] == [] and r["threat_model"] == "no aplica: solo cambia un texto del visor"


def test_t57_la_lista_real_sigue_exigiendo_modelo_fuera_de_smc(ce, monkeypatch):
    r = _t57(ce, monkeypatch, LISTA_REAL, ["smc/visor.py", "osv-scanner.toml"])
    assert r["threat_model"] is None and r["problems"]


def test_t57_la_lista_y_la_plantilla_describen_la_marca_sin_nombrar_smc():
    lista = [ln for ln in LISTA_REAL.splitlines() if ln.lstrip().startswith("#")]
    plantilla = (RAIZ / ".github/pull_request_template.md").read_text(encoding="utf-8")
    assert not any("smc/" in ln for ln in lista) and "smc/" not in plantilla
    assert any("~" in ln for ln in lista) and "~" in plantilla


def test_t57_el_threat_model_de_smc_011_pasa_la_puerta_y_sus_tests_existen(ce):
    texto = (RAIZ / "docs/threat-model/SMC-011.md").read_text(encoding="utf-8")
    assert ce.threat_model_problems(texto, [33]) == []
    citados = set(_re.findall(r"`(tests/[\w./-]+\.py)::(\w+)", texto))
    assert citados
    for fichero, nombre in citados:
        assert _re.search(rf"^\s*def {nombre}\b", (RAIZ / fichero).read_text(encoding="utf-8"), _re.M), f"{fichero}::{nombre}"


# --- T58 · SMC-011: cierre de los no bloqueantes de la auditoría ---
@pytest.mark.parametrize("linea", ["~\xa0app/*", "~\u3000app/*", "~\u2003\xa0~app/*", "~ ~\xa0app/*"])
def test_t58_espacios_unicode_tras_la_marca_se_quitan_y_la_ruta_queda_sensible_sin_marca(ce, linea):
    assert ce.parse_security_rules(linea + "\n") == [("app/*", False)]


@pytest.mark.parametrize("linea", ["\uff5eapp/*", "\u02dcapp/*"])
def test_t58_otros_signos_parecidos_a_la_marca_no_marcan_y_se_avisan(ce, monkeypatch, linea):
    assert ce.parse_security_rules(linea + "\n") == [(linea, False)]
    r = _t57(ce, monkeypatch, linea + "\nscripts/*\n", ["scripts/x.py"], body=TASK)
    assert any("no ASCII" in w for w in r["warnings"])


@pytest.mark.parametrize("linea,fragmento", [
    ("~./app/*", "./"), ("./app/*", "./"), ("~app/* ~lib/*", "espacio"), ("app/* lib/*", "espacio"), ("\u00e9/*", "no ASCII"),
    ("~\u00e9/*", "no ASCII"),
])
def test_t58_globs_sospechosos_dan_aviso_sin_cambiar_la_decision(ce, monkeypatch, linea, fragmento):
    con = _t57(ce, monkeypatch, linea + "\nscripts/*\n", ["scripts/x.py", "app/x.py"], body=TASK)
    sin = _t57(ce, monkeypatch, "scripts/*\n", ["scripts/x.py", "app/x.py"], body=TASK)
    assert any(fragmento in w and "security-paths" in w for w in con["warnings"])
    assert (con["required"], con["problems"], con["threat_model"]) == (sin["required"], sin["problems"], sin["threat_model"])


@pytest.mark.parametrize("lista", ["~app/*\nscripts/*\n.github/*\n", LISTA_REAL, "~*\n"])
def test_t58_una_lista_bien_escrita_no_da_avisos(ce, monkeypatch, lista):
    assert _t57(ce, monkeypatch, lista, ["app/x.py"], body=TASK)["warnings"] == []


def test_t58_el_aviso_sale_por_la_salida_de_la_puerta(ce, monkeypatch, capsys):
    rc, out, err, _ = _modo_security(ce, monkeypatch, capsys, files=["app/x.py"], lista="\uff5eapp/*\napp/*\n", body=TASK)
    assert "AVISO" in err and "no ASCII" in err


def test_t58_con_la_base_marcada_scripts_change_evidence_exige_modelo(ce, monkeypatch):
    r = _t57(ce, monkeypatch, "~scripts/*\n", ["scripts/change_evidence.py"])
    assert r["required"] is True and r["threat_model"] is None and any("no vale" in p for p in r["problems"])


def test_t58_con_la_base_marcada_scripts_otro_fichero_si_admite_no_aplica(ce, monkeypatch):
    r = _t57(ce, monkeypatch, "~scripts/*\n", ["scripts/otro.py"])
    assert r["problems"] == [] and r["threat_model"] is not None


@pytest.mark.parametrize("ruta", [".github/workflows/ci.yml", ".github/workflows/security-gate.yml"])
def test_t58_con_la_base_marcada_github_un_workflow_exige_modelo(ce, monkeypatch, ruta):
    r = _t57(ce, monkeypatch, "~.github/*\n", [ruta])
    assert r["required"] is True and r["threat_model"] is None and any("no vale" in p for p in r["problems"])


def test_t58_con_la_base_marcada_github_otro_fichero_si_admite_no_aplica(ce, monkeypatch):
    r = _t57(ce, monkeypatch, "~.github/*\n", [".github/CODEOWNERS"])
    assert r["problems"] == [] and r["threat_model"] is not None
