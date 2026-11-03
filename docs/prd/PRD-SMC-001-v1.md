# PRD-SMC-001 v1 — Security Manager Control

| Campo | Valor |
|---|---|
| Estado | Borrador. Roadmap v0.1 a v0.7 implementado (v0.7.0) |
| Versión | v1 |
| Fecha | 2026-11-03 |
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
| M12 Pentesting y purple team | Seguimiento de hallazgos de pentest (SLA, retest) y ejercicios purple team (cobertura por táctica, mejoras) | P1 |
| M13 IA | Obligaciones del RIA (Reglamento (UE) 2024/1689, con las fechas del Ómnibus Digital, Reglamento (UE) 2026/1744) y seguridad de agentes (OWASP LLM 2025, MITRE ATLAS) | P1 |
| M14 PMO | Presupuesto, horas, costes, valor ganado (EVM), riesgos y calendario de un proyecto de remediación | P1 |
| M10 Vulnerabilidades | Seguimiento de CVEs con SLA, priorización KEV/EPSS, playbooks por tecnología y por caso de uso | P0 |

## 5. Requisitos funcionales

- RF-01 Determinar marcos aplicables a partir del perfil (sector, tamaño, sector público).
- RF-02 Evaluar cada control con estado + evidencias + notas.
- RF-03 Calcular cumplimiento por marco y dominio.
- RF-04 Marcar controles "implementados" sin evidencia.
- RF-05 Mapear controles entre marcos para evaluar una vez y reutilizar (NIS2 ↔ ENS ↔ ISO 27001).
- RF-06 Inventariar recursos internos y externos y enlazarlos a controles.
- RF-07 Generar informe de brechas en Markdown (v0.1) y HTML imprimible a PDF (v0.3).
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
- RF-19 Catálogo de 22 verticales (incluye Threat Hunting, MDM, puesto de usuario, firewall, SASE, ZTNA, protección por capas OSI y, desde v0.7, IA y seguridad ofensiva) con madurez 0-5 o «no evaluable» con motivo obligatorio; sin doble cómputo con la vertical paraguas VRT-NET (`smc verticals`).
- RF-20 Evaluar cada tecnología del registro (cobertura, configuración, madurez) y el estado de sus reglas: any-any, sin uso y revisión caducada (180 días); «no evaluable» con motivo (`smc tech`).
- RF-21 Controlar suscripciones: coste, renovaciones próximas (90 días) y uso por debajo del 70 % de lo contratado (`smc subs`).
- RF-22 Catálogo de 28 protocolos por capa OSI con sus debilidades típicas y 8 fuentes oficiales de vulnerabilidades (NVD, ENISA, CISA KEV…) (`smc protocols`).
- RF-23 Madurez MITRE (niveles 1-5) de los casos de uso con detección, playbook y vertical, y export de capa para ATT&CK Navigator (`smc mitre --navigator`).
- RF-24 Listado de feeds RSS de seguridad (17, 13 verificados) con export OPML (`smc rss`) y registro del ecosistema público de recursos, con proyectos pendientes sin URL.
- RF-25 Mapa de dispositivos por zona y capa OSI con semáforo (rojo, ámbar, gris, verde) y JSON `smc-mapa/1` sin datos sensibles, base de un visor 3D (`smc mapa`, ADR-003).
- RF-26 `smc validate` comprueba los catálogos de la v0.5 y sus referencias cruzadas; informe HTML y dashboard muestran la madurez por vertical.
- RF-27 `smc report --registry` añade al informe HTML las secciones de tecnologías evaluadas, estado de las reglas (any-any siempre destacado), suscripciones y madurez MITRE ATT&CK; el Markdown de `smc gap` incluye siempre la madurez MITRE.
- RF-28 `smc dashboard` detecta por su forma los registros de tecnologías del directorio, los asocia a la evaluación por nombre (`<evaluación>.registry.yaml`), añade columnas de reglas y suscripciones y genera siempre la página común `mitre.html`.
- RF-29 `smc visor <mapa.json> -o visor.html` genera un visor 3D autocontenido y offline del mapa `smc-mapa/1`: una plataforma por zona con botón, piezas por semáforo (gris nunca verde), panel con los números del JSON, vistas, visita que cede al primer gesto, `prefers-reduced-motion` y tabla accesible. JSON inválido: rc 2 y sin fichero (ADR-003, ADR-004).
- RF-30 El HTML del visor no carga nada de la red (CSP `default-src 'none'`) y todo texto del JSON se inserta como texto, nunca como HTML.
- RF-31 Las 73 medidas ENS se contrastan con el Anexo II del RD 311/2022 (BOE-A-2022-7191): 45 confirmadas y 28 en `verificar` por depender de las dimensiones C/I/T/A/D.
- RF-32 `smc pentest <fichero> [--hoy]` calcula hallazgos abiertos, fuera de SLA (SLA de `vulnerabilities/policy.yaml`, KEV = crítica), pendientes de retest y aceptados sin revisión.
- RF-33 `smc purple <fichero> [--hoy]` calcula la cobertura por táctica del último ejercicio de cada técnica (detectado 1, parcial 0,5), las técnicas no detectadas, las mejoras abiertas y los ejercicios de más de 12 meses.
- RF-34 Madurez MITRE con purple: con `--purple` (en `smc mitre` y `smc report`), un ejercicio `detectado` con fecha cuenta como prueba del caso de uso (nivel 4, y 5 si es de los últimos 90 días). Sin el fichero, la madurez no cambia. `parcial` y `no_detectado` no suben nada.
- RF-35 `smc ai <inventario> [--hoy]` lista por sistema las obligaciones del RIA aplicables según rol, nivel de riesgo y fecha (30 obligaciones; alto riesgo del Anexo III desde 2027-12-02 y del Anexo I desde 2028-08-02; art. 50 desde 2026-08-02), su cumplimiento según la evidencia del inventario y las comprobaciones de seguridad de agentes AGT-01 a AGT-06. El informe lleva siempre el aviso de que no es asesoramiento jurídico y marca «verificar» las obligaciones con fecha o alcance sin contrastar.
- RF-36 `smc pmo <proyecto> [--ics eventos.ics] [--registry r.yaml] [--assessment a.yaml] [--hoy]` calcula presupuesto por partida, horas por rol y mes, EVM (PV, EV, AC, CPI, SPI), tareas retrasadas o sin control, próximos eventos (30 días) y exporta los eventos a iCalendar (RFC 5545). Con `--assessment` valida cada tarea contra el plan de acción y hereda sus controles.
- RF-37 `smc report` admite `--pentest`, `--purple`, `--ai` y `--pmo`; `smc dashboard` los toma de `<evaluación>.pentest.yaml`, `.purple.yaml`, `.ai.yaml` y `.pmo.yaml`. Sin esos ficheros el informe no cambia. Todo texto se escapa y solo se enlazan URLs `https://`. Un fichero que no vale da rc 2 en la CLI y un aviso en el dashboard.
- RF-38 `smc validate` valida también el catálogo `frameworks/ai-act/` y las plantillas de inventario de IA, pentest, purple team y PMO.
- RF-39 Los datos de pentest, purple team, IA y PMO de un cliente son datos de cliente: `.gitignore` los excluye salvo plantillas y ejemplos (ADR-001, ADR-005).

