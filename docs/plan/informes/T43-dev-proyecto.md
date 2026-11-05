# T43 (SMC-005): huecos fiables en change_evidence

Agente: dev-proyecto v1.6. Rama `t43-smc005`. Sin push, `PLAN.md` intacto.

## Qué se hizo
- `scripts/change_evidence.py`:
  - `collect_pr`: si `pr["commits"]` es entero y mayor que los commits leídos, hueco `PR #n: commits truncados por la API (leídos X de Y totales)`. Sin `pr["commits"]`, ni hueco ni error.
  - `latest_check_runs` (nueva): un check-run por (nombre, `app.id`), el de mayor (`started_at`, `id`), sin fiarse del orden. `app` ausente o nula no rompe (clave `None`). Un run sin concluir y sin `started_at` se tiene por el más reciente, para no dar por bueno un verde anterior. Un check en curso mantiene `conclusion` nula y su `status` entra como conclusión (no exitoso), como antes. Formato de `checks` sin cambios (`name`, `conclusion`, orden por nombre).
- `tests/test_change_evidence.py`:
  - Aserción de hueco que no podía fallar: ahora la primera página lleva `blind-review` en `success`, fallo en la segunda (y en el test del tope). Con esto el estado parcial se detecta (M8).
  - El test del modo PR con tope ejercita `mode_pr` (y comprueba que no se escribe el registro).
  - 12 tests nuevos: commits truncados/completos/sin total, dos órdenes de lista (fallo superado por verde, verde superado por fallo, verde superado por en curso), `started_at` sobre `id`, desempate por `id`, dos apps con mismo nombre, sin `app`, formato de `checks`, en curso sin `started_at` (x2 órdenes). `_conclusiones` devuelve lista para que un duplicado no se esconda.

## Verifica
- `uv run --extra dev pytest -q tests/test_change_evidence.py`: `46 passed`.
- `make test`: `710 passed in 47.55s`.
- Test primero: con el script sin el arreglo (git stash del script) fallaron 10 tests (commits truncados, 2+2+2 de órdenes, started_at, desempate id, sin app). Medido antes de añadir el test de en curso sin `started_at`.

## Contraprueba (copia temporal en el scratchpad, un mutante cada vez, resultado de pytest completo)
| Mutante | Resultado |
|---|---|
| M1 quitar comparación de commits | 1 en rojo: `test_commits_truncados_dejan_hueco_con_leidos_y_totales` |
| M2 quitar selección del más reciente | 9 en rojo: fallo_superado_por_verde (2), verde_superado_por_fallo (2), verde_superado_por_en_curso (2), started_at_manda_sobre_id, id_desempata, sin_app |
| M3 ordenar solo por id | 1 en rojo: `test_started_at_manda_sobre_id` |
| M4 ordenar solo por started_at | 1 en rojo: `test_id_desempata_con_mismo_started_at` |
| M5 ignorar la app | 1 en rojo: `test_dos_apps_con_el_mismo_nombre_cuentan_por_separado` |
| M6 fiarse del orden de la lista (último/primero gana) | 4 en rojo: fallo_superado[nuevo_primero], verde_superado_por_fallo[nuevo_primero], verde_superado_por_en_curso[nuevo_primero], id_desempata |
| M7 quitar la regla de en curso sin `started_at` | 2 en rojo: `test_check_en_curso_sin_started_at_supera_al_verde` (ambos órdenes) |
| M8 estado parcial tras fallo de página (aserción de hueco) | 2 en rojo: `test_fallo_en_pagina_posterior_queda_como_hueco[estados-statuses]`, `test_tope_de_paginas_en_checks_y_estados_es_hueco[estados-statuses]` |

Criterio de la issue 3 (nombre/ejercicio de `mode_pr`): no medido con mutante; el test ahora llama a `mode_pr`.

## Barrido de entradas malas (`latest_check_runs`)
Entradas: `[{}]` -> KeyError; `[None]` -> TypeError; `app` como str -> AttributeError; `started_at` int mezclado con `id` str -> sin excepción en un caso aislado. Un check-run sin `name` ya rompía antes (`c["name"]`); la API de GitHub siempre lo envía. Fuera de alcance, no se cambia. Tipos mixtos de `id` (str/int) darían TypeError al comparar; la API da enteros.

## Desvíos y notas
- Ninguno respecto al plan. Pie `Co-Authored-By` según el brief (Claude Opus 5.5), aunque el recordatorio del entorno indica Sonnet 5.5.
- Un check cuyo fallo posterior aparece sin `started_at` se ordena como más antiguo si ya concluyó; la API lo rellena siempre en runs concluidos.
- Queda: `gaps` por checks no exitosos en `mode_release` no se ha tocado; el hueco falso de PR #11 en v0.8.4 desaparece al regenerar (fuera de alcance).

## Revisión del coordinador (2026-11-05, v2.3)
- `uv run --extra dev pytest -q tests/test_change_evidence.py`: 46 passed. `make test`: 710 passed.
- Contraprueba en copias limpias (scratchpad, un mutante por copia, `git archive` + PYTHONPATH):
  - M1 quitar comparación de commits → 1 rojo (test_commits_truncados_dejan_hueco_con_leidos_y_totales).
  - M2 sin selección del más reciente → 11 rojos.
  - M3 ordenar solo por id → 1 rojo (test_started_at_manda_sobre_id).
  - M5 ignorar la app → 1 rojo (test_dos_apps_con_el_mismo_nombre_cuentan_por_separado).
  - M9 `mode_pr` traga PagesLimitError → 2 rojos (test_tope_en_commits_y_reviews_sigue_propagando_en_modo_pr[commits|reviews]).
  - M10 `mode_pr` escribe el registro antes de recolectar → 2 rojos (mismo test).
- Criterio 3 de la issue medido: el test ejercita `mode_pr` (M9 y M10 en rojo).
