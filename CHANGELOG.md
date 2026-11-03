# Changelog

Formato basado en Keep a Changelog. Versionado semántico.

## 0.5.0 (2026-11-03)

- Verticales: catálogo de 19 (nuevas HUNT, MDM, ENDUSER, FW, SASE, ZTNA, OSI; VRT-NET como paraguas sin doble cómputo). `smc verticals`; sección «Verticales» en informes y columna en el dashboard.
- Tecnologías: evaluación y estado de reglas (`smc tech`) y suscripciones (`smc subs`).
- Protocolos: 28 protocolos por capa OSI y 8 fuentes oficiales (`smc protocols`).
- MITRE: madurez de casos de uso (niveles 1-5), 7 playbooks nuevos (PB-UC-002 a 008) y capa Navigator (`smc mitre --navigator`).
- Recursos: 17 feeds RSS (13 verificados) con OPML (`smc rss`) y registro del ecosistema público.
- Mapa de red: `smc mapa` (JSON `smc-mapa/1`), diseño en `docs/mapa-3d.md` y ADR-003. Las plantillas de registro e inventario llevan `zona` y `capa_osi` ficticias.
- `smc validate` suma los catálogos de la v0.5. Los informes admiten enlaces `https://` a los recursos públicos (nada se carga de fuera).
- 196 tests. Los README ya no dicen «12 verticales».
- Pendiente para v0.6: visor 3D, contraste del Anexo II del ENS con el BOE, conectores de evidencias, ingesta NVD/KEV/EPSS, cumplimiento por dominio.

## 0.4.1 (2026-11-03)

Endurecimiento tras la revisión de la ola 3.

- Un estado no válido cuenta como «sin evaluar» (aplicable, puntúa 0) con aviso; antes sacaba el control del denominador.
- Las medidas ENS con `verificar: true` se señalan en los informes Markdown/HTML («aplicabilidad pendiente de contrastar») y el resumen lleva un aviso. `op.cont.2` y `op.cont.3` pasan a `verificar: true`. Recuento real con PyYAML: 39 de 73 (el 39 anterior salía de un grep que contaba comentarios; sin estas dos eran 37).
- Prioridad recalibrada: `50*estado + 30*criticidad + 10*entidad + 10*cobertura`, P1 >= 75. Un no_implementado de criticidad media en entidad importante o no obligada sin cobertura multinorma es P2; de criticidad alta en entidad esencial, P1.
- Una acción `bloqueada` ya no cubre una brecha a efectos de «sin acción» y «P1 sin acción».
- `categoria_minima` desconocida se trata como BASICA; `smc validate` la rechaza.
- Entradas mal formadas (`plan_accion` de texto, evaluación de texto, `cliente: null`) dan aviso en lugar de `AttributeError`.
- El dashboard ignora `*.template.yaml`; la cabecera muestra la categoría ENS también con `proveedor_sector_publico`.
- `.gitignore` ignora `*.html` y `dashboard/`.

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
