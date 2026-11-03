# ADR-001 — Catálogos como datos y datos de cliente fuera del repositorio

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-11-02 |

## Contexto

SMC necesita mantener marcos normativos que cambian (transposición NIS2 en España, guías CCN-STIC, nuevas versiones ISO) y evaluar clientes cuyos datos son confidenciales (brechas de seguridad, topologías de red, proveedores).

## Decisión

1. Los controles de cada marco se definen en **YAML** (`frameworks/*/controls.yaml`, `network/controls.yaml`) con IDs estables, y el código solo los lee.
2. Las **evaluaciones reales de clientes no se versionan** en este repositorio: `.gitignore` excluye `assessments/*` salvo plantillas y ejemplos ficticios. Se guardarán en un repositorio privado por cliente o en almacenamiento cifrado.
3. Primera interfaz: **CLI en Python** (`smc`), con salida Markdown. El dashboard web llega en v0.4 sobre el mismo modelo de datos.

## Consecuencias

- Actualizar un marco = PR sobre YAML, revisable sin tocar código.
- Los IDs (`NIS2-21.2.a`, `ENS-op.acc.6`, `NET-SEG-01`) son contrato: no se renombran, se deprecan.
- Hay que montar el almacenamiento de evaluaciones fuera del repo antes de usarlo con clientes reales.
