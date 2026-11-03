# T32 — Salida para auditor (dev-proyecto)

Hecho: `smc/soa.py` y `tests/test_soa.py` (9 tests nuevos; suite completa 536 verdes).

## Qué hace
- `declaracion(assessment, hoy=None)` usa `smc.gap.analyse` y devuelve un dict: `aplicabilidad` (una fila por control de cada marco en alcance), `evidencias` (hoja), `avisos`, `aviso` fijo, `cliente`, `fecha`.
- Columnas: marco, id, título, aplica (sí/no), justificación (notas si `no_aplica`; motivo de categoría ENS si no aplica por categoría), estado, evidencias, prioridad (brechas y sin evaluar), refuerzos ENS, mapeo (equivalentes y `ISO27001:x` del CSV).
- Evidencias: texto o dict `{ref, fecha, caduca|vigencia_dias}`; estado vigente / caduca_pronto (≤30 d) / caducada / sin_fecha, calculado en local sin depender de `smc/evidencias.py` (T33). No cambia puntuación.
- `a_csv` (BOM, `\r\n`, prefijo `'` en `= + - @ \t \r`), `a_xlsx` (zipfile, inlineStr, dos hojas «Aplicabilidad» y «Evidencias», nombres de hoja saneados, caracteres de control XML eliminados), `a_html` (`@media print`, todo escapado, sin JS ni CDN). Los tres aceptan la salida de `declaracion`; CSV y HTML también la lista de filas; `a_xlsx` también un dict `{hoja: filas}`.

## Verifica
`uv run --extra dev pytest -q` -> 536 passed. ENS MEDIA (ejemplo con `sector_publico: true`, `categoria_ens: MEDIA`) da 73 filas ENS con las no aplicables justificadas. XLSX abre con zipfile, todas las partes parsean con `xml.etree`, dos hojas.
Contraprueba: evidencia `=HYPERLINK(...)` sale como `'=HYPERLINK` en CSV y XLSX; `<script>` sale escapado en XLSX y HTML.

## Decisiones y desviaciones
- `ejemplo-energia.yaml` no tiene ENS (sector_publico false): el caso ENS MEDIA se construye en el test modificando el cliente en memoria.
- En CSV solo va la hoja de aplicabilidad (el CSV no tiene hojas); las evidencias van en el XLSX y en `d["evidencias"]`.
- Las evidencias de controles «no aplica» no se listan.
- Fechas no parseables se tratan como sin fecha, sin aviso (T33 puede añadirlo).
- No toca cli.py ni gap.py; no añade uv.lock.
