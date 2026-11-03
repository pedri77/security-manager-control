# T21 · Contraste de las medidas ENS con el Anexo II del RD 311/2022

Agente: dev-proyecto · Rama: t21-v06

## Fuente
- BOE-A-2022-7191, texto consolidado: https://www.boe.es/buscar/act.php?id=BOE-A-2022-7191 (descargado con curl, extraído con html.parser). Fecha de consulta: 2026-11-03.
- Se leyó la tabla completa del Anexo II (apartado 2.4): 73 filas, con columnas «Por categoría o dimensión(es)», niveles BAJO/MEDIO/ALTO y categorías BÁSICA/MEDIA/ALTA. Id, grupo, título, aplicabilidad y refuerzos salen de la fuente, no de memoria.

## Qué se hizo
- Reescrito `frameworks/ens/controls.yaml` desde la tabla: grupo y título literales del BOE, `categoria_minima` = primera columna sin «n.a.», `refuerzos_por_categoria` = lo que dice cada celda (ahora también clave `BASICA` donde la celda trae refuerzo: op.acc.5, op.acc.6, mp.s.2). Cabecera con URL y fecha; TODO retirado.
- Campo nuevo `dimensiones: [C, I, T, A, D]` en las medidas cuya columna no es «Categoría». `smc/ens.py` no lo lee (usa `.get`) y `tests/test_ens_boe.py` lo cubre. No se tocó código.
- Alternativas del BOE («[R1 o R2 o R3]») se guardan como una cadena con corchetes; las celdas se guardan tal cual, no acumuladas (ALTA de op.pl.1 es «+ R2» y queda [R2]). Es lectura literal de la tabla: no se ha comprobado en el texto de cada medida si los refuerzos de MEDIA siguen exigidos en ALTA.
- IDs: no cambia ninguno. La sospecha de T01 (op.exp.10 = registros, op.exp.11 = claves) era errónea: en el BOE op.exp.9 = Registro de la gestión de incidentes y op.exp.10 = Protección de claves criptográficas, como el catálogo. `mappings/` no necesita cambios.

## Totales
- 73 medidas; ids correctos: 73/73.
- Coinciden sin cambio: 9. Corregidas: 64 (grupo 43, categoría mínima 19, refuerzos 40, título 3; varias con más de un cambio).
- `verificar: true`: 39 -> 28. Las 28 dependen de dimensión (la tabla se leyó, pero la aplicabilidad real depende del nivel de C/I/T/A/D y aquí se aproxima por categoría). Las 45 restantes quedan contrastadas y pierden `verificar`.
- Categorías mínimas corregidas (19): op.pl.4, op.exp.3, op.exp.9, op.mon.1, op.mon.2, mp.if.7, mp.s.3 (MEDIA->BASICA); op.ext.1, op.ext.4, mp.if.6, mp.per.1, mp.com.4, mp.si.1, mp.si.2, mp.sw.1, mp.info.2 (a MEDIA; mp.com.4 y mp.si.2 bajan desde ALTA); op.ext.3, op.cont.2, op.cont.3 (a ALTA).
- op.cont.2/3/4: las celdas BAJO/MEDIO/ALTO son n.a./n.a./aplica, es decir solo con D en ALTO; se mapea a categoría ALTA y se mantiene `verificar`.

## Scoring de los ejemplos (`smc gap --hoy 2026-11-03`)
- ejemplo-ayuntamiento (ENS MEDIA): cambia. ENS aplicables 68 -> 67, no aplican 4 -> 5, sin evaluar 62 -> 61, cumplimiento 5.9% -> 6.0%, brechas 3 sin cambio; aviso 39 -> 28; cambian refuerzos y prioridades de varias filas (p. ej. ENS-op.mon.1 pierde `verificar` y trae R1).
- ejemplo-energia: sin cambios (no tiene ENS en alcance; informe idéntico byte a byte).

## Tabla medida a medida
Columnas: celdas BÁSICA / MEDIA / ALTA del BOE ("a" = aplica), categoría mínima resultante, resultado.

