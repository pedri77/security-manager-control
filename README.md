# Security Manager Control (SMC)

Centro de control para el **Security Manager**: una única vista para saber qué necesita un cliente en materia de seguridad, qué tiene ya implantado, con qué evidencias, y dónde están los huecos.

> Estado: **v0.4.0**. Catálogos de controles, análisis de brechas con aplicabilidad ENS por categoría y priorización por riesgo, plan de acción, informe HTML autocontenido y dashboard estático multicliente. Todo local, sin servidor ni dependencias de red. La v0.5 (conectores de evidencias) queda fuera de esta versión.

## Qué cubre

| Bloque | Base | Cuándo aplica |
|---|---|---|
| **NIS2** | Directiva (UE) 2022/2555, Art. 20, 21, 23 + Reglamento de Ejecución (UE) 2024/2690 | Línea base para **todos** los clientes (entidad esencial / importante, o como marco de referencia voluntario) |
| **ENS** | Real Decreto 311/2022, Anexo II (73 medidas) | Sector público y proveedores del sector público |
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
│   ├── adr/ADR-00N-...md              # Decisiones de arquitectura (ADR-001, ADR-002)
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

1. **Alcance del cliente**, copiar `assessments/assessment.template.yaml`, rellenar perfil (sector, tamaño, ¿sector público?, categoría ENS).
2. **Selección de marcos**, NIS2 siempre; ENS si `sector_publico: true`; transversal y red siempre.
3. **Inventario**, recursos internos y externos (plantillas en `resources/`).
4. **Evaluación**, estado de cada control + evidencias.
5. **Informe de brechas**, `smc gap <fichero>` genera el informe en Markdown, con brechas ordenadas por prioridad (P1 a P3).
6. **Plan de acción**, rellenar `plan_accion:` en la evaluación y revisarlo con `smc plan <fichero>` (acciones vencidas y brechas P1 sin acción).
7. **Entrega**, `smc report` para el informe HTML de un cliente (imprimible a PDF desde el navegador) y `smc dashboard` para la vista multicliente.

## CLI

```bash
pip install -e .
smc validate                                              # valida catálogos
smc gap assessments/examples/ejemplo-ayuntamiento.yaml    # informe de brechas
smc gap assessments/examples/ejemplo-ayuntamiento.yaml -o informe.md
smc gap assessments/examples/ejemplo-ayuntamiento.yaml --hoy 2026-11-03   # fecha de referencia fija
smc plan assessments/examples/ejemplo-ayuntamiento.yaml                   # plan de acción: vencidas y brechas sin acción
smc report assessments/examples/ejemplo-ayuntamiento.yaml -o informe.html # informe HTML autocontenido
smc dashboard assessments/examples -o dashboard/                          # dashboard estático multicliente (abrir dashboard/index.html)
smc soc soc/incidents.template.csv                        # MTTD/MTTA/MTTC/MTTR y % SLA
smc mitre                                                 # cobertura ATT&CK de casos de uso
smc expiring technologies/registry.template.yaml --days 90
smc vulns vulnerabilities/tracker.template.csv            # CVEs abiertos y fuera de SLA
smc refs NIS2-21.2.b                                      # normativa y guías CCN-CERT de un control
```

`gap`, `plan`, `report` y `dashboard` aceptan `--hoy AAAA-MM-DD` para fijar la fecha de referencia (por defecto, la del sistema). `smc --version` muestra la versión instalada.

Las salidas (`informe.md`, `informe.html`, `dashboard/`) contienen datos de la evaluación: no las guardes dentro de este repositorio si son de un cliente real (ver ADR-001).

Los informes HTML y el dashboard son ficheros únicos con CSS en línea, sin JavaScript, fuentes ni recursos externos (ver ADR-002). Se pueden abrir sin conexión o enviar como adjunto.

Estados de control: `implementado` (1.0) · `parcial` (0.5) · `no_implementado` (0) · `no_aplica` (excluido) · sin evaluar (cuenta como 0 y se lista aparte).

## Convenciones

- IDs de control: `NIS2-21.2.a`, `ENS-op.acc.6`, `TRV-RGPD-01`, `NET-SEG-01`.
- Documentos versionados: `PRD-SMC-001-v1.md`, `ADR-001-<slug>.md`.
- Evidencia antes que checkbox: un control `implementado` sin evidencia se marca como aviso en el informe.

## Limitaciones conocidas (v0.4.0)

- **ENS sin contrastar:** 39 de las 73 medidas de `frameworks/ens/controls.yaml` llevan `verificar: true`. Su `categoria_minima` (y todos los `refuerzos_por_categoria`) se rellenó de memoria, sin la tabla del Anexo II del RD 311/2022 delante. Hasta revisarlas, la aplicabilidad por categoría no es definitiva y el TODO de cabecera del YAML se mantiene.
- **Posible discrepancia de ID:** en el RD 311/2022 `op.exp.10` es la protección de los registros de actividad y `op.exp.11` la protección de claves criptográficas; el catálogo tiene `op.exp.10` como claves. No se han cambiado IDs (son contrato, ADR-001); hay que revisar si falta una medida o está desplazada.
- **Criticidades NIS2:** el campo `criticidad` de `frameworks/nis2/controls.yaml` es un juicio inicial sin fuente normativa. Afecta al orden de prioridad, no al cumplimiento.
- **«Sin evaluar» pesa 0.75 en la prioridad** y puntúa como no cumplido. Una evaluación incompleta se llena de P1/P2 en «sin evaluar» y el semáforo del dashboard sale en rojo (media por debajo del 50 %); los dos ejemplos ficticios salen en rojo por eso. Es lo esperado, no una brecha real: el informe separa las brechas evaluadas de las pendientes de evaluar.
- La ley española de transposición de NIS2 sigue en tramitación: revisar el catálogo al publicarse en el BOE.
