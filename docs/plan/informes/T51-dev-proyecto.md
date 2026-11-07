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

---

# Segunda vuelta (tras revisión del coordinador) · dev-proyecto v1.5 · 2026-11-07

Rama `t51-smc009`: integrada la base `8c4f639` con `git merge --no-ff` (trae T52 y el plan ampliado), sin push. Lo de arriba sigue siendo el
informe de la primera entrega; en esta vuelta quedan superadas sus líneas «Un modelo vacío o pobre pasa la puerta (T12, aceptada)», la
interpretación 4(c) y los desajustes 2 y 3 (ver abajo).

## Qué cambia
1. **Modelo tocado por el PR** (`evaluate_security`): el `docs/threat-model/<TASK_ID>.md` debe figurar en `pulls/N/files` con estado distinto de
   `removed` (`added`, `modified` o `renamed` con ese `filename`). Uno que existe en la cabeza pero el PR no toca no cuenta como modelo: falla
   con «no lo añade ni lo modifica», salvo que haya línea `Threat model: no aplica: <motivo>` (decisión mía: la línea es la salida prevista para
   «este cambio no necesita modelo»; un modelo tocado se sigue juzgando aunque haya línea). Un modelo movido a otro nombre
   (`previous_filename` = su ruta) no cuenta: ya no existe en la cabeza. Con varios TASK_ID, cada uno cumple por su cuenta.
2. **Contenido** (`threat_model_problems`): hace falta al menos una fila en una tabla con columna «Estado»; el estado, celda entera tras quitar
   `` ` * _ `` y espacios, sin distinguir mayúsculas, es `mitigada` o `aceptada` (`THREAT_STATES`); cualquier otro valor (vacío, `abierto`,
   `abierta (pendiente)`, `abierta, ver T3`, `mitigada (parcial)`) da «estado '…' fuera de mitigada/aceptada». Se retira `ABIERTA_RE`.
   `# x`, `""` y una tabla sin filas dan «sin filas de amenaza».
3. **Aceptación firmada**: por cada fila `aceptada` hace falta una fila con su ID en la sección 5 (el título `## 5…` hasta el siguiente `##`, sin
   comentarios HTML), con «Aceptado por» no vacío y «Fecha» con `AAAA-MM-DD` válido (`date.fromisoformat`; `2026-02-30` y `2026-13-45` no). Las
   columnas se buscan por nombre en la cabecera. La firma es esa columna: ningún agente la rellena.
4. **`read_file_at`** escapa `ref` (`quote(safe="")`) y la ruta (`quote(safe="/")`).
5. **`SMC-009.md`**: T12 retirada (fila y aceptación); T14, T15 y T16 pasan a `mitigada` con tests reales de `tests/test_vigilancia.py`
   (`test_permisos_minimos`, `test_run_no_interpola_expresiones`, `test_cuerpo_va_por_stdin_no_por_argumento`, `test_workflow_gh_usa_token_por_entorno`;
   `test_misma_imagen_osv_que_ci`, `test_imagen_osv_con_version_y_digest`; `test_error_del_escaner_rojo_y_no_toca_issues`,
   `test_error_del_escaner_no_crea_issue`, `test_hallazgos_busca_la_abierta_antes_de_crear`, `test_hallazgos_dos_veces_no_duplica`,
   `test_workflow_no_traga_el_codigo_del_escaner`). Cambia el texto de T14 (el cuerpo va por stdin; el script no «escapa» nada, como decía antes).
   T5 y T6 describen las reglas nuevas con sus tests; nueva T17 (`ref` con `&`, `#`, `?`) mitigada por `test_leer_fichero_escapa_ref_y_ruta`.
   Sección 5: la columna «Fecha» ya no lleva la ruta de un test; «Aceptado por» es `David Moya` como en la plantilla.
6. **README**: solo el número de la insignia, 645 a 690, que es el recuento real de `def test_` (`cat tests/test_*.py | grep -cE '^\s*def test_'`).

## Firmas que le quedan a David
`docs/threat-model/SMC-009.md`, sección 5, columna «Fecha» **vacía** en: **T11** (la puerta corre la versión del propio PR) y **T13** (motivo libre
de `no aplica`). Con ellas vacías, `security --pr` sobre un PR que traiga este modelo falla («aceptada sin aceptación firmada»): es lo pedido.
T12 ya no existe; T14 a T16 son `mitigada`. Las dos fechas las pone él con `AAAA-MM-DD`. No he escrito ninguna.

## Medido con GitHub real (solo GET, 2026-11-07)
- `pulls/24/files`: 7 ficheros, claves `filename` y `status` (`added`/`modified`), ninguno con `previous_filename`. `filename` trae la ruta completa.
- Renombrados: este repo no tiene ninguno. Medido en `astral-sh/uv#23009`: `status: "renamed"`, `filename` = ruta nueva, `previous_filename` = ruta
  anterior (`test/scenarios/indexes/default.toml` ← `pip-compile-default.toml`, y otro más). Con la lista inyectada solo con la ruta antigua,
  `evaluate_security("astral-sh/uv", 23009)` da `required: true` «toca rutas sensibles: …pip-compile-default.toml» (el renombrado cuenta como tocado).
- `security --pr` con la lista del worktree inyectada solo en la lectura de la base (en `main` sigue sin existir, 404): #24 (falta SMC-007), #26 (SMC-008),
  #19 (SMC-005) y #15 (SMC-003) fallan; #23 y #10 (release), #22, #16 y #11 no. 40 peticiones, todas `repos/…` por GET.
