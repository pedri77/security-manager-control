# T02 — Priorización por riesgo y mapeos completos

## Qué se hizo
- `mappings/nis2-ens-iso27001.csv`: las 15 filas NIS2 ya existían; se normalizó: IDs ENS con prefijo del catálogo (`ENS-org.1`), rango `op.acc.1-4` expandido, anotaciones de cláusulas ISO movidas a `notas`. Todos los ENS del CSV existen en el catálogo (73 medidas).
- `smc/mapping.py`: `cargar`, `equivalentes(control_id)` (NIS2<->ENS ambos sentidos), `normas_cubiertas`, `nis2_sin_fila`.
- `smc/priority.py`: `prioridad(control, estado, cliente) -> (0-100, P1|P2|P3)`.
  Fórmula: `60*estado + 20*criticidad + 10*entidad + 10*cobertura`. Estado: no_implementado 1, sin evaluar 0.75, parcial 0.5, implementado/no_aplica = (0, P3). Criticidad alta 1 / media 0.5 / baja 0 (defecto media). Entidad esencial 1 / importante 0.5 / otra 0. Cobertura (n_normas-1)/2 sobre NIS2, ENS, ISO27001. Umbrales: >=70 P1, >=40 P2.
- `frameworks/nis2/controls.yaml`: `criticidad` en los 15 controles (juicio inicial mío, a revisar: alta en gobernanza, riesgos, incidentes, continuidad, accesos, MFA y alerta/notificación 24h/72h; baja en evaluación de eficacia; resto media).
- `tests/test_priority.py`: 8 tests.

## Verifica
`uv run --no-project --with pytest --with pyyaml python -m pytest -q`: 20 passed (12 originales + 8).
Contraprueba: test que copia el CSV sin la fila NIS2-21.2.c y comprueba que `nis2_sin_fila` la señala (rojo si falta fila).

## Decisiones
- Estado "sin evaluar" (None) pesa 0.75; T04 puede decidir si lo usa.
- `mapping` acepta `path` opcional para poder testear con CSV alterado.
- Las criticidades son orientativas, sin fuente normativa.

## Queda
Integración en gap/CLI (T04). Ningún ISO del CSV se valida contra catálogo (no existe catálogo ISO).
