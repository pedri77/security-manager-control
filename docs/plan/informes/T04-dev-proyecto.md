# T04 — Integrar v0.2 en el análisis y el CLI (dev-proyecto v1.2)

## Qué se hizo
- `smc/gap.py`: `analyse(assessment, hoy=None)` devuelve un `Analisis` (dataclass). Aplicabilidad ENS con `ens.aplica` según `cliente.categoria_ens` (vacía/desconocida = ALTA con aviso en `warnings`). Brechas ordenadas por `priority.prioridad`. Heredado vía `mapping.equivalentes`. Plan de acción y aviso P1 sin acción. `run(path, hoy=None)` mantiene su firma (hoy opcional) y devuelve Markdown; nuevo `run_plan(path, hoy=None)`.
- `smc/cli.py`: `smc plan <assessment> [--hoy AAAA-MM-DD]`; `--hoy` también en `gap`. Fecha inválida = error de argparse.
- `tests/test_gap_v02.py`: 10 tests. `tests/test_smc.py` no se ha tocado (los 12 originales siguen verdes sin cambios).

## API estructurada (para T05/T06)
`from smc.gap import analyse, Analisis, FrameworkResult, Brecha, SinEvaluar`
- `Analisis`: `cliente: dict`, `results: list[FrameworkResult]`, `warnings: list[str]`, `hoy: date`, `categoria_ens: str|None` (normalizada; None si ENS fuera de alcance), `plan: list[plan.Accion]`, `vencidas: list[Accion]`, `p1_sin_accion: list[str]` (IDs, por puntuación desc.), `brechas_sin_accion: list[str]`. Iterable: `cliente, results, warnings = analyse(a)` sigue funcionando.
- `FrameworkResult`: `framework, total, aplicables, puntuacion (0-100), sin_evaluar: list[Control], brechas: list[Brecha] (orden prioridad desc., desempate por ID), sin_evidencia: list[Control], no_aplican: list[Control]` (solo ENS), `sin_evaluar_detalle: list[SinEvaluar]` (mismos controles, con prioridad, ordenados).
- `Brecha` (NamedTuple; los 3 primeros campos = tupla histórica): `control, estado, notas, puntuacion, nivel ("P1".."P3"), refuerzos: tuple[str]` (R1.. ENS exigibles en la categoría).
- `SinEvaluar`: `control, puntuacion, nivel, heredado_de: list[(id_equivalente, estado)], refuerzos`.
- Markdown: `render_markdown(analisis)` (acepta aún la firma vieja `(cliente, results, warnings)`); el bloque de plan: `_plan_section(analisis)` / `run_plan`.
- `hoy` se inyecta siempre; por defecto `date.today()`.

## Decisiones
- No cuentan: medidas ENS que no aplican (ni aplicables ni sin evaluar; se listan en «No aplican a la categoría X»). Una evaluación sobre una medida que no aplica se ignora en silencio.
- «Heredado»: control sin evaluar con equivalente (NIS2<->ENS del CSV) evaluado como implementado/parcial/no_implementado; solo sugerencia textual, no cambia puntuación ni lista de brechas. Aparece en la lista de sin evaluar (puede ser un estado negativo del equivalente: es informativo).
- Peso de «sin evaluar» sin reajustar (0.75): da muchos P1/P2 en sin evaluar en el ejemplo (62 ENS sin evaluar); es ruido esperado en una evaluación casi vacía. Se puede bajar en `priority.ESTADO` si se prefiere.
- El aviso «P1 sin acción» y `p1_sin_accion` solo consideran brechas evaluadas (no sin evaluar). Una acción `hecha` no cubre (regla de T03).
- Las 39 medidas `verificar: true` se tratan como las demás; no se marcan aparte en el informe (queda para T05 si se quiere una nota).
- Hallazgo: el ejemplo tiene `ENS-mp.if.6` como `no_aplica`, por lo que aplicables+no_aplican+1 = total.

## Verifica
`uv run --no-project --with pytest --with pyyaml python -m pytest -q` -> 48 passed (38 previos + 10 nuevos).
Ejemplo MEDIA: ENS 68 aplicables, 4 no aplican (solo-ALTA); NIS2-21.2.c y .d (P1) salen primero; `smc plan ... --hoy 2026-11-03` lista ACC-02 (VENCIDA) y avisa P1 sin acción: NIS2-21.2.d, ENS-op.mon.1.

## Contraprueba
Sustituir en `analyse` la condición de aplicabilidad ENS por `if False:` -> `test_media_excluye_medidas_solo_alta` y `test_contraprueba_forzar_alta_cambia_aplicables` en rojo (2 failed, 46 passed). Revertido. Además, forzar ALTA sube los aplicables ENS de 68 a 72.

## Queda
Informe HTML (T05) y dashboard (T06). PLAN.md sin marcar.
