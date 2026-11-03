# T12: Catálogo de RSS y ecosistema de recursos

## Qué se hizo
- `resources/rss.yaml`: 15 feeds (INCIBE-CERT x2, CCN-CERT, ENISA, CISA x2, NVD, CERT-EU, NCSC UK, BSI, MITRE ATT&CK, Microsoft MSRC, Cisco, Fortinet, Palo Alto). Todos `verificado: false`. Solo 6 llevan `url_feed` (los que se conocen con seguridad: CISA advisories, NCSC UK, MSRC, Cisco, Fortinet, Palo Alto); el resto `url_feed: null` con la página de avisos en `url_web`.
- `resources/ecosistema.yaml`: 8 Pages, 2 repos públicos sin Pages, 3 pendientes (`ECO-ZTNA`, `ECO-VULN-OSI`, `ECO-MAPA3D`) con `estado: pendiente` y `url: null`. El mapa 3D cita el origen: elvarofficial/teardown (MIT) sobre whaleyxbt/claude-motion (MIT). Sin URLs de repos privados; el agregador interno solo se menciona como consumidor en un comentario, sin nombre ni URL.
- `smc/resources.py` y `resources/README.md`.
- `tests/test_resources.py`: 9 tests. Suite: 87 verdes (78 + 9).

## API para T14 (`from smc import resources`)
- `cargar_rss() -> list[dict]`, `cargar_ecosistema() -> list[dict]`
- `validar(rss=None, eco=None) -> list[str]` (vacía = correcto). Para `smc validate`: añadir sus errores a la lista.
- `a_opml(feeds=None, titulo=...) -> str`: OPML 2.0, un outline por feed con `url_feed` (los null se omiten). Atributos escapados. Para `smc rss --opml -o`.
- `render_markdown(rss=None, eco=None) -> str`: tablas de feeds y lista de ecosistema. Para `smc rss` y enlaces en informe.
- Constantes: `CATEGORIAS`, `TIPOS_ECO`, `ESTADOS_ECO`, `PROHIBIDOS`, `RSS_FILE`, `ECO_FILE`.
- Campo `vertical` opcional en RSS (VRT-EDR, VRT-NET): ids actuales; T09 los mantiene. T14 puede validarlos contra `soc/verticals.yaml`.
- Nota: `render_markdown` no escapa el texto (salida Markdown, no HTML); si T14 lo mete en HTML debe usar `html.escape`.

## Verifica
`uv run --no-project --with pytest --with pyyaml python -m pytest -q`: 87 passed. OPML parsea con xml.etree y tiene un outline por feed con url_feed. Ids únicos. Sin repos privados.

## Contraprueba
Cambiar la `url_web` de un feed a `un repo privado`: 2 tests en rojo (`test_datos_validos`, `test_ningun_repo_privado`). Revertido, 87 verdes. `test_contraprueba_repo_privado_en_rojo` cubre también un repo privado en el ecosistema.

## Decisiones y pendiente
- El OPML solo incluye feeds con `url_feed`; "un outline por feed" se cumple para ellos. Si se prefiere incluir los null, habría que dar una URL.
- Pendiente humano: comprobar con red cada `url_feed` y averiguar las rutas de los 9 feeds con `null`, luego poner `verificado: true`. NVD ya no ofrece un RSS fiable (por eso null).

## Verificación del coordinador (2026-11-03)
- Verifica: pytest en worktree 87 passed; en main tras fusionar: 142 passed.
- Superficies: OK. Toca: sin ficheros fuera. gitleaks: sin hallazgos.
- Contraprueba: url_web de RSS-INCIBE-AVISOS -> un repo privado -> 2 failed, 85 passed; restaurada, 87 passed.
