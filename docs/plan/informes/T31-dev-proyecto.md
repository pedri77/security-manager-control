# T31 — Comparación entre evaluaciones

## Qué hice
- `smc/compare.py`: `comparar(anterior, actual, hoy=None) -> Comparacion` y `render_markdown(comp)`. Usa `smc.gap.analyse` (puntuación por marco, P1, plan, categoría ENS) y `smc.verticals.evaluar(estricto=False)` (madurez). Solo usa la API documentada de gap.
- `assessments/examples/historico/ejemplo-energia-2026-q1.yaml`: mismo cliente ficticio, fecha 2026-07-15, con más brechas.
- `tests/test_compare.py`: 11 tests.

## Criterios de clasificación de controles (por estado en `evaluaciones`, ausente = sin_evaluar)
- cerrados: brecha (parcial/no_implementado) -> implementado/no_aplica.
- nuevas_brechas: no brecha -> brecha.
- mejoran: entre brechas, sube de rango; o sin_evaluar -> implementado.
- empeoran: entre brechas, baja de rango; o implementado -> sin_evaluar.
- sin_cambio: el resto.
- acciones cerradas: presentes en ambos planes, no `hecha` antes y `hecha` ahora.
- Avisos: clientes distintos (por `cliente.nombre`), fecha ausente, actual más antigua o igual, categoría ENS distinta (marco ENS con `comparable=False`), `verticales` solo en una.

## Verificación
`uv run --extra dev pytest -q` -> 538 passed (11 nuevos; los tests de dashboard no cambian con la subcarpeta, el dashboard solo lee `*.yaml` del primer nivel).
Deltas a mano en el test: NIS2 7,5/15=50,0 -> 8/15=53,3 (+3,3); RED 3/20=15,0 -> 4/20=20,0 (+5,0); madurez 21/8=2,62 -> 27/9=3,00 (+0,38).

## Contraprueba
`test_contraprueba_intercambio...`: intercambiar anterior y actual da -3,3, -5,0, -0,38, invierte cerrados/nuevas brechas y avisa de «más antigua». Clientes distintos y categoría ENS distinta avisan (y con misma categoría no).

## Dudas / desviaciones
- `fecha` se lee de `cliente.fecha` (como en el ejemplo) o de `fecha` en raíz.
- No hay `smc compare` en la CLI (fuera de Toca; lo integra T35).
- Los delta de verticales se calculan solo para las que puntúan en ambas; una vertical solo presente en una sale con delta nulo.
