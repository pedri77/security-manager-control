# T36 · Endurecer v0.8 (v0.8.1)

Rama `t36`. 635 tests verdes (595 antes, 40 nuevos). Comandos del README rc=0 con salidas en directorio temporal. Los scripts `adv1.py`..`adv4.py` del revisor se reprodujeron a mano: ya no fallan y los escenarios están como tests en `tests/test_t36.py` y `tests/test_t34.py`.

## Hallazgo 1 · art. 111.2 (decisión a)
- Arreglo (`smc/ai_act.py`): `validar_inventario` rechaza `cambios_significativos` y `autoridad_publica` que no sean bool y un `en_mercado_desde` que no sea fecha (un datetime se reduce a su día). `obligaciones` solo recorta con `cambios_significativos: false` declarado; ausente o inválido = «no consta»: no recorta y avisa una vez por sistema. AIA-070 con dato ausente lleva nota «No consta…». Plantilla (`cambios_significativos: false` explícito en IA-001, comentario nuevo) y nota pública de AIA-070 sin «Desde T34» ni «criterio del plan».
- Tests: `tests/test_t34.py` (`test_sin_campo_cambios_significativos_no_recorta_y_avisa`, `test_t36_h1_*` con "sí", "true", 1, mapa, lista, etc.), `tests/test_t29.py`. Los tests antiguos que daban por hecho el recorte con dato ausente ahora declaran `False`.
- Contraprueba: con `"sí"` el sistema pasa de 0 a 7 obligaciones emitidas (antes recortaba 5 sin aviso); `True/False` y ausente validan sin errores.

## Hallazgo 2 · soa con fechas con hora y vigencia enorme (b)
- Arreglo: `smc/soa.py` usa `smc.evidencias.normalizar` y `estado`; los avisos de cada evidencia pasan a `avisos` de la declaración. `cli._comando_v08` captura además `TypeError` y `OverflowError` (rc=2, sin traceback).
- Tests: `test_h2_*`. Contraprueba: vigencia normal calcula la caducidad; un YAML que no es mapa sigue dando rc=2.

## Hallazgo 3 · XLSX mal formado (c)
- Arreglo: `_CONTROL_XML` pasa de lista negra de controles a «todo lo que no sea #x9 #xA #xD #x20-#xD7FF #xE000-#xFFFD #x10000+», con lo que salen `U+FFFE`, `U+FFFF`, surrogates sueltos y controles.
- Test: `test_h3_*` parsea todos los XML del zip. Contraprueba: Ñ, emoji, CJK, tab y salto de línea se conservan.

## Hallazgo 4 · dos lógicas de caducidad (b)
- Arreglo: borrada la copia de `soa.py`. `smc/evidencias.py::_fecha` exige `AAAA-MM-DD` por regex (antes `date.fromisoformat` aceptaba `20260101` y `2026-W01-1` en 3.11+ pero no en 3.10: el resultado dependía de la versión). `vigencia_dias: -1` da aviso y `sin_fecha` en los dos sitios.
- Test: `test_h4_soa_y_evidencias_coinciden_en_el_estado_de_cada_caso` (8 casos, incluido el del revisor). Contraprueba: `caduca` bien formada sí caduca.

## Hallazgo 5 · compare (d)
- Arreglo (`smc/compare.py`): solo se clasifican controles aplicables en las dos evaluaciones (catálogo de los marcos en alcance menos `no_aplican` de `analyse`); grupo nuevo `dejan_de_evaluarse` (presente antes, ausente ahora; antes salían como «sin cambio» o «empeoran») en Markdown y HTML; `sin_catalogo` y aviso para IDs inexistentes. Cada control evaluado cae en un solo grupo.
- Test: `test_h5_*` (brecha quitada, `NOEXISTE-1`, `ENS-op.cont.2`, cambio de categoría a BASICA, partición completa). Se actualizó `test_contraprueba_intercambio...` (NET-ACC-01 pasa de «empeora» a «dejan de evaluarse»).
- Contraprueba: una brecha real nueva sigue en `nuevas_brechas`.

## Hallazgo 6 · `--anterior` no mapa (e)
- Arreglo: `run_html` lanza `ValueError` si el YAML no es mapa; el CLI lo traduce a rc=2.
- Test: `test_h6_*` con lista, texto y fichero vacío (no se crea el HTML). Contraprueba: el par válido da rc=0 con la sección.

## Hallazgo 7 · CI (f)
- Arreglo: `.github/workflows/tests.yml` ejecuta `compare`, `soa` (csv, xlsx, html), `evidencias` y `report --anterior` en `$RUNNER_TEMP`; matriz 3.10, 3.11, 3.12.
- Test: `test_version.py::test_t36_workflow_ejecuta_los_comandos_de_v08` y `test_h7_*`. Contraprueba: quitar un comando o la 3.10 lo pone en rojo.

## Hallazgo 8 · CSV (g)
- Arreglo: `_seguro` prefija si el primer carácter es tab, CR o salto de línea, o si el primero no blanco (`str.lstrip`, incluye U+3000) es `= + - @` o `＝ ＋ － ＠`.
- Test: `test_h8_*`. Contraprueba: «a=b», «x - y», «1 + 1» no se tocan.

## Hallazgo 9 · CHANGELOG (i)
- Arreglo: «Ola 14-16» pasa a «Olas 15-16»; entrada 0.8.1 nueva; PRD (RF-46) y README al día (nota del art. 111.2, comparación, CSV, v0.8.1 en la hoja de ruta, 635 tests).
- Test: `test_h9_*`.

## Hallazgo (h) · caducidad en el informe HTML
- Arreglo: sección «Evidencia caducada (n)» en `_marco` de `smc/report_html.py`, escapada.
- Test: `test_h_informe_html_muestra_la_evidencia_caducada_escapada` (con `<b>`). Contraprueba: el ayuntamiento no la muestra.

## Desviaciones
- Tests fuera de «Toca» con cambio mínimo de versión a 0.8.1: `tests/` entero está en Toca, sin desviación real. Los de `test_cli_v06/v07/v08/t08` solo cambian `0.8.0` por `0.8.1`.
- Python 3.10 no probado en local (no instalado, sin red); solo se revisó que no haya `tomllib`, `StrEnum` ni similares. Lo comprobará el CI.
- `smc/report_html.py` y `smc/cli.py` ya estaban en Toca; no se tocó otro fichero.
