# T19 - Tecnologías, reglas, suscripciones y MITRE en informe y dashboard

Agente: dev-proyecto · Rama `t19-v06` · Tarea: docs/plan/PLAN.md#T19

## Qué se hizo
- `smc/report_html.py`: secciones «Tecnologías evaluadas», «Estado de las reglas» (any-any destacado en `alerta` con independencia de la revisión, sin revisar, no evaluables con motivo, revisadas), «Suscripciones» (vencen en 90 días, uso bajo 70 %, sobredespliegue, coste por proveedor y total por moneda) y «Madurez MITRE ATT&CK» (por táctica y casos sin playbook). Todo cálculo viene de `smc.tech` y `smc.mitre`. `render_body/render_html/run_html` aceptan `registry` (ruta o dict); MITRE se añade siempre. Helpers reutilizables: `es_registry`, `cargar_registry` (ValueError si no es registro), `datos_mitre`, `render_mitre`. Números por `_n()`: no numérico, NaN o inf salen como «—» y nunca rompen. Todo por `_e`; los enlaces del cuerpo siguen siendo solo `https://`.
- `smc/gap.py` (solo render Markdown): `render_v06_md(registry, hoy)`; `render_markdown(..., registry=None)` y `run(path, hoy, registry=None)`. MITRE siempre; las otras tres con registry. Texto libre por `md_texto`.
- `smc/cli.py`: solo `smc report ... --registry <registry.yaml>`. Registro ilegible, inexistente o sin lista `technologies` -> rc=2 con `ERROR: --registry ...` en stderr y sin escribir el fichero.
- `smc/dashboard.py`: los registros del directorio (mapa con lista `technologies`) ya no son avisos. Se asocian a una evaluación por nombre: `<stem>.<algo>.yaml`, `<stem>-<algo>.yaml` o `<stem>_<algo>.yaml` (p. ej. `ejemplo-energia.registry.yaml`). Columnas nuevas en el índice: «Reglas no evaluables», «Reglas any-any», «Suscripciones que vencen» («—» sin registro). La página del cliente suma las 3 secciones. Página común `mitre.html` (siempre se genera, enlazada desde el índice). Registros sin evaluación asociada se listan en una nota del índice. `mitre` pasa a ser slug reservado (como `index`).
- `tests/test_report_v06.py`: 22 casos (HTML con/sin registry, CLI, rc=2, XSS, coste no numérico x7, any-any, https, `hoy`, MITRE, Markdown, dashboard).

## Verifica
- `uv run --no-project --with pytest --with pyyaml python -m pytest -q` -> 244 passed (222 previos + 22 nuevos).
- `smc report ejemplo-energia.yaml -o x.html --registry technologies/registry.template.yaml --hoy 2026-11-03` rc=0; h2: Resumen, Detalle, Verticales, Tecnologías evaluadas (5), Estado de las reglas, Suscripciones, Madurez MITRE, Plan. Sin `--registry` rc=0 y solo MITRE. `smc dashboard assessments/examples -o ...` rc=0 (2 clientes, 0 avisos; genera `mitre.html`). `smc validate` OK. `smc gap` incluye la sección MITRE.
- gitleaks `--staged` sin fugas. Solo datos ficticios (plantilla y ejemplos).

## Contrapruebas (hechas de verdad)
- `_e` sin `html.escape`: rojo `test_motivo_con_script_escapado` y `test_dashboard_registro_con_xss_escapado`. Restaurado.
- `_n` sin guarda de tipo/finitud: rojo `test_coste_no_numerico_no_rompe[nan]`, `[inf]` y `test_registry_dict_y_mal_formado` (TypeError). Restaurado.

## Decisiones
- Un `coste_anual` no numérico lo avisa `smc.tech` (se suma 0) y el informe lo muestra en Avisos; el total nunca incluye NaN/inf.
- Asociación registro-evaluación por nombre de fichero (no hay campo cliente en la plantilla de registro).
- Fuera del «Toca», justificado: `tests/test_dashboard.py` línea 51: `test_dashboard_dos_filas_y_enlaces` contaba todos los `.html` del índice (2); ahora excluye `mitre.html`, que es común y no un cliente. Mismo caso que T14 con los tests de https.
- `smc gap` no recibe flag `--registry` (el «Toca» de cli solo permite flags de report/dashboard); la API Markdown está lista.

## Para T22
- Nuevo flag: `smc report <evaluacion.yaml> -o salida.html [--registry <registry.yaml>] [--hoy AAAA-MM-DD]`.
- `smc dashboard <dir> -o <salida> [--hoy ...]` sin flags nuevos: detecta registros en el directorio por forma (`technologies: [...]`) y nombre `<evaluación>.<algo>.yaml`.
- Si T22 quiere `smc gap --registry`: `gap.run(path, hoy, registry=ruta)` ya existe.
