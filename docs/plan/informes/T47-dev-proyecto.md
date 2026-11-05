# T47 (SMC-007, issue #21): FAIL de revisión ciega del PR #24

Agente: dev-proyecto v1.5 · rama `t47-smc007` (sale de f89e276).

## Qué se hizo
`http_status` solo reconocía `(HTTP 502)`. `gh` 2.89.0 escribe `gh: HTTP 502` (sin paréntesis, línea propia) cuando el cuerpo no es JSON con `message`. Ahora `HTTP_STATUS_RE` reconoce ambas formas (`\(HTTP (\d{3})\)` y `^gh: HTTP (\d{3})[ \t]*$` en multilínea), cuenta la última aparición y la docstring describe los dos formatos. El segundo patrón va anclado a línea: un mensaje que cita «HTTP 500» en medio no cuenta.

Ficheros: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, este informe. Nada más.

## Prueba con `gh` real (gh 2.89.0, servidor local en 127.0.0.1:18770, fuera del worktree y de la suite)
Montaje en el scratchpad `t47/` (`srv.py` cuenta peticiones en un fichero; `e2e.py` llama a `gh_json` con `time.sleep` anulado). Peticiones contadas en el servidor.

| Caso | Antes del fix | Después del fix | stderr real |
|---|---|---|---|
| 500 JSON con message | 3 | 3 | `gh: Server Error (HTTP 500)` |
| 500 JSON `{}` sin message | 1 | 3 | `gh: HTTP 500` |
| 502 HTML | 1 | 3 | `gh: HTTP 502` |
| 503 HTML | 1 | 3 | `gh: HTTP 503` |
| 504 vacío | 1 | 3 | `gh: HTTP 504` |
| 403 JSON con message | 1 | 1 | `gh: Server Error (HTTP 403)` |
| 403 HTML | 1 | 1 | `gh: HTTP 403` |
| 404 JSON con message | 1 | 1 | `gh: Server Error (HTTP 404)` |
| 404 HTML | 1 | 1 | `gh: HTTP 404` |

El «antes» reproduce el fallo del PR #24 (502, 503, 504 y 500 sin message no se reintentaban).

## TDD
Tests escritos primero: con el código anterior, 15 en rojo y 772 en verde (los de huso y de apps homónimas ya pasaban: el código era correcto y quedan como guarda de los mutantes). Después del fix: **787 passed** (761 de T46 + 26 nuevos).

Tests nuevos (stderr copiado textualmente de gh real):
- `test_http_status_reconoce_los_dos_formatos_de_gh` (9 casos)
- `test_5xx_sin_parentesis_se_reintenta_hasta_tres_llamadas` (500, 502, 503, 504)
- `test_502_sin_parentesis_y_luego_exito`, `test_503_sin_parentesis_y_luego_502_y_exito`
- `test_404_y_403_sin_parentesis_fallan_a_la_primera` (2)
- `test_dos_codigos_en_stderr_cuenta_el_ultimo`, `test_dos_codigos_el_ultimo_404_no_se_reintenta_aunque_el_primero_sea_5xx`, `test_dos_codigos_el_ultimo_5xx_se_reintenta_aunque_el_primero_sea_404`
- `test_502_sin_parentesis_en_collect_pr_deja_hueco_tras_tres_llamadas`
- `test_corte_con_merged_at_en_otro_huso_cuenta_el_instante`, `test_corte_con_started_at_en_otro_huso_cuenta_el_instante`, `test_corte_en_otro_huso_igual_al_merged_at_se_queda`
- `test_dos_apps_homonimas_solo_la_que_se_queda_sin_runs_deja_hueco`, `test_dos_apps_homonimas_ambas_con_runs_previos_no_dejan_hueco`

## Contraprueba (5 mutantes, una copia temporal cada uno fuera del worktree, pytest lanzado desde la copia, `tests/test_change_evidence.py`, 112 tests)
| Mutante | Rojos | Tests |
|---|---|---|
| m1 volver a `r"\(HTTP (\d{3})\)"` | 15 | los 6 `http_status` sin paréntesis, los 4 `5xx_sin_parentesis`, `502_..._y_luego_exito`, `503_..._502_y_exito`, `dos_codigos_en_stderr_cuenta_el_ultimo`, `dos_codigos_el_ultimo_5xx_...`, `502_..._collect_pr` |
| m2 primera aparición (`found[0]`) | 3 | `dos_codigos_en_stderr_cuenta_el_ultimo`, `dos_codigos_el_ultimo_404_...`, `dos_codigos_el_ultimo_5xx_...` |
| m3 corte comparado como texto | 3 | los 3 de huso |
| m4 `_utc` sin zona (ignora el offset) | 3 | los 3 de huso |
| m5 clave de runs sin app | 1 | `dos_apps_homonimas_solo_la_que_se_queda_sin_runs_deja_hueco` |

Ninguno verde. m5 solo lo caza un test; `..._ambas_con_runs_previos_...` es el caso complementario.

## Puntos donde la especificación no encaja con `gh` real
- «500 con JSON»: solo da `(HTTP 500)` si el JSON trae `message`; con `{}` da `gh: HTTP 500`. Probados ambos.
- Con cuerpo JSON con `message`, el texto antes del paréntesis es el `message` del cuerpo, no la frase HTTP.
- Fuera de alcance, sin tocar: `collect_pr` (línea ~211) decide el 404 de la rama base con `"HTTP 404" in stderr`, número suelto. Con el formato nuevo `gh: HTTP 404` funciona, pero un 403 que cite «HTTP 404» se tomaría por 404. Candidato a tarea aparte usando `http_status`.
- Los checks proyectados en `collect_pr` no llevan `app`, así que el test de apps homónimas comprueba conclusiones, no ids de app.

## Revisión del coordinador (2026-11-05)
- Alcance: solo los 3 ficheros de «Toca»; superficies.py diff dev-proyecto OK; gitleaks sin hallazgos.
- Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: 787 passed.
- `gh` 2.89.0 real contra servidor local propio (`/private/tmp/claude-501/-Users-pedri77-Dev-Claude-proyectos-Claude/954a23bc-d0e3-4e6f-999b-858a552b0b36/scratchpad/t47/srv.py` y `e2e.py`, peticiones contadas en el servidor): 500 JSON con message 3; 500 `{}` 3; 502 HTML 3; 503 HTML 3; 504 vacío (text/plain) 3; 403 JSON/HTML 1; 404 JSON/HTML 1. Matiz: un 504 vacío servido como `application/json` da `unexpected end of JSON input` sin código y 1 petición; no es una respuesta realista de GitHub y queda fuera de la spec.
- stderr real medido: `gh: Server Error (HTTP 500)`, `gh: HTTP 500|502|503|504|403|404`; coinciden con los de los tests (`tests/test_change_evidence.py` líneas 635-645).
- Contraprueba (copias limpias con git archive, un mutante por copia): m1 → 15 rojos; m2 → 3; m3 → 3; m4 → 3; m5 → 1 (112 tests; coincide con el agente). Copias en /private/tmp/claude-501/-Users-pedri77-Dev-Claude-proyectos-Claude/954a23bc-d0e3-4e6f-999b-858a552b0b36/scratchpad/t47/.
- `"HTTP 404" in stderr` de `is_release_pr`/`collect_pr`: fuera de T47, sin tocar.
