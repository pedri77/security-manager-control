# ADR-005: Los datos del PMO son datos de cliente y viven fuera del repositorio

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-11-03 |

## Contexto

El módulo PMO (`smc/pmo.py`) maneja presupuesto, horas imputadas, tarifas por rol, costes por proveedor y riesgos del proyecto. Son datos comerciales y de capacidad del cliente (y de la propia consultora) más sensibles que un catálogo de controles. ADR-001 ya fija que los datos de cliente no se versionan.

## Decisión

1. Los ficheros de proyecto reales (`proyecto.yaml` con presupuesto, horas, tarifas, costes) **no se versionan** en este repositorio, público. `.gitignore` excluye `pmo/*` salvo `pmo/proyecto.template.yaml` y `pmo/examples/` (ficticios).
2. Se guardan en un repositorio privado por cliente o en almacenamiento cifrado, junto a su evaluación (ADR-001).
3. El código no tiene dependencias de red: `smc pmo` lee el fichero indicado y escribe el informe y el `.ics` donde se le diga. Los `.ics` generados contienen títulos y fechas de eventos del cliente: tampoco se versionan.
4. Los ejemplos usan clientes e importes ficticios.

## Consecuencias

- El informe del PMO hereda la regla del informe HTML (ADR-002): salida con datos de cliente, fuera de git.
- Cuando el proyecto enlaza acciones del `plan_accion` de la evaluación, ambos ficheros se pasan por separado; el repositorio no los cruza.
- No hay base de datos ni servicio: la fuente de verdad es el YAML del cliente.
