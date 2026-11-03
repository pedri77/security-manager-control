# resources/

- `rss.yaml`: feeds de fuentes oficiales y de referencia. Todos `verificado: false` (escritos sin red; comprobar a mano). `url_feed: null` = ruta del feed no confirmada; se da la página de avisos en `url_web`.
- `ecosistema.yaml`: proyectos públicos (Pages y repos) y pendientes (`estado: pendiente`, sin URL).
- `external/`, `internal/`: plantillas de terceros e inventario (anteriores).

Código: `smc/resources.py` (`cargar_rss`, `cargar_ecosistema`, `validar`, `a_opml`, `render_markdown`).
El OPML (`a_opml()`) lo ingiere el agregador interno de noticias (consumidor interno, no se enlaza).
Regla: nunca enlazar repos privados; `validar()` lo comprueba.
