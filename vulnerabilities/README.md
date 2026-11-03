# Módulo de Vulnerabilidades y Playbooks

Seguimiento de CVEs sobre las tecnologías registradas y playbooks de respuesta por tecnología y por caso de uso. Cubre NIS2 21.2.e (gestión y divulgación de vulnerabilidades) y ENS op.exp.4.

## Ficheros

| Fichero / carpeta | Contenido |
|---|---|
| `policy.yaml` | SLA de remediación por severidad y reglas de priorización (CVSS, EPSS, CISA KEV, exposición) |
| `tracker.template.csv` | Seguimiento de CVEs: tecnología afectada, estado, responsable, fechas |
| `protocols.yaml` | 28 protocolos por capa OSI: puertos, riesgos, CWE, mitigaciones, controles SMC, técnicas ATT&CK y URLs de búsqueda en fuentes oficiales |
| `sources.yaml` | Fuentes oficiales (NVD, ENISA EUVD, CISA KEV, CVE Details, INCIBE-CERT, CCN-CERT, MITRE) |
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

## Vulnerabilidades por protocolo

`protocols.yaml` no contiene CVEs: cada protocolo trae URLs de **búsqueda** en las fuentes de `sources.yaml` para consultar lo vigente. Los CWE y las técnicas ATT&CK son representativos y se contrastan con MITRE antes de citarlos. Las URLs no se han comprobado en línea (se generó sin red): verificarlas a mano; INCIBE-CERT y CCN-CERT enlazan a su listado sin filtro. CVE Details es un agregador comercial, no una fuente oficial.

Aprendizaje: [Modelo OSI](https://pedri77.github.io/modelo_OSI/), [Protección por capas OSI](https://pedri77.github.io/Basicos_Proteccion_Capas_OSI/), [ICS/OT](https://pedri77.github.io/ics-security-studio/) y [WAF](https://pedri77.github.io/wafforge/).

```python
from smc import protocols
protocols.validar()                    # [] si todo es correcto
protocols.por_capa()                   # {2: [...], 3: [...], 6: [...], 7: [...]}
print(protocols.render_protocolo("SMB"))
```

Hasta T14 no hay subcomando `smc protocols`.

## Roadmap

- Ingesta automática desde NVD / CISA KEV / EPSS cruzando con el `cpe` del registro de tecnologías.
- Avisos CCN-CERT / INCIBE-CERT.
