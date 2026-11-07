# T56 · dev-proyecto v1.5 · Cerrar el FAIL de revisión ciega del PR #30 (SMC-009, issue #28)

Rama `t56-smc009` (sale de 61b461b). Sin push, sin PR, sin tocar main ni PLAN.md.

## Qué se hizo
- **G3**: dos tests ejecutan de verdad el `run` del paso «Publicar el estado security-gate…», leído del YAML, con `bash` sobre un fichero
  temporal (no `bash -c`), un `gh` falso al principio del `PATH` que registra los argumentos, y `HEAD_SHA`, `REPO`, `OUTCOME` por entorno.
  `OUTCOME` = `success` publica `state=success`; `failure`, `cancelled`, `skipped`, vacío, `Success` y `success ` publican `failure`
  (7 casos). Con un SHA ilegible (5 casos) el paso sale distinto de 0 y no llama a `gh`. El fragmento se deja ejecutar aislado: no se
  extrajo a script y el YAML no cambia.
- **M10**: 5 motivos no válidos (`.`, `<motivo>`, 14 `x`, `<a>`x10, 15 puntos), la plantilla del PR sin rellenar y la plantilla con
  `no aplica: <motivo>` sin rellenar, en un PR no `sec` que solo toca `smc/visor.py`, con la lista real de `.github/security-paths.txt`
  como lista de la base: todos dan problema (los motivos, con el texto «motivo no válido»). Uno válido no da problema. Los casos antiguos
  no llegaban a la rama porque usaban rutas de `scripts/` (modo estricto).
- **Usabilidad**: `NO_APLICA_RE` acepta el prefijo de casilla `- [ ] `, `- [x] `, `- [X] `, `* [ ] ` (con sangría). No valen `- [] `,
  `- [ ]Threat`, `- Threat`, ni texto delante. Dentro de comentario HTML sigue sin valer (4 casos).
- **Vigilancia**: `same_body()` en `scripts/vigilancia.py` normaliza `\r\n` y `\r` a `\n`, quita espacios y tabuladores finales por línea y
  recorta el conjunto antes de comparar. 4 variantes no comentan; un cuerpo con CRLF y hallazgos distintos sigue comentando.
- **Modelo SMC-009**: T4 y T25 citan los tests nuevos, y T4 dice que la línea puede ir como casilla. Las fechas de aceptación (sección 5,
  commit 13a2826) no se tocan. Un test nuevo comprueba que cada `tests/…::nombre` citado existe como `def`.
- **README**: insignia y árbol de 753 a 765 (recuento de `def test_` en `tests/`, que es lo que miden `test_cli_v06` y `test_cli_v07`).

## Ficheros (todos de «Toca»)
`scripts/change_evidence.py`, `scripts/vigilancia.py`, `tests/test_change_evidence.py`, `tests/test_vigilancia.py`,
`docs/threat-model/SMC-009.md`, `README.md`, este informe. `.github/workflows/security-gate.yml` no cambia.

## TDD
Antes del arreglo, 9 en rojo de 39 tests `t56`: casilla de lista (5), plantilla con la línea sin rellenar (1), vigilancia CRLF, espacios
finales y tabuladores (3). Los de G3 y M10 pasan sobre el código sin mutar, como corresponde: son tests de mutación.

## Verifica
`PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` : **1634 passed** (antes 1595; +39). 765 `def test_` (antes 753; +12).
Test de aceptación del modelo (`test_el_threat_model_de_smc_009_esta_aceptado_por_david_y_cada_mitigacion_tiene_su_test`) en verde.
Citas del modelo: 119 entradas únicas, 118 existen como test (con o sin parámetro, vía `--collect-only`); la restante es la ruta
`tests/test_vigilancia.py` (fichero, existe).

## Arnés de la revisión ciega (copia `git archive`-equivalente del árbol final, ruta `R` cambiada en una copia de mut.py)
27 mutantes: 26 ROJO, 1 VERDE. **G3_estado_siempre_success ROJO** (primer test: `test_t56_el_paso_publica_success_solo_con_outcome_success[failure-failure]`),
**M10_sin_motivo_vale ROJO** (`test_t56_motivo_no_valido_en_pr_no_sec_solo_smc_da_problema[.]`). El único verde es M3_abierta_pasa
(equivalente, previsto en el plan). Antes: G3, M10 y M3 verdes.

