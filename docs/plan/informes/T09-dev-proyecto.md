# T09 — Verticales ampliadas y madurez por vertical

Agente: dev-proyecto v1.2 · Rama t09 (desde 8d0a532, v0.4.1)

## Qué se hizo
- `soc/verticals.yaml` pasa a v2: 19 verticales = 12 anteriores (mismos IDs) + VRT-HUNT, VRT-MDM, VRT-ENDUSER, VRT-FW, VRT-SASE, VRT-ZTNA, VRT-OSI. Cada una con `id`, `nombre`, `nis2`, `controles` (IDs existentes), `criterios` concretos, `recursos` y, si procede, `estado_recursos`.
- VRT-NET se conserva como paraguas (`agrupa: [VRT-FW, VRT-SASE, VRT-ZTNA, VRT-OSI]`). Sus criterios "Ver network/controls.yaml" sustituidos por criterios reales. Los "Ver vulnerabilities/" y "Ver resources/external/" de VRT-VULN y VRT-TPRM también.
- `smc/verticals.py` nuevo. `assessments/assessment.template.yaml` y los dos ejemplos ganan la sección `verticales:` (ficticios).
- No se tocó cli, gap, report_html, dashboard.

## Recursos
Solo la lista pública del contexto: EDR (edr-visual-app), FW (Basic_Firewalls), SASE (sase-visual-app), OSI (Basicos_Proteccion_Capas_OSI y modelo_OSI), OT (ics-security-studio), APP (wafforge), MAIL (Basicos_email), VULN (repo kev_dash_project), HUNT (repo threat-intelligence-feeds). Pendientes sin URL (`estado: pendiente`): evaluación de productos ZTNA (VRT-ZTNA), repositorio de vulnerabilidades por capa OSI (VRT-OSI), mapa 3D de dispositivos (VRT-NET). MDM y puesto de usuario sin recursos.

## API para T14 (`from smc.verticals import ...`)
- `cargar_verticales(path=None) -> list[Vertical]` (id, nombre, nis2, controles, criterios, recursos, estado_recursos, agrupa).
- `validar_catalogo(verticales=None) -> list[str]`: errores (IDs duplicados, NIS2/control inexistente, URL fuera de `URLS_PUBLICAS`, `estado_recursos` con URL). Para `smc validate`.
- `evaluar(assessment, estricto=True, verticales=None) -> ResultadoVerticales`:
  - `verticales: list[ResultadoVertical]` (id, nombre, nis2, estado `evaluada|no_evaluable|sin_evaluar`, madurez, motivo, producto, notas), en orden del catálogo.
  - `por_nis2: dict[str, MedidaNIS2]` (medida, madurez media 2 decimales o None, verticales que puntúan, no_evaluables, sin_evaluar).
  - `madurez_media` (media de las que puntúan o None), `no_evaluables`, `sin_evaluar`, `warnings`, `errores`.
  - Entrada `{VRT-ID: {madurez: 0-5 | no_evaluable, motivo, producto, notas}}`. `no_evaluable` sin `motivo` y madurez no válida (no entero 0-5, bool incluido) lanzan `VerticalesError` (subclase de ValueError); con `estricto=False` quedan en `errores` y esa vertical cuenta sin evaluar (útil para `smc validate`). Sección ausente = todo sin evaluar sin avisos; VRT-ID desconocido o sección no mapa = aviso.
- `URLS_PUBLICAS` es la única lista de URLs permitidas.

## Decisiones
- Doble cómputo: si alguna de VRT-FW/SASE/ZTNA/OSI está evaluada, VRT-NET no puntúa (ni en medidas ni en la media); si ninguna, VRT-NET puntúa solo. Cubierto por test.
- Los `no_evaluable` de una medida se listan en esa medida pero no cambian su media.
- Mapeo NIS2 y `controles` de las verticales nuevas es juicio inicial, sin fuente normativa (revisión humana).
- README y `soc/README.md` aún dicen "12 verticales": fuera de «Toca», a corregir en T14/cierre de ola.

## Verifica
- `uv run --no-project --with pytest --with pyyaml python -m pytest -q`: 106 passed (78 previos + 28 nuevos).
- Cubierto: controles existentes en catálogos; URLs dentro de la lista (copia literal en el test, independiente del módulo); agregación NIS2 en un caso a mano (21.2.g = 7/3 = 2.33); `no_evaluable` sin motivo da error; ejemplos y plantilla pasan `analyse` y `evaluar`.

## Contraprueba
Cambiando en `soc/verticals.yaml` la URL de wafforge por `https://github.com/pedri77/repo-privado` (repo privado): 3 tests en rojo (`test_catalogo_valido`, `test_urls_dentro_de_la_lista_publica`, `test_url_fuera_de_la_lista_pone_rojo` pasa a rojo por la línea final). Revertido. También hay contraprueba en memoria (URL privada inyectada en `validar_catalogo`) y para el doble cómputo de VRT-NET.

## Queda
Integración (cli/informes/dashboard) en T14; corregir cifra "12 verticales" en README.

## Verificación del coordinador (2026-11-03)
- Verifica: pytest en worktree 106 passed; en main tras fusionar: 106 passed.
- Superficies: OK. Toca: sin ficheros fuera. gitleaks: sin hallazgos.
- Contraprueba: URL de wafforge -> repo privado repo-privado -> 3 failed, 103 passed; restaurada, 106 passed.
