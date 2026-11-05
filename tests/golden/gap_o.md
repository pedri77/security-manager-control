# Informe de brechas — Distribuidora Eléctrica Ejemplo, S.A.

- Sector: Energía (distribución eléctrica) · Entidad NIS2: esencial · Sector público: no
- Fecha: 2026-10-28

## Resumen

| Marco | Controles | Aplicables | Cumplimiento | Brechas | Sin evaluar | No aplican |
|---|---|---|---|---|---|---|
| NIS2 | 15 | 15 | 53.3% | 5 | 4 | 0 |
| TRANSVERSAL | 21 | 21 | 28.6% | 3 | 13 | 0 |
| RED | 20 | 20 | 20.0% | 3 | 14 | 0 |

## NIS2

### Brechas (por prioridad)

| P | Control | Título | Estado | Refuerzos ENS | Notas |
|---|---|---|---|---|---|
| P1 | NIS2-21.2.d | Seguridad de la cadena de suministro | no_implementado | — | Sin evaluación de riesgos de proveedores críticos de OT |
| P1 | NIS2-21.2.c | Continuidad de negocio, copias de seguridad, recuperación y gestión de crisis | parcial | — | Pruebas de restauración solo en sistemas corporativos, no en OT |
| P1 | NIS2-23.notificacion | Notificación del incidente en 72 h | parcial | — | Plantilla de notificación a las 72 h sin validar |
| P2 | NIS2-20.2 | Formación del órgano de dirección | parcial | — | Formación directiva solo a una parte del consejo |
| P2 | NIS2-21.2.e | Seguridad en adquisición, desarrollo y mantenimiento; gestión y divulgación de vulnerabilidades | parcial | — |  |

### Evidencia caducada (1)

> **Aviso:** todas las evidencias de estos controles han caducado; renovarlas. No afecta a la puntuación de cumplimiento.

- NIS2-21.2.a — Análisis de riesgos y políticas de seguridad de los sistemas de información

### Sin evaluar (4)

- P1 · NIS2-21.2.i — Seguridad de RR. HH., control de acceso y gestión de activos
- P2 · NIS2-21.2.g — Ciberhigiene básica y formación
- P2 · NIS2-21.2.h — Criptografía y cifrado
- P2 · NIS2-23.final — Informe final en un mes

## TRANSVERSAL

### Brechas (por prioridad)

| P | Control | Título | Estado | Refuerzos ENS | Notas |
|---|---|---|---|---|---|
| P1 | TRV-TI-01 | Threat intelligence y vigilancia de exposición digital (dark web, typosquatting, filtraciones) | no_implementado | — | Sin inventario de dependencias de terceros |
| P2 | TRV-EDR-01 | EDR desplegado en servidores y puestos | parcial | — | EDR en el 70 % de los equipos |
| P2 | TRV-VUL-01 | Escaneo continuo y SLA de remediación por criticidad | parcial | — | Parcheo mensual en TI, trimestral en OT |

### Sin evaluar (13)

- P2 · TRV-AI-01 — Inventario y política de uso de IA (shadow AI, fuga de datos a LLMs)
- P2 · TRV-CLOUD-01 — Postura cloud (CSPM) y gestión de configuraciones
- P2 · TRV-DATA-01 — Clasificación y DLP sobre información sensible
- P2 · TRV-DET-02 — Casos de uso mapeados a MITRE ATT&CK con cobertura medida
- P2 · TRV-DORA-01 — Si es entidad financiera, evaluar DORA (TIC, pruebas TLPT, registro de proveedores TIC)
- P2 · TRV-GOB-02 — Comité de seguridad con reporte periódico a dirección
- P2 · TRV-GOB-03 — Presupuesto y plan director de seguridad
- P2 · TRV-ID-01 — Gestión centralizada de identidades y ciclo de vida (joiner/mover/leaver)
- P2 · TRV-ID-02 — Gestión de cuentas privilegiadas (PAM) y tiering
- P2 · TRV-RGPD-02 — EIPD para tratamientos de alto riesgo
- P2 · TRV-RGPD-03 — Notificación de brechas a la AEPD en 72 h
- P2 · TRV-SEG-01 — Ciberseguro alineado con el riesgo residual
- P2 · TRV-VUL-02 — Pentest / red team periódico

## RED

### Brechas (por prioridad)

| P | Control | Título | Estado | Refuerzos ENS | Notas |
|---|---|---|---|---|---|
| P1 | NET-SEG-02 | Red de gestión out-of-band separada | no_implementado | — |  |
| P2 | NET-OT-01 | Separación IT/OT (modelo Purdue / IEC 62443) e inventario OT | parcial | — | Inventario OT incompleto |
| P2 | NET-SEG-01 | Segmentación por zonas (usuarios, servidores, DMZ, gestión, invitados, OT/IoT) | parcial | — | Separación TI/OT con cortafuegos, sin DMZ industrial |

### Sin evaluar (14)

