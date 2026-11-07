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
