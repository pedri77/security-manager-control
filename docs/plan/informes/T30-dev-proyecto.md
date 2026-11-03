# T30 - CI en GitHub Actions y política de versiones

## Qué se hizo
- `.github/workflows/tests.yml`: push y PR a `main`, matriz Python 3.11/3.12, `permissions: contents: read`, `persist-credentials: false`. Pasos: `uv run --extra dev pytest -q`, `uv run smc validate` y los comandos del README (gap, report, dashboard, mapa, visor) con salida en `$RUNNER_TEMP/smc`.
- Acciones fijadas por SHA (consultados con `gh api`, ambos tags son commits directos, no anotados):
  - actions/checkout v5 = fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 (v4 = 11d5960a326750d5838078e36cf38b85af677262, no usado)
  - astral-sh/setup-uv v10.3.3 (última release) = 68559e99cc807c1eb7e9238fd43a15bba460eec2
- `docs/release.md`: semver, qué sube cada número, checklist (tests, validate, gitleaks, repos privados, CHANGELOG, versión triple, tag anotado, push de David), nota de mantenimiento de SHAs.
- `tests/test_version.py` (6 tests): versión de pyproject = `smc.__version__` = última entrada del CHANGELOG; semver; workflow con permisos mínimos, triggers, matriz, acciones con SHA de 40 hex, y que ejecuta pytest y validate.

## Verificación
- `uv run --extra dev pytest -q`: 533 passed.
- Comandos de ejemplo del workflow ejecutados en local contra un tempdir: rc=0 y ficheros generados.

## Contraprueba
- `__version__ = "0.7.2"` en `smc/__init__.py`: `test_versiones_coinciden` en rojo (1 failed, 5 passed). Revertido.
- `checkout@v5` sin SHA: `test_workflow_acciones_fijadas_por_sha` en rojo. Revertido.

## Dudas / notas
- El workflow no se ha ejecutado en GitHub (sin push). No se puede confirmar hasta el primer push; setup-uv v10.3.3 tomado de la última release por API.
- `smc validate` y demás usan `uv run smc` (el paquete se instala del proyecto por defecto). `uv.lock` no incluido en el commit.
- PyYAML interpreta `on:` como `True`; el test lo contempla.
