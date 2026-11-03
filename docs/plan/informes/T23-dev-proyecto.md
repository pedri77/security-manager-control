# T23 · dev-proyecto · Endurecer v0.6 (v0.6.1)

Rama t23-v061. Tests: 363 verdes (`uv run --extra dev pytest -q`; antes 335 en main + los de T22; 17 nuevos en `tests/test_t23.py`).
Reproducción previa: con `smc/` revertido al estado de main, `tests/test_t23.py` da 13 fallos de 17 (los 4 que pasan son contrapruebas que deben pasar en ambos estados).

| # | Hallazgo | Test | Contraprueba real | Resultado |
|---|---|---|---|---|
| 1 | Registro de `acme_sur` en `acme.html` | `test_h1_registro_va_a_la_evaluacion_de_stem_mas_largo`, `test_h1_empate_exacto_avisa_y_no_asocia` | Con el código de main el proveedor de Sur aparece en `acme.html` (test en rojo). Sin empate se asocia y sin avisos (`test_h1_contraprueba_sin_empate_se_asocia`) | `_emparejar` en `dashboard.py`: gana el stem más largo; dos registros con el mismo stem = aviso y ninguno asociado |
| 2 | Inyección en la cabecera del visor y CSP `unsafe-inline` | `test_h2_resumen_mal_formado_da_valueerror` (7 mutaciones), `test_h2_cli_resumen_roto_rc2_sin_traceback`, `test_h2_cabecera_escapa`, `test_h2_csp_con_hash_del_script_del_modulo` (recalcula el sha256 sobre el HTML generado y compara) | Chrome 3.º: payload `"rojo": "<img src=x onerror=window.__pwn=1>"` con el visor de main: `__pwn = 1`. Con el nuevo: ValueError (rc 2); saltándome la validación, la cabecera lo escapa (`__pwn` undefined, 0 imgs); inyectando la etiqueta cruda en el HTML nuevo, la CSP la bloquea (`script-src-attr`, `__pwn` undefined). Un script alterado cambia el hash (`test_h2_contraprueba_...`) | Hecho |
| 3 | Aviso ENS desactualizado | `test_h3_aviso_ens_dice_la_verdad`; `tests/test_t08.py` actualizado (sigue la contraprueba: sin ENS no hay aviso) | En main el texto decía «pendiente de contrastar» (rojo) | `NOTA_VERIFICAR` nuevo en `gap.py`, usado también por `report_html.py` |
| 4 | TypeError con `proveedor`/`moneda` no str | `test_h4_proveedor_y_moneda_no_str` (123, 5, None, 2.5; HTML, Markdown y CLI rc 0) | En main: TypeError con proveedor 123, moneda 5 y 2.5 | `sorted(..., key=str)` en `report_html.py` y `gap.py` |
| 5 | Licencia MIT en el HTML | `test_h5_licencia_mit_completa_en_el_html` | En main solo «three.js r186 (MIT)» (rojo) | Comentario `/*! … */` con THREE-LICENSE completo, dentro del script hasheado |
| 6 | Tabla accesible incompleta | `test_h6_tabla_incluye_todo_el_panel`, `test_h6_contraprueba_aviso_hostil_escapado` | En main faltaban CVE, reglas, zonas, avisos y totales (rojo); un aviso hostil sale escapado | Columnas nuevas, bloque de resumen, zonas y avisos en servidor |
| 8 | MITRE sin etiqueta | `test_h8_mitre_etiquetado_en_html_y_markdown` | En main sin etiqueta (rojo) | «Catálogo de casos de uso del SOC (común a todos los clientes)» en HTML y Markdown |

## Chrome (channel chrome, swiftshader)
`visor.html` nuevo desde la plantilla: `data-listo=3d`, 0 errores de consola (filtrados los avisos del driver GL), 0 violaciones CSP. Scripts y salidas en el scratchpad de la sesión (`scratchpad/t23/`).

## Decisiones
- La validación nueva está en `visor.py` (`_validar_resumen`), no en `mapa.py`, que no estaba en el «Toca». Valida también que `avisos` sea una lista.
- La CSP conserva `style-src 'unsafe-inline'` (el CSS va en `<style>`); solo el script pasa a hash.
- `docs/img/visor.png` no se regenera: la cabecera y la escena 3D no cambian visiblemente (los cambios van en la tabla, bajo el pliegue).
- Versión 0.6.1 (`__init__`, pyproject, badge del README, CHANGELOG); los tests de versión pasan a 0.6.1.
- Refuerzos ENS tal cual la celda del BOE: ya era así, sin cambios.

## Queda
Nada de los hallazgos 1-6 y 8. `uv.lock` quedó sin versionar (no es del «Toca»).
