# T10 — Evaluación de tecnologías, estado de reglas y suscripciones (dev-proyecto v1.2)

## Qué se hizo
- `technologies/registry.template.yaml`: campos `vertical`, `evaluacion`, `reglas`, `suscripcion` en TEC-0001/0002 y 3 tecnologías ficticias nuevas (TEC-0003 firewall con reglas revisadas; TEC-0004 MDM con sobredespliegue; TEC-0005 SASE infrautilizado y renovación próxima). TEC-0002: firewall sin revisar desde 2025-11-01 con 6 any-any. TEC-0001: reglas `no_evaluable` con motivo («sin acceso a la consola»). Proveedores genéricos, sin datos reales.
- `smc/tech.py`: añadidos `evaluar_tecnologias`, `reglas`, `suscripciones` y `render_*`. `expiring`, `render_expiring` y `vulns` intactos.
- `technologies/README.md`: campos y API.
- `tests/test_tech_v05.py`: 11 tests.

## API para T14
`from smc import tech`; el registro es ruta YAML o dict; `hoy` siempre inyectable.
- `evaluar_tecnologias(registry) -> list[dict]` (id, nombre, vertical, cobertura_pct, configuracion, madurez, avisos); `render_evaluacion(filas) -> str`.
- `reglas(registry, hoy=None, dias=180) -> {revisadas, sin_revisar, no_evaluables, avisos}`. Cada fila: id, nombre, n_reglas, reglas_any_any, reglas_sin_uso (+ ultima_revision, dias_sin_revisar; `no_evaluables` lleva `motivo`, "SIN MOTIVO" más aviso si falta). Revisadas con más de `dias` pasan a `sin_revisar` (`caducada: True`). `render_reglas(res, hoy, dias) -> str` (sección «No evaluables» explícita).
- `suscripciones(registry, hoy=None, dias=90, umbral=0.70) -> {renovaciones, infrautilizadas, sobredespliegue, coste_por_proveedor {(proveedor, moneda): total}, avisos}`; `render_suscripciones(res, hoy, dias, umbral) -> str`.
- Datos mal formados (estado inválido, fecha mala, entradas de texto, bloque ausente) dan aviso, no excepción. Tecnologías sin bloque `reglas`/`suscripcion` se ignoran en esa vista.
- Constantes: `UMBRAL_REGLAS_DIAS=180`, `UMBRAL_INFRAUSO=0.70`.

## Verifica
`uv run --no-project --with pytest --with pyyaml python -m pytest -q` -> 89 passed (78 + 11; `smc expiring` y `smc vulns` siguen verdes).

## Contraprueba
Con `UMBRAL_INFRAUSO = 0.95` el test de suscripciones en rojo; restaurado a 0.70. Además `test_umbral_70_contraprueba` y `test_umbral_180_dias_contraprueba` cambian el umbral por parámetro y el resultado cambia.

## Decisiones / queda
- `vertical` no se valida contra el catálogo (lo hará una tarea posterior); los IDs VRT-EDR/NET/MDM/SASE son provisionales.
- Coste ocioso = coste × (1 − uso). Coste por proveedor separado por moneda.
- Sin tocar cli.py (integración en T14). PLAN.md sin marcar. Sin push.
