# T29 · dev-proyecto · Endurecer v0.7 (v0.7.1)

Rama `t29-v071`. Sin push. Plan no marcado. Tests: 527 verdes (509 + 18 nuevos en `tests/test_t29.py`); `uv.lock` sin commitear.

## Tabla por hallazgo

Contraprueba real = se retiraron los cambios de `smc/`, `frameworks/`, `ai/` y `.gitignore` (git stash) y se ejecutó `tests/test_t29.py` sobre el código de v0.7.0: 12 en rojo, 6 en verde (los 6 son contrapruebas "no sube / no se emite" y los 2 de ATLAS, que pasan en ambos lados por diseño).

| # | Hallazgo | Test(s) | Contraprueba real (código antiguo) | Resultado |
|---|---|---|---|---|
| 1 | purple de otra técnica sube el caso | `test_h1_purple_de_otra_tecnica_no_sube_el_caso`, `test_h1_navigator_tambien_filtra_por_tecnica`, `test_h1_catalogo_real_uc002_no_sube_con_t1003` | UC con T1566.001 y `detectado` de T1003: antes 5, ahora 3. UC-002 real con T1003: antes 5, ahora 3 (su nivel del catálogo) | Arreglado (a) |
| 2 | `detectado` anterior cuenta tras un `no_detectado` posterior | `test_h2_un_no_detectado_posterior_anula_el_detectado`, `test_h2_mismo_dia_...`, `test_h1_h2_la_madurez_nunca_baja_del_catalogo` | antes 5, ahora 3. Con el `detectado` más reciente sigue subiendo a 5. Mismo día manda el no detectado; un ejercicio posterior a `hoy` no cuenta; el catálogo es el suelo | Arreglado (b) |
| 3 | `corregido` con retest `persiste`/`parcial` desaparece | `test_h3_corregido_con_retest_persiste_...`, `test_h3_parcial_igual_...` | antes: `abiertos == []`, sin `retest_fallido`; ahora abierto, fuera de SLA (63 d desde `fecha_deteccion`), en `retest_fallido`, con aviso y en el Markdown. Contraprueba de comportamiento: retest `corregido` o vacío no es abierto | Arreglado (c) |
| 4 | falta art. 111.2 | `test_h4_*` (5 tests) | antes: no existe AIA-070 ni `preexistente` (rojo); no se emite si el sistema no es preexistente (anterior al corte, mismo día, sin fecha, nivel sin alto riesgo) | Arreglado (d), con límite (ver abajo) |
| 5 | `*.ics` no ignorado | `test_h5_ics_en_gitignore` | rojo sin la línea | Arreglado (e) |
| 6 | AC con costes no laborales y BAC sin ellos, sin aviso | `test_h6_aviso_...`, `test_h6_contrapruebas_sin_aviso` | rojo sin el aviso; sin aviso con `presupuesto` explícito, sin costes, o con el coste en el futuro | Arreglado (f) |
| 9 | AML.T0101, AML.M0036, AML.M0037 sin comprobar | `test_h9_ids_atlas_usados_existen_en_atlas_2026_10`, `test_h9_contraprueba_un_id_inventado_no_pasa` | un id inventado (AML.T9999) falla la comprobación; añadir un id no fijado a `COMPROBACIONES` pone el test en rojo | Comprobado (g): los tres existen |

Además (h): informe T25 corregido (22 verticales, no 24; la fusión no se anotó en el plan). Versión 0.7.1 en `pyproject.toml`, `smc/__init__.py`, badge del README y CHANGELOG; tests de versión actualizados (`test_t08`, `test_cli_v06`, `test_cli_v07`).

## (d) Art. 111.2: cita literal del Ómnibus

Fuente: https://www.boe.es/doue/2026/1744/L00001-00041.pdf (Reglamento (UE) 2026/1744, DO L de 24.7.2026), `pdftotext -layout`, punto 39 a):

