# T18 · dev-proyecto v1.2 · Vertical GRC (v0.5.2)

Rama `t18` desde main 90ed848.

## Qué se hizo
- `soc/verticals.yaml`: `VRT-GRC` (nis2: 20.1, 20.2, 21.2.a, 21.2.f; 17 controles existentes: NIS2-20.1/20.2/21.2.a/21.2.d/21.2.f, ENS-org.1-4, ENS-op.pl.1, TRV-GOB-01-03, TRV-RGPD-01-03, TRV-DORA-01), 10 criterios y `niveles` 0-5 comprobables (0 sin política ni análisis; 3 marco documentado, riesgos revisados al año, declaración de aplicabilidad; 5 cuadro de mando revisado por dirección, auditorías sin no conformidades mayores, seguimiento normativo continuo). Sin `recursos`.
- VRT-GRC añadida a la plantilla y a los dos ejemplos ficticios (madurez 3 y 4).
- Informes T09 y T12: nombres de repos privados sustituidos por «un repo privado».
- 20 verticales en README (badge, tabla, árbol, hoja de ruta) y `soc/README.md`; versión 0.5.2 (`pyproject.toml`, `smc/__init__.py`, badge, CHANGELOG); cifra de tests 222.
- `tests/test_t18.py` (8 tests nuevos).

## Verifica
- `uv run --no-project --with pytest --with pyyaml python -m pytest -q` -> 222 passed (214 + 8).
- `smc validate` -> «Catálogos OK». `smc verticals` sobre el ejemplo de energía muestra VRT-GRC evaluada (4); `test_ejemplos_y_plantilla_incluyen_grc_y_agregan_a_nis2_20` comprueba que agrega a NIS2-20.1 y 21.2.a en ambos ejemplos.
- `git grep` de `repo-privado|repo-privado` fuera de `tests/`: sigue habiendo coincidencias en `smc/resources.py` (lista PROHIBIDOS, es la guarda que impide enlazarlos) y en `docs/plan/PLAN.md` (fuera de Toca). Los informes T09/T12 quedan limpios.

## Contraprueba (ejecutada)
Cambiar `ENS-op.pl.1` por `ENS-op.pl.99` en VRT-GRC: 10 failed (test_catalogo_valido, test_todo_controles_existe_en_catalogos, etc.); restaurado, 222 passed. Además `test_contraprueba_control_inexistente_en_grc_falla`, `..._medida_nis2_inexistente...` y `test_contraprueba_sin_grc_no_hay_agregacion_en_20`.

## Cambios en tests previos (justificados)
- Cifra 19 -> 20 en `test_verticals.py` (2) y `test_t17.py` (1).
- `test_ejemplo_energia_valores`: NIS2-21.2.a pasa de 3.0 a 3.33 y de 3.5 a 3.67 porque VRT-GRC (4) puntúa en el ejemplo.
- `test_t08.py::test_version_051` -> `test_version_052`.

## Decisiones y lo que queda
- Los descriptores son criterio inicial, a validar por el Security Manager.
- Decidir si `PROHIBIDOS` en `smc/resources.py` y PLAN.md deben conservar los nombres (el «Verifica» pedía vacío fuera de tests/; no están en Toca, no se tocan).
- Tarea no marcada.
