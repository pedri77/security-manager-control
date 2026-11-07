# Plan: SMC de v0.1 a v0.4 (ENS por categoría, priorización, plan de acción, informe HTML y dashboard multicliente)

Contexto: Security Manager Control (`~/Dev/security-manager-control`) está en v0.1 (catálogos YAML + CLI `smc gap` en Markdown). El PRD `docs/prd/PRD-SMC-001-v1.md` fija el roadmap: v0.2 aplicabilidad ENS por categoría, priorización por riesgo y mapeos; v0.3 informe HTML/PDF y plan de acción; v0.4 dashboard multicliente. Este plan cubre v0.2 a v0.4. v0.5 (conectores, NVD/KEV/EPSS) queda fuera. ADR-001 manda: datos de cliente fuera del repo; solo ejemplos ficticios.

Validar y mover tareas: `python3 ~/Dev/Claude_proyectos/Claude/tools/plan_check.py --plan docs/plan/PLAN.md <check|next|status|graph|claim|done|release|atasco>`

Tests: `uv run --no-project --with pytest --with pyyaml python -m pytest -q` desde la raíz del repo (el `python3` del PATH no tiene pytest). Hoy: 12 verdes.

## Cómo usar este plan

Igual que la plantilla `~/.claude/plantillas/PLAN.md` (elegir con `next`, reservar, trabajar solo en «Toca», informe en `docs/plan/informes/<ID>-<agente>.md`, commit en worktree con pies `Agente:` y `Tarea: docs/plan/PLAN.md#<ID>`, el coordinador fusiona y ejecuta `done --evidencia`).

**Restricciones de este plan:** sin dependencias nuevas de Python salvo PyYAML (HTML generado con la stdlib, sin CDN ni JS externo). Nada de red ni de servicios externos. Ningún dato real de clientes: solo `assessments/examples/` ficticio. Sin push (lo hace la sesión principal). Commits con el email `pedri77@users.noreply.github.com`.

## Papeles

- **Sesión principal**: lanza agentes de tarea (`dev-proyecto`, `isolation: worktree`) y coordinador por ola.
- **coordinador**: revisa contra «Verifica», fusiona a `main`, marca `done`.
- **revisor-ola**: revisión adversarial antes de la entrega.

Revisión de ola: 3

## Grupos

| Grupo | Coordinador | Tareas |
|---|---|---|
| smc | coordinador | T01, T02, T03, T04, T05, T06, T07, T08 |
| smc-v05 | coordinador | T09, T10, T11, T12, T13, T14, T15, T16, T17, T18, T19, T20, T21, T22, T23, T24, T25, T26, T27, T28, T29, T30, T31, T32, T33, T34, T35, T36 |
| smc-f2p | coordinador | T37, T38, T39, T40, T41, T42, T43, T44, T45 |

## Ola 1

- [x] **T01** — Aplicabilidad ENS por categoría
  - Hace: añade a cada una de las 73 medidas de `frameworks/ens/controls.yaml` el campo `categoria_minima` (BASICA | MEDIA | ALTA, la categoría más baja en la que la medida aplica según el Anexo II del RD 311/2022) y, cuando aplique, `refuerzos_por_categoria` (p. ej. `{MEDIA: [R1], ALTA: [R1, R2]}`). Donde no haya certeza, añade `verificar: true` y explícalo en el informe; quita el TODO de cabecera solo si todas quedan rellenas. Crea `smc/ens.py` con `aplica(control, categoria) -> bool` y `refuerzos(control, categoria) -> list[str]`; categoría desconocida o vacía = ALTA (conservador) con aviso.
  - No hace: no toca `smc/gap.py` ni `smc/cli.py` (lo integra T04). No cambia IDs.
  - Toca: `frameworks/ens/controls.yaml`, `smc/ens.py`, `tests/test_ens.py`, `docs/plan/informes/T01-dev-proyecto.md`
  - Depende: —
  - Verifica: `smc validate` sigue OK; tests de `aplica` para BASICA/MEDIA/ALTA con medidas reales del YAML (p. ej. una medida que solo aplica en ALTA no aplica en BASICA) y categoría vacía. Contraprueba: cambiar el orden de categorías en `ens.py` pone un test en rojo.
  - Prod: —
  - Estado: hecha en 7b6bb26af1841f5cad0f628e4bd793d0f2600196 · evidencia informes/T01-dev-proyecto.md

- [x] **T02** — Priorización por riesgo y mapeos completos entre marcos
  - Hace: completa `mappings/nis2-ens-iso27001.csv` para que cada control NIS2 del catálogo tenga fila (medidas ENS e ISO 27001:2022 Anexo A). Crea `smc/mapping.py` (carga el CSV; `equivalentes(control_id) -> set[str]` en ambos sentidos NIS2↔ENS) y `smc/priority.py` con `prioridad(control, estado, cliente) -> (puntuacion 0-100, nivel P1|P2|P3)` basada en: peso del estado (no_implementado > parcial), criticidad del control (campo opcional `criticidad: alta|media|baja` en los YAML, por defecto media), tipo de entidad NIS2 (esencial pesa más) y si el control cubre varias normas vía mapeo. Documenta la fórmula en el docstring.
  - No hace: no toca `smc/gap.py` ni `smc/cli.py`, ni los YAML de marcos salvo para añadir `criticidad` a controles NIS2 en `frameworks/nis2/controls.yaml`.
  - Toca: `mappings/nis2-ens-iso27001.csv`, `frameworks/nis2/controls.yaml`, `smc/mapping.py`, `smc/priority.py`, `tests/test_priority.py`, `docs/plan/informes/T02-dev-proyecto.md`
  - Depende: —
  - Verifica: test que comprueba que todo ID NIS2 del catálogo está en el CSV y que todo ID ENS del CSV existe en el catálogo ENS; tests de orden de prioridad (esencial+no_implementado+alta > importante+parcial+baja). Contraprueba: borrar una fila del CSV pone en rojo el test de cobertura.
  - Prod: —
  - Estado: hecha en 785aa4f07c8a2c1443ce1a9346f9ad8db88f5d10 · evidencia informes/T02-dev-proyecto.md

- [x] **T03** — Plan de acción en la evaluación
  - Hace: añade a `assessments/assessment.template.yaml` y al ejemplo ficticio `assessments/examples/ejemplo-ayuntamiento.yaml` una sección `plan_accion:` (lista de acciones con `id`, `controles`, `accion`, `responsable`, `fecha_objetivo`, `estado: pendiente|en_curso|hecha|bloqueada`). Crea `smc/plan.py` con `cargar_plan(assessment) -> list[Accion]`, `vencidas(plan, hoy)`, `brechas_sin_accion(brechas, plan)` y `render_plan_md(...)`.
  - No hace: no toca `smc/gap.py` ni `smc/cli.py`. Sin datos reales.
  - Toca: `assessments/assessment.template.yaml`, `assessments/examples/ejemplo-ayuntamiento.yaml`, `smc/plan.py`, `tests/test_plan.py`, `docs/plan/informes/T03-dev-proyecto.md`
  - Depende: —
  - Verifica: tests con fecha fija (`hoy` inyectado) para vencidas, acciones hechas no vencen, brechas sin acción; el ejemplo carga sin errores. Contraprueba: comparar fechas con `<=` en vez de `<` cambia el resultado de un test.
  - Prod: —
  - Estado: hecha en d6bbd813b904cd4fcf18615c867648aa493254dd · evidencia informes/T03-dev-proyecto.md

## Ola 2

- [x] **T04** — Integrar v0.2 en el análisis y el CLI
  - Hace: `smc/gap.py` usa `ens.aplica` con `cliente.categoria_ens` (las medidas ENS que no aplican no cuentan como aplicables ni como sin evaluar; se listan aparte), ordena brechas por `priority.prioridad`, añade columna de prioridad y refuerzos ENS al Markdown y marca como «heredado» un control sin evaluar cuyo equivalente mapeado sí esté evaluado (no puntúa, solo sugiere). El informe incluye la sección de plan de acción (`plan.render_plan_md`) y avisa de brechas P1 sin acción. CLI: `smc plan <assessment> [--hoy AAAA-MM-DD]`. Expone `analyse()` con resultado estructurado reutilizable por T05/T06 (dataclasses; sin romper la firma de `run`).
  - No hace: nada de HTML.
  - Toca: `smc/gap.py`, `smc/cli.py`, `tests/test_smc.py`, `tests/test_gap_v02.py`, `docs/plan/informes/T04-dev-proyecto.md`
  - Depende: T01, T02, T03
  - Verifica: los 12 tests originales siguen verdes; tests nuevos: ejemplo del ayuntamiento (MEDIA) excluye medidas solo-ALTA, brecha P1 sale primero, `smc plan` lista vencidas con `--hoy`. Contraprueba: forzar categoría ALTA cambia el número de aplicables ENS.
  - Prod: —
  - Estado: hecha en 5c473b9 · evidencia informes/T04-dev-proyecto.md

## Ola 3

- [x] **T05** — Informe HTML autocontenido (v0.3)
  - Hace: `smc/report_html.py` genera un único HTML sin dependencias externas (CSS en línea, sin JS obligatorio) con: resumen ejecutivo para dirección (cumplimiento por marco con barras, top 10 brechas P1, acciones vencidas), detalle por marco, plan de acción y avisos. Estilos de impresión (`@media print`) para guardar como PDF desde el navegador. Escapa todo texto de la evaluación (`html.escape`). CLI: `smc report <assessment> -o informe.html`.
  - No hace: no genera PDF con librerías; no toca el dashboard.
  - Toca: `smc/report_html.py`, `smc/cli.py`, `tests/test_report_html.py`, `docs/plan/informes/T05-dev-proyecto.md`
  - Depende: T04
  - Verifica: test que genera el informe del ejemplo y comprueba secciones, ausencia de `http://`/`https://` en `<link>`/`<script>` y que una nota con `<script>` sale escapada. Contraprueba: quitar el escape pone en rojo el test de XSS.
  - Prod: —
  - Estado: hecha en e6a5b05 · evidencia informes/T05-dev-proyecto.md

- [x] **T06** — Dashboard estático multicliente (v0.4)
  - Hace: `smc/dashboard.py` + CLI `smc dashboard <dir_evaluaciones> -o <dir_salida>`: recorre `*.yaml` de evaluaciones, genera `index.html` (tabla de clientes con cumplimiento por marco, nº de brechas P1, acciones vencidas, fecha de evaluación, semáforo) y una página por cliente reutilizando `report_html`. Todo estático, local, sin servidor. Añade un segundo ejemplo ficticio privado (empresa de energía, entidad esencial, no sector público) en `assessments/examples/` para que el dashboard muestre dos clientes.
  - No hace: no sirve por red ni añade autenticación; no publica nada.
  - Toca: `smc/dashboard.py`, `smc/cli.py`, `assessments/examples/ejemplo-energia.yaml`, `tests/test_dashboard.py`, `docs/plan/informes/T06-dev-proyecto.md`
  - Depende: T05
  - Verifica: test que genera el dashboard de `assessments/examples/` en un tmp y comprueba 2 filas, enlaces relativos válidos a las páginas de cliente y escape de nombres. Contraprueba: un YAML inválido en el directorio se informa como aviso y no rompe el resto.
  - Prod: —
  - Estado: hecha en 2c13473 · evidencia informes/T06-dev-proyecto.md

- [x] **T07** — Documentación y versión 0.4.0
  - Hace: actualiza `README.md` (estado v0.4, comandos nuevos, flujo), `docs/prd/PRD-SMC-001-v1.md` (roadmap: marca v0.2-v0.4 como hechas), crea `docs/adr/ADR-002-informes-html-y-dashboard-estatico.md` (por qué HTML autocontenido y dashboard estático local: soberanía, sin servidor, ADR-001), sube versión a 0.4.0 en `pyproject.toml` y `smc/__init__.py`, añade `CHANGELOG.md`.
  - No hace: no toca código de `smc/` salvo `__init__.py`.
  - Toca: `README.md`, `docs/prd/PRD-SMC-001-v1.md`, `docs/adr/ADR-002-informes-html-y-dashboard-estatico.md`, `pyproject.toml`, `smc/__init__.py`, `CHANGELOG.md`, `docs/plan/informes/T07-dev-proyecto.md`
  - Depende: T06
  - Verifica: `smc --version` da 0.4.0; todos los comandos del README se ejecutan sin error sobre los ejemplos. Contraprueba: un comando mal escrito en el README falla al ejecutarlo.
  - Prod: —
  - Estado: hecha en 7d920f4 · evidencia informes/T07-dev-proyecto.md

## Ola 4

- [x] **T08** — Endurecer v0.4 antes de publicar (hallazgos de revisor-ola)
  - Hace: corrige los hallazgos 1-10 y 12 de `informes/ola-3-revisor-ola.md`: estado no válido cuenta como sin evaluar (aplicable, 0) con aviso; medidas ENS con `verificar: true` señaladas en informes Markdown/HTML («aplicabilidad pendiente de contrastar») y aviso en el resumen; `.gitignore` ignora `*.html` salvo lo versionado y `dashboard/`; recalibra `priority` para que un no_implementado de criticidad media en entidad no esencial no sea P1 (test nuevo) y documenta la fórmula; `verificar: true` en op.cont.2 y op.cont.3; cifra correcta de medidas `verificar` (37 o la que resulte) en README, PRD, CHANGELOG y Libro; `categoria_minima` desconocida tratada como BASICA y validada en `smc validate`; entradas mal formadas (`plan_accion` de texto, evaluación de texto, `cliente: null`) dan aviso, no AttributeError; el dashboard ignora `*.template.yaml`; la cabecera muestra la categoría ENS también con `proveedor_sector_publico`; test 12 con valor esperado real.
  - No hace: no contrasta el Anexo II con el BOE (queda para revisión humana); no cambia IDs ENS; no añade mapeos TRANSVERSAL/RED.
  - Toca: `smc/`, `tests/`, `frameworks/ens/controls.yaml`, `.gitignore`, `README.md`, `docs/prd/PRD-SMC-001-v1.md`, `CHANGELOG.md`, `docs/plan/informes/T08-dev-proyecto.md`
  - Depende: T07
  - Verifica: un test por hallazgo, cada uno con su contraprueba anotada en el informe; los 65 tests previos siguen verdes salvo los que cambien por la recalibración (justificados).
  - Prod: —
  - Estado: hecha en 2e15979 · evidencia informes/T08-dev-proyecto.md

## Ola 5 (v0.5)

Contexto v0.5 (pedido de David el 2026-11-03): verticales Threat Hunting, EDR/XDR, MDM, puesto de usuario, perimetrales (firewall, SASE, ZTNA, protección on-prem por capas OSI); estado de las reglas de los dispositivos («no evaluable» con motivo si no se puede); evaluación de tecnologías y control de suscripciones; playbooks y madurez con MITRE; vulnerabilidades por protocolo con fuentes oficiales (NIST/NVD, ENISA, CISA KEV, cvedetails.com); listado de RSS; mapa de dispositivos 3D a partir de la skill teardown. Enlaces SOLO a páginas públicas (GitHub Pages) verificadas: EDR/XDR https://pedri77.github.io/edr-visual-app/ · SASE https://pedri77.github.io/sase-visual-app/ · Firewalls https://pedri77.github.io/Basic_Firewalls/ · Protección por capas OSI https://pedri77.github.io/Basicos_Proteccion_Capas_OSI/ · Modelo OSI https://pedri77.github.io/modelo_OSI/ · ICS/OT https://pedri77.github.io/ics-security-studio/ · WAF https://pedri77.github.io/wafforge/ · Correo https://pedri77.github.io/Basicos_email/. Repos públicos sin Pages (enlazar el repo): https://github.com/pedri77/kev_dash_project · https://github.com/pedri77/threat-intelligence-feeds. Nada de repos privados (los dos privados de evaluación SASE y de noticias) enlazados. Proyectos pendientes de crear: evaluación de productos ZTNA, repositorio de vulnerabilidades por capa OSI, mapa 3D de dispositivos (se marcan `estado: pendiente`, sin URL).

Regla de reparto: en la ola 5 NINGUNA tarea toca `smc/cli.py`, `smc/gap.py`, `smc/report_html.py`, `smc/dashboard.py` ni los ejemplos de `assessments/` salvo la que lo diga; la integración es T14.

- [x] **T09** — Verticales ampliadas y madurez por vertical
  - Hace: amplía `soc/verticals.yaml` con verticales nuevas: Threat Hunting, MDM, puesto de usuario, y separa el perímetro en firewall, SASE/SSE, ZTNA y protección on-prem por capas OSI (manteniendo los 12 IDs actuales; VRT-NET se conserva y se documenta su relación). Cada vertical: `id`, `nombre`, `nis2` (medidas 21.2), `controles` relacionados (IDs existentes), `criterios` de madurez 0-5 concretos, `recursos` (lista de {titulo, url} solo de la lista pública del contexto) y `estado_recursos` para los pendientes. `smc/verticals.py`: `cargar_verticales()`, `evaluar(assessment)` que lee una sección opcional `verticales:` de la evaluación ({VRT-ID: {madurez 0-5 o no_evaluable, motivo, producto, notas}}), agrega por medida NIS2 21.2 y devuelve resultado estructurado; `no_evaluable` exige `motivo` y no puntúa. Añade la sección `verticales:` a `assessments/assessment.template.yaml` y a los dos ejemplos ficticios.
  - No hace: no toca cli/gap/report/dashboard.
  - Toca: `soc/verticals.yaml`, `smc/verticals.py`, `tests/test_verticals.py`, `assessments/assessment.template.yaml`, `assessments/examples/`, `docs/plan/informes/T09-dev-proyecto.md`
  - Depende: T08
  - Verifica: todo `controles` existe en catálogos; todo `url` está en la lista pública del contexto; agregación NIS2 correcta en un caso; `no_evaluable` sin motivo da error. Contraprueba: una URL fuera de la lista pone un test en rojo.
  - Prod: —
  - Estado: hecha en 663c5a1 · evidencia informes/T09-dev-proyecto.md

