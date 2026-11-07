# T53 · Cerrar el bloqueo de la auditoría de seguridad de SMC-009

Agente dev-proyecto v1.5 · rama `t53-smc009` (sale de 6beaab1) · issue #28 · sin push ni PR · sin fechas de aceptación.

## Qué se hizo
- **B1**: `is_release_pr` exige que `previous_filename`, si existe, sea también un fichero de versión. Reproducido antes con el arnés `h.py`: caso D, renombrado `scripts/change_evidence.py` -> `version.txt` en rama `release-please--branches--*` daba `required: False` («PR de release»). Ahora `required: True`, con la ruta de origen en el motivo. El renombrado entre dos ficheros de versión sigue siendo release.
- **T11**: nuevo `.github/workflows/security-gate.yml` (job `security-gate`, `pull_request_target`, tipos opened/edited/synchronize/reopened). Un solo checkout, sin `ref` ni `repository` (la rama por defecto), con `persist-credentials: false`; nada del PR se ejecuta. Permisos: lectura a nivel de workflow; en el job, lectura más `statuses: write`. Sale de `pr-meta.yml` (que queda sin el job y sin `pull_request_target`).
- **Estado de commit** `security-gate` sobre `github.event.pull_request.head.sha` (por variable de entorno, validado como 40 hex), siempre (`if: always()`); el paso final deja el job en rojo si la puerta falla (`continue-on-error` en el paso de la puerta).
- **T13 y N9**: «no aplica» no vale en PR `sec` ni si toca la lista, `scripts/change_evidence.py` o `.github/workflows/*` (también por `previous_filename`). El motivo exige 15 caracteres sin contar placeholders `<...>` y 8 letras o cifras (`no_aplica_invalid`). `safe_text` quita saltos de línea (a espacio) y caracteres de control/formato en todo lo que se imprime (`mode_security`, avisos de `mode_pr`, razones).
- **Issue**: `threat_model_problems(text, closes)` exige `**Issue:** #N` con N entre las issues que cierra el PR (cuerpo, sin comentarios).
- **N1**: lista ausente en la base -> la puerta aplica, motivo «falta la lista…» y problema fijo (falla en cerrado, también con modelo). Tocar la lista activa la puerta aunque falte (ya no está en un `else`).
- **N4**: `.github/security-paths.txt` con `.github/*` (en lugar de `.github/workflows/*`), `osv-scanner.toml`, `release-please-config.json`, `docs/threat-model/*`.
- **N5**: «fecha de aceptación» en mensajes y modelo (`_signed` -> `_accepted_on`).
- **N7**: tablas por `_tables`: una línea es de tabla si lleva un `|` sin escapar (con o sin inicial). `abierta`/`abierto` como celda entera en cualquier línea de tabla no pasa; dos o más columnas «Estado» no pasan; `mitigada` exige celdas de «Mitigación» y «Test…» no vacías (vacías son también `-`, `n/a`, `pendiente`…) y las columnas deben existir.
- **N8**: `allowed_release_files` escapa `ref` con `quote(safe='')`.
- **Modelo `docs/threat-model/SMC-009.md` v2**: T11 `mitigada` (sale de §5); T13 `aceptada` acotada; T2, T3, T4, T5, T6, T7, T8, T10, T17 corregidas; T14 acotada a lo que prueban sus tests; nuevas T18 (B1), T19 (N1), T20 (N5), T21 (N4), T22 (N9), T23 (N6: el pack reevalúa la puerta al publicar; aceptada, SMC-010 #29 punto 1), T24 (quién publica los estados, aceptada, SMC-010 #29), T25 (regla de rama / medición tras fusionar, aceptada); nota de por qué se retiró T12. §5: T13, T23, T24, T25 con «Fecha» vacía. Declara `**Issue:** #28`.
- README: insignia `tests-693` (recuento real de `def test_`).

## T11: documentación oficial de GitHub y decisión
Fuentes consultadas (docs.github.com):
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows : para `pull_request_target`, `GITHUB_SHA` = «Last commit on default branch» y `GITHUB_REF` = «Default branch». Corre «en el contexto de la rama por defecto del repositorio base». Un workflow `pull_request_target` solo se dispara si el fichero existe en la rama por defecto.
- https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks : «For checks created by workflow jobs to be evaluated for a pull request, the workflow run must be triggered by one of these events: push, pull_request, pull_request_review, pull_request_target, deployment, deployment_status». También: «If a check and a commit status have the same name, both must pass when that name is required».

Lectura: la documentación dice que `pull_request_target` es un evento elegible para que un check de job se evalúe en el PR, pero ese check se crea sobre `GITHUB_SHA` (la rama por defecto), y la documentación no afirma que quede asociado a la cabeza del PR. Decisión: usar ambas vías. El job `security-gate` existe (por si la asociación funciona) y además publica un estado de commit `security-gate` sobre el SHA de la cabeza (`statuses: write`, única escritura), que sí es de la cabeza con seguridad. Con el mismo nombre ambos deben pasar y coinciden, porque salen del mismo resultado. Así no depende de un comportamiento no documentado. **Esto solo se puede medir de verdad tras fusionar**: el workflow debe estar en la rama por defecto para dispararse; en el PR que lo añade no corre. A medir en el primer PR posterior: si el check queda en la cabeza o solo el estado, y qué contexto añade David a la regla de rama.

## Verifica
- `PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q`: **1354 passed** (antes de la fusión de la rama base: 1269 en 6beaab1; 1354 con T53). `tests/test_change_evidence.py`: 599 passed (era 514). `def test_` en el repositorio: 693 = insignia.
- GitHub real, solo GET, con la lista inyectada (la lista de este worktree; en `main` aún no existe): `security --pr` (vía `evaluate_security`) en pedri77/security-manager-control: #24 aplica (toca `scripts/change_evidence.py`, falta `docs/threat-model/SMC-007.md`), #26 aplica (falta `SMC-008.md`), #23 «PR de release: no le afecta la puerta», #22 no aplica. `previous_filename` real: pedri77/security-manager-control no tiene ningún renombrado en sus ~26 PR; el caso real es astral-sh/uv#23101 (`crates/uv-cache/src/lib.rs` -> `lib.c`, status `renamed`): con la lista `crates/uv-cache/src/lib.rs` la puerta aplica por el nombre antiguo.
- Arnés `h.py` tras los cambios: D `required: True`; E lista ausente tocada `required: True` con problema; F `ref=a%26ref%3Devil`; B (filas vacías, sin pipe, otra cabecera, dos Estado) ahora devuelven problemas.

## Contraprueba (10 mutantes, copia temporal fuera del worktree, lanzado desde la copia, `tests/test_change_evidence.py`)
1. exención sin `previous_filename`: 2 en rojo (`release_renombrado_desde_ruta_sensible_aplica`, `release_copiado_desde_ruta_sensible_aplica`).
2. volver a `pull_request`: 1 (`usa_pull_request_target_con_los_tipos_de_edicion`).
3. checkout de la cabeza (`ref: head.sha`): 2 (`un_solo_checkout_el_de_la_base_sin_ref_ni_repositorio`, `ningun_with_ni_ref_apunta_a_la_cabeza`).
4. «no aplica» en PR `sec`: 1 (`no_aplica_no_vale_en_tipo_sec`).
5. motivo con placeholders contados: 2 (`motivo_no_valido_3`, `motivo_no_valido_8`).
6. modelo de otra issue: 4 (`modelo_de_otra_issue_no_vale`, `pr_que_no_cierra_ninguna_issue_con_modelo_no_vale`, `issue_12_no_es_la_1`, test del modelo SMC-009).
7. lista ausente que pasa: 1 (`sin_lista_en_la_base_falla_aunque_haya_modelo`).
8. `mitigada` sin test: 3 (`mitigada_sin_test_no_pasa`, `…sin_mitigacion_ni_test…`, `…test_en_blanco…`).
9. `abierta` sin `|` inicial que pasa: 2 (`abierta_sin_pipe_inicial_no_pasa` y su variante en negrita).
10. `ref` sin escapar en `allowed_release_files`: 4 (`test_allowed_release_files_escapa_ref` con `a&ref=evil`, `x#y`, `con espacio`, `x\ny`).
Diez de diez en rojo. Los tests nuevos fallaban antes del código (100 en rojo con 499 verdes; luego 12 en rojo hasta escribir workflow y modelo).

## Desajustes y decisiones
- **N2, N3, N6**: el coordinador dio después su texto. N6 = T23 (el pack reevalúa la puerta al publicar; aceptada, SMC-010 #29). Mi interpretación previa pasó a T25 (aceptada). N2 y N3 los cierra T54: se añadirán al integrarla.
- **T14 / T54**: T54 aún no está en la rama base (la fusión solo trajo cambios de PLAN.md). T14 queda `mitigada` acotada a permisos/stdin/entorno, que sus tests prueban; el contenido de terceros de la issue no se declara mitigado hasta que T54 lo fusione. Tras T54 habrá que añadir su fila/tests y ajustar la insignia (cuenta de `def test_`).
- Los casos `no_aplica_no_vale_*` se generan desde un diccionario; el modelo cita la función completa, no cada id.
- El estado `security-review` sigue siendo la firma real (decisión del Libro); el modelo solo guarda la fecha.
- Fechas de aceptación: ninguna rellenada (T13, T23, T24 con «Fecha» vacía); la puerta devuelve exactamente 3 problemas «sin fecha de aceptación» para el modelo, comprobado por test.
- Los PR siguientes que toquen `.github/*` o `docs/threat-model/*` ahora activan la puerta (N4).

## Acción de prod pendiente
Ninguna. Tras fusionar: David añade `security-gate` a la regla de rama (contexto del estado de commit y, si aparece, del check) y rellena las fechas de T13, T23, T24 en §5.

## Ampliación: integración de T54 (eb371e4)
- `git merge --no-ff eb371e4` sin conflictos (T54 trae `vigilancia.py`, `vigilancia.yml`, `test_vigilancia.py`, informe T54 y PLAN.md).
- Modelo: T26 = N2 (adopción de la issue por un tercero) y T27 = N3 (datos de terceros en issue pública), ambas `mitigada`, con 7 y 11 tests citados de `tests/test_vigilancia.py` (nombres reales, comprobados con grep: 105 citas en el modelo, 0 inexistentes). T27 incluye el artefacto `osv-vigilancia`: contenido público de OSV en repo público, aceptado como dato público, sin fila `aceptada` nueva. T14 remite a T26 y T27.
- Insignia del README: `tests-731` (recuento real de `def test_` en `tests/`).
- Fechas de aceptación: ninguna rellenada (T13, T23, T24, T25 siguen vacías).

---

# Revisión del coordinador (coordinador v2.4, 2026-11-07)
- Alcance: diff contra la base solo en los 8 ficheros de «Toca»; `superficies.py diff dev-proyecto`: OK (salida 0). Pies de la rama: `Agente: dev-proyecto v1.5`, `Tarea: …#T53`, `Task: SMC-009`. gitleaks: no leaks; grep de secretos: vacío. Worktree limpio. README: una línea (690 a 731).
- Verifica (mío): `pytest -q` → **1550 passed**, sin fallos (tras integrar T54 en eb371e4). `tests/test_change_evidence.py`: 599 passed.
- B1 con el arnés `aud/h.py`: contra la base (`/Users/pedri77/Dev/wt/smc-009`) el caso D (renombrado `scripts/change_evidence.py` a `version.txt` en rama `release-please--branches--*`) da `required: False`, «PR de release»; contra T53 da `required: True` (toca `scripts/change_evidence.py`). También cambian: B (filas vacías, `abierta` sin `|` inicial, otra cabecera, dos «Estado») ahora devuelven problemas; E (lista ausente y tocada) `required: True` con problema; F `ref=a%26ref%3Devil`. T23, T24 y T25 aparte, la puerta reprocha solo T13, T23, T24 y T25 «aceptada sin fecha de aceptación» al modelo propio (cuatro filas, ninguna fecha rellenada); sin cerrar la issue con `closes=[12]`, 5 problemas.
- `security-gate.yml` (leído con PyYAML): evento `pull_request_target` (tipos opened, edited, synchronize, reopened); un solo checkout `actions/checkout@3d3c42e…` (mismo SHA que `ci.yml`) sin `ref` ni `repository` y con `persist-credentials: false`, es decir, la rama por defecto; ningún paso ejecuta código del PR (el único `run` con datos del PR es el script de la base, y los datos llegan por `env`); permisos a nivel de workflow `contents: read` + `pull-requests: read`; del job, más `statuses: write` (única escritura); `HEAD_SHA` validado como 40 hex; estado de commit `security-gate` con descripción fija. `pr-meta.yml` ya no tiene `pull_request_target` (solo en un comentario). `actionlint` no está instalado: no se ha pasado.
- Fuente del check frente al estado de commit (leída hoy en docs.github.com): `troubleshooting-required-status-checks` dice que para evaluar en un PR los checks de jobs el workflow debe dispararse por «push, pull_request, pull_request_review, pull_request_target, deployment, deployment_status» y que «If a check and a commit status have the same name, both must pass when that name is required»; `events-that-trigger-workflows` da para `pull_request_target` `GITHUB_SHA` = «Last commit on default branch». La conclusión del informe (el check queda en la rama por defecto y la documentación no dice que quede en la cabeza; por eso además hay estado de commit) es coherente con las dos citas. Lo que falta, a medir tras fusionar, está en T25.
- Medida real, solo GET: `security --pr` con la lista inyectada: #24 rc 1 (falta SMC-007), #26 rc 1 (falta SMC-008), #23 rc 0 (release), #22 rc 0. `previous_filename` real en `astral-sh/uv#23101`: `crates/uv-cache/src/lib.c`, `renamed`, desde `lib.rs`. `contents?ref=<SHA de la cabeza>` de un PR de repo ya borrado (cabeza sin `repo`) responde 200 en el repo base: la lectura por SHA funciona con cabezas de fork.
- Citas del modelo: 105 citas `tests/…::test_…`, 42 pares únicos; todas definen una función existente (grep de `def`).
- Contraprueba (copias de `git archive HEAD`, un mutante por copia, `tests/test_change_evidence.py`, base 599 passed): m1 exención sin `previous_filename` 2; m2 `pull_request` 1; m3 checkout de la cabeza 2; m4 «no aplica» en `sec` 1; m5 motivo `<motivo>` 2; m6 modelo de otra issue 4; m7 lista ausente que pasa 1; m8 `mitigada` sin test 3; m9 `abierta` sin `|` inicial 2; m10 `ref` sin escapar 4; extra x2 tocar la lista no activa 4. Extra x1 (quitar `safe_text` del motivo) **sobrevive**: es defensa en profundidad, porque lo que se imprime pasa otra vez por `safe_text` en `mode_security`.
- `<!--` sin cerrar dentro del modelo (juicio del coordinador): `HTML_COMMENT_RE` se come el resto del fichero. Comprobado: un modelo con una fila `mitigada` válida y, tras un `<!--` sin cerrar, una fila `abierta` o una `aceptada` sin fecha pasa con `problems=[]`. No lo tomo por fallo: lo oculto es lo que tampoco ve la vista renderizada de GitHub, y quien quiera colar algo puede escribir `mitigada` con celdas rellenas sin más (límite ya aceptado: la puerta es un suelo, no juzga calidad); no permite pasar sin modelo, porque la fila válida anterior hace falta. En la vista en crudo del diff el revisor sí lo ve. Mejora barata y opcional, no exigida por T53: que `threat_model_problems` falle si queda `<!--` sin `-->` tras quitar comentarios.
