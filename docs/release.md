# Política de versiones y release

SMC sigue [versionado semántico](https://semver.org/lang/es/) `MAJOR.MINOR.PATCH`.

## Qué sube cada número

- **Mayor (X.0.0)**: cambio incompatible. Renombrar o quitar IDs de controles de los catálogos, cambiar el formato de las evaluaciones o de los ficheros de entrada de forma que los existentes dejen de cargar, quitar o cambiar el significado de opciones de la CLI.
- **Menor (0.X.0)**: funciones o catálogos nuevos compatibles: nuevos comandos o flags, nuevos marcos u obligaciones, campos opcionales nuevos, nuevas secciones de informe.
- **Parche (0.0.X)**: correcciones sin función nueva: fallos, endurecimiento, erratas en catálogos que no cambian IDs, documentación.

Mientras la versión mayor sea 0, los cambios incompatibles pueden ir en una menor, pero se anotan en el CHANGELOG como «Incompatible».

## Flujo de release

Todo cambio entra por PR a `main`: push directo bloqueado, también para administradores. El título y los commits siguen conventional commits y llevan `Closes #N` y `Task: SMC-NNN`.

1. Cada PR pasa el CI y la revisión ciega (estado `blind-review`).
2. Al fusionar un `feat`, `fix`, `sec` o `perf`, release-please abre o actualiza el PR de release: calcula la versión, escribe el CHANGELOG y sube la versión en `pyproject.toml` y `smc/__init__.py` (lo comprueba `tests/test_version.py`).
3. Antes de fusionar el PR de release, David revisa que no aparecen nombres de repos privados ni datos reales de clientes en README, docs, ejemplos ni CHANGELOG. release-please no lo cubre.
4. Fusionar ese PR es el gate humano: crea el tag y la release, y `release.yml` adjunta SBOM firmado y evidence pack.

No se publica en PyPI.

## CI

`.github/workflows/ci.yml` y `pr-meta.yml` son los gates del playbook feature-to-prod: secretos, SAST, dependencias, ficheros, trazabilidad y SBOM.

`.github/workflows/tests.yml` corre en cada push y pull request a `main` (Python 3.11 y 3.12): tests, `smc validate` y los comandos de ejemplo del README con la salida en un directorio temporal. Permisos `contents: read`, sin secretos, y las acciones fijadas por SHA de commit con el tag en comentario. Para actualizar una acción, resolver el SHA del nuevo tag con `gh api repos/<dueño>/<repo>/git/ref/tags/<tag>` (desreferenciar si el tag es anotado) y cambiar SHA y comentario a la vez.
