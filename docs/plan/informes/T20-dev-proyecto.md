# T20 · Visor 3D offline del mapa de dispositivos

Rama `t20-v06`. Ficheros fuera del «Toca» (anotado): `docs/img/visor.png` (pedido en el brief) y `smc/assets/*` (cubierto por «Toca: smc/assets/»).

## Qué se hizo
- `smc/visor.py`: `generar_visor(mapa: dict) -> str` y `python -m smc.visor <mapa.json> [-o visor.html]`. Valida con `mapa.validar_mapa` y lanza `ValueError` si el mapa no cumple `smc-mapa/1`. rc=2 con mensaje `error: ...` si falta el fichero, el JSON está roto o el esquema no es `smc-mapa/1`. Sin `-o` escribe en stdout.
- `smc/assets/`: `three.bundle.min.js` (three 0.186.1 vendorizado, bundle único con tree-shaking, 540 KiB), `three-entry.js` (lista de símbolos), `THREE-LICENSE` (MIT), `visor-app.js` (código propio, ~250 líneas). `pyproject.toml`: `package-data` de assets.
- ADR-004 (decisión, origen, versión y comando esbuild 0.28.1). `docs/mapa-3d.md` actualizado.
- Patrón de teardown (modelo único, un botón por zona, panel con números del JSON, vistas, visita que cede al primer gesto) escrito desde cero; no se copió código de la skill. `three.module.js` importa `./three.core.js`, por eso se vendoriza un bundle único.

## Qué hace el visor
Plataformas por zona (8 + «Sin zona» aparte si hay), piezas por dispositivo coloreadas por semáforo (rojo/ámbar/gris/verde; valor desconocido = gris), botón por zona (aísla y acerca), vistas general / planta / capas OSI / solo rojos, clic en pieza = detalle, visita automática (rojos primero, 6 s por zona; pointerdown/wheel/keydown la cede, 25 s de calma la devuelven), `prefers-reduced-motion` (sin visita ni transiciones). Panel con resumen, reglas no evaluables con motivo y KEV fuera de SLA. Tabla accesible server-side con la misma información. CSP `default-src 'none'`.

## Comandos y resultados
```
uv run smc mapa technologies/registry.template.yaml -o <scratch>/mapa.json
uv run python -m smc.visor <scratch>/mapa.json -o <scratch>/visor.html   # 565 KiB (578.826 bytes)
uv run pytest -q                                                          # 235 passed (222 previos + 13 nuevos)
node shot.mjs visor.html docs/img/visor.png general                      # Playwright channel 'chrome', 1280x720
```
- Navegador (Chrome del sistema, GL por swiftshader): `data-listo=3d`, **0 errores de consola**, **0 peticiones de red**. Con `reducedMotion: reduce` también 0 errores. (Solo aparece el aviso del driver «GPU stall due to ReadPixels» al hacer la captura en GL por software; no es del visor y se filtra.)
- HTML sin `src=`/`href=`/`fetch(`/`XMLHttpRequest`/`import(` (test). Las cadenas `http://www.w3.org/1999/xhtml` y una URL en un comentario de shader están dentro del bundle de three, no se cargan.

## Captura (docs/img/visor.png)
Cabecera «Mapa de la red (SMC)» con 5 dispositivos (rojo 1, ámbar 1, gris 1, verde 2). Barra de 9 botones de zona (puntos de color por semáforo) y barra de vistas. Escena: 8 losas oscuras con borde del color de su semáforo y etiqueta; Perímetro con una esfera roja y otra verde, Usuarios con una gris y una verde, Nube con una ámbar, el resto vacías (gris). A la derecha el panel «Resumen del mapa» (1/1/1/2, reglas no evaluables 1 con el motivo del EDR ficticio, «sin evaluación» en madurez). Debajo, leyenda y la tabla en texto. La esfera gris no es verde. También revisé la vista de capas (piezas flotando por capa, losas casi transparentes) y la vista de zona con panel por dispositivo.

## Contraprueba real
- Con un nombre `</script><img src=x onerror="window.__pwn=1">` (y un motivo `<b onmouseover=...>`) en Chrome: el panel lo muestra como texto, `window.__pwn` queda `undefined`, 0 `<img>` en el DOM, la página no se rompe.
- Mutación: quitar el `.replace("<", "\\u003c")` de `json_embebido` pone en rojo 2 tests (`test_json_embebido_escapa_menor`, `test_nombre_malicioso_no_rompe_la_pagina`); restaurado, 13/13.
- `test_contraprueba_sin_escape_se_rompe` prueba que sin escape hay más de 2 `</script>`.
- Semáforo `azul` en un dispositivo: `ValueError` (test).

## Decisiones y lo que queda
- El panel no suma por su cuenta: usa `resumen` y valores por dispositivo del JSON (KEV y motivos se listan, no se agregan).
- La prueba en navegador real es manual (script Playwright en el scratchpad, no en el repo, para no añadir Node al proyecto). Pendiente: GPU integrada y móvil vertical; revisión de contraste de las etiquetas 3D.
- T22: cablear `smc visor <mapa.json> -o visor.html` llamando a `smc.visor.generar_visor` (o a `smc.visor.main`).
- `uv.lock` generado por uv no se versiona.
