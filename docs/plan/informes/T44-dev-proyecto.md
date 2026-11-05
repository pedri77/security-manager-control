# T44 (SMC-005) · informe dev-proyecto v1.7

Rama `t44-smc005`. Toca solo `scripts/change_evidence.py`, `tests/test_change_evidence.py` y este informe.

## Qué se hizo
- `_run_order` (`latest_check_runs`): un run sin `started_at` cuenta como el más reciente, esté en curso o ya concluido (antes solo si no tenía `conclusion`). Docstring ajustado. Consecuencia simétrica: un verde concluido sin `started_at` también supera a un fallo anterior.
- 8 tests nuevos (10 casos con los dos órdenes de lista):
  - `test_fallo_concluido_sin_started_at_supera_al_verde` y `test_verde_concluido_sin_started_at_supera_al_fallo` (x2 órdenes).
  - `mode_release` con `FakeGh` (huecos filtrados por «checks no exitosos»): `test_release_fallo_superado_por_verde_no_deja_hueco_de_checks` (caso real PR #11: falló y se relanzó en verde; comprueba `gaps` vacío y `ci_status` ✅), `test_release_verde_superado_por_fallo_deja_hueco_de_checks` (hueco exacto `PR #7 con checks no exitosos: ci`, `ci_status` ❌ ci), `test_release_fallo_sin_started_at_tras_verde_deja_hueco` (x2 órdenes cada uno).

## Test primero (antes del arreglo, medido)
`6 failed, 50 passed`: los 2 de fallo concluido sin started_at, los 2 de verde concluido sin started_at y los 2 de release con fallo sin started_at (los `[nuevo_primero]` y `[viejo_primero]` de cada uno). Los tests de release con started_at pasaban ya (el código de `mode_release` era correcto; faltaba cobertura).

## Verifica (tras el arreglo)
- `uv run --extra dev pytest -q tests/test_change_evidence.py`: `56 passed in 0.08s`
- `make test`: `720 passed in 43.55s`

## Contraprueba (un mutante por copia temporal en `.mut/<nombre>`, ya borrada; script en el scratchpad; pytest con la venv del worktree)
Salida literal (el filtro de mi script también imprimía 4 líneas `ce = <module ...>` del traceback, omitidas aquí por ser ruido):

Mutante `failed = []` en `mode_release`:
```
FAILED test_release_verde_superado_por_fallo_deja_hueco_de_checks[nuevo_primero]
FAILED test_release_verde_superado_por_fallo_deja_hueco_de_checks[viejo_primero]
FAILED test_release_fallo_sin_started_at_tras_verde_deja_hueco[nuevo_primero]
FAILED test_release_fallo_sin_started_at_tras_verde_deja_hueco[viejo_primero]
4 failed, 52 passed in 0.24s
```
Mutante: quitar el `gaps.append` de «checks no exitosos» (sustituido por `pass`):
```
FAILED test_release_verde_superado_por_fallo_deja_hueco_de_checks[nuevo_primero]
FAILED test_release_verde_superado_por_fallo_deja_hueco_de_checks[viejo_primero]
FAILED test_release_fallo_sin_started_at_tras_verde_deja_hueco[nuevo_primero]
FAILED test_release_fallo_sin_started_at_tras_verde_deja_hueco[viejo_primero]
4 failed, 52 passed in 0.14s
```
Mutante: centinela solo a runs en curso (`... or ("￿" if not r.get("conclusion") else "")`):
```
FAILED test_fallo_concluido_sin_started_at_supera_al_verde[nuevo_primero]
FAILED test_fallo_concluido_sin_started_at_supera_al_verde[viejo_primero]
FAILED test_verde_concluido_sin_started_at_supera_al_fallo[nuevo_primero]
FAILED test_verde_concluido_sin_started_at_supera_al_fallo[viejo_primero]
FAILED test_release_fallo_sin_started_at_tras_verde_deja_hueco[nuevo_primero]
FAILED test_release_fallo_sin_started_at_tras_verde_deja_hueco[viejo_primero]
6 failed, 50 passed in 0.26s
```
Los tres ponen en rojo al menos un test. Los mutantes de `failed` los matan los tests de release con fallo; el test de «fallo superado por verde» es el contrapeso (mutar a hueco siempre lo pondría en rojo, no medido).

## Barrido de entradas malas
No aplica: no se toca lectura de ficheros. Sí tocado: el orden de check-runs de la API; `started_at` ausente o `None` cubierto, `id` ausente ya cubierto por el `or 0` existente (no medido con test nuevo).

## Desvíos / decisiones
- Un verde concluido sin `started_at` ahora supera a un fallo anterior (simetría de la regla pedida); test propio.
- La copia temporal no lleva `pyproject.toml` (el build del paquete fallaba en la copia); el test solo usa el script, así que mide lo mismo.
- Prod: ninguna. Sin push, sin tocar PLAN.md.
