# T46 (SMC-007) · informe dev-proyecto v1.5

Rama `t46-smc007` (desde 14e2515). Toca solo `scripts/change_evidence.py`, `tests/test_change_evidence.py` y este informe.

## Qué se hizo
- `latest_check_runs`: por grupo (nombre, app), gana el mayor (`started_at`, `id`) entre los runs con fecha; un run sin fecha solo lo sustituye si su `id` supera al mayor `id` de todos los fechados del grupo (entre varios sin fecha, el de mayor `id`); sin ningún fechado, mayor `id`.
- `cut_at_merge` (nuevo) y `collect_pr`: con `merged_at`, descarta los check-runs con `started_at` estrictamente posterior (igual o sin fecha se quedan; comparación con `datetime`, no de cadenas). Un check (nombre, app) que se queda sin runs sale de `checks` y se anota el hueco `PR #N: el check <nombre> no tenía ningún run al fusionar (merged_at ...)`. Sin `merged_at`, nada cambia.
- `gh_json`: `RETRIES = 2` (3 intentos), `time.sleep(RETRY_DELAY * n)` con `RETRY_DELAY = 1.0`. `http_status` toma el ÚLTIMO `(HTTP nnn)` de stderr; solo 500-599 reintenta. 403, 404, errores sin código o con stderr `None` propagan a la primera. Agotados, se propaga el último error y `collect_pr` lo anota como hueco como hasta ahora.
- Formato `gh` contrastado con los tests existentes (`gh: Server Error (HTTP 502)`, `gh: Not Found (HTTP 404)`): `(HTTP <código>)` al final.
- 26 tests nuevos (761 en total). Ninguno espera tiempo real: `time.sleep` y `run` simulados.

## Test primero
Antes de tocar el script: `17 failed, 69 passed` (salida de la primera ejecución). Ojo: los tests de reintento fallaban en parte por `AttributeError: module 'change_evidence' has no attribute 'time'` (aún no se importaba `time`), no por la lógica. Su valor como detector lo prueban los mutantes de abajo.

## Verifica
`PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` -> `761 passed in 44.69s`.

## Contraprueba
Un mutante por copia en `/private/tmp/claude-501/-Users-pedri77-Dev-Claude-proyectos-Claude/954a23bc-d0e3-4e6f-999b-858a552b0b36/scratchpad/t46/<m>/` (copia del worktree sin `.git`), lanzando `uv run --extra dev pytest -q tests/test_change_evidence.py` desde la copia. Resultado medido, todos en rojo:

| Mutante | Cambio | Rojos | Tests en rojo |
|---|---|---|---|
| m1 | regla de T44 (si falta fecha en alguno, mayor `id`) | 2 (84 verdes) | `test_caso_de_la_issue_run_sin_fecha_ajeno_no_cambia_la_eleccion`, `test_run_sin_fecha_con_id_mayor_que_algunos_pero_no_que_todos_no_gana` |
| m2 | sin fecha gana con `id` mayor que el ganador, no que todos | 1 (85) | `test_run_sin_fecha_con_id_mayor_que_algunos_pero_no_que_todos_no_gana` |
| m3 | sin fecha nunca sustituye a un fechado (`elif False and ...`) | 11 (75) | check_en_curso_sin_started_at (2), fallo_concluido_sin_started_at (2), verde_sin_started_at_con_id_mayor (2), release_fallo_sin_started_at_tras_verde (2), run_sin_fecha_con_id_mayor_que_todos_los_fechados_gana, varios_sin_fecha_con_id_mayor_gana_el_mayor_de_ellos, run_sin_started_at_se_queda_en_pr_fusionado |
| m4 | sin corte por `merged_at` (`if False:`) | 4 (82) | pr_fusionado_la_repeticion_verde_posterior (2), check_solo_posterior_al_merge_sale_de_checks_y_deja_hueco, hueco_por_corte_aparece_en_el_pack_de_release |
| m5 | corte con `>=` (`started < cut`) | 1 (85) | `test_run_iniciado_justo_en_merged_at_se_queda` |
| m6 | sin hueco del check sin runs | 2 (84) | check_solo_posterior_al_merge_sale_de_checks_y_deja_hueco, hueco_por_corte_aparece_en_el_pack_de_release |
| m7 | sin reintento (`RETRIES = 0`) | 4 (82) | 500_y_luego_exito, dos_500_y_luego_exito, tres_500_son_tres_llamadas, tres_500_en_collect_pr_dejan_hueco |
| m8 | reintenta cualquier `CalledProcessError` | 6 (80) | 403_y_404 (3 parámetros), 403_cuyo_mensaje_contiene_http_500, error_sin_codigo_http, error_con_stderr_none |
| m9 | 3 reintentos (4 llamadas) | 2 (84) | tres_500_son_tres_llamadas, tres_500_en_collect_pr_dejan_hueco |
| m10 | 5xx por `"HTTP 500" in stderr` | 3 (83) | dos_500_y_luego_exito (502/503 no se reconocen), tres_500_son_tres_llamadas, 403_cuyo_mensaje_contiene_http_500 |

