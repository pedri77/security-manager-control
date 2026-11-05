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
| smc-v05 | coordinador | T09, T10, T11, T12, T13, T14, T15, T16, T17, T18, T19, T20, T21, T22, T23, T24, T25, T26, T27, T28, T29, T30, T31, T32, T33, T34, T35, T36, T37 |

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

## Ola 18 (SMC-004, prueba real del enjambre con F2P)

- [x] **T37** — Error limpio en `smc gap` y `smc plan`
  - Issue: SMC-004 https://github.com/pedri77/security-manager-control/issues/14
  - Hace: `smc gap` y `smc plan` con fichero inexistente o YAML mal formado escriben `ERROR: <ruta>: <motivo>` en stderr y salen con rc=2, sin traceback, igual que `smc evidencias` y `smc compare`. Reutiliza `_ERRORES_DATOS` y `_error` de `smc/cli.py`. Si falla, `smc gap -o` no crea el fichero de salida.
  - No hace: no cambia el YAML válido que no es un mapa (sigue rc=0 con aviso), ni los fallos al escribir en `-o`, ni `smc report`, `smc dashboard` u otros comandos. No toca `smc/gap.py`, `smc/plan.py`, README ni CHANGELOG (lo genera release-please).
  - Toca: `smc/cli.py`, `tests/test_cli_errores.py`, `docs/plan/informes/T37-dev-proyecto.md`
  - Depende: T36
  - Verifica: `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` en verde, con un test por criterio de aceptación de la issue. Contraprueba en una copia temporal, no en el worktree: quitar la captura de errores de `gap` y de `plan` pone en rojo los tests nuevos.
  - Prod: —
  - Estado: hecha en 2877f634a68b028cad5cb174960f0f6cbf1441b8 · evidencia informes/T37-dev-proyecto.md

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
- 2026-11-05 · T37 (SMC-004): `smc gap` y `smc plan` capturan `_ERRORES_DATOS` y dan `ERROR: <ruta>: <motivo>` rc=2; `gap -o` no crea fichero si falla. 654 tests; contraprueba (quitar la captura) = 6 de 9 tests nuevos en rojo, los 3 de evaluación válida siguen verdes. Un ValueError interno de `analyse` también sale ahora como ERROR rc=2.

### Supuestos
- La tabla del Anexo II del RD 311/2022 se puede reconstruir con fiabilidad suficiente; lo dudoso va con `verificar: true`.

### Decisiones
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
