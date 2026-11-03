# T26 · dev-proyecto · RIA (Reglamento (UE) 2024/1689) y seguridad de agentes de IA

Rama t26-v07. Tests: 391 verdes (`uv run --extra dev pytest -q`; 363 en la base + 28 nuevos en `tests/test_ai_act.py`). `smc validate`: «Catálogos OK» (no valida aún `frameworks/ai-act/`: lo integra T28).

Ficheros: `frameworks/ai-act/obligaciones.yaml` (30 obligaciones), `ai/inventario.template.yaml` (3 sistemas y 2 agentes ficticios), `smc/ai_act.py`, `tests/test_ai_act.py`.

No es asesoramiento jurídico: el render lo dice en un aviso al principio.

## Fuentes (consulta 2026-11-03)

| Fuente | URL | Cómo se leyó |
|---|---|---|
| RIA, Reglamento (UE) 2024/1689 | https://eur-lex.europa.eu/eli/reg/2024/1689/oj | EUR-Lex devolvió HTTP 202 sin cuerpo (curl y WebFetch; firecrawl también falló). Se leyó la copia del DOUE en el BOE: https://www.boe.es/buscar/doc.php?id=DOUE-L-2024-81079 (texto original, no consolidado) |
| Ómnibus digital sobre IA, Reglamento (UE) 2026/1744 | https://eur-lex.europa.eu/eli/reg/2026/1744/oj | PDF del DOUE (DO L de 24.7.2026) en el BOE: https://www.boe.es/doue/2026/1744/L00001-00041.pdf, con `pdftotext` |
| Nota del Consejo de 2026-05-07 | https://www.consilium.europa.eu/en/press/press-releases/2026/05/07/artificial-intelligence-council-and-parliament-agree-to-simplify-and-streamline-rules/ | HTTP 403. No hizo falta: el texto publicado en el DOUE manda |
| OWASP Top 10 for LLM Applications 2025 | https://genai.owasp.org/llm-top-10/ | Web: LLM01:2025 a LLM10:2025; fichas de LLM06 y LLM10 para las mitigaciones (registro, límite de llamadas, aprobación humana) |
| MITRE ATLAS | https://atlas.mitre.org/ | La web es una SPA (404 sin JS). IDs contrastados con los datos oficiales: https://github.com/mitre-atlas/atlas-data, `dist/v6/ATLAS-2026.10.yaml` (221 técnicas) |

## Fechas: el Ómnibus en el DOUE

- Art. 4 del Ómnibus: entra en vigor «a los tres días de su publicación» (DO L 24.7.2026), es decir, el 2026-07-27. Coincide con las fuentes secundarias.
- Punto 40 (art. 113 RIA, párrafo tercero): letra c) capítulo III, secciones 1, 2 y 3 (salvo art. 6.5) desde 2027-12-02 (art. 6.2 y Anexo III) y 2028-08-02 (art. 6.1 y Anexo I); letra a) capítulos I y II desde 2025-02-02, salvo el art. 5.1 b bis) y b ter) y 5.1 bis y 1 ter, desde 2026-12-02; nueva letra d) arts. 102 a 110 desde 2026-07-27.
- Punto 39 b) (nuevo art. 111.4 RIA): los proveedores de sistemas que generan contenido sintético y estaban en el mercado antes de 2026-08-02 cumplen el art. 50.2 a más tardar el 2026-12-02 (considerando 38: «período transitorio de cuatro meses»).
- **Art. 50: resuelto, sin `verificar`.** El Ómnibus solo cambia su apartado 7 (códigos de buenas prácticas, punto 20) y no lo saca de la fecha general. El art. 50 aplica desde 2026-08-02 (fecha general del art. 113 RIA); solo el marcado del art. 50.2 de sistemas ya en el mercado antes de esa fecha se aplaza al 2026-12-02. De las dos lecturas de las fuentes secundarias, la correcta es esa.
- Punto 5: el art. 4 (alfabetización) pasa a «adoptarán medidas para apoyar la promoción de la alfabetización» y «no exige […] un nivel específico». La fecha (2025-02-02) no cambia.

## Fechas originales del art. 113 RIA (contrastadas)

«Será aplicable a partir del 2 de agosto de 2026», salvo: a) capítulos I y II desde 2025-02-02 (prohibiciones art. 5 y alfabetización art. 4); b) capítulo III sección 4, capítulos V, VII y XII y art. 78 desde 2025-08-02 (salvo art. 101); c) art. 6.1 desde 2027-08-02. La c) original la sustituye el Ómnibus. Art. 111.3: modelos de uso general en el mercado antes de 2025-08-02, a más tardar 2027-08-02.

