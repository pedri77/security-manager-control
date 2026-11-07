#!/usr/bin/env python3
"""change_evidence.py — PLAYBOOK-F2P-001 · capacidad change_evidence (registro v2)

Genera registros de cambio verificables a partir de GitHub + git.
Solo usa la librería estándar y la CLI `gh` (preinstalada en los runners de GitHub).

Modos:
  pr       Comprueba la trazabilidad de un PR y escribe change-record.{json,md}.
           Falla (exit 1) si el PR no enlaza una issue ("Closes #N") o no declara TASK_ID.
  release  Junta todos los PRs entre el tag anterior y el tag dado y escribe el evidence pack.
  security Puerta de seguridad de un PR (sin escribir ficheros). Aplica si el título es de tipo `sec` o si el PR toca
           una ruta de `.github/security-paths.txt` (leída de la rama BASE) o esa lista. Si aplica, exige
           `docs/threat-model/<TASK_ID>.md` en la cabeza, sin filas `abierta` ni placeholders, o una línea
           `Threat model: no aplica: <motivo>` en la descripción (motivo de 15 caracteres o más, sin placeholders; no vale en
           PR de tipo `sec` ni si toca la lista, este script, un workflow o una ruta de la lista sin marca `~`). El modelo declara `**Issue:** #N` con N entre las
           issues que cierra el PR. Sin lista en la base la puerta aplica y falla. Sale con 1 si no se cumple o si no puede
           leer la API. Corre en `.github/workflows/security-gate.yml` con `pull_request_target`, desde la rama base.

Uso:
  python3 scripts/change_evidence.py pr --pr 123 --out change-record
  python3 scripts/change_evidence.py release --tag v2.3.0 --out evidence/v2.3.0
  python3 scripts/change_evidence.py release --tag v2.3.0 --out /tmp/ev --offline   # solo git, sin API
  python3 scripts/change_evidence.py security --pr 123

Excepción: el PR de release recibe TASK_ID "MAINT": rama release-please--branches--* del propio
repo que SOLO toca ficheros de versión. El nombre de rama no basta: cualquiera con push puede
elegirlo. Es solo una excepción de trazabilidad: blind-review se exige igual, y su falta es un hueco.

Revisión: sin aprobación de GitHub. Vale el estado `blind-review` sobre el SHA de cabeza del PR.

Lectura de la API: `gh api -i` da el estado HTTP real en la línea de estado de stdout. Se reintenta (2 veces) si y
solo si es 5xx, sea cual sea el cuerpo; un 403 o 404 falla a la primera aunque el cuerpo venga vacío o truncado, y
un fallo de red (sin línea de estado) tampoco se reintenta.

PR fusionado: el registro refleja el estado en `merged_at`. Se descartan los check-runs que empezaron (o, sin
`started_at`, terminaron) después y el `blind-review` creado después. Una fecha ilegible no corta y deja hueco.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

TASK_RE = re.compile(r"^\s*Task:\s*([A-Z][A-Z0-9]{1,9}-\d{1,5})\s*$", re.MULTILINE)
CLOSES_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)\b", re.IGNORECASE)
# Un comentario sin cerrar se ignora hasta el final del texto, por prudencia.
HTML_COMMENT_RE = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)
PR_IN_SUBJECT_RE = re.compile(r"\(#(\d+)\)\s*$")
BLIND_REVIEW_CONTEXT = "blind-review"
SECURITY_REVIEW_CONTEXT = "security-review"
SECURITY_PATHS_FILE = ".github/security-paths.txt"
THREAT_MODEL_DIR = "docs/threat-model"
FILES_API_CAP = 3000  # `pulls/N/files` no devuelve más de 3000 ficheros y no avisa: llegar ahí es lectura incompleta
# La línea puede ir como casilla de lista (`- [ ] `, `- [x] `, `* [ ] `), que es como la trae la plantilla del PR.
NO_APLICA_RE = re.compile(r"^[ \t]*(?:[-*][ \t]+\[[ xX]\][ \t]+)?Threat model:[ \t]*no aplica:(.*)$", re.MULTILINE | re.IGNORECASE)
SEC_TITLE_RE = re.compile(r"^\s*sec(?:\([^)]*\))?!?:", re.IGNORECASE)
THREAT_STATES = ("mitigada", "aceptada")  # vocabulario cerrado del estado de una amenaza
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISSUE_DECL_RE = re.compile(r"\*\*Issue:\*\*[ \t]*#(\d+)\b")
OPEN_CELL_RE = re.compile(r"^abiert[ao]\b", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"<[^<>]*>")
NO_APLICA_MIN = 15  # caracteres de motivo, sin contar placeholders `<...>`
EMPTY_CELLS = ("", "-", "--", "—", "–", "n/a", "na", "ninguno", "ninguna", "pendiente", "tbd")
CHANGE_EVIDENCE_PATH = "scripts/change_evidence.py"
WORKFLOWS_PREFIX = ".github/workflows/"
# Restos de TEMPLATE.md que un threat model terminado no puede conservar.
THREAT_PLACEHOLDERS = ("<TASK_ID>", "<feature>", "<n>", "<slug>", "YYYY-MM-DD", "NNNN", "tests/...", "sí / no")
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


# `gh api -i` escribe en stdout la línea de estado, las cabeceras y el cuerpo, también cuando falla (código >= 400):
# «HTTP/1.1 503 Service Unavailable» (o «HTTP/2.0 …» contra GitHub), cabeceras y, tras una línea en blanco, el cuerpo.
# En bytes el separador es «\r\n\r\n»; `subprocess.run(text=True)` traduce «\r\n» a «\n», así que aquí es «\n\n».
# `run()` hace `.strip()`: con cuerpo vacío la salida llega sin separador. Medido con `gh` 2.89.0.
STATUS_LINE_RE = re.compile(r"HTTP/[0-9.]+[ \t]+(\d{3})(?:[ \t]|$)")
RETRIES = 2  # reintentos tras el primer intento: 3 llamadas como máximo
RETRY_DELAY = 1.0  # segundos; se multiplica por el número de reintento


def split_response(out: str | None) -> tuple[int | None, str]:
    """(estado, cuerpo) de la salida de `gh api -i`. Sin línea de estado en la primera línea: (None, salida)."""
    out = out or ""
    m = STATUS_LINE_RE.match(out.split("\n", 1)[0])
    if not m:
        return None, out
    return int(m.group(1)), out.partition("\n\n")[2]


def http_status(e: subprocess.CalledProcessError) -> int | None:
    """Estado HTTP de la línea de estado en stdout de `gh api -i`, también en un fallo. Sin ella devuelve None.

    No mira stderr ni el cuerpo: un 403 puede citar «HTTP 500» o «HTTP 404» en su mensaje, y con cuerpo vacío o
    ilegible `gh` no escribe el código en stderr. Un fallo de red no trae línea de estado.
    """
    return split_response(e.stdout)[0]


def is_transient(e: subprocess.CalledProcessError) -> bool:
    """Se reintenta si y solo si el estado es 5xx, sea cual sea el cuerpo.

    Un 403 o 404 falla a la primera aunque el cuerpo venga vacío o truncado; sin línea de estado (fallo de red)
    tampoco se reintenta.
    """
    status = http_status(e)
    return status is not None and 500 <= status <= 599


def gh_json(path: str) -> object:
    cmd = ["gh", "api", "-i", "-H", "Accept: application/vnd.github+json", path]
    for attempt in range(RETRIES + 1):
        try:
            out = run(cmd)
        except subprocess.CalledProcessError as e:
            if attempt == RETRIES or not is_transient(e):
                raise
            time.sleep(RETRY_DELAY * (attempt + 1))
        else:
            return json.loads(split_response(out)[1])
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


def cut_at_merge(runs: list[dict], merged_at: str, problems: list[str] | None = None) -> list[dict]:
    """Descarta los check-runs posteriores a merged_at.

    La fecha de un run es `started_at`; sin ella, `completed_at`; sin ninguna de las dos el run se queda.
    Igual a merged_at se queda. Una fecha ilegible (de merged_at o del run) no corta: el run se queda y
    la causa se anota en `problems` si se pasa la lista.
    """
    cut = _utc(merged_at)
    if cut is None:
        if problems is not None:
            problems.append(f"merged_at ilegible ({merged_at!r}); los checks no se cortaron")
        return runs
    kept = []
    for r in runs:
        campo = "started_at" if r.get("started_at") else "completed_at" if r.get("completed_at") else None
        when = _utc(r[campo]) if campo else None
        if campo and when is None and problems is not None:
            problems.append(f"el check {r.get('name')} tiene {campo} ilegible ({r[campo]!r}); no se pudo cortar en merged_at")
        if when is None or when <= cut:
            kept.append(r)
    return kept


def status_at_merge(statuses: list[dict], merged_at: str,
                    contexts: tuple[str, ...] = (BLIND_REVIEW_CONTEXT,)) -> tuple[list[dict], list[str]]:
    """Quita los estados de `contexts` creados después de merged_at (igual se queda).

    Devuelve (estados, problemas). Un created_at ilegible no corta y se anota. Con merged_at ilegible no se
    corta y no se anota nada: `cut_at_merge` ya lo anota para los checks.
    """
    cut = _utc(merged_at)
    if cut is None:
        return statuses, []
    kept, problems = [], []
    for s in statuses:
        if s.get("context") in contexts and s.get("created_at"):
            when = _utc(s["created_at"])
            if when is None:
                problems.append(f"el estado {s['context']} tiene created_at ilegible ({s['created_at']!r}); no se pudo cortar en merged_at")
            elif when > cut:
                continue
        kept.append(s)
    return kept, problems


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
        meta = gh_json(f"repos/{repo}/contents/release-please-config.json?ref={quote(base_ref, safe='')}")
    except subprocess.CalledProcessError as e:
        if http_status(e) == 404:  # rama base sin configuración: solo los ficheros fijos
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
    # un renombrado o copia desde una ruta sensible a un fichero de versión no es un cambio de versión
    return bool(files) and all(f["filename"] in allowed and (f.get("previous_filename") or f["filename"]) in allowed for f in files)


# ───────────── puerta de seguridad (SMC-009) ─────────────
def parse_security_rules(text: str) -> list[tuple[str, bool]]:
    """Reglas de `.github/security-paths.txt`: (glob, admite_no_aplica), una por línea; `#` abre un comentario.

    `~` pegado al inicio del glob (tras quitar espacios) lo marca: la ruta sigue siendo sensible y además admite
    «no aplica». Una marca mal escrita (`~ ruta`, `~~ruta`) no marca: la ruta queda sensible y sin exención.
    """
    rules = []
    for line in text.splitlines():
        line = re.split(r"(?:^|\s)#", line, maxsplit=1)[0].strip()
        if not line.startswith("~"):
            if line:
                rules.append((line, False))
            continue
        rest = line[1:]
        marked = bool(rest) and not rest[0].isspace() and rest[0] != "~"
        glob = rest if marked else rest.lstrip("~ \t")
        if glob:
            rules.append((glob, marked))
    return rules


def parse_security_paths(text: str) -> list[str]:
    """Globs de la lista de rutas sensibles, sin la marca `~`."""
    return [glob for glob, _ in parse_security_rules(text)]


def pr_title_type(title: str) -> str | None:
    """Tipo conventional del título (`sec`) o None."""
    return "sec" if SEC_TITLE_RE.match(title or "") else None


def read_file_at(repo: str, path: str, ref: str) -> str | None:
    """Texto de `path` en `ref` (rama o SHA). None solo si el estado HTTP es 404.

    Cualquier otro fallo propaga. Una carpeta (la API devuelve una lista), un enlace simbólico, un submódulo o un
    fichero que la API no sirve en base64 no son un fichero legible: ValueError, no «ausente».
    """
    try:
        meta = gh_json(f"repos/{repo}/contents/{quote(path, safe='/')}?ref={quote(ref, safe='')}")
    except subprocess.CalledProcessError as e:
        if http_status(e) == 404:
            return None
        raise
    if not isinstance(meta, dict) or meta.get("type") != "file" or meta.get("encoding") != "base64" or not meta.get("content"):
        raise ValueError(f"{path} en {ref}: no es un fichero legible por la API de contenidos")
    try:
        return base64.b64decode("".join(meta["content"].split()), validate=True).decode("utf-8")
    except ValueError as e:  # binascii.Error y UnicodeDecodeError lo son
        raise ValueError(f"{path} en {ref}: contenido ilegible ({e})") from e


def _cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _clean(cell: str) -> str:
    return cell.strip().strip("`*_ \t")


def _is_table_line(line: str) -> bool:
    """Línea de tabla: lleva un `|` sin escapar, con o sin `|` inicial."""
    return re.search(r"(?<!\\)\|", line) is not None


def _tables(text: str) -> list[list[list[str]]]:
    """Tablas del texto: líneas seguidas con `|`; la primera es la cabecera. Cada fila es su lista de celdas."""
    tables: list[list[list[str]]] = []
    current: list[list[str]] | None = None
    for line in text.splitlines():
        if not _is_table_line(line):
            current = None
            continue
        if current is None:
            current = []
            tables.append(current)
        current.append(_cells(line))
    return tables


def _is_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-+:?", c) for c in cells if c)


def _table_rows(text: str, column: str) -> list[tuple[list[str], dict[str, int]]]:
    """Filas de datos de las tablas cuya cabecera tiene la columna `column`, con los índices de sus columnas."""
    rows = []
    for table in _tables(text):
        names = {_clean(c).casefold(): i for i, c in enumerate(table[0])}
        if column.casefold() not in names:
            continue
        rows.extend((cells, names) for cells in table[1:] if not _is_separator(cells))
    return rows


def _accepted_on(section5: str, threat: str) -> bool:
    """¿Hay en la sección 5 una fila de `threat` con quien acepta y «Fecha» con formato de fecha real?

    La fecha es la fecha de aceptación que escribe quien acepta; no autentica a nadie. La firma real es el estado
    `security-review` que publica David sobre el SHA del PR.
    """
    for cells, cols in _table_rows(section5, "Fecha"):
        def cell(name: str) -> str:
            i = cols.get(name)
            return _clean(cells[i]) if i is not None and i < len(cells) else ""
        if _clean(cells[0]) == threat and cell("aceptado por") and ISO_DATE_RE.match(cell("fecha")):
            try:
                dt.date.fromisoformat(cell("fecha"))
            except ValueError:
                continue
            return True
    return False


def _cell_at(cells: list[str], names: dict[str, int], prefix: str) -> tuple[bool, str]:
    """(¿existe la columna cuyo nombre empieza por `prefix`?, su celda limpia)."""
    for name, i in names.items():
        if name.startswith(prefix):
            return True, (_clean(cells[i]) if i < len(cells) else "")
    return False, ""


def threat_model_problems(text: str, closes: list[int] | None = None) -> list[str]:
    """Motivos por los que un threat model no vale.

    Los comentarios HTML no cuentan (no se ven). Hace falta al menos una fila de amenaza (tabla con una columna
    «Estado»); el estado de cada fila es, entera la celda, `mitigada` o `aceptada` (cualquier otro valor, vacío o
    `abierta (x)` incluidos, no pasa); una `mitigada` exige celdas de mitigación y de test no vacías; una `aceptada`
    exige su fila en la sección 5 con «Fecha» con formato de fecha (la fecha de aceptación, que escribe David);
    `abierta` en cualquier celda de cualquier línea de tabla no pasa, tenga o no `|` inicial y sea cual sea la
    cabecera; y no quedan placeholders de la plantilla. Con `closes` (las issues que cierra el PR), el modelo declara
    `**Issue:** #N` y N está entre ellas.
    """
    text = HTML_COMMENT_RE.sub("", text or "")
    problems = []
    rows: list[tuple[list[str], dict[str, int]]] = []
    for table in _tables(text):
        names = {_clean(c).casefold(): i for i, c in enumerate(table[0])}
        n_estado = sum(1 for c in table[0] if _clean(c).casefold() == "estado")
        if n_estado > 1:
            problems.append(f"tabla con dos columnas «Estado» (o más, {n_estado}): el estado de cada amenaza debe ser una sola celda")
        elif n_estado == 1:
            rows.extend((cells, names) for cells in table[1:] if not _is_separator(cells))
        for cells in table:
            if any(OPEN_CELL_RE.match(_clean(c)) for c in cells):
                problems.append(f"celda 'abierta' en la línea de tabla de {cells[0] or '?'}: una amenaza abierta no pasa la puerta")
    if not rows:
        problems.append("sin filas de amenaza: falta la tabla con columna «Estado» y al menos una amenaza")
    section5 = ""
    m5 = re.search(r"^##[ \t]+5\b.*$", text, re.MULTILINE)
    if m5:
        rest = text[m5.end():]
        nxt = re.search(r"^##[ \t]", rest, re.MULTILINE)
        section5 = rest[:nxt.start()] if nxt else rest
    for cells, cols in rows:
        name = cells[0] or "?"
        idx = cols["estado"]
        estado = _clean(cells[idx]) if len(cells) > idx else ""
        if estado.casefold() not in THREAT_STATES:
            problems.append(f"amenaza {name}: estado '{estado.casefold()}' fuera de {'/'.join(THREAT_STATES)}")
        elif estado.casefold() == "aceptada" and not _accepted_on(section5, _clean(name)):
            problems.append(f"amenaza {name} aceptada sin fecha de aceptación en la sección 5 "
                            "(fila con su ID, quien acepta y «Fecha» con formato AAAA-MM-DD)")
        elif estado.casefold() == "mitigada":
            for etiqueta, prefijo in (("mitigación", "mitigaci"), ("test que la verifica", "test")):
                existe, valor = _cell_at(cells, cols, prefijo)
                if valor.casefold() in EMPTY_CELLS:
                    problems.append(f"amenaza {name} mitigada sin {etiqueta}: "
                                    + ("celda vacía" if existe else f"falta la columna «{etiqueta}»"))
    for ph in THREAT_PLACEHOLDERS:
        if ph in text:
            problems.append(f"queda un placeholder de la plantilla: {ph}")
    if closes is not None:
        m = ISSUE_DECL_RE.search(text)
        if not m:
            problems.append("el modelo no declara su issue con '**Issue:** #N'")
        elif int(m.group(1)) not in closes:
            problems.append(f"el modelo declara **Issue:** #{m.group(1)} y el PR cierra "
                            + (", ".join(f"#{n}" for n in closes) if closes else "ninguna issue"))
    return problems


def safe_text(value: object) -> str:
    """Texto sin saltos de línea ni caracteres de control, para imprimir lo que controla el autor del PR.

    Un salto de línea (también U+2028 o U+0085) abre una línea nueva en el log, y una línea que empieza por `::` es
    un comando de workflow. Los saltos se vuelven un espacio; el resto de caracteres de control o de formato se quitan.
    """
    out = re.sub(r"[\r\n\t\x0b\x0c\x85\u2028\u2029]+", " ", str(value))
    return "".join(c for c in out if not unicodedata.category(c).startswith("C"))


def no_aplica_reason(body: str) -> str | None:
    """Motivo de la línea `Threat model: no aplica: <motivo>` (fuera de comentarios HTML). None si no hay línea;
    cadena vacía si la hay sin motivo."""
    m = NO_APLICA_RE.search(HTML_COMMENT_RE.sub("", body or ""))
    return m.group(1).strip() if m else None


def no_aplica_invalid(motivo: str) -> str | None:
    """Por qué un motivo de `no aplica` no vale (None si vale): sin contar placeholders `<...>`, al menos
    NO_APLICA_MIN caracteres y 8 letras o cifras. `<motivo>`, `.` o una fila de puntos no son un motivo."""
    rest = PLACEHOLDER_RE.sub("", motivo or "").strip()
    if len(rest) < NO_APLICA_MIN or sum(c.isalnum() for c in rest) < 8:
        return f"el motivo debe decir algo: al menos {NO_APLICA_MIN} caracteres sin placeholders <...> (hay {len(rest)})"
    return None


class HeadMovedError(RuntimeError):
    """La cabeza del PR ya no es el commit sobre el que se va a publicar el estado."""


def _check_head(pr: dict, head_sha: str, number: int, when: str) -> None:
    actual = (pr.get("head") or {}).get("sha")
    if actual != head_sha:
        raise HeadMovedError(f"PR #{number}: la cabeza {when} es {str(actual)[:12]} y el evento trae {head_sha[:12]}: "
                             "la evaluación no vale para ese commit")


def evaluate_security(repo: str, number: int, pr: dict | None = None, tasks: list[str] | None = None,
                      maint: bool | None = None, head_sha: str | None = None) -> dict:
    """Puerta de seguridad de un PR. Devuelve required, reason, threat_model, problems y warnings.

    La lista de rutas se lee de la rama BASE; el threat model, de la cabeza. Cualquier fallo de la API
    propaga (la puerta falla en cerrado). `pr`, `tasks` y `maint` se pasan si el llamador ya los tiene.
    Con `head_sha` (el commit sobre el que se publicará el estado) la cabeza del PR debe ser ese commit al
    empezar y al acabar: si se mueve, lanza HeadMovedError (la cabeza nueva tendrá su propia evaluación).
    """
    pr = pr if pr is not None else gh_json(f"repos/{repo}/pulls/{number}")
    if head_sha is None:
        return _evaluate_security(repo, number, pr, tasks, maint)
    _check_head(pr, head_sha, number, "actual")
    out = _evaluate_security(repo, number, pr, tasks, maint)
    _check_head(gh_json(f"repos/{repo}/pulls/{number}"), head_sha, number, "al acabar")
    return out


def _evaluate_security(repo: str, number: int, pr: dict, tasks: list[str] | None, maint: bool | None) -> dict:
    body = pr.get("body") or ""
    if tasks is None:
        commits = gh_pages(f"repos/{repo}/pulls/{number}/commits")
        tasks = extract_tasks(body, *[c["commit"]["message"] for c in commits])
    if maint is None:
        head_repo = (pr["head"].get("repo") or {}).get("full_name")
        maint = is_release_pr(repo, number, pr["head"].get("ref") or "", pr["base"]["ref"], head_repo == repo)
    out = {"required": False, "reason": "", "threat_model": None, "problems": [], "warnings": []}
    if maint:
        out["reason"] = "PR de release: no le afecta la puerta"
        return out

    files = gh_pages(f"repos/{repo}/pulls/{number}/files")
    if len(files) >= FILES_API_CAP:
        raise PagesLimitError(f"pulls/{number}/files: {len(files)} ficheros; la API corta en {FILES_API_CAP}, lectura incompleta")
    touched = {n for f in files for n in (f.get("filename"), f.get("previous_filename")) if n}
    listing = read_file_at(repo, SECURITY_PATHS_FILE, pr["base"]["ref"])
    reasons = []
    is_sec = pr_title_type(pr.get("title") or "") == "sec"
    if is_sec:
        reasons.append("título de tipo sec")
    if SECURITY_PATHS_FILE in touched:
        reasons.append(f"toca la lista de rutas sensibles ({SECURITY_PATHS_FILE})")
    missing_list = listing is None
    listed_hits: list[str] = []
    exempt_hits: set[str] = set()
    if missing_list:
        # sin lista en la base no se puede saber qué es sensible: la puerta aplica y falla en cerrado
        reasons.append(f"falta la lista de rutas sensibles ({SECURITY_PATHS_FILE}) en la rama base {safe_text(pr['base']['ref'])}")
        out["warnings"].append(f"no existe {SECURITY_PATHS_FILE} en la rama base {safe_text(pr['base']['ref'])}: la puerta falla en cerrado")
    else:
        rules = parse_security_rules(listing)
        hits = sorted(n for n in touched if any(fnmatch.fnmatchcase(n, g) for g, _ in rules))
        listed_hits = hits
        # admite «no aplica» la ruta que casa con una regla marcada y con ninguna sin marcar
        exempt_hits = {n for n in hits if any(m and fnmatch.fnmatchcase(n, g) for g, m in rules)
                       and not any(not m and fnmatch.fnmatchcase(n, g) for g, m in rules)}
        if hits:
            shown = ", ".join(safe_text(h) for h in hits[:5])
            reasons.append("toca rutas sensibles: " + shown + (f" y {len(hits) - 5} más" if len(hits) > 5 else ""))
    if not reasons:
        out["reason"] = "no toca rutas sensibles ni es de tipo sec"
        return out

    out["required"], out["reason"] = True, "; ".join(reasons)
    if missing_list:
        out["problems"].append(f"falta {SECURITY_PATHS_FILE} en la rama base {safe_text(pr['base']['ref'])}: la puerta falla en cerrado")
    # «no aplica» no vale donde el riesgo es mayor: tipo sec, la lista, esta puerta, un workflow o cualquier ruta de
    # la lista que la propia lista no marque con `~` (N12, SMC-011)
    strict = (is_sec or SECURITY_PATHS_FILE in touched or CHANGE_EVIDENCE_PATH in touched
              or any(n.startswith(WORKFLOWS_PREFIX) for n in touched)
              or any(h not in exempt_hits for h in listed_hits))
    motivo_raw = no_aplica_reason(body)
    motivo = None
    if motivo_raw is not None:
        bad = no_aplica_invalid(motivo_raw)
        if strict:
            out["problems"].append("la línea 'Threat model: no aplica' no vale en un PR de tipo sec ni si toca la lista de rutas, "
                                   f"{CHANGE_EVIDENCE_PATH}, un workflow o cualquier ruta de la lista sin marca ~: "
                                   "hace falta el threat model")
        elif bad:
            out["problems"].append(f"motivo no válido en la línea 'Threat model: no aplica': {bad}")
        else:
            motivo = safe_text(motivo_raw)
    closes = extract_issues(body)
    found = []
    present = {f["filename"] for f in files if f.get("filename") and f.get("status") != "removed"}
    for task in tasks or []:
        path = f"{THREAT_MODEL_DIR}/{task}.md"
        text = read_file_at(repo, path, pr["head"]["sha"])
        if text is not None and path not in present:
            # existe en la cabeza pero el PR no lo toca: es de antes (o de otra tarea) y no prueba nada de este cambio
            if not motivo:
                out["problems"].append(f"{path} existe en la cabeza pero el PR no lo añade ni lo modifica en pulls/{number}/files "
                                       "y no hay línea 'Threat model: no aplica: <motivo>'")
            continue
        if text is None:
            if not motivo:
                out["problems"].append(f"falta {path} en la cabeza del PR y no hay línea 'Threat model: no aplica: <motivo>'"
                                       + (" con motivo" if motivo == "" else ""))
            continue
        found.append(path)
        out["problems"].extend(f"{path}: {m}" for m in threat_model_problems(text, closes))
    if not tasks and not motivo:
        out["problems"].append("sin TASK_ID no se puede localizar docs/threat-model/<TASK_ID>.md y no hay línea "
                               "'Threat model: no aplica: <motivo>'" + (" con motivo" if motivo == "" else ""))
    out["threat_model"] = ", ".join(found) if found else (f"no aplica: {motivo}" if motivo else None)
    return out


# ───────────── recogida de datos ─────────────
def collect_pr(repo: str, number: int) -> dict:
    pr = gh_json(f"repos/{repo}/pulls/{number}")
    commits = gh_pages(f"repos/{repo}/pulls/{number}/commits")
    reviews = gh_pages(f"repos/{repo}/pulls/{number}/reviews")
    head_sha = pr["head"]["sha"]
    gaps: list[str] = []
    try:
        # filter=all: sin él la API devuelve solo el último run de cada check suite (por nombre y suite) y el
        # corte en merged_at se queda sin el run que había al fusionar.
        checks = gh_pages(f"repos/{repo}/commits/{head_sha}/check-runs?filter=all", "check_runs")
    except READ_ERRORS as e:
        checks = []
        gaps.append(f"PR #{number}: no se pudieron leer los checks ({reason(e)})")
    if pr.get("merged_at"):
        problems: list[str] = []
        kept = cut_at_merge(checks, pr["merged_at"], problems)
        gaps.extend(f"PR #{number}: {m}" for m in problems)
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
    if pr.get("merged_at"):  # el registro refleja el estado al fusionar: un blind-review posterior no cuenta
        statuses, odd = status_at_merge(statuses, pr["merged_at"], (BLIND_REVIEW_CONTEXT, SECURITY_REVIEW_CONTEXT))
        gaps.extend(f"PR #{number}: {m}" for m in odd)
    blind = latest_status(statuses, BLIND_REVIEW_CONTEXT)
    sec_review = latest_status(statuses, SECURITY_REVIEW_CONTEXT)

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
    try:
        gate = evaluate_security(repo, number, pr, tasks, maint)
    except (*READ_ERRORS, ValueError) as e:
        gate = {"required": None, "reason": f"no se pudo evaluar ({reason(e)})", "threat_model": None}
        gaps.append(f"PR #{number}: no se pudo evaluar la puerta de seguridad ({reason(e)})")

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
        "security": {
            "required": gate["required"], "reason": gate["reason"], "threat_model": gate["threat_model"],
            "review": sec_review.get("state") if sec_review else None,
        },
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


def security_label(sec: dict) -> str:
    if sec["required"] is None:
        return f"sin evaluar · {sec['reason']}"
    if not sec["required"]:
        return f"no aplica · {sec['reason']}"
    return (f"aplica ({sec['reason']}) · threat model: {sec['threat_model'] or '—'} · "
            f"security-review: {sec['review'] or '—'}")


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
        f"- **Puerta de seguridad:** {security_label(p['security'])}\n"
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
        print(f"AVISO: {safe_text(g)}", file=sys.stderr)
    return 1 if errors else 0


def mode_security(args: argparse.Namespace) -> int:
    """Puerta de seguridad: 1 si aplica y no se cumple, o si no se pudo leer la API (falla en cerrado)."""
    try:
        repo = repo_slug()
        r = evaluate_security(repo, args.pr, head_sha=args.head_sha)
    except Exception as e:  # noqa: BLE001 — cualquier fallo de lectura o de forma cierra la puerta
        print(f"ERROR: PR #{args.pr}: no se pudo evaluar la puerta de seguridad ({safe_text(reason(e))})", file=sys.stderr)
        return 1
    for w in r["warnings"]:
        print(f"AVISO: {safe_text(w)}", file=sys.stderr)
    if not r["required"]:
        print(f"PR #{args.pr}: no aplica la puerta de seguridad ({safe_text(r['reason'])})")
        return 0
    print(f"PR #{args.pr}: aplica la puerta de seguridad ({safe_text(r['reason'])}) · threat model: {safe_text(r['threat_model'] or '—')}")
    for m in r["problems"]:
        print(f"ERROR: {safe_text(m)}", file=sys.stderr)
    return 1 if r["problems"] else 0


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
            sec = p["security"]
            if sec["required"] and sec["review"] != "success":
                gaps.append(f"PR #{n} activa la puerta de seguridad sin security-review correcto (estado: {sec['review'] or '—'})")
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
    c = sub.add_parser("security")
    c.add_argument("--pr", type=int, required=True)
    c.add_argument("--head-sha", required=True,
                   help="commit del evento sobre el que se publicará el estado: debe ser la cabeza actual del PR")
    b = sub.add_parser("release")
    b.add_argument("--tag", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--offline", action="store_true", help="solo git, sin llamadas a la API")
    args = ap.parse_args()
    sys.exit({"pr": mode_pr, "security": mode_security, "release": mode_release}[args.mode](args))


if __name__ == "__main__":
    main()
