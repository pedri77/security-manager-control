# Ola 9 · revisor-ola (T19, T20, T21)

Rango revisado: bbb08bc..1308daf (main). Commits de tarea: dc1e6f2 (T19), 2fda399 (T21), bd1c6aa (T20); merges 3b26090, 880a926, 6fc75da limpios (diff contra el segundo padre = solo lo de las ramas ya fusionadas).
Tests: `uv run --extra dev pytest -q` -> 335 passed.

## Veredicto: APTA con reservas

No hay hallazgos [V] de severidad alta que invaliden una tarea marcada hecha. Lo grave es un emparejamiento erróneo de registros entre clientes en el dashboard (T19) y una inyección HTML en el visor (T20) con un mapa.json manipulado. Conviene arreglarlos antes de publicar v0.6.0 (T22) o en una tarea de endurecimiento.

## Hallazgos

1. [V] media-alta · T19 · smc/dashboard.py:93-97 (`_asociar`): el registro se asigna por prefijo y por orden alfabético de evaluación, no por la coincidencia más larga. Escenario: el directorio tiene `acme.yaml`, `acme_sur.yaml` y `acme_sur.registry.yaml`. `acme.yaml` se procesa antes y se queda con el registro de ACME SUR: la página `acme.html` muestra los proveedores, costes y reglas de otro cliente, y `acme_sur` sale con «—». Reproducido: el texto del proveedor de acme_sur aparece en `o1/acme.html` y no en `acme-sur.html`. Es una mezcla silenciosa de datos entre clientes. Arreglo: asociar primero las evaluaciones de stem más largo, o exigir el nombre exacto `<stem>.registry.yaml`, y añadir un test con `x` y `x_y`.
2. [V] media · T20 · smc/visor.py:97-98: `resumen.por_semaforo` (y `resumen.dispositivos`) se insertan en la cabecera HTML sin `_e`, y `validar_mapa` no comprueba sus tipos. Escenario: un mapa.json con `"por_semaforo": {"rojo": "<img src=x onerror=...>"}` ejecuta código en Chrome headless (`<body data-pwn="1">`). La CSP `script-src 'unsafe-inline'` (visor.py:106) permite los manejadores inline. Incumple «escape de todos los textos del JSON». Si falta `por_semaforo`, sale KeyError con traceback en lugar de rc=2. Arreglo: escapar con `_e` y validar que son enteros. Como el script del módulo es constante, cambiar la CSP a `script-src 'sha256-…'` en vez de `'unsafe-inline'`.
3. [V] media · T19×T21 · smc/gap.py:84 (`NOTA_VERIFICAR`), smc/report_html.py:92: el aviso sigue diciendo que 28 medidas tienen «aplicabilidad pendiente de contrastar con el Anexo II» y que los refuerzos «no son definitivos». Tras T21 ya están contrastadas con el Anexo II; lo pendiente es la dependencia de dimensiones y las guías CCN-STIC. El informe del cliente afirma algo falso, y tests/test_t08.py fija ese texto. Arreglo: reformular como «depende del nivel de las dimensiones C/I/T/A/D (aproximado por categoría)». Va en T22 o en una tarea nueva, porque gap.py y report_html.py no estaban en el «Toca» de T21.
4. [V] baja · T19 · smc/report_html.py:308 y :336, smc/gap.py:279: `sorted()` sobre claves (proveedor, moneda) mezcla str con int. Escenario: un registro con `proveedor: 123` o `moneda: 5` hace que `smc report --registry` acabe con TypeError y traceback, no con rc=2 y «ERROR». El CLI solo captura ValueError. Arreglo: `str()` en las claves al ordenar o `key=lambda kv: tuple(map(str, kv[0]))`.
5. [V] baja · T20 · smc/visor.py:131 y la cabecera de smc/assets/three.bundle.min.js (esbuild `--legal-comments=none`): el visor.html que se entrega solo lleva «three.js r186 (MIT)». No incluye el aviso de copyright ni el de permiso que exige la MIT para las copias distribuidas. En el repo la licencia está bien (smc/assets/THREE-LICENSE). Arreglo: incrustar THREE-LICENSE completa en un comentario `/*! … */` del script.
6. [V] baja · T20 · smc/visor.py `_tabla`: la tabla accesible no tiene la misma información que el panel. Faltan los CVE fuera de SLA, nº de reglas, reglas sin uso, semáforo de zona, avisos del mapa y totales del resumen (no evaluables, madurez de verticales). El panel se pinta con JS aunque no haya WebGL, así que solo pierde quien no ejecuta JS. Arreglo: añadir esas columnas y un bloque de resumen y avisos en el servidor.
7. [V] baja · T19/T20 · fuera de «Toca»: tests/test_dashboard.py (T19, una línea, justificado en el informe) y docs/img/visor.png (T20, anotado en el informe y pedido en el brief). Sin efecto funcional.
8. [D] baja · T19: la sección MITRE es global (catálogo de casos de uso del SOC) y aparece igual en el informe de cada cliente, sin decir que no es del cliente. Falta confirmar con David si debe llevar la etiqueta «capacidad del SOC, no del cliente».

