# T27 · dev-proyecto · PMO: vida del proyecto, horas, costes y presupuesto

Rama t27-v07. Tests: 390 verdes (`uv run --extra dev pytest -q`; 363 previos + 27 en `tests/test_pmo.py`).

## Hecho
- `smc/pmo.py`: carga tolerante (avisos, nunca excepción), análisis con `hoy` inyectable, `render_markdown`, iCalendar.
- `pmo/proyecto.template.yaml` y `pmo/examples/ejemplo-energia.yaml` (cliente ficticio de `assessments/examples/ejemplo-energia.yaml`; tareas enlazadas a ENE-01..04 y a sus controles, que existen en esa evaluación; test que lo comprueba).
- `docs/pmo.md` (fórmulas EVM, caso a mano, API), `docs/adr/ADR-005-pmo-datos-de-cliente.md`, `.gitignore` (`pmo/*` salvo plantilla y ejemplos).

## Verifica
- EVM a mano (comentario en `test_evm_a_mano`): PV 500, EV 600, AC 450, CPI 1,33, SPI 1,20.
- Imputación a tarea inexistente: aviso y no cuenta. Importe no numérico (texto, NaN, bool): no rompe. Entradas mal formadas (None, lista, secciones de tipo erróneo): no rompe.
- `.ics`: CRLF en todas las líneas, plegado a 75 octetos sin partir UTF-8, escape de `\ ; ,` y saltos de línea (un salto no puede inyectar `END:VEVENT`), UID estable e independiente de `hoy`, DTSTAMP = `hoy`.
- Markdown: `<script>`, `<img>`, `|` en títulos escapados.

## Contrapruebas reales (mutar `smc/pmo.py`, ejecutar `tests/test_pmo.py`, restaurar)
| Mutación | Resultado |
|---|---|
| PV con `(hoy - inicio).days + 1` | 2 tests en rojo |
| Plegado a 76 octetos en vez de 75 | 2 en rojo |
| Quitar el escape de `;` | `test_ics_escapado` en rojo |
| Retrasada con `fin <= hoy` | 1 en rojo |
| Terminar líneas con `\n` en vez de CRLF | 7 en rojo |
| Aceptar tarifa negativa/no numérica sin aviso | `test_importes_no_numericos_no_rompen` en rojo |
Código restaurado tras cada una (cmp idéntico); 390 verdes.

## Decisiones
- Las imputaciones son la única fuente de horas reales; no hay `horas_imputadas` en la tarea (evita doble contabilidad).
- BAC de tarea = `presupuesto` si existe, si no horas estimadas × tarifa del responsable.
- Los costes no laborales sin `tarea` cuentan en el coste real por partida pero no en AC.
- Imputaciones y costes posteriores a `hoy` no cuentan (aviso).
- Suscripciones del registry: se muestran aparte (solo EUR; otras monedas con aviso), no entran en presupuesto ni AC.
- Retrasada: `fin < hoy` y avance < 100 (estricto, como `vencidas` de T03). Próximos eventos: de `hoy` a `hoy`+30 inclusive.
- Eventos de día completo (`VALUE=DATE`, DTEND exclusivo). Sin hora: el modelo no la tiene.

## Queda
- T28: CLI (`smc pmo`, `--ics`, `--registry`), informe HTML y `smc validate` de la plantilla (la plantilla tiene ceros y un `Consultor` con tarifa 0; carga sin avisos de formato).
- `uv.lock` sin versionar (no es del «Toca»).
