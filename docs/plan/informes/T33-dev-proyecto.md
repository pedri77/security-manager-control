# T33 — Evidencias con fecha, caducidad y huella

Rama t33. Tests: `uv run --extra dev pytest -q` -> 534 passed.

## Qué se hizo
- `smc/evidencias.py` (nuevo): `normalizar`, `estado` (vigente, caduca_pronto <= 30 días, caducada, sin_fecha), `todas_caducadas`, `verificar_huellas(assessment, base)`, `sha256_fichero`, `render_markdown`.
- `smc/gap.py`: `FrameworkResult.evidencia_caducada` (implementados con todas sus evidencias caducadas), sección «Evidencia caducada» con aviso en el Markdown. La puntuación no cambia (test que lo comprueba contra el mismo ejemplo con texto plano).
- Plantilla con ejemplo dict comentado; `ejemplo-energia.yaml` con dos evidencias dict (NIS2-21.2.a caducada por `vigencia_dias`, NIS2-21.2.f vigente con `caduca`).
- `tests/test_evidencias.py`: 7 tests.

## Seguridad de `verificar_huellas`
Rechaza (resultado `rechazada`, aviso «no se lee») rutas absolutas (`/`, `\`, `~`, unidad `C:`), con `..`, vacías o con NUL; luego `Path.resolve()` y `is_relative_to(base resuelta)`, lo que rechaza symlinks que salen de base (un symlink que queda dentro sí se admite). Lectura en bloques de 64 KiB. Solo se lee si hay `sha256` declarado. Contraprueba en test: `../../etc/passwd`, ruta absoluta, enlace a fichero fuera y a directorio fuera.

## Consumidores de `evidencias`
grep: solo `smc/gap.py` lee `ev.get("evidencias")` (truthiness, válido con dicts). `report_html.py` usa `r.sin_evidencia` (controles), no el contenido; `ai_act.py` tiene otro campo `evidencia` sin relación. No se tocó ningún fichero fuera de «Toca».

## Decisiones / desviaciones
- El aviso de caducada va en el Markdown (bloque «Aviso»), no en `analysis.warnings`, para no alterar la lista de avisos que otros tests/CLI asumen. Si se prefiere en `warnings`, es una línea.
- «Caducada» a nivel de control exige que todas sus evidencias lo estén; el texto plano (sin_fecha) nunca caduca, así que una mezcla no se lista.
- `caduca` explícita manda sobre `vigencia_dias`. Un `caduca` igual a hoy cuenta como caduca_pronto.
- El ejemplo con `vigencia_dias` caducada depende de la fecha real si se ejecuta sin `hoy`; los tests inyectan `hoy`.
- `render_markdown` del módulo es independiente del de `gap`; no está conectado a la CLI (fuera de alcance, lo integra T35).

## Lo que queda
Integración CLI/HTML (T35). No marcada como hecha.
