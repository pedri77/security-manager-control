# T52 (SMC-009) · Vigilancia diaria de dependencias · dev-proyecto v1.5

Rama `t52-smc009` (desde cdefdcb). Sin push ni PR. Ficheros: los cuatro de «Toca».

## Qué se hizo
- `.github/workflows/vigilancia.yml`: `schedule` diario (`17 5 * * *`) y `workflow_dispatch`; permisos de workflow `contents: read`, del job `contents: read` + `issues: write`; checkout de `main` fijado por SHA (el mismo de `ci.yml`) con `persist-credentials: false`; `OSV_IMAGE` idéntica a la de `ci.yml` (v2.7.0 + digest); sin `${{ }}` dentro de `run` (el token y el repo van por `env`). El paso del escáner guarda el código con `|| code=$?` y la salida en `$RUNNER_TEMP`; el segundo paso llama al script.
- `scripts/vigilancia.py` (stdlib + `gh`): `classify(code, texto)` -> clean | findings | no_packages | error; `findings()` un hallazgo por grupo de osv; `render_body()` tabla paquete / versión / identificador (+CVE) / versión corregida (o «sin versión corregida»). Salida: 0 limpio, 1 hallazgos, 2 error del escáner o de `gh`, 3 manifiesto sin lockfile.
- Con hallazgos: busca la issue abierta por título exacto (`gh issue list --state open --limit 1000`, sin índice de búsqueda), crea con etiqueta `security` (antes `gh label create security --force`, porque la etiqueta no existe en el repo) o, si el cuerpo cambió, comenta y edita el cuerpo; sin cambios no toca nada; siempre rojo. Sin hallazgos: cierra con comentario la abierta. Error del escáner: rojo, no toca issues. 128: igual que `sca` (manifiesto versionado -> rojo). `osv-scanner.toml` lo respeta el propio escáner (se escanea la raíz); no existe hoy en el repo.
- Los cuerpos van por stdin (`--body-file -`), nunca como argumento.

## Medidas reales (imagen `OSV_IMAGE` de ci.yml, Docker 29.9.2, `scan source -r --format json`)
| Caso | Código | stdout |
|---|---|---|
| este repo (uv.lock, 11 paquetes) | 0 | `{"results": [], "experimental_config": ...}` (124 B) |
| temporal con `requirements.txt` `django==1.11.0`, `pyyaml==5.3` | 1 | 552 KB: django 49 vulns / 30 grupos, pyyaml 4 / 2 grupos; 137 `fixed` |
| carpeta vacía | 128 | vacío; stderr «No package sources found» |
| solo `pyproject.toml` | 128 | vacío (mismo mensaje) |
| ruta inexistente | 127 | vacío |
| opción desconocida | 127 | vacío |
Ninguna de las 53 vulnerabilidades medidas carecía de versión corregida: el caso «sin versión corregida» es derivado (se quitan los eventos `fixed` del fixture), no medido. Los fixtures de `tests/test_vigilancia.py` son esa salida recortada (2 grupos por paquete, sin `details`/`references`/`versions`); los de código 0 y 128 se copian tal cual.
Hallazgo de la medida: con el JSON completo la primera versión de `_fixed` lanzó `TypeError` (ordenar int con str); el fixture recortado no lo mostraba. Arreglado con clave `(0,int)/(1,str)` y test `test_versiones_corregidas_mezcladas_no_rompen_la_ordenacion`. Con el JSON completo: 32 hallazgos (30 + 2 grupos), 32 filas.

Con `gh` real, solo lectura: `gh issue list --state open --json number,title,body --limit 1000` -> `[]` (rc 0); `--search 'título in:title'` -> `[]`; `gh label list`: no existe `security`. `scripts/vigilancia.py --code 0` con `gh` real: «Sin hallazgos», rc 0, ninguna escritura (no hay issue abierta). `--code 128` sobre este repo: rc 3 (tiene `pyproject.toml` versionado; misma regla que `sca`; hoy no se da porque hay `uv.lock`). `--code 127`: rc 2. No se creó ni cerró ninguna issue real.

## Tests (45 en `tests/test_vigilancia.py`; 80 casos con parametrización)
Unidad: `test_hallazgos_reales_uno_por_grupo`, `test_hallazgo_trae_version_corregida_medida`, `test_sin_version_corregida_se_dice`, `test_cuerpo_lista_paquete_version_id_y_corregida`, `test_cuerpo_determinista_y_sin_orden_de_entrada`, `test_limpio_real_sin_hallazgos`, `test_codigo_0_json_limpio`, `test_codigo_1_con_hallazgos`, `test_codigo_128_sin_paquetes_stdout_vacio`, `test_otros_codigos_son_error_del_escaner`, `test_json_ilegible_es_error_no_limpio`, `test_codigo_0_con_hallazgos_es_incoherente`, `test_codigo_1_sin_hallazgos_es_incoherente`.
Integración con `gh` simulado (ejecutable `gh` en el PATH que registra llamadas): `test_limpio_*`, `test_hallazgos_crean_issue_con_etiqueta_y_salen_en_rojo`, `test_hallazgos_busca_la_abierta_antes_de_crear`, `test_hallazgos_dos_veces_no_duplica`, `test_hallazgos_sin_cambios_no_comenta`, `test_hallazgos_distintos_comentan_y_actualizan_la_abierta`, `test_error_del_escaner_rojo_y_no_toca_issues`, `test_codigo_128_*`, `test_gh_*_falla_*`, `test_cuerpo_va_por_stdin_no_por_argumento`.
Workflow: `test_misma_imagen_osv_que_ci`, `test_disparadores_programado_diario_y_manual`, `test_permisos_minimos`, `test_actions_fijadas_por_sha`, `test_run_no_interpola_expresiones`, y otros.
TDD: antes del script, 22 fallos + 41 errores (no existía). Tras él, 80 en verde.

