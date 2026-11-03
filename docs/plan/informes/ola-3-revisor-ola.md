# Ola 3 · revisor-ola v1.1 · revisión final T01-T06 (24784db..fb7b4a9)

Veredicto: APTA con reservas. Ningún hallazgo [V] de severidad alta; ninguna tarea marcada como hecha sin hacer; las seis con evidencia real. Arreglar 1-3 antes de publicar.

## Comprobaciones
- [V] 65 tests verdes.
- [V] Hashes del plan existen; cada commit de tarea toca solo su «Toca».
- [V] Todas las lecturas YAML con `yaml.safe_load`; sin eval/exec/subprocess/pickle/red en `smc/`.
- [V] XSS: todo texto de evaluación y catálogos pasa por `_e` (html.escape, quote=True); atributos solo con slug `[a-z0-9-]` o clases de lista blanca.
- [V] Path traversal: nombre de salida por `slugify(f.stem)`; `../../etc` da `etc`.
- [V] Sin secretos ni datos reales en árbol ni historial; commits con email noreply; ejemplos ficticios.

## Hallazgos
1. [V] media · T04 · `smc/gap.py:125-127`: estado no válido saca el control del denominador e infla el cumplimiento (NIS2 23,3 % → 25,0 % con una errata). Arreglo: contarlo como sin evaluar con aviso.
2. [V] media · T01/T04/T05: las medidas ENS con `verificar: true` no se señalan en ningún informe; «no aplica a MEDIA» se presenta como hecho. Arreglo: marcarlas y avisar en el resumen.
3. [V] media · `.gitignore`: no ignora `*.html` ni `dashboard/`, y el README propone escribirlos en la raíz; riesgo de subir datos de cliente (ADR-001).
4. [V] media · T02 · `smc/priority.py:18-35`: todo no_implementado de criticidad media ya es P1; TRANSVERSAL y RED sin criticidad. Arreglo: recalibrar pesos o umbral y test.
5. [D] media · T01 · `frameworks/ens/controls.yaml`: op.cont.2/op.cont.3 como MEDIA sin `verificar` (posiblemente ALTA); mp.si.2 posiblemente desde MEDIA; numeración mp.info posiblemente desfasada respecto al RD 311/2022. Requiere contrastar con el BOE.
6. [V] baja · la cifra de medidas con `verificar` es 37, no 39 (grep contaba comentarios).
7. [V] baja · `smc/ens.py:27-29`: `categoria_minima` no válida se trata como ALTA (no conservador); no lo valida `smc validate`.
8. [V] baja · `smc/plan.py:37`, `smc/gap.py:93,124`: entradas mal formadas dan AttributeError en gap/plan/report.
9. [V] baja · `smc/dashboard.py:84-92`: el dashboard incluye `assessment.template.yaml` como cliente.
10. [V] baja · `smc/gap.py:168`, `smc/report_html.py:179`: la categoría ENS no se muestra con `proveedor_sector_publico`.
11. [V] baja · `smc/plan.py:74`: una acción `bloqueada` cubre la brecha (decisión no registrada).
12. [V] baja · `tests/test_dashboard.py:131`: aserción siempre cierta.
13. [V] baja · informes T05/T06 sin sección de verificación del coordinador (T05 la verificó la sesión principal: contraprueba XSS 1 failed, 6 passed).
14. [V] baja · PLAN.md con rutas locales y notas internas; decidir si se publican.

## Objetivo
v0.2-v0.4 cubierto en lo esencial (RF-07, RF-08, RF-09, prioridad, dashboard estático según ADR-002). Sin cubrir: contraste del Anexo II con la fuente; RF-05 (heredado solo sugiere); mapeos TRANSVERSAL/RED; RF-03 cumplimiento por dominio.

Tareas a reabrir: ninguna. Puntos 1-10 y 12 van a T08.
