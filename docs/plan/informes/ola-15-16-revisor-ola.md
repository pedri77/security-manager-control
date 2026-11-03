# Olas 15-16 · revisor-ola · revisión T30-T35 (88d4b5f..4503af9)

Veredicto: APTA con reservas. 595 tests verdes; `smc compare`, `smc soa` (csv, xlsx, html), `smc evidencias` y `smc report --anterior` rc=0 sobre los ejemplos. SHAs del workflow reales.

## Hallazgos
1. [V] media · T34/T35 · `smc/ai_act.py:375, 289-293`: `cambios_significativos: "sí"` (cadena) recorta como si no hubiera cambios, sin aviso; ausente también recorta (choca con «un dato ausente cuenta como no consta»).
2. [V] media · T32 · `smc/soa.py:32-34, 56`: `caduca` con hora (datetime de PyYAML) da `TypeError` sin capturar; `vigencia_dias` enorme da `OverflowError`.
3. [V] media · T32 · `smc/soa.py:170`: `\uFFFE`/`\uFFFF` producen un XLSX con XML mal formado.
4. [V] baja-media · T32/T35 · `smc/soa.py:43-62` frente a `smc/evidencias.py:32-74`: dos implementaciones de caducidad que discrepan (`vigencia_dias: -1`, `caduca: "20260101"`).
5. [V] media · T31 · `smc/compare.py:100-101, 157-162`: clasificación desde el YAML en bruto: quitar una brecha sale como «sin cambio»; IDs inexistentes y controles ENS no aplicables cuentan como «nueva brecha».
6. [V] baja · T35 · `smc/report_html.py:632`: `--anterior` con un YAML que no es un mapa da rc=0 y una evolución falsa.
7. [V] baja · T30/T35 · `.github/workflows/tests.yml:30-39`: el CI no ejecuta los comandos nuevos; matriz sin Python 3.10 aunque `requires-python` dice 3.10+.
8. [D] baja · T32 · `smc/soa.py:151`: CSV no neutraliza celdas que empiezan por espacio, `\n` o `＝` (ancho completo); sin comprobar en Excel/LibreOffice.
9. [V] baja · T35 · `CHANGELOG.md:7` dice «Ola 14-16»; la nota de AIA-070 lleva jerga del plan («Desde T34…»).
10. [V] baja · T35: tests fuera de «Toca» (solo cambio de versión, declarado). Aceptable.

## Comprobado sin defectos
`verificar_huellas` (traversal, absolutas, `~`, `C:\`, UNC, NUL, symlinks fuera, FIFO); escape HTML de Evolución, soa, régimen transitorio y retest fallido; prefijo de fórmulas en CSV para `= + - @ \t \r`; XLSX normal con dos hojas; CI con permisos mínimos y sin secretos; fechas del art. 111.2 con autoridad pública; evidencia caducada no cambia la puntuación; cifras de README; sin repos privados; ejemplos ficticios.

## Objetivo
Entregadas las cinco piezas de v0.8. Sin cubrir: caducidad de evidencias en el informe HTML; CI de los comandos nuevos.

Tareas a reabrir: ninguna. Hallazgos 1-9 van a T36.
