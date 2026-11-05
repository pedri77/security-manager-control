# T40 informe (dev-proyecto v1.5)

Rama t40-smc004, un commit solo con `smc/cli.py`, `tests/test_cli_errores.py`, `tests/golden/{gap.md,gap_o.md,plan.md}`.

## Cambios
- `smc/cli.py`: `smc gap` y `smc plan` capturan `_ERRORES_DATOS + (RecursionError,)`. `_ERRORES_DATOS` intacto.
- Caso nuevo `yaml-profundo` (500 `[` sin cerrar) en los tests parametrizados: rc=2, `ERROR: <ruta>:`, sin Traceback, y sin crear `-o`.
- `test_evaluacion_valida_sigue_igual` sustituido por tres tests contra ficheros de referencia: `gap`, `plan`, `gap -o` (fichero, y stdout `Informe escrito en <ruta>`).

## Generación de las referencias (código de 0c1a5be)
```
D=$(mktemp -d); git archive 0c1a5be | tar -x -C $D
export PYTHONPATH=$D; cd $D      # cwd = D para que smc salga de D
uv run --no-project --with pyyaml python -c "import smc;print(smc.__file__)"   # -> $D/smc/__init__.py (comprobado)
uv run --no-project --with pyyaml python -m smc.cli gap  <worktree>/assessments/examples/ejemplo-energia.yaml --hoy 2026-11-03 > tests/golden/gap.md
uv run --no-project --with pyyaml python -m smc.cli plan <worktree>/assessments/examples/ejemplo-energia.yaml --hoy 2026-11-03 > tests/golden/plan.md
uv run --no-project --with pyyaml python -m smc.cli gap  <worktree>/assessments/examples/ejemplo-energia.yaml --hoy 2026-11-03 -o tests/golden/gap_o.md
```
rc=0 en los tres. `grep` de `/Users`, `/private`, `/var/` en las referencias: 0. Sin fechas variables (`--hoy` fijo). El stdout de `-o` lleva la ruta, por eso no se guarda: el test la reconstruye.
Nota: lanzado desde el worktree, `python -m` importó el `smc` del cwd; por eso se generó desde `$D`.

## Verifica
`PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: 677 passed.

## Contraprueba
Copia temporal (`git archive HEAD` + ficheros modificados), `PYTHONPATH=<copia>`, `smc.__file__` comprobado en la copia. Solo `tests/test_cli_errores.py`. Base: 12 passed.
| Mutante | Resultado | Tests en rojo |
|---|---|---|
| quitar RecursionError de gap | 2 failed | `test_fichero_malo_da_error_limpio[yaml-profundo-gap]`, `test_gap_con_salida_no_crea_fichero[yaml-profundo]` |
| quitar RecursionError de plan | 1 failed | `test_fichero_malo_da_error_limpio[yaml-profundo-plan]` |
| `print(report + "X")` | 1 failed | `test_gap_valido_igual_que_referencia` |
| `write_text(report + "X")` | 1 failed | `test_gap_con_salida_valida_igual_que_referencia` |
| línea extra en `run_plan` (gap.py de la copia) | 1 failed | `test_plan_valido_igual_que_referencia` |

## Queda
Nada. Sin acción de prod. gitleaks staged sin hallazgos.

## Revisión del coordinador (2026-11-05)
- Alcance: `git diff --stat` = cli.py, test_cli_errores.py, tests/golden/{gap,gap_o,plan}.md; todo dentro de «Toca». Superficie (superficies.py diff dev-proyecto): OK. gitleaks y grep de secretos: sin hallazgos. «No hace» respetado (`_ERRORES_DATOS` intacto, sin tocar gap.py/plan.py).
- Procedencia golden: regenerados por mí desde `git archive 0c1a5be` con `PYTHONPATH=<copia>` (smc.__file__ en la copia); `cmp` idéntico en los tres. 0 rutas absolutas en las referencias.
- Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en el worktree: 677 passed.
- Contraprueba (copia limpia de HEAD por mutante, PYTHONPATH=copia, smc.__file__ en la copia; base 12 passed):
  - quitar RecursionError de gap → 2 failed: `test_fichero_malo_da_error_limpio[yaml-profundo-gap]`, `test_gap_con_salida_no_crea_fichero[yaml-profundo]`
  - quitar RecursionError de plan → 1 failed: `test_fichero_malo_da_error_limpio[yaml-profundo-plan]`
  - `print(report + "X")` → 1 failed: `test_gap_valido_igual_que_referencia`
  - `write_text(report + "X")` → 1 failed: `test_gap_con_salida_valida_igual_que_referencia`
  - línea `print("X")` al inicio de `run_plan` (smc/gap.py) → 4 failed: `test_fichero_malo_da_error_limpio[inexistente-plan]`, `[yaml-roto-plan]`, `[yaml-profundo-plan]`, `test_plan_valido_igual_que_referencia` (el informe del agente dice 1; depende de la línea añadida: con `print` también caen los casos de error, que comparan stderr/stdout).
