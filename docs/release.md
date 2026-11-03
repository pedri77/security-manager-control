# Política de versiones y release

SMC sigue [versionado semántico](https://semver.org/lang/es/) `MAJOR.MINOR.PATCH`.

## Qué sube cada número

- **Mayor (X.0.0)**: cambio incompatible. Renombrar o quitar IDs de controles de los catálogos, cambiar el formato de las evaluaciones o de los ficheros de entrada de forma que los existentes dejen de cargar, quitar o cambiar el significado de opciones de la CLI.
- **Menor (0.X.0)**: funciones o catálogos nuevos compatibles: nuevos comandos o flags, nuevos marcos u obligaciones, campos opcionales nuevos, nuevas secciones de informe.
- **Parche (0.0.X)**: correcciones sin función nueva: fallos, endurecimiento, erratas en catálogos que no cambian IDs, documentación.

Mientras la versión mayor sea 0, los cambios incompatibles pueden ir en una menor, pero se anotan en el CHANGELOG como «Incompatible».

## Checklist de release

1. Rama de trabajo limpia y al día con `main`.
2. Tests: `uv run --extra dev pytest -q` en verde.
3. Catálogos: `uv run smc validate` sin errores.
4. `gitleaks git` sin hallazgos y grep de secretos en lo que sube.
5. Revisar que no aparecen nombres de repos privados ni datos reales de clientes en README, docs, ejemplos ni CHANGELOG.
6. CHANGELOG: nueva entrada `## X.Y.Z (AAAA-MM-DD)` arriba del todo.
7. Versión igual en `pyproject.toml`, `smc/__init__.py` y la última entrada del CHANGELOG (lo comprueba `tests/test_version.py`).
8. Commit de release en `main`.
9. Tag anotado: `git tag -a vX.Y.Z -m "SMC X.Y.Z"`.
10. El push de `main` y del tag (`git push origin vX.Y.Z`) lo hace David.

No se publica en PyPI.

## CI

`.github/workflows/tests.yml` corre en cada push y pull request a `main` (Python 3.11 y 3.12): tests, `smc validate` y los comandos de ejemplo del README con la salida en un directorio temporal. Permisos `contents: read`, sin secretos, y las acciones fijadas por SHA de commit con el tag en comentario. Para actualizar una acción, resolver el SHA del nuevo tag con `gh api repos/<dueño>/<repo>/git/ref/tags/<tag>` (desreferenciar si el tag es anotado) y cambiar SHA y comentario a la vez.
