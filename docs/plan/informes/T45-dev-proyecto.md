# T45 (SMC-006): informe dev-proyecto v1.5

Rama `t45-smc006`, worktree `/Users/pedri77/Dev/wt/smc-006-t45`. Commit `03ab447` (pies Agente, Tarea, Task: SMC-006). Sin push ni PR.

## Qué se hizo
`smc/gap.py`:
- `analyse`: `elif ev is not None and not (isinstance(estado, str) and estado in VALID_STATES)`. Un estado no texto sigue el camino de estado no válido (aviso `estado no válido '...'`, sin evaluar). El texto del aviso no cambia.
- `_heredado`: `if isinstance(estado, str) and estado in SCORES`. Decisión añadida: es el mismo `in` sobre un valor no hashable, y un control sin evaluar con equivalente cuyo estado es `[]` daba el mismo TypeError. Es el mismo fichero y el mismo defecto (estado no escalar en gap/plan).

`tests/test_cli_errores.py` (añadidos):
- `test_estado_no_escalar_no_da_traceback` (gap/plan x `[]`/`{}`): rc=0, sin Traceback, stderr vacío.
- `test_gap_estado_no_escalar_avisa_y_cuenta_sin_evaluar` (`[]`, `{}`): aviso y control en `sin_evaluar`, no en brechas.
- `test_gap_estado_no_escalar_en_equivalente_no_da_traceback` (ENS-org.1 con `estado: []`, hereda NIS2-20.1).
- `test_yaml_valido_no_mapa_da_rc0_con_aviso` (`42`, `- a`, `hola`, vacío): rc=0 y aviso "La evaluación no es un mapa YAML: se trata como vacía".

No se tocó `cli.py`, `_ERRORES_DATOS`, `_load`, `compare.py` ni `tests/golden/`.

## Verifica
`PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: 735 passed. `git diff --stat HEAD~1 -- tests/golden`: vacío. gitleaks staged: sin fugas.

## Contraprueba (una copia por mutante, `git archive HEAD`, `PYTHONPATH=<copia>`, lanzado desde la copia, `smc.__file__` dentro de la copia; pytest sobre `tests/test_cli_errores.py`)
Copias (no borradas), en `/var/folders/db/ccfn3h311m941bgd0sggl7v00000gn/T/`:
- `tmp.dWvsouaSPW`: mutante A, `estado not in VALID_STATES` sin comprobación de tipo. 6 failed, 33 passed. Rojos: `test_estado_no_escalar_no_da_traceback[[]-gap]`, `[[]-plan]`, `[{}-gap]`, `[{}-plan]`; `test_gap_estado_no_escalar_avisa_y_cuenta_sin_evaluar[[]]`, `[{}]`.
- `tmp.5TOty6fCh5`: mutante B, `_load` lanza ValueError si el resultado no es mapa. 4 failed, 35 passed. Rojos: `test_yaml_valido_no_mapa_da_rc0_con_aviso[entero]`, `[lista]`, `[texto]`, `[vacio]`.
- `tmp.zBQm0kckto`: mutante C (extra), `_heredado` con `estado in SCORES`. 1 failed, 38 passed. Rojo: `test_gap_estado_no_escalar_en_equivalente_no_da_traceback`.

## Queda
Nada de T45. Acción de prod: ninguna. El informe lo commitea el coordinador.

## Verificación del coordinador (coordinador-smc-f2p v2.3, 2026-11-05)
- Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en `/Users/pedri77/Dev/wt/smc-006-t45`: 735 passed. `git diff --stat <base>...HEAD -- tests/golden`: vacío. Worktree limpio.
- Alcance: solo `smc/gap.py` y `tests/test_cli_errores.py`; `superficies.py diff dev-proyecto`: OK. gitleaks: sin fugas; grep de secretos: nada.
- Nota: el cambio en `_heredado` (mismo `in` sobre estado no hashable) no figura en «Hace» pero está en `smc/gap.py` y es el mismo defecto; aceptado.
- Contraprueba (copias `git archive HEAD`, `PYTHONPATH=<copia>`, `smc.__file__` dentro de la copia; `pytest tests/test_cli_errores.py`; copias no borradas):
  - `/var/folders/db/ccfn3h311m941bgd0sggl7v00000gn/T/tmp.Pn2USQXkzQ`: `estado not in VALID_STATES` sin tipo → 6 failed, 33 passed: `test_estado_no_escalar_no_da_traceback[[]-gap]`, `[[]-plan]`, `[{}-gap]`, `[{}-plan]`; `test_gap_estado_no_escalar_avisa_y_cuenta_sin_evaluar[[]]`, `[{}]`.
  - `/var/folders/db/ccfn3h311m941bgd0sggl7v00000gn/T/tmp.Jwyhldw0MH`: `_load` lanza ValueError si no es mapa → 4 failed, 35 passed: `test_yaml_valido_no_mapa_da_rc0_con_aviso[entero]`, `[lista]`, `[texto]`, `[vacio]`.
  - Coinciden con las cifras del agente.
