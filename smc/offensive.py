"""Pentesting (seguimiento de hallazgos) y ejercicios purple team (T24).

Pentest: campañas y hallazgos. El SLA de remediación sale de `vulnerabilities/policy.yaml` y la severidad
efectiva se calcula con `smc.tech.severidad_efectiva` (normalizada sin tildes, KEV = crítica, desconocida =
crítica con aviso). No se duplica la política.

Purple team: ejercicios por técnica ATT&CK y caso de uso del SOC (`soc/use-cases/catalog.yaml`).
Cobertura por táctica: se toma el ÚLTIMO ejercicio de cada técnica; detectado cuenta 1, parcial 0,5 y
no_detectado 0; la cobertura es esa suma entre las técnicas ejercitadas de la táctica (0-100 %).

Errores y avisos: ids ATT&CK mal formados, caso de uso inexistente (o retirado), estados o resultados
no válidos son ERRORES (`validar_*` los lista y `cargar_*` lanza `OffensiveError`). Fechas ilegibles, CWE o
CVSS fuera de rango y controles SMC inexistentes son AVISOS (nunca excepciones).
Los ejemplos son ficticios (ADR-001): los datos reales de un cliente no van al repositorio.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import yaml

from . import mitre, tech
from .catalog import ROOT, load_all

OFFENSIVE_DIR = ROOT / "offensive"
TIPOS_CAMPANIA = ("interno", "externo", "web", "red_team")
ESTADOS_HALLAZGO = ("abierto", "en_remediacion", "corregido", "aceptado", "falso_positivo")
ABIERTOS = ("abierto", "en_remediacion")
RESULTADOS_PURPLE = ("detectado", "parcial", "no_detectado")
ESTADOS_MEJORA = ("abierta", "en_curso", "hecha")
RESULTADOS_RETEST = ("corregido", "persiste", "parcial")
PESO_RESULTADO = {"detectado": 1.0, "parcial": 0.5, "no_detectado": 0.0}
RE_ATTACK = re.compile(r"^T\d{4}(\.\d{3})?$")
RE_CWE = re.compile(r"^CWE-\d+$")
MESES_CADUCIDAD = 12


class OffensiveError(ValueError):
    """Datos de pentest o purple team no válidos (la lista completa va en `.errores`)."""

    def __init__(self, errores: list[str]):
        self.errores = list(errores)
        super().__init__("; ".join(self.errores))


@dataclass
class Campania:
    id: str
    nombre: str
    tipo: str
    alcance: str = ""
    proveedor: str = ""
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


@dataclass
class Hallazgo:
    id: str
    titulo: str
    severidad: str
    estado: str
    campania: str = ""
    cvss: float | None = None
    cwe: str = ""
    activo: str = ""
    control: str = ""
    kev: bool = False
    fecha_deteccion: date | None = None
    fecha_retest: date | None = None
    resultado_retest: str = ""
    fecha_revision: date | None = None


@dataclass
class Pentest:
    campanias: list[Campania] = field(default_factory=list)
    hallazgos: list[Hallazgo] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


@dataclass
class FueraSla:
    hallazgo: Hallazgo
    severidad_efectiva: str
    dias: int
    sla_dias: int


@dataclass
class EstadoHallazgos:
    hoy: date
    total: int
    abiertos: list[Hallazgo]
    fuera_sla: list[FueraSla]
    pendientes_retest: list[Hallazgo]
    aceptados_sin_revision: list[Hallazgo]
    por_severidad: dict[str, int]
    avisos: list[str] = field(default_factory=list)


@dataclass
class Mejora:
    descripcion: str = ""
    estado: str = "abierta"


@dataclass
class Ejercicio:
    id: str
    fecha: date | None
    tecnica: str
    caso_uso: str
    resultado: str
    tactica: str = ""
    tiempo_deteccion_min: float | None = None
    mejora: Mejora | None = None


@dataclass
class Purple:
    ejercicios: list[Ejercicio] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


@dataclass
class ResultadoPurple:
    hoy: date
    total: int
    cobertura_por_tactica: dict[str, dict]
    no_detectadas: list[Ejercicio]
    mejoras_abiertas: list[Ejercicio]
    ejercicios_caducados: list[Ejercicio]
    avisos: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- utilidades

def _fecha(v) -> date | None:
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v.strip())
        except ValueError:
            return None
    return None


def _texto(v) -> str:
    return "" if v is None else str(v).strip()


def _leer(fuente) -> dict:
    """Acepta ruta al YAML o dict ya cargado."""
    if isinstance(fuente, (str, Path)):
        fuente = yaml.safe_load(Path(fuente).read_text(encoding="utf-8"))
    return fuente if isinstance(fuente, dict) else {}


def _lista(d: dict, clave: str) -> list[dict]:
    v = d.get(clave)
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def sla_politica() -> dict:
    """SLA de remediación en días por severidad, tal cual `vulnerabilities/policy.yaml`."""
    return yaml.safe_load(tech.POLICY_FILE.read_text(encoding="utf-8"))["sla_remediacion_dias"]


def _ids_controles() -> set[str]:
    return {c.id for lista in load_all().values() for c in lista}


def _casos_de_uso(uc_path: Path | None) -> dict[str, dict]:
    casos = mitre.cargar(uc_path) if uc_path else mitre.cargar()
    return {u["id"]: u for u in casos}


# ---------------------------------------------------------------- pentest

def validar_pentest(datos) -> list[str]:
    d = _leer(datos)
    errores: list[str] = []
    ids_c: set[str] = set()
    for i, c in enumerate(_lista(d, "campanias"), 1):
        cid = _texto(c.get("id"))
        if not cid:
            errores.append(f"campanias[{i}]: falta 'id'")
        elif cid in ids_c:
            errores.append(f"campanias[{i}]: id '{cid}' repetido")
        ids_c.add(cid)
        if _texto(c.get("tipo")) not in TIPOS_CAMPANIA:
            errores.append(f"campania '{cid or i}': tipo '{_texto(c.get('tipo'))}' no válido ({', '.join(TIPOS_CAMPANIA)})")
    sla = sla_politica()
    ids_h: set[str] = set()
    for i, h in enumerate(_lista(d, "hallazgos"), 1):
        hid = _texto(h.get("id"))
        if not hid:
            errores.append(f"hallazgos[{i}]: falta 'id'")
        elif hid in ids_h:
            errores.append(f"hallazgos[{i}]: id '{hid}' repetido")
        ids_h.add(hid)
        if _texto(h.get("estado")) not in ESTADOS_HALLAZGO:
            errores.append(f"hallazgo '{hid or i}': estado '{_texto(h.get('estado'))}' no válido ({', '.join(ESTADOS_HALLAZGO)})")
        sev = tech.normalizar_severidad(h.get("severidad"))
        if sev not in sla:
            errores.append(f"hallazgo '{hid or i}': severidad '{_texto(h.get('severidad'))}' no válida ({', '.join(sla)})")
        camp = _texto(h.get("campania"))
        if camp and camp not in ids_c:
            errores.append(f"hallazgo '{hid or i}': campaña '{camp}' no existe")
    return errores


def cargar_pentest(fuente) -> Pentest:
    """Carga campañas y hallazgos. Lanza `OffensiveError` si hay errores; el resto son avisos."""
    d = _leer(fuente)
    errores = validar_pentest(d)
    if errores:
        raise OffensiveError(errores)
    avisos: list[str] = []
    controles = _ids_controles()
    camps = []
    for c in _lista(d, "campanias"):
        f_ini, f_fin = _fecha(c.get("fecha_inicio")), _fecha(c.get("fecha_fin"))
        if (c.get("fecha_inicio") and f_ini is None) or (c.get("fecha_fin") and f_fin is None):
            avisos.append(f"campaña {c['id']}: fecha no válida")
        camps.append(Campania(_texto(c["id"]), _texto(c.get("nombre")), _texto(c["tipo"]), _texto(c.get("alcance")),
                              _texto(c.get("proveedor")), f_ini, f_fin))
    hallazgos = []
    for h in _lista(d, "hallazgos"):
        hid = _texto(h["id"])
        det, ret, rev = _fecha(h.get("fecha_deteccion")), _fecha(h.get("fecha_retest")), _fecha(h.get("fecha_revision"))
        for campo, bruto, val in (("fecha_deteccion", h.get("fecha_deteccion"), det), ("fecha_retest", h.get("fecha_retest"), ret),
                                  ("fecha_revision", h.get("fecha_revision"), rev)):
            if bruto and val is None:
                avisos.append(f"{hid}: '{campo}' no es una fecha válida")
        if h.get("fecha_deteccion") in (None, "") and _texto(h["estado"]) in ABIERTOS:
            avisos.append(f"{hid}: sin 'fecha_deteccion', no se evalúa su SLA")
        cvss = None
        if h.get("cvss") not in (None, ""):
            try:
                cvss = float(h["cvss"])
                if isinstance(h["cvss"], bool) or not 0 <= cvss <= 10:
                    raise ValueError
            except (TypeError, ValueError):
                avisos.append(f"{hid}: CVSS '{h['cvss']}' fuera de rango 0-10, se ignora")
                cvss = None
        cwe = _texto(h.get("cwe"))
        if cwe and not RE_CWE.match(cwe):
            avisos.append(f"{hid}: CWE '{cwe}' no tiene el formato CWE-<número>")
        ctl = _texto(h.get("control"))
        if ctl and ctl not in controles:
            avisos.append(f"{hid}: control SMC '{ctl}' no existe en los catálogos")
        res = _texto(h.get("resultado_retest"))
        if res and res not in RESULTADOS_RETEST:
            avisos.append(f"{hid}: resultado_retest '{res}' no reconocido ({', '.join(RESULTADOS_RETEST)})")
        hallazgos.append(Hallazgo(hid, _texto(h.get("titulo")), _texto(h.get("severidad")), _texto(h["estado"]),
                                  _texto(h.get("campania")), cvss, cwe, _texto(h.get("activo")), ctl,
                                  str(h.get("kev")).strip().lower() == "true", det, ret, res, rev))
    return Pentest(camps, hallazgos, avisos)


def estado_hallazgos(datos, hoy: date | None = None) -> EstadoHallazgos:
    """Abiertos, fuera de SLA, pendientes de retest y aceptados sin fecha de revisión.

    - Abierto: estado `abierto` o `en_remediacion`.
    - Fuera de SLA: abierto y días desde `fecha_deteccion` > SLA de su severidad efectiva (estricto).
    - Pendiente de retest: `corregido` sin `fecha_retest`.
    - Aceptado sin revisión: `aceptado` sin `fecha_revision` válida."""
    hoy = hoy or date.today()
    p = datos if isinstance(datos, Pentest) else cargar_pentest(datos)
    sla = sla_politica()
    avisos = list(p.avisos)
    abiertos = [h for h in p.hallazgos if h.estado in ABIERTOS]
    fuera: list[FueraSla] = []
    for h in abiertos:
        sev, av = tech.severidad_efectiva(h.severidad, h.kev, sla)
        avisos += [f"{h.id}: {x}" for x in av]
        if h.fecha_deteccion is None:
            continue
        dias = (hoy - h.fecha_deteccion).days
        if dias > sla[sev]:
            fuera.append(FueraSla(h, sev, dias, sla[sev]))
    fuera.sort(key=lambda f: (list(sla).index(f.severidad_efectiva), -f.dias, f.hallazgo.id))
    pend = [h for h in p.hallazgos if h.estado == "corregido" and h.fecha_retest is None]
    acep = [h for h in p.hallazgos if h.estado == "aceptado" and h.fecha_revision is None]
    por_sev = {s: 0 for s in sla}
    for h in abiertos:
        sev, _ = tech.severidad_efectiva(h.severidad, h.kev, sla)
        por_sev[sev] += 1
    return EstadoHallazgos(hoy, len(p.hallazgos), abiertos, fuera, pend, acep, por_sev, avisos)


# ---------------------------------------------------------------- purple team

def validar_purple(datos, uc_path: Path | None = None) -> list[str]:
    d = _leer(datos)
    casos = _casos_de_uso(uc_path)
    errores: list[str] = []
    ids: set[str] = set()
    for i, e in enumerate(_lista(d, "ejercicios"), 1):
        eid = _texto(e.get("id"))
        if not eid:
            errores.append(f"ejercicios[{i}]: falta 'id'")
        elif eid in ids:
            errores.append(f"ejercicios[{i}]: id '{eid}' repetido")
        ids.add(eid)
        etq = eid or str(i)
        tec = _texto(e.get("tecnica"))
        if not RE_ATTACK.match(tec):
            errores.append(f"ejercicio '{etq}': técnica ATT&CK '{tec}' no válida (T1234 o T1234.001)")
        uc = _texto(e.get("caso_uso"))
        if uc not in casos:
            errores.append(f"ejercicio '{etq}': caso de uso '{uc}' no existe en el catálogo del SOC")
        if _texto(e.get("resultado")) not in RESULTADOS_PURPLE:
            errores.append(f"ejercicio '{etq}': resultado '{_texto(e.get('resultado'))}' no válido ({', '.join(RESULTADOS_PURPLE)})")
        m = e.get("mejora")
        if isinstance(m, dict) and _texto(m.get("estado") or "abierta") not in ESTADOS_MEJORA:
            errores.append(f"ejercicio '{etq}': estado de mejora '{_texto(m.get('estado'))}' no válido ({', '.join(ESTADOS_MEJORA)})")
    return errores


def cargar_purple(fuente, uc_path: Path | None = None) -> Purple:
    """Carga ejercicios purple. Lanza `OffensiveError` ante ids ATT&CK mal formados o casos de uso inexistentes."""
    d = _leer(fuente)
    errores = validar_purple(d, uc_path)
    if errores:
        raise OffensiveError(errores)
    casos = _casos_de_uso(uc_path)
    avisos: list[str] = []
    ejercicios = []
    for e in _lista(d, "ejercicios"):
        eid, uc, tec = _texto(e["id"]), _texto(e["caso_uso"]), _texto(e["tecnica"])
        f = _fecha(e.get("fecha"))
        if f is None:
            avisos.append(f"{eid}: fecha no válida o ausente, no se evalúa su antigüedad")
        if tec not in (casos[uc].get("mitre") or []):
            avisos.append(f"{eid}: la técnica {tec} no figura entre las del caso de uso {uc}")
        t = e.get("tiempo_deteccion_min")
        if t in (None, ""):
            t = None
        else:
            try:
                t = float(t)
                if isinstance(e["tiempo_deteccion_min"], bool) or t < 0:
                    raise ValueError
            except (TypeError, ValueError):
                avisos.append(f"{eid}: tiempo_deteccion_min '{t}' no válido, se ignora")
                t = None
        if _texto(e["resultado"]) == "no_detectado" and t is not None:
            avisos.append(f"{eid}: resultado no_detectado con tiempo de detección, se ignora el tiempo")
            t = None
        m = e.get("mejora")
        mejora = Mejora(_texto(m.get("descripcion")), _texto(m.get("estado")) or "abierta") if isinstance(m, dict) else None
        ejercicios.append(Ejercicio(eid, f, tec, uc, _texto(e["resultado"]), _texto(casos[uc].get("tactica")), t, mejora))
    return Purple(ejercicios, avisos)


def purple(datos, hoy: date | None = None, uc_path: Path | None = None) -> ResultadoPurple:
    """Cobertura por táctica, técnicas no detectadas, mejoras abiertas y ejercicios de más de 12 meses.

    - Cobertura: último ejercicio de cada técnica (ver docstring del módulo).
    - No detectadas: técnicas cuyo último ejercicio no fue `detectado` (parcial y no_detectado).
    - Mejoras abiertas: ejercicios con mejora que no está `hecha`.
    - Caducado: ejercicio con más de 365 días a `hoy` (estricto)."""
    hoy = hoy or date.today()
    p = datos if isinstance(datos, Purple) else cargar_purple(datos, uc_path)
    ultimo: dict[str, Ejercicio] = {}
    for e in sorted(p.ejercicios, key=lambda x: (x.fecha or date.min, x.id)):
        ultimo[e.tecnica] = e
    cobertura: dict[str, dict] = {}
    for e in ultimo.values():
        c = cobertura.setdefault(e.tactica, {"tecnicas": 0, "detectado": 0, "parcial": 0, "no_detectado": 0, "cobertura_pct": 0.0,
                                             "tiempo_medio_min": None, "_t": []})
        c["tecnicas"] += 1
        c[e.resultado] += 1
        c["cobertura_pct"] += PESO_RESULTADO[e.resultado]
        if e.tiempo_deteccion_min is not None:
            c["_t"].append(e.tiempo_deteccion_min)
    for c in cobertura.values():
        c["cobertura_pct"] = round(100 * c["cobertura_pct"] / c["tecnicas"], 1)
        t = c.pop("_t")
        c["tiempo_medio_min"] = round(sum(t) / len(t), 1) if t else None
    limite = hoy - timedelta(days=365)
    return ResultadoPurple(
        hoy, len(p.ejercicios), dict(sorted(cobertura.items())),
        sorted((e for e in ultimo.values() if e.resultado != "detectado"), key=lambda e: e.tecnica),
        [e for e in p.ejercicios if e.mejora and e.mejora.estado != "hecha"],
        [e for e in p.ejercicios if e.fecha is not None and e.fecha < limite],
        list(p.avisos))


# ---------------------------------------------------------------- render

def _c(v) -> str:
    """Celda Markdown: escapa `|`, `<`, `>` y saltos de línea."""
    return (str(v).replace("\\", "\\\\").replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")
            .replace("\r", " ").replace("\n", " "))


def _f(v) -> str:
    return v.isoformat() if v else "—"


def render_markdown(pentest: EstadoHallazgos | None = None, purple_res: ResultadoPurple | None = None) -> str:
    out = ["# Pentesting y purple team", ""]
    if pentest is not None:
        e = pentest
        out += [f"## Hallazgos de pentest a {e.hoy.isoformat()}", "",
                f"Total: {e.total} · Abiertos: {len(e.abiertos)} · Fuera de SLA: {len(e.fuera_sla)} · "
                f"Pendientes de retest: {len(e.pendientes_retest)} · Aceptados sin revisión: {len(e.aceptados_sin_revision)}", ""]
        out += ["| Severidad | Abiertos |", "|---|---|"] + [f"| {_c(s)} | {n} |" for s, n in e.por_severidad.items()] + [""]
        if e.fuera_sla:
            out += ["### Fuera de SLA", "", "| ID | Título | Sev. efectiva | Días | SLA | Activo | Control |", "|---|---|---|---|---|---|---|"]
            out += [f"| {_c(f.hallazgo.id)} | {_c(f.hallazgo.titulo)} | {_c(f.severidad_efectiva)} | {f.dias} | {f.sla_dias} | "
                    f"{_c(f.hallazgo.activo or '—')} | {_c(f.hallazgo.control or '—')} |" for f in e.fuera_sla] + [""]
        for titulo, lista in (("Pendientes de retest", e.pendientes_retest), ("Aceptados sin fecha de revisión", e.aceptados_sin_revision)):
            if lista:
                out += [f"### {titulo}", ""] + [f"- {_c(h.id)}: {_c(h.titulo)}" for h in lista] + [""]
        if e.avisos:
            out += ["Avisos:"] + [f"- {_c(a)}" for a in e.avisos] + [""]
    if purple_res is not None:
        r = purple_res
        out += [f"## Ejercicios purple team a {r.hoy.isoformat()}", "", f"Ejercicios: {r.total}", ""]
        if r.cobertura_por_tactica:
            out += ["| Táctica | Técnicas | Detectado | Parcial | No detectado | Cobertura | Tiempo medio (min) |", "|---|---|---|---|---|---|---|"]
            for t, c in r.cobertura_por_tactica.items():
                tm = "—" if c["tiempo_medio_min"] is None else c["tiempo_medio_min"]
                out.append(f"| {_c(t)} | {c['tecnicas']} | {c['detectado']} | {c['parcial']} | {c['no_detectado']} | {c['cobertura_pct']} % | {tm} |")
            out.append("")
        if r.no_detectadas:
            out += ["### Técnicas no detectadas del todo", ""] + [f"- {_c(e.tecnica)} ({_c(e.caso_uso)}, {_c(e.resultado)}, {_f(e.fecha)})" for e in r.no_detectadas] + [""]
        if r.mejoras_abiertas:
            out += ["### Mejoras abiertas", ""] + [f"- {_c(e.id)} ({_c(e.mejora.estado)}): {_c(e.mejora.descripcion)}" for e in r.mejoras_abiertas] + [""]
        if r.ejercicios_caducados:
            out += [f"### Ejercicios de más de {MESES_CADUCIDAD} meses", ""] + [f"- {_c(e.id)} ({_f(e.fecha)}, {_c(e.tecnica)})" for e in r.ejercicios_caducados] + [""]
        if r.avisos:
            out += ["Avisos:"] + [f"- {_c(a)}" for a in r.avisos] + [""]
    if pentest is None and purple_res is None:
        out.append("Sin datos.")
    return "\n".join(out).rstrip("\n") + "\n"