- `pr` de esta rama frente a `origin/main` sobre #24, #26, #22, #10 y #19: la única clave distinta del registro es `security`.
- `ref` sin escapar contra la API: `contents/README.md?ref=nope&ref=main` devuelve el fichero de `main` (33225 caracteres) con el script de HEAD; con el
  escapado (`ref=nope%26ref%3Dmain`) da 404 y `read_file_at` devuelve `None`. GitHub se queda con el último `ref` repetido.
  No hay ramas con `/` en el repo; el escapado de `/` (`%2F`) se comprueba solo en tests y la API respondió 404 a `x%2Fy`, sin medir un 200 con barra.

## Verifica
`PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` → **1269 passed** (1119 antes de esta vuelta; 690 `def test_`, insignia 690).
TDD: con los tests nuevos y el `change_evidence.py` de HEAD, 57 en rojo en `tests/test_change_evidence.py`; con el cambio, 514 verdes ahí y 1269 en total.
Los tests nuevos son casos parametrizados de las tablas existentes más `test_leer_fichero_escapa_ref_y_ruta` y el de SMC-009 reescrito
(`test_el_threat_model_de_smc_009_solo_espera_la_firma_de_david_y_cada_mitigacion_tiene_su_test`: comprueba que T12 no está, que T14 a T16 apuntan a tests
que existen, que todas las «Fecha» de §5 están vacías y que lo único que la puerta le reprocha son esas firmas).

## Contraprueba (copias en el directorio temporal de la sesión, fuera del worktree, una por mutante, `uv run --extra dev pytest -q` lanzado desde la copia)
La copia no es un repo git: 4 rojos ajenos en una copia sin mutar (`test_t08::test_h3_gitignore_ignora_html_y_dashboard` y los 3
`test_cli_v07::test_gitignore_de_datos_de_cliente[…]`). Cifras restando esos 4.

| # | Mutante | Rojos | Muestra |
|---|---|---|---|
| 1 | leer la lista de la cabeza | 61 | `test_exige_…[linea_en_comentario_html_0…3]`, y decenas más |
| 2 | no activar por tocar la lista | 2 | `test_puerta_decide_si_aplica[tocar_la_lista_activa_la_puerta]`, `[borrar_la_lista_activa_la_puerta]` |
| 3 | aceptar motivo vacío | 3 | `test_exige_…[linea_sin_motivo_0, _1, _2]` |
| 4 | aceptar la línea en comentario HTML | 1 | `test_exige_…[linea_en_comentario_html_1]` |
| 5 | ignorar `abierta` (añadirla al vocabulario) | 9 | `test_contenido_del_threat_model[estado_0…]` |
| 6 | no eximir el PR de release | 5 | `test_modo_security[pr_de_release_sale_con_0]`, `test_puerta_decide_si_aplica[el_pr_de_release_no_se_ve_afectado]` |
| 7 | pasar si falla la API (`mode_security` devuelve 0) | 19 | `test_modo_security[api_caida_commits_403]`, `[3000_ficheros_es_lectura_incompleta]` |
| 8 | quitar el hueco de `security-review` | 5 | `test_pack_de_release_anota_el_hueco_de_security_review[aplica_sin_security_review_deja_hueco]` |
| 9 | contar un `security-review` posterior a `merged_at` | 5 | `test_registro_con_campo_security[el_posterior_no_sustituye_al_previo]`, `[el_corte_vale_para_los_dos_contextos]` |
| 10 | aceptar un modelo que no está en los ficheros del PR | 6 | `test_exige_…[modelo_existente_en_la_cabeza_sin_tocar_no_vale]`, `[modelo_borrado_no_vale]` |
| 11 | aceptar estado fuera del vocabulario (solo rechaza `abierta` exacta) | 13 | `test_contenido_del_threat_model[estado_fuera_del_vocabulario_0]`, `[el_problema_nombra_la_amenaza_y_el_estado]` |
| 12 | aceptar un modelo sin filas | 7 | `test_contenido_del_threat_model[sin_filas_de_amenaza_0…3]` |
| 13 | aceptar `aceptada` sin firma | 21 | `test_contenido_del_threat_model[aceptada_con_fecha_ilegible_0…]`, `[aceptada_con_fecha_vacia_no_pasa]` |
| 14 | `ref` sin escapar | 5 | `test_leer_fichero_escapa_ref_y_ruta[a&ref=main]`, `[x#y]`, `[a+b]` |

(Los 9 primeros son los originales; 10 a 14 los nuevos. El 14 cuenta 5 nombres únicos porque el id de un caso lleva un salto de línea y el recuento lo parte.)
Cifras de los originales distintas de la primera entrega (52, 2, 4, 1, 10, 5, 19, 5, 5): los tests de estado y de modelo se reescribieron.

## Desajustes y decisiones
1. El modelo `SMC-009.md` no pasa su propia puerta hasta que David ponga las dos fechas (T11, T13). Cualquier PR de SMC-009 que cite `Task: SMC-009` y toque
   rutas sensibles queda en rojo hasta entonces; es el efecto buscado, pero conviene que lo sepa el coordinador antes de la ola.
2. Un modelo existente sin tocar más línea `no aplica` pasa por la línea (mi lectura). Si se prefiere que un modelo sin tocar nunca valga ni con línea, es un
   cambio de una condición y el test `modelo_sin_tocar_con_linea_no_aplica_pasa_por_la_linea`.
3. «Aceptado por» no vacío es mi añadido a la definición de firma (fecha sin nombre no firma); la plantilla ya trae `David Moya`.
4. El estado de amenaza solo se mira en tablas con columna «Estado» (sección 3 de la plantilla). La palabra `abierta` en otra columna o en prosa ya no cuenta.
5. Desajuste 1 de la primera entrega sigue vigente: la lista no existe en `main` hasta fusionar T51; las cifras con GitHub real usan la lista inyectada.
6. La insignia queda en 690 = recuento real; cualquier test nuevo exige subirla otra vez.
