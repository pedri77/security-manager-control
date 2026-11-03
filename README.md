# Security Manager Control (SMC)

Centro de control para el **Security Manager**: una única vista para saber qué necesita un cliente en materia de seguridad, qué tiene ya implantado, con qué evidencias, y dónde están los huecos.

> Estado: **v0.1 — esqueleto inicial**. Catálogos de controles, plantillas y un CLI mínimo de análisis de brechas.

## Qué cubre

| Bloque | Base | Cuándo aplica |
|---|---|---|
| **NIS2** | Directiva (UE) 2022/2555 — Art. 20, 21, 23 + Reglamento de Ejecución (UE) 2024/2690 | Línea base para **todos** los clientes (entidad esencial / importante, o como marco de referencia voluntario) |
| **ENS** | Real Decreto 311/2022 — Anexo II (73 medidas) | Sector público y proveedores del sector público |
| **Transversal** | ISO/IEC 27001:2022, RGPD/LOPDGDD, DORA, CIS Controls v8 | Temas de interés para cualquier organización |
| **Recursos internos** | Inventario propio | Activos, personas, procesos, herramientas y capacidades propias |
| **Recursos externos** | Inventario de terceros | Proveedores, cloud, MSSP/SOC, cadena de suministro |
| **Red** | Módulo especial | Segmentación, perímetro, exposición, DNS, Wi‑Fi, OT, monitorización |
| **SOC** | SLAs, MTTD/MTTA/MTTC/MTTR, KPIs, cobertura MITRE ATT&CK, casos de uso | Rendimiento del SOC y evaluación de 12 verticales clasificadas por NIS2 21.2 |
| **Tecnologías** | Registro de tecnologías | Licencias, caducidades (licencia, soporte, certificados), configuraciones, despliegues |
| **Normativa** | NIS2 completa + CCN-CERT | Directiva 2022/2555, Reglamento de Ejecución 2024/2690, guía técnica de ENISA, anteproyecto español; guías CCN-STIC, informes BP e instrucciones técnicas, enlazados a controles |
| **Vulnerabilidades** | CVEs + playbooks | Seguimiento de CVEs con SLA (KEV/EPSS/CVSS), playbooks por tecnología y por caso de uso |

> **NIS2 en España (nov. 2026):** la transposición se hace mediante el *Anteproyecto de Ley de Coordinación y Gobernanza de la Ciberseguridad* (aprobado en Consejo de Ministros el 14/01/2025), que sigue en tramitación. Los controles se basan en el texto de la Directiva y del Reglamento 2024/2690; revisar cuando se publique la ley en el BOE.

## Estructura

```
security-manager-control/
├── README.md
├── docs/
│   ├── prd/PRD-SMC-001-v1.md          # Requisitos de producto
│   ├── adr/ADR-001-...md              # Decisiones de arquitectura
│   └── templates/                     # Plantillas ADR / PRD
├── frameworks/
│   ├── nis2/controls.yaml             # Art. 20, 21.2 (a–j), 23
│   ├── ens/controls.yaml              # 73 medidas Anexo II RD 311/2022
│   └── transversal/controls.yaml      # Temas transversales
├── mappings/nis2-ens-iso27001.csv     # Correspondencias entre marcos
├── resources/
│   ├── internal/inventory.template.yaml
│   └── external/third-parties.template.yaml
├── network/
│   ├── README.md                      # Módulo de red
│   └── controls.yaml
├── normativa/
│   ├── nis2/nis2.yaml                 # Directiva, RE 2024/2690, ENISA, sectores, sanciones
│   └── ccn-cert/guias.yaml            # CCN-STIC, BP, ITS ↔ controles
├── soc/
│   ├── sla.yaml · metrics.yaml        # SLAs por severidad/tier y KPIs
│   ├── verticals.yaml                 # Verticales de seguridad ↔ NIS2 21.2
│   ├── use-cases/catalog.yaml         # Casos de uso ↔ MITRE ATT&CK
│   └── incidents.template.csv
├── technologies/registry.template.yaml
├── vulnerabilities/
│   ├── policy.yaml · tracker.template.csv
│   └── playbooks/{tecnologia,caso-uso}/
├── assessments/
│   ├── assessment.template.yaml       # Evaluación de un cliente
│   └── examples/ejemplo-ayuntamiento.yaml
├── smc/                               # CLI Python
└── tests/
```

## Flujo de trabajo

1. **Alcance del cliente** — copiar `assessments/assessment.template.yaml`, rellenar perfil (sector, tamaño, ¿sector público?, categoría ENS).
2. **Selección de marcos** — NIS2 siempre; ENS si `sector_publico: true`; transversal y red siempre.
3. **Inventario** — recursos internos y externos (plantillas en `resources/`).
4. **Evaluación** — estado de cada control + evidencias.
5. **Informe de brechas** — `smc gap <fichero>` genera el informe en Markdown.

## CLI

```bash
pip install -e .
smc validate                                              # valida catálogos
smc gap assessments/examples/ejemplo-ayuntamiento.yaml    # informe de brechas
smc gap assessments/examples/ejemplo-ayuntamiento.yaml -o informe.md
smc soc soc/incidents.template.csv                        # MTTD/MTTA/MTTC/MTTR y % SLA
smc mitre                                                 # cobertura ATT&CK de casos de uso
smc expiring technologies/registry.template.yaml --days 90
smc vulns vulnerabilities/tracker.template.csv            # CVEs abiertos y fuera de SLA
smc refs NIS2-21.2.b                                      # normativa y guías CCN-CERT de un control
```

Estados de control: `implementado` (1.0) · `parcial` (0.5) · `no_implementado` (0) · `no_aplica` (excluido) · sin evaluar (cuenta como 0 y se lista aparte).

## Convenciones

- IDs de control: `NIS2-21.2.a`, `ENS-op.acc.6`, `TRV-RGPD-01`, `NET-SEG-01`.
- Documentos versionados: `PRD-SMC-001-v1.md`, `ADR-001-<slug>.md`.
- Evidencia antes que checkbox: un control `implementado` sin evidencia se marca como aviso en el informe.
