# T51 · Puerta de seguridad en PR (SMC-009, issue #28) · dev-proyecto v1.5

Rama `t51-smc009` (sale de cdefdcb). Sin push, sin PR, sin tocar main.

## Qué se hizo
- `scripts/change_evidence.py`: modo `security --pr N` y funciones compartidas con `pr`: `parse_security_paths`, `pr_title_type`,
  `read_file_at`, `threat_model_problems`, `no_aplica_reason`, `evaluate_security`, `mode_security`, `security_label`.
  Reutiliza `gh_json`, `gh_pages`, `http_status`, `is_release_pr`, `HTML_COMMENT_RE` y `status_at_merge`
  (ahora con parámetro `contexts`, por defecto solo `blind-review`, para cortar también `security-review` en `merged_at`).
- `collect_pr` añade `security` (`required`, `reason`, `threat_model`, `review`); un fallo de lectura deja `required: null` y un hueco
  con el PR, sin abortar. `mode_release` anota `PR #n activa la puerta de seguridad sin security-review correcto (estado: …)`.
  `pr_markdown` muestra la línea «Puerta de seguridad». El modo `pr` no falla por la puerta.
- `.github/workflows/pr-meta.yml`: job `security-gate` (`pull_request`, lectura, acciones por SHA, `persist-credentials: false`,
  número de PR y token por `env`, nada interpolado en el shell).
- `.github/security-paths.txt` con las 6 rutas pedidas. `docs/threat-model/SMC-009.md` con 16 amenazas (10 mitigadas con su test,
  6 aceptadas pendientes de firma de David; no firmadas).

## Medido con `gh` 2.89.0 real, solo GET (2026-11-07)
- `pulls/24/files?per_page=100`: lista de objetos `{sha, filename, status, additions, deletions, changes, blob_url, raw_url, contents_url, patch}`;
  7 ficheros en #24, 4 en #26. `previous_filename` (renombrados) solo está documentado: ninguno de los PR del repo renombra.
- `contents/<ruta>?ref=<rama|sha>`: objeto `{name, path, sha, size, url, html_url, git_url, download_url, type:"file", content, encoding:"base64", _links}`;
  el base64 lleva `\n` cada 60 caracteres. Sobre una carpeta devuelve una lista.
