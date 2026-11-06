# T50 (SMC-008, issue #25): estado HTTP real con `gh api -i` y casos límite del corte en `merged_at`

Rama `t50-smc008` (sale de afccb41). Agente dev-proyecto v1.5. Ficheros: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, este informe.

## Medido antes de escribir código (`gh` 2.89.0, servidor local y GitHub real)

| Pregunta | Medida |
|---|---|
| Separadores en bytes | Línea de estado acabada en `\n`; cada cabecera en `\r\n`; cabeceras y cuerpo separados por `\r\n\r\n`. Igual con el servidor local (`HTTP/1.1`) y con GitHub real (`HTTP/2.0`). |
| ¿`text=True` conserva `\r`? | No. Traduce todo `\r\n` a `\n`: el separador que ve el script es `\n\n`. |
| Cuerpo vacío | La salida acaba en `\n\n` (cabeceras + línea en blanco). `run()` hace `.strip()` y la deja SIN separador (`...Server: x` y nada más). El código lo tolera: sin `\n\n` el cuerpo es `""`. |
| Fallo (código >= 400) | rc=1; la línea de estado y el cuerpo van a stdout; `CalledProcessError.stdout` y `.output` traen la salida sin `strip`. |
| Cuerpo ilegible como JSON | `gh` no vuelve a escribir el cuerpo en stdout (queda vacío): truncado, solo espacios, no JSON y vacío con Content-Type JSON. stderr: `unexpected end of JSON input` (vacío, truncado, espacios) o `invalid character 'o' in literal null (expecting 'u')` (no JSON). Sin código en ningún caso. La línea de estado de stdout sí está en las 45 celdas. |
| Bloques de cabeceras | Siempre uno. Probado un `100 Continue` previo y una redirección 302: `gh` imprime solo el bloque final. |
| Fallo de red (conexión rechazada) | rc=1, stdout vacío, stderr `Get "http://127.0.0.1:1/refused": dial tcp ...: connection refused`. Sin línea de estado: no se reintenta. |
| 200 con paginación | La cabecera `Link` va en las cabeceras; el cuerpo es solo la página. `gh_pages` sigue igual. |

Cómo encaja con la especificación: todo encaja. Un ajuste de redacción: el mutante «partir por `\n\n` si `gh` usa `\r\n`, o al revés» se aplica en el sentido real. Como `text=True` ya dejó `\n\n`, el código parte por `\n\n` y el mutante parte por `\r\n\r\n`.

`check_runs`: medido con GET real en `cli/cli` (este repo no tiene repeticiones: 15 runs = 15 en `latest` y `all`). En un commit con 19 suites del mismo nombre y la misma app, `filter=all` da 19 y el `latest` por defecto también 19. Es decir, el último es por (nombre, check suite), no por (nombre, app). El simulador agrupa así.

## Cambios en `scripts/change_evidence.py`

1. `gh_json` llama a `gh api -i`. `split_response` saca (estado, cuerpo) de la salida: el estado es el de la primera línea (`HTTP/<v> NNN`), el cuerpo lo que sigue al primer `\n\n`. `http_status(e)` lee `e.stdout`. Quitados `HTTP_STATUS_RE` y `EMPTY_BODY_LINE`. `is_transient`: 5xx y nada más. Un 403/404 falla a la primera con cualquier cuerpo, y sin línea de estado (red) tampoco se reintenta.
2. `allowed_release_files`: `http_status(e) == 404`.
3. `cut_at_merge(runs, merged_at, problems=None)`: la fecha del run es `started_at`; sin ella, `completed_at`; sin ninguna, el run se queda. Igual a `merged_at` se queda.
4. Fecha ilegible (`merged_at`, `started_at` o `completed_at`): el run se queda y la causa se anota en `problems`; `collect_pr` la convierte en hueco con `PR #n:`. `started_at` ilegible no cae a `completed_at`.
5. `status_at_merge` (nuevo): quita los `blind-review` con `created_at > merged_at`. Sin `merged_at`, nada cambia.
6. Comentario de `collect_pr` y docstring del módulo actualizados.

Decisiones mías donde la especificación no dice (revisar):
- Un `blind-review` con `created_at` ilegible cuenta y deja hueco (`PR #n: el estado blind-review tiene created_at ilegible`). La especificación solo pide el hueco para el corte de checks. Sigue el mismo criterio de fallar en abierto con aviso. Si no se quiere, se quita `status_at_merge` el `problems.append` (mutante x2).
- Con `merged_at` ilegible el hueco sale una sola vez (de `cut_at_merge`); los estados tampoco se cortan y no lo repiten.
- `cut_at_merge` gana un tercer parámetro opcional; sus llamadas antiguas siguen valiendo.
- Un `blind-review` posterior al merge se descarta sin hueco propio: si era el único, el registro queda `blind_review: null` y en release sale el hueco de hoy (`PR #n sin revisión ciega correcta (estado: —)`). En modo `pr` no sale hueco. Se podría anotar el descarte; no lo pide T50.

