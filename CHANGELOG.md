# Changelog

Formato basado en Keep a Changelog. Versionado semántico.

## 0.4.0 (2026-11-03)

- Dashboard estático multicliente: `smc dashboard <directorio> -o <salida>` con índice, semáforo y un HTML por cliente (ADR-002).
- Segundo ejemplo ficticio: `assessments/examples/ejemplo-energia.yaml`.

## 0.3.0 (2026-11-03)

- Informe HTML autocontenido: `smc report <evaluación> -o informe.html` (CSS en línea, sin JavaScript, imprimible a PDF).
- Plan de acción: sección `plan_accion:` en plantilla y ejemplo, `smc plan`, acciones vencidas y brechas sin acción.
- Opción `--hoy AAAA-MM-DD` en `gap`, `plan`, `report` y `dashboard`.

## 0.2.0 (2026-11-03)

- Aplicabilidad ENS por categoría (`categoria_minima`, `refuerzos_por_categoria`); 39 medidas pendientes de contrastar con el Anexo II (`verificar: true`).
- Priorización por riesgo (P1 a P3) y mapeo NIS2, ENS e ISO 27001 completo; «heredado» como sugerencia.
- API estructurada `smc.gap.analyse`.

## 0.1.0 (2026-11-02)

- Catálogos YAML (NIS2, ENS, transversal, red, normativa, SOC, tecnologías, vulnerabilidades), plantillas y CLI inicial: `validate`, `list`, `gap`, `soc`, `mitre`, `expiring`, `vulns`, `refs`.