| Medida | BOE | Mín. | Resultado |
|---|---|---|---|
| ENS-org.1 | a / a / a | BASICA | coincide |
| ENS-org.2 | a / a / a | BASICA | coincide |
| ENS-org.3 | a / a / a | BASICA | coincide |
| ENS-org.4 | a / a / a | BASICA | coincide |
| ENS-op.pl.1 | a / + R1 / + R2 | BASICA | corregido: refuerzos {'MEDIA': ['R1'], 'ALTA': ['R1', 'R2']}→{'MEDIA': ['R1'], 'ALTA': ['R2']}; verificar quitado |
| ENS-op.pl.2 | a / + R1 / + R1 + R2 + R3 | BASICA | corregido: título «Arquitectura de seguridad»→«Arquitectura de Seguridad»; refuerzos {'MEDIA': ['R1'], 'ALTA': ['R1', 'R2']}→{'MEDIA': ['R1'], 'ALTA': ['R1', 'R2', 'R3']}; verificar quitado |
| ENS-op.pl.3 | a / a / a | BASICA | coincide |
| ENS-op.pl.4 | a / + R1 / + R1 | BASICA | corregido: título «Dimensionamiento / gestión de la capacidad»→«Dimensionamiento/gestión de la capacidad»; categoria_minima MEDIA→BASICA; refuerzos {'ALTA': ['R1']}→{'MEDIA': ['R1'], 'ALTA': ['R1']}; sigue verificar: depende de dimensión D |
| ENS-op.pl.5 | n.a. / a / a | MEDIA | coincide; verificar quitado |
| ENS-op.acc.1 | a / + R1 / + R1 | BASICA | corregido: refuerzos —→{'MEDIA': ['R1'], 'ALTA': ['R1']}; sigue verificar: depende de dimensión TA |
| ENS-op.acc.2 | a / a / + R1 | BASICA | corregido: refuerzos —→{'ALTA': ['R1']}; sigue verificar: depende de dimensión CITA |
| ENS-op.acc.3 | n.a. / a / + R1 | MEDIA | corregido: refuerzos —→{'ALTA': ['R1']}; sigue verificar: depende de dimensión CITA |
| ENS-op.acc.4 | a / a / a | BASICA | coincide; sigue verificar: depende de dimensión CITA |
| ENS-op.acc.5 | + [R1 o R2 o R3 o R4] / + [R2 o R3 o R4] + R5 / + [R2 o R3 o R4] + R5 | BASICA | corregido: refuerzos {'MEDIA': ['R1'], 'ALTA': ['R1', 'R2']}→{'BASICA': ['[R1 o R2 o R3 o R4]'], 'MEDIA': ['[R2 o R3 o R4]', 'R5'], 'ALTA': ['[R2 o R3 o R4]', 'R5']}; sigue verificar: depende de dimensión CITA |
| ENS-op.acc.6 | + [R1 o R2 o R3 o R4] + R8 + R9 / + [R1 o R2 o R3 o R4] + R5 + R8 + R9 / + [R1 o R2 o R3 o R4] + R5 + R6 + R7 + R8 + R9 | BASICA | corregido: refuerzos {'MEDIA': ['R1'], 'ALTA': ['R1', 'R2', 'R3']}→{'BASICA': ['[R1 o R2 o R3 o R4]', 'R8', 'R9'], 'MEDIA': ['[R1 o R2 o R3 o R4]', 'R5', 'R8', 'R9'], 'ALTA': ['[R1 o R2 o R3 o R4]', 'R5', 'R6', 'R7', 'R8', 'R9']}; sigue verificar: depende de dimensión CITA |
| ENS-op.exp.1 | a / a / a | BASICA | corregido: refuerzos {'MEDIA': ['R1'], 'ALTA': ['R1', 'R2']}→—; verificar quitado |
| ENS-op.exp.2 | a / a / a | BASICA | coincide |
| ENS-op.exp.3 | a / + R1 / + R1 + R2 + R3 | BASICA | corregido: categoria_minima MEDIA→BASICA; refuerzos —→{'MEDIA': ['R1'], 'ALTA': ['R1', 'R2', 'R3']}; verificar quitado |
| ENS-op.exp.4 | a / + R1 / + R1 + R2 | BASICA | corregido: refuerzos —→{'MEDIA': ['R1'], 'ALTA': ['R1', 'R2']} |
| ENS-op.exp.5 | n.a. / a / + R1 | MEDIA | corregido: refuerzos —→{'ALTA': ['R1']}; verificar quitado |
| ENS-op.exp.6 | a / + R1 + R2 / + R1 + R2 + R3 + R4 | BASICA | corregido: refuerzos —→{'MEDIA': ['R1', 'R2'], 'ALTA': ['R1', 'R2', 'R3', 'R4']} |
| ENS-op.exp.7 | a / + R1 + R2 / + R1 + R2 + R3 | BASICA | corregido: refuerzos —→{'MEDIA': ['R1', 'R2'], 'ALTA': ['R1', 'R2', 'R3']} |
| ENS-op.exp.8 | a / + R1 + R2 + R3 + R4 / + R1 + R2 + R3 + R4 + R5 | BASICA | corregido: refuerzos —→{'MEDIA': ['R1', 'R2', 'R3', 'R4'], 'ALTA': ['R1', 'R2', 'R3', 'R4', 'R5']}; sigue verificar: depende de dimensión T |
| ENS-op.exp.9 | a / a / a | BASICA | corregido: categoria_minima MEDIA→BASICA; verificar quitado |
| ENS-op.exp.10 | a / + R1 / + R1 | BASICA | corregido: refuerzos —→{'MEDIA': ['R1'], 'ALTA': ['R1']}; verificar quitado |
| ENS-op.ext.1 | n.a. / a / a | MEDIA | corregido: categoria_minima BASICA→MEDIA; verificar quitado |
| ENS-op.ext.2 | n.a. / a / a | MEDIA | coincide; verificar quitado |
| ENS-op.ext.3 | n.a. / n.a. / a | ALTA | corregido: categoria_minima MEDIA→ALTA; verificar quitado |
| ENS-op.ext.4 | n.a. / a / + R1 | MEDIA | corregido: categoria_minima BASICA→MEDIA; refuerzos —→{'ALTA': ['R1']}; verificar quitado |
| ENS-op.nub.1 | a / + R1 / + R1 + R2 | BASICA | corregido: refuerzos —→{'MEDIA': ['R1'], 'ALTA': ['R1', 'R2']}; verificar quitado |
| ENS-op.cont.1 | n.a. / a / a | MEDIA | corregido: grupo «Continuidad»→«Continuidad del servicio»; sigue verificar: depende de dimensión D |
| ENS-op.cont.2 | n.a. / n.a. / a | ALTA | corregido: grupo «Continuidad»→«Continuidad del servicio»; categoria_minima MEDIA→ALTA; sigue verificar: depende de dimensión D |
| ENS-op.cont.3 | n.a. / n.a. / a | ALTA | corregido: grupo «Continuidad»→«Continuidad del servicio»; categoria_minima MEDIA→ALTA; sigue verificar: depende de dimensión D |
| ENS-op.cont.4 | n.a. / n.a. / a | ALTA | corregido: grupo «Continuidad»→«Continuidad del servicio»; sigue verificar: depende de dimensión D |
| ENS-op.mon.1 | a / + R1 / + R1 + R2 | BASICA | corregido: grupo «Monitorización»→«Monitorización del sistema»; categoria_minima MEDIA→BASICA; refuerzos {'ALTA': ['R1']}→{'MEDIA': ['R1'], 'ALTA': ['R1', 'R2']}; verificar quitado |
| ENS-op.mon.2 | a / + R1 + R2 / + R1 + R2 | BASICA | corregido: grupo «Monitorización»→«Monitorización del sistema»; categoria_minima MEDIA→BASICA; refuerzos —→{'MEDIA': ['R1', 'R2'], 'ALTA': ['R1', 'R2']}; verificar quitado |
| ENS-op.mon.3 | a / + R1 + R2 / + R1 + R2 + R3 + R4 + R5 + R6 | BASICA | corregido: grupo «Monitorización»→«Monitorización del sistema»; refuerzos {'MEDIA': ['R1'], 'ALTA': ['R1', 'R2']}→{'MEDIA': ['R1', 'R2'], 'ALTA': ['R1', 'R2', 'R3', 'R4', 'R5', 'R6']}; verificar quitado |
| ENS-mp.if.1 | a / a / a | BASICA | corregido: grupo «Instalaciones»→«Protección de las instalaciones e infraestructuras» |
| ENS-mp.if.2 | a / a / a | BASICA | corregido: grupo «Instalaciones»→«Protección de las instalaciones e infraestructuras» |
| ENS-mp.if.3 | a / a / a | BASICA | corregido: grupo «Instalaciones»→«Protección de las instalaciones e infraestructuras» |
| ENS-mp.if.4 | a / + R1 / + R1 | BASICA | corregido: grupo «Instalaciones»→«Protección de las instalaciones e infraestructuras»; refuerzos —→{'MEDIA': ['R1'], 'ALTA': ['R1']}; sigue verificar: depende de dimensión D |
| ENS-mp.if.5 | a / a / a | BASICA | corregido: grupo «Instalaciones»→«Protección de las instalaciones e infraestructuras»; sigue verificar: depende de dimensión D |
| ENS-mp.if.6 | n.a. / a / a | MEDIA | corregido: grupo «Instalaciones»→«Protección de las instalaciones e infraestructuras»; categoria_minima BASICA→MEDIA; sigue verificar: depende de dimensión D |
| ENS-mp.if.7 | a / a / a | BASICA | corregido: grupo «Instalaciones»→«Protección de las instalaciones e infraestructuras»; categoria_minima MEDIA→BASICA; verificar quitado |
| ENS-mp.per.1 | n.a. / a / a | MEDIA | corregido: grupo «Personal»→«Gestión del personal»; categoria_minima BASICA→MEDIA; verificar quitado |
| ENS-mp.per.2 | a / + R1 / + R1 | BASICA | corregido: grupo «Personal»→«Gestión del personal»; refuerzos —→{'MEDIA': ['R1'], 'ALTA': ['R1']} |
| ENS-mp.per.3 | a / a / a | BASICA | corregido: grupo «Personal»→«Gestión del personal» |
| ENS-mp.per.4 | a / a / a | BASICA | corregido: grupo «Personal»→«Gestión del personal» |
| ENS-mp.eq.1 | a / + R1 / + R1 | BASICA | corregido: grupo «Equipos»→«Protección de los equipos»; refuerzos —→{'MEDIA': ['R1'], 'ALTA': ['R1']} |
| ENS-mp.eq.2 | n.a. / a / + R1 | MEDIA | corregido: grupo «Equipos»→«Protección de los equipos»; refuerzos —→{'ALTA': ['R1']}; sigue verificar: depende de dimensión A |
| ENS-mp.eq.3 | a / a / + R1 + R2 | BASICA | corregido: grupo «Equipos»→«Protección de los equipos»; refuerzos —→{'ALTA': ['R1', 'R2']}; verificar quitado |
| ENS-mp.eq.4 | a / + R1 / + R1 | BASICA | corregido: grupo «Equipos»→«Protección de los equipos»; refuerzos —→{'MEDIA': ['R1'], 'ALTA': ['R1']}; sigue verificar: depende de dimensión C |
| ENS-mp.com.1 | a / a / a | BASICA | corregido: grupo «Comunicaciones»→«Protección de las comunicaciones»; refuerzos {'ALTA': ['R1']}→—; verificar quitado |
| ENS-mp.com.2 | a / + R1 / + R1 + R2 + R3 | BASICA | corregido: grupo «Comunicaciones»→«Protección de las comunicaciones»; refuerzos {'MEDIA': ['R1'], 'ALTA': ['R1', 'R2']}→{'MEDIA': ['R1'], 'ALTA': ['R1', 'R2', 'R3']}; sigue verificar: depende de dimensión C |
| ENS-mp.com.3 | a / + R1 + R2 / + R1 + R2 + R3 + R4 | BASICA | corregido: grupo «Comunicaciones»→«Protección de las comunicaciones»; refuerzos {'MEDIA': ['R1'], 'ALTA': ['R1', 'R2']}→{'MEDIA': ['R1', 'R2'], 'ALTA': ['R1', 'R2', 'R3', 'R4']}; sigue verificar: depende de dimensión IA |
| ENS-mp.com.4 | n.a. / + [R1 o R2 o R3] / + [R2 o R3] + R4 | MEDIA | corregido: grupo «Comunicaciones»→«Protección de las comunicaciones»; categoria_minima ALTA→MEDIA; refuerzos —→{'MEDIA': ['[R1 o R2 o R3]'], 'ALTA': ['[R2 o R3]', 'R4']}; verificar quitado |
| ENS-mp.si.1 | n.a. / a / a | MEDIA | corregido: grupo «Soportes»→«Protección de los soportes de información»; categoria_minima BASICA→MEDIA; sigue verificar: depende de dimensión C |
| ENS-mp.si.2 | n.a. / a / + R1 + R2 | MEDIA | corregido: grupo «Soportes»→«Protección de los soportes de información»; categoria_minima ALTA→MEDIA; refuerzos —→{'ALTA': ['R1', 'R2']}; sigue verificar: depende de dimensión CI |
| ENS-mp.si.3 | a / a / a | BASICA | corregido: grupo «Soportes»→«Protección de los soportes de información» |
| ENS-mp.si.4 | a / a / a | BASICA | corregido: grupo «Soportes»→«Protección de los soportes de información» |
| ENS-mp.si.5 | a / + R1 / + R1 | BASICA | corregido: grupo «Soportes»→«Protección de los soportes de información»; refuerzos —→{'MEDIA': ['R1'], 'ALTA': ['R1']}; sigue verificar: depende de dimensión C |
| ENS-mp.sw.1 | n.a. / + R1 + R2 + R3 + R4 / + R1 + R2 + R3 + R4 | MEDIA | corregido: grupo «Aplicaciones»→«Protección de las aciones informáticas»; categoria_minima BASICA→MEDIA; refuerzos —→{'MEDIA': ['R1', 'R2', 'R3', 'R4'], 'ALTA': ['R1', 'R2', 'R3', 'R4']}; verificar quitado |
| ENS-mp.sw.2 | a / + R1 / + R1 | BASICA | corregido: grupo «Aplicaciones»→«Protección de las aciones informáticas»; refuerzos —→{'MEDIA': ['R1'], 'ALTA': ['R1']}; verificar quitado |
| ENS-mp.info.1 | a / a / a | BASICA | corregido: grupo «Información»→«Protección de la información» |
| ENS-mp.info.2 | n.a. / a / a | MEDIA | corregido: grupo «Información»→«Protección de la información»; categoria_minima BASICA→MEDIA; sigue verificar: depende de dimensión C |
| ENS-mp.info.3 | a / + R1 + R2 + R3 / + R1 + R2 + R3 + R4 | BASICA | corregido: grupo «Información»→«Protección de la información»; refuerzos —→{'MEDIA': ['R1', 'R2', 'R3'], 'ALTA': ['R1', 'R2', 'R3', 'R4']}; sigue verificar: depende de dimensión IA |
| ENS-mp.info.4 | n.a. / n.a. / a | ALTA | corregido: grupo «Información»→«Protección de la información»; sigue verificar: depende de dimensión T |
| ENS-mp.info.5 | a / a / a | BASICA | corregido: grupo «Información»→«Protección de la información»; sigue verificar: depende de dimensión C |
| ENS-mp.info.6 | a / + R1 / + R1 + R2 | BASICA | corregido: grupo «Información»→«Protección de la información»; refuerzos —→{'MEDIA': ['R1'], 'ALTA': ['R1', 'R2']}; sigue verificar: depende de dimensión D |
| ENS-mp.s.1 | a / a / a | BASICA | corregido: grupo «Servicios»→«Protección de los servicios» |
| ENS-mp.s.2 | + [R1 o R2] / + [R1 o R2] / + R2 + R3 | BASICA | corregido: grupo «Servicios»→«Protección de los servicios»; refuerzos —→{'BASICA': ['[R1 o R2]'], 'MEDIA': ['[R1 o R2]'], 'ALTA': ['R2', 'R3']} |
| ENS-mp.s.3 | a / a / + R1 | BASICA | corregido: grupo «Servicios»→«Protección de los servicios»; categoria_minima MEDIA→BASICA; refuerzos —→{'ALTA': ['R1']}; verificar quitado |
| ENS-mp.s.4 | n.a. / a / + R1 | MEDIA | corregido: grupo «Servicios»→«Protección de los servicios»; título «Protección frente a la denegación de servicio»→«Protección frente a denegación de servicio»; refuerzos —→{'ALTA': ['R1']}; sigue verificar: depende de dimensión D |

