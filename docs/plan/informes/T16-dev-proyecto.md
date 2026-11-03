# T16 - Documentación y versión 0.5.0

Agente: dev-proyecto v1.2 · Rama `t16` (desde 9aa1c87) · Tarea: docs/plan/PLAN.md#T16

## Qué se hizo
- `README.md`: misma estructura, imágenes y paleta. Badges nuevos (versión 0.5.0, tests 196, verticales 19, protocolos 28, RSS 17/13 verificados). Tabla de módulos con verticales, tecnologías y reglas, suscripciones, protocolos, RSS y mapa; comandos `verticals`, `tech`, `subs`, `protocols`, `rss`, `mitre --navigator`, `mapa`. Sección «Ecosistema» (8 Pages y 2 repos públicos; pendientes: ZTNA, vulnerabilidades por capa OSI, visor 3D desde teardown con origen elvarofficial/teardown y whaleyxbt/claude-motion, MIT). Hoja de ruta: v0.5 hecha, v0.6 con lo pendiente. Aviso del ENS intacto; limitaciones nuevas sobre datos de muestra. Sin repos privados.
- `soc/README.md`: quitado «12 verticales», refleja las 19 de la v2, VRT-NET paraguas, `smc verticals` y `--navigator`.
- `docs/prd/PRD-SMC-001-v1.md`: RF-19 a RF-26 y roadmap v0.5 hecha / v0.6 pendiente.
- `CHANGELOG.md` 0.5.0; versión 0.5.0 en `pyproject.toml` y `smc/__init__.py`.
- Plantillas: `zona` y `capa_osi` ficticias en las 5 tecnologías del registro y en `AST-0001` del inventario.

## Fuera de «Toca» (necesario para dejar los tests verdes)
- `tests/test_t08.py`: la prueba de versión pasa a 0.5.0.
- `tests/test_mapa.py`: cinco tests dependían de que las plantillas no tuvieran zona; ahora usan copias sin `zona`/`capa_osi` (`REG_SIN`, `INV_SIN`) y se añade `test_plantillas_traen_zona_y_nada_cae_en_sin_zona`. 195 -> 196 tests.

## Verifica
- `uv run --no-project --with pytest --with pyyaml python -m pytest -q` -> 196 passed.
- Todos los comandos del README sobre ejemplos y plantillas (salidas en un temporal): validate, list, gap, plan, report, dashboard, soc, mitre, mitre --navigator, verticals (ayuntamiento y energía), tech, subs, expiring, vulns, protocols, protocols SMB, rss, rss --opml, mapa, refs, --version: rc=0.
- `smc mapa` con registro e inventario de plantilla + tracker + evaluación: 6 dispositivos, `sin_zona` = 0, avisos vacíos (antes todo en `sin_zona`). Solo con el registro: 5 dispositivos, 0 en `sin_zona`.

## Contraprueba
- Con las plantillas sin zona (las copias `REG_SIN`/`INV_SIN`) los dispositivos caen en `sin_zona` (test existente); quitar `zona` de una plantilla pone en rojo `test_plantillas_traen_zona_y_nada_cae_en_sin_zona`. Antes de adaptar los tests, 5 de mapa fallaban justo por esto.

## Cifras usadas
Tests 196 · controles NIS2 15, ENS 73, transversal 21, red 20 · verticales 19 · protocolos 28 · feeds 17 (13 verificados) · casos de uso 8 con playbooks PB-UC-001..008.

## Queda
Sin push, tarea no marcada. Pendiente humano: contraste del Anexo II del ENS con el BOE.