## Contraprueba propia (un mutante por copia limpia, solo el fichero de tests afectado)
| Mutante | Resultado |
|---|---|
| `if true` en el paso de estado (G3) | ROJO, 6 tests |
| `elif bad:` a `elif False:` (M10) | ROJO, 6 tests |
| casilla dentro de comentario HTML que vale (quitar `HTML_COMMENT_RE.sub`) | ROJO, 2 tests |
| comparación del cuerpo sin normalizar (solo `strip`) | ROJO, 3 tests |
| quitar el prefijo de casilla de la regex | ROJO, 6 tests |

## Desajustes y límites
- El plan pide la insignia «al recuento real»: se tomó `def test_` (765), no los 1634 casos de pytest, porque es lo que comprueban los
  tests del README y el badge anterior (753) seguía esa medida. Si se prefiere el recuento de pytest, esos dos tests exigen `>=` y valdría.
- La comparación del cuerpo no normaliza otros espacios (internos, Unicode) ni líneas en blanco intermedias.
- Los estados de G3 se prueban con `bash` de la máquina (`/usr/bin:/bin`); no se ejecuta en un runner real de Actions.
- No se hizo ninguna lectura con `gh` real: la tarea no la pedía.
- Acción de prod pendiente: ninguna.

---

# Revisión del coordinador (coordinador v2.4, 2026-11-07)
- Alcance: diff contra la base solo en los 7 ficheros tocados, todos de «Toca»; `superficies.py diff dev-proyecto`: OK (salida 0). Pie de `37e6487`: `Agente: dev-proyecto v1.5`, `Tarea: …#T56`, `Task: SMC-009`. gitleaks: no leaks; grep de secretos: vacío. Worktree limpio.
- Verifica (mío): `pytest -q` → **1634 passed**, sin ningún rojo; 765 `def test_` = insignia 765 (README: badge y línea del árbol).
- Arnés de la revisión ciega (`rc14m/mut.py`, copiado a `scratchpad/rev56/mut_rev.py` con `R` y `W` cambiados; `R` = `git archive 37e6487`; lanzado con `uv run --extra dev python -I`; original sin tocar): de 27 mutantes, 26 en ROJO y solo `M3_abierta_pasa` VERDE (equivalente: añade `abierta` a `THREAT_STATES` pero la comprobación de celda abierta lo sigue rechazando; `M3b_sin_check_celda` sí sale en rojo). `G3_estado_siempre_success` ROJO (`test_t56_el_paso_publica_success_solo_con_outcome_success[failure-failure]`); `M10_sin_motivo_vale` ROJO (`test_t56_motivo_no_valido_en_pr_no_sec_solo_smc_da_problema[.]`).
- G3: el test lee el `run` del paso «Publicar el estado security-gate…» del YAML, lo escribe a un script y lo ejecuta con `bash` y un `gh` falso al principio del `PATH` que registra los argumentos; el entorno es solo `PATH`, `GH_LOG`, `GH_TOKEN` falso, `REPO`, `HEAD_SHA` y `OUTCOME` (nada del PR interpolado: el `run` solo usa variables de entorno). Casos `success`→`success`; `failure`, `cancelled`, `skipped`, vacío, `Success` y `success ` → `failure`; SHA ilegible (vacío, corto, mayúsculas, 41 caracteres, no hex) → no llama a `gh` y sale con error. No hizo falta extraer a un script.
- Casilla de lista: `- [ ] `, `- [x] `, `- [X] `, `* [ ] ` y con sangría valen; `- [] `, `- [ ]Threat…`, `- Threat…` y `texto - [ ] Threat…` no; dentro de un comentario HTML (cerrado, de una línea, o sin cerrar) no vale. Comprobado a mano con `no_aplica_reason`. La plantilla del PR sin rellenar (`<motivo>`) da «motivo no válido».
- `docs/threat-model/SMC-009.md`: la §5 es idéntica byte a byte a la de `13a2826` (fechas de David 2026-11-07 en T13, T23, T24, T25, T30, T31 y T32); `threat_model_problems(modelo, [28])` devuelve `[]`: el modelo pasa su propia puerta. Solo cambian el texto de T4 y la cita de T25 (se añade el test de G3). Los tests citados existen (`test_t56_los_tests_citados_en_el_threat_model_de_smc_009_existen`).
- Contraprueba propia (copias de `git archive HEAD`, un mutante por copia, `test_change_evidence.py` y `test_vigilancia.py`, base 959): casilla dentro de comentario HTML que vale (quitar `HTML_COMMENT_RE` en `no_aplica_reason`) 2 rojos; comparar el cuerpo de la issue sin normalizar 3 rojos (`test_t56_cuerpo_igual_salvo_saltos_y_espacios_finales_no_comenta`); extras: quitar la casilla 6; G3 con `if true` 6.
