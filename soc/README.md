# Módulo SOC — Rendimiento y cobertura

Evalúa el rendimiento general del SOC (propio o externalizado) con datos, no con percepciones. Responde a NIS2 21.2.b (gestión de incidentes), 21.2.f (eficacia de las medidas) y Art. 23 (plazos de notificación).

## Componentes

| Fichero | Contenido |
|---|---|
| `sla.yaml` | SLAs por severidad (ack, contención, resolución) y por tier N1/N2/N3 |
| `metrics.yaml` | Catálogo de KPIs del SOC con fórmula, objetivo y umbral |
| `verticals.yaml` | 19 verticales (v2) con su clasificación NIS2, criterios de madurez y recursos públicos; VRT-NET es paraguas de FW, SASE, ZTNA y OSI (no puntúa si alguna de ellas está evaluada) |
| `use-cases/catalog.yaml` | Casos de uso de detección mapeados a MITRE ATT&CK, fuentes y playbook |
| `incidents.template.csv` | Formato de exportación de incidentes para calcular métricas |

## Cálculo

```bash
smc soc soc/incidents.template.csv      # MTTD, MTTA, MTTC, MTTR, cumplimiento de SLA por severidad
smc mitre                               # cobertura y madurez ATT&CK de los casos de uso (técnicas y tácticas)
smc mitre --navigator -o capa.json      # capa para ATT&CK Navigator
smc verticals <evaluación.yaml>         # madurez 0-5 por vertical y por medida NIS2
```

## Métricas principales

- **MTTD** detección = `detected_at - occurred_at`
- **MTTA** reconocimiento = `acknowledged_at - detected_at`
- **MTTC** contención = `contained_at - detected_at`
- **MTTR** resolución = `resolved_at - detected_at`
- **% SLA** = incidentes dentro de objetivo / total, por severidad
- **Tasa de falsos positivos**, **escalado N1→N2**, **carga por analista**, **cobertura MITRE**, **cobertura de fuentes de log**