- Fichero inexistente (lista en `main`, `docs/threat-model/SMC-009.md` en la cabeza de #26): `HTTP/2.0 404 Not Found`, cuerpo
  `{"message":"Not Found","documentation_url":"https://docs.github.com/rest/repos/contents#get-repository-content","status":"404"}`,
  stderr `gh: Not Found (HTTP 404)`. `http_status` lo lee de stdout.
- `commits/<sha>/statuses` de la cabeza de #26: lista con `{url, id, node_id, state, description, target_url, context, created_at, updated_at, creator, …}`.
- Sin medir (solo documentado): fichero >1 MB (`encoding` distinto de base64), tope de 3000 ficheros de `pulls/N/files`, SHA de un fork en `contents`.
  Los tres se tratan como error (falla en cerrado).
Los simuladores de los tests (`FakeSec`, `contenido`, `fallo_404_github`) copian estos formatos; hay un test con el binario `gh` falso
que imprime los bytes del 404 medido (`test_leer_fichero_404_con_gh_falso_y_los_bytes_medidos`).

## Verifica
`PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` → **1119 passed** (981 antes; +138 casos en 12 funciones `test_`).
Fallan primero: con el `change_evidence.py` de HEAD y los tests nuevos, 130 en rojo (los de workflow y lista pasan porque los ficheros ya existían).

### Contra GitHub real (solo GET, salida en `/private/tmp/claude-501/smc009`)
| PR | `security --pr` con la lista leída de `main` hoy (404) | con la lista del worktree sustituyendo SOLO la lectura de la base |
|---|---|---|
| #24 | rc 0, no aplica (solo cuenta `sec`, con AVISO) | rc 1: toca `scripts/change_evidence.py`, falta `docs/threat-model/SMC-007.md` |
| #26 | rc 0, no aplica | rc 1: falta `docs/threat-model/SMC-008.md` |
| #23 | rc 0, PR de release exento | rc 0, exento |
| #22 | rc 0, no aplica | rc 0, no aplica |
`pr` del worktree frente al de `origin/main` (con y sin lista) sobre #24, #26, #22 y #10: la única clave distinta del registro es `security`.

## Contraprueba (copias temporales fuera del worktree, una por mutante, lanzando desde la copia)
Cada copia da además 4 rojos ajenos (`test_t08::test_h3_gitignore…` y 3 de `test_cli_v07::test_gitignore_de_datos_de_cliente`):
la copia no es un repo git; el mismo fallo sale con el script de HEAD. Cifras sin esos 4.
| Mutante | Rojos | Tests que lo detectan (muestra) |
|---|---|---|
| 1 leer la lista de la cabeza | 52 | `test_puerta_decide_si_aplica[lista_de_la_cabeza_vaciada_no_libra]`, `test_exige_threat_model_…` |
| 2 no activar por tocar la lista | 2 | `test_puerta_decide_si_aplica[tocar_la_lista_activa_la_puerta]`, `[borrar_la_lista_activa_la_puerta]` |
| 3 aceptar motivo vacío | 4 | `test_exige_…[linea_sin_motivo_0/1/2]`, `test_funciones_puras_de_la_puerta[no_aplica_reason]` |
| 4 aceptar la línea en comentario HTML | 1 | `test_exige_…[linea_en_comentario_html_1]` (comentario de varias líneas) |
| 5 ignorar `abierta` | 10 | `test_contenido_del_threat_model[estado_0…5]`, `[una_fila_abierta_entre_cerradas]`, `[la_plantilla_sin_rellenar_no_pasa]` |
| 6 no eximir el PR de release | 5 | `test_puerta_decide_si_aplica[el_pr_de_release_no_se_ve_afectado]`, `[…de_tipo_sec_tampoco]`, `test_modo_security[pr_de_release_sale_con_0]`, `test_registro_con_campo_security[pr_de_release_no_aplica]`, `test_pack_…[el_pr_de_release_no_deja_hueco]` |
| 7 pasar si falla la API (`mode_security` devuelve 0) | 19 | `test_modo_security[api_caida_*]`, `[excepcion_inesperada_sale_con_1]` |
| 7b (extra) todo error de lectura es «ausente» | 7 | `test_leer_fichero_distingue_ausencia_de_error[otro_error_*]`, `test_modo_security[403_en_la_lista_no_es_lista_ausente]` |
| 8 quitar el hueco de `security-review` | 5 | `test_pack_de_release_anota_el_hueco_de_security_review[aplica_sin_security_review_deja_hueco, security_review_{failure,pending,error}_deja_hueco, …solo_posterior_al_merge…]` |
| 9 contar `security-review` posterior a `merged_at` | 5 | `test_registro_con_campo_security[security_review_posterior_al_merge_no_cuenta, el_posterior_no_sustituye_al_previo, el_corte_vale_para_los_dos_contextos, created_at_ilegible…]`, `test_pack_…[…solo_posterior_al_merge…]` |

## Desajustes y decisiones (a revisar por el coordinador)
1. **La lista no existe en `main`.** Hasta que se fusione T51, `security --pr 24` y `26` no fallan (solo cuenta `sec`), contra lo que dice el
   Verifica. Solo fallan con la lista inyectada en la lectura de la base (tabla de arriba). Hay que repetir esa prueba tras fusionar.
2. **Insignia de tests del README.** `test_cli_v06` y `test_cli_v07` exigen `tests-NNN` ≥ número de `def test_` (633 con insignia 645). El README no está en
   «Toca», así que las pruebas van en 12 funciones parametrizadas (644 `def test_`). Queda margen 1: T52 y cualquier test nuevo exigen subir la insignia.
3. **T52 no toca `SMC-009.md`.** Las filas T14 a T16 (job de vigilancia) quedan `aceptada`, pendientes de firma de David, con la mitigación «prevista en T52»
   y `tests/test_vigilancia.py::pendiente_de_t52` que no existe. Si T52 debe pasarlas a `mitigada`, hay que añadir el fichero a su «Toca».
4. **Interpretaciones** (comportamiento no fijado en el brief): (a) con la lista ausente en la base, tocar la lista no activa nada (literal); (b) con varios
   TASK_ID, cada uno necesita su threat model; (c) si el fichero existe se juzga aunque haya línea «no aplica»; (d) `abierta` cuenta en cualquier celda de tabla
   (comentarios HTML aparte), la palabra en prosa no; (e) placeholders: `<TASK_ID> <feature> <n> <slug> YYYY-MM-DD NNNN tests/... sí / no`; (f) la línea
   «no aplica» debe empezar la línea (la casilla `- [ ] Threat model:` de la plantilla no cuenta); (g) la lista se lee de `base.ref`, no de `base.sha`.
5. **Límite de `pull_request`:** el job ejecuta el `change_evidence.py` del propio PR. Aceptado en T11 (la lista incluye `scripts/*` y los workflows;
   falta añadir `security-gate` a la regla de rama, que hace David).
6. Un modelo vacío o pobre pasa la puerta (T12, aceptada): solo se comprueba `abierta` y placeholders.
7. `git status` de la rama: solo los 5 ficheros de «Toca» más este informe.

## Acción de prod
Ninguna. `security-gate` no es obligatorio hasta que David lo añada a la regla de rama.