> «2. Sin perjuicio de que se aplique el artículo 5 con arreglo a lo dispuesto en el artículo 113, párrafo tercero, letra a), el presente Reglamento se aplicará a los operadores de sistemas de IA de alto riesgo, distintos de los mencionados en el apartado 1 del presente artículo, que se hayan introducido en el mercado o puesto en servicio antes de la fecha de aplicación del capítulo III a que se refiere el artículo 113, únicamente si, a partir de esa fecha, dichos sistemas se ven sometidos a cambios significativos en sus diseños. En cualquier caso, los proveedores y los responsables del despliegue de los sistemas de IA de alto riesgo destinados a ser utilizados por las autoridades públicas adoptarán las medidas necesarias para cumplir los requisitos y obligaciones establecidas en el presente Reglamento a más tardar el 2 de agosto de 2030.»

Implementación: AIA-070 (fuente OMNIBUS, roles proveedor y responsable del despliegue, niveles alto riesgo Anexo III y Anexo I, `aplica_desde` = fecha del capítulo III de su nivel) con la clave de catálogo nueva `preexistente: true`: solo se emite si el sistema declara `en_mercado_desde` estrictamente anterior a esa fecha. Con `autoridad_publica: true` y sin `cambios_significativos` la fecha pasa a 2030-08-02; con `cambios_significativos: true` se queda la del capítulo. Si falta `cambios_significativos` se asume que no hay y sale un warning. No lleva `verificar`: el texto está leído. Campos de inventario documentados en `ai/inventario.template.yaml`.

Límites (decisión mía, a revisar): la obligación avisa del régimen y fija la fecha, pero NO recorta las demás obligaciones del capítulo III de un sistema preexistente sin cambios (hacerlo sería una función nueva y T29 "no hace funciones nuevas"). Tampoco define «cambio significativo»: lo declara quien rellena el inventario. Las 31 obligaciones se reflejan en README y su test de cifras; el PRD (fuera de «Toca») sigue diciendo 30.

## (g) ATLAS

El `dist/ATLAS.yaml` de la raíz está obsoleto (cabecera: "deprecated", versión 5.6.0) y no contiene AML.T0101, AML.M0036 ni AML.M0037. El vigente es `dist/v6/ATLAS-2026.10.yaml` (también `ATLAS-latest.yaml`, 2026-10-28). Contra ese fichero existen los 18 ids usados por `COMPROBACIONES`; ninguno hubo que sustituir:

- AML.T0101 Data Destruction via AI Agent Tool Invocation
- AML.M0036 Limit AI Workload Resource Consumption
- AML.M0037 AI Agent Authority Expansion Controls

Los 18 ids con su nombre quedan fijados en el test (`ATLAS_2026_10`), sin red en la suite.

## Decisiones y notas

- (a)/(b) en `mitre.pruebas_purple(purple, hoy, tecnicas_por_caso)`: la técnica del ejercicio debe estar exacta en `mitre` del caso (una sub-técnica no casa con su padre; se mantiene el criterio literal del plan). La fecha del caso es la del `detectado` más reciente entre sus técnicas cuyo último ejercicio es `detectado`. Ejercicios sin fecha o posteriores a `hoy` se ignoran.
- (c) `EstadoHallazgos.retest_fallido` es un campo nuevo al final del dataclass (con valor por defecto). El HTML (`smc/report_html.py`, fuera de «Toca») no lo muestra como sección: los hallazgos salen en "Abiertos" y "Fuera de SLA" y el aviso aparece en la lista de avisos. Queda por si se quiere una sección propia.
- (f) El ejemplo `pmo/examples/ejemplo-energia.yaml` (fuera de «Toca») tiene costes en T-03 y T-04 sin `presupuesto`, así que ahora genera 2 avisos; `test_pmo.py::test_ejemplo_carga_y_enlaza_con_la_evaluacion` pasa de "sin avisos" a "exactamente esos dos". Alternativa: añadir `presupuesto` a esas tareas del ejemplo.
- Cifras: tests 509 a 527; obligaciones RIA 30 a 31.

## Lo que queda

- Sección HTML propia para `retest_fallido` y PRD (30 a 31 obligaciones): fuera de «Toca».
- Hallazgos 7 (cerrado con (h)), 8 y 10 son notas sin acción de código.
