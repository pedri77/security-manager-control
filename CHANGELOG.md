# Changelog

Formato basado en Keep a Changelog. Versionado semántico.

## 0.6.0 (2026-11-03)

- `smc visor <mapa.json> -o visor.html`: visor 3D offline y autocontenido del mapa `smc-mapa/1` (three.js 0.186.1 vendorizado, MIT, ADR-004; patrón de teardown, ADR-003). Sin red, CSP estricta, texto del JSON siempre como texto, tabla accesible, `prefers-reduced-motion`. Captura en `docs/img/visor.png`. JSON inválido: rc 2.
- `smc report --registry <registro.yaml>`: secciones de tecnologías evaluadas, estado de reglas (any-any destacado), suscripciones y madurez MITRE ATT&CK. El Markdown de `smc gap` incluye siempre la madurez MITRE.
- `smc dashboard`: detecta registros de tecnologías por su forma, columnas de reglas y suscripciones, y página común `mitre.html`.
- ENS contrastado con el Anexo II del RD 311/2022 (BOE-A-2022-7191): 45 de 73 medidas confirmadas; 28 siguen en `verificar` por depender de las dimensiones C/I/T/A/D (antes 39). Los tests de cifras pasan a 28.
- README, PRD (RF-27 a RF-31) y hoja de ruta actualizados; v0.7 con lo pendiente.

## 0.5.2 (2026-11-03)

- Vertical `VRT-GRC` (gobierno, riesgo y cumplimiento): 20 verticales. Cubre NIS2 art. 20 (dirección y su formación) y 21.2.a/21.2.f, con controles ENS-org.*, ENS-op.pl.1, NIS2, TRV de gobierno y RGPD, criterios y baremo 0-5 comprobable. Sin recursos públicos. Añadida a la plantilla y a los dos ejemplos ficticios.
- Informes T09 y T12: los nombres de repos privados se sustituyen por «un repo privado».

## 0.5.1 (2026-11-03)

Endurecimiento tras la revisión de las olas 5-6 (hallazgos 1-10 y 12).

- Mapa: la KEV cuenta como crítica a efectos de SLA (7 días) según `policy.yaml`; toda KEV o crítica abierta pone el dispositivo al menos en ámbar aunque esté dentro de SLA. La severidad se normaliza (minúsculas, sin tildes) y la desconocida cuenta como crítica con aviso. `smc vulns` usa la misma severidad efectiva.
- Reglas: `tech.reglas()` devuelve `any_any` con independencia del estado y `smc tech` lo destaca (una revisión reciente ya no oculta un any-any).
- Verticales: VRT-NET con subverticales evaluadas se muestra como «no puntúa (detallada en FW, SASE, ZTNA y OSI)» en Markdown y HTML. Cada vertical lleva `niveles` (descriptor por nivel 0-5) y el catálogo valida que haya 6. Mapeos ENS: VRT-EDR a ENS-op.exp.6 y VRT-ENDUSER a ENS-op.exp.4. El Markdown escapa `<`, `>` y `|`.
- Plantilla de registro: los dos firewalls pasan a VRT-FW (capa por defecto 4; la declarada manda).
- MITRE: la madurez por táctica es el mínimo de los casos activos (antes, el máximo) y sale en `smc mitre`; los casos no activos se listan aparte.
- Suscripciones: `coste_anual` no numérico da aviso.
- Informe T15: el gris de la ejecución real es AST-0001, no TEC-0001.
- Tests de versión, XSS (Markdown), capa OSI por vertical y táctica por mínimo ajustados a estos cambios (anotado en el informe T17).

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
