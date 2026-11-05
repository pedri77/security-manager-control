# T44 (SMC-005) · informe dev-proyecto v1.7 (corrección tras devolución)

Rama `t44-smc005`. Toca solo `scripts/change_evidence.py`, `tests/test_change_evidence.py` y este informe. Fusionada antes la rama base `fix/SMC-005-huecos-evidencias` (PLAN.md al día).

## Qué se hizo
- `latest_check_runs` agrupa por (nombre, app) y decide viendo el grupo entero: si todos los runs tienen `started_at`, gana el mayor (`started_at`, `id`); si alguno no lo tiene, gana el mayor `id`. Se quita `_run_order` y su centinela. Motivo de la devolución: con el centinela un `success` sin `started_at` e id 1 ganaba a un `failure` con `started_at` e id 2 (fallo en abierto).
- Tests (cada uno con los dos órdenes de lista):
  - Sustituido `test_verde_concluido_sin_started_at_supera_al_fallo` por `test_verde_sin_started_at_e_id_1_no_tapa_fallo_con_started_at_e_id_2` (gana el fallo).
  - Mantenido `test_fallo_concluido_sin_started_at_supera_al_verde` (fallo sin `started_at`, id mayor, frente a verde: gana el fallo).
  - Nuevos: `test_verde_sin_started_at_con_id_mayor_supera_al_fallo_anterior` (gana el verde) y `test_run_en_cola_antiguo_con_id_menor_no_tapa_al_verde_mas_nuevo` (gana el verde).
  - Mantenido `test_check_en_curso_sin_started_at_supera_al_verde` (id 2 en curso sin `started_at` frente a verde id 1: gana el check en curso).
  - Revisados los demás tests de `started_at`: los ids son coherentes con el orden real (mayor id = más nuevo, salvo `test_started_at_manda_sobre_id`, que invierte a propósito id y fecha y todos los runs tienen `started_at`). Ninguna aserción relajada.
- Siguen los tests de `mode_release` del primer envío (fallo superado por verde, verde superado por fallo, fallo sin `started_at` tras verde).

## Verifica
- `uv run --extra dev pytest -q tests/test_change_evidence.py`: `60 passed in 0.12s`
- `make test`: `724 passed in 44.40s`

## Contraprueba (un mutante por copia en `$SB/<nombre>`, con `scripts/` y `tests/` del worktree)
`$SB` = `/private/tmp/claude-501/-Users-pedri77-Dev-Claude-proyectos-Claude/954a23bc-d0e3-4e6f-999b-858a552b0b36/scratchpad/t44b`. Salida literal del filtro `grep -E "^FAILED|passed|failed|error"` (las líneas `ce = <module ...>` son ruido del traceback que el filtro dejó pasar; se conservan tal cual en el primero).

Mutante 1, `failed = []` en `mode_release` (diff: línea 361):
```
ce = <module 'change_evidence' from '.../t44b/failed/scripts/change_evidence.py'>   (x4)
FAILED tests/test_change_evidence.py::test_release_verde_superado_por_fallo_deja_hueco_de_checks[nuevo_primero]
FAILED tests/test_change_evidence.py::test_release_verde_superado_por_fallo_deja_hueco_de_checks[viejo_primero]
FAILED tests/test_change_evidence.py::test_release_fallo_sin_started_at_tras_verde_deja_hueco[nuevo_primero]
FAILED tests/test_change_evidence.py::test_release_fallo_sin_started_at_tras_verde_deja_hueco[viejo_primero]
4 failed, 56 passed in 0.15s
```
Mutante 2, quitar el `gaps.append` de «checks no exitosos» (sustituido por `pass`, línea 370):
```
FAILED tests/test_change_evidence.py::test_release_verde_superado_por_fallo_deja_hueco_de_checks[nuevo_primero]
FAILED tests/test_change_evidence.py::test_release_verde_superado_por_fallo_deja_hueco_de_checks[viejo_primero]
FAILED tests/test_change_evidence.py::test_release_fallo_sin_started_at_tras_verde_deja_hueco[nuevo_primero]
FAILED tests/test_change_evidence.py::test_release_fallo_sin_started_at_tras_verde_deja_hueco[viejo_primero]
4 failed, 56 passed in 0.14s
```
Mutante 3, centinela (`started_at or "￿"`, el código anterior) en vez de decidir por `id` cuando falta `started_at`:
```
FAILED tests/test_change_evidence.py::test_verde_sin_started_at_e_id_1_no_tapa_fallo_con_started_at_e_id_2[nuevo_primero]
FAILED tests/test_change_evidence.py::test_verde_sin_started_at_e_id_1_no_tapa_fallo_con_started_at_e_id_2[viejo_primero]
FAILED tests/test_change_evidence.py::test_run_en_cola_antiguo_con_id_menor_no_tapa_al_verde_mas_nuevo[nuevo_primero]
FAILED tests/test_change_evidence.py::test_run_en_cola_antiguo_con_id_menor_no_tapa_al_verde_mas_nuevo[viejo_primero]
4 failed, 56 passed in 0.23s
```
Mutante 4, comparar siempre solo por `id`:
```
FAILED tests/test_change_evidence.py::test_started_at_manda_sobre_id - Assert...
1 failed, 59 passed in 0.12s
```
Los cuatro ponen en rojo al menos un test. Mutante «solo por `started_at`»: no medido (no está en el Verifica).

## Barrido de entradas malas (sobre `latest_check_runs`, medido)
- `[{"name":"a"}]`, `started_at` vacío, `id` None, lista vacía: sin excepción.
- Run sin `name`: `KeyError 'name'` (ya existía con `r["name"]`; la API siempre lo da; fuera de alcance, no cambiado).
- `started_at` int mezclado con str: `TypeError`. No ocurre con la API (siempre str ISO); fuera de alcance.
- Ficheros no se leen aquí: binario, directorio, vacío, inexistente: no aplica.

## Desvíos / decisiones
- Ninguno respecto a la petición. Se elimina el desvío anterior (un run sin `started_at` ya no cuenta como el más reciente por serlo).
- Prod: ninguna. Sin push, sin tocar PLAN.md ni `main`.

## Verificación del coordinador (2026-11-05, coordinador v2.3)
- `pytest -q tests/test_change_evidence.py`: 60 passed. `make test`: 724 passed.
- Casos sobre `latest_check_runs` (mismo nombre y app, todas las permutaciones): A (success sin started_at id1, failure con id2) gana el fallo; B (failure sin started_at id2, success con id1) gana el fallo; C (success con id1, success sin id2, failure con id3) gana el fallo id3.
- Mutantes, uno por copia en scratchpad/c44 (m1..m4, m3b), módulo importado de la copia: m1 `failed = []` = 4 rojos; m2 sin `gaps.append` de checks = 4 rojos; m4 solo por `id` (rama `if False`) = 1 rojo (`test_started_at_manda_sobre_id`); m3 centinela (`started_at or "￿"/""` según concluido, el código anterior) = 8 rojos, no los 4 del informe de arriba (el mutante del informe no coincide con el que repite el coordinador; ambos en rojo).
