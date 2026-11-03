# ADR-002: Informes HTML autocontenidos y dashboard estático local

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-11-03 |

## Contexto

ADR-001 prevé un dashboard web en v0.4 sobre el mismo modelo de datos que el CLI. Las evaluaciones contienen datos confidenciales de clientes (brechas, topologías, proveedores) y SMC debe poder ejecutarse en local u on-prem en la UE. El Security Manager y el consultor necesitan entregar un informe legible a dirección y ver varios clientes de un vistazo.

## Opciones consideradas

1. Aplicación web con servidor (API, base de datos, autenticación).
2. Generar PDF directamente con una librería de terceros.
3. Generar HTML autocontenido y un sitio estático local, solo con la biblioteca estándar.

## Decisión

1. `smc report` produce **un único fichero HTML** con CSS en línea, sin JavaScript, fuentes, imágenes ni recursos externos. Incluye estilos `@media print`: el PDF se obtiene imprimiendo desde el navegador.
2. `smc dashboard` genera un **sitio estático** en un directorio de salida: un `index.html` multicliente (cumplimiento por marco, brechas P1, acciones vencidas, semáforo) y un HTML por cliente que reutiliza el renderizado del informe.
3. Todo se genera con la biblioteca estándar de Python; la única dependencia del proyecto sigue siendo PyYAML.
4. Todo texto procedente de las evaluaciones se escapa (`html.escape`) antes de entrar en el HTML. Los nombres de fichero de salida se derivan del nombre del fichero de entrada, no del nombre del cliente.
5. Los informes y el dashboard consumen `smc.gap.analyse`; no reimplementan el análisis.

## Consecuencias

- Soberanía: nada sale del equipo ni requiere red; no hay servidor que operar, proteger ni parchear. Coherente con ADR-001: las evaluaciones reales y las salidas generadas viven fuera de este repositorio.
- Un informe se puede archivar, enviar como adjunto o abrir sin conexión, y reproducir con `--hoy`.
- No hay interactividad (filtros, edición en la página) ni actualización en vivo: el dashboard se regenera con cada ejecución. Si más adelante hace falta una aplicación con servidor, queda como decisión nueva y deberá respetar la soberanía del dato.
- El PDF depende del navegador del usuario; no hay PDF determinista generado por SMC.
- La salida generada contiene datos de cliente: es responsabilidad del operador guardarla fuera del repositorio.
