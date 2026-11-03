# T22 · Documentación y versión 0.6.0

Agente: dev-proyecto · Rama `t22-v06` · Tarea: docs/plan/PLAN.md#T22 (plan sin marcar)

## Qué se hizo
- `smc/cli.py`: subcomando `smc visor <mapa.json> -o visor.html` (llama a `smc.visor.generar_visor`). JSON ilegible, inexistente o que no sea `smc-mapa/1`: `ERROR: ...` en stderr, rc 2 y sin fichero de salida.
- `tests/test_cli_v06.py` (12 casos con parametrización): visor genera HTML, JSON roto, esquema inválido (3), fichero inexistente, nombre `</script><img onerror>` escapado, ayuda, versión 0.6.0, cifra ENS 28 en README y PRD, comandos y badge de tests.
- README: badge 0.6.0 y 346 tests; sección «Visor 3D» con `docs/img/visor.png` y créditos (teardown de elvarofficial MIT sobre claude-motion de whaleyxbt MIT; three.js 0.186.1 MIT); `report --registry` y `visor` en comandos; ecosistema sin enlaces nuevos (ZTNA y vulnerabilidades por capa OSI «en preparación»); hoja de ruta v0.6 hecha y v0.7 con lo pendiente (28 medidas ENS por dimensión con CCN-STIC, visor en GPU integrada y móvil); aviso ENS reescrito (45 contrastadas, 28 de las 73 en `verificar`).
- PRD: RF-27 a RF-31, roadmap v0.6 hecha / v0.7 pendiente, sección 8 con la cifra 28 de 73.
- CHANGELOG 0.6.0; versión 0.6.0 en `pyproject.toml` y `smc/__init__.py`.
- Fuera del «Toca», necesario: `tests/test_t08.py` (`test_version_052` pasa a `test_version_060`, mismo fichero que T21 anotó para T22). Las aserciones de «39 de las 73» se reponen en `tests/test_cli_v06.py` con 28.
- `uv.lock` generado por uv, sin versionar.

## Cifras de los badges
versión 0.6.0 · tests 346 · verticales 20 · protocolos 28 · RSS 17 feeds, 13 verificados · NIS2 15 · ENS 73 · transversal 21 (red 20). Verificadas con `pytest` (346 passed), `smc list` y los YAML.

## Verifica
`uv run --extra dev pytest -q` -> 346 passed. Comandos del README, todos rc=0 sobre los ejemplos y plantillas: validate, list, gap (stdout y -o), plan, report (sin y con --registry), dashboard, soc, mitre (y --navigator), verticals, tech, subs, expiring, vulns, protocols (y SMB), rss (y --opml), mapa (con y sin --inventario/--evaluacion), visor, refs NIS2-21.2.b, --version. El visor del registro de plantilla pesa 578.826 bytes. gitleaks sin fugas (ver commit).

## Contrapruebas reales
- README con «39 de las 73»: `test_readme_y_prd_cifra_ens_verificar` en rojo; restaurado.
- Quitar `ValueError` del `except` en `smc visor`: 4 tests en rojo (esquema inválido x3 y JSON roto); restaurado.

## Queda
Contrastar las 28 medidas ENS por dimensión con CCN-STIC; visor en GPU integrada y móvil.