## Verifica
`PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: 1059 passed, 2 failed (1061 casos; base 981). Los 2 fallos NO son de la lógica: `tests/test_cli_v06.py::test_readme_comandos_v06_y_cifras` y `tests/test_cli_v07.py::test_cifras_del_readme_son_las_reales` exigen que el badge del README (`tests-645%20en%20verde`) sea >= al número de `def test_` en `tests/` (678 con los 45 nuevos; base 633, margen 12). El README no está en «Toca»: hay que subir el badge a >= 678 (y su cifra de texto si la hay) en la sesión principal o en una tarea que lo toque. `tests/test_vigilancia.py` solo: 80 passed.

## Contraprueba (copias en scratchpad, fuera del worktree, una por mutante, lanzado desde la copia, `tests/test_vigilancia.py`)
| Mutante | En rojo |
|---|---|
| m1: 128 tratado como limpio | 7 (`test_codigo_128_*`) |
| m2: JSON ilegible tratado como limpio | 22 (`test_json_ilegible_es_error_no_limpio` x18, `test_error_del_escaner_rojo_y_no_toca_issues` x4) |
| m3: sin rojo con hallazgos (rc 0 con issue sin cambios) | 4 (`test_hallazgos_crean_issue...`, `..._dos_veces_no_duplica`, `..._distintos_comentan...`, `..._issue_cerrada_crea_nueva`) |
| m4: crear sin buscar la abierta | 5 (`busca_la_abierta_antes_de_crear`, `dos_veces_no_duplica`, `distintos_comentan`, `gh_list_falla_con_hallazgos`, `gh_list_devuelve_json_ilegible`) |
| m5: cerrar la issue con error del escáner | 10 (`test_error_del_escaner_*`, `test_hallazgos_y_codigo_distinto_de_1_no_crea`) |
| m6: no cerrar sin hallazgos | 2 (`test_limpio_cierra_la_issue_abierta_con_comentario`, `test_gh_close_falla_rojo`) |
| m7: digest distinto al de ci.yml | 1 (`test_misma_imagen_osv_que_ci`) |

## Decisiones y límites
- Código 0 con hallazgos o código 1 sin hallazgos se tratan como error del escáner (incoherencia).
- Etiqueta `security`: se crea con `gh label create --force` justo antes de crear la issue; no probado de verdad (solo simulado). `issues: write` basta para etiquetas, pero se verá tras fusionar.
- Un cuerpo de issue > 65 536 caracteres haría fallar `gh issue create` (rojo, 2); con ~32 hallazgos son pocos KB. Sin recorte.
- Comparación del cuerpo para «cambian»: igualdad tras `strip`; si alguien edita la issue a mano, se vuelve a comentar y editar una vez.
- Pendiente tras fusionar (de David/coordinador): lanzar `workflow_dispatch` una vez y comprobar creación y cierre reales; subir el badge del README; el rojo diario es esperado mientras haya hallazgos.

## Revisión del coordinador (coordinador v2.4, 2026-11-07)
- Alcance: `git diff --stat` solo los 4 ficheros de «Toca»; `superficies.py diff dev-proyecto`: OK (salida 0). Pies de los commits de la rama: `Agente: dev-proyecto v1.5`, `Tarea: …#T52`, `Task: SMC-009`. gitleaks: no leaks; grep de secretos: sin resultados.
- Verifica (mío): `pytest -q` → 1059 passed, 2 failed. Los dos son exactamente `tests/test_cli_v06.py::test_readme_comandos_v06_y_cifras` y `tests/test_cli_v07.py::test_cifras_del_readme_son_las_reales`, por la misma causa (`assert 645 >= 678`: insignia del README, fuera del «Toca»). Los cierra T53.
- Medida real con Docker 29.9.2 y la imagen fijada (`OSV_IMAGE` idéntica a la de `ci.yml`, línea 22 de ambos ficheros), `scan source -r --format json`, en carpetas temporales, sin instalar ni ejecutar paquetes: este repo → rc 0, 124 B, `{"results": []…}`; temporal con `django==1.11.0` y `pyyaml==5.3` → rc 1, 552249 B; carpeta vacía → rc 128, stdout vacío. `classify` sobre la salida real: findings con 32 hallazgos, `clean` con la de rc 0, `no_packages` con 128, `error` con 127. Los 4 hallazgos del fixture `OSV_HALLAZGOS` están en la salida real, iguales, y sus claves son un subconjunto de las reales.
- `gh` real, solo lectura: `gh issue list --state open --json number,title` → solo la #28; búsqueda del título `[vigilancia] …` → `[]`.
- Contraprueba (copias limpias de `git archive HEAD`, un mutante por copia, `tests/test_vigilancia.py`, módulo de la copia): m1 128=limpio → 7 rojos; m2 JSON ilegible=limpio → 22; m3 `return 1`→`return 0` tras hallazgos → 4; m4 `issue = None` (crear sin buscar) → 8; m5 cerrar la issue con error del escáner → 8; m6 no cerrar sin hallazgos → 2 (`test_limpio_cierra_la_issue_abierta_con_comentario`, `test_gh_close_falla_rojo`); m7 digest distinto → 1 (`test_misma_imagen_osv_que_ci`). Copias en `…/scratchpad/c52.*` (no se borran).
