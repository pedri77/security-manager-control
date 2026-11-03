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

## CLI

```bash
smc expiring technologies/registry.template.yaml --days 90   # caducidades en los próximos 90 días
```
