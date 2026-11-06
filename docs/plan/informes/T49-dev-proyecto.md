# T49 (SMC-007, issue #21): filter=all en check-runs

Agente: dev-proyecto 1.5 (versión en disco de la definición del agente; el commit decía 1.7 por suposición y lo corrigió el coordinador). Rama `t49-smc007` desde 68aa580.

## Qué se hizo
- `scripts/change_evidence.py`: `collect_pr` pide `commits/<sha>/check-runs?filter=all` (`gh_pages` añade `&per_page=100&page=N`). Sin ese filtro la API da solo el último run de cada (check, app) y el corte en `merged_at` se quedaba sin el run que había al fusionar. Docstring de `is_transient`: un 403/404 con cuerpo vacío y JSON se reintenta (criterio acotado de la issue).
- `tests/test_change_evidence.py`: el simulador `FakeGh` imita a la API (`_ultimos`): sin `filter=all` sirve un run por (nombre, app id), el de mayor (`started_at`, `id`); con `filter=all`, todos. `todo=True` conserva el comportamiento ingenuo anterior solo para la contraprueba. `FakeGh.paths` registra las rutas pedidas.
- Tests nuevos (8): `test_simulador_sin_filter_all_sirve_solo_el_ultimo_run`, `test_collect_pr_pide_check_runs_con_filter_all_en_cada_pagina`, `test_pr_fusionado_rojo_al_fusionar_y_repeticion_verde_deja_el_rojo_sin_hueco`, `test_pr_fusionado_verde_al_fusionar_y_repeticion_posterior_deja_el_verde_sin_hueco`, `test_pr_fusionado_check_que_solo_corrio_tras_el_merge_deja_hueco_con_simulador_fiel`, `test_simulador_ingenuo_no_distingue_el_filtro`, `test_404_seguido_de_cuerpo_vacio_falla_a_la_primera`, `test_403_que_cita_http_500_tras_el_codigo_real_falla_a_la_primera`.

## Hallazgo: el simulador fiel destapó 14 tests existentes
Antes de tocar el código, con solo el simulador cambiado: 14 failed, 794 passed (808 tests). Esos 14 usaban runs repetidos con el simulador ingenuo y no habrían funcionado contra la API real: `test_check_solo_en_segunda_pagina_de_check_runs`, `test_check_en_curso_sin_started_at_supera_al_verde` (2), `test_fallo_concluido_sin_started_at_supera_al_verde` (2), `test_verde_sin_started_at_con_id_mayor_supera_al_fallo_anterior` (2), `test_release_fallo_sin_started_at_tras_verde_deja_hueco` (2), `test_pr_fusionado_la_repeticion_verde_posterior_no_sustituye_al_rojo` (2), `test_run_sin_started_at_se_queda_en_pr_fusionado`, `test_corte_con_merged_at_en_otro_huso_cuenta_el_instante`, `test_dos_apps_homonimas_ambas_con_runs_previos_no_dejan_hueco`. Con el simulador y los tests nuevos, antes del arreglo: 17 failed (esos 14 + 3 nuevos: ruta con filter, rojo al fusionar, verde al fusionar). Después: 816 passed.

Ojo: los 4 casos de `latest_check_runs` (orden por started_at/id) no se tocaron; solo cambió lo que sirve el simulador.

## Verifica
`PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -q` -> 816 passed (808 + 8).

## Contraprueba (copias en /private/tmp/claude-501/mut49, un mutante por copia, lanzando desde la copia, `tests/test_change_evidence.py`, 141 tests)
- m1 quitar `filter=all`: 17 failed, los 14 de arriba + `test_collect_pr_pide_check_runs_con_filter_all_en_cada_pagina` + los 2 de rojo/verde al fusionar.
- m2 simulador que sirve todo sin mirar el filtro (`todo=True` por defecto), código correcto: 1 failed (`test_simulador_sin_filter_all_sirve_solo_el_ultimo_run`).
- m1+m2 juntos (sin filtro y simulador ingenuo): 2 failed (`test_simulador_sin_filter_all_sirve_solo_el_ultimo_run` y `test_collect_pr_pide_check_runs_con_filter_all_en_cada_pagina`). Los tests de rojo/verde al fusionar quedan en verde: no distinguen el mutante m1. Por eso el test de ruta es necesario.
- m3 regex `HTTP (\d{3})` suelto: 1 failed (`test_403_que_cita_http_500_tras_el_codigo_real_falla_a_la_primera`).
- m4 un código no 5xx cae a la comprobación de cuerpo vacío: 1 failed (`test_404_seguido_de_cuerpo_vacio_falla_a_la_primera`).
En copia sin `.git`, la suite completa da además 4 fallos ajenos (`test_gitignore_de_datos_de_cliente` x3 y `test_h3_gitignore_ignora_html_y_dashboard`) porque necesitan `git check-ignore`; por eso los mutantes se miden sobre el fichero de T49.

