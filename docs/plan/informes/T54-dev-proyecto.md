# T54 (SMC-009) · Vigilancia: adopción de la issue, contenido de terceros y concurrencia · dev-proyecto v1.5

Rama `t54-smc009` (desde 6beaab1). Sin push ni PR. Ficheros: los de «Toca» (`scripts/vigilancia.py`, `tests/test_vigilancia.py`, `.github/workflows/vigilancia.yml`, este informe).

## Medido con `gh` real (solo GET)
- Este repo (`gh issue list --state all --json author,labels`, 12 issues): todas `author` = `{"id":"MDQ6VXNlcjEyOTg5Njk0","is_bot":false,"login":"pedri77","name":"pedri77"}`; `labels` = lista de objetos `{"id","name","description","color"}` (p. ej. `task:SMC-010`). No hay ninguna issue del bot en este repo.
- Issue creada por `github-actions[bot]`: repo público `happyhappy82/github-trending-notion`, issue #1465: `gh issue list --json number,author,labels` da `author` = `{"is_bot":true,"login":"app/github-actions"}` (sin `id` ni `name`) y `labels` = `[{"id":"LA_kwDORuIXqs8AAAACcc1fag","name":"workflow-failure",...}]`.
- Desajuste con lo que se supondría: el login en `gh issue list` es `app/github-actions`, NO `github-actions[bot]`. Esa forma (`login:"github-actions[bot]"`, `type:"Bot"`, `is_bot:false`) es la de `gh search issues` (medida en `github/gh-aw` #75683). Un test fija que la forma de `search` no se adopta.

## Qué se hizo
- N2: `open_issue` pide `number,title,body,author,labels` y solo adopta si título exacto Y `author.is_bot is True` Y `author.login == "app/github-actions"` Y existe una etiqueta `security`. Una issue ajena con el mismo título se ignora: ni se edita, ni se comenta, ni se cierra, y si hay hallazgos se crea la propia. Si falta `author` o `labels` (cambio de forma de `gh`), error de `gh` (código 2), no adopción a ciegas.
- N3: `NAME_RE` (≤100: `[A-Za-z0-9@][A-Za-z0-9._+:/~@-]*`), `VERSION_RE` (≤64: `[A-Za-z0-9][A-Za-z0-9._+:~-]*`), `ID_RE` (≤64: `[A-Za-z0-9][A-Za-z0-9._:-]*`), con `fullmatch`, solo ASCII; además se rechaza `://`. Lo que no cumple, o no es texto, se sustituye por `(valor no válido)`. Aplica a paquete, versión, identificador, alias CVE (si no cumple, se omite el paréntesis) y cada versión corregida. Quedan fuera `|`, saltos de línea y controles, espacios, `` ` ``, `<`, `>`, `!`, `[`, `]`, `(`, `)`, `#`, `&`, `\`, `*`, Unicode (homoglifos, ceros de ancho, RTL).
- `@`: solo lo admite el nombre del paquete (npm `@scope/paquete`). No se borra: el valor se muestra entero envuelto en código en línea (`` `@org/team` ``). GitHub no crea menciones ni notifica dentro de código, y el nombre legítimo se lee igual. El resto de campos no admiten `@`. Test: fuera de los códigos en línea no queda ningún `@`.
- N10: `vigilancia.yml` con `concurrency: {group: vigilancia, cancel-in-progress: false}` y `timeout-minutes: 15` en el job (T52 midió django+pyyaml en ~segundos de escáner; 15 min cubre el pull de la imagen con margen).
- El `gh` simulado copia la forma medida (author/labels como objetos, bot = `app/github-actions`).

## Verifica
- TDD: con los tests nuevos y sin implementación, 104 fallos (119 pasaban) en `tests/test_vigilancia.py`.
- `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: **1419 passed, 2 failed** (1421 tests). Los 2 son los de la insignia del README (`test_cli_v06::test_readme_comandos_v06_y_cifras`, `test_cli_v07::test_cifras_del_readme_son_las_reales`), que cierra T53. `tests/test_vigilancia.py`: 232 casos.
- Textos de la auditoría probados en paquete, versión, id, versión corregida y alias: `@org/team`, `|`, salto de línea (también `a\nb` y `abc\n`), imagen externa `![x](https://…)`, `<!--`, más enlace, URL, HTML, `#1234`, CR, ancho cero, homoglifo cirílico, RTL, 300 caracteres, vacío, espacio y comilla invertida. En todos la tabla conserva 3 filas de 5 barras y el valor no llega literal. Legítimos que siguen pasando: `@scope/paquete`, `@babel/core`, `github.com/gorilla/mux`, `org.apache.logging.log4j:log4j-core`, `GHSA-9r8w-6x8c-6jr9`, `PYSEC-2017-44`, `GO-2024-0001`, `RUSTSEC-2023-0001`, versiones `1.2.3+build.5`, `v2.0.0+incompatible`, `1:2.3-4~bpo11+1`, `2.0.0b1`, `1.11rc1`. Las filas de los fixtures reales (django, pyyaml) no cambian.

## Contraprueba (6 mutantes, uno por copia fuera del worktree, lanzando `pytest tests/test_vigilancia.py` desde la copia)
| Mutante | Fallan | Primer test en rojo |
|---|---|---|
| m1 adoptar sin mirar autor ni etiqueta (`and _mine(i)` fuera) | 11 | `test_issue_ajena_con_el_mismo_titulo_no_se_adopta_ni_se_toca` |
| m2 adoptar sin mirar etiqueta | 1 | `test_issue_del_bot_sin_etiqueta_security_no_se_adopta` |
| m3 no escapar `@` (sin código en línea) | 5 | `test_nombres_legitimos_de_paquete_pasan[@scope/paquete]` y `test_mencion_de_npm_se_neutraliza_en_codigo_no_se_borra` |
| m4 no escapar `\|` (permitido en las tres listas) | 6 | `test_campo_hostil_no_llega_literal_ni_rompe_la_tabla[barra-*]` |
| m5 aceptar salto de línea (`\n` en las tres listas) | 10 | `…[salto_solo-*]`, `…[salto_final-*]` |
| m6 quitar `concurrency` | 1 | `test_concurrency_sin_cancelar_la_que_corre` |
Una primera pasada de m5 sobrevivió (222 passed): el único caso con salto también llevaba `|` y espacios. Se añadieron `salto_solo` y `salto_final` y el mutante pasó a rojo.

## Decisiones y lo que queda
- Se acepta solo `app/github-actions` (lo medido). Si el flujo pasara a otra credencial (PAT, GitHub App), la adopción dejaría de reconocer su propia issue y crearía una nueva cada día: hay que actualizar `BOT_LOGIN`.
- Cualquier workflow del repo con `GITHUB_TOKEN` y la etiqueta `security` puede crear una issue con ese título y ser adoptada; es el límite aceptado de «creada por el bot».
- Una issue antigua creada por un humano con ese título queda huérfana tras este cambio; no se toca.
- Sin límite de tamaño del cuerpo total (65 536 caracteres de GitHub): no pedido, no cambiado.
- Acción de prod: ninguna (el despliegue es el merge a main; `vigilancia.yml` no está en `api/**`).

---
# Segunda vuelta (tras la revisión del coordinador) · base integrada con `git merge --no-ff 7651aca` (77e1c01)

## Qué falló en la primera vuelta
`www.evil.com/login` pasaba la lista blanca (sin `://`) y GFM lo autoenlaza; `GH-12` enlaza a una issue; `a~~b~~c` tacha. Mi comprobación de autolink solo miraba `://`. La lista blanca no puede cubrir todo el Markdown: el control es el código en línea.

## Cambios en `scripts/vigilancia.py`
- `_cell`: todo campo de terceros (paquete, versión, identificador, alias CVE y cada versión corregida) que pase la lista blanca va entero en código en línea (`` `www.evil.com/login` ``), no solo los que llevan `@`. Lo que no pasa sigue siendo `(valor no válido)` (texto fijo nuestro). La lista blanca sigue sin comilla invertida, `|`, salto de línea ni espacios.
- Tope: `MAX_BODY = 60000` (< 65 536 de issue y de comentario). `render_body` añade filas mientras quepan (con 200 caracteres de margen para el aviso) y, si recorta, escribe «Lista recortada: se muestran N de M hallazgos por el tope de tamaño de la issue; el resto está en la salida del job `vigilancia`» [FALSO, corregido en la tercera vuelta: el aviso ahora remite al artefacto `osv-vigilancia`]. La cabecera sigue diciendo el total real y el script sigue saliendo con 1 (rojo). Una fila acota además sus versiones corregidas a 10 (`MAX_FIXED`, «y N más»), para que una sola fila no pueda pasar del tope.
- Efecto en la tabla: `| `django` | `1.11.0` | `PYSEC-2017-44` (`CVE-2017-12794`) | `1.10.8`, `1.11.5` |`. Cambia el formato visible de las filas; actualizadas las aserciones de T52/T54 que lo fijaban.

## Tests nuevos (`tests/test_vigilancia.py`: 270 casos, eran 232)
- `test_campo_valido_pero_peligroso_va_entero_en_codigo_en_linea` (5 campos x 6 valores: `www.evil.com/login`, `GH-12`, `a~~b~~c`, `x@evil.com`, `a__b__c`, `evil.com/login`): fuera del código en línea no queda `www.`, `GH-`, `~~`, `@`, `__`.
- `test_cada_celda_de_datos_es_un_codigo_en_linea_o_la_marca`, `test_www_evil_com_login_en_el_paquete_se_muestra_como_codigo`, `test_la_lista_blanca_sigue_sin_comilla_invertida_ni_barra`.
- Cuerpo enorme: 3000 hallazgos (a mano, función y de punta a punta con `gh` simulado) quedan por debajo de 65 536 y de `MAX_BODY`, con aviso, el recuento mostrado coincide con las filas, la cabecera dice 3000, sale en rojo; el comentario de actualización también cabe; 50 hallazgos no se recortan; una fila con 5000 versiones corregidas se acota.
- Rojo previo: con el `vigilancia.py` de la primera vuelta y los tests nuevos, 61 fallos.

## Verifica
- `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: **1457 passed, 2 failed** (1459 tests); los 2 son los de la insignia del README (T53). `tests/test_vigilancia.py`: 270 passed.
- Contraprueba: 9 mutantes, cada uno en su copia limpia (rsync del worktree sin `.git` ni `.venv`) y lanzando `pytest tests/test_vigilancia.py` desde la copia:
| Mutante | Fallan | Primeros en rojo |
|---|---|---|
| m1 adoptar sin mirar autor ni etiqueta | 11 | `test_issue_ajena_con_el_mismo_titulo_no_se_adopta_ni_se_toca` |
| m2 adoptar sin mirar etiqueta | 1 | `test_issue_del_bot_sin_etiqueta_security_no_se_adopta` |
| m3 no escapar `@` (sin código si lleva `@`) | 6 | `…[mencion-package]`, `test_mencion_de_npm_se_neutraliza_en_codigo_no_se_borra` |
| m4 no escapar `\|` | 7 | `…[barra-package]`, `…[barra-version]` |
| m5 aceptar salto de línea | 11 | `…[salto_final-*]`, `…[salto_solo-*]` |
| m6 quitar `concurrency` | 1 | `test_concurrency_sin_cancelar_la_que_corre` |
| m7 versión fuera de código en línea | 35 | `test_cuerpo_lista_paquete_version_id_y_corregida`, `test_valor_no_valido_se_sustituye_por_marca_fija` |
| m7b paquete fuera de código en línea | 26 | `test_cuerpo_lista_paquete_version_id_y_corregida`, `…[mencion-package]` |
| m8 quitar el tope del cuerpo (`MAX_BODY = 10**9`) | 3 | `test_cuerpo_enorme_se_recorta_bajo_el_limite_de_github_y_lo_dice`, `test_cuerpo_enorme_de_punta_a_punta_issue_bajo_limite_y_en_rojo`, `test_comentario_de_actualizacion_tambien_cabe` |

## Queda / decisiones
- El recorte pierde los hallazgos del final (orden por paquete, versión, id); [corrección, tercera vuelta: NO quedaban en la salida del job, el workflow no imprimía el JSON; ahora quedan en el artefacto `osv-vigilancia`, ver abajo]. No se mide la longitud en bytes: el contenido es ASCII por la lista blanca y el texto fijo en español tiene pocos caracteres no ASCII.
- Los alias distintos del primero CVE no se muestran (como antes).

---
# Tercera vuelta (aprobada por David) · base integrada con `git merge --no-ff 2834c62`

## El fallo
El aviso de recorte decía «el resto está en la salida del job». Falso: `vigilancia.yml` mandaba el JSON a `$RUNNER_TEMP/osv.json` sin imprimirlo y el script solo imprime el recuento. Los hallazgos recortados no estaban en ningún sitio. Las dos frases falsas de este informe (segunda vuelta: descripción del tope y «Queda / decisiones») quedan marcadas arriba como falsas.

## Cambios
- `vigilancia.yml`: último paso `actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2` (el mismo SHA de `pr-meta.yml`, con test que los compara), `if: always()`, nombre fijo `osv-vigilancia`, ruta `${{ runner.temp }}/osv.json`, `retention-days: 90`, `if-no-files-found: ignore` (si el escáner no llegó a escribirlo, no falla).
- `vigilancia.py`: constante `ARTIFACT = "osv-vigilancia"`; el aviso dice «el JSON completo de osv-scanner está en el artefacto `osv-vigilancia` de la ejecución de `vigilancia.yml`». No se imprime ningún hallazgo en el log (test: stdout y stderr sin `PYSEC` ni `django`).
- Tests nuevos (6; `tests/test_vigilancia.py` ahora 276): paso único con SHA, nombre igual a `vig.ARTIFACT`, ruta, retención 90; `if: always()`; `if-no-files-found: ignore`; mismo SHA que `pr-meta.yml`; es el último paso y el script no imprime hallazgos; el aviso nombra el artefacto y no menciona el log.

## Verifica
- `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: 1463 passed, 2 failed (1465 tests); los 2 son los de la insignia del README (T53). `tests/test_vigilancia.py`: 276 passed.
- Contraprueba, 12 mutantes en copias limpias, uno por copia, lanzando desde la copia:
| Mutante | Fallan | Primer test en rojo |
|---|---|---|
| m1 adoptar sin autor ni etiqueta | 11 | `test_issue_ajena_con_el_mismo_titulo_no_se_adopta_ni_se_toca` |
| m2 adoptar sin etiqueta | 1 | `test_issue_del_bot_sin_etiqueta_security_no_se_adopta` |
| m3 no escapar `@` | 6 | `…[mencion-package]` |
| m4 no escapar `\|` | 7 | `…[barra-package]` |
| m5 aceptar salto de línea | 11 | `…[salto_final-package]` |
| m6 quitar `concurrency` | 1 | `test_concurrency_sin_cancelar_la_que_corre` |
| m7 versión fuera de código en línea | 35 | `test_cuerpo_lista_paquete_version_id_y_corregida` |
| m7b paquete fuera de código en línea | 26 | `test_cuerpo_lista_paquete_version_id_y_corregida` |
| m8 quitar el tope del cuerpo | 4 | `test_cuerpo_enorme_se_recorta_bajo_el_limite_de_github_y_lo_dice` |
| m9 subir el artefacto solo si el job acaba en verde (sin `if: always()`) | 1 | `test_artefacto_se_sube_tambien_con_el_job_en_rojo` |
| m10 aviso de recorte que no nombra el artefacto («en el log») | 1 | `test_aviso_de_recorte_nombra_el_artefacto_y_no_el_log` |
| m11 quitar `if-no-files-found: ignore` | 1 | `test_artefacto_no_falla_si_el_escaner_no_escribio_el_fichero` |

## Queda
- El artefacto contiene el JSON crudo del escáner (texto de terceros, descargable con permiso de lectura del repo; el repo es público, pero el artefacto de un repo público lo puede descargar cualquier usuario con sesión de GitHub). Es la misma información pública de OSV; no lleva datos del repo más allá de rutas de lockfile.
- Verificación real del paso en Actions: solo se ejecuta tras el merge; los tests comprueban la definición, no la subida.
