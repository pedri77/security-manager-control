# T03 — Plan de acción en la evaluación (dev-proyecto v1.2)

## Qué se hizo
- Sección `plan_accion:` en `assessments/assessment.template.yaml` y en el ejemplo ficticio del ayuntamiento (4 acciones; responsables por rol; una vencida, una hecha, una bloqueada, una en curso).
- `smc/plan.py`: dataclass `Accion`; `cargar_plan(assessment)` (tolerante: estado inválido -> pendiente con aviso, fecha inválida -> None con aviso, `controles` como str o lista); `vencidas(plan, hoy)` (no hecha y fecha estrictamente < hoy); `brechas_sin_accion(brechas, plan)` (IDs o tuplas `(Control, estado, notas)`; una acción `hecha` no cubre la brecha); `render_plan_md(plan, hoy, brechas=None)`.
- `tests/test_plan.py`: 8 tests con `hoy` inyectado (2026-11-03).

## Verifica
`uv run --no-project --with pytest --with pyyaml python -m pytest -q` -> 20 passed (12 originales + 8 nuevos).
Ejemplo carga sin avisos, controles existen en el catálogo, ACC-02 es la única vencida, NIS2-21.2.d queda sin acción.

## Contraprueba
Cambiar `<` por `<=` en `vencidas` -> `test_fecha_igual_a_hoy_no_vence` en rojo (1 failed, 19 passed). Revertido.

## Decisiones
- Una acción `hecha` no cuenta como cobertura de una brecha todavía abierta (si sigue en brecha, hace falta acción nueva).
- `render_plan_md` recibe `hoy` (y `brechas` opcional) en vez de leer la fecha del sistema; T04 integra.
- No se toca `gap.py` ni `cli.py`. Sin datos reales.

## Queda
Integración en informe y CLI (`smc plan`) en T04. PLAN.md sin marcar.

## Verificación del coordinador (2026-11-03)
- Superficie dev-proyecto: OK; gitleaks sin hallazgos; solo ficheros del Toca.
- Tests en worktree: verdes; en main tras fusionar: ver Libro (38 al final).
- Contraprueba: '<' por '<=' en vencidas -> test_fecha_igual_a_hoy_no_vence rojo (1 failed, 19 passed). Restaurado, diff limpio.
