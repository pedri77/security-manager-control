# T17 · dev-proyecto v1.2 · Endurecer v0.5 (v0.5.1)

Rama `t17` desde main 9cd5ff0. Hallazgos 1-10 y 12 de `informes/ola-5-6-revisor-ola.md`, decisiones (a)-(k) del plan.

## Qué se hizo
- (a)(b) `tech.severidad_efectiva` y `normalizar_severidad`: minúsculas y sin tildes; KEV = crítica (SLA 7 d); severidad desconocida = crítica con aviso. `mapa._vulns` las usa y expone `kev_o_criticas_abiertas`; el semáforo pone al menos ámbar con KEV o crítica abierta aunque esté en SLA. `tech.vulns` (listado) usa la misma severidad.
- (c) `tech.reglas()` devuelve `any_any` (todo dispositivo con any-any > 0, sea cual sea el estado); `render_reglas` abre con una sección «ATENCIÓN».
- (d) `ResultadoVertical.puntua` / `detallada_en`; Markdown y HTML muestran «no puntúa (detallada en FW, SASE, ZTNA y OSI)» y la madurez como «—» (`gap.estado_vertical`).
- (e) `niveles` (descriptores 0-5 concretos y comprobables, adaptados) en las 19 verticales de `soc/verticals.yaml`; `validar_catalogo` exige los 6, no vacíos.
- (f) VRT-EDR: ENS-op.exp.6 (antes mp.eq.3). VRT-ENDUSER: ENS-op.exp.4 (antes mp.sw.2).
- (g) Los dos firewalls de `technologies/registry.template.yaml` pasan a VRT-FW (capa por defecto 4; la declarada, 3, manda). `docs/mapa-3d.md` ajustado (ejemplo, severidad efectiva, regla ámbar, campo nuevo).
- (h) `mitre.madurez`: táctica = mínimo de los casos activos (documentado en el docstring); `no_activos` aparte; `smc mitre` muestra la tabla por táctica y los no activos. La técnica sigue siendo el máximo.
- (i) `coste_anual` no numérico (texto, bool, vacío) da aviso y suma 0; `_num` ya no convierte `True` en 1.
- (j) `gap.md_texto` escapa `<`, `>`, `|` y saltos de línea en el Markdown de verticales (id, nombre, estado, producto, motivo, títulos, avisos).
- (k) Informe T15: el gris de la ejecución real es AST-0001 (comprobado ejecutando `construir_mapa` sobre las plantillas con `--hoy 2026-11-03`: TEC-0001 sale ámbar).
- Versión 0.5.1 (`pyproject.toml`, `smc/__init__.py`, badge del README), entrada en CHANGELOG, README: badge y árbol 196 -> 214 tests (único cambio de cifra).

## Verifica
`uv run --no-project --with pytest --with pyyaml python -m pytest -q` -> 214 passed (196 previos + 18 nuevos en `tests/test_t17.py`).

## Cambios en tests previos (justificados)
- `test_t08.py::test_version_050` -> `test_version_051` (versión y CHANGELOG).
- `test_mitre.py`: `test_tecnica_y_tactica_toman_el_maximo` -> `..._tecnica_toma_el_maximo_y_tactica_el_minimo` (decisión h: táctica 3 -> 2).
- `test_cli_v05.py::test_xss_en_motivo_escapado`: su contraprueba decía que el Markdown conservaba el payload; ahora lo escapa (hallazgo 10).
- `test_mapa.py`: el dict de vulnerabilidades suma `kev_o_criticas_abiertas`; la capa por vertical de TEC-0002 pasa de 3 a 4 (VRT-FW) y el test de capa declarada usa 2.

## Contrapruebas (ejecutadas: se rompe el código, se corre el test, se restaura)
| Hallazgo | Mutación | Resultado |
|---|---|---|
| 1 | quitar el ámbar por KEV/crítica abierta | `test_h1_kev_abierta_dentro_de_sla_no_es_verde` en rojo |
| 1 | no tratar KEV como crítica | `test_h1_kev_cuenta_como_critica_a_efectos_de_sla` en rojo |
| 2 | no normalizar tildes | `test_h2_severidad_con_tilde_y_mayusculas` en rojo |
| 2 | desconocida sin pasar a crítica | `test_h2_severidad_desconocida_es_critica_con_aviso` en rojo |
| 3 | `any_any` solo para sin_revisar | `test_h3_any_any_con_revision_reciente` en rojo |
| 4 | VRT-NET sin la marca «no puntúa» | `test_h4_vrt_net_no_puntua_en_markdown_y_html` en rojo |
| 5 | validador sin comprobar los 6 niveles | `test_h5_contraprueba_baremo_incompleto_o_vacio_falla` en rojo |
| 6 | VRT-EDR de nuevo con mp.eq.3 | `test_h6_mapeos_ens` en rojo |
| 7 | firewall de la plantilla de nuevo en VRT-NET | `test_h7_...` en rojo |
| 8 | táctica = máximo | `test_h8_tactica_es_el_minimo_de_los_activos` en rojo |
| 8 | los no activos cuentan | `test_h8_no_activos_aparte_y_no_cuentan` en rojo |
| 8 | CLI sin tabla por táctica | `test_h8_cli_expone_madurez_por_tactica` en rojo |
| 9 | sin aviso de coste | `test_h9_coste_no_numerico_avisa` en rojo |
| 10 | `md_texto` sin escape | `test_h10_markdown_escapa_html_y_pipes` en rojo |
| 12 | informe T15 con la atribución antigua | `test_h12_...` en rojo |
Cada test lleva además su contraprueba positiva (caso que debe seguir en verde: alta sin KEV en SLA, VRT-NET sin hijas puntúa, un solo caso, números sin aviso, texto normal sin cambios).

## Decisiones y lo que queda
- La técnica de Navigator sigue siendo el máximo de sus casos (el hallazgo solo pedía la táctica). Una táctica sin casos activos no aparece en `tacticas`.
- Los descriptores 0-5 son criterio inicial, a validar por el Security Manager (no tienen fuente normativa).
- `md_texto` no escapa `&` para no alterar texto existente; solo `<`, `>` y `|`.
- No tocados (fuera de T17): hallazgos 11, 13 y 14. Tarea no marcada.