## Prueba contra GitHub real (solo GET)
`scripts/change_evidence.py pr --pr N` con `GITHUB_REPOSITORY=pedri77/security-manager-control`, de esta rama y de `origin/main` (8d04cfe), salida en `/private/tmp/claude-501/real49`. rc=0 en los 8. Registros completos idénticos salvo `generated_at`; diff de `checks` y `gaps`: vacío en los cuatro.

| PR | merged_at | runs en head (sin filtro / filter=all) | checks | gaps |
|---|---|---|---|---|
| #11 | 2026-11-04T20:45:39Z | 15 / 15 | 13 | [] |
| #19 | 2026-11-05T15:40:43Z | 13 / 13 | 13 | [] |
| #20 | 2026-11-05T16:03:59Z | 13 / 13 | 13 | [] |
| #22 | 2026-11-05T19:29:43Z | 13 / 13 | 13 | [] |

Explicación: en el commit head de estos PR la API sin filtro ya devuelve todos los runs (ninguno tiene repeticiones del mismo check y app; los 2 nombres repetidos de #11 son de apps distintas). El job `evidence` no figura en el head (0 en los cuatro). Por tanto estos PR no ejercitan el arreglo: la diferencia no aparece. El fallo medido (431754b: 13 runs y 1 `evidence` sin filtro; 15 y 2 con `filter=all`) lo reproduje con GET: `total_count` 13 vs 15, y `filter=all&per_page=5&page=2` da 5 elementos con `total_count` 15.

## Paginación y PR sin fusionar
- `filter=all` no cambia la paginación: `gh_pages` añade `&per_page&page` tras el `?filter=all`; `total_count` y la página corta de cierre son coherentes (medido en 431754b). Con más runs el tope es el mismo (50 páginas de 100, hueco).
- PR sin fusionar: no hay corte; `latest_check_runs` ya elige un run por (nombre, app) por (started_at, id). Con `filter=all` recibe más runs pero el resultado es el mismo que hoy (test `test_pr_sin_fusionar_la_misma_repeticion_gana` en verde). Medido en real: los PR probados están todos fusionados; para uno sin fusionar no hay medida real, solo el test.

## Dónde la especificación no encaja
1. El «403 con una cita de `HTTP 500` detrás del código real (1 llamada)» no puede ser una cita entre paréntesis: `http_status` cuenta la última aparición `(HTTP nnn)` por contrato de T47 (`test_dos_codigos_el_ultimo_5xx_se_reintenta_aunque_el_primero_sea_404`). El test usa una cita sin paréntesis («el mensaje cita HTTP 500 de otro intento») y falla con el regex suelto. Una segunda línea `(HTTP 500)` tras un 403 se seguirá reintentando.
2. La prueba real de los cuatro PR no distingue rama de main (ver arriba).

## Queda
Nada pendiente en alcance. Fuera de alcance: `"HTTP 404" in stderr` suelto en `collect_pr`/`allowed_release_files`. Sin push ni PR.

## Revisión del coordinador (2026-11-05)
- Alcance: solo los 3 ficheros de «Toca»; superficies.py diff dev-proyecto OK; gitleaks sin hallazgos. Pie del commit corregido de v1.7 a v1.5 (versión en disco de dev-proyecto) con amend en la rama de tarea antes de fusionar: SHA nuevo 2e9a60c (antes d006d5a); el informe también.
- Verifica: pytest completo 816 passed.
- Contraprueba (copias limpias con git archive, un mutante por copia, 141 tests): Contraprueba: m1 quitar filter=all → 17 rojos; m2 simulador ingenuo → 1; m1+m2 → 2; m3 regex suelto → 1; m4 no 5xx cae a cuerpo vacío → 1 (coincide con el agente). Copias en /private/tmp/claude-501/-Users-pedri77-Dev-Claude-proyectos-Claude/954a23bc-d0e3-4e6f-999b-858a552b0b36/scratchpad/t49/.
- Comparación real en solo lectura (GET), rama contra origin/main 8d04cfe, PR #11, #19, #20 y #22, rc=0: registros idénticos salvo generated_at; 13 checks y gaps [] en los cuatro. No ejercitan el arreglo (sin repeticiones).
- Medida sobre 431754b (script `/private/tmp/claude-501/-Users-pedri77-Dev-Claude-proyectos-Claude/954a23bc-d0e3-4e6f-999b-858a552b0b36/scratchpad/t49/real.py`, código de la rama, merged_at = 2026-11-05T16:05:00Z): con filter=all 15 runs; evidence tiene 127363451389 (16:06:24Z) y 127362747209 (16:04:27Z); tras `cut_at_merge` y `latest_check_runs` queda 127362747209 (16:04), sin hueco de evidence. Hay hueco de e2e y evals porque sus únicos runs (skipped) empezaron a las 16:05:12Z y 16:05:20Z, tras el merge: hueco legítimo. Sin filter=all: 13 runs, solo 127363451389 (16:06), tras el corte evidence desaparece y sale hueco falso de evidence (además de e2e y evals).
- 403 con segunda línea `(HTTP 500)`: `gh api` escribe un error por invocación, una línea `gh: <mensaje> (HTTP nnn)` o `gh: HTTP nnn`; no se observó ningún caso real con segunda línea con código. Se acepta.