## Obligaciones del catálogo

| ID | Artículo | Rol | Nivel | Fecha vigente | Fuente de la fecha | verificar |
|---|---|---|---|---|---|---|
| AIA-001 | art. 4 | proveedor, responsable | todos salvo prohibido y modelos de uso general | 2025-02-02 | RIA art. 113 a); texto Ómnibus punto 5 | no |
| AIA-002 | art. 5 | los cuatro | prohibido | 2025-02-02 | RIA art. 113 a) | no |
| AIA-003 | art. 5.1 b bis) y b ter) | los cuatro | prohibido (supuesto) | 2026-12-02 | Ómnibus punto 40 a) | no |
| AIA-010 a 017 | arts. 9, 10, 11, 12, 13, 14, 15, 16-17 | proveedor | alto riesgo | Anexo III 2027-12-02 · Anexo I 2028-08-02 | Ómnibus punto 40 b) | no |
| AIA-018 | arts. 43, 47, 48 | proveedor | alto riesgo | ídem | Ómnibus (por coherencia) | **sí** |
| AIA-019 | art. 49.1 | proveedor | Anexo III | 2027-12-02 | ídem | **sí** |
| AIA-020 | arts. 72, 73 | proveedor | alto riesgo | ídem | ídem | **sí** |
| AIA-030 | art. 23 | importador | alto riesgo | ídem | Ómnibus punto 40 b) | no |
| AIA-031 | art. 24 | distribuidor | alto riesgo | ídem | Ómnibus punto 40 b) | no |
| AIA-040 a 044 | art. 26.1, 26.2, 26.5, 26.6, 26.7 | responsable | alto riesgo | ídem | Ómnibus punto 40 b) | no |
| AIA-045 | art. 27 | responsable | Anexo III (supuesto) | 2027-12-02 | Ómnibus punto 40 b) | no |
| AIA-046 | art. 49.3 | responsable | Anexo III (organismo público) | 2027-12-02 | ídem | **sí** |
| AIA-050 | art. 50.1 | proveedor | sistemas (supuesto) | 2026-08-02 | RIA art. 113 | no |
| AIA-051 | art. 50.2 | proveedor | sistemas (supuesto) | 2026-08-02; en el mercado antes: 2026-12-02 | Ómnibus punto 39 b) | no |
| AIA-052, 053 | art. 50.3, 50.4 | responsable | sistemas (supuesto) | 2026-08-02 | RIA art. 113 | no |
| AIA-060 a 062 | arts. 53, 54, 55 | proveedor | uso general (55 solo riesgo sistémico) | 2025-08-02; en el mercado antes: 2027-08-02 | RIA art. 113 b) y 111.3 | no |

Todas las fuentes: RIA https://eur-lex.europa.eu/eli/reg/2024/1689/oj y Ómnibus https://eur-lex.europa.eu/eli/reg/2026/1744/oj, consulta 2026-11-03.

## Qué queda en `verificar` y por qué

4 obligaciones (AIA-018, 019, 020, 046). El art. 113 c) modificado solo retrasa las **secciones 1, 2 y 3** del capítulo III. La evaluación de la conformidad, la declaración UE, el marcado CE y el registro (arts. 43, 47, 48, 49, sección 5) y la vigilancia poscomercialización y los incidentes (arts. 72 y 73, capítulo IX) no están entre las excepciones: en lectura literal aplicarían desde el 2026-08-02. Se usa la fecha del nivel (2027-12-02 o 2028-08-02) porque esas obligaciones recaen sobre sistemas cuyos requisitos aún no aplican, pero no lo he encontrado dicho de forma expresa en el texto. Pendiente de orientaciones de la Comisión o de revisión humana.

Fuera del catálogo, sin modelar: el art. 111.2 (sistemas de alto riesgo ya en el mercado antes de la fecha del capítulo III solo quedan sujetos si cambian de diseño de forma significativa; los de autoridades públicas, a más tardar el 2030-08-02). Lo dice la nota del informe; el inventario no tiene campo para «cambio significativo».

## Seguridad de agentes (`riesgos_agente`)

