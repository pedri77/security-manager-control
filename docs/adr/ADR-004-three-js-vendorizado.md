# ADR-004: three.js vendorizado en el repositorio

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-11-03 |

## Contexto

El visor 3D (ADR-003, T20) debe ser una sola página HTML que funcione sin red: sin CDN, sin `fetch`, y con datos de cliente que no salen del equipo (ADR-001). Necesita una librería WebGL. Escribir un motor propio sería coste de mantenimiento sin valor.

## Opciones

1. CDN: rechazada (rompe offline y soberanía, y ejecuta código de terceros sin control de versión).
2. Dependencia npm en el repo: añadiría Node a un proyecto cuya única dependencia es PyYAML.
3. Vendorizar una copia fija de three.js (MIT) en `smc/assets/` y generar el HTML con ella incrustada.

## Decisión

Opción 3.

- Origen: three.js 0.186.1 (`three.module.js`, MIT, Copyright 2010-2026 three.js authors), tomado de `~/.agents/skills/teardown/node_modules/three` (instalado con npm desde el paquete oficial `three`). Licencia en `smc/assets/THREE-LICENSE`.
- `three.module.js` importa `./three.core.js` (1,4 MB). Para no incrustar dos módulos ni 2 MB, se genera un bundle único con tree-shaking solo con lo que usa el visor (`smc/assets/three-entry.js` lista los símbolos) y se vendoriza el resultado: `smc/assets/three.bundle.min.js` (540 KiB, IIFE con `var THREE`).
- Comando de regeneración (esbuild 0.28.1; sustituir `THREE_SRC` en `three-entry.js` por la ruta a `three/build/three.module.js`):

```
esbuild three-entry.js --bundle --minify --format=iife --global-name=THREE \
        --legal-comments=none --target=es2020 --outfile=smc/assets/three.bundle.min.js
```

- El generador (`smc/visor.py`) incrusta el bundle y `visor-app.js` (código propio del visor) dentro de un único `<script type="module">`; el aviso de copyright MIT va en un comentario de ese script y la licencia completa en el repo. Se declara `[tool.setuptools.package-data] smc = ["assets/*"]` para que los ficheros viajen en el paquete.
- Actualizar three.js es una decisión explícita: regenerar el bundle, repasar el diff y los tests del visor, y anotar la versión aquí.
- La CSP de la página (`default-src 'none'; script-src 'unsafe-inline'`) impide cualquier carga externa aunque se colara una.

## Consecuencias

- El HTML pesa ~565 KiB y funciona offline y sin servidor.
- El bundle minificado no es legible: la fuente de verdad es el paquete `three` de esa versión y el comando de arriba.
- Hay que vigilar avisos de seguridad de three.js a mano (no hay gestor de dependencias que lo haga).
- Del repo teardown solo se usó el patrón (ADR-003); no se copió código de la skill.