## 6. Requisitos no funcionales

- Datos de clientes fuera del repositorio público (ver ADR-001).
- Soberanía del dato: ejecución local u on-prem en UE.
- Catálogos como datos (YAML) versionados, revisables en PR.

## 7. Roadmap

| Versión | Entregable | Estado |
|---|---|---|
| v0.1 | Catálogos YAML, plantillas, CLI `smc gap` | Hecha |
| v0.2 | Aplicabilidad ENS por categoría, priorización por riesgo, mapeos completos | Hecha (28 medidas ENS por verificar tras el contraste con el BOE, ver sección 8) |
| v0.3 | Informe HTML y plan de acción (`smc report`, `smc plan`). PDF: se obtiene imprimiendo el HTML desde el navegador | Hecha |
| v0.4 | Dashboard estático multicliente (`smc dashboard`), ver ADR-002 | Hecha |
| v0.5 | Verticales ampliadas, evaluación de tecnologías y suscripciones, protocolos, madurez MITRE con Navigator, RSS, ecosistema y mapa de red (RF-19 a RF-26) | Hecha |
| v0.6 | Visor 3D del mapa, informe y dashboard con registro de tecnologías y MITRE, contraste del Anexo II del ENS con el BOE (RF-27 a RF-31) | Hecha |
| v0.7 | Pentesting y purple team, RIA y seguridad de agentes, PMO, verticales de identidad y datos, IA y seguridad ofensiva (22 en total), informe y dashboard con las secciones nuevas (RF-32 a RF-39) | Hecha |
| v0.8 | Contraste de las 28 medidas ENS por dimensión con CCN-STIC, visor en GPU integrada y móvil, conectores de evidencias (EDR, SIEM, escáneres, EASM, firewall), ingesta NVD/KEV/EPSS, cumplimiento por dominio | Pendiente |

Nota: el dashboard de v0.4 se resolvió como sitio estático generado en local, no como aplicación web con servidor (ADR-002).

## 8. Riesgos y supuestos

- La ley española de transposición de NIS2 sigue en tramitación (nov. 2026): revisar catálogo al publicarse en el BOE.
- La aplicabilidad exacta por categoría ENS debe validarse contra el Anexo II y guías CCN-STIC. Estado a v0.7.0: contrastadas con el BOE (BOE-A-2022-7191, Anexo II) 45 de 73; 28 de 73 medidas siguen con `verificar: true` porque dependen de las dimensiones C/I/T/A/D (recuento con PyYAML). Pendiente cruzarlas con las guías CCN-STIC.
- Las criticidades NIS2 son un juicio inicial sin fuente normativa.
- «Sin evaluar» pesa 0.75 en la prioridad y puntúa como no cumplido: las evaluaciones incompletas salen en rojo en el dashboard.
