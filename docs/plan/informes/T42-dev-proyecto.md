# T42 informe (dev-proyecto v1.5)

Rama t42-smc004, commit e7968e4. Ficheros: `smc/gap.py` (+TypeError en la tupla de `_load`), `tests/test_cli_errores.py` (caso `a: !!timestamp {=}` en `MALAS`, id `tag-timestamp-mapa`). No toca cli.py, `_ERRORES_DATOS`, golden, ni el mensaje.

## Verifica
- Antes del cambio: `smc gap` sobre `a: !!timestamp {=}` daba `TypeError: expected string or bytes-like object, got 'list'` (traceback).
- `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: 693 passed (690 + 3 nuevos: gap, plan, gap con -o).
- `git diff --stat -- tests/golden`: vacío.

## Contraprueba
Copia temporal (`git archive HEAD`, con TypeError quitado de la tupla), lanzada desde la copia con `PYTHONPATH=<copia>`. `smc.__file__` impreso: `<copia>/smc/__init__.py` (importa la copia). `pytest tests/test_cli_errores.py`: 3 failed, 25 passed.
Rojos de gap:
- test_fichero_malo_da_error_limpio[tag-timestamp-mapa-gap]
- test_gap_con_salida_no_crea_fichero[tag-timestamp-mapa]
Rojos de plan:
- test_fichero_malo_da_error_limpio[tag-timestamp-mapa-plan]
Los demás casos (tag-timestamp con `abc`, etc.) siguen en verde sin TypeError: solo el caso nuevo cubre este hueco.

## Notas
- Primer intento con `sed -i` de BSD falló sin aplicar nada; rehecho con python. Sin efecto en el commit.
- Queda: nada.

## Verificación del coordinador (coordinador v2.2, 2026-11-05)
- `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en el worktree de la tarea: 693 passed. `git diff --stat -- tests/golden`: vacío. gitleaks: no leaks; grep de secretos: sin coincidencias. Superficie (superficies.py diff dev-proyecto): OK.
- Contraprueba (copia temporal `git archive HEAD`, `PYTHONPATH=<copia>`, lanzada desde la copia, `smc.__file__` = `/private/tmp/t42cp.TI43/smc/__init__.py`): Contraprueba: quitar `TypeError` de la tupla de `_load` → 3 failed, 25 passed en `tests/test_cli_errores.py`.
  - gap: `test_fichero_malo_da_error_limpio[tag-timestamp-mapa-gap]`, `test_gap_con_salida_no_crea_fichero[tag-timestamp-mapa]`
  - plan: `test_fichero_malo_da_error_limpio[tag-timestamp-mapa-plan]`
