# T14 - Integración v0.5 en CLI, validate, informe y dashboard

Agente: dev-proyecto v1.2 · Rama `t14` (desde 4560b02) · Tarea: docs/plan/PLAN.md#T14

## Qué se hizo
- `smc/cli.py`: subcomandos `verticals <evaluación>`, `tech <registry> [--hoy --days]`, `subs <registry> [--hoy --days]`, `protocols [ID]`, `rss [--opml -o]`, `mitre [--navigator -o capa.json] [--hoy]`. `smc mitre` sin flags conserva su salida. `protocols` con ID desconocido y `verticals` con `no_evaluable` sin motivo dan rc=2 con mensaje en stderr. Sin `-o`, OPML y Navigator van a stdout.
- `smc/catalog.py`: `validar_casos_uso()` (IDs únicos, estado, deteccion, técnicas `Txxxx[.xxx]`, playbook existente, vertical existente) y `validar_v05()` (verticales, protocolos+fuentes, RSS+ecosistema, casos de uso, y `vertical` de RSS y del registro de tecnologías contra el catálogo de verticales). `smc validate` los suma.
- `smc/gap.py`: `Analisis.verticales` (campo nuevo al final, `None` si la evaluación no trae `verticales:`); `analyse` usa `evaluar(estricto=False)` y los errores/avisos pasan a `warnings`. `url_https()` (solo `https://`, sin espacios ni `<>"`), `render_verticales_md()`; el informe Markdown suma la sección «Verticales» (madurez, no evaluables con motivo, recursos públicos).
- `smc/report_html.py`: sección «Verticales» (tabla con barra, no evaluables con motivo, recursos). Todo por `_e`; `href` solo si `url_https`, si no queda texto sin enlace. Recursos pendientes como «(pendiente)» sin URL.
- `smc/dashboard.py`: columna «Madurez verticales» (`Fila.vert_media`, «—» si no hay dato).
- Tests existentes ajustados (`test_report_html.py::test_autocontenido`, `test_dashboard.py::test_sin_recursos_externos_ni_js`): prohibían cualquier `https://`; ahora admiten solo `<a href="https://...">` (enlaces, no cargan nada) y siguen prohibiendo script/link/img/iframe, `@import`, `url(`.
- `tests/test_cli_v05.py`: 21 tests nuevos.

## Verifica
- `uv run --no-project --with pytest --with pyyaml python -m pytest -q` -> 172 passed (151 + 21).
- Comandos rc=0 sobre ejemplos y plantillas (energía, ayuntamiento, `assessment.template.yaml`, `registry.template.yaml`): validate, verticals, tech, subs, protocols, protocols SMB, rss, rss --opml -o, mitre, mitre --navigator -o.
- `smc validate` rc=0 con los catálogos de la ola 5 tal cual (no se tocó ningún catálogo).

## Contrapruebas
- Quitar el escape de `_e` en report_html: falla `test_xss_en_motivo_escapado`.
- Quitar el filtro https de `url_https`: falla `test_javascript_url_no_sale_como_href`.
- Un error en `protocols.validar` hace que `smc validate` dé rc=1; casos de uso con datos rotos y una vertical inexistente en RSS dan errores concretos.

## Decisiones
- Los avisos de `verticales:` se añaden a `warnings` del análisis (no rompen informe/dashboard); el comando `smc verticals` es estricto.
- La validación de la vertical de las tecnologías se hace sobre `technologies/registry.template.yaml` (único registro versionado).
- Markdown no escapa (es texto plano), pero filtra los enlaces a `https://`.

## Queda
- T15 (mapa) y T16 (docs/versión). Sin push, tarea no marcada.
