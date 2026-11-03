# PRD-SMC-001 v1 — Security Manager Control

| Campo | Valor |
|---|---|
| Estado | Borrador |
| Versión | v1 |
| Fecha | 2026-11-02 |
| Autor | David Moya García |

## 1. Problema

El Security Manager de una organización (o el consultor que da servicio a varios clientes) no tiene una vista única que responda a: *¿qué me exige la normativa, qué tengo, con qué evidencia y qué me falta?* La información está repartida entre hojas de cálculo, informes de auditoría, herramientas de seguridad y contratos con proveedores.

## 2. Objetivo

Un centro de control que, a partir del perfil del cliente, determine los marcos aplicables, evalúe recursos internos y externos, y genere un plan de brechas priorizado y basado en evidencias.

## 3. Usuarios

- **Security Manager / CISO / RSI** — dueño del estado de seguridad.
- **Consultor GRC** — evalúa varios clientes con el mismo método.
- **Dirección** — consume el resumen ejecutivo (responsabilidad NIS2 Art. 20).

## 4. Alcance

| Módulo | Contenido | Prioridad |
|---|---|---|
| M1 NIS2 | Art. 20, 21.2 (a–j), 23; detalle Reglamento 2024/2690 | P0 |
| M2 ENS | 73 medidas Anexo II RD 311/2022 con categoría BÁSICA/MEDIA/ALTA | P0 (sector público) |
| M3 Transversal | ISO 27001, RGPD, DORA, CIS, IA, ciberseguro | P1 |
| M4 Recursos internos | Personas, activos, procesos, herramientas, capacidades | P0 |
| M5 Recursos externos | Proveedores, cloud, cadena de suministro, exposición | P0 |
| M6 Red | Segmentación, perímetro, acceso remoto, DNS, OT, monitorización | P0 |
| M7 Informes | Brechas, resumen ejecutivo, plan de acción | P0 |
| M8 SOC | SLAs por severidad y tier, MTTD/MTTA/MTTC/MTTR, KPIs, cobertura MITRE, casos de uso, madurez por vertical clasificada en NIS2 | P0 |
| M9 Tecnologías | Registro, licenciamiento, caducidades, configuraciones, provisión y despliegues | P0 |
| M11 Normativa | NIS2 completa (Directiva, RE 2024/2690, ENISA, transposición ES) y guías CCN-STIC / BP / ITS del CCN-CERT enlazadas a controles | P0 |
| M10 Vulnerabilidades | Seguimiento de CVEs con SLA, priorización KEV/EPSS, playbooks por tecnología y por caso de uso | P0 |

## 5. Requisitos funcionales

- RF-01 Determinar marcos aplicables a partir del perfil (sector, tamaño, sector público).
- RF-02 Evaluar cada control con estado + evidencias + notas.
- RF-03 Calcular cumplimiento por marco y dominio.
- RF-04 Marcar controles "implementados" sin evidencia.
- RF-05 Mapear controles entre marcos para evaluar una vez y reutilizar (NIS2 ↔ ENS ↔ ISO 27001).
- RF-06 Inventariar recursos internos y externos y enlazarlos a controles.
- RF-07 Generar informe de brechas en Markdown (v0.1) y PDF/HTML (v0.3).
- RF-08 Seguimiento del plan de acción (responsable, fecha, estado).
- RF-09 Aplicabilidad ENS por categoría y refuerzos.
- RF-10 Calcular MTTD/MTTA/MTTC/MTTR y % de cumplimiento de SLA por severidad desde exportación de incidentes.
- RF-11 Medir cumplimiento de plazos de notificación NIS2 (24 h / 72 h / 1 mes).
- RF-12 Cobertura MITRE ATT&CK por táctica; casos de uso sin probar o sin playbook.
- RF-13 Evaluar madurez (0–5) de cada vertical de seguridad y agregarla por medida NIS2 21.2.
- RF-14 Avisar de caducidades (licencia, soporte, certificados) y sobredespliegue de licencias.
- RF-15 Seguimiento de CVEs enlazado al registro de tecnologías (CPE) con SLA de remediación.
- RF-16 Playbooks versionados por tecnología y por caso de uso, enlazados desde ambos registros.
- RF-17 Desde cualquier control, consultar su base legal (NIS2/RE 2024/2690) y las guías CCN-CERT aplicables (`smc refs`).
- RF-18 Marcar guías pendientes de verificación y vigilar cambios de estado (p. ej. CCN-STIC 892 en revisión).

## 6. Requisitos no funcionales

- Datos de clientes fuera del repositorio público (ver ADR-001).
- Soberanía del dato: ejecución local u on-prem en UE.
- Catálogos como datos (YAML) versionados, revisables en PR.

## 7. Roadmap

| Versión | Entregable |
|---|---|
| v0.1 | Catálogos YAML, plantillas, CLI `smc gap` |
| v0.2 | Aplicabilidad ENS por categoría, priorización por riesgo, mapeos completos |
| v0.3 | Informe HTML/PDF y plan de acción |
| v0.4 | Dashboard web (centro de control) multicliente |
| v0.5 | Conectores de evidencias (EDR, SIEM, escáneres, EASM, firewall); ingesta NVD/KEV/EPSS; capa ATT&CK Navigator |

## 8. Riesgos y supuestos

- La ley española de transposición de NIS2 sigue en tramitación (nov. 2026): revisar catálogo al publicarse en el BOE.
- La aplicabilidad exacta por categoría ENS debe validarse contra el Anexo II y guías CCN-STIC.
