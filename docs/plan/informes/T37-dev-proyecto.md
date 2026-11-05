# T37 · informe dev-proyecto (v1.5)

Rama `t37`, worktree `/Users/pedri77/Dev/wt/smc-t37`. Sin push ni PR. Issue SMC-003 (#13).

## Qué hice
- `gh_pages(path, key=None)` en `scripts/change_evidence.py`: pide `page=1,2,...` con `per_page=100` hasta una página corta (`MAX_PAGES=50`; si se alcanza lanza error, que acaba como hueco, no corta en silencio). `key` extrae la lista de respuestas objeto (`check_runs`).
- `collect_pr` usa `gh_pages` para commits, reviews, check-runs y estados.
- `latest_status(statuses, context)`: el más reciente por `(created_at, id)`, sin fiarse del orden de la lista.
- Errores: checks y estados mantienen su `try/except` → hueco, ahora también si falla la página 2+ (se descarta lo leído y se anota). Commits y reviews siguen propagando el error como antes.

## Ficheros
`scripts/change_evidence.py`, `tests/test_change_evidence.py` (commit en `t37`). Informe sin commitear. Un test existente se adaptó: su simulación servía `/status`; ahora sirve `/statuses?`.

## Decisiones comprobadas
1. **`/status` vs `/statuses`**. Usé `commits/<sha>/statuses`. El combinado (`/status`) devuelve `state` agregado y una entrada por contexto (la última de cada uno), pero su lista `statuses` también se pagina y mezcla el estado global; la lista `/statuses` devuelve todo el historial, el más reciente primero. Para «cuenta el estado más reciente» de un contexto concreto, elegir yo el máximo por `created_at,id` sobre el historial completo es explícito, testeable y no depende de cómo deduplique el combinado ni del orden. Observado contra la API real (commit `0c1a5be`, sin estados): ambos devuelven vacío, así que no pude contrastar la deduplicación en vivo con un caso con repeticiones; la descripción del combinado sale de la documentación, no de prueba propia.
2. **`gh api --paginate`**. Comprobado con gh 2.89.0 sobre `check-runs?per_page=1`: sin `--slurp` imprime las páginas una tras otra (`{..}{..}` para objetos, `[..][..]` para listas), que `json.loads` no acepta; el objeto de check-runs repite `total_count` y no se fusiona la clave `check_runs`. Con `--slurp` devuelve una lista de páginas (13 objetos, cada uno con `total_count: 13`), de forma distinta según sea lista u objeto. Por eso no lo uso: bucle explícito con `page=N`, que además se simula bien en tests.
3. Límite conocido de GitHub: `pulls/<n>/commits` devuelve como máximo 250 commits aunque se pagine; no se aborda aquí.

## Verifica
- `uv run --extra dev pytest -q tests/test_change_evidence.py` → 18 passed.
- `make test` → 654 passed.
- Tests nuevos (un criterio cada uno, `gh` simulado con `per_page=2`): Task en página 2 de commits; aprobación en página 2 de reviews; check en página 2 de check-runs; blind-review fuera de la primera página de estados; blind-review repetido (orden nuevo-primero y viejo-primero); fallo en página 2 de check-runs y de estados queda como hueco; página exacta/vacía termina.

## Contraprueba
- Lectura de una sola página (`if len(chunk) < PER_PAGE` → `if True`): 7 de los tests nuevos en rojo (los de Task, aprobación, check, blind-review en página 2, repetido viejo-primero y los dos de hueco). Los de «repetido nuevo-primero» y «página exacta» pasan por diseño (todo cabe en la primera página).
- Tomar el primer estado en vez del más reciente: `test_blind_review_repetido...[viejo_primero]` en rojo.
- Código restaurado tras ambas.

## Lo que queda
- La plantilla `f2p/repo-templates` de enjambre-agentes se sincroniza aparte tras fusionar (fuera de alcance).
- Cuando haya un SHA real con `blind-review` repetido, contrastar en vivo `/status` frente a `/statuses`.

## Revisión del coordinador (2026-11-05)
- Alcance: solo `scripts/change_evidence.py` y `tests/test_change_evidence.py`; superficies.py diff OK; gitleaks sin hallazgos; pie `Task: SMC-003` y `Tarea:` presentes.
- `uv run --extra dev pytest -q tests/test_change_evidence.py` → 18 passed.
- `make test` → 654 passed.
- Contraprueba: `if len(chunk) < PER_PAGE:` → `if True:` (línea 87) → 7 failed, 11 passed (Task p2, aprobación p2, check p2, blind-review p2, repetido viejo-primero, hueco checks, hueco estados). Restaurado, diff limpio.
