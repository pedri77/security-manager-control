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
| smc-v05 | coordinador | T09, T10, T11, T12, T13, T14, T15, T16 |

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

Contexto v0.5 (pedido de David el 2026-11-03): verticales Threat Hunting, EDR/XDR, MDM, puesto de usuario, perimetrales (firewall, SASE, ZTNA, protección on-prem por capas OSI); estado de las reglas de los dispositivos («no evaluable» con motivo si no se puede); evaluación de tecnologías y control de suscripciones; playbooks y madurez con MITRE; vulnerabilidades por protocolo con fuentes oficiales (NIST/NVD, ENISA, CISA KEV, cvedetails.com); listado de RSS; mapa de dispositivos 3D a partir de la skill teardown. Enlaces SOLO a páginas públicas (GitHub Pages) verificadas: EDR/XDR https://pedri77.github.io/edr-visual-app/ · SASE https://pedri77.github.io/sase-visual-app/ · Firewalls https://pedri77.github.io/Basic_Firewalls/ · Protección por capas OSI https://pedri77.github.io/Basicos_Proteccion_Capas_OSI/ · Modelo OSI https://pedri77.github.io/modelo_OSI/ · ICS/OT https://pedri77.github.io/ics-security-studio/ · WAF https://pedri77.github.io/wafforge/ · Correo https://pedri77.github.io/Basicos_email/. Repos públicos sin Pages (enlazar el repo): https://github.com/pedri77/kev_dash_project · https://github.com/pedri77/threat-intelligence-feeds. Nada de repos privados (repo-privado, repo-privado) enlazados. Proyectos pendientes de crear: evaluación de productos ZTNA, repositorio de vulnerabilidades por capa OSI, mapa 3D de dispositivos (se marcan `estado: pendiente`, sin URL).

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
  - Hace: `resources/rss.yaml` con feeds de fuentes oficiales y de referencia (INCIBE-CERT, CCN-CERT, ENISA, CISA, NIST/NVD, CERT-EU, NCSC UK, BSI, MITRE ATT&CK y fabricantes principales con avisos) con {id, nombre, organismo, url_feed, url_web, idioma, categoria: avisos|noticias|vulnerabilidades|normativa, vertical opcional, verificado: false}; `verificado: false` porque no hay red (lo comprueba un humano). Exporta OPML (`smc/resources.py: a_opml()`) para que lo ingiera el agregador interno (repo-privado usa feedparser con la URL; no se enlaza el repo privado). `resources/ecosistema.yaml`: proyectos públicos con sus Pages (lista del contexto), repos públicos sin Pages y pendientes (ZTNA, vulnerabilidades por capa OSI, mapa 3D) con `estado: pendiente`. `smc/resources.py` con carga, validación y render Markdown.
  - No hace: no consulta la red; no toca cli.py.
  - Toca: `resources/rss.yaml`, `resources/ecosistema.yaml`, `resources/README.md`, `smc/resources.py`, `tests/test_resources.py`, `docs/plan/informes/T12-dev-proyecto.md`
  - Depende: T08
  - Verifica: OPML válido (xml.etree parsea, un outline por feed); ninguna URL a repos privados (`repo-privado`, `repo-privado`); ids únicos. Contraprueba: añadir una URL de repo privado pone en rojo el test.
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

- [~] **T16** — Documentación y versión 0.5.0
  - Hace: README (mantén el estilo actual con imágenes y badges; actualiza cifras, tabla de módulos, comandos, hoja de ruta v0.5 hecha y v0.6 con lo pendiente, sección «Ecosistema» con las Pages públicas), PRD (RF nuevos), CHANGELOG 0.5.0, versión 0.5.0.
  - No hace: no regenera imágenes.
  - Toca: `README.md`, `soc/README.md`, `docs/prd/PRD-SMC-001-v1.md`, `CHANGELOG.md`, `pyproject.toml`, `smc/__init__.py`, `technologies/registry.template.yaml`, `resources/internal/inventory.template.yaml`, `docs/plan/informes/T16-dev-proyecto.md` (UPDATE 1: añadir `zona` y `capa_osi` ficticias a las plantillas para que `smc mapa` muestre zonas; corregir «12 verticales»)
  - Depende: T15
  - Verifica: todos los comandos del README rc=0 sobre los ejemplos; badges con cifras reales (tests, controles, verticales, protocolos).
  - Prod: —
  - Estado: reservada por coordinador 2026-11-03

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

- 2026-11-03 · v0.5: enlaces solo a Pages públicas; repo-privado como consumidor del RSS sin enlazarlo; 3D desde la skill teardown con origen citado · David
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

### Atasco
- Ola 1: 0
- Ola 2: 0
- Ola 3: 0
- Ola 4: 0
- Ola 5: 0
- Ola 6: 0
