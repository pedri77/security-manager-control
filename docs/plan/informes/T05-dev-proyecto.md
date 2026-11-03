# T05 — Informe HTML autocontenido (dev-proyecto v1.2)

## Qué se hizo
- `smc/report_html.py`: HTML único, CSS en línea, sin JS, sin `<link>`/`<script>`/imágenes ni URLs. `@media print` para guardar como PDF. Todo texto (cliente, notas, títulos, acciones, avisos) pasa por `html.escape` (`_e`). Consume `Analisis` de T04, no reimplementa el análisis.
- Secciones: resumen ejecutivo (tabla por marco con barras CSS, nota de que «sin evaluar» puntúa como no cumplido, aviso P1 sin acción, top 10 P1 evaluadas, acciones vencidas), detalle por marco (brechas evaluadas, sin evidencia, sin evaluar aparte con heredado como sugerencia, medidas ENS que no aplican agrupadas por categoría mínima), plan de acción con vencidas y brechas sin acción, avisos.
- CLI: `smc report <assessment> -o informe.html [--hoy AAAA-MM-DD]` (`-o` obligatorio).
- `tests/test_report_html.py`: 7 tests.

## API para T06
`from smc.report_html import render_html, render_body, run_html, CSS`
- `render_html(analisis) -> str`: documento completo.
- `render_body(analisis, nivel=2) -> str`: solo el cuerpo (`<div class="smc-cuerpo">`), sin `<html>` ni título del cliente; `nivel` = nivel del primer encabezado (1 a 4). Necesita `CSS` y un contenedor con clase `smc` (como `<main class="smc">` en `render_html`).
- `run_html(path, hoy=None) -> str`.
- `_e` (escape) es reutilizable para nombres de cliente en el índice del dashboard, o usar `html.escape`.

## Verifica
`uv run --no-project --with pytest --with pyyaml python -m pytest -q` -> 55 passed (48 + 7). Informe del ejemplo generado en el scratchpad (25 KB) y revisado: estructura y tablas correctas.

## Contraprueba
Quitar `escape` de `_e` -> `test_xss_escapado` en rojo (1 failed, 54 passed). Restaurado. `test_contraprueba_sin_escape_rompe` fija el mismo efecto por monkeypatch.

## Decisiones / queda
- Sin `<details>` (no imprime cerrado): listas completas de «sin evaluar» en tablas.
- Columna «Refuerzos ENS» aparece también en marcos no ENS (valor «—»); cosmético.
- PLAN.md sin marcar. Sin push.