- [x] **T10** — Evaluación de tecnologías, estado de reglas y suscripciones
  - Hace: amplía `technologies/registry.template.yaml` con, por tecnología: `vertical` (ID de vertical, validado más tarde), `evaluacion` {cobertura %, configuracion: bastionada|por_defecto|desconocida, madurez 0-5}, `reglas` {estado: revisadas|sin_revisar|no_evaluable, ultima_revision, motivo (obligatorio si no_evaluable, p. ej. «sin acceso a la consola»), n_reglas, reglas_any_any, reglas_sin_uso} y `suscripcion` {proveedor, coste_anual, moneda, renovacion, propietario (rol), unidades_contratadas, unidades_en_uso, autorrenovacion}. `smc/tech.py`: `evaluar_tecnologias(registry)`, `reglas(registry, hoy)` (reglas sin revisar más de 180 días, any-any, no evaluables con su motivo) y `suscripciones(registry, hoy, dias)` (renovaciones próximas, infrautilizadas por debajo del 70 %, sobredespliegue, coste total por proveedor) con salidas Markdown. Mantiene `expiring` y `vulns` como están.
  - No hace: no toca cli.py; datos ficticios.
  - Toca: `technologies/registry.template.yaml`, `technologies/README.md`, `smc/tech.py`, `tests/test_tech_v05.py`, `docs/plan/informes/T10-dev-proyecto.md`
  - Depende: T08
  - Verifica: tests con `hoy` inyectado; contraprueba: cambiar el umbral de 70 % cambia el resultado de un test.
  - Prod: —
  - Estado: hecha en efce805 · evidencia informes/T10-dev-proyecto.md

- [x] **T11** — Vulnerabilidades por protocolo y fuentes oficiales
  - Hace: `vulnerabilities/protocols.yaml` con al menos 20 protocolos (SMB, RDP, SSH, Telnet, FTP, SNMP, DNS, NTP, LDAP, Kerberos, NTLM, TLS/SSL, HTTP, SMTP, IMAP/POP3, SIP, MQTT, Modbus, S7comm, DNP3, BACnet, OPC UA): capa OSI, puertos, riesgos típicos, CWE representativos, mitigaciones, controles SMC relacionados (IDs existentes), técnicas MITRE ATT&CK, y `consulta` con URLs de búsqueda en fuentes oficiales: NVD (nvd.nist.gov), ENISA EUVD (euvd.enisa.europa.eu), CISA KEV, CVE Details (www.cvedetails.com), INCIBE-CERT y CCN-CERT. No inventar CVEs concretos: solo URLs de búsqueda. `vulnerabilities/sources.yaml` con las fuentes oficiales (nombre, organismo, url, tipo, uso). Enlaces de aprendizaje a las Pages de Modelo OSI, Protección por capas OSI, ICS/OT y WAF. `smc/protocols.py`: carga, validación, `por_capa()`, `render_protocolo(id)`.
  - No hace: no consulta la red; no toca cli.py.
  - Toca: `vulnerabilities/protocols.yaml`, `vulnerabilities/sources.yaml`, `vulnerabilities/README.md`, `smc/protocols.py`, `tests/test_protocols.py`, `docs/plan/informes/T11-dev-proyecto.md`
  - Depende: T08
  - Verifica: 20 o más protocolos; todo control existe; toda URL es https y de un dominio de la lista de fuentes o de pedri77.github.io; capa OSI 1-7. Contraprueba: un dominio no permitido pone en rojo un test.
  - Prod: —
  - Estado: hecha en 9aea222 · evidencia informes/T11-dev-proyecto.md

- [x] **T12** — Catálogo de RSS y ecosistema de recursos
  - Hace: `resources/rss.yaml` con feeds de fuentes oficiales y de referencia (INCIBE-CERT, CCN-CERT, ENISA, CISA, NIST/NVD, CERT-EU, NCSC UK, BSI, MITRE ATT&CK y fabricantes principales con avisos) con {id, nombre, organismo, url_feed, url_web, idioma, categoria: avisos|noticias|vulnerabilidades|normativa, vertical opcional, verificado: false}; `verificado: false` porque no hay red (lo comprueba un humano). Exporta OPML (`smc/resources.py: a_opml()`) para que lo ingiera el agregador interno (el agregador interno usa feedparser con la URL; no se enlaza el repo privado). `resources/ecosistema.yaml`: proyectos públicos con sus Pages (lista del contexto), repos públicos sin Pages y pendientes (ZTNA, vulnerabilidades por capa OSI, mapa 3D) con `estado: pendiente`. `smc/resources.py` con carga, validación y render Markdown.
  - No hace: no consulta la red; no toca cli.py.
  - Toca: `resources/rss.yaml`, `resources/ecosistema.yaml`, `resources/README.md`, `smc/resources.py`, `tests/test_resources.py`, `docs/plan/informes/T12-dev-proyecto.md`
  - Depende: T08
  - Verifica: OPML válido (xml.etree parsea, un outline por feed); ninguna URL a repos privados (repos privados); ids únicos. Contraprueba: añadir una URL de repo privado pone en rojo el test.
  - Prod: —
  - Estado: hecha en 18b88a7 · evidencia informes/T12-dev-proyecto.md

- [x] **T13** — Madurez MITRE ATT&CK con playbooks
  - Hace: amplía `soc/use-cases/catalog.yaml` para que cada caso de uso tenga técnicas ATT&CK (IDs Txxxx), `deteccion` (sin|regla|probada), `ultima_prueba`, `playbook` (ruta en `vulnerabilities/playbooks/caso-uso/`) y `vertical`. Crea los playbooks de caso de uso que falten (formato de PB-UC-001, sin datos reales). `smc/mitre.py`: madurez por técnica y por táctica (0 sin caso, 1 caso sin regla, 2 regla, 3 regla + playbook, 4 probada, 5 probada en los últimos 90 días con `hoy` inyectado), casos sin playbook, playbooks huérfanos y export de capa ATT&CK Navigator (JSON, puntuación = madurez) con `a_navigator()`. `smc/soc.py:mitre_coverage` sigue funcionando (puede delegar).
  - No hace: no toca cli.py ni report.
  - Toca: `soc/use-cases/catalog.yaml`, `vulnerabilities/playbooks/caso-uso/`, `smc/mitre.py`, `smc/soc.py`, `tests/test_mitre.py`, `docs/plan/informes/T13-dev-proyecto.md`
  - Depende: T08
  - Verifica: todo playbook referenciado existe; JSON Navigator con `techniques[].score`; tests de niveles con `hoy`. Contraprueba: borrar un playbook pone en rojo el test de enlaces.
  - Prod: —
  - Estado: hecha en 8f4fe31 · evidencia informes/T13-dev-proyecto.md

## Ola 6 (v0.5)

- [x] **T14** — Integración v0.5 en CLI, validate, informe y dashboard
  - Hace: subcomandos `smc verticals <evaluación>`, `smc tech <registry>` (evaluación + reglas), `smc subs <registry> [--hoy --days]`, `smc protocols [ID]`, `smc rss [--opml -o]`, `smc mitre [--navigator -o capa.json] [--hoy]`; `smc validate` valida también verticales, protocolos, fuentes, RSS, ecosistema y casos de uso; informe HTML y Markdown con sección de verticales (madurez y no evaluables con motivo) y enlaces a recursos; dashboard con columna de madurez media de verticales. Escape HTML en todo lo nuevo.
  - No hace: no cambia los catálogos de la ola 5 salvo errores que impidan validar (anotarlos).
  - Toca: `smc/cli.py`, `smc/catalog.py`, `smc/gap.py`, `smc/report_html.py`, `smc/dashboard.py`, `tests/test_cli_v05.py`, `docs/plan/informes/T14-dev-proyecto.md`
  - Depende: T09, T10, T11, T12, T13
  - Verifica: cada comando nuevo rc=0 sobre los ejemplos; XSS en un `motivo` de no_evaluable sale escapado (contraprueba).
  - Prod: —
  - Estado: hecha en 7f12649 · evidencia informes/T14-dev-proyecto.md

- [x] **T15** — Mapa 3D de dispositivos: contrato de datos y adaptación de teardown
  - Hace: `smc/mapa.py` + `smc mapa <registry> [--evaluacion] -o mapa.json`: exporta dispositivos (de `technologies/registry` y `resources/internal`) con zona de red, capa OSI, vertical, estado de reglas, vulnerabilidades abiertas del tracker y semáforo, en un JSON versionado (`schema: smc-mapa/1`). `docs/mapa-3d.md`: diseño de la adaptación de la skill teardown (origen: elvarofficial/teardown, MIT, sobre whaleyxbt/claude-motion, MIT): la «máquina» es la red del cliente, cada zona un subsistema que se abre, paneles que leen los números reales del JSON, visita automática; qué se reutiliza y qué se cambia; todo offline. `docs/adr/ADR-003-mapa-3d-desde-teardown.md`. El prototipo HTML queda como siguiente paso.
  - No hace: no construye aún el visor 3D; no copia código de teardown al repo.
  - Toca: `smc/mapa.py`, `smc/cli.py`, `tests/test_mapa.py`, `docs/mapa-3d.md`, `docs/adr/ADR-003-mapa-3d-desde-teardown.md`, `docs/plan/informes/T15-dev-proyecto.md`
  - Depende: T14
  - Verifica: el JSON del ejemplo valida contra el esquema descrito (test); sin rutas absolutas ni datos fuera del registro. Contraprueba: un dispositivo sin zona aparece en `sin_zona` y no rompe.
  - Prod: —
  - Estado: hecha en 1acd498 · evidencia informes/T15-dev-proyecto.md

- [x] **T16** — Documentación y versión 0.5.0
  - Hace: README (mantén el estilo actual con imágenes y badges; actualiza cifras, tabla de módulos, comandos, hoja de ruta v0.5 hecha y v0.6 con lo pendiente, sección «Ecosistema» con las Pages públicas), PRD (RF nuevos), CHANGELOG 0.5.0, versión 0.5.0.
  - No hace: no regenera imágenes.
  - Toca: `README.md`, `soc/README.md`, `docs/prd/PRD-SMC-001-v1.md`, `CHANGELOG.md`, `pyproject.toml`, `smc/__init__.py`, `technologies/registry.template.yaml`, `resources/internal/inventory.template.yaml`, `docs/plan/informes/T16-dev-proyecto.md` (UPDATE 1: añadir `zona` y `capa_osi` ficticias a las plantillas para que `smc mapa` muestre zonas; corregir «12 verticales»)
  - Depende: T15
  - Verifica: todos los comandos del README rc=0 sobre los ejemplos; badges con cifras reales (tests, controles, verticales, protocolos).
  - Prod: —
  - Estado: hecha en 8be8109 · evidencia informes/T16-dev-proyecto.md

## Ola 7 (v0.5.1)

- [x] **T17** — Endurecer v0.5 antes de publicar (hallazgos de revisor-ola olas 5-6)
  - Hace: corrige los hallazgos 1-10 y 12 de `informes/ola-5-6-revisor-ola.md`. Decisiones de la sesión principal: (a) KEV se trata como crítica a efectos de SLA (7 días) según `vulnerabilities/policy.yaml`, y toda KEV o crítica abierta pone el dispositivo al menos en ámbar aunque esté dentro de SLA; (b) severidad normalizada (minúsculas, sin tildes) y la desconocida cuenta como crítica con aviso; (c) `reglas()` devuelve una lista `any_any` con independencia del estado y el Markdown la destaca; (d) VRT-NET con subverticales evaluadas se muestra como «no puntúa (detallada en FW, SASE, ZTNA y OSI)» en Markdown y HTML; (e) baremo 0-5: cada vertical lleva `niveles` con un descriptor por nivel 0-5 (validado: 6 niveles) además de los `criterios`; (f) mapeos ENS: VRT-EDR a ENS-op.exp.6 y VRT-ENDUSER a ENS-op.exp.4; (g) firewalls de la plantilla a VRT-FW; (h) madurez por táctica = mínimo de los casos activos (documentado) y se expone en el CLI; los casos no activos se marcan aparte; (i) `coste_anual` no numérico da aviso; (j) escape de `<`, `>` y `|` en el Markdown de verticales; (k) corrige la atribución del informe T15. Sube la versión a 0.5.1 y añade la entrada al CHANGELOG.
  - No hace: no añade secciones nuevas al informe HTML ni al dashboard (v0.6); no construye el visor 3D.
  - Toca: `smc/`, `tests/`, `soc/verticals.yaml`, `technologies/registry.template.yaml`, `docs/mapa-3d.md`, `docs/plan/informes/T15-dev-proyecto.md`, `CHANGELOG.md`, `pyproject.toml`, `README.md`, `docs/plan/informes/T17-dev-proyecto.md`
  - Depende: T16
  - Verifica: un test por hallazgo con su contraprueba anotada en el informe; los 196 tests previos verdes salvo cambios justificados.
  - Prod: —
  - Estado: hecha en a329797 · evidencia informes/T17-dev-proyecto.md

## Ola 8 (v0.5.2)

- [x] **T18** — Vertical GRC (gobierno, riesgo y cumplimiento)
  - Hace: añade `VRT-GRC` a `soc/verticals.yaml` con el mismo formato que las demás (nis2, controles existentes, criterios y `niveles` 0-5 concretos). Cubre: responsabilidad y supervisión de la dirección (NIS2 art. 20), formación de la dirección, política y marco normativo, análisis y tratamiento de riesgos, registro y aceptación de riesgos, gestión de excepciones, indicadores y cuadro de mando de cumplimiento, auditorías (ENS bienal en MEDIA/ALTA, ISO 27001), declaración de aplicabilidad, gestión de terceros desde el punto de vista contractual, registro de actividades y protección de datos (RGPD), notificación a autoridades, y seguimiento normativo (transposición de NIS2, cambios CCN-STIC). Controles relacionados solo con IDs existentes en los catálogos (NIS2-20.x, NIS2-21.2.a, NIS2-21.2.f, ENS-org.*, ENS-op.pl.1, controles TRV de ISO/RGPD/DORA que existan). Sin `recursos` (no hay páginas públicas de GRC; no enlazar repos privados). Añade la vertical a la sección `verticales:` de la plantilla y de los dos ejemplos ficticios. Quita además los nombres de repos privados de `docs/plan/informes/T09-dev-proyecto.md` y `docs/plan/informes/T12-dev-proyecto.md` (sustituir por «un repo privado»). Actualiza cifras (20 verticales) en README, `soc/README.md` y CHANGELOG 0.5.2; versión 0.5.2.
  - No hace: no toca código de `smc/` salvo que un test de cifras o versión lo exija.
  - Toca: `soc/verticals.yaml`, `soc/README.md`, `assessments/assessment.template.yaml`, `assessments/examples/`, `docs/plan/informes/T09-dev-proyecto.md`, `docs/plan/informes/T12-dev-proyecto.md`, `README.md`, `CHANGELOG.md`, `pyproject.toml`, `smc/__init__.py`, `tests/`, `docs/plan/informes/T18-dev-proyecto.md`
  - Depende: T17
  - Verifica: `smc validate` OK y `smc verticals` sobre los ejemplos muestra VRT-GRC agregada a NIS2 20/21.2; `git grep` de los nombres de repos privados fuera de `tests/` vacío. Contraprueba: un control inexistente en VRT-GRC pone un test en rojo.
  - Prod: —
  - Estado: hecha en f26fa59 · evidencia informes/T18-dev-proyecto.md

## Ola 9 (v0.6)

- [x] **T19** — Tecnologías, reglas, suscripciones y MITRE en el informe HTML y el dashboard
  - Hace: `smc report` acepta opcionalmente `--registry <registry.yaml>` y `--hoy`; con registry añade al HTML (y al Markdown) secciones de tecnologías evaluadas, estado de reglas (revisadas, sin revisar, no evaluables con motivo, lista `any_any` destacada) y suscripciones (vencen en 90 días, uso bajo umbral, coste anual total). Siempre añade la sección de madurez MITRE (por táctica y casos sin playbook) desde `smc.mitre`. El dashboard estático (`smc dashboard`) añade, si en el directorio hay registros (`kind`/forma de registry), columnas de reglas no evaluables, any-any y suscripciones que vencen, y una página de madurez MITRE común. Reutiliza `smc.tech` y `smc.mitre`: no reimplementa cálculos. Escape HTML en todo, solo enlaces `https://`.
  - No hace: no cambia catálogos ni el cálculo de prioridad; no toca `smc/mapa.py`.
  - Toca: `smc/report_html.py`, `smc/dashboard.py`, `smc/gap.py` (solo render Markdown si hace falta), `smc/cli.py` (solo flags de `report`/`dashboard`), `tests/test_report_v06.py`, `docs/plan/informes/T19-dev-proyecto.md`
  - Depende: T18
  - Verifica: `smc report` sobre los ejemplos con y sin `--registry` rc=0; el HTML contiene las 4 secciones; contraprueba: un `motivo` con `<script>` en reglas no evaluables sale escapado; un `coste_anual` no numérico no rompe.
  - Prod: —
  - Estado: hecha en 3b26090 · evidencia informes/T19-dev-proyecto.md

