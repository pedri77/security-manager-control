# T57 · SMC-011 · informe de dev-proyecto v1.5

Rama `t57-smc011` (sale de 0069ef7). Issue #33. Sin push, sin PR, sin tocar PLAN.md.

## Qué se hizo
- `scripts/change_evidence.py`: eliminado `NO_APLICA_PREFIX`. Nuevo `parse_security_rules(text) -> list[(glob, marcada)]`;
  `parse_security_paths` pasa a devolver los globs sin la marca (misma firma). En `_evaluate_security`, `strict` ya no mira un prefijo:
  una ruta sensible tocada (nombre actual u origen de un renombrado, ambos están en `touched`) admite «no aplica» solo si casa con una
  regla marcada y con ninguna sin marcar. La lista se sigue leyendo de la base. `grep -n 'smc/' scripts/change_evidence.py` vacío.
- Marca mal escrita (`~ ruta`, `~~ruta`, `~<tab>ruta`): no marca; la ruta queda sensible sin exención (falla en cerrado). `~` solo se ignora.
- `.github/security-paths.txt`: `~` en las cuatro rutas de `smc/`; comentario sin nombrar `smc/`. Plantilla del PR igual.
- `docs/threat-model/SMC-011.md`: 6 amenazas (T1 a T6), todas `mitigada` con test; sin aceptaciones de riesgo (sección 5 sin filas), así que no hay fecha pendiente para David.
- `README.md`: insignia y árbol de 765 a 784 (recuento real de `def test_` en `tests/*.py`).
- `tests/test_change_evidence.py`: 7 literales `lista="smc/*` pasan a `lista="~smc/*` (sin la marca ya serían estrictos) y 19 tests nuevos `test_t57_*` (con parametrizados: 27 casos).

## Decisión a revisar
El enunciado dice «casan con rutas marcadas». He elegido la lectura que falla en cerrado: si una ruta casa con una regla marcada y también
con una sin marcar, NO admite «no aplica» (test `test_t57_una_ruta_que_casa_con_una_marcada_y_otra_sin_marcar_no_vale`). En la lista real no hay solapes, así que no cambia SMC.

## Verifica
- TDD: antes de implementar, `-k t57` daba 12 failed, 15 passed (los 15 verdes son casos que ya fallaban en cerrado o eran de la lista vieja).
- `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: 1661 passed. `def test_` en `tests/*.py`: 784 (antes 765).
- `threat_model_problems(texto_SMC-011, [33])` devuelve `[]`; los tests citados en el modelo existen (test `test_t57_el_threat_model_de_smc_011_pasa_la_puerta_y_sus_tests_existen`, que busca cada `def`).
- GitHub real, solo GET: `security --pr N --head-sha <head>` con el código de `origin/main` (f61209d) y con el nuevo, salida idéntica (md5 igual):
  #30 (cabeza 4bed2e1f) rc=0, aplica y pasa; #24 (cabeza 634c6d94) rc=1, falta `docs/threat-model/SMC-007.md`. La lista de la base de GitHub aún no lleva `~`, y aun así coinciden (ambos PR son estrictos).

## Contraprueba (mutantes en copias temporales fuera del worktree, uno por copia, lanzando desde la copia; `tests/test_change_evidence.py -k "t57 or n12 or t55 or t56"`)
| Mutante | Tests en rojo |
|---|---|
| 1 todas admiten (strict sin rutas de la lista) | 23 (9 n12 por ruta, 2 n12 renombrado/mixto, 3 sin marca, mixto marcada/sin marcar, solape, renombrado, cabeza, 4 marca mal escrita, lista real fuera de smc) |
| 2 ninguna admite | 21 (4 n12 smc, 9 t56, 4 smc real, `una_ruta_marcada_admite_no_aplica` y otros) |
| 3 leer la marca (la lista) de la cabeza | 38 (incluye `test_t57_marcar_una_ruta_en_la_cabeza_no_libra_la_marca_se_lee_de_la_base`) |
| 4 «no aplica» con una ruta marcada y otra sin marcar (basta una marcada) | 15 (incluye `una_ruta_marcada_y_otra_sin_marcar_no_valen`, `el_origen_de_un_renombrado_tambien_cuenta`) |
| 5 «no aplica» en `sec` con todo marcado | 1 (`test_t57_en_un_pr_sec_no_aplica_no_vale_aunque_todo_este_marcado`) |
| 6 `~` como parte del glob | 38 (parse y todas las rutas de smc real) |
Los seis ponen en rojo al menos un test.

## Queda
- Tras fusionar: la lista de la base debe ganar las marcas `~` (ya vienen en esta rama); hasta entonces el PR de esta rama se evalúa contra la lista sin marcas, estricta, y exige el modelo, que lleva.
- Sincronizar la plantilla de enjambre-agentes (fuera de alcance). Sin versión ni CHANGELOG. Prod: ninguna.
