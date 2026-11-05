#!/usr/bin/env python3
"""change_evidence.py — PLAYBOOK-F2P-001 · capacidad change_evidence (registro v2)

Genera registros de cambio verificables a partir de GitHub + git.
Solo usa la librería estándar y la CLI `gh` (preinstalada en los runners de GitHub).

Modos:
  pr       Comprueba la trazabilidad de un PR y escribe change-record.{json,md}.
           Falla (exit 1) si el PR no enlaza una issue ("Closes #N") o no declara TASK_ID.
  release  Junta todos los PRs entre el tag anterior y el tag dado y escribe el evidence pack.

Uso:
  python3 scripts/change_evidence.py pr --pr 123 --out change-record
  python3 scripts/change_evidence.py release --tag v2.3.0 --out evidence/v2.3.0
  python3 scripts/change_evidence.py release --tag v2.3.0 --out /tmp/ev --offline   # solo git, sin API

Excepción: el PR de release recibe TASK_ID "MAINT": rama release-please--branches--* del propio
repo que SOLO toca ficheros de versión. El nombre de rama no basta: cualquiera con push puede
elegirlo. Es solo una excepción de trazabilidad: blind-review se exige igual, y su falta es un hueco.

Revisión: sin aprobación de GitHub. Vale el estado `blind-review` sobre el SHA de cabeza del PR.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

TASK_RE = re.compile(r"^\s*Task:\s*([A-Z][A-Z0-9]{1,9}-\d{1,5})\s*$", re.MULTILINE)
CLOSES_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)\b", re.IGNORECASE)
# Un comentario sin cerrar se ignora hasta el final del texto, por prudencia.
HTML_COMMENT_RE = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)
PR_IN_SUBJECT_RE = re.compile(r"\(#(\d+)\)\s*$")
BLIND_REVIEW_CONTEXT = "blind-review"
RELEASE_BRANCH_PREFIX = "release-please--branches--"
RELEASE_FILES = {"CHANGELOG.md", ".release-please-manifest.json", "pyproject.toml", "uv.lock",
                 "package.json", "package-lock.json", "version.txt"}
FIRST_RELEASE_LIMIT = 50
FILES_PAGE = 100  # un PR de release toca pocos ficheros: llenar la página ya lo descarta
REVIEW_MODEL = (
    "Revisión ciega por agente de IA (estado blind-review sobre el SHA de cabeza) "
    "más gate humano en el merge del PR de release. Sin aprobación humana por PR."
)
CONTROLS = {
    "ENS": ["op.exp.5", "mp.sw.1", "mp.sw.2"],
    "ISO27001": ["A.8.25", "A.8.29", "A.8.32"],
    "NIS2": ["art. 21.2.e"],
    "DORA": ["art. 9.4.e"],
    "_nota": "Mapeo orientativo. Validar con el auditor antes de presentarlo como evidencia formal.",
}


# ───────────── utilidades ─────────────
def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


# `gh` escribe dos formas en stderr: «gh: <mensaje> (HTTP 503)» si el cuerpo es JSON con `message`, y
# «gh: HTTP 503» (sin paréntesis, línea propia) si es HTML, vacío o JSON sin `message`.
HTTP_STATUS_RE = re.compile(r"\(HTTP (\d{3})\)|^gh: HTTP (\d{3})[ \t]*$", re.MULTILINE)
# Con cuerpo vacío y `Content-Type: application/json`, `gh` escribe solo esta línea, sin código de estado.
EMPTY_BODY_LINE = "unexpected end of JSON input"
RETRIES = 2  # reintentos tras el primer intento: 3 llamadas como máximo
RETRY_DELAY = 1.0  # segundos; se multiplica por el número de reintento


def http_status(e: subprocess.CalledProcessError) -> int | None:
    """Código de estado que `gh` escribe en stderr: `gh: <mensaje> (HTTP <código>)` o `gh: HTTP <código>`.

    Cuenta la última aparición. Sin código reconocible devuelve None.

    No se busca un número suelto: un 403 puede citar «HTTP 500» en su mensaje.
    """
    found = [m.group(1) or m.group(2) for m in HTTP_STATUS_RE.finditer(e.stderr or "")]
    return int(found[-1]) if found else None


def is_transient(e: subprocess.CalledProcessError) -> bool:
    """5xx con código en stderr, o, sin código, una línea que es exactamente el aviso de cuerpo vacío.

    Sin código no se distingue un 5xx de otro estado (un 403 con cuerpo vacío también se reintenta; es un GET).
    Con código manda el código: un 403 que cita el texto en su mensaje no se reintenta.
    """
    status = http_status(e)
    if status is not None:
        return 500 <= status <= 599
    return EMPTY_BODY_LINE in (e.stderr or "").splitlines()


def gh_json(path: str) -> object:
    cmd = ["gh", "api", "-H", "Accept: application/vnd.github+json", path]
    for attempt in range(RETRIES + 1):
        try:
            return json.loads(run(cmd))
        except subprocess.CalledProcessError as e:
            if attempt == RETRIES or not is_transient(e):
                raise
            time.sleep(RETRY_DELAY * (attempt + 1))
    raise AssertionError("inalcanzable")


class PagesLimitError(RuntimeError):
    """Se alcanzó MAX_PAGES sin página corta: la lectura quedó incompleta (se trata como hueco)."""


def reason(e: Exception) -> str:
    """Motivo legible de un fallo de lectura; no depende de que el error traiga stderr."""
    if isinstance(e, subprocess.CalledProcessError):
        return (e.stderr or "").strip() or str(e)
    return str(e)


READ_ERRORS = (subprocess.CalledProcessError, PagesLimitError)

PER_PAGE = 100
MAX_PAGES = 50  # tope de seguridad: si se alcanza, error (hueco) en vez de cortar en silencio


def gh_pages(path: str, key: str | None = None) -> list:
    """Lee todas las páginas de una lista de la API pidiendo page=N una a una.

    No usa `gh api --paginate`: sin `--slurp` concatena las páginas una tras otra
    (`[..][..]` o `{..}{..}`), que no es JSON válido, y con `--slurp` devuelve una
    lista de páginas cuya forma depende de si la respuesta es lista u objeto.
    `key` nombra la lista dentro de una respuesta objeto (p. ej. `check_runs`).
    Termina con la primera página corta; cualquier error de una página se propaga.
    """
    sep = "&" if "?" in path else "?"
    items: list = []
    for page in range(1, MAX_PAGES + 1):
        data = gh_json(f"{path}{sep}per_page={PER_PAGE}&page={page}")
        chunk = data[key] if key else data
        items.extend(chunk)
        if len(chunk) < PER_PAGE:
            return items
    raise PagesLimitError(f"{path}: más de {MAX_PAGES} páginas de {PER_PAGE}; lectura incompleta")


def latest_status(statuses: list[dict], context: str) -> dict | None:
    """Estado más reciente de un contexto (por created_at e id; no se fía del orden de la lista)."""
    mine = [s for s in statuses if s.get("context") == context]
    return max(mine, key=lambda s: (s.get("created_at") or "", s.get("id") or 0), default=None)


def latest_check_runs(runs: list[dict]) -> list[dict]:
    """Un check-run por (nombre, app): el más reciente; no se fía del orden de la lista.

    Por grupo: entre los runs con started_at gana el mayor (started_at, id). Un run sin started_at
    solo lo sustituye si su id supera al de todos los runs con fecha del grupo (el mayor de ellos
    si son varios). Sin ningún run con fecha gana el mayor id. Un run sin fecha ajeno al par no
    cambia la elección entre los fechados.
    """
    groups: dict[tuple, list[dict]] = {}
    for r in runs:
        groups.setdefault((r["name"], (r.get("app") or {}).get("id")), []).append(r)
    best = []
    for group in groups.values():
        dated = [r for r in group if r.get("started_at")]
        undated = [r for r in group if not r.get("started_at")]
        winner = max(dated, key=lambda r: (r["started_at"], r.get("id") or 0)) if dated else None
        newest_undated = max(undated, key=lambda r: r.get("id") or 0) if undated else None
        if winner is None:
            winner = newest_undated
        elif newest_undated is not None and (newest_undated.get("id") or 0) > max(r.get("id") or 0 for r in dated):
            winner = newest_undated
        best.append(winner)
    return best


def _utc(ts: str) -> dt.datetime | None:
    try:
        d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def cut_at_merge(runs: list[dict], merged_at: str) -> list[dict]:
    """Descarta los check-runs iniciados después de merged_at (igual o sin started_at se quedan)."""
    cut = _utc(merged_at)
    if cut is None:
        return runs
    kept = []
    for r in runs:
        started = _utc(r["started_at"]) if r.get("started_at") else None
        if started is None or started <= cut:
            kept.append(r)
    return kept


def repo_slug() -> str:
    slug = os.environ.get("GITHUB_REPOSITORY")
    if slug:
        return slug
    return run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def extract_tasks(*texts: str) -> list[str]:
    found: list[str] = []
    for t in texts:
        for m in TASK_RE.findall(HTML_COMMENT_RE.sub("", t or "")):
            if m not in found:
                found.append(m)
    return found


def extract_issues(text: str) -> list[int]:
    return sorted({int(n) for n in CLOSES_RE.findall(HTML_COMMENT_RE.sub("", text or ""))})


def allowed_release_files(repo: str, base_ref: str) -> set[str]:
    """Ficheros de versión: los fijos más los extra-files de la rama BASE, nunca los del propio PR."""
    allowed = set(RELEASE_FILES)
    try:
        meta = gh_json(f"repos/{repo}/contents/release-please-config.json?ref={base_ref}")
    except subprocess.CalledProcessError as e:
        if "HTTP 404" in (e.stderr or ""):  # rama base sin configuración: solo los ficheros fijos
            return allowed
        raise
    config = json.loads(base64.b64decode(meta["content"]))
    for pkg in (config.get("packages") or {}).values():
        for extra in pkg.get("extra-files") or []:
            allowed.add(extra["path"] if isinstance(extra, dict) else extra)
    return allowed


def is_release_pr(repo: str, number: int, head_ref: str, base_ref: str, same_repo: bool) -> bool:
    if not (same_repo and head_ref.startswith(RELEASE_BRANCH_PREFIX)):
        return False
    files = gh_json(f"repos/{repo}/pulls/{number}/files?per_page={FILES_PAGE}")
    if len(files) >= FILES_PAGE:  # puede haber más páginas sin leer
        return False
    allowed = allowed_release_files(repo, base_ref)
    return bool(files) and all(f["filename"] in allowed for f in files)


# ───────────── recogida de datos ─────────────
def collect_pr(repo: str, number: int) -> dict:
    pr = gh_json(f"repos/{repo}/pulls/{number}")
    commits = gh_pages(f"repos/{repo}/pulls/{number}/commits")
    reviews = gh_pages(f"repos/{repo}/pulls/{number}/reviews")
    head_sha = pr["head"]["sha"]
    gaps: list[str] = []
    try:
        checks = gh_pages(f"repos/{repo}/commits/{head_sha}/check-runs", "check_runs")
    except READ_ERRORS as e:
        checks = []
        gaps.append(f"PR #{number}: no se pudieron leer los checks ({reason(e)})")
    if pr.get("merged_at"):
        kept = cut_at_merge(checks, pr["merged_at"])
        kept_keys = {(r["name"], (r.get("app") or {}).get("id")) for r in kept}
        lost = sorted({r["name"] for r in checks if (r["name"], (r.get("app") or {}).get("id")) not in kept_keys})
        for name in lost:
            gaps.append(f"PR #{number}: el check {name} no tenía ningún run al fusionar (merged_at {pr['merged_at']})")
        checks = kept
    try:
        statuses = gh_pages(f"repos/{repo}/commits/{head_sha}/statuses")
    except READ_ERRORS as e:
        statuses = []
        gaps.append(f"PR #{number}: no se pudo leer el estado blind-review ({reason(e)})")
    blind = latest_status(statuses, BLIND_REVIEW_CONTEXT)

    author = pr["user"]["login"]
    head_repo = (pr["head"].get("repo") or {}).get("full_name")
    try:
        maint = is_release_pr(repo, number, pr["head"].get("ref") or "", pr["base"]["ref"], head_repo == repo)
    except subprocess.CalledProcessError as e:
        maint = False
        gaps.append(f"PR #{number}: no se pudo comprobar si es PR de release ({(e.stderr or '').strip() or e})")
    body = pr.get("body") or ""
    total = pr.get("commits")
    if isinstance(total, int) and total > len(commits):  # la API corta en 250 sin error
        gaps.append(f"PR #{number}: commits truncados por la API (leídos {len(commits)} de {total} totales)")
    messages = [c["commit"]["message"] for c in commits]
    tasks = extract_tasks(body, *messages) or (["MAINT"] if maint else [])
    approvals = sorted({r["user"]["login"] for r in reviews if r.get("state") == "APPROVED"})

    return {
        "pr": number,
        "title": pr["title"],
        "url": pr["html_url"],
        "author": author,
        "maint": maint,
        "tasks": tasks,
        "issues": extract_issues(body),
        "approved_by": approvals,
        "blind_review": (
            {"state": blind.get("state"), "description": blind.get("description"), "url": blind.get("target_url")}
            if blind else None
        ),
        "gaps": gaps,
        "merged": bool(pr.get("merged_at")),
        "merged_at": pr.get("merged_at"),
        "merged_by": (pr.get("merged_by") or {}).get("login"),
        "base": pr["base"]["ref"],
        "head_sha": head_sha,
        "merge_sha": pr.get("merge_commit_sha"),
        "commits": [c["sha"] for c in commits],
        "checks": sorted(
            ({"name": c["name"], "conclusion": c.get("conclusion") or c.get("status")} for c in latest_check_runs(checks)),
            key=lambda c: c["name"],
        ),
    }


def previous_tag(tag: str) -> str | None:
    try:
        return run(["git", "describe", "--tags", "--abbrev=0", f"{tag}^"])
    except subprocess.CalledProcessError:
        return None


def blind_review_label(p: dict) -> str:
    b = p.get("blind_review")
    return b["state"] if b else "—"


def git_range_commits(rng: str) -> list[dict]:
    sep, end = "\x1f", "\x1e"
    out = run(["git", "log", "--format=%H" + sep + "%s" + sep + "%an" + sep + "%B" + end, rng])
    commits = []
    for chunk in out.split(end):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        sha, subject, author, body = (chunk.split(sep) + ["", "", "", ""])[:4]
        commits.append({"sha": sha, "subject": subject, "author": author, "tasks": extract_tasks(body)})
    return commits


# ───────────── salida ─────────────
def write_outputs(out: Path, record: dict, md: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "change-record.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "change-record.md").write_text(md, encoding="utf-8")
    print(f"Escrito: {out / 'change-record.json'} · {out / 'change-record.md'}")


def pr_markdown(p: dict) -> str:
    checks = "\n".join(f"| {c['name']} | {c['conclusion']} |" for c in p["checks"]) or "| — | — |"
    return (
        f"# Registro de cambio — PR #{p['pr']}\n\n"
        f"- **Título:** {p['title']}\n- **URL:** {p['url']}\n"
        f"- **TASK_ID:** {', '.join(p['tasks']) or '—'}\n"
        f"- **Issues:** {', '.join('#' + str(i) for i in p['issues']) or '—'}\n"
        f"- **Autor:** {p['author']} · **Aprobado por:** {', '.join(p['approved_by']) or '—'}\n"
        f"- **Revisión ciega:** {blind_review_label(p)}\n"
        f"- **Merge:** {p['merged_at'] or 'pendiente'} por {p['merged_by'] or '—'} → `{p['base']}`\n"
        f"- **Head SHA:** `{p['head_sha']}`\n\n"
        f"| Check | Resultado |\n|---|---|\n{checks}\n"
        + ("\n## Huecos\n\n" + "\n".join(f"- {g}" for g in p["gaps"]) + "\n" if p["gaps"] else "")
    )


def release_markdown(r: dict) -> str:
    rows = []
    for p in r["changes"]:
        if "pr" in p:
            rows.append(
                f"| [#{p['pr']}]({p['url']}) | {p['title']} | {', '.join(p['tasks']) or '⚠ —'} | "
                f"{p['author']} | {blind_review_label(p)} | {', '.join(p['approved_by']) or '—'} | {p['ci_status']} |"
            )
        else:
            rows.append(f"| `{p['sha'][:8]}` | {p['subject']} | {', '.join(p['tasks']) or '⚠ —'} | {p['author']} | — | — | — |")
    gaps = "\n".join(f"- {g}" for g in r["gaps"]) or "- Ninguno"
    ctrl = "\n".join(f"- **{k}:** {', '.join(v)}" for k, v in r["controls"].items() if not k.startswith("_"))
    return (
        f"# Evidence pack — {r['tag']}\n\n"
        f"- **Repositorio:** {r['repo']}\n- **Rango:** `{r['range']}`\n- **Generado:** {r['generated_at']}\n"
        f"- **Cambios:** {len(r['changes'])}\n- **Modelo de revisión:** {r['review_model']}\n\n"
        f"| Cambio | Título | TASK_ID | Autor | Revisión ciega | Aprobado por | CI |\n|---|---|---|---|---|---|---|\n"
        + "\n".join(rows)
        + f"\n\n## Huecos de trazabilidad\n\n{gaps}\n\n## Controles relacionados\n\n{ctrl}\n\n> {r['controls']['_nota']}\n"
        f"\n## Verificación de la firma del SBOM\n\n```bash\ncosign verify-blob \\\n"
        f"  --bundle sbom.cdx.json.bundle \\\n"
        f"  --certificate-identity-regexp '^https://github.com/{r['repo']}/.github/workflows/release.yml@refs/heads/(main|master)$' \\\n"
        f"  --certificate-oidc-issuer https://token.actions.githubusercontent.com \\\n"
        f"  sbom.cdx.json\n```\n"
    )


# ───────────── modos ─────────────
def mode_pr(args: argparse.Namespace) -> int:
    repo = repo_slug()
    p = collect_pr(repo, args.pr)
    record = {"type": "pr", "repo": repo, "generated_at": now_iso(), "review_model": REVIEW_MODEL, "controls": CONTROLS, **p}
    write_outputs(Path(args.out), record, pr_markdown(p))

    errors = []
    if not p["tasks"]:
        errors.append("Falta TASK_ID: añade una línea 'Task: <PROJ>-<NNN>' en la descripción del PR o en un commit.")
    if not p["issues"] and not p["maint"]:
        errors.append("Falta issue enlazada: añade 'Closes #<n>' en la descripción del PR.")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    for g in p["gaps"]:
        print(f"AVISO: {g}", file=sys.stderr)
    return 1 if errors else 0


def mode_release(args: argparse.Namespace) -> int:
    prev = previous_tag(args.tag)
    rng = f"{prev}..{args.tag}" if prev else args.tag
    commits = git_range_commits(rng)
    first_release_gap = None
    if not prev and len(commits) > FIRST_RELEASE_LIMIT:
        first_release_gap = f"Primera release: revisados solo los últimos {FIRST_RELEASE_LIMIT} de {len(commits)} commits"
        commits = commits[:FIRST_RELEASE_LIMIT]
    repo = "local" if args.offline else repo_slug()

    changes, gaps, seen = [], [first_release_gap] if first_release_gap else [], set()
    for c in commits:
        m = PR_IN_SUBJECT_RE.search(c["subject"])
        if m and not args.offline:
            n = int(m.group(1))
            if n in seen:
                continue
            seen.add(n)
            try:
                p = collect_pr(repo, n)
            except READ_ERRORS as e:
                # La release ya existe: un fallo aquí no puede dejarla sin SBOM ni evidencias.
                changes.append(c)
                gaps.append(f"PR #{n} no se pudo leer ({reason(e)})")
                continue
            failed = [ch["name"] for ch in p["checks"] if ch["conclusion"] not in ("success", "skipped", "neutral")]
            p["ci_status"] = "✅" if not failed else "❌ " + ", ".join(failed)
            changes.append(p)
            if not p["tasks"]:
                gaps.append(f"PR #{n} sin TASK_ID")
            gaps.extend(p["gaps"])
            if blind_review_label(p) != "success":
                gaps.append(f"PR #{n} sin revisión ciega correcta (estado: {blind_review_label(p)})")
            if failed:
                gaps.append(f"PR #{n} con checks no exitosos: {', '.join(failed)}")
        else:
            changes.append(c)
            if not c["tasks"]:
                gaps.append(f"Commit {c['sha'][:8]} directo (sin PR) y sin TASK_ID")

    record = {
        "type": "release", "repo": repo, "tag": args.tag, "previous_tag": prev, "range": rng,
        "generated_at": now_iso(), "review_model": REVIEW_MODEL, "controls": CONTROLS, "changes": changes, "gaps": gaps,
    }
    write_outputs(Path(args.out), record, release_markdown(record))
    if gaps:
        print("AVISO: huecos de trazabilidad:\n  - " + "\n  - ".join(gaps), file=sys.stderr)
    # La release ya existe: los huecos se documentan, no bloquean (bloquean en el PR).
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    a = sub.add_parser("pr")
    a.add_argument("--pr", type=int, required=True)
    a.add_argument("--out", default="change-record")
    b = sub.add_parser("release")
    b.add_argument("--tag", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--offline", action="store_true", help="solo git, sin llamadas a la API")
    args = ap.parse_args()
    sys.exit(mode_pr(args) if args.mode == "pr" else mode_release(args))


if __name__ == "__main__":
    main()
