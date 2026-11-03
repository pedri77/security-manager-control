# Módulo de Tecnologías

Registro único de las tecnologías de seguridad (y las de negocio que las sustentan): qué hay, quién lo gestiona, licencias, caducidades, configuración y estado de despliegue. Base para ENS op.exp.1–5, op.pl.3/5 y NIS2 21.2.e/21.2.i.

## Ficheros

| Fichero | Contenido |
|---|---|
| `registry.template.yaml` | Registro de tecnologías: producto, versión, licencias, caducidades, config, despliegue |

## Qué controla

- **Licenciamiento** — modelo, cantidad contratada vs desplegada, coste, renovación.
- **Caducidades** — licencias, soporte del fabricante (EoS/EoL), certificados, contratos.
- **Configuraciones** — baseline aplicada (CCN-STIC / CIS), dónde está la config versionada, última revisión.
- **Provisión y despliegues** — entornos, cobertura (%), método (manual, IaC, GPO, MDM), pendientes.
- **Relaciones** — vertical, casos de uso que alimenta, playbooks asociados, CVEs abiertos.

## Campos v0.5 (ejemplos ficticios en la plantilla)

- `vertical`: ID de vertical (se valida más adelante).
- `evaluacion`: `cobertura_pct`, `configuracion` (`bastionada | por_defecto | desconocida`), `madurez` 0-5.
- `reglas`: `estado` (`revisadas | sin_revisar | no_evaluable`), `ultima_revision`, `n_reglas`, `reglas_any_any`, `reglas_sin_uso`. Si `estado: no_evaluable`, `motivo` es **obligatorio** (p. ej. «sin acceso a la consola»): si no se pueden evaluar las reglas, se dice explícitamente y por qué. Revisadas hace más de 180 días cuentan como sin revisar.
- `suscripcion`: `proveedor`, `coste_anual`, `moneda`, `renovacion`, `propietario` (rol), `unidades_contratadas`, `unidades_en_uso`, `autorrenovacion`. Infrautilizada = uso por debajo del 70 %.

API (`smc/tech.py`, `hoy` inyectable): `evaluar_tecnologias`, `reglas`, `suscripciones` y sus `render_*` en Markdown.

## CLI

```bash
smc expiring technologies/registry.template.yaml --days 90   # caducidades en los próximos 90 días
```