| ID | Comprobación | OWASP | ATLAS (técnicas) | ATLAS (mitigaciones) |
|---|---|---|---|---|
| AGT-01 | herramienta sin `limite_llamadas` | LLM10:2025, LLM06:2025 | AML.T0034 Cost Harvesting, AML.T0034.002 Agentic Resource Consumption, AML.T0029 Denial of AI Service | AML.M0036, AML.M0004 |
| AGT-02 | permisos sensibles sin aprobación o sin mínimo privilegio | LLM06:2025 | AML.T0053 AI Agent Tool Invocation, AML.T0101 Data Destruction via AI Agent Tool Invocation | AML.M0028, AML.M0026, AML.M0037 |
| AGT-03 | sin supervisión humana | LLM06:2025 («Require user approval») | AML.T0053 | AML.M0029 Human In-the-Loop for AI Agent Actions |
| AGT-04 | sin registro | LLM06:2025 y LLM10:2025 (mitigación «Log and monitor») | ninguna (es una carencia de control, no una técnica) | AML.M0024 AI Telemetry Logging and Monitoring |
| AGT-05 | entrada no confiable sin mitigación de prompt injection | LLM01:2025 | AML.T0051 LLM Prompt Injection, AML.T0051.001 Indirect | AML.M0020, AML.M0030, AML.M0033 |
| AGT-06 | datos personales + entrada no confiable + salida a red sin aprobación | LLM02:2025, LLM01:2025, LLM06:2025 | AML.T0086 Exfiltration via AI Agent Tool Invocation | AML.M0030, AML.M0028 |

Todos los IDs existen en `ATLAS-2026.10.yaml` y en la lista OWASP 2025. Un dato ausente cuenta como «no consta» (hallazgo), nunca como cumplido.

## Verifica y contraprueba real

- `hoy` inyectado antes (2027-12-01) y después (2027-12-02) de la fecha del Anexo III: AIA-041 pasa de «aplicable desde 2027-12-02» a «vigente»; Anexo I sigue «aplicable desde 2028-08-02».
- Alto riesgo sin supervisión humana: AIA-041 queda **pendiente** y figura en `incumplidas` tras 2027-12-02; con `supervision_humana: {existe: true}` pasa a cumplida; ausente = pendiente.
- Nivel de riesgo inexistente: `clasificar` y `obligaciones` lanzan `AIActError`; con `estricto=False` va a `errores` y `no_clasificados`.
- Mutaciones ejecutadas sobre `smc/ai_act.py` (restaurado después, `diff` limpio):

| Mutación | Resultado |
|---|---|
| `hoy >= fecha` cambiado a `hoy > fecha` | 2 en rojo |
| `_evidencia` siempre verdadera | 4 en rojo (entre ellos la contraprueba de supervisión) |
| `clasificar` sin validar el nivel | 2 en rojo |
| transitorio aplicado siempre | 1 en rojo |
| `gap.md_texto` sin escape | 1 en rojo (XSS en el nombre del sistema) |

## Decisiones

- `obligaciones(..., estricto=True)` sigue el patrón de `verticals.evaluar`: el nivel o el rol inexistentes son error de esquema; lo demás mal formado (supuestos que no son lista, fecha inválida, `sistemas` de texto) da aviso.
- Cumplimiento por evidencia del inventario (`supervision_humana`, `registro`, `alfabetizacion`, ...): `cumplida`, `pendiente` (falso o ausente) o `no_comprobable` (la obligación no tiene campo de evidencia).
- Sin `en_mercado_desde`, los periodos transitorios usan la fecha general (la más temprana) con aviso: conservador.
- Nivel «transparencia» sin `supuestos`: se aplican las cuatro obligaciones del art. 50 con aviso.
- Un modelo de uso general declarado sin rol `proveedor` es error: el capítulo V solo obliga al proveedor del modelo; quien lo integra es proveedor o responsable de un sistema.
- Art. 4 y art. 50 no se aplican a los niveles de modelo (`uso_general*`): el texto habla de sistemas de IA.
- Reutiliza `gap.md_texto` para el escape Markdown (`|`, `<`, `>`).

## Para T28

- `.gitignore` no ignora inventarios reales fuera de `assessments/` (no estaba en el «Toca»): la plantilla dice copiarlos a `assessments/<cliente>/ia.yaml`, que sí está ignorado.
- `smc validate` debe sumar `ai_act.validar_catalogo()` y `ai_act.validar_inventario(INVENTARIO_TEMPLATE)`.
- `uv.lock` quedó sin versionar (no es del «Toca»).
