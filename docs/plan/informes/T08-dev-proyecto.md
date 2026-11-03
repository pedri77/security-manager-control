# T08 · dev-proyecto · Endurecer v0.4 antes de publicar

Rama `t08` (desde 488d086). Versión 0.4.1. Tests: 78 verdes (65 previos + 13 nuevos; ninguno de los previos cambió de resultado con la recalibración; solo se endureció la aserción del hallazgo 12).

## Qué se hizo, un test por hallazgo (`tests/test_t08.py`) y contraprueba

Contraprueba general: se apartó el código (`git stash` de `smc/`, `frameworks/`, `.gitignore`) con los tests nuevos puestos: 12 en rojo (todos los de T08), y vuelven a verde al restaurar. Detalle:

| H | Cambio | Test | Contraprueba |
|---|---|---|---|
| 1 | `gap.py`: estado no válido = sin evaluar (aplicable, 0) + aviso | `test_h1_*` | con el código viejo, aplicables baja y el % sube: rojo |
| 2 | Medidas `verificar` marcadas «(verificar)» en MD y HTML y aviso en el resumen (`Analisis.ens_verificar`) | `test_h2_*` | sin ENS en alcance no hay aviso; código viejo: AttributeError |
| 3 | `.gitignore`: `*.html`, `dashboard/` | `test_h3_*` (usa `git check-ignore`) | README.md no se ignora; sin la regla, rojo |
| 4 | `priority.py` recalibrada (ver Decisión) | `test_h4_*` | esencial/alta siguen P1; con 60/20/10/10 media-importante sería P1 |
| 5 | `verificar: true` en op.cont.2 y op.cont.3 | `test_h5_h6_*` | cuenta == 39 |
| 6 | Recuento con PyYAML | idem | idem |
| 7 | `categoria_minima` desconocida = BASICA; `validate` la rechaza (también claves de refuerzos) | `test_h7_*` | ALTA sigue sin aplicar en BASICA; catálogo real valida OK |
| 8 | `plan_accion` de texto, entrada de plan/evaluación no mapa, `cliente: null`, `evaluaciones` de texto, evaluación None: aviso, sin AttributeError | `test_h8_*` | evaluación bien formada no da avisos de forma |
| 9 | Dashboard ignora `*.template.yaml` | `test_h9_*` | con otro nombre sí se procesa |
| 10 | Cabecera MD/HTML usa `an.categoria_ens` (ENS en alcance) | `test_h10_*` | sin proveedor no aparece |
| 11 | `bloqueada` y `hecha` no cubren (`plan.NO_CUBREN`) | `test_h11_*` (2) | pendiente/en_curso sí cubren |
| 12 | Dashboard: `en.p1 == 5 and en.p1_sin_accion == 1` e ID `NIS2-23.notificacion` | `test_ayuntamiento_datos` | valor exacto, no `>= 0` |

Medidas `verificar` con PyYAML: **39 de 73** tras añadir op.cont.2/3 (eran 37 antes; el 39 anterior venía de un grep que contaba comentarios, por casualidad coincide). Corregido el texto en README, PRD y CHANGELOG (0.4.1), `pyproject.toml` y `smc/__init__.py` a 0.4.1. No marcado en PLAN.md ni Libro (lo hace el coordinador); la cifra del Libro (T01 dice 39 «incluye los 11 refuerzos») debe reescribirse: la cifra real es 37 + 2.

## Decisiones

- **Prioridad v0.4.1** = 50·estado + 30·criticidad + 10·entidad + 10·cobertura; P1 >= 75, P2 >= 40. Estado: no_implementado 1, sin evaluar 0.75, parcial 0.5. Entidad: esencial 1, importante 0.5, otra 0. Resultados: no_implementado media + importante/no obligada sin cobertura multinorma = 70 / 65 (P2); alta + esencial >= 90 (P1); media + esencial = 75 (P1). Media con cobertura multinorma (n=3) en importante llega a 80 (P1): coherente con «sin cobertura multinorma» de la consigna. TRANSVERSAL y RED (sin criticidad ni mapeo) son P1 solo en esencial. Documentado en el docstring de `priority.py`, README y CHANGELOG. «Sin evaluar» queda en 0.75 (37.5 puntos): ahora casi todo sin evaluar es P2 y P1 solo con criticidad alta + esencial.
- **Hallazgo 11**: `bloqueada` no cubre en ningún cómputo (`brechas_sin_accion` y por tanto `p1_sin_accion`), no solo en P1, para no tener dos criterios. Es un cambio de comportamiento respecto a T03 (registrado en el Libro como «una acción hecha no cubre»; ampliar).
- `categoria_minima` desconocida = BASICA (aplica en todas las categorías, lo conservador); la categoría del cliente desconocida sigue siendo ALTA con aviso. Constante duplicada `CATEGORIAS_ENS` en `catalog.py` para evitar importación cruzada; un test comprueba que coincide con `ens.CATEGORIAS`.
- El aviso ENS de verificar no entra en `warnings` (para no ensuciar los avisos de datos), sino como nota en el resumen.
- Hallazgo 5 (contraste real de op.cont.2/3, mp.si.2, numeración mp.info) y 14 quedan fuera: requieren BOE / decisión humana.

## Verificación

- `uv run --no-project --with pytest --with pyyaml python -m pytest -q`: 78 passed.
- Comandos del README (validate, list, gap, plan, report, dashboard, refs, mitre, expiring, vulns, soc) ejecutados sobre los ejemplos con salidas en un directorio temporal: todos OK, 0 avisos en el dashboard; el informe MD lleva 39 marcas «verificar».
- `gitleaks git --staged`: sin fugas. Sin red, sin dependencias nuevas, sin push.

## Lo que queda

Hallazgos 5 (contraste con BOE), 13 y 14; actualizar Libro/PLAN (cifra 37+2, prioridad, `bloqueada`).
