# T07: Documentación y versión 0.4.0 (dev-proyecto v1.2)

## Qué se hizo
- `README.md`: estado v0.4.0; comandos `smc plan`, `smc report`, `smc dashboard` y `--hoy`; flujo ampliado (pasos 6 y 7); aviso de no guardar salidas de clientes reales en el repo; sección «Limitaciones conocidas» (39 medidas ENS `verificar: true`, posible discrepancia op.exp.10/op.exp.11, criticidades NIS2 como juicio inicial, peso 0.75 de «sin evaluar» y semáforo en rojo en evaluaciones incompletas, ley NIS2 en tramitación). Se sustituyeron las rayas largas por comas en todo el README.
- `docs/prd/PRD-SMC-001-v1.md`: roadmap con columna Estado (v0.1 a v0.4 hechas, v0.5 pendiente), riesgos actualizados, RF-07 ajustado (PDF = imprimir el HTML).
- `docs/adr/ADR-002-informes-html-y-dashboard-estatico.md`: nueva, siguiendo la plantilla (contexto, opciones, decisión, consecuencias; soberanía, sin servidor, stdlib, coherente con ADR-001).
- `CHANGELOG.md` con 0.1.0 a 0.4.0. Versión 0.4.0 en `pyproject.toml` y `smc/__init__.py`.

## Verifica
- `smc --version` -> `smc 0.4.0`.
- Todos los comandos del README ejecutados sobre los ejemplos (validate, list, gap con y sin -o y --hoy, plan, report, dashboard, soc, mitre, expiring, vulns, refs): rc=0. Salidas en el scratchpad, nada en el repo.
- `uv run --no-project --with pytest --with pyyaml python -m pytest -q` -> 65 passed.

## Contraprueba
`smc reprot ...` (comando mal escrito) -> `invalid choice`, rc=2.

## Decisiones / queda
- No se tocó código de `smc/` salvo `__init__.py`. PLAN.md sin marcar. Sin push.
- Las fechas del CHANGELOG para 0.2 a 0.4 son la de la sesión (todo se construyó el 2026-11-03).
- Queda la revisión humana de las 39 medidas ENS y del ID op.exp.10/11.
