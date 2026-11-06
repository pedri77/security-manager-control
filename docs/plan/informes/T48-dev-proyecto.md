# T48 (SMC-007, issue #21): reintentar el 5xx de cuerpo vacío que `gh` no identifica

Agente: dev-proyecto v1.5 · rama `t48-smc007` (sale de 6a8a4bc).

## Qué se hizo
`gh_json` reintenta (2 reintentos, misma espera que un 5xx) cuando el `CalledProcessError` no trae código de estado y su stderr tiene una línea que es exactamente `unexpected end of JSON input`. Nueva función `is_transient(e)`: si `http_status` da código, manda el código (5xx sí, resto no); si no da código, comprueba la línea exacta con `splitlines()`. Agotados los reintentos se propaga el error. Constante `EMPTY_BODY_LINE`. Ficheros: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, este informe.

## Prueba con `gh` real (gh 2.89.0, servidor local 127.0.0.1:18778, en `.../scratchpad/t48/`, fuera del worktree y de la suite)
Peticiones contadas en el servidor (servidor reiniciado antes de cada serie). `time.sleep` anulado.

| Caso | Antes | Después | stderr real |
|---|---|---|---|
| 500 vacío, application/json | 1 | 3 | `unexpected end of JSON input` |
| 502 vacío, application/json | 1 | 3 | ídem |
| 504 vacío, application/json | 1 | 3 | ídem |
| 500 JSON con message (T47) | 3 | 3 | `gh: Server Error (HTTP 500)` |
| 502 HTML (T47) | 3 | 3 | `gh: HTTP 502` |
| 504 vacío text/plain (T47) | 3 | 3 | `gh: HTTP 504` |
| 403 JSON con message | 1 | 1 | `gh: Server Error (HTTP 403)` |
| 404 JSON con message | 1 | 1 | `gh: Server Error (HTTP 404)` |
| 403 vacío application/json | 1 | 3 | `unexpected end of JSON input` (aceptado por la spec) |
| 404 vacío application/json | 1 | 3 | ídem (aceptado) |
| 403 con cuerpo `{"message":"unexpected end of JSON input"}` | 1 | 1 | `gh: unexpected end of JSON input (HTTP 403)` |

Código de salida de `gh` en el caso de cuerpo vacío: 1 (comprobado a mano y en `e.returncode`). La especificación encaja.

## TDD
Tests antes del código: 7 en rojo, 801 en verde. Después: **808 passed** (787 + 21 nuevos casos en 10 tests).

Tests nuevos (todos `tests/test_change_evidence.py`): `test_cuerpo_vacio_json_se_reintenta_hasta_tres_llamadas` (2), `test_cuerpo_vacio_json_y_luego_exito`, `test_cuerpo_vacio_json_dos_veces_y_luego_exito`, `test_cuerpo_vacio_json_mezclado_con_5xx_con_codigo`, `test_con_codigo_no_5xx_y_cita_del_texto_falla_a_la_primera` (4), `test_http_status_reconoce_el_codigo_cuando_el_cuerpo_cita_el_texto` (2), `test_otros_textos_no_se_reintentan` (7), `test_linea_exacta_entre_otras_lineas_se_reintenta`, `test_json_loads_que_falla_sobre_salida_correcta_no_se_reintenta`, `test_cuerpo_vacio_json_en_collect_pr_deja_hueco_tras_tres_llamadas`.

## Contraprueba (copias temporales fuera del worktree, una por mutante, pytest lanzado desde la copia, `tests/test_change_evidence.py`, 133 tests)
| Mutante | Rojos | Tests |
|---|---|---|
| m1 quitar el reconocimiento (`return False`) | 7 | los 2 `cuerpo_vacio_json_se_reintenta_hasta_tres_llamadas`, `_y_luego_exito`, `_dos_veces_y_luego_exito`, `_mezclado_con_5xx_con_codigo`, `linea_exacta_entre_otras_lineas`, `collect_pr_deja_hueco` |
| m2 subcadena en vez de línea exacta | 4 | `otros_textos_no_se_reintentan` con `error: ...`, `gh: ... input.`, `... input extra`, `x unexpected...` |
| m3 reintentar cualquier `CalledProcessError` | 20 | 403/404/410, 403 con HTTP 500 citado, sin código, stderr None, 404/403 sin paréntesis, dos códigos, `con_codigo_no_5xx_y_cita...` (4), `otros_textos...` (7) |
| m4 no propagar al agotar (`return None`) | 10 | `tres_500...`, `tres_500_en_collect_pr`, 4 de `5xx_sin_parentesis`, `502_..._collect_pr`, 2 de `cuerpo_vacio..._tres_llamadas`, `cuerpo_vacio_..._collect_pr` |

Ninguno verde.

## Puntos donde la especificación no encaja con `gh` real
Ninguno. Matices: con cuerpo no vacío `{"message":"unexpected end of JSON input"}` `gh` escribe `gh: unexpected end of JSON input (HTTP 403)`, y el código manda (1 petición), como pide la spec. El 403/404 con cuerpo vacío y JSON sí se reintenta (3), aceptado por la spec. Un stderr con la línea exacta y además código no 5xx en otra línea: manda el código.

## Revisión del coordinador (2026-11-05)
- Alcance: solo los 3 ficheros de «Toca»; superficies.py diff dev-proyecto OK; gitleaks sin hallazgos.
- Verifica: pytest completo 808 passed.
- `gh` 2.89.0 real, servidor local propio (peticiones contadas): 500, 502 y 504 vacíos con application/json = 3 cada uno (stderr `unexpected end of JSON input`); casos de T47 (500 JSON, 500 `{}`, 502/503 HTML, 504 text/plain) = 3; 403 y 404 con cuerpo no vacío y 403 HTML/JSON, 404 HTML/JSON = 1; 403 con `{"message":"unexpected end of JSON input"}` = 1 (`gh: unexpected end of JSON input (HTTP 403)`). Un 403 vacío con application/json = 3 (aceptado en la spec). Los stderr simulados coinciden con los reales. Montaje en /../t47/.
- Contraprueba (copias limpias con git archive, un mutante por copia, 133 tests): m1 → 7 rojos; m2 → 4; m3 → 20; m4 → 10 (coincide con el agente). Copias en /.
