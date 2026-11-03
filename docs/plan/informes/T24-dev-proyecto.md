# T24: Pentesting (seguimiento) y purple team

## Qué se hizo
- `smc/offensive.py`: carga, validación, estado de hallazgos, análisis purple y `render_markdown`.
- `offensive/pentest.template.yaml`, `offensive/purple.template.yaml` y ejemplos ficticios en `offensive/examples/` (ADR-001).
- `tests/test_offensive.py`: 32 tests nuevos, `hoy` inyectado. Suite completa: 395 verdes.

## Reutilización (sin duplicar)
- SLA: se lee `vulnerabilities/policy.yaml` vía `smc.tech.POLICY_FILE`.
- Severidad efectiva: `smc.tech.severidad_efectiva` (sin tildes, KEV = crítica, desconocida = crítica con aviso).
- Casos de uso: `smc.mitre.cargar` (excluye retirados, que cuentan como inexistentes). Controles: `smc.catalog.load_all`.
- No se tocan `cli.py`, `mitre.py` ni catálogos.

## Decisiones
- Error (excepción `OffensiveError`, con `.errores`): id ATT&CK mal formado, caso de uso inexistente o retirado, estado, tipo, resultado o severidad fuera de lista, ids repetidos, campaña inexistente. Aviso: fechas ilegibles, CVSS fuera de 0-10, CWE mal formado, control SMC inexistente, técnica que no figura en el caso de uso, tiempo negativo o con no_detectado.
- Severidad de un hallazgo fuera de política = error (en el tracker de `tech` es crítica con aviso; aquí el dato lo escribe una persona en una plantilla y conviene fallar). `kev: true` opcional sí aplica la regla KEV.
- Fuera de SLA: abierto o en_remediacion, días desde `fecha_deteccion` estrictamente mayores que el SLA. Pendiente de retest: `corregido` sin `fecha_retest`. Aceptado sin revisión: sin `fecha_revision` (campo añadido a la plantilla).
- Cobertura purple: último ejercicio de cada técnica; detectado 1, parcial 0,5, no_detectado 0; por táctica del caso de uso. Ejercicio caducado: más de 365 días (estricto).
- No se sube la madurez MITRE (lo decide T28). Tipo de campaña `red_team` con guion bajo.

## Verifica
`uv run --extra dev pytest -q` -> 395 passed. `gitleaks git --staged` sin fugas.

## Contraprueba (real)
- `dias > sla[sev]` cambiado a `* 100`: 6 tests en rojo, entre ellos el hallazgo crítico abierto fuera de SLA.
- Comprobación de caso de uso desactivada: `test_caso_de_uso_inexistente_en_purple_da_error` y el de retirado en rojo.
Ambas revertidas; suite verde.

## Queda
- T28: CLI (`smc pentest`, `smc purple`), validación de plantillas en `smc validate`, informe HTML y madurez MITRE.
- `uv.lock` sin seguir (no se commitea).