## Tests

`PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: **981 passed** (antes 816 en T49). `tests/test_change_evidence.py`: 306 tests (124 funciones; antes 91).

Rojo antes del arreglo: con los tests nuevos y el script de afccb41, `tests/test_change_evidence.py` dio **99 failed, 206 passed** (305 tests). Tras el arreglo, todo verde.

Los stderr simulados de T47 y T48 se sustituyeron por salidas de `gh api -i` construidas con los valores medidos (`CUERPOS`, `gh_i`, `fallo`, `fallo_red`; la salida de GitHub real con `HTTP/2.0` va literal recortada). Además un `gh` falso (ejecutable en el PATH) imprime los bytes con `\r\n` y cuenta llamadas: ejercita la traducción de `text=True` de verdad.

Tests por criterio (nombres):
- Estado y reintento: `test_5xx_se_reintenta_sea_cual_sea_el_cuerpo` (27), `test_403_y_404_fallan_a_la_primera_sea_cual_sea_el_cuerpo` (18), `test_http_status_lee_la_linea_de_estado_con_cualquier_cuerpo` (45), `test_matriz_con_gh_falso_5xx_tres_peticiones_403_y_404_una` (45), `test_200_*` (lista, objeto, `check_runs`, `Link`), `test_gh_json_llama_a_gh_api_con_i`, `test_el_estado_de_stdout_manda_sobre_el_de_stderr`, `test_stderr_con_5xx_pero_sin_linea_de_estado_no_se_reintenta`, `test_sin_linea_de_estado_fallo_de_red_no_se_reintenta`, `test_403_que_cita_http_500_en_su_mensaje_falla_a_la_primera`, `test_404_con_stderr_de_cuerpo_vacio_falla_a_la_primera`, `test_http_status_solo_lee_la_primera_linea_de_stdout`.
- 404 de `allowed_release_files`: `test_config_ausente_404_con_cualquier_cuerpo_deja_los_ficheros_fijos` (9), `test_403_cuyo_mensaje_cita_http_404_no_es_config_ausente`, `test_stderr_con_http_404_*`.
- `completed_at`: `test_run_sin_started_at_completado_tras_el_merge_no_sustituye_al_que_habia`, `..._antes_del_merge_se_queda`, `..._justo_en_merged_at_se_queda`, `test_run_sin_ninguna_fecha_se_queda`, `test_started_at_manda_sobre_completed_at`, `test_started_at_posterior_manda_sobre_completed_at_anterior`, `test_check_cuyo_unico_run_sin_started_at_acabo_tras_el_merge_sale_y_deja_hueco`.
- Fecha ilegible: `test_started_at_ilegible_deja_hueco_*`, `test_completed_at_ilegible_*`, `test_started_at_ilegible_no_cae_a_completed_at`, `test_merged_at_ilegible_*`, `test_cut_at_merge_con_fecha_que_no_es_texto_deja_hueco_y_se_queda` (ramas `ValueError` y `AttributeError` de `_utc`), `test_hueco_de_fecha_ilegible_aparece_en_el_pack_de_release`.
- `blind-review`: `test_blind_review_publicado_tras_el_merge_no_sustituye_al_previo`, `..._solo_posterior_al_merge_no_cuenta`, `..._justo_en_merged_at_cuenta`, `..._un_segundo_despues_no_cuenta`, `..._sin_fusionar_el_posterior_gana`, `..._otro_huso_cuenta_el_instante`, `test_blind_review_con_created_at_ilegible_cuenta_y_deja_hueco`, `test_release_con_blind_review_solo_posterior_al_merge_sale_en_el_hueco_de_hoy`.
- Simulador por check suite: `test_simulador_sin_filter_all_sirve_el_ultimo_run_por_check_suite`, `test_simulador_dos_suites_de_la_misma_app_con_el_mismo_nombre_se_quedan_las_dos`.

## Matriz con `gh` real contra servidor local (peticiones contadas en el servidor)

Servidor `http.server` en 127.0.0.1:18778, `GH_TOKEN` ficticio, `gh_json` real del script de la rama. Cada celda es el número de peticiones que recibió el servidor. Esperado: 5xx = 3, 403 y 404 = 1.

| estado | `message` | `{}` | `{"errors":[]}` | HTML | vacío text/plain | vacío JSON | no JSON (CT JSON) | JSON truncado | solo espacios |
|---|---|---|---|---|---|---|---|---|---|
| 500 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| 502 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| 503 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| 403 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 404 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

45 de 45 celdas como se pide. Con el script de afccb41 (stderr) la misma matriz da 9 celdas mal: 5xx con cuerpo no JSON = 1 (sin código), y 403/404 con vacío JSON, truncado y espacios = 3 (el hueco que T48 aceptaba).

200: objeto `{"x":1}` y lista de 2 elementos, 1 petición y JSON correcto. Con paginación (`gh_pages`, 101 elementos con cabecera `Link`): lista = 2 peticiones y 101 elementos, objeto `check_runs` = 2 peticiones y 101 elementos.

Montaje: `/private/tmp/claude-501/-Users-pedri77-Dev-Claude-proyectos-Claude/954a23bc-d0e3-4e6f-999b-858a552b0b36/scratchpad/t50/` (`srv.py`, `matriz.py`), fuera del worktree.

## GitHub real, solo GET: rama frente a `origin/main`

`scripts/change_evidence.py pr --pr N` con `GITHUB_REPOSITORY=pedri77/security-manager-control`, para N = 10..24, con el script de la rama y con el de `origin/main` (0961722; su script es idéntico al de afccb41). Salida en `.../scratchpad/t50/real/{rama,main}/`. No se escribió nada en GitHub.

- PR fusionados (9): #10, #11, #15, #16, #19, #20, #22, #23, #24. En los 9, `change-record.json` es idéntico entre rama y main salvo `generated_at`: **diferencia de `checks` = ninguna, de `gaps` = ninguna (0 en ambos), de `blind_review` = ninguna (`success` en ambos)**.
- #12, #13, #14, #17, #18, #21 no son PR (son issues): `pulls/N` da 404 y ambas versiones terminan igual con `CalledProcessError` (rc=1, sin registro). El 404 real también pasa por la línea `HTTP/2.0 404 Not Found` sin diferencia.
- No hay hallazgo de `blind-review` posterior al merge: en los 9 el `success` se publicó entre 3 y 43 segundos antes de `merged_at`. Tampoco hay ningún run iniciado tras el merge.
- Observación fuera de alcance (no es diferencia entre versiones): #10 tiene 15 runs y 13 checks en el registro, porque `change-record` y `pr-title` corrieron en 2 check suites y `latest_check_runs` deja uno por (nombre, app). Coincide con la nota de la issue sobre `latest_check_runs`, que T50 no toca.

Por qué no hay diferencias: ninguno de los 9 PR tiene runs sin `started_at`, ni fechas ilegibles, ni `blind-review` tras el merge; los cambios de T50 solo actúan en esos casos, y el parseo con `-i` devuelve el mismo JSON.

## Contraprueba: mutantes en copias fuera del worktree

Un mutante por copia, en `.../scratchpad/t50/mut/<id>/`, lanzando `uv run --extra dev pytest -q tests/test_change_evidence.py` desde la copia (306 tests). Script: `mutantes.py`; salida: `mutantes.out`.

| Mutante | Resultado | Tests distintos en rojo |
|---|---|---|
| m1 leer el estado de stderr | 65 failed | 11 |
| m2 reintentar cualquier error | 45 failed | 11 |
| m3 partir por `\r\n\r\n` (el sentido real del «al revés» de la especificación) | 16 failed | 11 |
| m4 ignorar `completed_at` | 4 failed | 3 |
| m5 `completed_at` aunque haya `started_at` | 3 failed | 3 |
| m6 quitar el hueco de fecha ilegible del run | 10 failed | 7 |
| m7 quitar el corte de `blind-review` | 7 failed | 5 |
| m8 cortar `blind-review` con `>=` | 1 failed | 1 (`test_blind_review_publicado_justo_en_merged_at_cuenta`) |
| m9 404 por texto en stderr | 7 failed | 4 |
| x1 (extra) quitar el hueco de `merged_at` ilegible | 6 failed | 4 |
| x2 (extra) quitar el hueco de `created_at` ilegible | 1 failed | 1 |
| x3 (extra) quitar `-i` | 4 failed | 2 |
| x4 (extra) buscar el estado en cualquier línea | 2 failed | 1 |

Los 9 mutantes de «Verifica» ponen en rojo al menos un test. m3 solo se detecta porque los tests simulados usan `\n\n` (lo que ve el script) y el `gh` falso emite `\r\n` reales: sin el `gh` falso un cambio de `text=True` a bytes pasaría. m8 depende de un único test (el límite exacto); m6 está cubierto por 7 tests.

## Lo que queda / avisos

- Issue punto 8 (dos tests que solo prueban el simulador): no está en el «Hace» de T50; `test_simulador_sin_filter_all_sirve_el_ultimo_run_por_check_suite` y `test_simulador_ingenuo_no_distingue_el_filtro` siguen siendo pruebas del simulador.
- Issue puntos 1-2 y el caso de ids invertidos: `latest_check_runs` sin tocar, como pide «No hace».
- `latest_check_runs` compara `started_at` como texto: una fecha que no sea texto (lista, entero) lanzaría `TypeError`. La API siempre da texto; fuera de alcance. `_utc` sí lo tolera y se prueba directamente sobre `cut_at_merge`.
- Plantilla de enjambre-agentes, versión y CHANGELOG sin tocar. Regenerar packs: no.

Prod: ninguna.
