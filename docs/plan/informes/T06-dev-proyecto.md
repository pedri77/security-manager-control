# T06 — Dashboard estático multicliente (dev-proyecto v1.2)

## Qué se hizo
- `smc/dashboard.py`: `generar(dir, salida, hoy)`, `recopilar`, `semaforo`, `slugify`, `render_index`, `render_cliente`. Recorre `*.yaml` del directorio (no recursivo), genera `index.html` y `<slug>.html` por cliente reutilizando `report_html.render_html` (con enlace «Volver» y un poco de CSS extra para el semáforo). CSS en línea, sin JS, `<link>`, `<img>` ni URLs.
- Índice: cliente (enlace relativo), sector, entidad NIS2, categoría ENS, cumplimiento por marco (columnas dinámicas; «—» si el marco no está en alcance), brechas P1 evaluadas, acciones vencidas, fecha de evaluación, semáforo (texto + color) y nota con las reglas.
- CLI `smc dashboard <dir> -o <salida> [--hoy AAAA-MM-DD]`; directorio inexistente = código 2; avisos también a stderr.
- `assessments/examples/ejemplo-energia.yaml`: distribuidora ficticia, esencial, sin sector público (sin ENS), 26 evaluaciones en NIS2/transversal/red y 4 acciones (una vencida).
- `tests/test_dashboard.py`: 10 tests. Sin tocar `gap.py` ni `report_html.py`.

## Semáforo (documentado en el docstring y en el índice)
Cumplimiento = media simple de los marcos en alcance (sin evaluar puntúa como no cumplido).
Rojo: media < 50 % o alguna brecha P1 evaluada sin acción abierta. Ámbar: media < 80 %, alguna P1 evaluada o alguna acción vencida. Verde: el resto.

## Verifica
`uv run --no-project --with pytest --with pyyaml python -m pytest -q` -> 65 passed (55 + 10). `smc dashboard assessments/examples -o <tmp> --hoy 2026-11-03`: 2 clientes, 0 avisos, 3 HTML.

## Contraprueba
- Sustituir la guarda `if not _es_evaluacion(datos)` por `if False` -> `test_yaml_roto_no_rompe` en rojo (1 failed). Restaurado.
- Quitar `_e` del sector en el índice -> `test_escape_de_nombres` en rojo (1 failed). Restaurado.

## Decisiones / queda
- Slug a partir del nombre del fichero (ASCII seguro, único, nunca `index`), no del nombre del cliente: estable y sin datos del cliente en rutas.
- Un fallo inesperado en `analyse` de un cliente se informa como aviso.
- Con las reglas actuales ambos ejemplos salen en rojo (media < 50 % por los controles sin evaluar; el ayuntamiento además tiene P1 sin acción). La variedad de colores está cubierta por el test de `semaforo`. Si se quiere una demo más variada, hay que evaluar más controles en el ejemplo de energía o cambiar la regla de media.
- PLAN.md sin marcar. Sin push.
