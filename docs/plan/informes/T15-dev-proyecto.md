# T15 - Mapa 3D de dispositivos: contrato de datos y adaptación de teardown

Agente: dev-proyecto v1.2 · Rama `t15` (desde f5caf91) · Tarea: docs/plan/PLAN.md#T15

## Qué se hizo
- `smc/mapa.py`: `construir_mapa(registry, inventario, tracker, evaluacion, hoy, dias_reglas)` y `validar_mapa(mapa)`. JSON `schema: smc-mapa/1` con 8 zonas fijas (alineadas con NET-SEG-01), `sin_zona`, resumen y avisos. Dispositivos del registro y de `activos` del inventario con lista blanca de campos (sin propietario, coste, CPE, rutas ni notas). Reutiliza `tech.reglas` y `tech.evaluar_tecnologias`; SLA desde `vulnerabilities/policy.yaml`; madurez de vertical vía `verticals.evaluar(estricto=False)`.
- `smc/cli.py`: `smc mapa <registry> [--inventario --tracker --evaluacion --hoy --days] [-o]`. Stdout si no hay `-o`; rc=2 con fichero inexistente o YAML/CSV roto.
- `docs/mapa-3d.md`: diseño (qué se reutiliza de teardown y qué se cambia, esquema documentado, reglas del semáforo, boceto de vistas). `docs/adr/ADR-003-mapa-3d-desde-teardown.md` (Propuesta).
- `tests/test_mapa.py`: 23 tests.

## Verifica
- `uv run --no-project --with pytest --with pyyaml python -m pytest -q` -> 195 passed (172 + 23).
- Esquema: el JSON generado con registro (con zonas añadidas en un temporal), inventario, tracker y evaluación de energía pasa `validar_mapa`; sin rutas absolutas ni ruta del temporal en el texto (`contiene_ruta_absoluta`, y comprobación explícita).
- CLI sobre las plantillas con `--hoy 2026-11-03`: 6 dispositivos, 1 rojo (TEC-0002: KEV crítica fuera de SLA y 6 any-any), 2 ámbar, 1 gris (AST-0001, activo del inventario sin datos de reglas; el no evaluable con motivo del registro es TEC-0001, que sale ámbar por una vulnerabilidad fuera de SLA), 2 verdes. Corregido en T17 (hallazgo 12 de revisor-ola).

## Contrapruebas (aplicadas y revertidas)
- `dias > limite` -> `>=`: rojo `test_sla_estricto_en_el_limite`.
- No evaluable pintado de verde en vez de gris: rojo `test_no_evaluable_lleva_motivo_y_es_gris`.
- Ignorar la zona (todo a zonas): rojo `test_esquema_valido_con_plantillas`.
- Contraprueba pedida por el plan: dispositivo sin zona va a `sin_zona` con motivo y no rompe (`test_dispositivo_sin_zona_...`, `test_zona_desconocida_...`, `test_plantilla_sin_zonas_todo_en_sin_zona`); id duplicado, tracker huérfano y entradas mal formadas dan avisos, no excepción.

## Decisiones
- Las plantillas NO tienen `zona` ni `capa_osi` (no están en «Toca»): con ellas todo cae en `sin_zona`. Los campos son opcionales y están documentados; añadirlos a `registry.template.yaml` e `inventory.template.yaml` queda para T16 u otra tarea.
- Capa OSI: declarada (1-7) o aproximada por vertical, marcada en `capa_osi_origen`; si no, `null`.
- Semáforo: rojo (KEV o crítica fuera de SLA, o any-any), ámbar (otras fuera de SLA, reglas sin revisar/caducadas), gris (no evaluable o sin datos: nunca verde), verde. Zona = peor de sus dispositivos; zona vacía gris. Es criterio inicial, a validar con el Security Manager.
- `generado_para` es la `--hoy`, no la hora de ejecución: salida determinista.
- Activos del inventario sin bloque de reglas quedan `sin_datos` (gris).

## Queda
- Visor HTML 3D (siguiente paso), `zona`/`capa_osi` en plantillas, T16. Sin push; tarea no marcada.
