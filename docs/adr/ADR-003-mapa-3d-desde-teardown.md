# ADR-003: Mapa 3D de dispositivos adaptado de la skill teardown

| Campo | Valor |
|---|---|
| Estado | Propuesta |
| Fecha | 2026-11-03 |

## Contexto

SMC ya sabe qué dispositivos tiene un cliente (registro de tecnologías, inventario), en qué estado están sus reglas, qué vulnerabilidades tienen abiertas y cuánta madurez hay por vertical. Hoy eso se lee en tablas. Para explicar a dirección y al equipo dónde está el riesgo hace falta una vista espacial: qué zonas de la red hay, qué dispositivos las protegen y cuáles están en rojo o sin poder evaluarse.

La skill local `teardown` (origen: elvarofficial/teardown, licencia MIT, sobre whaleyxbt/claude-motion, MIT) construye una máquina como una sola página HTML offline: un modelo único mueve piezas y paneles, un botón por subsistema abre la pieza que trabaja, hay cortes y vistas de cámara, una visita automática cede el control al primer gesto y la misma línea de tiempo se graba a vídeo. Encaja con la soberanía de ADR-001 y ADR-002 (nada sale del equipo, sin servidor, sin CDN).

## Opciones consideradas

1. Gráfico 2D estático (SVG) generado por SMC: sin dependencias nuevas, pero sin vistas, cortes ni visita.
2. Visor 3D con una librería cargada desde CDN: rechazado, rompe offline y soberanía.
3. Adaptar el patrón de teardown (modelo único, subsistemas, cortes, visita) a una red de cliente, con el JSON de SMC como única fuente y el HTML autocontenido con la librería 3D incluida en el fichero.

## Decisión

1. Se adopta la opción 3, en dos pasos. Este ADR y la tarea T15 fijan solo el **contrato de datos**: `smc mapa` exporta un JSON versionado `schema: smc-mapa/1` (zonas, dispositivos, capa OSI, vertical, estado de reglas con motivo si no es evaluable, vulnerabilidades abiertas fuera de SLA, semáforo). El visor queda como siguiente paso.
2. El visor lee **solo ese JSON**. Ningún número del visor se calcula por su cuenta: es la regla de «una sola fuente» de teardown aplicada a SMC.
3. De teardown se reutiliza el **patrón**, no el código: no se copia ningún fichero de la skill al repositorio. Si más adelante se incorporan fragmentos del kit (MIT), se hará con aviso de licencia y atribución en un ADR nuevo.
4. Se descarta lo que es física de máquina (cinemática, motores, sonido de motor). Una red no se mueve: lo que cambia es el estado.
5. El semáforo tiene reglas fijas y documentadas (`docs/mapa-3d.md`). Un dato que falta nunca se pinta de verde: es gris.
6. El JSON no incluye rutas, propietarios, costes, CPE ni notas libres: solo los campos del esquema. El mapa generado contiene datos de cliente y vive fuera del repositorio (ADR-001).
7. Los dispositivos sin zona o con zona desconocida se exportan en `sin_zona` con su motivo; el visor los dibuja en un área aparte, no los oculta.

## Consecuencias

- El contrato queda probado y estable antes de invertir en el visor; el esquema se versiona (`smc-mapa/2` si cambia de forma incompatible).
- Los registros reales necesitan campos opcionales nuevos (`zona`, `capa_osi`) para que el mapa sea útil; con las plantillas actuales todo cae en `sin_zona`. Añadirlos a las plantillas queda para T16 o una tarea posterior.
- La zona y la capa OSI son declaradas por quien rellena el registro: el mapa no las descubre. La capa por defecto según la vertical es una aproximación y se marca como tal (`capa_osi_origen`).
- Mantener un visor 3D propio es coste continuo (WebGL, rendimiento en equipos modestos, accesibilidad). Mitigación: el informe HTML y las tablas de SMC siguen siendo la vía principal; el mapa es complemento y debe incluir la misma información en texto.
- Atribución: cualquier reutilización futura de código de teardown o claude-motion conserva el aviso MIT de ambos.