- P2 · NET-ACC-02 — Acceso de terceros controlado, temporal y registrado
- P2 · NET-CRY-01 — TLS 1.2+ en tránsito y protocolos inseguros deshabilitados (Telnet, SMBv1, SNMPv1/2)
- P2 · NET-DNS-01 — DNS protector/filtrado y registro de consultas
- P2 · NET-DNS-02 — DNSSEC y control de dominios propios (expiración, registros huérfanos)
- P2 · NET-HARD-01 — Bastionado de equipos de red (guías CCN-STIC / CIS) y credenciales por defecto eliminadas
- P2 · NET-INV-01 — Diagrama de red actualizado (L2/L3, zonas, flujos)
- P2 · NET-INV-02 — Inventario de dispositivos de red con versión de firmware y fin de soporte
- P2 · NET-MON-02 — NDR / IDS en puntos clave y visibilidad de tráfico (NetFlow)
- P2 · NET-NAC-01 — Control de acceso a red (802.1X / NAC) para dispositivos
- P2 · NET-PER-01 — Firewall perimetral con política deny-by-default y revisión periódica de reglas
- P2 · NET-PER-02 — Superficie expuesta a Internet inventariada (EASM) y justificada
- P2 · NET-PER-03 — WAF y protección anti-DDoS en servicios publicados
- P2 · NET-RES-01 — Redundancia de enlaces y equipos críticos; backup de configuraciones
- P2 · NET-SEG-03 — Microsegmentación / filtrado este-oeste en servidores críticos

## Verticales

Madurez media de las verticales evaluadas: 3.0 / 5

| Vertical | Estado | Madurez (0-5) | Producto |
|---|---|---|---|
| VRT-EDR Endpoint (EDR/XDR) | evaluada | 4 | EDR ejemplo |
| VRT-IAM Identidad y su seguridad (IAM, IGA, PAM, MFA, ITDR) | evaluada | 4 | — |
| VRT-NET Red (paraguas; detalle en VRT-FW, VRT-SASE, VRT-ZTNA y VRT-OSI) | no puntúa (detallada en FW, SASE, ZTNA y OSI) | — | — |
| VRT-FW Firewall | evaluada | 4 | Firewall ejemplo |
| VRT-SASE SASE / SSE (SWG, CASB, FWaaS) | sin_evaluar | — | — |
| VRT-ZTNA ZTNA (acceso de confianza cero) | evaluada | 1 | — |
| VRT-OSI Protección on-prem por capas OSI | sin_evaluar | — | — |
| VRT-MAIL Correo electrónico | sin_evaluar | — | — |
| VRT-CLOUD Cloud (IaaS/PaaS/SaaS) | sin_evaluar | — | — |
| VRT-APP Aplicaciones y web | sin_evaluar | — | — |
| VRT-DATA Seguridad del dato (clasificación, DSPM, DLP, cifrado y retención) | evaluada | 3 | — |
| VRT-BCK Copias y recuperación | sin_evaluar | — | — |
| VRT-VULN Gestión de vulnerabilidades | sin_evaluar | — | — |
| VRT-OT OT / IoT | evaluada | 2 | — |
| VRT-TPRM Terceros y cadena de suministro | sin_evaluar | — | — |
| VRT-AWARE Concienciación | sin_evaluar | — | — |
| VRT-HUNT Threat Hunting | no_evaluable | — | — |
| VRT-MDM Gestión de dispositivos móviles (MDM/UEM) | sin_evaluar | — | — |
| VRT-ENDUSER Puesto de usuario | sin_evaluar | — | — |
| VRT-GRC Gobierno, riesgo y cumplimiento (GRC) | evaluada | 4 | — |
| VRT-AI Inteligencia artificial (inventario, gobierno y seguridad de agentes y LLM) | evaluada | 2 | — |
| VRT-OFF Seguridad ofensiva (pentesting, purple team y red team) | evaluada | 3 | — |

### No evaluables

- VRT-HUNT Threat Hunting: Sin telemetría centralizada para cazar

### Recursos públicos

- VRT-EDR: [EDR/XDR (visual)](https://pedri77.github.io/edr-visual-app/)
- VRT-FW: [Firewalls básicos](https://pedri77.github.io/Basic_Firewalls/)
- VRT-OT: [ICS/OT Security Studio](https://pedri77.github.io/ics-security-studio/)
- VRT-HUNT: [Feeds de inteligencia de amenazas](https://github.com/pedri77/threat-intelligence-feeds)

## Madurez MITRE ATT&CK

**Catálogo de casos de uso del SOC (común a todos los clientes).** No describe al cliente: es la cobertura del SOC.

Técnicas con caso de uso: 13 · Casos de uso: 8

| Táctica | Madurez (0-5) |
|---|---|
| credential-access | 3 |
| execution | 3 |
| impact | 3 |
| initial-access | 3 |

### Casos sin playbook (0)

- Ninguno

## Plan de acción

| ID | Controles | Acción | Responsable | Fecha objetivo | Estado |
|---|---|---|---|---|---|
| ENE-04 | TRV-EDR-01 | Completar el despliegue de EDR | Responsable de puesto de trabajo | 2026-09-30 | hecha |
| ENE-02 | NIS2-21.2.c | Probar la restauración de copias en sistemas OT | Responsable de OT | 2026-10-30 | en_curso (VENCIDA) |
| ENE-01 | NIS2-21.2.d, TRV-TI-01 | Evaluar a los proveedores críticos de OT y mantener el inventario de terceros | Responsable de compras y CISO | 2027-01-31 | en_curso |
| ENE-03 | NET-SEG-02, NET-SEG-01 | Crear DMZ industrial y microsegmentar el entorno OT | Responsable de redes | 2027-06-30 | pendiente |

Acciones vencidas a 2026-11-03: 1

### Brechas sin acción (6)

- NIS2-23.notificacion
- NIS2-20.2
- NIS2-21.2.e
- TRV-EDR-01
- TRV-VUL-01
- NET-OT-01

**AVISO: 1 brecha(s) P1 sin acción:** NIS2-23.notificacion
