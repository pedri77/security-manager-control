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
| smc | coordinador | T01, T02, T03, T04, T05, T06, T07 |

## Ola 1

- [~] **T01** — Aplicabilidad ENS por categoría
  - Hace: añade a cada una de las 73 medidas de `frameworks/ens/controls.yaml` el campo `categoria_minima` (BASICA | MEDIA | ALTA, la categoría más baja en la que la medida aplica según el Anexo II del RD 311/2022) y, cuando aplique, `refuerzos_por_categoria` (p. ej. `{MEDIA: [R1], ALTA: [R1, R2]}`). Donde no haya certeza, añade `verificar: true` y explícalo en el informe; quita el TODO de cabecera solo si todas quedan rellenas. Crea `smc/ens.py` con `aplica(control, categoria) -> bool` y `refuerzos(control, categoria) -> list[str]`; categoría desconocida o vacía = ALTA (conservador) con aviso.
  - No hace: no toca `smc/gap.py` ni `smc/cli.py` (lo integra T04). No cambia IDs.
  - Toca: `frameworks/ens/controls.yaml`, `smc/ens.py`, `tests/test_ens.py`, `docs/plan/informes/T01-dev-proyecto.md`
  - Depende: —
  - Verifica: `smc validate` sigue OK; tests de `aplica` para BASICA/MEDIA/ALTA con medidas reales del YAML (p. ej. una medida que solo aplica en ALTA no aplica en BASICA) y categoría vacía. Contraprueba: cambiar el orden de categorías en `ens.py` pone un test en rojo.
  - Prod: —
  - Estado: reservada por coordinador 2026-11-03

- [~] **T02** — Priorización por riesgo y mapeos completos entre marcos
  - Hace: completa `mappings/nis2-ens-iso27001.csv` para que cada control NIS2 del catálogo tenga fila (medidas ENS e ISO 27001:2022 Anexo A). Crea `smc/mapping.py` (carga el CSV; `equivalentes(control_id) -> set[str]` en ambos sentidos NIS2↔ENS) y `smc/priority.py` con `prioridad(control, estado, cliente) -> (puntuacion 0-100, nivel P1|P2|P3)` basada en: peso del estado (no_implementado > parcial), criticidad del control (campo opcional `criticidad: alta|media|baja` en los YAML, por defecto media), tipo de entidad NIS2 (esencial pesa más) y si el control cubre varias normas vía mapeo. Documenta la fórmula en el docstring.
  - No hace: no toca `smc/gap.py` ni `smc/cli.py`, ni los YAML de marcos salvo para añadir `criticidad` a controles NIS2 en `frameworks/nis2/controls.yaml`.
  - Toca: `mappings/nis2-ens-iso27001.csv`, `frameworks/nis2/controls.yaml`, `smc/mapping.py`, `smc/priority.py`, `tests/test_priority.py`, `docs/plan/informes/T02-dev-proyecto.md`
  - Depende: —
  - Verifica: test que comprueba que todo ID NIS2 del catálogo está en el CSV y que todo ID ENS del CSV existe en el catálogo ENS; tests de orden de prioridad (esencial+no_implementado+alta > importante+parcial+baja). Contraprueba: borrar una fila del CSV pone en rojo el test de cobertura.
  - Prod: —
  - Estado: reservada por coordinador 2026-11-03

- [~] **T03** — Plan de acción en la evaluación
  - Hace: añade a `assessments/assessment.template.yaml` y al ejemplo ficticio `assessments/examples/ejemplo-ayuntamiento.yaml` una sección `plan_accion:` (lista de acciones con `id`, `controles`, `accion`, `responsable`, `fecha_objetivo`, `estado: pendiente|en_curso|hecha|bloqueada`). Crea `smc/plan.py` con `cargar_plan(assessment) -> list[Accion]`, `vencidas(plan, hoy)`, `brechas_sin_accion(brechas, plan)` y `render_plan_md(...)`.
  - No hace: no toca `smc/gap.py` ni `smc/cli.py`. Sin datos reales.
  - Toca: `assessments/assessment.template.yaml`, `assessments/examples/ejemplo-ayuntamiento.yaml`, `smc/plan.py`, `tests/test_plan.py`, `docs/plan/informes/T03-dev-proyecto.md`
  - Depende: —
  - Verifica: tests con fecha fija (`hoy` inyectado) para vencidas, acciones hechas no vencen, brechas sin acción; el ejemplo carga sin errores. Contraprueba: comparar fechas con `<=` en vez de `<` cambia el resultado de un test.
  - Prod: —
  - Estado: reservada por coordinador 2026-11-03

## Ola 2

