# T11 — Vulnerabilidades por protocolo y fuentes oficiales

## Qué se hizo
- `vulnerabilities/protocols.yaml`: 28 protocolos (los 22 pedidos más ARP, 802.1X/EAP, ICMP, IPsec/IKE, BGP, DHCP). Por protocolo: `id`, `nombre`, `capa_osi` (2, 3, 6 o 7), `puertos`, `riesgos`, `cwe`, `mitigaciones`, `controles` (IDs existentes NET-*, ENS-*, TRV-*), `attack`, `consulta` (6 URLs) y `aprendizaje` (claves a las Pages). Sin CVEs concretos.
- `vulnerabilities/sources.yaml`: NVD, EUVD, CISA KEV, CVE Details, INCIBE-CERT, CCN-CERT, MITRE CWE y ATT&CK (nombre, organismo, url, tipo, uso).
- `smc/protocols.py`, `tests/test_protocols.py` (16 casos), README de `vulnerabilities/`.
- Ficheros: solo los de «Toca».

## API para T14
```python
from smc import protocols
protocols.cargar() -> dict; protocols.cargar_fuentes() -> list[dict]
protocols.protocolos(data=None) -> list[dict]
protocols.obtener(id) -> dict | None            # sin distinguir mayúsculas
protocols.por_capa() -> dict[int, list[dict]]   # claves ordenadas
protocols.render_protocolo(id) -> str           # Markdown; ValueError si no existe
protocols.validar(data=None, fuentes=None, controles=None) -> list[str]  # [] = OK
```
`smc validate` (T14) debe añadir `errores += protocols.validar()`. `validar` carga los controles con `smc.catalog.load_all()` (import local, sin ciclo). Subcomando previsto `smc protocols [ID]`: sin ID, listar `por_capa()`; con ID, `render_protocolo`. Capturar `ValueError` y salir con rc!=0.

## Verifica
`uv run --no-project --with pytest --with pyyaml python -m pytest -q`: 94 passed (78 previos + 16).
Contraprueba: `test_contraprueba_dominio_no_permitido` (URL a evil.example.com), `..._http_no_https`, `..._control_inexistente`, `..._capa_fuera_de_rango`, y formato CWE/ATT&CK, ID duplicado y fuente de consulta ausente: cada uno pone `validar` en errores. También hay un test que falla si aparece un patrón `CVE-AAAA-NNNN` o un repo privado en el YAML.

## Decisiones y dudas
- Dominios permitidos = hosts de `sources.yaml` + `pedri77.github.io`; añadir una fuente nueva la habilita.
- Capa OSI por convención de la capa de aplicación (TLS = 6, BGP = 7 por ir sobre TCP); discutible.
- Formato de CWE y ATT&CK validado por regex, no contra el catálogo MITRE. Incluí solo IDs de los que estoy seguro; contrastar de todos modos.
- URLs de búsqueda NVD, EUVD, CISA KEV y CVE Details llevan parámetros de consulta recordados de memoria; no verificadas (sin red). EUVD (`/search?text=`) y CVE Details (`google-search-results.php?q=`) son las más dudosas. INCIBE-CERT y CCN-CERT sin filtro por esa razón.
- No se enlazan repos privados ni se toca cli/gap/report/dashboard.

## Queda
Integración en CLI y `smc validate` (T14); verificación humana de las URLs de búsqueda.

## Verificación del coordinador (2026-11-03)
- Verifica: pytest en worktree 94 passed; en main tras fusionar: 133 passed.
- Superficies: OK. Toca: sin ficheros fuera. gitleaks: sin hallazgos.
- Contraprueba: URL modelo_OSI -> evil.example.com -> 3 failed, 91 passed; restaurada, 94 passed.
