# T34 · dev-proyecto · Flecos de la v0.7: art. 111.2 del RIA y retest fallido en el informe

Rama `t34`. Sin push. Plan no marcado. Tests: 543 verdes (527 + 16 nuevos en `tests/test_t34.py`); `uv.lock` generado por `uv run` y NO commiteado.

## (a) Art. 111.2 en `smc/ai_act.py`

Texto contrastado: apartado 2 del art. 111 en la copia del DOUE del RIA (BOE, `DOUE-L-2024-81079`, leído hoy) y en el Ómnibus (punto 39 a, cita literal en el informe T29). EUR-Lex (`eli/reg/2024/1689/oj` y las URL CELEX consolidadas) responde 202 sin cuerpo a clientes automáticos, así que no pude leer el consolidado allí: la nota de AIA-070 lo dice. El texto vigente: el Reglamento se aplica a los operadores de alto riesgo ya en el mercado antes de la fecha del capítulo III «únicamente si» hay cambios significativos de diseño; proveedores y responsables de sistemas para autoridades públicas, a más tardar el 2 de agosto de 2030.

Criterio de capítulo III: `es_capitulo_iii(articulo)` lee los números de artículo del campo `articulo` (se ignoran apartados: «art. 26.1» -> 26; «arts. 43, 47 y 48» -> 43, 47, 48) y exige que TODOS estén entre 6 y 49. Cita mixta = no recorta. Resultado en el catálogo: AIA-010 a 019, 030, 031, 040 a 046 (los de AIA-044 a 046 solo con su supuesto). Quedan fuera: art. 4 (AIA-001), 5, 50, 53-55, arts. 72-73 (AIA-020, capítulo IX) y AIA-070.

Comportamiento (solo niveles `alto_riesgo_*`, `en_mercado_desde` < fecha de la obligación para su nivel, `cambios_significativos` no verdadero; si falta el campo se asume que no hay, con el aviso de T29):
- Sin `autoridad_publica`: la obligación del capítulo III no se emite; sale en `ObligacionesSistema.regimen_transitorio` (`ObligacionTransitoria`, con `aplica_desde=None` y condición «solo con cambios significativos»).
- Con `autoridad_publica` y `hoy` < 2030-08-02: en `regimen_transitorio` con `aplica_desde=2030-08-02`. Con `hoy` >= 2030-08-02: vuelven a `obligaciones`, vigentes, con `aplica_desde=2030-08-02`.
- Con `cambios_significativos: true`: todo como antes (fecha del capítulo).
- AIA-070 sigue saliendo como aviso; su `nota` en el YAML está actualizada. `render_markdown` añade la tabla «Régimen transitorio» por sistema (escapada).

## (b) `smc/report_html.py`

`render_pentest` muestra, si `retest_fallido` no está vacío, la tabla «Retest fallido» (ID, título, resultado del retest, fechas de retest y detección, activo, control), toda escapada con `_e`.

## Verifica y contrapruebas (`tests/test_t34.py`)

- Anexo III en mercado desde 2026-01-01 sin cambios: ninguna obligación de capítulo III emitida ni pendiente, todas en `regimen_transitorio`; art. 4, AIA-020 y AIA-070 siguen.
- Contrapruebas: `cambios_significativos: true` devuelve todas (mismo conjunto que un sistema nuevo salvo AIA-070); `autoridad_publica` con `hoy` 2030-08-03 (y 2030-08-02) vuelven vigentes, con 2030-08-01 no; sin `en_mercado_desde` o posterior a la fecha no se recorta; Anexo I usa su fecha (2028-08-02); transparencia no se recorta; catálogo inyectado sin capítulo III no rompe.
- HTML: tabla y `<script>`/`<img>` escapados; sin tabla si el retest es `corregido`, vacío o el estado es `abierto`.
- Contraprueba real: con `smc/` y `frameworks/` del commit anterior (git stash) 14 de los 16 tests de `test_t34.py` quedan en rojo (los 2 verdes no dependen del código nuevo: contrapruebas de HTML sin tabla y plantilla válida). Con el código nuevo: 543 verdes.

## Decisiones y desviaciones

- El art. 111.2 dice «el presente Reglamento», no solo el capítulo III. Limité el recorte al capítulo III porque lo manda el plan; anotado en la `nota` de AIA-070. Consecuencia: las obligaciones fuera del capítulo III (arts. 72-73, 4, 50) se siguen emitiendo para un sistema preexistente.
- No se modela el apartado 111.1 (sistemas informáticos de gran magnitud del anexo X, plazo 2030-12-31); el apartado 2 los excluye.
- «Cambio significativo» lo declara quien rellena el inventario (no se define).
- `render_ia` del HTML (fuera de «Toca») no muestra `regimen_transitorio`: en el informe HTML esas obligaciones simplemente no aparecen. Queda para T35 o una tarea nueva. Tampoco se tocó el PRD (cifras de obligaciones sin cambio: 31).
- `uv run` generó `uv.lock`; sin commitear.
