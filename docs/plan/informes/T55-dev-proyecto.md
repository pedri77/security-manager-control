# T55 · SMC-009 (issue #28) · segunda auditoría de seguridad · informe dev-proyecto v1.5

Rama `t55-smc009` (sale de 1664a9b). Sin push, sin PR, sin tocar `main`, sin tocar `PLAN.md`. Fechas de aceptación sin rellenar.

## Qué se hizo
- **B2** (`scripts/change_evidence.py`, `security-gate.yml`): `security` exige `--head-sha` (argparse `required=True`; los otros modos no lo piden). `evaluate_security(..., head_sha=)` compara el SHA del evento con la cabeza de `pulls/N` al empezar y otra vez al acabar (`HeadMovedError`); si no coincide, `mode_security` sale con 1 y `ERROR`. El workflow fija `HEAD_SHA` una vez en el `env` del job; el script lo recibe con `--head-sha "$HEAD_SHA"` y el estado se publica en `repos/$REPO/statuses/$HEAD_SHA`: el mismo. `concurrency` a nivel de workflow, grupo `security-gate-<nº de PR>`, `cancel-in-progress: true`. El paso de publicar pasa de `always()` a `${{ !cancelled() }}`.
- **N11**: `if: github.event.pull_request.base.ref == github.event.repository.default_branch` en el job. Un PR hacia otra rama no publica estado.
- **N12**: «no aplica» no vale si el PR toca (nombre actual o `previous_filename`) cualquier ruta de la lista que no empiece por `smc/` (`NO_APLICA_PREFIX`). Siguen valiendo las rutas de `smc/` de la lista.
- **N13**: `SMC-009.md` separa «rama por defecto» (workflow y script, checkout) de «base del PR» (lista, `release-please-config.json`, diff). Cambiadas 8 apariciones de «rama base» (alcance, diagrama con nodo nuevo, T1, T3, T6, T8, T11, T19); el diagrama ahora tiene `DEF` y `BASE`.
- **N14**: filas T28 (B2) y T29 (N11) `mitigada`; T30, T31, T32 (puntos 3, 4 y 5 de #29) `aceptada` con fecha vacía; extra: T33 (N15) y T34 (N16) `mitigada`. T13 reescrita para N12 con 4 tests más.
- **N15**: `vigilancia.flat()` (Cc, Cf, Zl, Zp y espacios a un espacio) en los dos `::error::` con datos externos (`except Error` y lectura del JSON). `gh()` lanza `GhError` (lleva el stderr crudo) con el texto ya aplanado.
- **N16**: `gh label create` sin `--force`, en `ensure_label()`. Si el stderr empieza por `label with name "..." already exists` (regex anclada) sigue; cualquier otro fallo corta con 2 y sin crear la issue.
- README: insignia y línea del árbol (`tests/ 645 tests`) al recuento real: 753 `def test_` (lo que cuenta el test del README), antes 731 y 645.

## Ficheros (todos de «Toca»)
`scripts/change_evidence.py`, `tests/test_change_evidence.py`, `.github/workflows/security-gate.yml`, `scripts/vigilancia.py`, `tests/test_vigilancia.py`, `docs/threat-model/SMC-009.md`, `README.md`, este informe.

## Verifica
- `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: **1595 passed** (antes 1550; +45). Sin ningún rojo, ni siquiera la insignia.
- TDD: antes de tocar código, los tests nuevos daban 26 rojos en `test_change_evidence.py` (los de `test_vigilancia.py`, 7 rojos de 13 nuevos: los de `\x1b`, `\x00`, ruta con salto y los dos de «etiqueta existe» pasaban ya, por cómo simula `gh` el fake y porque `repr` escapa el salto en el `OSError`).
- **Cambiados en tests existentes** (comportamiento nuevo de N12, no relajados): 7 casos que usaban `scripts/x.py` con «no aplica» pasan a `smc/visor.py` con lista `smc/*` (`linea_no_aplica_con_motivo_pasa`, `..._sin_distinguir_mayusculas`, `linea_tras_un_comentario_cerrado_pasa`, `modelo_sin_tocar_con_linea_no_aplica_pasa_por_la_linea`, `motivo_de_quince_o_mas_caracteres_pasa`, `recoge_la_linea_no_aplica`, `..._no_imprime_lineas_de_comando_con_el_motivo`); `_c_publica_el_estado_en_la_cabeza` espera `${{ !cancelled() }}` y `HEAD_SHA` en el `env` del job; el test del modelo fija ahora aceptadas = T13, T23, T24, T25, T30, T31, T32 con fecha vacía.
- Citas del modelo: 115 citas con `::`; todas existen (comprobado con `def` por grep y con los ids de `pytest --collect-only`). `threat_model_problems(SMC-009.md, {28})` da 7 problemas, todos «fecha de aceptación» (T13, T23, T24, T25, T30, T31, T32).

### B2 con el arnés de la auditoría (`as2h/race.py`, con `GITHUB_REPOSITORY=o/r`)
- Antes: `rc 0 -> success sobre aaaaaaa (evento); evaluado: bbbbbbb`. Reproducido.
- Después, arnés original: rc 1 (falla porque el `Namespace` no trae `head_sha`: el arnés no vale tal cual con el parámetro obligatorio).
- Después, copia del arnés con `head_sha=EVENT_SHA` (`scratchpad/race_t55.py`): rc 1, «la cabeza actual es bbbbbbbbbbbb y el evento trae aaaaaaaaaaaa». Control con `head_sha=LIVE_SHA` (`race_t55_ok.py`): rc 0 (el texto «sobre aaaaaaa» de la última línea está fijo en el arnés; ahí el estado iría sobre b).

### GitHub real, solo GET
- `gh api repos/pedri77/security-manager-control/pulls/24`: `head.sha` = `634c6d9440aacd4c1a63cb81c08a759c9e6e8c0e` (40 hex), `base.ref` = `main`, `base.repo.default_branch` = `main`; `GET repos/.../ .default_branch` = `main`. Los PR recientes (40 últimos) tienen todos base `main`.
- `github.event.repository.default_branch` no se pudo ver en un evento real (solo se mide en el primer `pull_request_target`); es un campo documentado del payload.
- Texto de `gh label create` con la etiqueta existente: no se puede ver sin crearla (es un POST; la etiqueta `security` además no existe en el repo). Medido en el binario `gh` 2.89.0 (`strings`): `label with name %q already exists; use `--force` to update its color and description`. El fake de `test_vigilancia.py` usa ese texto con la etiqueta entre comillas; el formato real de `%q` y el 422 quedan por ver en el primer `workflow_dispatch` de vigilancia.
- Punto 3 de #29 leído con `gh issue view 29` (GET).

## Contraprueba (8 mutantes, una copia en `scratchpad/mut/<mutante>/` cada uno, lanzado desde la copia con `tests/test_change_evidence.py` y `tests/test_vigilancia.py`)
| Mutante | Rojos | Tests |
|---|---|---|
| m1 no comparar el SHA con la cabeza | 7 | `test_b2_la_cabeza_del_evento_no_es_la_actual_falla`, `..._se_mueve_durante_la_evaluacion_falla`, `..._se_mueve_en_una_puerta_que_no_aplica_tambien_falla`, `test_b2_cualquier_sha_distinto_de_la_cabeza_falla[]`, `[H2]`, `[h]`, `[HH]` |
| m2 publicar sobre otro SHA (`$GITHUB_SHA`) | 2 | `test_workflow_security_gate_y_lista_de_rutas[publica_el_estado_security_gate_en_la_cabeza_siempre]`, `test_t55_workflow_security_gate[el_sha_del_estado_es_el_que_recibe_el_script]` |
| m3 quitar `concurrency` | 2 | `test_t55_workflow_security_gate[concurrency_por_numero_de_pr_con_cancel_in_progress_true]`, `[cancel_in_progress_es_true]` |
| m4 `cancel-in-progress: false` | 2 | los mismos dos |
| m5 quitar la condición de rama por defecto | 1 | `test_t55_workflow_security_gate[solo_corre_si_la_base_es_la_rama_por_defecto]` |
| m6 «no aplica» válido para `osv-scanner.toml` | 2 | `test_n12_no_aplica_no_vale_en_las_rutas_de_la_lista_fuera_de_smc[osv-scanner.toml]`, `test_n12_un_renombrado_desde_una_ruta_sensible_fuera_de_smc_tampoco_vale` |
| m7 no aplanar errores de `gh` (`flat` devuelve `str`) | 6 | `test_n15_el_stderr_de_gh_con_saltos_no_forma_lineas_de_comando`, `test_n15_cualquier_separador_o_control_se_aplana[\n]`, `[\r]`, `[\r\n]`, `[ ]`, `test_n15_flat_deja_el_texto_normal_igual` |
| m8 volver a `--force` | 1 | `test_n16_label_create_no_lleva_force` |

## Decisiones
- `--head-sha` obligatorio, sin valor por omisión: un script llamado sin él (o un workflow antiguo) falla en cerrado.
- Segunda lectura de `pulls/N` al acabar: cierra la ventana en que la cabeza cambia mientras se leen ficheros y commits (si no, el estado de A podría salir de ficheros de B). Cuesta una petición más.
- **Estado `failure` sobre un SHA que ya no es la cabeza**: no molesta. La regla de rama y el pack miran la cabeza (que tiene su propia ejecución). Solo ensucia el historial de estados de ese commit, y si luego se vuelve a empujar ese mismo SHA, el `synchronize` publica uno nuevo que lo sustituye. Aun así, con `concurrency` la ejecución vieja se cancela y `!cancelled()` evita publicarlo. Sí se publica `failure` (correcto) sobre el SHA del evento cuando la ejecución no se cancela pero la cabeza se movió.
- N11 en el workflow y no en el script: si el job no corre, no hay estado que publicar. Con la condición el check queda «skipped», que cuenta como pasado en una regla de rama: correcto para PR que no van a la rama por defecto.
- Filas de #29: se marcan `aceptada` con su fila en §5 y fecha vacía aunque el riesgo de T30 (1x2=2) y T31 (1x3=3) sea menor de 4, porque el vocabulario cerrado de la puerta solo admite `mitigada` o `aceptada` y toda `aceptada` pide fila fechada. Prob. e Impacto están en la tabla. T32 es 2x2=4. Son estimaciones mías, no medidas.

## Queda / no hecho
- Fechas de aceptación de T13, T23, T24, T25, T30, T31, T32: de David. `SMC-009.md` no pasa su propia puerta hasta entonces (ya era así).
- `.github/security-paths.txt` (comentario de la línea 4) y `.github/pull_request_template.md` siguen diciendo que «no aplica» no vale solo para sec, lista, `change_evidence.py` o workflows: están fuera de «Toca». Hay que ajustarlos en otra tarea.
- `actionlint` no disponible: el workflow no ha pasado por él. `if: ${{ !cancelled() }}`, `concurrency` a nivel de workflow con expresión y `github.event.repository.default_branch` en un `pull_request_target` solo se confirman en el primer PR tras la fusión (antes de fusionar, GitHub ejecuta la versión de `main`).
- Tras fusionar, el nombre del check no cambia; la regla de rama (`security-gate` requerido, `strict`) sigue siendo de David.
- Límite residual: entre la segunda lectura y la publicación del estado hay un hueco de milisegundos; un push ahí deja un estado sobre el SHA anterior, que ya no es cabeza y se sustituye por el nuevo `synchronize`.
