# T41 informe (dev-proyecto v1.5)

Rama t41-smc004. Ficheros: `smc/gap.py`, `tests/test_cli_errores.py`. No se tocan `smc/cli.py` ni `tests/golden/`.

## Qué se hizo
- `_load` lee con `read_text` fuera del `try`; el `try` envuelve solo `yaml.safe_load` y convierte `(KeyError, IndexError, AttributeError)` en `ValueError("el YAML no es válido (valor que no cumple su tag explícito)")`, una línea. Así `smc gap` y `smc plan` dan `ERROR: <ruta>: <motivo>` y rc=2.
- Tests: cuatro casos nuevos en `MALAS` (`tag-bool`, `tag-int-vacio`, `tag-float-vacio`, `tag-timestamp`), que cubren gap y plan, y gap con `-o` sin crear fichero. Test nuevo `test_tag_roto_mensaje_una_linea`.

## Verifica
`PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: 690 passed. `git diff` no toca `tests/golden/`.

## Contraprueba (copia temporal de los ficheros versionados, PYTHONPATH a la copia, import comprobado en la copia)
Base: 25 passed en test_cli_errores.py.
- Sin KeyError: 4 failed. `test_fichero_malo_da_error_limpio[tag-bool-gap]`, `[tag-bool-plan]`, `test_gap_con_salida_no_crea_fichero[tag-bool]`, `test_tag_roto_mensaje_una_linea`.
- Sin IndexError: 6 failed. `test_fichero_malo_da_error_limpio[tag-int-vacio-gap|plan]`, `[tag-float-vacio-gap|plan]`, `test_gap_con_salida_no_crea_fichero[tag-int-vacio]`, `[tag-float-vacio]`.
- Sin AttributeError: 3 failed. `test_fichero_malo_da_error_limpio[tag-timestamp-gap|plan]`, `test_gap_con_salida_no_crea_fichero[tag-timestamp]`.
- Sin el `try` (sustituido por `if 1:`): 13 failed, los 4 tags en gap y plan, en `-o` y `test_tag_roto_mensaje_una_linea`.

## Queda
Nada. Los cambios de comportamiento en `evidencias`, `compare` y `soa` (que comparten `_load`) son los decididos por David (05-11).

## Verificación del coordinador (coordinador v2.2, 2026-11-05)
- `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en el worktree de T41: 690 passed.
- Superficie (superficies.py diff dev-proyecto): dentro. Sin `tests/golden/`, `smc/cli.py` ni `_ERRORES_DATOS`; sin `except Exception`; el `try` envuelve solo `yaml.safe_load`. gitleaks y grep de secretos: limpios.
- Contraprueba medida en copias limpias por mutante (git archive de 665a04f en /tmp, `smc.__file__` = copia, mutante aplicado comprobado, PYTHONPATH a la copia):
  - Contraprueba: quitar KeyError → 4 failed (tag-bool-gap, tag-bool-plan, no_crea_fichero[tag-bool], test_tag_roto_mensaje_una_linea); 21 passed.
  - Contraprueba: quitar IndexError → 6 failed (tag-int-vacio y tag-float-vacio en gap y plan, y en no_crea_fichero); 19 passed.
  - Contraprueba: quitar AttributeError → 3 failed (tag-timestamp-gap, -plan, no_crea_fichero[tag-timestamp]); 22 passed.
  - Contraprueba: borrar el try → 13 failed (4 tags x gap/plan, 4 en -o, test_tag_roto_mensaje_una_linea); 12 passed.
  Coincide con el informe del agente.
