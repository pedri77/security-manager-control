"""Madurez MITRE ATT&CK de los casos de uso y export a ATT&CK Navigator.

Niveles por caso de uso:
  0 sin caso | 1 caso sin regla | 2 regla (o probada sin playbook) |
  3 regla + playbook existente | 4 probada | 5 probada en los últimos 90 días.
Por técnica se toma el máximo de sus casos (retirados excluidos).
Por táctica se toma el MÍNIMO de sus casos activos (`estado: activo`): el máximo ocultaba huecos.
Los casos no activos (en_desarrollo, propuesto) no cuentan para la táctica y se devuelven aparte
en `no_activos`; una táctica sin casos activos no aparece en `tacticas`.

Ejercicios purple team (v0.7, decisión de T28): si se pasa el resultado de cargar un fichero purple
(`purple=` en `madurez`/`a_navigator`, `--purple` en la CLI y en `smc report`), un ejercicio con resultado
`detectado` y fecha válida cuenta como prueba del caso de uso (equivale a `deteccion: probada` con
`ultima_prueba` = el ejercicio detectado más reciente, nunca posterior a `hoy`): nivel 4, y 5 si esa fecha
está en los últimos 90 días. Como en la prueba declarada, el caso necesita su playbook; un caso con
`deteccion: sin` no cambia. Resultado `parcial` o `no_detectado` y ejercicios sin fecha no suben nada, y la
madurez nunca baja por un ejercicio. Sin fichero purple la madurez es la de siempre.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from .catalog import ROOT

UC_FILE = ROOT / "soc" / "use-cases" / "catalog.yaml"
PB_DIR = Path("vulnerabilities") / "playbooks" / "caso-uso"
VENTANA_DIAS = 90


def cargar(uc_path: Path = UC_FILE) -> list[dict]:
    data = yaml.safe_load(Path(uc_path).read_text(encoding="utf-8")) or {}
    return [u for u in data.get("use_cases", []) if u.get("estado") != "retirado"]


def _fecha(v) -> date | None:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)) if v else None
    except ValueError:
        return None


def playbook_existe(u: dict, root: Path = ROOT) -> bool:
    pb = u.get("playbook")
    return bool(pb) and (Path(root) / pb).is_file()


def pruebas_purple(purple, hoy: date) -> dict[str, date]:
    """{caso de uso: fecha del ejercicio `detectado` más reciente, no posterior a `hoy`}.

    `purple`: `offensive.Purple`, ruta o dict; None = sin pruebas."""
    if purple is None:
        return {}
    if not hasattr(purple, "ejercicios"):
        from . import offensive
        purple = offensive.cargar_purple(purple)
    out: dict[str, date] = {}
    for e in purple.ejercicios:
        if e.resultado == "detectado" and e.fecha is not None and e.fecha <= hoy:
            if e.caso_uso not in out or e.fecha > out[e.caso_uso]:
                out[e.caso_uso] = e.fecha
    return out


def nivel_caso(u: dict, hoy: date, root: Path = ROOT, prueba_purple: date | None = None) -> int:
    det = u.get("deteccion", "sin")
    if det == "sin":
        return 1
    tiene_pb = playbook_existe(u, root)
    if prueba_purple is not None:
        det = "probada"
        u = {**u, "ultima_prueba": max(x for x in (_fecha(u.get("ultima_prueba")), prueba_purple) if x)}
    if det == "probada" and tiene_pb:
        f = _fecha(u.get("ultima_prueba"))
        if f and 0 <= (hoy - f).days <= VENTANA_DIAS:
            return 5
        return 4
    return 3 if tiene_pb else 2


def madurez(uc_path: Path = UC_FILE, hoy: date | None = None, root: Path = ROOT, purple=None) -> dict:
    """{'tecnicas': {id: nivel}, 'tacticas': {nombre: nivel (mínimo de activos)},
    'casos': {uc: nivel}, 'no_activos': {uc: {'nivel', 'estado', 'tactica'}}}"""
    hoy = hoy or date.today()
    pruebas = pruebas_purple(purple, hoy)
    tec: dict[str, int] = {}
    tac: dict[str, int] = {}
    casos: dict[str, int] = {}
    no_activos: dict[str, dict] = {}
    for u in cargar(uc_path):
        n = nivel_caso(u, hoy, root, pruebas.get(u["id"]))
        casos[u["id"]] = n
        for t in u.get("mitre", []):
            tec[t] = max(tec.get(t, 0), n)
        if u.get("estado") == "activo":
            tac[u["tactica"]] = min(tac.get(u["tactica"], n), n)
        else:
            no_activos[u["id"]] = {"nivel": n, "estado": u.get("estado"), "tactica": u["tactica"]}
    return {"tecnicas": dict(sorted(tec.items())), "tacticas": dict(sorted(tac.items())), "casos": casos,
            "no_activos": no_activos}


def sin_playbook(uc_path: Path = UC_FILE, root: Path = ROOT) -> list[str]:
    """Casos sin playbook declarado o cuyo fichero no existe."""
    return [u["id"] for u in cargar(uc_path) if not playbook_existe(u, root)]


def playbooks_huerfanos(uc_path: Path = UC_FILE, root: Path = ROOT) -> list[str]:
    """Ficheros PB-UC-* de caso-uso/ que ningún caso referencia (rutas relativas)."""
    usados = {u.get("playbook") for u in cargar(uc_path)}
    d = Path(root) / PB_DIR
    return sorted(p for p in (str(f.relative_to(root)) for f in d.glob("PB-UC-*.md")) if p not in usados)


def a_navigator(uc_path: Path = UC_FILE, hoy: date | None = None, root: Path = ROOT,
                nombre: str = "SMC madurez de detección", purple=None) -> dict:
    """Capa ATT&CK Navigator (puntuación = madurez 0-5)."""
    m = madurez(uc_path, hoy, root, purple)
    por_tec: dict[str, list[str]] = {}
    for u in cargar(uc_path):
        for t in u.get("mitre", []):
            por_tec.setdefault(t, []).append(u["id"])
    return {
        "name": nombre,
        "versions": {"attack": "16", "navigator": "5.1.0", "layer": "4.5"},
        "domain": "enterprise-attack",
        "description": "Madurez de detección por técnica: 1 caso sin regla, 2 regla, 3 regla+playbook, 4 probada, 5 probada <=90 días.",
        "gradient": {"colors": ["#ff6666", "#ffe766", "#8ec843"], "minValue": 0, "maxValue": 5},
        "techniques": [
            {"techniqueID": t, "score": s, "comment": "Casos: " + ", ".join(por_tec.get(t, []))}
            for t, s in m["tecnicas"].items()
        ],
    }