- [x] **T20** — Visor 3D offline del mapa de dispositivos
  - Hace: `python -m smc.visor <mapa.json> -o visor.html` (función `generar_visor(mapa: dict) -> str`; el subcomando `smc visor` lo cablea T22) genera una sola página HTML autocontenida que lee SOLO el JSON `smc-mapa/1` embebido (sin fetch, sin CDN, sin red). Patrón de teardown (ADR-003): la red es la máquina; cada zona es un subsistema (plataforma/anillo) con un botón que la abre y enfoca la cámara; dispositivos como piezas coloreadas por semáforo (verde, ámbar, rojo, gris; gris nunca se pinta verde); `sin_zona` en un área aparte; panel lateral que lee los números del JSON (dispositivos, reglas no evaluables con motivo, vulns fuera de SLA, KEV); vistas de cámara; visita automática que cede el control al primer gesto; respeta `prefers-reduced-motion`; alternativa en texto (tabla accesible con la misma información, ADR-003). Librería: three.js (MIT) incrustada en el HTML desde una copia vendorizada `smc/assets/three.module.min.js` minificada o el `three.module.js` de 0.186 con su `LICENSE` en `smc/assets/THREE-LICENSE`; origen y versión anotados. No copia código de la skill teardown (solo el patrón). ADR-004 con la decisión de vendorizar three.js. Escape de todos los textos del JSON al insertarlos en el DOM (textContent, nunca innerHTML con datos); el JSON se inserta en `<script type="application/json">` con `<` escapado como `<`.
  - No hace: no cambia el esquema `smc-mapa/1` ni `smc/mapa.py`; no toca `smc/cli.py`; no graba vídeo.
  - Toca: `smc/visor.py`, `smc/assets/`, `pyproject.toml` (package-data de assets), `tests/test_visor.py`, `docs/mapa-3d.md`, `docs/adr/ADR-004-three-js-vendorizado.md`, `docs/plan/informes/T20-dev-proyecto.md`
  - Depende: T18
  - Verifica: el HTML del ejemplo no contiene `http://` ni `https://` cargados como script/fetch (test); abre en Chrome headless sin errores de consola y dibuja (captura en el informe, Playwright channel chrome); contraprueba: un nombre de dispositivo `</script><img onerror>` no rompe ni ejecuta.
  - Prod: —
  - Estado: hecha en 6fc75da · evidencia informes/T20-dev-proyecto.md

- [x] **T21** — Contrastar las medidas ENS con el Anexo II del RD 311/2022 (BOE)
  - Hace: contrasta las 73 medidas de `frameworks/ens/controls.yaml` con el texto consolidado del BOE (BOE-A-2022-7191, Anexo II): id, grupo, título, categoría mínima (BASICA/MEDIA/ALTA o aplica por dimensión) y refuerzos por categoría. Corrige lo que no coincida y quita `verificar: true` solo de lo contrastado; deja en `verificar` (con nota) lo que dependa de dimensiones o de guías CCN-STIC no consultadas. Fuente citada con URL del BOE en la cabecera. Actualiza los mapeos que dependan de ids corregidos y los tests de cifras.
  - No hace: no cambia la fórmula de prioridad ni otros marcos.
  - Toca: `frameworks/ens/controls.yaml`, `mappings/`, `tests/test_ens.py`, `tests/test_ens_boe.py`, `tests/test_smc.py`, `tests/test_gap_v02.py`, `tests/test_t08.py`, `tests/test_t17.py`, `tests/test_t18.py`, `docs/plan/informes/T21-dev-proyecto.md`
  - Depende: T18
  - Verifica: tabla en el informe medida a medida (coincide / corregido / sigue verificar y por qué) con la URL y fecha de consulta; `smc validate` OK; contraprueba: un id ENS inexistente en un mapeo pone un test en rojo.
  - Prod: —
  - Estado: hecha en 880a926 · evidencia informes/T21-dev-proyecto.md

## Ola 10 (v0.6.0)

- [x] **T22** — Documentación y versión 0.6.0
  - Hace: cablea `smc visor <mapa.json> -o visor.html` en el CLI (llama a `smc.visor.generar_visor`) con test; README (mismo estilo: badges, imágenes; cifras reales; comandos `report --registry`, `visor`; hoja de ruta v0.6 hecha y lo que queda), PRD (RF nuevos), `docs/mapa-3d.md` enlazado, CHANGELOG 0.6.0, versión 0.6.0; nota de que el ENS ya está contrastado con el BOE (o cuántas medidas siguen en verificar).
  - No hace: no regenera imágenes salvo una captura nueva del visor en `docs/img/visor.png` si el informe de T20 la deja.
  - Toca: `smc/cli.py`, `tests/test_cli_v06.py`, `README.md`, `docs/prd/PRD-SMC-001-v1.md`, `CHANGELOG.md`, `pyproject.toml`, `smc/__init__.py`, `docs/img/`, `docs/plan/informes/T22-dev-proyecto.md`
  - Depende: T19, T20, T21
  - Verifica: todos los comandos del README rc=0 sobre los ejemplos; badges con cifras reales.
  - Prod: —
  - Estado: hecha en a2b7aef · evidencia informes/T22-dev-proyecto.md

## Ola 11 (v0.6.1)

- [x] **T23** — Endurecer v0.6 antes de publicar (hallazgos de revisor-ola ola 9)
  - Hace: corrige los hallazgos 1-6 y 8 de `informes/ola-9-revisor-ola.md`. Decisiones de la sesión principal: (a) emparejamiento registro-evaluación en el dashboard: gana el stem de evaluación más largo que case, y si dos casan igual, aviso y sin asociar; test con `acme`/`acme_sur`; (b) visor: validar como enteros no negativos `resumen.dispositivos` y `resumen.por_semaforo.*` (si faltan o no son enteros, ValueError y rc=2 sin traceback), escapar todo lo que entre en la cabecera, y CSP `script-src 'sha256-…'` calculado sobre el script constante en lugar de `'unsafe-inline'` (comprobar en Chrome que sigue dibujando); (c) texto del aviso ENS en `gap.py` y `report_html.py`: las 73 medidas están contrastadas con el Anexo II del BOE; las 28 marcadas dependen de las dimensiones C/I/T/A/D y faltan las guías CCN-STIC; actualizar `tests/test_t08.py`; (d) `proveedor`, `moneda` y demás campos de texto del registro se convierten con `str()` antes de escapar: nunca TypeError; (e) el HTML del visor incluye el texto completo de la licencia MIT de three.js en un comentario; (f) la tabla accesible del visor incluye CVE fuera de SLA, reglas (total, no evaluables, sin uso), semáforo de zona, avisos y totales del resumen; (g) la sección MITRE del informe de cliente lleva la etiqueta «Catálogo de casos de uso del SOC (común a todos los clientes)». Los refuerzos ENS se muestran tal cual la celda del BOE (decisión). Versión 0.6.1 y CHANGELOG.
  - No hace: no cambia catálogos ni el esquema `smc-mapa/1`.
  - Toca: `smc/dashboard.py`, `smc/visor.py`, `smc/assets/visor-app.js`, `smc/gap.py`, `smc/report_html.py`, `tests/`, `CHANGELOG.md`, `pyproject.toml`, `smc/__init__.py`, `README.md`, `docs/plan/informes/T23-dev-proyecto.md`
  - Depende: T22
  - Verifica: un test por hallazgo con su contraprueba anotada; el visor sigue dibujando en Chrome con la CSP nueva (0 errores de consola, `data-listo`); todos los tests verdes.
  - Prod: —
  - Estado: hecha en f621bca · evidencia informes/T23-dev-proyecto.md

## Ola 12 (v0.7)

- [x] **T24** — Pentesting (seguimiento) y purple team
  - Hace: módulo `smc/offensive.py` y carpeta `offensive/` con: plantilla `pentest.template.yaml` (campañas de pentest: alcance, tipo interno/externo/web/red team, proveedor, fechas; hallazgos con id, severidad, CVSS opcional, CWE, activo, control SMC relacionado, estado abierto/en_remediacion/corregido/aceptado/falso_positivo, fecha_deteccion, fecha_retest, resultado_retest) con SLA por severidad tomado de `vulnerabilities/policy.yaml` (reutiliza, no duplica); plantilla `purple.template.yaml` (ejercicios purple team: técnica ATT&CK, caso de uso del SOC de `soc/use-cases/catalog.yaml`, fecha, resultado detectado/parcial/no_detectado, tiempo de detección, mejora acordada y su estado). Funciones: `cargar_pentest`, `estado_hallazgos(datos, hoy)` (abiertos, fuera de SLA, pendientes de retest, aceptados sin fecha de revisión), `purple(datos, hoy)` (cobertura por táctica, técnicas no detectadas, mejoras abiertas, ejercicios con más de 12 meses) y `render_markdown`. Validación: ids ATT&CK con regex y casos de uso existentes. Ejemplos ficticios.
  - No hace: no toca `smc/cli.py`, `smc/mitre.py` ni catálogos existentes (no sube la madurez MITRE con ejercicios purple: lo decide T28).
  - Toca: `offensive/`, `smc/offensive.py`, `tests/test_offensive.py`, `docs/plan/informes/T24-dev-proyecto.md`
  - Depende: T23
  - Verifica: tests con `hoy` inyectado; contraprueba: un hallazgo crítico abierto más allá del SLA aparece fuera de SLA y un caso de uso inexistente en purple da error.
  - Prod: —
  - Estado: hecha en a2fda17 · evidencia informes/T24-dev-proyecto.md

- [x] **T25** — Verticales de identidad, dato, IA y seguridad ofensiva
  - Hace: añade a `soc/verticals.yaml`, con el formato vigente (nis2, controles existentes, criterios y `niveles` 0-5 concretos): `VRT-IAM` (identidad y su seguridad: IGA y ciclo de vida, MFA resistente a phishing, PAM, identidades no humanas y de servicio, ITDR, revisión de accesos, AD/Entra hardening), `VRT-DATA` (seguridad del dato: clasificación, DSPM, DLP en endpoint/correo/nube, identidades y permisos con acceso al dato, cifrado y claves, retención), `VRT-AI` (IA: inventario de sistemas y modelos, clasificación según el RIA, gobierno, seguridad de agentes y LLM según OWASP Top 10 for LLM Applications y MITRE ATLAS, permisos y herramientas de agentes, registro y supervisión humana) y `VRT-OFF` (pentesting y purple team: plan anual, retest, ejercicios purple, red team). Controles solo con IDs existentes en los catálogos. Recursos solo de la lista pública (si no hay, ninguno). Añade las 4 a la plantilla y a los dos ejemplos ficticios. Cifras: 24 verticales.
  - No hace: no toca `smc/` salvo `URLS_PUBLICAS` si hiciera falta (no debería).
  - Toca: `soc/verticals.yaml`, `soc/README.md`, `assessments/assessment.template.yaml`, `assessments/examples/`, `tests/test_verticals.py`, `tests/test_t18.py`, `tests/test_verticals_v07.py`, `docs/plan/informes/T25-dev-proyecto.md`
  - Depende: T23
  - Verifica: `smc validate` OK; `smc verticals` sobre los ejemplos muestra las 4; contraprueba: un control inexistente en VRT-AI pone un test en rojo.
  - Prod: —
  - Estado: hecha en a13ab5b · evidencia informes/T25-dev-proyecto.md

- [x] **T26** — RIA (Reglamento (UE) 2024/1689) y seguridad de agentes de IA
  - Hace: `frameworks/ai-act/obligaciones.yaml`: obligaciones por rol (proveedor, responsable del despliegue, importador, distribuidor) y por nivel de riesgo (prohibido art. 5, alto riesgo Anexo I y Anexo III, transparencia art. 50, modelos de uso general art. 53-55, riesgo mínimo), con artículo, descripción breve y fecha de aplicación vigente tras el Ómnibus Digital (Reglamento (UE) 2026/1744: alto riesgo Anexo III 2027-12-02, Anexo I 2028-08-02; contrastar art. 50 y demás fechas en el texto del DOUE o EUR-Lex; lo no contrastado lleva `verificar: true` con nota). `ai/inventario.template.yaml`: sistemas de IA del cliente (nombre, finalidad, rol, nivel de riesgo, datos personales, proveedor del modelo, agentes con herramientas y permisos, supervisión humana, registro). `smc/ai_act.py`: `clasificar` (valida nivel y rol), `obligaciones(inventario, hoy)` (obligaciones aplicables por sistema con estado por fecha: vigente / aplicable desde), `riesgos_agente` (comprobaciones de seguridad de agentes basadas en OWASP Top 10 for LLM Applications 2025 y MITRE ATLAS: herramientas sin límite, permisos excesivos, sin supervisión humana, sin registro, prompt injection sin mitigación) y `render_markdown`. Fuentes con URL https en la cabecera.
  - No hace: no toca `soc/verticals.yaml` (es de T25) ni `smc/cli.py`; no es asesoramiento jurídico (aviso en el render).
  - Toca: `frameworks/ai-act/`, `ai/`, `smc/ai_act.py`, `tests/test_ai_act.py`, `docs/plan/informes/T26-dev-proyecto.md`
  - Depende: T23
  - Verifica: tests con `hoy` inyectado antes y después de 2027-12-02; contraprueba: un sistema de alto riesgo sin supervisión humana genera la obligación pendiente; un nivel de riesgo inexistente da error.
  - Prod: —
  - Estado: hecha en 351cd26 · evidencia informes/T26-dev-proyecto.md

