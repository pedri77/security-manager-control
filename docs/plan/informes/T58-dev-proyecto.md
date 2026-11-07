# T58 · SMC-011 · informe de dev-proyecto v1.5

Rama `t58-smc011` (sale de bf11873). Issue #33. Sin push ni PR.

## Qué se hizo
- `scripts/change_evidence.py`: `parse_security_rules` quita del inicio, tras la marca mal escrita, los `~` y cualquier espacio Unicode
  (`re.sub(r"^[~\s]+", "", rest)`, antes `lstrip("~ \t")`): `~` + NBSP o U+3000 deja `app/*` sensible y sin marca.
  Nueva `security_rule_warnings(rules)`, llamada desde `_evaluate_security` cuando la lista existe: `AVISO` (sale por stderr con los demás)
  si un glob tiene caracteres no ASCII, empieza por `./` o tiene espacios internos. No cambia la decisión (test que compara con y sin el glob).
  `～` (U+FF5E) y `˜` no son marca: quedan como glob y se avisan (decisión del coordinador).
- `tests/test_change_evidence.py`: el test de T1 ahora simula la cabeza con `~scripts/*` y la base sin marcas y exige modelo; 3 casos NBSP/U+3000/mezcla
  añadidos a la marca mal escrita; 9 tests `test_t58_*` nuevos (33 casos en total con T57): espacios Unicode, signos parecidos, avisos (6 globs),
  lista bien escrita sin avisos (incluida la real), aviso por la salida, y base `~scripts/*` con `change_evidence.py` y con otro fichero,
  base `~.github/*` con dos workflows y con otro fichero.
- `docs/threat-model/SMC-011.md` v2: T1 describe su test, T2 cita los tests de espacios Unicode, signos parecidos y avisos, T4 cita los 4 tests de la puerta propia y workflows.
- `README.md`: 784 a 793 (`def test_` real).

## Verifica
- TDD: antes de implementar fallaban 16 casos (los de aviso y espacios Unicode); los de base marcada ya pasaban (cubrían una mitigación que existía sin test).
- `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: 1685 passed; 793 `def test_`.
- `threat_model_problems(SMC-011.md, [33])` = `[]`. Los tests citados existen (`test_t57_el_threat_model_de_smc_011_pasa_la_puerta_y_sus_tests_existen`).

## Contraprueba (copias temporales fuera del worktree, una por mutante, lanzado desde la copia)
| Mutante | En rojo |
|---|---|
| volver a `lstrip("~ \t")` | 7 (3 en `test_t57_una_marca_mal_escrita...`, 4 en `test_t58_espacios_unicode...`) |
| quitar los avisos | 9 (`test_t58_otros_signos...` x2, `test_t58_globs_sospechosos...` x6, `test_t58_el_aviso_sale...`) |
| quitar lo estricto de `change_evidence.py` (base `~scripts/*`) | 1 (`test_t58_con_la_base_marcada_scripts_change_evidence_exige_modelo`) |
| quitar lo estricto de workflows (base `~.github/*`) | 2 (`test_t58_con_la_base_marcada_github_un_workflow_exige_modelo` x2) |

## Notas
- `~*` (marca todo) no da aviso: el plan no lo pedía y es legal; sigue sin librar `sec`, la lista, `change_evidence.py` ni workflows.
- Prod: ninguna.

## Corrección tras la devolución del coordinador
- Cerrado el backtick que faltaba tras `test_t57_lista_sin_ruta_marcada_no_admite_no_aplica` en la fila T4 de SMC-011.md. Revisión de backticks impares por línea: solo quedan las vallas del bloque mermaid (líneas 22 y 32), ninguna celda.
- T2 dice expresamente que `~` + NBSP o U+3000 es marca mal escrita: ruta sensible y sin exención.
