# Módulo de Vulnerabilidades y Playbooks

Seguimiento de CVEs sobre las tecnologías registradas y playbooks de respuesta por tecnología y por caso de uso. Cubre NIS2 21.2.e (gestión y divulgación de vulnerabilidades) y ENS op.exp.4.

## Ficheros

| Fichero / carpeta | Contenido |
|---|---|
| `policy.yaml` | SLA de remediación por severidad y reglas de priorización (CVSS, EPSS, CISA KEV, exposición) |
| `tracker.template.csv` | Seguimiento de CVEs: tecnología afectada, estado, responsable, fechas |
| `playbooks/tecnologia/` | Qué hacer ante un CVE o incidente en una tecnología concreta (parcheo, mitigación, rollback) |
| `playbooks/caso-uso/` | Respuesta a la alerta de cada caso de uso del SOC (`soc/use-cases/catalog.yaml`) |

## Priorización

1. **CISA KEV** o explotación activa conocida → crítica, sin importar CVSS.
2. Activo **expuesto a Internet** → sube un nivel.
3. **EPSS ≥ 0,1** → sube un nivel.
4. Resto según CVSS base.

## CLI

```bash
smc vulns vulnerabilities/tracker.template.csv   # abiertas, vencidas por SLA, por tecnología
```

## Roadmap

- Ingesta automática desde NVD / CISA KEV / EPSS cruzando con el `cpe` del registro de tecnologías.
- Avisos CCN-CERT / INCIBE-CERT.