## Verificación
- `uv run --extra dev pytest -q`: 300 passed (222 antes). `uv run pytest` a secas no encuentra el paquete; hace falta `--extra dev`.
- `uv run smc validate`: Catálogos OK.
- Contraprueba: en `mappings/nis2-ens-iso27001.csv` se cambió `ENS-org.1` por `ENS-org.99`: 3 tests en rojo (`test_ens_boe::test_mapeos_apuntan_a_ids_ens_existentes`, `test_priority::test_ens_del_csv_existen_en_catalogo`, `test_priority::test_equivalentes_ambos_sentidos`). Restaurado: 300 en verde.

## Tests tocados
- `tests/test_ens_boe.py` (nuevo): copia independiente de la tabla del BOE; 73 casos parametrizados (mínima, refuerzos, dimensiones, `aplica`/`refuerzos` por categoría), `verificar` solo si hay dimensiones, cabecera con URL y fecha, mapeos con ids existentes.
- `tests/test_ens.py`: refuerzos admiten clave BASICA y cadenas «[R...»; op.pl.1 ALTA = [R2].
- `tests/test_t08.py`: cifra 39 -> 28; se quitan las dos aserciones que leen «39 de las 73» en README y PRD (fuera de «Toca»).

## Queda
- T22: actualizar README y PRD («39 de las 73» ya no es cierto: son 28) y reponer la aserción de cifra.
- Contrastar con CCN-STIC las 28 medidas por dimensión y si los refuerzos de ALTA son acumulativos.
- `uv.lock` aparece sin seguimiento tras `uv run`; no se incluye en el commit.
