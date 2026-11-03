# Olas 12-13 · revisor-ola · revisión T24-T28 (e126a88..c9fd41a)

Veredicto: APTA con reservas. 509 tests verdes. Hashes de «hecha en» verificados. Commits con email noreply. Sin nombres de repos privados en árbol ni historial del rango. Ejemplos ficticios. Escape HTML probado con `<img onerror>` en PMO, pentest, purple e IA (16 escapes, 0 crudos); `.ics` sin inyección de propiedades (CRLF, plegado ≤ 75 octetos). Seis obligaciones RIA contrastadas con el Ómnibus (PDF del BOE): AIA-001, 003, 010, 050, 051, 060 correctas. (Informe transcrito por el coordinador: el revisor no puede escribir ficheros.)

## Hallazgos
1. [V] media · T28 · `smc/mitre.py` (`pruebas_purple`/`nivel_caso`): un ejercicio `detectado` sube la madurez del caso aunque la técnica no sea de ese caso (UC-002 con T1003 pasa a 5).
2. [V] media · T28 · `smc/mitre.py:52-66`: cuenta el último `detectado` aunque haya un `no_detectado` posterior; contradice `purple().no_detectadas`.
3. [V] media · T24 · `smc/offensive.py:278,289`: hallazgo `corregido` con retest `persiste`/`parcial` desaparece de todas las listas.
4. [V] media · T26 · `frameworks/ai-act/obligaciones.yaml`: falta el nuevo art. 111.2 (sistemas de alto riesgo ya en el mercado: solo con cambios significativos; autoridades públicas a más tardar 2030-08-02).
5. [V] baja · T27/T28 · `.gitignore`: `*.ics` no ignorado aunque `docs/pmo.md` dice que no se versiona.
6. [V] baja · T27 · `smc/pmo.py:247` y `380-383`: AC incluye costes no laborales de la tarea y el BAC por defecto no; CPI sesgado. Documentado; falta aviso.
7. [V] baja · T25: plan pedía 24 verticales, se entregaron 22 (fusión decidida por el coordinador, sin anotar); informe T25 contradictorio.
8. [V] baja · fuera de «Toca»: T25 `tests/test_t17.py`; T28 `smc/soc.py`, `smc/resources.py`, `tests/test_resources.py`, `resources/ecosistema.yaml`, `.gitignore` (justificado en su informe).
9. [D] baja · T26 · `smc/ai_act.py:373-383`: AML.T0101, AML.M0036, AML.M0037 bien formados, existencia en ATLAS sin comprobar.
10. Nota: T26 consultó red (BOE, EUR-Lex) por encargo de su «Hace»; excepción a anotar.

Sin revisar: `smc/catalog.py validar_v07`, rutas de error de `smc/cli.py`, `riesgos_agente` en detalle.

Tareas a reabrir: ninguna. Hallazgos 1-6 y 9 van a T29.