- [ ] **T04** — Integrar v0.2 en el análisis y el CLI
  - Hace: `smc/gap.py` usa `ens.aplica` con `cliente.categoria_ens` (las medidas ENS que no aplican no cuentan como aplicables ni como sin evaluar; se listan aparte), ordena brechas por `priority.prioridad`, añade columna de prioridad y refuerzos ENS al Markdown y marca como «heredado» un control sin evaluar cuyo equivalente mapeado sí esté evaluado (no puntúa, solo sugiere). El informe incluye la sección de plan de acción (`plan.render_plan_md`) y avisa de brechas P1 sin acción. CLI: `smc plan <assessment> [--hoy AAAA-MM-DD]`. Expone `analyse()` con resultado estructurado reutilizable por T05/T06 (dataclasses; sin romper la firma de `run`).
  - No hace: nada de HTML.
  - Toca: `smc/gap.py`, `smc/cli.py`, `tests/test_smc.py`, `tests/test_gap_v02.py`, `docs/plan/informes/T04-dev-proyecto.md`
  - Depende: T01, T02, T03
  - Verifica: los 12 tests originales siguen verdes; tests nuevos: ejemplo del ayuntamiento (MEDIA) excluye medidas solo-ALTA, brecha P1 sale primero, `smc plan` lista vencidas con `--hoy`. Contraprueba: forzar categoría ALTA cambia el número de aplicables ENS.
  - Prod: —

## Ola 3

- [ ] **T05** — Informe HTML autocontenido (v0.3)
  - Hace: `smc/report_html.py` genera un único HTML sin dependencias externas (CSS en línea, sin JS obligatorio) con: resumen ejecutivo para dirección (cumplimiento por marco con barras, top 10 brechas P1, acciones vencidas), detalle por marco, plan de acción y avisos. Estilos de impresión (`@media print`) para guardar como PDF desde el navegador. Escapa todo texto de la evaluación (`html.escape`). CLI: `smc report <assessment> -o informe.html`.
  - No hace: no genera PDF con librerías; no toca el dashboard.
  - Toca: `smc/report_html.py`, `smc/cli.py`, `tests/test_report_html.py`, `docs/plan/informes/T05-dev-proyecto.md`
  - Depende: T04
  - Verifica: test que genera el informe del ejemplo y comprueba secciones, ausencia de `http://`/`https://` en `<link>`/`<script>` y que una nota con `<script>` sale escapada. Contraprueba: quitar el escape pone en rojo el test de XSS.
  - Prod: —

- [ ] **T06** — Dashboard estático multicliente (v0.4)
  - Hace: `smc/dashboard.py` + CLI `smc dashboard <dir_evaluaciones> -o <dir_salida>`: recorre `*.yaml` de evaluaciones, genera `index.html` (tabla de clientes con cumplimiento por marco, nº de brechas P1, acciones vencidas, fecha de evaluación, semáforo) y una página por cliente reutilizando `report_html`. Todo estático, local, sin servidor. Añade un segundo ejemplo ficticio privado (empresa de energía, entidad esencial, no sector público) en `assessments/examples/` para que el dashboard muestre dos clientes.
  - No hace: no sirve por red ni añade autenticación; no publica nada.
  - Toca: `smc/dashboard.py`, `smc/cli.py`, `assessments/examples/ejemplo-energia.yaml`, `tests/test_dashboard.py`, `docs/plan/informes/T06-dev-proyecto.md`
  - Depende: T05
  - Verifica: test que genera el dashboard de `assessments/examples/` en un tmp y comprueba 2 filas, enlaces relativos válidos a las páginas de cliente y escape de nombres. Contraprueba: un YAML inválido en el directorio se informa como aviso y no rompe el resto.
  - Prod: —

- [ ] **T07** — Documentación y versión 0.4.0
  - Hace: actualiza `README.md` (estado v0.4, comandos nuevos, flujo), `docs/prd/PRD-SMC-001-v1.md` (roadmap: marca v0.2-v0.4 como hechas), crea `docs/adr/ADR-002-informes-html-y-dashboard-estatico.md` (por qué HTML autocontenido y dashboard estático local: soberanía, sin servidor, ADR-001), sube versión a 0.4.0 en `pyproject.toml` y `smc/__init__.py`, añade `CHANGELOG.md`.
  - No hace: no toca código de `smc/` salvo `__init__.py`.
  - Toca: `README.md`, `docs/prd/PRD-SMC-001-v1.md`, `docs/adr/ADR-002-informes-html-y-dashboard-estatico.md`, `pyproject.toml`, `smc/__init__.py`, `CHANGELOG.md`, `docs/plan/informes/T07-dev-proyecto.md`
  - Depende: T06
  - Verifica: `smc --version` da 0.4.0; todos los comandos del README se ejecutan sin error sobre los ejemplos. Contraprueba: un comando mal escrito en el README falla al ejecutarlo.
  - Prod: —

## Libro

### Hechos
- 2026-11-03 · v0.1 importada desde `~/Downloads/security-manager-control`; 12 tests verdes con uv.

### Supuestos
- La tabla del Anexo II del RD 311/2022 se puede reconstruir con fiabilidad suficiente; lo dudoso va con `verificar: true`.

### Decisiones
- 2026-11-03 · Alcance v0.2-v0.4; v0.5 fuera · sesión principal (David pidió hacerlo con el enjambre sin pedir autorización)
- 2026-11-03 · HTML con stdlib, sin dependencias nuevas · sesión principal

### Atasco
- Ola 1: 0
- Ola 2: 0
- Ola 3: 0