## Comprobado sin defecto
- T19: escape de motivo, nombre, moneda, proveedor, any-any, fechas y licencias hostiles en HTML y Markdown (fuzz de 13 casos). Enlaces solo `https://`. Coste NaN, inf o texto sin romper. `--registry` inválido o inexistente da rc=2 sin escribir el fichero. Slugs reservados: `MITRE.yaml` sale como mitre-2 e `Index.yaml` como index-2. El dashboard sin `--hoy` funciona. Cálculos de `smc.tech` y `smc.mitre` reutilizados; solo se suman totales por moneda.
- T20: el JSON va embebido con `<` escapado (`<`) y U+2028/2029. visor-app.js no usa innerHTML, fetch ni eval; todo pasa por textContent o fillText. Bundle sin fetch ni XHR; solo dos URL en cadenas internas que no se cargan. En Chrome headless con swiftshader: `data-listo=3d` y solo mensajes del driver GL en consola. El gris nunca sale verde (`sem()` y `SEMAFORO_TXT.get` caen a gris). Ninguna línea de 40 caracteres o más coincide con el código de ~/.agents/skills/teardown (147 líneas comparadas); three.js viene del paquete npm oficial (MIT).
- T21: comparé las 73 medidas, no una muestra, contra la tabla del BOE descargada el 2026-11-03 (BOE-A-2022-7191, parseo `<tr>/<td>`). Grupo, título, categoría mínima, refuerzos por celda (incluidas las de «[R1 o R2…]»: op.acc.5, op.acc.6, mp.com.4, mp.s.2), dimensiones y `verificar` solo si hay dimensión: 0 diferencias. `smc.ens.refuerzos` devuelve la celda de la categoría sin acumular, igual que el BOE (op.pl.1 ALTA = [R2]). La salida de `smc gap` muestra bien «[R1 o R2 o R3 o R4], R5, R8, R9». `smc validate` OK. Contraprueba propia en una copia: un id inexistente en el CSV y una alternativa alterada en op.acc.5 ponen 2 tests en rojo.
- Evidencias: T19, T20 y T21 tienen informe con comandos, salidas y contrapruebas reales. Las cifras de tests de los informes (244, 235, 300) son de sus ramas; main tiene 335.

## Sin revisar
- La semántica de los refuerzos de ALTA en el texto de cada medida (si R1 de MEDIA sigue exigido en ALTA cuando la celda no lo repite) y las guías CCN-STIC.
- GPU real, móvil y contraste de las etiquetas 3D; `prefers-reduced-motion` en navegador.
- La lógica de semáforo por zona en smc/mapa.py (fuera de la ola).

## Tareas que deberían reabrirse
Ninguna como «no hecha». Los hallazgos 1-4 conviene meterlos en una tarea de endurecimiento antes o junto a T22.

## Objetivo
La ola acerca el objetivo de v0.6: informe y dashboard con tecnologías, reglas, suscripciones y MITRE; visor 3D offline; ENS contrastado con el BOE. Sin cubrir: el CLI `smc visor` y `smc gap --registry` (T22 y una opción), el texto del aviso ENS (hallazgo 3) y el contraste por dimensiones de las 28 medidas. Ninguna tarea pasa su «Verifica» sin servir al objetivo, pero la de T19 no cubría el dashboard con varios clientes de nombres parecidos (hallazgo 1).

## Libro
- Supuesto confirmado: la tabla del Anexo II se puede reconstruir con fiabilidad (73/73 contra el BOE).
- Supuesto desmentido: la sospecha de T01 de que op.exp.10 eran los registros (en el BOE es la protección de claves) y la cifra de 39 medidas en verificar (son 28).
- Decisiones que faltan: regla de asociación registro-evaluación (prefijo o nombre exacto); si los refuerzos se muestran acumulados o tal cual la celda; si MITRE va en el informe del cliente marcado como capacidad del SOC; la CSP del visor con hash.
