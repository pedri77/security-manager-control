# T38 · dev-proyecto v1.5

Rama t38 en /Users/pedri77/Dev/wt/smc-t38. Sin push ni PR.

## Qué hice
- `scripts/change_evidence.py`: `gh_pages` lanza ahora `PagesLimitError` (subclase de `RuntimeError`) al pasar de `MAX_PAGES`. `READ_ERRORS = (CalledProcessError, PagesLimitError)` se usa en los `except` de checks, estados y `mode_release`. Nuevo `reason(e)`: stderr si lo hay, si no `str(e)`. Los mensajes de hueco ya no dependen de `e.stderr`.
- Sin cambios: `PER_PAGE`, `MAX_PAGES`, `is_release_pr` (su `except` sigue con `CalledProcessError`, porque no usa `gh_pages`), workflows, plantilla. Commits y reviews en modo PR siguen propagando el error (hay test). En `mode_release` el tope en commits o reviews cae en el `except` de `collect_pr` y queda como hueco, sin abortar.
- Tests nuevos (8 casos más parametrizados, todos en rojo antes del cambio): tope en checks y estados (hueco, mensaje "más de 3 páginas ... lectura incompleta"); página corta justo en el tope no es hueco; commits/reviews propagan en modo PR; mensaje con `stderr=None`; `mode_release` escribe `change-record.json` y `.md` con hueco para commits, reviews, check-runs y statuses; desempate por `id` con mismo `created_at` (ambos órdenes de entrada).

## Verifica
- `uv run --extra dev pytest -q tests/test_change_evidence.py`: 29 passed.
- `make test`: 665 passed.
- TDD: antes del cambio, 8 failed, 21 passed.

## Contrapruebas ejecutadas (fichero restaurado tras cada una)
- A. `gh_pages` devuelve `items` en silencio al llegar al tope: 8 failed.
- B. `READ_ERRORS` sin `PagesLimitError` (el `except` no lo captura): 6 failed.
- C. `latest_status` ordena solo por `created_at`: 1 failed (desempate).

## Decisiones
- Excepción propia en vez de capturar `RuntimeError`, para no tragarse errores ajenos.
- `commit` con pie `Co-Authored-By` según la instrucción de atribución.

## Queda
- Nada pendiente de T38. `/status` vs `/statuses` sigue sin contrastar en vivo (de T37).

## Revisión del coordinador (2026-11-05)
- Alcance: solo scripts/change_evidence.py y tests/test_change_evidence.py; superficie OK; sin secretos (gitleaks limpio).
- Verifica: `uv run --extra dev pytest -q tests/test_change_evidence.py` → 29 passed; `make test` → 665 passed.
- Tope en commits/reviews: en modo PR propaga (líneas 164-165 fuera de try, test); en mode_release cae en `except READ_ERRORS` de collect_pr (línea 335) y queda como hueco.
- Contraprueba: línea 335 `except READ_ERRORS` → `except subprocess.CalledProcessError` → 2 failed (test_release_con_tope_escribe_el_pack_con_hueco[commits] y [reviews]), 27 passed. Restaurado.