- [x] **T27** — PMO: vida del proyecto, horas, costes y presupuesto
  - Hace: `smc/pmo.py` y `pmo/` con plantilla `proyecto.template.yaml` y un ejemplo ficticio: proyecto (cliente ficticio, fechas, presupuesto total y por partida: horas, licencias, servicios, formación), tareas (id, título, controles o brechas SMC relacionados, acción del `plan_accion` opcional, responsable por rol, horas estimadas, horas imputadas, % avance, fechas, dependencias), tarifas por rol, imputaciones de horas (fecha, rol, tarea, horas), costes no laborales (proveedor, concepto, importe, fecha, partida), eventos e hitos (comités, auditorías, renovaciones, entregas) y riesgos del proyecto. Cálculos con `hoy` inyectado: coste real por partida, desviación sobre presupuesto, valor ganado simple (PV, EV, AC, CPI, SPI), tareas retrasadas, tareas sin control asociado, próximos eventos (30 días), horas por rol y mes. Opcional: sumar `coste_anual` de suscripciones de un registry vía `smc.tech` (sin recalcular). `render_markdown` y export de eventos a iCalendar (`.ics`, texto escapado según RFC 5545). `docs/pmo.md` y ADR-005 (presupuesto, horas y tarifas son datos de cliente: fuera del repositorio, ADR-001).
  - No hace: no toca `smc/cli.py` ni el informe HTML (lo integra T28); no es un gestor de proyectos completo (sin Gantt interactivo).
  - Toca: `pmo/`, `smc/pmo.py`, `tests/test_pmo.py`, `docs/pmo.md`, `docs/adr/ADR-005-pmo-datos-de-cliente.md`, `docs/plan/informes/T27-dev-proyecto.md`
  - Depende: T23
  - Verifica: EVM correcto en un caso calculado a mano en el test; contraprueba: una imputación a una tarea inexistente da aviso y un importe no numérico no rompe; el .ics valida (líneas CRLF, escapado de `,;\`).
  - Prod: —
  - Estado: hecha en 2f9d181 · evidencia informes/T27-dev-proyecto.md

## Ola 13 (v0.7.0)

- [x] **T28** — Integración v0.7 y documentación
  - Hace: subcomandos `smc pentest <fichero>`, `smc purple <fichero>`, `smc ai <inventario>`, `smc pmo <proyecto> [--ics eventos.ics] [--registry r.yaml]`; `smc validate` valida también `frameworks/ai-act/` y las plantillas nuevas; informe HTML y dashboard con secciones de pentest/purple, IA y PMO cuando se pasen los ficheros (`smc report ... --pentest --purple --ai --pmo`), con escape y solo `https://`. Decide y documenta si los ejercicios purple detectados cuentan como «probada» en la madurez MITRE (recomendado: sí, con fecha del ejercicio). README (mismo estilo; cifras reales; módulos nuevos), PRD, CHANGELOG 0.7.0, versión 0.7.0.
  - No hace: no cambia catálogos de T24-T27 salvo errores (anotados).
  - Toca: `smc/cli.py`, `smc/catalog.py`, `smc/report_html.py`, `smc/dashboard.py`, `smc/gap.py`, `smc/mitre.py`, `tests/test_cli_v07.py`, `tests/test_t08.py`, `tests/test_cli_v06.py`, `README.md`, `docs/prd/PRD-SMC-001-v1.md`, `CHANGELOG.md`, `pyproject.toml`, `smc/__init__.py`, `docs/plan/informes/T28-dev-proyecto.md`
  - Depende: T24, T25, T26, T27
  - Verifica: cada comando nuevo rc=0 sobre los ejemplos; XSS en un título de tarea PMO y en un hallazgo de pentest sale escapado (contraprueba); todos los comandos del README rc=0.
  - Prod: —
  - Estado: hecha en 1f7f610 · evidencia informes/T28-dev-proyecto.md

## Ola 14 (v0.7.1)

- [x] **T29** — Endurecer v0.7 (hallazgos de revisor-ola olas 12-13)
  - Hace: corrige los hallazgos 1-6 y 9 de `informes/ola-12-13-revisor-ola.md`. Decisiones: (a) purple cuenta para la madurez solo si `tecnica` está en las técnicas del caso de uso; (b) por caso y técnica manda el ejercicio más reciente: solo sube si ese es `detectado`; la madurez nunca baja por debajo de lo declarado en el catálogo; (c) hallazgo `corregido` con `resultado_retest` `persiste` o `parcial` se trata como abierto con su SLA desde `fecha_deteccion` y aparece además en una lista `retest_fallido` con aviso; (d) RIA: obligación nueva para el art. 111.2 (sistemas de alto riesgo en el mercado antes de la fecha del capítulo III: obligados solo con cambios significativos de diseño; los destinados a autoridades públicas, a más tardar 2030-08-02), con campos de inventario opcionales `en_mercado_desde`, `cambios_significativos`, `autoridad_publica`; contrastar con el PDF del BOE del Ómnibus; (e) `*.ics` al `.gitignore`; (f) aviso en PMO cuando una tarea tiene costes no laborales y no tiene `presupuesto` explícito; (g) comprobar AML.T0101, AML.M0036 y AML.M0037 contra `ATLAS.yaml` de mitre-atlas/atlas-data y corregir los que no existan; (h) corrige el informe T25 (22 verticales). Versión 0.7.1 y CHANGELOG.
  - No hace: no añade funciones nuevas.
  - Toca: `smc/mitre.py`, `smc/offensive.py`, `smc/ai_act.py`, `smc/pmo.py`, `frameworks/ai-act/obligaciones.yaml`, `ai/inventario.template.yaml`, `.gitignore`, `tests/`, `docs/plan/informes/T25-dev-proyecto.md`, `CHANGELOG.md`, `pyproject.toml`, `smc/__init__.py`, `README.md`, `docs/plan/informes/T29-dev-proyecto.md`
  - Depende: T28
  - Verifica: un test por hallazgo con su contraprueba anotada; todos los tests verdes.
  - Prod: —
  - Estado: hecha en 51f5745 · evidencia informes/T29-dev-proyecto.md

## Ola 15 (v0.8)

- [x] **T30** — CI en GitHub Actions y política de versiones
  - Hace: `.github/workflows/tests.yml` que en cada push y pull request a `main` instala con `uv` (Python 3.11 y 3.12), ejecuta `uv run --extra dev pytest -q`, `smc validate` y los comandos de ejemplo del README que no escriben fuera de un directorio temporal; permisos mínimos (`permissions: contents: read`), acciones fijadas por SHA de commit con el tag en comentario, sin secretos ni red más allá de instalar dependencias. `docs/release.md`: versionado semántico, qué sube mayor/menor/parche, checklist de release (tests, validate, gitleaks, nombres de repos privados, CHANGELOG, versión en `pyproject.toml` y `smc/__init__.py`, tag anotado `vX.Y.Z`, push del tag lo hace David). Un test que comprueba que la versión de `pyproject.toml`, `smc/__init__.py` y la última entrada del CHANGELOG coinciden.
  - No hace: no toca README (lo hace T35) ni crea tags (los crea la sesión principal). No publica en PyPI.
  - Toca: `.github/workflows/tests.yml`, `docs/release.md`, `tests/test_version.py`, `docs/plan/informes/T30-dev-proyecto.md`
  - Depende: T29
  - Verifica: el YAML del workflow parsea con `yaml.safe_load` y tiene `permissions` y acciones con SHA de 40 hex (test); `act` no es obligatorio; contraprueba: cambiar la versión en `smc/__init__.py` pone `test_version` en rojo.
  - Prod: —
  - Estado: hecha en 2869e47 · evidencia informes/T30-dev-proyecto.md

- [x] **T31** — Comparación entre evaluaciones (evolución)
  - Hace: `smc/compare.py` con `comparar(anterior, actual, hoy=None) -> Comparacion` que reutiliza `smc.gap.analyse` sobre las dos evaluaciones (no reimplementa el análisis) y devuelve: cumplimiento por marco antes, después y delta; controles que mejoran, empeoran, cerrados (brecha que deja de serlo), nuevas brechas y sin cambio; P1 antes y después; madurez de verticales antes, después y delta (vía `smc.verticals.evaluar`, `estricto=False`); acciones del `plan_accion` cerradas entre una y otra. Avisos si los clientes no coinciden, si la evaluación «actual» es más antigua (campo `fecha` si existe; si no, aviso) o si la categoría ENS cambia (el delta ENS no es comparable y se marca). `render_markdown(comp)`. Un segundo ejemplo ficticio `assessments/examples/historico/ejemplo-energia-2026-q1.yaml` (mismo cliente ficticio que `ejemplo-energia.yaml`, unos meses antes, con más brechas) para demostrar la evolución.
  - No hace: no toca `smc/gap.py`, `smc/cli.py`, ni el informe HTML (lo integra T35). No cambia `ejemplo-energia.yaml`.
  - Toca: `smc/compare.py`, `tests/test_compare.py`, `assessments/examples/historico/`, `docs/plan/informes/T31-dev-proyecto.md`
  - Depende: T29
  - Verifica: deltas calculados a mano en el test sobre el par de ejemplos; contraprueba: intercambiar anterior y actual invierte el signo y da aviso de fechas; clientes distintos dan aviso. Comprobar que los tests existentes que leen `assessments/examples/` (dashboard) no cambian con la subcarpeta nueva; si cambian, anotarlo y decidir con el coordinador.
  - Prod: —
  - Estado: hecha en 9698b14 · evidencia informes/T31-dev-proyecto.md

- [x] **T32** — Salida para auditor: declaración de aplicabilidad y registro de evidencias
  - Hace: `smc/soa.py` con `declaracion(assessment, hoy=None)` que, a partir de `smc.gap.analyse`, produce filas por control de cada marco aplicable (marco, id, título, aplica sí/no, justificación de no aplicación —`notas` o el motivo de categoría ENS—, estado, evidencias, prioridad si es brecha, refuerzos ENS de la categoría, mapeo a otros marcos de `mappings/`) y una hoja de evidencias (control, evidencia, fecha y caducidad si la evidencia es un dict, ver formato en Decisiones). Exportadores: `a_csv(filas) -> str` (stdlib `csv`, UTF-8 con BOM para Excel, sin inyección de fórmulas: celdas que empiezan por `= + - @` o tabulador se prefijan con `'`), `a_xlsx(hojas) -> bytes` (SpreadsheetML mínimo con `zipfile` de la stdlib, sin dependencias, cadenas en línea escapadas para XML, dos hojas: «Aplicabilidad» y «Evidencias») y `a_html(filas) -> str` imprimible a PDF desde el navegador (`@media print`, escape, sin JS ni CDN). Aviso fijo: «Documento de trabajo generado por SMC; la declaración formal la firma el responsable de seguridad».
  - No hace: no toca `smc/cli.py` ni `smc/gap.py`. No genera PDF directamente (sin dependencias).
  - Toca: `smc/soa.py`, `tests/test_soa.py`, `docs/plan/informes/T32-dev-proyecto.md`
  - Depende: T29
  - Verifica: el xlsx abre con `zipfile` y su XML parsea con `xml.etree` (test) y contiene las dos hojas; ENS MEDIA del ejemplo da 73 filas ENS con las no aplicables justificadas; contraprueba: una evidencia `=HYPERLINK(...)` sale prefijada en CSV y XLSX y un `<script>` sale escapado en HTML.
  - Prod: —
  - Estado: hecha en 62e093e · evidencia informes/T32-dev-proyecto.md

- [x] **T33** — Evidencias con fecha, caducidad y huella
  - Hace: admite en `evidencias` de cada control, además de texto, un dict `{ref, fecha (AAAA-MM-DD), caduca (AAAA-MM-DD) | vigencia_dias, sha256 (64 hex, opcional)}` (formato en Decisiones). `smc/evidencias.py`: `normalizar(e)`, `estado(e, hoy)` (vigente, caduca_pronto ≤ 30 días, caducada, sin_fecha), `verificar_huellas(assessment, base: Path)` (calcula sha256 de `base/ref` cuando `ref` es una ruta relativa sin `..` ni absoluta y la compara; no sigue enlaces simbólicos fuera de `base`) y `render_markdown`. En `smc/gap.py`: `FrameworkResult` gana `evidencia_caducada` (implementados cuyas evidencias están todas caducadas), listado en el Markdown y aviso; **no cambia la puntuación** (decisión anotada; se revisa con David). Texto plano sigue funcionando igual. Plantilla con un ejemplo del formato dict comentado y el ejemplo `ejemplo-energia.yaml` con dos evidencias en formato dict (una caducada) para demostrarlo.
  - No hace: no toca `smc/cli.py` ni el informe HTML (lo integra T35); no sube ficheros de evidencia al repo.
  - Toca: `smc/evidencias.py`, `smc/gap.py`, `assessments/assessment.template.yaml`, `assessments/examples/ejemplo-energia.yaml`, `tests/test_evidencias.py`, `docs/plan/informes/T33-dev-proyecto.md`
  - Depende: T29
  - Verifica: tests con `hoy` inyectado para los cuatro estados; huella correcta e incorrecta sobre un fichero temporal; contraprueba: `ref: ../../etc/passwd` y una ruta absoluta no se leen (aviso); todos los tests anteriores siguen verdes (las cifras de cumplimiento del ejemplo no cambian).
  - Prod: —
  - Estado: hecha en b743827 · evidencia informes/T33-dev-proyecto.md

- [x] **T34** — Flecos de la v0.7: art. 111.2 del RIA y retest fallido en el informe
  - Hace: (a) en `smc/ai_act.py`, cuando un sistema de alto riesgo tiene `en_mercado_desde` anterior a la fecha de su nivel y `cambios_significativos` no es verdadero, las obligaciones del capítulo III de ese nivel no se emiten como pendientes: salen en una lista `regimen_transitorio` con la fecha en que pasarían a aplicar (2030-08-02 si `autoridad_publica`; si no, «solo con cambios significativos»); AIA-070 sigue apareciendo como aviso; actualiza la `nota` de AIA-070. Las obligaciones que no son del capítulo III (art. 4, 5, 50, uso general) no se recortan. Contrastar el alcance con el texto del art. 111.2 en EUR-Lex (excepción a «sin red» ya aprobada para el RIA). (b) En `smc/report_html.py`, la sección de pentest muestra una tabla «Retest fallido» propia (escapada) cuando `retest_fallido` no está vacío.
  - No hace: no toca `smc/cli.py` ni otras secciones del informe.
  - Toca: `smc/ai_act.py`, `frameworks/ai-act/obligaciones.yaml`, `smc/report_html.py`, `tests/test_t34.py`, `docs/plan/informes/T34-dev-proyecto.md`
  - Depende: T29
  - Verifica: sistema Anexo III en mercado desde 2026-01-01 sin cambios: sin obligaciones de capítulo III pendientes y con régimen transitorio; con `cambios_significativos: true`: vuelven todas (contraprueba); con `autoridad_publica: true` y `hoy` 2030-08-03: vuelven. Informe HTML con un hallazgo de retest fallido muestra la tabla y escapa `<script>`.
  - Prod: —
  - Estado: hecha en 4b9a8b9 · evidencia informes/T34-dev-proyecto.md

## Ola 16 (v0.8.0)

- [x] **T35** — Integración v0.8 y documentación
  - Hace: subcomandos `smc compare <anterior.yaml> <actual.yaml> [--hoy] [-o]`, `smc soa <evaluación.yaml> --formato csv|xlsx|html -o <fichero>` y `smc evidencias <evaluación.yaml> [--base <dir>] [--hoy]`; `smc report ... --anterior <evaluación.yaml>` añade una sección «Evolución» (escapada); el dashboard muestra la evidencia caducada por cliente. README (mismo estilo, cifras reales, badge del workflow de CI, sección de comparación, salida para auditor y evidencias), PRD (RF nuevos), CHANGELOG 0.8.0, versión 0.8.0.
  - No hace: no cambia la lógica de T31-T34 salvo errores (anotados).
  - Toca: `smc/cli.py`, `smc/report_html.py`, `smc/dashboard.py`, `smc/catalog.py`, `tests/test_cli_v08.py`, `README.md`, `docs/prd/PRD-SMC-001-v1.md`, `CHANGELOG.md`, `pyproject.toml`, `smc/__init__.py`, `docs/plan/informes/T35-dev-proyecto.md`
  - Depende: T30, T31, T32, T33, T34
  - Verifica: cada comando nuevo rc=0 sobre los ejemplos; `smc soa` en los tres formatos; todos los comandos del README rc=0; `test_version` verde con 0.8.0.
  - Prod: —
  - Estado: hecha en cb3ead8 · evidencia informes/T35-dev-proyecto.md

## Ola 17 (v0.8.1)

- [x] **T36** — Endurecer v0.8 (hallazgos de revisor-ola olas 15-16)
  - Hace: corrige los hallazgos 1-9 de `informes/ola-15-16-revisor-ola.md`. Decisiones: (a) `cambios_significativos`, `autoridad_publica` y `en_mercado_desde` se validan: los dos primeros solo bool (otro tipo = error de validación en `validar_inventario`); **ausente no recorta** (cuenta como «no consta»: las obligaciones del capítulo III se emiten como pendientes, con aviso de que, si no hay cambios significativos, aplicaría el régimen transitorio); actualiza la plantilla y la nota pública de AIA-070 sin jerga del plan; (b) `smc/soa.py` usa `smc.evidencias.normalizar` y `estado` (una sola lógica de caducidad; fechas con hora, cadenas sin guiones y `vigencia_dias` fuera de rango no rompen y dan aviso; el CLI captura los errores de datos con rc=2, sin traceback); (c) el XLSX filtra todos los caracteres no válidos en XML 1.0 (incluidos `\uFFFE`, `\uFFFF` y surrogates sueltos); (d) `smc/compare.py` clasifica solo controles aplicables según `analyse` de cada evaluación y añade el grupo «dejan de evaluarse» (presentes antes, ausentes ahora) y «sin catálogo» para IDs inexistentes (aviso); los totales cuadran con los porcentajes; (e) `smc report --anterior` valida que el fichero sea un mapa (rc=2 si no); (f) el CI ejecuta también `compare`, `soa` (tres formatos), `evidencias` y `report --anterior`, y la matriz incluye Python 3.10; (g) el CSV de soa neutraliza también celdas cuyo primer carácter no blanco sea `= + - @` o su variante de ancho completo, y las que empiezan por `\n`; (h) la caducidad de evidencias sale en el informe HTML (sección de cada marco, escapada); (i) CHANGELOG corregido. Versión 0.8.1 y CHANGELOG.
  - No hace: no añade funciones nuevas.
  - Toca: `smc/ai_act.py`, `ai/inventario.template.yaml`, `frameworks/ai-act/obligaciones.yaml`, `smc/soa.py`, `smc/evidencias.py`, `smc/compare.py`, `smc/cli.py`, `smc/report_html.py`, `.github/workflows/tests.yml`, `tests/`, `README.md`, `CHANGELOG.md`, `pyproject.toml`, `smc/__init__.py`, `docs/prd/PRD-SMC-001-v1.md`, `docs/plan/informes/T36-dev-proyecto.md`
  - Depende: T35
  - Verifica: un test por hallazgo con su contraprueba anotada (los escenarios del informe del revisor reproducidos); todos los tests verdes; comandos del README rc=0.
  - Prod: —
  - Estado: hecha en c1e83b2 · evidencia informes/T36-dev-proyecto.md

## Ola 18 (SMC-003)

- [x] **T37** — Paginar las lecturas de la API en `collect_pr`
  - Issue: SMC-003 https://github.com/pedri77/security-manager-control/issues/13
  - Hace: `collect_pr` de `scripts/change_evidence.py` lee todas las páginas de commits, reviews, check-runs y estados del commit, y cumple los criterios de aceptación de la issue. Si `blind-review` se publicó varias veces sobre el mismo SHA, cuenta el estado más reciente. Un error de lectura de checks o estados, también en una página posterior, sigue anotándose como hueco.
  - No hace: no toca `is_release_pr`, los workflows ni la plantilla de enjambre-agentes. No cambia el formato del registro de cambio. No toca versión ni CHANGELOG (los lleva release-please).
  - Toca: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, `docs/plan/informes/T37-dev-proyecto.md`
  - Depende: T36
  - Verifica: `uv run --extra dev pytest -q tests/test_change_evidence.py` y `make test` en verde; un test por criterio de la issue, con `gh` simulado y varias páginas; contraprueba anotada en el informe: con la lectura de una sola página, cada test nuevo falla.
  - Prod: —
  - Estado: hecha en 97e4d3c546382d4be9c9140d02658174b4047f82 · evidencia informes/T37-dev-proyecto.md

- [x] **T38** — Tope de páginas como hueco (FAIL de revisión ciega del PR #15)
  - Issue: SMC-003 https://github.com/pedri77/security-manager-control/issues/13
  - Hace: el error que lanza `gh_pages` al superar `MAX_PAGES` se trata igual que un error de lectura: en `collect_pr` queda como hueco al leer checks o estados, y `mode_release` no aborta y escribe el pack con el hueco anotado, también si el tope salta en commits o reviews. Añade test del desempate por `id` de `latest_status`: dos estados con el mismo `created_at` y distinto resultado.
  - No hace: no cambia `PER_PAGE`, `MAX_PAGES`, `is_release_pr`, los workflows ni la plantilla. No cambia el comportamiento ante errores en modo PR para commits y reviews.
  - Toca: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, `docs/plan/informes/T38-dev-proyecto.md`
  - Depende: T37
  - Verifica: `uv run --extra dev pytest -q tests/test_change_evidence.py` y `make test` en verde; test del tope en checks, en estados y en modo release; contraprueba anotada: si el tope corta en silencio, o si el `except` no lo captura, esos tests fallan; si `latest_status` ordena solo por `created_at`, el test de desempate falla.
  - Prod: —
  - Estado: hecha en 08fba06dab59fb502ed46caa1470ca942ad8a79b · evidencia informes/T38-dev-proyecto.md

## Ola 19 (SMC-004, prueba real del enjambre con F2P)

- [x] **T39** — Error limpio en `smc gap` y `smc plan`
  - Issue: SMC-004 https://github.com/pedri77/security-manager-control/issues/14
  - Hace: `smc gap` y `smc plan` con fichero inexistente o YAML mal formado escriben `ERROR: <ruta>: <motivo>` en stderr y salen con rc=2, sin traceback, igual que `smc evidencias` y `smc compare`. Reutiliza `_ERRORES_DATOS` y `_error` de `smc/cli.py`. Si falla, `smc gap -o` no crea el fichero de salida.
  - No hace: no cambia el YAML válido que no es un mapa (sigue rc=0 con aviso), ni los fallos al escribir en `-o`, ni `smc report`, `smc dashboard` u otros comandos. No toca `smc/gap.py`, `smc/plan.py`, README ni CHANGELOG (lo genera release-please).
  - Toca: `smc/cli.py`, `tests/test_cli_errores.py`, `docs/plan/informes/T39-dev-proyecto.md`
  - Depende: T36
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde, con un test por criterio de aceptación de la issue. Contraprueba en una copia temporal, no en el worktree: quitar la captura de errores de `gap` y de `plan` pone en rojo los tests nuevos.
  - Prod: —
  - Estado: hecha en 2877f634a68b028cad5cb174960f0f6cbf1441b8 · evidencia informes/T39-dev-proyecto.md

- [x] **T40** — Cerrar el FAIL de revisión ciega del PR #16
  - Issue: SMC-004 https://github.com/pedri77/security-manager-control/issues/14
  - Hace: (1) `smc gap` y `smc plan` capturan también `RecursionError`, que PyYAML lanza con anidamiento profundo: un YAML con 500 corchetes sin cerrar da `ERROR: <ruta>: <motivo>` y rc=2, sin traceback. (2) Tests de referencia para el criterio 5 de la issue: la salida de `smc gap`, de `smc gap -o` y de `smc plan` con una evaluación válida y `--hoy` fijo se compara con ficheros de referencia generados con el código de `0c1a5be`, anterior a este cambio, nunca con el código nuevo. El test `test_evaluacion_valida_sigue_igual` deja de comparar dos ejecuciones entre sí.
  - No hace: no añade `RecursionError` a `_ERRORES_DATOS`: cambiaría otros comandos, fuera de alcance. No toca `smc evidencias`, `smc/gap.py` ni `smc/plan.py`. No reordena la captura de `ValueError` y `OSError`.
  - Toca: `smc/cli.py`, `tests/test_cli_errores.py`, `tests/golden/`, `docs/plan/informes/T40-dev-proyecto.md`
  - Depende: T39
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde. Contraprueba en una copia temporal, no en el worktree, y con `PYTHONPATH` apuntando a esa copia (la instalación editable importa `smc` de otro sitio): cada mutante por separado debe poner en rojo al menos un test de `tests/test_cli_errores.py`: quitar `RecursionError` de `gap`, quitarlo de `plan`, `print(report + "X")`, `write_text(report + "X")`, y añadir una línea a `run_plan`. El informe da el resultado medido de cada mutante, test a test.
  - Prod: —
  - Estado: hecha en 11a2e6fb41cb4e36960b7b32288ae8090d032749 · evidencia informes/T40-dev-proyecto.md

- [x] **T41** — Cerrar el segundo FAIL de revisión ciega del PR #16
  - Issue: SMC-004 https://github.com/pedri77/security-manager-control/issues/14
  - Hace: `_load` de `smc/gap.py` convierte en `ValueError` las excepciones `KeyError`, `IndexError` y `AttributeError` que `yaml.safe_load` lanza con un escalar que no cumple su tag explícito, como `a: !!bool abc`, `a: !!int ""`, `a: !!float ""` y `a: !!timestamp abc`. El `try` envuelve solo `yaml.safe_load`, no `read_text`. El mensaje es de una línea y dice que el YAML no es válido. Con eso, `smc gap` y `smc plan` dan `ERROR: <ruta>: <motivo>` y rc=2, sin traceback. Decisión de David (05-11): el arreglo va en `_load` aunque también cambie `evidencias`, `compare` y `soa`, que comparten esa función.
  - No hace: no toca `smc/cli.py` ni `_ERRORES_DATOS`: ampliar el `except` ocultaría fallos internos de `analyse`. No toca `tests/golden/`. No captura `Exception`. No cambia los `yaml.safe_load` de otros módulos.
  - Toca: `smc/gap.py`, `tests/test_cli_errores.py`, `docs/plan/informes/T41-dev-proyecto.md`
  - Depende: T40
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde. Los cuatro documentos de «Hace» están en `MALAS` o en un test equivalente, para `gap` y para `plan`. `git diff` no toca `tests/golden/`. Contraprueba en una copia temporal, con `PYTHONPATH` apuntando a esa copia y lanzando desde ella: cada mutante por separado debe poner en rojo al menos un test de `tests/test_cli_errores.py`: quitar `KeyError` de la tupla, quitar `IndexError`, quitar `AttributeError` y borrar el `try` entero. El informe da el resultado medido de cada mutante, test a test.
  - Prod: —
  - Estado: hecha en 05ff66c809bf361e6eda3003733c1d4801300115 · evidencia informes/T41-dev-proyecto.md

- [x] **T42** — `_load` convierte también `TypeError` de tags YAML
  - Issue: SMC-004 https://github.com/pedri77/security-manager-control/issues/14
  - Hace: añade `TypeError` a la tupla de `_load` en `smc/gap.py`. Con `a: !!timestamp {=}`, `yaml.safe_load` lanza `TypeError`, y `smc gap` y `smc plan` dan traceback y rc=1. Tras el cambio dan `ERROR: <ruta>: <motivo>` y rc=2. Hueco medido antes del push de T41, sobre `2ee27ba`.
  - No hace: no toca `smc/cli.py` ni `_ERRORES_DATOS`. No toca `tests/golden/`. No captura `Exception`. No cambia el mensaje de error.
  - Toca: `smc/gap.py`, `tests/test_cli_errores.py`, `docs/plan/informes/T42-dev-proyecto.md`
  - Depende: T41
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde. `a: !!timestamp {=}` está en `MALAS`, para `gap` y para `plan`. `git diff` no toca `tests/golden/`. Contraprueba en una copia temporal, con `PYTHONPATH` apuntando a esa copia y lanzando desde ella: quitar `TypeError` de la tupla debe poner en rojo al menos un test de `tests/test_cli_errores.py`, para `gap` y para `plan`. El informe da el resultado medido, test a test.
  - Prod: —
  - Estado: hecha en 21109a944fdd166f1c898ecfa2707ade595a732b · evidencia informes/T42-dev-proyecto.md

## Ola 20 (SMC-005)

- [x] **T43** — Huecos fiables en `change_evidence`: commits truncados y checks repetidos
  - Issue: SMC-005 https://github.com/pedri77/security-manager-control/issues/17
  - Hace: en `scripts/change_evidence.py`, `collect_pr` anota un hueco si `pr["commits"]` es mayor que los commits leídos (la API corta en 250 sin error). `collect_pr` se queda con el check-run más reciente de cada par nombre y app, por `started_at` e `id`, sin fiarse del orden de la lista y sin dar por bueno un check que sigue en curso: un fallo superado por un verde no deja hueco, y un verde superado por un fallo o por un check en curso sí. En `tests/test_change_evidence.py`, añade el test con `blind-review` en `success` en la primera página y fallo de lectura en la segunda: el estado se descarta y queda hueco. Corrige la aserción de hueco que hoy no puede fallar. El test del modo PR con tope de páginas ejercita `mode_pr`, o se renombra a lo que prueba. Cumple los criterios de aceptación de la issue.
  - No hace: no toca `is_release_pr`, los workflows ni la plantilla de enjambre-agentes. No cambia el formato del registro de cambio. No regenera el evidence pack de v0.8.4. No toca versión ni CHANGELOG (los lleva release-please).
  - Toca: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, `docs/plan/informes/T43-dev-proyecto.md`
  - Depende: T38, T42
  - Verifica: `uv run --extra dev pytest -q tests/test_change_evidence.py` y `make test` en verde. Un test por criterio de la issue, con `gh` simulado. Hay test con los check-runs en los dos órdenes de lista, y con dos apps distintas que comparten nombre de check. Contraprueba en una copia temporal, con resultado medido test a test en el informe: quitar la comparación de `pr["commits"]`, quitar la selección del check-run más reciente, ordenar solo por `id` o solo por `started_at` si el test lo distingue, e ignorar la app deben poner en rojo al menos un test cada uno.
  - Prod: —
  - Estado: hecha en 946b4fedd4b61d7d1a55d99520f9e5e9753a481c · evidencia informes/T43-dev-proyecto.md

- [x] **T44** — Cerrar el FAIL de revisión ciega del PR #19
  - Issue: SMC-005 https://github.com/pedri77/security-manager-control/issues/17
  - Hace: añade en `tests/test_change_evidence.py` un test de `mode_release`, parametrizado con los dos órdenes, que comprueba en `rec["gaps"]` que un fallo superado por un verde no deja «checks no exitosos» y que un verde superado por un fallo sí lo deja; incluye el caso real de PR #11 como regresión. En `latest_check_runs` de `scripts/change_evidence.py`, dentro de cada grupo de nombre y app: si todos los runs tienen `started_at`, gana el mayor (`started_at`, `id`); si alguno no lo tiene, gana el mayor `id`. Así un fallo sin `started_at` no queda tapado por un verde anterior, y un verde antiguo sin `started_at` no tapa un fallo más nuevo.
  - No hace: no compara con `merged_at`. No cambia la clave nombre y app. No toca `is_release_pr`, los workflows ni la plantilla de enjambre-agentes. No cambia el formato del registro.
  - Toca: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, `docs/plan/informes/T44-dev-proyecto.md`
  - Depende: T43
  - Verifica: `uv run --extra dev pytest -q tests/test_change_evidence.py` y `make test` en verde. Contraprueba en copia temporal, un mutante por copia, con resultado medido test a test en el informe: `failed = []` en `mode_release`, quitar el `gaps.append` de checks no exitosos, comparar por `started_at` con centinela en vez de por `id` cuando falta `started_at`, y comparar siempre solo por `id` deben poner en rojo al menos un test cada uno. Hay test con verde sin `started_at` e id 1 frente a fallo con `started_at` e id 2, en los dos órdenes: gana el fallo.
  - Prod: —
  - Estado: hecha en 72e33a6677b5d42074e8ddc6da6892ce2cc62fbc · evidencia informes/T44-dev-proyecto.md

## Ola 21 (SMC-006)

- [x] **T45** — `estado` que no es escalar en `smc gap` y `smc plan`
  - Issue: SMC-006 https://github.com/pedri77/security-manager-control/issues/18
  - Hace: en `smc/gap.py`, un `estado` que no es texto, como `estado: []` o `estado: {}`, sigue el camino de un estado no válido: aviso `estado no válido` y cuenta como sin evaluar. `smc gap` y `smc plan` dejan de dar `TypeError: unhashable type`. Añade tests de esos dos valores en `gap` y en `plan`, y un test de que un YAML válido que no es un mapa (`42`, `- a`, `hola`, vacío) da rc=0 con su aviso en `smc gap`.
  - No hace: no toca `smc/cli.py`, `_ERRORES_DATOS`, `_load` ni `smc/compare.py`. No toca `tests/golden/`. No cambia el texto de ningún aviso. Nada de `smc report`, `smc dashboard` ni `smc verticals`.
  - Toca: `smc/gap.py`, `tests/test_cli_errores.py`, `docs/plan/informes/T45-dev-proyecto.md`
  - Depende: T42
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde y `git diff` sin cambios en `tests/golden/`. Contraprueba en una copia temporal, lanzando desde ella y con `PYTHONPATH` a esa copia, un mutante por copia: volver a `estado not in VALID_STATES` sin la comprobación de tipo debe poner en rojo tests de `gap` y de `plan`; hacer que `_load` lance `ValueError` si el resultado no es un mapa debe poner en rojo el test de YAML no mapa. El informe da cada resultado medido, test a test.
  - Prod: —
  - Estado: hecha en 5b1b59b · evidencia informes/T45-dev-proyecto.md

## Ola 22 (SMC-007)

- [x] **T46** — `change_evidence`: elección de check-run, corte en `merged_at` y reintento ante 5xx
  - Issue: SMC-007 https://github.com/pedri77/security-manager-control/issues/21
  - Hace: en `scripts/change_evidence.py`, tres cambios. (1) `latest_check_runs`, por grupo de nombre y app: elige entre los runs con `started_at` por el mayor (`started_at`, `id`); un run sin `started_at` solo sustituye a ese ganador si su `id` es mayor que el de todos los runs con fecha del grupo; sin ningún run con fecha gana el mayor `id`. (2) `collect_pr`, en un PR con `merged_at`: descarta antes de elegir los check-runs con `started_at` posterior a `merged_at` (uno con `started_at` igual a `merged_at` o sin `started_at` se queda); si un check se queda sin ningún run por ese corte, sale de `checks` y se anota un hueco que nombra el PR y el check. Sin `merged_at`, nada cambia. (3) `gh_json`: ante `CalledProcessError` con 5xx hace hasta 2 reintentos (3 intentos en total) con `time.sleep` corto; el 5xx se reconoce por el código de estado que `gh` escribe en stderr, `(HTTP 5xx)`, no por un número suelto en el mensaje. Otros errores, 403 y 404 incluidos, se propagan a la primera; agotados los reintentos se propaga el último error y el hueco se anota como hoy. En `tests/test_change_evidence.py`, un test por criterio de la issue, con `gh` simulado y `time.sleep` simulado.
  - No hace: no cambia la clave nombre y app ni el borde 251/250. No toca `latest_status`, `is_release_pr`, `mode_release` ni los workflows. No cambia el formato del registro. No regenera evidence packs. No toca la plantilla de enjambre-agentes. No toca versión ni CHANGELOG.
  - Toca: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, `docs/plan/informes/T46-dev-proyecto.md`
  - Depende: T44
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde. Hay test con el caso de la issue (id 9 `success` 20:41, id 2 `failure` 20:43, id 1 sin `started_at`: gana el `failure`) en los órdenes de lista posibles; con verde sin `started_at` frente a fallo más nuevo; con fallo sin `started_at` e `id` mayor frente a verde anterior; con PR fusionado y repetición verde posterior a `merged_at`: queda el rojo; con check solo posterior al merge: hueco; con PR sin fusionar y la misma repetición: gana la repetición; con 500 y luego éxito, con 3 veces 500 (3 llamadas y error propagado, y hueco en `collect_pr`), con 403 y 404 (1 llamada y sin `sleep`), y con un 403 cuyo mensaje contiene `HTTP 500` (1 llamada). Contraprueba en copia temporal, un mutante por copia, con resultado medido test a test en el informe: volver a la regla de T44 (si falta `started_at` en alguno, mayor `id`); dejar que un run sin fecha gane con `id` mayor que el ganador pero no que todos; ignorar del todo los runs sin fecha; quitar el corte por `merged_at`; usar `>=` en ese corte; quitar el hueco del check sin runs; quitar el reintento; reintentar cualquier `CalledProcessError`; reintentar 3 veces en vez de 2; reconocer el 5xx con `"HTTP 500" in stderr`. Cada uno debe poner en rojo al menos un test.
  - Prod: —
  - Estado: hecha en 2889c5b · evidencia informes/T46-dev-proyecto.md

- [x] **T47** — Cerrar el FAIL de revisión ciega del PR #24
  - Issue: SMC-007 https://github.com/pedri77/security-manager-control/issues/21
  - Hace: en `scripts/change_evidence.py`, `http_status` reconoce los dos formatos reales de `gh` en stderr: `gh: <mensaje> (HTTP 503)` y `gh: HTTP 503`, este último cuando el cuerpo no es JSON con `message`. Cuenta la última aparición del código, para que un 403 cuyo mensaje cita `HTTP 500` no se reintente. Corrige la docstring. En `tests/test_change_evidence.py`, añade tests de: `gh: HTTP 502` y `gh: HTTP 503` con reintento; `gh: HTTP 404` sin reintento; stderr con dos códigos, donde cuenta el último; corte en `merged_at` con fechas en otro huso (`+01:00`), donde cuenta el instante y no el texto; y dos apps con el mismo nombre de check, donde solo la que se queda sin runs por el corte deja hueco.
  - No hace: no corta por `completed_at` ni toca `latest_status`. No cambia `is_release_pr`, `latest_check_runs` ni los workflows. No cambia el formato del registro. No toca la plantilla de enjambre-agentes, versión ni CHANGELOG.
  - Toca: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, `docs/plan/informes/T47-dev-proyecto.md`
  - Depende: T46
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde. Prueba con el binario real de `gh` contra un servidor local, contando peticiones en el servidor: 500 con JSON, 502 con HTML, 503 con HTML y 504 con cuerpo vacío dan 3 peticiones cada uno; 403 y 404, con JSON y con HTML, dan 1. Resultado en el informe. Contraprueba en copia temporal, un mutante por copia, con resultado medido test a test: volver a `r"\(HTTP (\d{3})\)"`; tomar la primera aparición en vez de la última; comparar el corte como texto; `_utc` sin zona; quitar la app de la clave de runs conservados. Cada uno debe poner en rojo al menos un test.
  - Prod: —
  - Estado: hecha en 631e049 · evidencia informes/T47-dev-proyecto.md

- [x] **T48** — Reintentar el 5xx de cuerpo vacío que `gh` no identifica
  - Issue: SMC-007 https://github.com/pedri77/security-manager-control/issues/21
  - Hace: en `scripts/change_evidence.py`, `gh_json` trata también como fallo transitorio un `CalledProcessError` cuyo stderr tiene una línea que es exactamente `unexpected end of JSON input`: con cuerpo vacío y `Content-Type: application/json`, `gh` escribe solo eso, sin código de estado. Mismos 2 reintentos y misma espera que un 5xx; agotados, se propaga el error y queda el hueco. Es seguro porque `gh_json` solo hace GET. Sin código no se distingue un 5xx de otro estado: un 403 o 404 con ese mismo cuerpo también se reintenta, y se acepta. Un stderr con código `(HTTP 403)` o `gh: HTTP 404` que además cite ese texto dentro de otra línea sigue fallando a la primera. En `tests/test_change_evidence.py`, tests de esos casos, con el stderr copiado de `gh` real.
  - No hace: no pasa a `gh api -i` ni cambia cómo se invoca `gh`. No reintenta otros errores de JSON ni un `json.loads` que falle sobre salida correcta. No toca `latest_status`, `is_release_pr`, `latest_check_runs` ni los workflows. No toca la plantilla de enjambre-agentes, versión ni CHANGELOG.
  - Toca: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, `docs/plan/informes/T48-dev-proyecto.md`
  - Depende: T47
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde. Prueba con el binario real de `gh` contra un servidor local, contando peticiones en el servidor: 500, 502 y 504 con cuerpo vacío y `Content-Type: application/json` dan 3 peticiones cada uno; siguen dando 3 los casos de T47 (500 JSON, 502 HTML, 504 `text/plain`) y 1 los 403 y 404 con cuerpo no vacío. Contraprueba en copia temporal, un mutante por copia, con resultado medido test a test: quitar el reconocimiento del texto; buscarlo como subcadena en vez de línea exacta; reintentar cualquier `CalledProcessError`; no propagar al agotar. Cada uno debe poner en rojo al menos un test.
  - Prod: —
  - Estado: hecha en 39e7d37 · evidencia informes/T48-dev-proyecto.md

- [x] **T49** — Cerrar el segundo FAIL de revisión ciega del PR #24
  - Issue: SMC-007 https://github.com/pedri77/security-manager-control/issues/21
  - Hace: en `scripts/change_evidence.py`, `collect_pr` pide `commits/<sha>/check-runs?filter=all`: sin ese filtro la API solo devuelve el último run de cada check, y el corte en `merged_at` se queda sin el run que había al fusionar. En `tests/test_change_evidence.py`, el simulador de `gh` imita a la API: sin `filter=all` solo sirve el run más reciente de cada check. Con ese simulador, un rojo al fusionar y repetición verde posterior deja el rojo y ningún hueco; un verde al fusionar y repetición posterior deja el verde y ningún hueco; un check que solo corrió tras el merge deja hueco. Añade tests de: `gh: HTTP 404` seguido de `unexpected end of JSON input` en stderr (1 llamada, manda el código), y un 403 con una cita de `HTTP 500` detrás del código real (1 llamada). La docstring recoge que un 403 o 404 con cuerpo vacío y JSON se reintenta, según el criterio acotado de la issue.
  - No hace: no pasa a `gh api -i`. No corta por `completed_at` ni toca `latest_status`, `is_release_pr` ni `latest_check_runs`. No cambia `mode_release` ni el formato del registro. No toca workflows, plantilla de enjambre-agentes, versión ni CHANGELOG.
  - Toca: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, `docs/plan/informes/T49-dev-proyecto.md`
  - Depende: T48
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde. Prueba en solo lectura contra GitHub real: `scripts/change_evidence.py pr` de esta rama y de `origin/main` sobre los PR #11, #19, #20 y #22, con `GITHUB_REPOSITORY=pedri77/security-manager-control`, salida en carpeta temporal; el informe da las diferencias de `checks` y `gaps` y explica cada una. Contraprueba en copia temporal, un mutante por copia, con resultado medido test a test: quitar `filter=all`; simulador que sirva todos los runs sin mirar el filtro (el test de rojo al fusionar debe dejar de distinguir el mutante anterior, y el informe lo dice); regex `HTTP (\d{3})` suelto; dejar que un código que no es 5xx caiga a la comprobación de cuerpo vacío. Los mutantes de código deben poner en rojo al menos un test.
  - Prod: —
  - Estado: hecha en b361173 · evidencia informes/T49-dev-proyecto.md

## Ola 23 (SMC-008)

- [x] **T50** — `change_evidence`: estado HTTP real con `gh api -i` y casos límite del corte en `merged_at`
  - Issue: SMC-008 https://github.com/pedri77/security-manager-control/issues/25
  - Hace: en `scripts/change_evidence.py`. (1) `gh_json` llama a `gh api -i` y separa cabeceras y cuerpo; `http_status` lee el código de la línea de estado de la salida estándar, también en el `CalledProcessError`, en vez de stderr. Se quitan `HTTP_STATUS_RE` y `EMPTY_BODY_LINE`: reintenta si y solo si el estado es 5xx, sea cual sea el cuerpo; un 403 o 404 falla a la primera aunque el cuerpo venga vacío o truncado; sin línea de estado (fallo de red) no reintenta, como hoy. (2) El 404 de `allowed_release_files` se reconoce con `http_status`, no con `"HTTP 404" in stderr`. (3) `cut_at_merge` usa `completed_at` cuando falta `started_at`: si es posterior a `merged_at`, el run se descarta; sin ninguna de las dos fechas se queda. (4) Una fecha ilegible en el corte, `merged_at` o la del run, deja hueco que nombra el PR, y no corta ese run. (5) En `collect_pr`, un estado `blind-review` con `created_at` posterior a `merged_at` no cuenta: el registro refleja el estado al fusionar, y sin ninguno previo sale el hueco de hoy. Sin `merged_at`, nada cambia. (6) El comentario de `collect_pr` dice que sin `filter=all` llega el último run por check suite, y el simulador de `tests/test_change_evidence.py` lo imita. Los tests sustituyen los stderr simulados de T47 y T48 por salidas de `gh api -i` copiadas de `gh` real.
  - No hace: no reintenta fallos de red. No toca `latest_check_runs` (el caso de ids invertidos sigue igual), `is_release_pr` más allá del 404, los workflows ni el formato del registro. No regenera packs. No toca la plantilla de enjambre-agentes, versión ni CHANGELOG.
  - Toca: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, `docs/plan/informes/T50-dev-proyecto.md`
  - Depende: T49
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde. Prueba con el binario real de `gh` contra un servidor local, contando peticiones en el servidor, matriz de estados 500, 502, 503, 403 y 404 por cuerpos JSON con `message`, `{}`, `{"errors":[]}`, HTML, vacío `text/plain`, vacío JSON, no JSON con `Content-Type` JSON, JSON truncado y solo espacios: los 5xx dan 3 peticiones y los 403 y 404 dan 1, en todas las celdas; 200 devuelve el JSON, lista y objeto, y también el cuerpo con paginación. Prueba en solo lectura contra GitHub real: `scripts/change_evidence.py pr` de esta rama y de `origin/main` sobre los PR #10 a #24 fusionados; el informe da las diferencias de `checks`, `gaps` y `blind_review` y explica cada una; un `blind-review` real publicado tras el merge es hallazgo, no fallo de la prueba. Contraprueba en copia temporal, un mutante por copia, con resultado medido test a test: leer el estado de stderr; reintentar cualquier error; partir cabeceras por `\n\n` si `gh` usa `\r\n`, o al revés, según lo medido; ignorar `completed_at`; usar `completed_at` aunque haya `started_at`; quitar el hueco de fecha ilegible; quitar el corte de `blind-review`; cortar `blind-review` con `>=`; 404 por texto en stderr. Cada uno debe poner en rojo al menos un test.
  - Prod: —
  - Estado: hecha en 9ddc2d90e02e605243cd07dc034b3a91333d9f19 · evidencia informes/T50-dev-proyecto.md

## Ola 24 (SMC-009)

- [x] **T51** — Puerta de seguridad en PR
  - Issue: SMC-009 https://github.com/pedri77/security-manager-control/issues/28
  - Hace: en `scripts/change_evidence.py`, modo nuevo `security --pr N` y funciones que comparte con el modo `pr`. La puerta aplica si el título es de tipo `sec` o si algún fichero del PR casa con una ruta de `.github/security-paths.txt` (globs con `fnmatch`, comentarios con `#`), leído de la rama base, nunca de la cabeza; tocar ese fichero también activa la puerta; si no existe en la base, solo cuenta el tipo `sec` y se avisa en la salida. Si aplica, exige `docs/threat-model/<TASK_ID>.md` en la cabeza, sin filas con estado `abierta` ni placeholders de la plantilla, o una línea `Threat model: no aplica: <motivo>` en la descripción, fuera de comentarios HTML. Sale con código 1 si no se cumple o si no puede leer la API. El PR de release no se ve afectado. `collect_pr` añade al registro el campo `security` (`required`, `reason`, `threat_model`, `review`), con el estado `security-review` cortado en `merged_at` igual que `blind-review`; `mode_release` anota hueco si `required` y `review` no es `success`. En `.github/workflows/pr-meta.yml`, job `security-gate`, con `pull_request`, nunca `pull_request_target`, y sin interpolar datos del PR en el shell. Crea `.github/security-paths.txt` con `.github/workflows/*`, `scripts/*`, `smc/report_html.py`, `smc/dashboard.py`, `smc/visor.py` y `smc/evidencias.py`. Crea `docs/threat-model/SMC-009.md` con la plantilla: cubre los dos jobs de la issue, incluida la manipulación del PR y el permiso `issues: write`.
  - Vuelta tras revisión del coordinador: el threat model debe estar añadido o modificado en `pulls/N/files`; uno de otra tarea o ya existente sin tocar no vale. Con varios TASK_ID basta con que cada uno cumpla. Estado de amenaza en vocabulario cerrado, solo `mitigada` o `aceptada`: cualquier otro valor, también `abierta (pendiente)` o `abierto`, no pasa. Un modelo sin filas de amenaza no pasa. Una fila `aceptada` exige su aceptación firmada en la sección de aceptación de riesgos de la plantilla; la firma es de David y no la pone ningún agente. `read_file_at` escapa `ref`. Integra primero la rama base, que ya trae T52, y en `docs/threat-model/SMC-009.md` pasa las amenazas de vigilancia a `mitigada` con los nombres reales de los tests de `tests/test_vigilancia.py`, corrige la columna «Fecha» de la sección 5 y retira la fila T12. Sube la insignia de tests del README al número real, sin tocar nada más del README: cierra los 2 rojos que dejó T52.
  - No hace: no publica `security-review`. No toca la regla de rama, `vigilancia.yml`, la plantilla de enjambre-agentes, versión ni CHANGELOG. No exige `security-review` en el modo `pr`.
  - Toca: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, `.github/workflows/pr-meta.yml`, `.github/security-paths.txt`, `docs/threat-model/SMC-009.md`, `README.md`, `docs/plan/informes/T51-dev-proyecto.md`
  - Depende: T50
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde. Prueba en solo lectura contra GitHub real: `scripts/change_evidence.py security --pr` sobre los PR #24 y #26 (tocan `scripts/`: debe exigir threat model y fallar) y #23 y #22 (no deben fallar), y `pr` de esta rama frente a `origin/main` sobre #24 y #26: solo cambia el campo `security`. Medida con `gh` real: lectura de la lista desde la base y 404 del threat model. Contraprueba en copia temporal, un mutante por copia, medida test a test: leer la lista de la cabeza; no activar por tocar la lista; aceptar motivo vacío; aceptar la línea dentro de un comentario HTML; ignorar `abierta`; no eximir el PR de release; pasar si falla la API; quitar el hueco de `security-review`; contar un `security-review` posterior a `merged_at`. Cada uno debe poner en rojo al menos un test. Además: aceptar un modelo que no está en los ficheros del PR; aceptar estado fuera del vocabulario; aceptar modelo sin filas; aceptar `aceptada` sin firma; `ref` sin escapar.
  - Prod: —
  - Estado: hecha en 47fa7edeb33506760e5a6ee4aa7cbdf9aa55f9b1 · evidencia informes/T51-dev-proyecto.md

- [x] **T52** — Vigilancia diaria de dependencias
  - Issue: SMC-009 https://github.com/pedri77/security-manager-control/issues/28
  - Hace: `.github/workflows/vigilancia.yml` con `schedule` diario y `workflow_dispatch`, permisos `contents: read` e `issues: write`, actions fijadas por SHA y la misma imagen `OSV_IMAGE` de `ci.yml`, con la misma versión y digest. `scripts/vigilancia.py` lee el JSON de `osv-scanner`: código 0 sin hallazgos, 1 con hallazgos, 128 sin paquetes y otro código o JSON ilegible es error del escáner. Con hallazgos, crea la issue `[vigilancia] vulnerabilidades en dependencias` con etiqueta `security`, o comenta en la abierta si cambian, sin duplicar, y el job acaba en rojo. Sin hallazgos, cierra esa issue con un comentario si está abierta. Con error del escáner, el job acaba en rojo y no toca ninguna issue. Con 128 aplica la misma regla de `sca`: si hay manifiesto sin lockfile, rojo. Respeta `osv-scanner.toml`. La issue lista paquete, versión, identificador y si hay versión corregida.
  - No hace: no abre PR de dependencias ni actualiza nada. No toca `ci.yml`, `pr-meta.yml`, `change_evidence.py`, la plantilla de enjambre-agentes, versión ni CHANGELOG.
  - Toca: `.github/workflows/vigilancia.yml`, `scripts/vigilancia.py`, `tests/test_vigilancia.py`, `docs/plan/informes/T52-dev-proyecto.md`
  - Depende: T50
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde. Medida real, con la imagen fijada por Docker: `osv-scanner` sobre este repo, y sobre una carpeta temporal con un `requirements.txt` o lock de una versión vieja con CVE conocida; las salidas reales se copian a los fixtures de los tests, con sus códigos de salida. Comprueba además con `gh` real, solo lectura, la búsqueda de issue abierta por título. Contraprueba en copia temporal, un mutante por copia, medida test a test: tratar el código 128 como limpio; tratar JSON ilegible como limpio; no ponerse en rojo con hallazgos; crear issue sin buscar la abierta; cerrar la issue con error del escáner; no cerrarla sin hallazgos. Cada uno debe poner en rojo al menos un test. Una imagen distinta de la de `ci.yml` debe fallar un test que compare las dos.
  - Prod: —
  - Estado: hecha en 00c100303b86cf6282d19f9f6cd7376d1fc0c68d · evidencia informes/T52-dev-proyecto.md

- [x] **T53** — Cerrar el bloqueo de la auditoría de seguridad de SMC-009
  - Issue: SMC-009 https://github.com/pedri77/security-manager-control/issues/28
  - Hace: en `scripts/change_evidence.py`. (B1) La exención de release exige que también `previous_filename`, si existe, sea un fichero de versión, o rechaza los estados `renamed` y `copied`. (T11) La puerta pasa a `.github/workflows/security-gate.yml`, con job `security-gate`, evento `pull_request_target` y permisos de solo lectura, y sale de `pr-meta.yml`. El checkout es el de la rama base y nunca la cabeza del PR: no ejecuta nada del PR y solo lo lee por API. Antes de escribirlo, comprueba en la documentación oficial de GitHub si el check de un `pull_request_target` cuenta como check requerido del PR, en la cabeza. Si no cuenta, el job publica un estado de commit `security-gate` sobre el SHA de la cabeza con `statuses: write`. Dilo en el informe con la fuente. (T13 y N9) «no aplica» no vale en PR de tipo `sec` ni en los que tocan la lista de rutas, `change_evidence.py` o un workflow; el motivo tiene al menos 15 caracteres y no puede ser `<motivo>` ni otro placeholder `<...>`; al imprimir se quitan caracteres de control de nombres de fichero y textos del PR. (Issue) El modelo declara `**Issue:** #N`, como trae la plantilla, y N debe estar entre las issues que cierra el PR. (N1) Lista ausente en la base: la puerta aplica y falla en cerrado; tocar la lista activa la puerta también en ese caso. (N4) La lista añade `.github/*` en lugar de `.github/workflows/*`, más `osv-scanner.toml`, `release-please-config.json` y `docs/threat-model/*`. (N7) Una fila `mitigada` exige celdas de mitigación y de test no vacías, y `abierta` en cualquier celda o línea de tabla del modelo, fuera de comentarios, no pasa. (N8) `allowed_release_files` escapa `ref`. (N5) En el modelo y en los mensajes, «fecha de aceptación» en vez de «firma»; la firma real es el estado `security-review` que publica David. En `docs/threat-model/SMC-009.md`: T11 pasa a `mitigada` con sus tests y sale de la sección 5; T13 sigue `aceptada`, acotada a lo que queda; corrige T2, T3, T5, T14 y T17 según la auditoría; añade amenazas de B1, N1, N2, N3, N5, N6 y de quién publica los estados (las de N6 y quién publica, `aceptada` y remitidas a SMC-010 #29); explica por qué se retiró T12. Al final integra la rama base, que traerá T54, y sube la insignia de tests del README al recuento real.
  - No hace: no firma ni rellena fechas de aceptación. No toca la regla de rama, `vigilancia.py`, `vigilancia.yml`, la plantilla de enjambre-agentes, versión ni CHANGELOG. Nada de SMC-010.
  - Toca: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, `.github/workflows/security-gate.yml`, `.github/workflows/pr-meta.yml`, `.github/security-paths.txt`, `docs/threat-model/SMC-009.md`, `README.md`, `docs/plan/informes/T53-dev-proyecto.md`
  - Depende: T51
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde. Reproduce primero B1 con el arnés de la auditoría (`/private/tmp/claude-501/-Users-pedri77-Dev-Claude-proyectos-Claude/954a23bc-d0e3-4e6f-999b-858a552b0b36/scratchpad/aud/h.py`) y comprueba que deja de pasar. GitHub real, solo GET: `security --pr` sobre #24, #26, #23 y #22 con la lista inyectada, y `previous_filename` en un renombrado real. Un test comprueba que `security-gate.yml` no hace checkout de la cabeza ni usa `github.event.pull_request.head` en `ref`, y que no tiene permisos de escritura salvo `statuses: write` si hiciera falta. Contraprueba en copia temporal, un mutante por copia, medida test a test: exención sin mirar `previous_filename`; volver a `pull_request`; checkout de la cabeza; «no aplica» en PR `sec`; motivo `<motivo>`; modelo de otra issue; lista ausente que pasa; `mitigada` sin test; `abierta` sin `|` inicial que pasa; `ref` sin escapar en `allowed_release_files`. Cada uno debe poner en rojo al menos un test.
  - Prod: —
  - Estado: hecha en 9f93b33584ff6490acdab0c1c2a94922d0ded00b · evidencia informes/T53-dev-proyecto.md

- [x] **T54** — Vigilancia: adopción de la issue, contenido de terceros y concurrencia
  - Issue: SMC-009 https://github.com/pedri77/security-manager-control/issues/28
  - Hace: en `scripts/vigilancia.py`, la issue abierta solo se adopta si la creó `github-actions[bot]` y lleva la etiqueta `security`; otra con el mismo título se ignora. Los campos de `osv-scanner` (paquete, versión, identificador, versión corregida) se validan con lista blanca de caracteres y longitud; lo que no cumple se sustituye y no puede formar menciones, enlaces, imágenes, comentarios HTML ni romper la tabla. En `.github/workflows/vigilancia.yml`, `concurrency` sin cancelar la que corre y `timeout-minutes`.
  - Vuelta tras revisión del coordinador: `www.evil.com/login` pasa la lista blanca y GFM lo convierte en enlace automático; `GH-12` enlaza a una issue y `~~` tacha. Cada campo de terceros se muestra entero dentro de un código en línea, donde GFM no forma enlaces, menciones, referencias ni formato; la lista blanca sigue excluyendo la comilla invertida y `|`. El cuerpo de la issue tiene un tope por debajo del límite de GitHub (65 536 caracteres): si se pasa, recorta la lista y lo dice, y el job sigue en rojo.
  - Tercera vuelta, aprobada por David: el aviso de recorte decía que el resto estaba en el log del job y no era cierto. El workflow sube el JSON completo de `osv-scanner` como artefacto (`actions/upload-artifact`, fijada por el mismo SHA que en `pr-meta.yml`, retención 90 días), también cuando el job acaba en rojo, y el aviso de recorte remite a ese artefacto por su nombre. No se imprimen hallazgos en el log: texto de terceros en stdout podría formar comandos de workflow.
  - No hace: no toca `change_evidence.py`, la puerta, `docs/threat-model/SMC-009.md` (lo actualiza T53), el README, la plantilla de enjambre-agentes, versión ni CHANGELOG.
  - Toca: `scripts/vigilancia.py`, `tests/test_vigilancia.py`, `.github/workflows/vigilancia.yml`, `docs/plan/informes/T54-dev-proyecto.md`
  - Depende: T52
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde salvo los dos tests de la insignia del README, que cierra T53. Con `gh` real, solo GET: forma real de `author` en `gh issue list --json author,labels`. Prueba los textos de la auditoría: `@org/team`, `|`, salto de línea, imagen externa y `<!--`. Contraprueba en copia temporal, un mutante por copia, medida test a test: adoptar sin mirar autor; adoptar sin mirar etiqueta; no escapar `@`; no escapar `|`; aceptar salto de línea; quitar `concurrency`; algún campo fuera de código en línea; quitar el tope del cuerpo; subir el artefacto solo si el job acaba en verde; aviso de recorte que no nombra el artefacto. Cada uno debe poner en rojo al menos un test.
  - Prod: —
  - Estado: hecha en 05fa099829a43fc69fb12f1412f7868ac0e55d8f · evidencia informes/T54-dev-proyecto.md

- [x] **T55** — Cerrar el bloqueo de la segunda auditoría de seguridad de SMC-009
  - Issue: SMC-009 https://github.com/pedri77/security-manager-control/issues/28
  - Hace: (B2) `security-gate.yml` pasa el SHA del evento al script (`--head-sha`, por variable de entorno) y `change_evidence.py security` falla si no es la cabeza actual del PR; el estado se publica siempre sobre ese mismo SHA. El workflow lleva `concurrency` por número de PR con `cancel-in-progress: true`. (N11) El job solo corre si la base del PR es la rama por defecto del repositorio. (N12) «no aplica» no vale para ninguna ruta de `.github/security-paths.txt` salvo las de `smc/`. (N13) `docs/threat-model/SMC-009.md` dice bien de dónde sale cada cosa: workflow y script de la rama por defecto, lista y diff de la base del PR. (N14) Filas para los puntos 3, 4 y 5 de SMC-010 #29, `aceptada` con fecha vacía, o con el cálculo que muestre riesgo menor de 4; filas también para B2 y N11, `mitigada` con sus tests. (N15) `vigilancia.py` aplana los saltos de línea de los errores de `gh` antes de imprimirlos. (N16) `gh label create security` sin `--force`, y tolera que la etiqueta ya exista. Insignia del README al recuento real.
  - No hace: no rellena fechas de aceptación. No toca la regla de rama, la plantilla de enjambre-agentes, versión ni CHANGELOG. Nada más de SMC-010.
  - Toca: `scripts/change_evidence.py`, `tests/test_change_evidence.py`, `.github/workflows/security-gate.yml`, `scripts/vigilancia.py`, `tests/test_vigilancia.py`, `docs/threat-model/SMC-009.md`, `README.md`, `docs/plan/informes/T55-dev-proyecto.md`
  - Depende: T53, T54
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde. Reproduce B2 con el arnés de la auditoría (`/private/tmp/claude-501/-Users-pedri77-Dev-Claude-proyectos-Claude/954a23bc-d0e3-4e6f-999b-858a552b0b36/scratchpad/as2h/race.py`) antes del arreglo y comprueba que deja de pasar. Con `gh` real, solo GET, la forma de `head.sha` y `base.ref` del PR y el texto real de error de `gh label create` cuando la etiqueta existe, si se puede ver sin crearla; si no, dilo. Un test comprueba en `security-gate.yml` el `concurrency` con `cancel-in-progress: true`, la condición de rama por defecto y que el SHA del estado es el mismo que recibe el script. Contraprueba en copia temporal, un mutante por copia, medida test a test: no comparar el SHA del evento con la cabeza; publicar sobre otro SHA; quitar `concurrency`; `cancel-in-progress: false`; quitar la condición de rama por defecto; «no aplica» válido para `osv-scanner.toml`; no aplanar los errores de `gh`; volver a `--force`. Cada uno debe poner en rojo al menos un test.
  - Prod: —
  - Estado: hecha en a5bef6a63312ee032efd720122d6fc358dbc297b · evidencia informes/T55-dev-proyecto.md

## Libro

### Hechos
- 2026-11-03 · v0.1 importada desde `~/Downloads/security-manager-control`; 12 tests verdes con uv.
- 2026-11-03 · T01: las 73 medidas ENS llevan `categoria_minima`; 39 con `verificar: true` (rellenas de memoria, sin Anexo II a mano; incluye los 11 `refuerzos_por_categoria`). TODO de cabecera mantenido. Posible discrepancia de ID: en el RD 311/2022 `op.exp.10` = registros de actividad y `op.exp.11` = claves; el catálogo tiene `op.exp.10` = claves. Sin cambiar IDs; revisar. 22 tests.
- 2026-11-03 · T02: CSV normalizado (prefijo `ENS-`, rangos expandidos); 15 controles NIS2 con fila y todos los ENS del CSV existen. `criticidad` NIS2 es juicio inicial sin fuente normativa. 20 tests.
- 2026-11-03 · T03: `plan_accion` en plantilla y ejemplo; `smc/plan.py`. Vence = no hecha y fecha < hoy (estricto). 20 tests. Main tras fusionar T01-T03: 38 tests verdes.
- 2026-11-03 · T04: `analyse(assessment, hoy=None) -> Analisis`, `smc plan`, `--hoy`. ENS MEDIA del ejemplo: 73 = 68 aplicables + 4 no aplican + 1 evaluada no_aplica. 48 tests; contraprueba (quitar filtro ENS) = 2 en rojo.

- 2026-11-03 · T08: 78 tests; medidas ENS con `verificar: true` = 39 (37 iniciales + op.cont.2 y op.cont.3); la cifra «39» de T01 venía de un grep que contaba comentarios.
- 2026-11-03 · Pendiente humano: contrastar con el BOE el Anexo II (op.cont.2/3, mp.si.2, numeración mp.info y op.exp.10/11) y quitar `verificar`.
- 2026-11-03 · T09: 19 verticales (12 anteriores con los mismos IDs + HUNT, MDM, ENDUSER, FW, SASE, ZTNA, OSI); VRT-NET paraguas (`agrupa`). Ejemplos y plantilla con sección `verticales:`. Recursos pendientes sin URL: ZTNA, VRT-OSI, mapa 3D. 28 tests nuevos.
- 2026-11-03 · T10: evaluación de tecnologías, reglas (any-any, sin uso, caducadas a 180 d) y suscripciones (umbral 70 %, renovaciones a 90 d); 3 tecnologías ficticias nuevas. 11 tests nuevos.
- 2026-11-03 · T11: 28 protocolos (capas 2, 3, 6, 7; sin CVEs concretos) y 8 fuentes oficiales; 16 tests nuevos. URL de búsqueda NVD corregida por la sesión principal (`?keyword=…&resultType=records`) con nota de verificación con Chrome.
- 2026-11-03 · T12: 17 feeds RSS, 13 con `verificado: true` (comprobados con red por la sesión principal; CCN-CERT, ENISA, CISA KEV y NVD sin RSS, con alternativa en `nota`); ecosistema con 8 Pages, 2 repos públicos y 3 pendientes. OPML solo con feeds con `url_feed`. 9 tests.
- 2026-11-03 · T13: 8 casos de uso con `deteccion`, `playbook`, `vertical`; 7 playbooks nuevos PB-UC-002..008; `smc.mitre` (niveles 1-5, export Navigator, ATT&CK "16"). 9 tests nuevos.
- 2026-11-03 · Main tras fusionar T09-T13 (sin conflictos, en orden T09, T10, T11, T12, T13): 151 tests verdes (78 + 28 + 11 + 16 + 9 + 9).
- 2026-11-05 · T37: `collect_pr` pagina con `gh_pages` (per_page=100, tope 50 páginas que falla como hueco); `blind-review` se lee de `commits/<sha>/statuses` y cuenta el más reciente por (created_at, id). `/status` vs `/statuses` no contrastado en vivo con repetidos. Límite GitHub: 250 commits por PR. 654 tests verdes.
- 2026-11-05 · T38: `PagesLimitError` (subclase de RuntimeError) capturada con `READ_ERRORS` en checks, estados y `mode_release`: el tope es hueco, no aborta; commits y reviews siguen propagando en modo PR. Desempate por `id` con test. 665 tests; contraprueba (except sin PagesLimitError en release) = 2 en rojo.
- 2026-11-05 · T39 (SMC-004): `smc gap` y `smc plan` capturan `_ERRORES_DATOS` y dan `ERROR: <ruta>: <motivo>` rc=2; `gap -o` no crea fichero si falla. 654 tests; contraprueba (quitar la captura) = 6 de 9 tests nuevos en rojo, los 3 de evaluación válida siguen verdes. Un ValueError interno de `analyse` también sale ahora como ERROR rc=2.
- 2026-11-05 · T40 (SMC-004): `gap` y `plan` capturan también `RecursionError` (YAML con 500 `[` da rc=2 sin traceback); `_ERRORES_DATOS` intacto. Referencias `tests/golden/{gap,gap_o,plan}.md` regeneradas por el coordinador desde `0c1a5be` y idénticas (cmp). 677 tests; 5 mutantes en copia limpia, todos en rojo.
- 2026-11-05 · T41 (SMC-004): `_load` de `gap.py` convierte KeyError/IndexError/AttributeError de `yaml.safe_load` (tags explícitos rotos) en ValueError; `try` solo sobre `safe_load`. Cambia también `evidencias`, `compare` y `soa` (decisión de David). 690 tests; 4 mutantes en copia limpia, todos en rojo (4, 6, 3 y 13 tests).
- 2026-11-05 · T44 (SMC-005): `latest_check_runs` decide por grupo (nombre, app): con `started_at` en todos gana (`started_at`, `id`); si falta en alguno, el mayor `id`, sin centinela. 724 tests; 4 mutantes en copia limpia, todos en rojo (m3 centinela: 8, no 4 como decía el informe). Los 3 casos de orden dan el fallo. `dev-proyecto` 1.7 sin evals en verde: cifras del informe no avaladas.
- 2026-11-05 · T43 (SMC-005): `collect_pr` anota hueco si `pr["commits"]` supera los leídos y `latest_check_runs` deja un check-run por (nombre, app) por (started_at, id); un en curso sin `started_at` supera al verde. Aserción de hueco con `blind-review` real; test del modo PR ejercita `mode_pr`. 710 tests; 6 mutantes en copia limpia, todos en rojo (incluidos 2 sobre `mode_pr`).
- 2026-11-05 · T42 (SMC-004): `_load` convierte también `TypeError` (`a: !!timestamp {=}`); caso `tag-timestamp-mapa` en `MALAS`, 693 tests. Contraprueba en copia (quitar TypeError) = 3 en rojo: gap 2 (error_limpio, salida), plan 1 (error_limpio).
- 2026-11-05 · T45 (SMC-006): en `gap.py`, `analyse` y `_heredado` comprueban `isinstance(estado, str)` antes de `in VALID_STATES`/`in SCORES`; `estado: []`/`{}` da aviso `estado no válido` y cuenta sin evaluar, sin TypeError en gap ni plan. Test de YAML no mapa (`42`, `- a`, `hola`, vacío) con rc=0 y aviso. 735 tests; contraprueba en copias: mutante tipo = 6 rojos (gap y plan), mutante `_load` = 4 rojos.
- 2026-11-05 · T46 (SMC-007): `latest_check_runs` elige entre los fechados por (`started_at`, `id`) y un run sin fecha solo gana con `id` mayor que todos los fechados; `collect_pr` corta en `merged_at` (`>` estricto; igual o sin fecha se quedan) y anota hueco con PR y check si se queda sin runs (sin nombre de app: con dos apps homónimas es ambiguo, no falso); `gh_json` reintenta 2 veces ante `(HTTP 5xx)` en stderr. `merged_at` ilegible = sin corte. 761 tests; 10 mutantes en rojo (2, 1, 11, 4, 1, 2, 4, 6, 2, 3), lectura estricta de m3 = 15.
- 2026-11-05 · T47 (SMC-007, FAIL ciego del PR #24): `gh` 2.89.0 escribe `gh: <mensaje> (HTTP 5xx)` solo si el cuerpo es JSON con `message`; con HTML, vacío o `{}` escribe `gh: HTTP 5xx` y T46 no reintentaba. `http_status` reconoce ambas formas (la segunda anclada a línea) y cuenta la última aparición. Medido con `gh` real y servidor local: 500/502/503/504 = 3 peticiones, 403/404 = 1. Un cuerpo vacío con content-type JSON da `unexpected end of JSON input` sin código (1 petición en T47); GitHub real lo dio el 2026-11-05 en el incidente de v0.8.5 (el 5xx es inferido), cerrado en T48. Corte en `merged_at` por instante (huso) y hueco solo de la app que se queda sin runs, con test. 787 tests; mutantes 15, 3, 3, 3, 1. Pendiente fuera de alcance: `"HTTP 404" in stderr` en `collect_pr` (número suelto).
- 2026-11-05 · T48 (SMC-007): `gh_json` reintenta (2 veces, misma espera) también cuando stderr tiene una línea exactamente `unexpected end of JSON input` (cuerpo vacío con content-type JSON, sin código); con código manda el código (un 403 que cita el texto no se reintenta; sin código un 403/404 vacío sí, aceptado por ser GET). Medido con `gh` real: 500/502/504 vacíos JSON = 3 peticiones, 403 con `{"message":"unexpected end of JSON input"}` = 1 (`gh: unexpected end of JSON input (HTTP 403)`), 403/404 con cuerpo = 1, casos de T47 siguen en 3. 808 tests; mutantes 7, 4, 20, 10.
- 2026-11-05 · T49 (SMC-007, 2.º FAIL ciego del PR #24): sin `filter=all` la API de check-runs devuelve solo el último run de cada check, y el corte en `merged_at` perdía el run de antes del merge. `collect_pr` pide `check-runs?filter=all`. Medido en 431754b con merged_at 16:05:00Z: con filter=all queda `evidence` 127362747209 (16:04:27Z) sin hueco; sin filtro, hueco falso de `evidence`. e2e y evals dejan hueco legítimo (sus runs, skipped, empezaron tras el merge). El simulador de `gh` de los tests imita ahora a la API: destapó 14 tests que no valían contra la API real. Los PR #11, #19, #20 y #22 dan el mismo registro que main (no tienen repeticiones). 403/404 con cuerpo vacío JSON se reintenta (criterio acotado de la issue #21). 816 tests; mutantes 17, 1, 2 (con simulador ingenuo), 1, 1.
- 2026-11-06 · T50 (SMC-008, issue #25): `gh_json` llama a `gh api -i`; el estado HTTP sale de la línea de estado de stdout (\n tras `text=True`; cabeceras y cuerpo separados por `\n\n`) y se reintenta si y solo si es 5xx. Medido con `gh` real y servidor propio contando peticiones: 5xx = 3 y 403/404 = 1 en las 45 celdas (5 estados por 9 cuerpos). 404 de `allowed_release_files` por `http_status`. `cut_at_merge` usa `completed_at` sin `started_at`; fecha ilegible (corte, run o `created_at` del blind-review) deja hueco con el PR y no corta; un `blind-review` posterior a `merged_at` no cuenta. Frente a `origin/main`, los 9 PR fusionados (#10 a #24) dan registros idénticos. 981 tests; 9 mutantes en rojo. Fuera de alcance: `latest_check_runs` con `started_at` no texto lanza `TypeError`; sigue sin tocar el caso de ids invertidos.
- 2026-11-07 · T52 (SMC-009, issue #28): medido con Docker y la imagen fijada de `ci.yml` (v2.7.0 + digest): este repo rc 0 (124 B, `results: []`); `django==1.11.0` + `pyyaml==5.3` rc 1 (552 KB, 32 grupos con versión corregida); carpeta vacía rc 128 (stdout vacío); ruta u opción inválida rc 127. Los fixtures son esa salida recortada y están contenidos en la real. `gh issue list` por título exacto con `--limit 1000` (sin índice de búsqueda); la etiqueta `security` no existe en el repo y se crea con `gh label create --force` (solo simulado, a ver en el primer `workflow_dispatch`). 1059 passed y 2 en rojo: la insignia del README (`645 >= 678`), fuera de su «Toca»; los cierra T53. Mutantes: 7 de 7 en rojo.
- 2026-11-07 · T51 devuelta (no fusionada): `security --pr` medido con `gh` real; con la lista inyectada #24, #26 y #19 y #15 fallan y #23, #22, #16, #11 y #10 no; `pr` solo cambia `security`. Vías encontradas: un PR sensible que cita el TASK_ID de otra tarea cuyo threat model ya existe pasa (no exige que el PR lo añada o toque); un modelo vacío pasa; `abierta (pendiente)` o `abierto` pasan. Los 9 mutantes salen en rojo.
- 2026-11-07 · T51 hecha en segunda vuelta (SMC-009, issue #28): la puerta exige que `docs/threat-model/<TASK_ID>.md` esté añadido o modificado en `pulls/N/files` (salvo línea `no aplica` con motivo, que es la válvula declarada), estado en vocabulario cerrado `mitigada`/`aceptada`, al menos una fila y, para `aceptada`, fila en la sección 5 con «Aceptado por» y «Fecha» AAAA-MM-DD. `ref` y ruta se escapan en `contents` (medido: `refs%2Fheads%2Fmain` 200; `nope&ref=main` antes devolvía `main`). Con `gh` real y la lista inyectada, #24, #26, #19 y #15 fallan y #23, #22, #16, #11 y #10 no. 1269 passed; 17 mutantes en rojo. Insignia del README 690. `SMC-009.md` no pasa su propia puerta hasta que David ponga la «Fecha» de T11 y T13 (pendientes de firma, sin firmar). Límites conocidos: un modelo ajeno tocado a propósito, una «Fecha» inventada y rutas fuera de la lista (`osv-scanner.toml`, `.github/actions/*`, `.github/CODEOWNERS`, `pyproject.toml`) pasan la puerta.
- 2026-11-07 · T54 hecha en tercera vuelta (SMC-009, issue #28): la issue de vigilancia solo se adopta si la creó `app/github-actions` (`is_bot: true`; forma medida con `gh issue list` en un repo público, distinta de `github-actions[bot]` de `gh search`) y lleva la etiqueta `security`. Todo campo de `osv-scanner` que pasa la lista blanca va entero en código en línea (cubre `@`, `www.`, `GH-12`, `~~`); lo que no pasa es `(valor no válido)`; tope de 10 versiones corregidas por fila y de 60000 caracteres en el cuerpo, con aviso que nombra el artefacto `osv-vigilancia` (JSON completo, 90 días, `if: always()`). El script no imprime hallazgos. `concurrency` sin cancelar y `timeout-minutes: 15`. Primera vuelta devuelta por `www.` (autolink) y segunda por afirmar que el resto estaba en el log del job (no lo estaba). 1463 passed y 2 en rojo por la insignia del README (los cierra T53); 17 mutantes en rojo. `actionlint` no disponible: workflow no pasado por él.
- 2026-11-07 · T53 hecha (SMC-009, issue #28): B1 reproducido con el arnés de la auditoría (renombrado `scripts/change_evidence.py` a `version.txt` en rama de release daba `required: False`; ahora `True`, y `previous_filename` real medido en `astral-sh/uv#23101`). La puerta pasa a `security-gate.yml` con `pull_request_target`, checkout de la rama por defecto sin `ref`, sin ejecutar código del PR, solo `statuses: write`, y publica además un estado de commit `security-gate` en la cabeza; la documentación de GitHub confirma que `pull_request_target` es evento elegible para los checks del PR y que si un check y un estado comparten nombre deben pasar los dos, pero que `GITHUB_SHA` es el último commit de la rama por defecto: dónde queda el check se mide tras fusionar (T25). «no aplica» no vale en `sec`, lista, `change_evidence.py` ni workflows; motivo ≥15 caracteres sin placeholders; el modelo declara `**Issue:** #N` ligado a las que cierra el PR; sin lista en la base la puerta falla; `.github/*`, `osv-scanner.toml`, `release-please-config.json` y `docs/threat-model/*` en la lista; `mitigada` exige mitigación y test; `abierta` en cualquier línea de tabla no pasa; `ref` escapado también en `allowed_release_files`. 1550 passed; 10 mutantes pedidos en rojo (extra: quitar `safe_text` del motivo sobrevive, defensa en profundidad). 105 citas de tests del modelo, todas existentes. Un `<!--` sin cerrar en el modelo oculta el resto del fichero a la puerta: no permite pasar sin modelo y equivale a escribir `mitigada` a mano (límite aceptado); mejora opcional: fallar en cerrado. Pendiente de David, sin rellenar: fecha de aceptación de T13, T23, T24 y T25 (§5), alta de `security-gate` en la regla de rama y medida del check tras el primer PR posterior a la fusión. `actionlint` no disponible.
- 2026-11-07 · T55 hecha (SMC-009, issue #28): B2 reproducido con el arnés de la segunda auditoría (base: `rc 0`, `success` sobre el SHA del evento mientras se evaluó otro; T55: `rc 1`; con el SHA igual a la cabeza viva, `rc 0`). `security-gate.yml` fija `HEAD_SHA` una vez, lo pasa al script (`--head-sha`, obligatorio, comprueba al empezar y al acabar) y publica sobre ese mismo SHA con `!cancelled()`; `concurrency` por PR con `cancel-in-progress: true`; el job solo corre si la base es la rama por defecto (N11). «no aplica» no vale para ninguna ruta de la lista fuera de `smc/` (N12). Modelo con T28 a T34 y su cálculo (P×I) correcto, 129 citas de tests existentes y exactamente 7 filas `aceptada` sin fecha (T13, T23, T24, T25, T30, T31, T32), ninguna rellenada. `vigilancia.py`: errores de `gh` aplanados (N15) y `gh label create` sin `--force` tolerando que ya exista (N16). 1595 passed; los 8 mutantes pedidos en rojo (quitar solo una de las dos capas de aplanado sobrevive: defensa en profundidad). Sin medir: texto real de `gh label create` con etiqueta existente (solo en el binario `gh` 2.89.0 con `strings`; crear etiquetas está denegado en la sesión) y dónde queda el check de `pull_request_target` (T25). Corrección de la principal pendiente en la rama base: comentario de `security-paths.txt` y plantilla de PR.

### Supuestos
- La tabla del Anexo II del RD 311/2022 se puede reconstruir con fiabilidad suficiente; lo dudoso va con `verificar: true`.

### Decisiones
- 2026-11-07 · `security-gate` con `pull_request_target`, sin checkout del PR: corrige la regla «nunca `pull_request_target`» de T51, que era demasiado tajante; el riesgo de ese evento es ejecutar código del PR, y aquí no se ejecuta nada · sesión principal
- 2026-11-07 · La firma real de un riesgo aceptado es el estado `security-review` que publica David; la fecha del modelo no autentica · sesión principal
- 2026-11-07 · Sin Renovate ni PR automáticos de dependencias: `change-record` los rechazaría sin issue; la vigilancia diaria abre issue y el arreglo entra por el flujo normal · sesión principal
- 2026-11-07 · Puerta de seguridad dentro de `change_evidence.py` y no en otro script: reutiliza lectura de API y corte en `merged_at`, y la plantilla sigue siendo un fichero · sesión principal
- 2026-11-06 · `gh api -i` adoptado (SMC-008): el estado HTTP sale de la línea de estado, con cualquier cuerpo. Medido con 200 y 404 reales. Sustituye el reconocimiento por stderr de T47 y T48 y retira la excepción del 403 o 404 con cuerpo vacío · sesión principal
- 2026-11-03 · Alcance v0.2-v0.4; v0.5 fuera · sesión principal (encargo de David: ejecutar con el enjambre)
- 2026-11-03 · HTML con stdlib, sin dependencias nuevas · sesión principal
- 2026-11-03 · Prioridad = 60·estado + 20·criticidad + 10·entidad + 10·cobertura; P1 >= 70, P2 >= 40, resto P3. Estado: no_implementado 1, sin evaluar 0.75, parcial 0.5, implementado/no_aplica = 0 (P3). Categoría ENS vacía o desconocida = ALTA con aviso. T04 puede reajustar el peso de «sin evaluar» · T02/T01
- 2026-11-03 · Formato `plan_accion`: lista de {id, controles (str o lista), accion, responsable (rol), fecha_objetivo (AAAA-MM-DD), estado pendiente|en_curso|hecha|bloqueada}. Estado o fecha inválidos = aviso, no error. Una acción `hecha` no cubre una brecha aún abierta · T03
- 2026-11-03 · Brief de T04: tener en cuenta las 39 medidas `verificar` y que `render_plan_md(plan, hoy, brechas)` recibe `hoy` inyectado · coordinador
- 2026-11-03 · API de T04 que deben seguir T05/T06: `from smc.gap import analyse, Analisis, FrameworkResult, Brecha, SinEvaluar`; `analyse(assessment, hoy=None) -> Analisis` (dataclass desempaquetable como tupla `cliente, results, warnings`; campos extra: hoy, categoria_ens, plan, vencidas, p1_sin_accion, brechas_sin_accion). No reimplementar el análisis: consumir `Analisis`; `render_markdown(analisis)`; `hoy` siempre inyectado · T04
- 2026-11-03 · Aviso para T05/T06: «sin evaluar» sigue pesando 0.75 (no reajustado), así que una evaluación casi vacía llena de P1/P2 en sin evaluar (62 ENS en el ejemplo); presentarlo como esperado y separado de las brechas evaluadas (`p1_sin_accion` solo cuenta evaluadas) · T04

- 2026-11-03 · T08: prioridad 50·estado + 30·criticidad + 10·entidad + 10·cobertura, P1 >= 75, P2 >= 40 (sustituye la fórmula de T02) · revisor-ola + sesión principal
- 2026-11-03 · T08: una acción `bloqueada` o `hecha` no cubre una brecha abierta (sustituye lo registrado en T03) · sesión principal
- 2026-11-03 · Estado no válido = sin evaluar (aplicable, 0) con aviso · sesión principal

- 2026-11-03 · v0.5: enlaces solo a Pages públicas; agregador interno de noticias como consumidor del RSS sin enlazarlo; 3D desde la skill teardown con origen citado · David
- 2026-11-03 · API para T14 (ola 5) · T09-T13
  - Verticales: `from smc.verticals import cargar_verticales, validar_catalogo, evaluar, URLS_PUBLICAS`. `evaluar(assessment, estricto=True)` -> `ResultadoVerticales` (verticales, por_nis2, madurez_media, no_evaluables, sin_evaluar, warnings, errores). Entrada `verticales: {VRT-ID: {madurez 0-5|no_evaluable, motivo, producto, notas}}`; `no_evaluable` sin motivo o madurez inválida lanza `VerticalesError` (con `estricto=False` va a `errores`). `smc validate` debe sumar `validar_catalogo()`. Doble cómputo: si alguna de FW/SASE/ZTNA/OSI puntúa, VRT-NET no puntúa.
  - Tecnologías: `from smc import tech`: `evaluar_tecnologias(registry)`, `reglas(registry, hoy, dias=180)` (revisadas, sin_revisar, no_evaluables con motivo), `suscripciones(registry, hoy, dias=90, umbral=0.70)`, más `render_*`. `hoy` inyectable. Datos mal formados dan aviso. `vertical` no se valida contra el catálogo (T14 debe hacerlo).
  - Protocolos: `from smc import protocols`: `cargar`, `cargar_fuentes`, `protocolos`, `obtener(id)`, `por_capa()`, `render_protocolo(id)` (ValueError si no existe), `validar()` -> lista de errores (sumar a `smc validate`). Subcomando previsto `smc protocols [ID]`, rc!=0 en ValueError.
  - Recursos: `from smc import resources`: `cargar_rss`, `cargar_ecosistema`, `validar()` (sumar a `smc validate`), `a_opml()` (para `smc rss --opml -o`), `render_markdown()`. `render_markdown` no escapa: usar `html.escape` si va a HTML. El campo `vertical` de RSS debería validarse contra `soc/verticals.yaml`.
  - MITRE: `from smc.mitre import madurez, nivel_caso, cargar, playbook_existe, sin_playbook, playbooks_huerfanos, a_navigator`. `madurez(uc_path, hoy, root)` -> {tecnicas, tacticas, casos}. `a_navigator(...)` -> dict para `json.dumps`. `smc.soc.mitre_coverage` conserva su salida y añade tabla de madurez. `smc mitre` no cambia; el export Navigator queda para T14.
- 2026-11-03 · Avisos de ola 5 para T14/T16 · coordinador
  - El mapeo NIS2 y `controles` de las verticales nuevas (T09) y `deteccion`/`ultima_prueba` de los casos de uso (T13) son juicio inicial sobre datos de muestra, sin fuente normativa ni SOC real.
  - CVE Details no se puede verificar automáticamente (Cloudflare); EUVD y CVE Details son las URLs de búsqueda más dudosas.
  - Capa OSI de TLS (6) y BGP (7) es convención discutible; CWE y ATT&CK validados por regex, no contra el catálogo MITRE.
  - README y `soc/README.md` aún dicen «12 verticales» (fuera del «Toca» de T09-T13): lo arregla T16.

- 2026-11-03 · v0.6 propuesta (revisor olas 5-6): visor 3D que lee mapa.json; secciones de tecnologías, reglas, suscripciones y MITRE en el informe HTML y el dashboard; vertical de gobierno y riesgo (GRC) si David la quiere; evaluación ZTNA y repo de vulnerabilidades por capa OSI · sesión principal

- 2026-11-03 · Vertical GRC propia (VRT-GRC) y quitar nombres de repos privados de los informes públicos · David («si»)

- 2026-11-03 · v0.6: informe y dashboard con tecnologías/reglas/suscripciones/MITRE, visor 3D offline con three.js vendorizado, ENS contrastado con BOE · David («Hacemos el resto?»)

- 2026-11-03 · Ola 9 revisada (APTA con reservas): emparejamiento registro por stem más largo, CSP del visor con hash, refuerzos ENS tal cual la celda del BOE, MITRE del informe etiquetado como catálogo común; ATT&CK ICS T0855/T0856 renumeradas a T1692.001/.002 · sesión principal

- 2026-11-03 · v0.7: pentesting y purple team, verticales IAM/DATA/AI/OFF, RIA con fechas del Ómnibus Digital (Reglamento (UE) 2026/1744) y seguridad de agentes, PMO con horas, costes, presupuesto y eventos · David

- 2026-11-03 · T25: VRT-IDSEC/VRT-DSPM fusionadas en VRT-IAM/VRT-DATA (ya existían): 22 verticales, no 24 · coordinador
- 2026-11-03 · T28: purple `detectado` con fecha cuenta como prueba (nivel 4, 5 si ≤ 90 días) solo con `--purple`; ECO-ZTNA en estado privado sin URL ni nombre; offensive/, ai/, pmo/ reales fuera del repo · sesión principal
- 2026-11-03 · T26: excepción a «sin red» para leer el RIA y el Ómnibus (BOE/DOUE) · sesión principal
- 2026-11-03 · Olas 12-13 revisadas (APTA con reservas): T29 con hallazgos 1-6 y 9 · sesión principal

- 2026-11-03 · v0.8: CI y versiones, comparación entre evaluaciones, salida para auditor (CSV, XLSX con stdlib, HTML imprimible), evidencias con caducidad y huella, flecos v0.7 (art. 111.2 recorta capítulo III; retest fallido en HTML). Fuera: importadores, DORA completo y contraste CCN-STIC (v0.9) · David («si, prepara la v0.8»)
- 2026-11-03 · Formato de evidencia (T32, T33): `str` o `{ref: str, fecha: AAAA-MM-DD, caduca: AAAA-MM-DD | vigencia_dias: int, sha256: 64 hex opcional}`; si hay `vigencia_dias`, caduca = fecha + días. Evidencia caducada avisa y se lista, no cambia la puntuación · sesión principal

- 2026-11-03 · Ola 15 fusionada (576 tests). Notas para T35: (1) `render_ia` del HTML debe mostrar `regimen_transitorio` (T34); (2) aviso de evidencia caducada va en el Markdown de gap, no en `Analisis.warnings` (T33); (3) el CSV de `smc soa` lleva solo aplicabilidad, las evidencias van en XLSX (T32); (4) el art. 111.2 habla de «el presente Reglamento»: el recorte se limita al capítulo III por prudencia (arts. 4, 5, 50 y 72-73 se siguen emitiendo); revisar con asesoría jurídica · sesión principal

- 2026-11-03 · Olas 15-16 revisadas (APTA con reservas): T36 con hallazgos 1-9. Decisiones conservadoras: art. 111.2 con dato ausente no recorta; compare lista «dejan de evaluarse»; caducidad de evidencias en el informe HTML; Python 3.10 en la matriz de CI · sesión principal

### Atasco
- Ola 1: 0
- Ola 2: 0
- Ola 3: 0
- Ola 4: 0
- Ola 5: 0
- Ola 6: 0
- Ola 7: 0
- Ola 8: 0
- Ola 9: 0
- Ola 10: 0
- Ola 11: 0
- Ola 12: 0
- Ola 13: 0
- Ola 14: 0
- Ola 15: 0
- Ola 16: 0
- Ola 17: 0
- Ola 18: 0
- Ola 19: 0
