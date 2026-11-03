# T13 — Madurez MITRE ATT&CK con playbooks

Rama `t13` (desde main 8d0a532). 87 tests verdes (78 previos + 9 nuevos).

## Hecho
- `soc/use-cases/catalog.yaml`: cada caso lleva `deteccion` (sin|regla|probada), `ultima_prueba`, `playbook` y `vertical` (solo IDs existentes de `soc/verticals.yaml`). Técnicas ATT&CK ya presentes (no se añadieron IDs nuevos).
- 7 playbooks nuevos `PB-UC-002..008` en `vulnerabilities/playbooks/caso-uso/` (castellano, genéricos, fases detección/contención/erradicación/recuperación/lecciones, sección NIS2 24 h / 72 h / 1 mes).
- `smc/mitre.py` nuevo; `smc/soc.py:mitre_coverage(uc_path, hoy=None)` mantiene su salida y añade tabla de madurez por técnica; "sin playbook" ahora exige que el fichero exista.

## API para T14 (`smc.mitre`)
- `madurez(uc_path=UC_FILE, hoy=None, root=ROOT) -> {"tecnicas": {id: 0-5}, "tacticas": {nombre: 0-5}, "casos": {UC: 0-5}}`
- `nivel_caso(u, hoy, root)`, `cargar(uc_path)` (excluye `retirado`), `playbook_existe(u, root)`
- `sin_playbook(uc_path, root) -> [UC-ids]`, `playbooks_huerfanos(uc_path, root) -> [rutas relativas]`
- `a_navigator(uc_path, hoy, root, nombre) -> dict` (name, versions, domain=enterprise-attack, description, gradient 0-5, techniques[{techniqueID, score, comment}]); serializar con `json.dumps`.
- `hoy` es `datetime.date`; `None` = hoy real.

## Niveles
1 caso sin regla · 2 regla (o probada sin playbook existente) · 3 regla + playbook que existe · 4 probada · 5 probada en ≤90 días (inclusive). Técnica y táctica = máximo de sus casos; los `retirado` no cuentan; la táctica es la del caso.

## Decisiones / supuestos
- Valores `deteccion` del catálogo de ejemplo: UC-001 probada (única con prueba, 2026-09-15); UC-002/003/004/006/007 regla; UC-005 y UC-008 sin. Es juicio sobre datos de muestra, no un SOC real.
- Estados `propuesto`/`en_desarrollo` cuentan como caso (nivel según `deteccion`).
- Versión ATT&CK del export fijada en "16" (editable en `a_navigator`); sin red para verificar la última.
- No se tocó cli.py: `smc mitre` sigue igual; el export Navigator en CLI y el informe quedan para T14.

## Verifica
- `uv run --no-project --with pytest --with pyyaml python -m pytest -q` → 87 passed.
- Contraprueba: mover `PB-UC-004-volcado-lsass.md` fuera pone en rojo `test_playbooks_referenciados_existen`; restaurado vuelve a verde.

## Verificación del coordinador (2026-11-03)
- Verifica: pytest en worktree 87 passed; en main tras fusionar: 151 passed.
- Superficies: OK. Toca: sin ficheros fuera. gitleaks: sin hallazgos.
- Contraprueba: mover PB-UC-004-volcado-lsass.md fuera -> 1 failed, 86 passed; restaurado, 87 passed.