Salida literal del filtro `grep -E "^FAILED|passed|failed"`, p. ej. m5: `FAILED tests/test_change_evidence.py::test_run_iniciado_justo_en_merged_at_se_queda` / `1 failed, 85 passed in 0.42s`; m2: `1 failed, 85 passed in 0.52s`; m1: `2 failed, 84 passed in 0.47s`; m9: `2 failed, 84 passed in 0.44s`.

Ningún mutante quedó verde. Matiz m3: la lectura estricta de «ignorar del todo los runs sin fecha» (tampoco ganar cuando ninguno tiene fecha) no se midió por separado; el m3 medido deja ganar al sin fecha solo cuando no hay fechados.

## Puntos donde la especificación no encaja del todo (sin decidir)
- Con `merged_at` ilegible, `cut_at_merge` no corta (conserva todo). La spec no lo dice; es el fallo hacia el comportamiento de hoy.
- El hueco se anota por (nombre, app) pero el texto nombra solo el check; si dos apps comparten nombre y solo una queda sin runs, el mensaje es ambiguo.
- El T44 informó «dev-proyecto 1.7»; el fichero del agente en disco declara 1.5, la versión que uso en pies e informe.
- `run()` devuelve stderr solo en `CalledProcessError`; un `gh` que falle sin `(HTTP nnn)` (red caída) no se reintenta, por la spec («otros errores se propagan»).

## Queda
Sincronizar la plantilla `f2p/repo-templates` de enjambre-agentes tras fusionar (fuera de alcance). Sin acción de prod.

## Revisión del coordinador (2026-11-05)
- Alcance: solo los 3 ficheros de «Toca»; superficies.py diff dev-proyecto: OK; gitleaks y grep de secretos: sin hallazgos.
- Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en la rama de tarea: 761 passed.
- Contraprueba (copias limpias con git archive, un mutante por copia, `tests/test_change_evidence.py`, 86 tests): Contraprueba: m1 → 2 rojos; m2 → 1; m3 → 11; m4 → 4; m5 → 1; m6 → 2; m7 → 4; m8 → 6; m9 → 2; m10 → 3 (coincide con lo del agente).
- Lectura estricta de m3 (grupo sin ningún run con fecha se descarta y un run sin fecha nunca gana): 15 rojos, 71 verdes. Añade a los de m3 `test_check_solo_en_segunda_pagina_de_check_runs`, `test_justo_en_el_tope_con_pagina_corta_no_es_hueco`, `test_si_ninguno_tiene_fecha_gana_el_mayor_id` y `test_run_sin_fecha_de_otro_grupo_no_afecta`.
- merged_at ilegible o ausente: una sola rama, sin corte (`cut_at_merge` devuelve los runs). Hueco por corte sin app: con dos apps del mismo nombre y una sin runs tras el corte, el hueco nombra el check aunque la otra app se conserve: ambiguo, no falso.
