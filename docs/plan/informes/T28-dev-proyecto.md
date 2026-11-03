# T28 · dev-proyecto · Integración v0.7 y documentación

Rama `t28-v07`, sin push, plan sin marcar. Versión 0.7.0. Tests: 509 verdes (`uv run --extra dev pytest -q`; 458 en la base + 50 en `tests/test_cli_v07.py` y 1 en `tests/test_resources.py`).

## Comandos nuevos

```
smc pentest <fichero> [--hoy AAAA-MM-DD]
smc purple <fichero> [--hoy AAAA-MM-DD]
smc ai <inventario> [--hoy AAAA-MM-DD]
smc pmo <proyecto> [--ics eventos.ics] [--registry r.yaml] [--assessment a.yaml] [--hoy AAAA-MM-DD]
smc mitre [--navigator [-o capa.json]] [--purple p.yaml] [--hoy AAAA-MM-DD]
smc report <evaluación> -o informe.html [--registry r.yaml] [--pentest p.yaml] [--purple p.yaml] [--ai inv.yaml] [--pmo proy.yaml] [--hoy ...]
smc dashboard <dir> -o <salida>     # acompañantes <evaluación>.pentest|purple|ai|pmo.yaml
smc validate                        # suma frameworks/ai-act/ y las plantillas de IA, pentest, purple y PMO
```
Fichero inexistente o datos no válidos: rc 2, `ERROR: <ruta>: <motivo>`, sin traceback. `smc ai` usa `estricto=False` (un nivel inexistente sale como «no clasificado», no rompe).

## Qué se hizo
- `smc/cli.py`: los cuatro subcomandos, `--purple` en `mitre`, flags de `report`, `--assessment` en `pmo`.
- `smc/mitre.py`: `pruebas_purple`, `madurez(..., purple=)`, `a_navigator(..., purple=)`, `nivel_caso(..., prueba_purple=)`. `smc/soc.py`: `mitre_coverage(..., purple=)` (necesario para `smc mitre --purple`, fuera de Toca).
- `smc/report_html.py`: `render_pentest`, `render_purple`, `render_ia`, `render_pmo`, `calcular_extras`, `run_html(..., pentest, purple, ai, pmo)`. Todo con `_e`; las fuentes del RIA con `_enlace` (solo https). La evaluación y el registro del cliente alimentan `analizar` del PMO.
- `smc/dashboard.py`: acompañantes por nombre exacto `<stem>.<tipo>.yaml`; sin evaluación o con datos rotos, aviso (no rompe). El purple del cliente sube la madurez solo en su página; `mitre.html` sigue común.
- `smc/catalog.py`: `validar_v07()`. `smc/gap.py` no se toca (no hizo falta; así `ai_act` -> `gap` no tiene ciclo).
- `.gitignore`: `offensive/*` y `ai/*` salvo plantillas y `examples/`.
- Ecosistema (decisión 3): ECO-ZTNA `estado: privado`, `url: null`, sin nombrar el repo. `smc/resources.py` admite `privado` (rechaza URL en privados y sigue rechazando repos no listados) y `tests/test_resources.py` ajustado; ambos fuera de Toca por la decisión.
- README (cifras reales: 22 verticales, 509 tests, 129 controles = 15 NIS2 + 73 ENS + 21 transversal + 20 red, 30 obligaciones RIA, 28 protocolos, 17 RSS/13 verificados), secciones Pentest y purple team, IA, PMO, mermaid, hoja de ruta (v0.7 hecha, v0.8 pendiente), frase de ZTNA sustituida. PRD: RF-32 a RF-39, M12-M14, roadmap. CHANGELOG 0.7.0. `tests/test_t08.py` y `tests/test_cli_v06.py`: versión 0.7.0.

## Decisión purple y madurez MITRE
Ejercicio `detectado` con fecha (no posterior a `hoy`) = `deteccion: probada` con `ultima_prueba` = el detectado más reciente: nivel 4, y 5 en los últimos 90 días. Solo con `--purple`. Sigue exigiendo playbook (como la prueba declarada) y un caso `deteccion: sin` no cambia; `parcial`, `no_detectado` y ejercicios sin fecha no suben nada; la madurez nunca baja. Documentado en el docstring de `smc/mitre.py`, README, PRD y CHANGELOG. Con el ejemplo: T1190 pasa de 3 a 4.

## Verifica
- Cada comando nuevo rc=0 sobre los ejemplos (pentest, purple, ai con la plantilla, pmo con `--ics --registry --assessment`, mitre `--purple`, report con las cuatro secciones, dashboard con acompañantes, validate «Catálogos OK»).
- Comandos del README rc=0 (test `test_comandos_del_readme_rc0` extrae y ejecuta las líneas `smc` del bloque «Empezar en 1 minuto»): validate, gap, report, dashboard, mapa, visor, pentest, purple, mitre --purple, ai, pmo (con --ics y --assessment), report con --pentest --purple --ai --pmo. Los del bloque «Comandos» llevan placeholders; sus subcomandos están cubiertos por los tests de CLI.
- XSS (`<script>alert(1)</script>` y `"><img onerror=...>`) en el título de una tarea PMO (retrasada, sin control y nombre del proyecto), en un hallazgo de pentest, en el inventario de IA y en una mejora purple: sale como `&lt;script&gt;` en el HTML (informe y dashboard) y en el Markdown.
- gitleaks: ver commit (sin fugas).

## Contrapruebas reales
| Mutación | Resultado |
|---|---|
| `_e` sin `escape` en `report_html.py` | 3 en rojo (XSS hallazgo/PMO, IA/purple, dashboard) |
| `madurez` ignorando `purple` (`pruebas = {}`) | 3 en rojo (T1190 4, caso recién probado = 5, CLI/Navigator) |
Restaurado tras cada una; 509 verdes. Además, tests de contraprueba: `validate` en rojo (rc 1) con un catálogo RIA roto o una plantilla de pentest rota; sin `--purple` la madurez es idéntica; ZTNA con URL de repo privado falla; el badge/versión antiguos ya no están en el README.

## Decisiones y queda
- Los acompañantes del dashboard casan por nombre exacto (no por prefijo) para no mezclar clientes.
- La plantilla de PMO se valida solo en avisos de carga (es tolerante por diseño).
- `uv.lock` sin versionar. Sin acción de prod (repo público: el push a main lo decide la sesión principal).
