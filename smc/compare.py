"""Comparación entre dos evaluaciones del mismo cliente (evolución). Reutiliza `smc.gap.analyse`."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from . import gap as _gap
from . import verticals as _vert

_RANGO = {"no_implementado": 0, "parcial": 1, "implementado": 2}
_BRECHA = ("no_implementado", "parcial")


@dataclass
class DeltaMarco:
    framework: str
    antes: float | None
    despues: float | None
    delta: float | None
    comparable: bool = True
    nota: str = ""


@dataclass
class CambioControl:
    id: str
    antes: str     # estado o "sin_evaluar"
    despues: str


@dataclass
class DeltaVertical:
    id: str
    antes: int | None
    despues: int | None
    delta: int | None


@dataclass
class Comparacion:
    marcos: list[DeltaMarco]
    mejoran: list[CambioControl]
    empeoran: list[CambioControl]
    cerrados: list[CambioControl]
    nuevas_brechas: list[CambioControl]
    sin_cambio: list[CambioControl]
    p1_antes: list[str]
    p1_despues: list[str]
    verticales: list[DeltaVertical]
    madurez_antes: float | None
    madurez_despues: float | None
    madurez_delta: float | None
    acciones_cerradas: list[str]
    avisos: list[str] = field(default_factory=list)
    cliente_antes: str = ""
    cliente_despues: str = ""
    fecha_antes: date | None = None
    fecha_despues: date | None = None


def _fecha(assessment) -> date | None:
    if not isinstance(assessment, dict):
        return None
    cli = assessment.get("cliente")
    for v in ((cli.get("fecha") if isinstance(cli, dict) else None), assessment.get("fecha")):
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            try:
                return date.fromisoformat(v.strip())
            except ValueError:
                pass
    return None


def _nombre(assessment) -> str:
    cli = assessment.get("cliente") if isinstance(assessment, dict) else None
    n = cli.get("nombre") if isinstance(cli, dict) else None
    return str(n).strip() if n else ""


def _estados(assessment) -> dict[str, str]:
    ev = assessment.get("evaluaciones") if isinstance(assessment, dict) else None
    out = {}
    for cid, e in (ev.items() if isinstance(ev, dict) else []):
        estado = e.get("estado") if isinstance(e, dict) else None
        if estado in _gap.VALID_STATES:
            out[str(cid)] = estado
    return out


def _clasificar(a: str, d: str) -> str:
    """a, d: estado o 'sin_evaluar'. Devuelve mejoran|empeoran|cerrados|nuevas_brechas|sin_cambio."""
    if a == d:
        return "sin_cambio"
    if a in _BRECHA and d in _BRECHA:
        return "mejoran" if _RANGO[d] > _RANGO[a] else "empeoran"
    if a in _BRECHA:
        return "cerrados" if d in ("implementado", "no_aplica") else "sin_cambio"
    if d in _BRECHA:
        return "nuevas_brechas"
    if a == "sin_evaluar" and d == "implementado":
        return "mejoran"
    if a == "implementado" and d == "sin_evaluar":
        return "empeoran"
    return "sin_cambio"


def _p1(an) -> list[str]:
    return sorted(b.control.id for r in an.results for b in r.brechas if b.nivel == "P1")


def _acciones_hechas(an) -> dict[str, str]:
    return {a.id: a.estado for a in an.plan}


def comparar(anterior: dict, actual: dict, hoy: date | None = None) -> Comparacion:
    hoy = hoy or date.today()
    an0, an1 = _gap.analyse(anterior, hoy), _gap.analyse(actual, hoy)
    avisos: list[str] = []

    n0, n1 = _nombre(anterior), _nombre(actual)
    if n0 != n1:
        avisos.append(f"Los clientes no coinciden: «{n0 or 'sin nombre'}» y «{n1 or 'sin nombre'}»; la comparación puede no ser válida")
    f0, f1 = _fecha(anterior), _fecha(actual)
    if f0 is None or f1 is None:
        avisos.append("Falta la fecha en " + ("ambas evaluaciones" if f0 is None and f1 is None else
                      "la evaluación anterior" if f0 is None else "la evaluación actual")
                      + ": no se puede comprobar el orden temporal")
    elif f1 < f0:
        avisos.append(f"La evaluación «actual» ({f1.isoformat()}) es más antigua que la «anterior» ({f0.isoformat()}): "
                      "los deltas están invertidos respecto a la evolución real")
    elif f1 == f0:
        avisos.append(f"Ambas evaluaciones tienen la misma fecha ({f0.isoformat()})")

    ens_ok = an0.categoria_ens == an1.categoria_ens
    if not ens_ok:
        avisos.append(f"La categoría ENS cambia ({an0.categoria_ens or 'fuera de alcance'} → "
                      f"{an1.categoria_ens or 'fuera de alcance'}): el delta ENS no es comparable")

    r0 = {r.framework: r for r in an0.results}
    r1 = {r.framework: r for r in an1.results}
    marcos = []
    for fw in [f for f in r0 if f in r1] + [f for f in r0 if f not in r1] + [f for f in r1 if f not in r0]:
        a = r0[fw].puntuacion if fw in r0 else None
        d = r1[fw].puntuacion if fw in r1 else None
        delta = round(d - a, 1) if a is not None and d is not None else None
        if fw == "ENS" and not ens_ok:
            marcos.append(DeltaMarco(fw, a, d, delta, False, "categoría ENS distinta: no comparable"))
        elif a is None or d is None:
            marcos.append(DeltaMarco(fw, a, d, None, False, "marco fuera de alcance en una de las evaluaciones"))
        else:
            marcos.append(DeltaMarco(fw, a, d, delta))

    e0, e1 = _estados(anterior), _estados(actual)
    grupos: dict[str, list[CambioControl]] = {k: [] for k in
                                              ("mejoran", "empeoran", "cerrados", "nuevas_brechas", "sin_cambio")}
    for cid in sorted(set(e0) | set(e1)):
        a, d = e0.get(cid, "sin_evaluar"), e1.get(cid, "sin_evaluar")
        grupos[_clasificar(a, d)].append(CambioControl(cid, a, d))

    v0 = _vert.evaluar(anterior, estricto=False) if isinstance(anterior, dict) and anterior.get("verticales") is not None else None
    v1 = _vert.evaluar(actual, estricto=False) if isinstance(actual, dict) and actual.get("verticales") is not None else None
    mad = {}
    for res, k in ((v0, 0), (v1, 1)):
        for v in (res.verticales if res else []):
            if v.estado == "evaluada" and v.puntua:
                mad.setdefault(v.id, [None, None])[k] = v.madurez
    verts = [DeltaVertical(i, a, d, d - a if a is not None and d is not None else None)
             for i, (a, d) in sorted(mad.items())]
    m0 = v0.madurez_media if v0 else None
    m1 = v1.madurez_media if v1 else None
    if (v0 is None) != (v1 is None):
        avisos.append("Solo una de las evaluaciones trae `verticales`: no hay delta de madurez")

    p0, p1 = _acciones_hechas(an0), _acciones_hechas(an1)
    cerradas = sorted(i for i, e in p1.items() if e == "hecha" and i in p0 and p0[i] != "hecha")

    return Comparacion(marcos, grupos["mejoran"], grupos["empeoran"], grupos["cerrados"], grupos["nuevas_brechas"],
                       grupos["sin_cambio"], _p1(an0), _p1(an1), verts, m0, m1,
                       round(m1 - m0, 2) if m0 is not None and m1 is not None else None,
                       cerradas, avisos, n0, n1, f0, f1)


def _s(x, dec=1) -> str:
    return "—" if x is None else f"{x:.{dec}f}"


def _d(x, dec=1) -> str:
    return "—" if x is None else f"{x:+.{dec}f}"


def _lista(titulo: str, items: list[CambioControl]) -> list[str]:
    out = [f"### {titulo} ({len(items)})", ""]
    out += [f"- {_gap.md_texto(c.id)}: {c.antes} → {c.despues}" for c in items] or ["Ninguno."]
    return out + [""]


def render_markdown(comp: Comparacion) -> str:
    L = ["# Evolución entre evaluaciones", ""]
    L.append(f"Anterior: {_gap.md_texto(comp.cliente_antes or 'sin nombre')} ({comp.fecha_antes or 'sin fecha'}). "
             f"Actual: {_gap.md_texto(comp.cliente_despues or 'sin nombre')} ({comp.fecha_despues or 'sin fecha'}).")
    L.append("")
    if comp.avisos:
        L += ["## Avisos", ""] + [f"- {_gap.md_texto(a)}" for a in comp.avisos] + [""]
    L += ["## Cumplimiento por marco", "", "| Marco | Antes | Después | Delta |", "|---|---|---|---|"]
    for m in comp.marcos:
        L.append(f"| {m.framework} | {_s(m.antes)} | {_s(m.despues)} | "
                 f"{_d(m.delta) if m.comparable else 'no comparable'} |")
    L += ["", "## Controles", ""]
    L += _lista("Cerrados", comp.cerrados) + _lista("Mejoran", comp.mejoran) + _lista("Empeoran", comp.empeoran)
    L += _lista("Nuevas brechas", comp.nuevas_brechas)
    L += [f"Sin cambio: {len(comp.sin_cambio)} controles.", ""]
    L += ["## Brechas P1", "", f"Antes ({len(comp.p1_antes)}): {', '.join(comp.p1_antes) or 'ninguna'}",
          f"Después ({len(comp.p1_despues)}): {', '.join(comp.p1_despues) or 'ninguna'}", ""]
    L += ["## Madurez de verticales", "",
          f"Media: {_s(comp.madurez_antes, 2)} → {_s(comp.madurez_despues, 2)} ({_d(comp.madurez_delta, 2)})", "",
          "| Vertical | Antes | Después | Delta |", "|---|---|---|---|"]
    L += [f"| {v.id} | {_s(v.antes, 0)} | {_s(v.despues, 0)} | {_d(v.delta, 0)} |" for v in comp.verticales]
    L += ["", "## Acciones del plan cerradas", ""]
    L += [f"- {_gap.md_texto(i)}" for i in comp.acciones_cerradas] or ["Ninguna."]
    return "\n".join(L) + "\n"
