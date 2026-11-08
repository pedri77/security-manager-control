# T59 · SMC-012 · informe de dev-proyecto v1.5

Rama `t59-smc012` (sale de dcb2acc). Issue #36. Sin push ni PR.

## Qué se hizo
- `.github/workflows/vigilancia.yml`: `ref: "${{ github.event.repository.default_branch }}"` en el checkout (antes `main`); el comentario de cabecera dice «rama por defecto». La expresión va solo en `with:`, no en un `run`.
- `tests/test_vigilancia.py`: 7 tests nuevos `test_t59_*` (con parametrizados, 26 casos nuevos más 1):
  checkout con la rama por defecto; detector sobre YAML real de `.github/workflows/*.yml` (recorre el árbol YAML, así que los comentarios no cuentan);
  detector sobre `scripts/*.py` (regex por línea, sin comentarios); detectores probados con 13 casos YAML y 9 de Python (`[main, master]`, la etiqueta de `release.yml`
  y la rama por defecto no se rechazan; `ref: main`, `ref: master`, `branches: [main]`, `branches: main` y la lista de un elemento sí);
  la excepción de `tests.yml` sigue haciendo falta; y modelo SMC-012 pasa la puerta con las citas existentes. `test_workflow_escanea_la_rama_principal_y_llama_al_script` ya no admite `ref: main`.
- `docs/threat-model/SMC-012.md`: T1 (DoS por rama equivocada), T2 (inyección por el nombre de rama), T3 (regresión). Todas `mitigada`; sin aceptaciones.
- `README.md`: 793 a 800 (`def test_` real).

## Desajuste con el enunciado
`.github/workflows/tests.yml` tiene `branches: [main]` en `push` y `pull_request`, y T59 no permite tocar otros workflows. Un test que rechace toda rama fija única
falla con él. Solución: lista `WORKFLOWS_CON_RAMA_FIJA_CONOCIDA = {"tests.yml"}` en el test, y `test_t59_la_excepcion_de_tests_yml_sigue_haciendo_falta`
falla cuando se arregle tests.yml, para obligar a quitarla. Conviene una tarea aparte para `tests.yml` (`[main, master]` o la rama por defecto; en `on:` no se admite la expresión de contexto, así que sería `[main, master]`).

## Verifica
- TDD: antes del arreglo fallaban `test_t59_el_checkout...` y `test_t59_ningun_workflow_fija...`; los detectores ya pasaban (no dependen del arreglo).
- `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: 1710 passed y los 2 tests de cifras del README, que fallaron porque `wc` había metido espacios en la insignia; corregido y repetidos (`test_cli_v06`, `test_cli_v07`: 61 passed). 800 `def test_`.
- `threat_model_problems(SMC-012.md, [36])` = `[]`; citas existentes (test propio).
- GET real: `gh api repos/pedri77/security-manager-control --jq .default_branch` = `main`; `gh api repos/pedri77/MalwareIntel --jq .default_branch` = `master`.
- `actionlint`: no instalado, no medido.

## Contraprueba (copias fuera del worktree, una por mutante, `tests/test_vigilancia.py`)
| Mutante | En rojo |
|---|---|
| `ref: main` en vigilancia.yml | 3 (`test_workflow_escanea_la_rama_principal_y_llama_al_script`, `test_t59_el_checkout...`, `test_t59_ningun_workflow_fija...`) |
| `ref: master` | 2 (`test_t59_el_checkout...`, `test_t59_ningun_workflow_fija...`) |
| `branches: [main]` en ci.yml | 1 (`test_t59_ningun_workflow_fija...`) |

Prod: ninguna.
