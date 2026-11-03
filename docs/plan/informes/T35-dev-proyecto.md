# T35 · dev-proyecto · Integración v0.8 y documentación

Rama `t35`. Sin push. Plan no marcado. Tests: 595 verdes (`uv run --extra dev pytest -q`; 19 nuevos en `tests/test_cli_v08.py`). `uv.lock` generado por `uv run`, no commiteado. gitleaks sobre lo staged: sin fugas.

## Qué se hizo
- `smc/cli.py`: `smc compare <anterior> <actual> [--hoy] [-o]`, `smc soa <evaluación> --formato csv|xlsx|html -o <fichero> [--hoy]`, `smc evidencias <evaluación> [--base] [--hoy]`, y `smc report --anterior`. rc 2 con ERROR para ficheros o datos no válidos. `-o` escribe donde diga el usuario (igual que los demás); el CSV se escribe en bytes UTF-8 (BOM de `a_csv`, sin traducir `\r\n`).
- `smc/report_html.py`: `render_evolucion` (todo escapado), `run_html(..., anterior=)`, y `render_ia` muestra el régimen transitorio del art. 111.2 (tabla propia por sistema, también si el sistema solo tiene obligaciones transitorias).
- `smc/dashboard.py`: `Fila.evid_caducadas` y columna «Evidencia caducada» en el índice.
- README (badge de CI del workflow de T30, versión, 595 tests, sección «Evolución, salida para auditor y evidencias» con mermaid, comandos en «Empezar» y «Comandos», estructura, hoja de ruta: v0.8 hecha y lo pendiente pasa a v0.9), PRD (RF-40 a RF-45, roadmap), CHANGELOG 0.8.0, versión 0.8.0 en `pyproject.toml` y `smc/__init__.py`.

## Verifica
- Todos los comandos `smc` ejecutables del README (25; mapa y visor repetidos a mano con ruta limpia): rc=0, salidas en directorio temporal. `smc soa` en los tres formatos rc=0 (CSV con BOM, XLSX con XML parseable y dos hojas, HTML sin JS).
- `test_version` y los tests de versión verdes con 0.8.0.

## Contraprueba
Sin los cambios de `cli.py` y `report_html.py` (git stash) `tests/test_cli_v08.py` queda en rojo. Dentro de los tests: orden invertido en compare da signo contrario y aviso; fichero inexistente rc=2; `--formato` ausente o inválido sale con 2; `=HYPERLINK` prefijado y `<script>` escapado; huella incorrecta avisa; ruta `../../etc/passwd` rechazada; sin `--anterior` no hay sección; `cambios_significativos: true` no genera tabla transitoria.

## Desviaciones y notas
- Ficheros fuera de «Toca»: `tests/test_cli_v06.py`, `tests/test_cli_v07.py`, `tests/test_t08.py` (solo cambia la versión 0.7.1 a 0.8.0 en sus aserciones de versión). `smc/catalog.py` no hizo falta tocarlo.
- Los tests antiguos exigen que el badge de tests sea >= nº de `def test_`; el badge dice 595 (= tests recogidos por pytest).
- Nota 2 de la ola 15: el aviso de evidencia caducada sigue en el Markdown de gap, no en `warnings`; `smc evidencias` imprime los avisos de cada evidencia.
- Nota 3: el CSV solo lleva la aplicabilidad; el README lo dice y remite al XLSX para las evidencias.
- El workflow de CI no se tocó (no ejecuta los comandos nuevos); se podrían añadir `compare`, `soa` y `evidencias` en una tarea posterior.
- `smc dashboard` ignora la subcarpeta `historico/` (solo lee `*.yaml` del primer nivel).
