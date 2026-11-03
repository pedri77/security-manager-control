# T01 — Aplicabilidad ENS por categoría (informe)

## Qué se hizo
- `frameworks/ens/controls.yaml`: las 73 medidas llevan `categoria_minima`; 11 llevan `refuerzos_por_categoria`; 39 llevan `verificar: true`. IDs sin cambios.
- `smc/ens.py`: `aplica(control, categoria)` y `refuerzos(control, categoria)`. Categoría vacía, `None` o desconocida = ALTA con `UserWarning`. Acepta `Control` o dict.
- `tests/test_ens.py`: 10 tests (22 en total con los 12 originales).

## Limitación importante (honestidad de fuente)
Sin red ni copia del Anexo II/CCN-STIC en el repo, los valores se rellenaron **de memoria** del RD 311/2022 (y del RD 3/2010 anterior). Las 34 medidas sin `verificar` (org.*, op.cont.1-4, if.1-6, per.2-4, eq.1-2, si.1/3/4, info.1/5/6, s.1/2, pl.3, acc.1/2/4, exp.2/4/6/7/8) las considero seguras; las 39 con `verificar: true` hay que contrastarlas con el Anexo II antes de dar el scoring por categoría como definitivo. Por eso **el TODO de cabecera se mantiene** (reformulado), según la regla de la tarea.

## Dudas principales
- Todos los `refuerzos_por_categoria` (11 medidas) están marcados `verificar`: el reparto R1..Rn por categoría no está contrastado.
- Discrepancia de ID: en el RD 311/2022 `op.exp.10` es «Protección de los registros de actividad» y `op.exp.11` «Protección de claves criptográficas»; el catálogo tiene `op.exp.10` = claves. No se cambió el ID (regla de T01); revisar si falta una medida o está desplazada (el catálogo suma 73).
- Categoría mínima dudosa entre BASICA/MEDIA/ALTA: pl.2, pl.5, acc.3, exp.3/5/9, ext.1-4, nub.1, mon.1/2, if.7, per.1, eq.3/4, com.1-4, si.2/5, sw.1/2, info.2/3/4, s.3/s.4.

## Verifica
- `smc validate` -> `Catálogos OK`.
- `pytest -q` -> 22 passed.
- Contraprueba: invertir `CATEGORIAS` en `smc/ens.py` -> 5 tests en rojo (`test_solo_alta`, `test_media`, `test_refuerzos`, `test_orden_categorias`, `test_basica_aplica_en_todas`); restaurado, 22 verdes.
- Nota: al alternar el orden con el mismo tamaño de fichero, pytest usó un `.pyc` obsoleto hasta tocar el fichero; no afecta al código.

## Decisiones / queda
- Ficheros fuera de «Toca»: ninguno. `gap.py` y `cli.py` intactos (T04 integra).
- Pendiente: revisión humana de las 39 medidas `verificar` contra el Anexo II / CCN-STIC 804/808; después, quitar el TODO.
