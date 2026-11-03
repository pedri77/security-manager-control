"""PMO: vida del proyecto, horas, costes y presupuesto (T27).

Datos de cliente (presupuesto, horas, tarifas): fuera del repositorio (ADR-005, ADR-001).
Importes en `Decimal` con 2 decimales; las sumas se hacen sin redondeo intermedio y se
redondean una sola vez (ROUND_HALF_UP) al producir el resultado. Detalle de las
fórmulas en docs/pmo.md.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

import yaml

PARTIDAS = ("horas", "licencias", "servicios", "formacion")
TIPOS_EVENTO = ("comite", "auditoria", "renovacion", "entrega", "hito")
CENT = Decimal("0.01")
PRODID = "-//SMC//PMO//ES"


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


def _dec(v) -> Decimal | None:
    """Decimal finito o None (bool, texto no numérico, NaN, infinito)."""
    if v is None or isinstance(v, bool):
        return None
    try:
        d = Decimal(str(v).strip())
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() else None


def _r2(d: Decimal) -> Decimal:
    return d.quantize(CENT, rounding=ROUND_HALF_UP)


def _lista(v) -> list:
    if v is None or v == "":
        return []
    return v if isinstance(v, list) else [v]


def _mes(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


# ---------------------------------------------------------------- modelo
@dataclass
class Tarea:
    id: str
    titulo: str
    controles: list[str]
    accion: str
    responsable: str
    horas_estimadas: Decimal
    avance: Decimal                 # 0-100
    inicio: date | None
    fin: date | None
    depende: list[str]
    presupuesto: Decimal            # BAC de la tarea (ver docs/pmo.md)


@dataclass
class Imputacion:
    fecha: date | None
    rol: str
    tarea: str
    horas: Decimal


@dataclass
class Coste:
    proveedor: str
    concepto: str
    importe: Decimal
    fecha: date | None
    partida: str
    tarea: str


@dataclass
class Evento:
    id: str
    titulo: str
    tipo: str
    fecha: date
    fecha_fin: date | None = None
    descripcion: str = ""
    lugar: str = ""


@dataclass
class Riesgo:
    id: str
    descripcion: str
    probabilidad: str
    impacto: str
    mitigacion: str
    responsable: str
    estado: str


@dataclass
class Proyecto:
    id: str
    nombre: str
    cliente: str
    inicio: date | None
    fin: date | None
    presupuesto_total: Decimal
    presupuesto: dict[str, Decimal]
    tarifas: dict[str, Decimal]
    tareas: list[Tarea] = field(default_factory=list)
    imputaciones: list[Imputacion] = field(default_factory=list)
    costes: list[Coste] = field(default_factory=list)
    eventos: list[Evento] = field(default_factory=list)
    riesgos: list[Riesgo] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


@dataclass
class Evm:
    pv: Decimal
    ev: Decimal
    ac: Decimal
    bac: Decimal
    cpi: Decimal | None
    spi: Decimal | None


@dataclass
class Analisis:
    proyecto: Proyecto
    hoy: date
    por_partida: dict[str, dict[str, Decimal]]   # partida -> {presupuesto, real, desviacion}
    total: dict[str, Decimal]                    # {presupuesto, real, desviacion}
    evm: Evm
    tareas_retrasadas: list[Tarea]
    tareas_sin_control: list[Tarea]
    proximos_eventos: list[Evento]
    horas_rol_mes: dict[str, dict[str, Decimal]]  # rol -> {AAAA-MM: horas}
    suscripciones: dict | None
    avisos: list[str]


# ---------------------------------------------------------------- carga
def cargar_proyecto(origen) -> Proyecto:
    """Lee un proyecto desde una ruta YAML o un dict. Datos mal formados = aviso, no error."""
    if isinstance(origen, (str, Path)):
        origen = yaml.safe_load(Path(origen).read_text(encoding="utf-8"))
    raw = origen if isinstance(origen, dict) else {}
    av: list[str] = []
    if not isinstance(origen, dict):
        av.append("el proyecto no es un mapa; se carga vacío")
    p = raw.get("proyecto") if isinstance(raw.get("proyecto"), dict) else {}
    if not p:
        av.append("falta la sección 'proyecto'")

    def importe(valor, ctx, defecto=Decimal("0")):
        if valor is None:
            return defecto
        d = _dec(valor)
        if d is None:
            av.append(f"{ctx}: importe '{valor}' no es numérico, se toma como 0")
            return defecto
        if d < 0:
            av.append(f"{ctx}: importe negativo '{valor}'")
        return d

    pres_raw = p.get("presupuesto") if isinstance(p.get("presupuesto"), dict) else {}
    presupuesto = {k: importe(pres_raw.get(k), f"presupuesto.{k}") for k in PARTIDAS}
    for k in pres_raw:
        if k not in PARTIDAS:
            av.append(f"presupuesto: partida desconocida '{k}'")
    total = _dec(p.get("presupuesto_total"))
    suma = sum(presupuesto.values(), Decimal("0"))
    if total is None:
        total = suma
        if p.get("presupuesto_total") is not None:
            av.append(f"presupuesto_total '{p.get('presupuesto_total')}' no es numérico; se usa la suma de partidas")
    elif _r2(total) != _r2(suma):
        av.append(f"presupuesto_total ({_r2(total)}) no coincide con la suma de partidas ({_r2(suma)})")

    tarifas: dict[str, Decimal] = {}
    tar_raw = raw.get("tarifas") if isinstance(raw.get("tarifas"), dict) else {}
    for rol, v in tar_raw.items():
        d = _dec(v)
        if d is None or d < 0:
            av.append(f"tarifa del rol '{rol}': '{v}' no es un importe válido, se toma como 0")
            d = Decimal("0")
        tarifas[str(rol)] = d

    ini, fin = _fecha(p.get("inicio")), _fecha(p.get("fin"))
    if ini is None or fin is None:
        av.append("proyecto: inicio o fin ausentes o no válidos")
    elif fin < ini:
        av.append("proyecto: fin anterior a inicio")

    proy = Proyecto(id=str(p.get("id") or "PRY"), nombre=str(p.get("nombre") or ""),
                    cliente=str(p.get("cliente") or ""), inicio=ini, fin=fin,
                    presupuesto_total=total, presupuesto=presupuesto, tarifas=tarifas)

    ids: set[str] = set()
    for i, t in enumerate(_lista(raw.get("tareas")), 1):
        if not isinstance(t, dict):
            av.append(f"tareas[{i}]: entrada mal formada, se ignora")
            continue
        tid = str(t.get("id") or f"T-{i:02d}")
        if tid in ids:
            av.append(f"{tid}: id de tarea repetido")
        ids.add(tid)
        rol = str(t.get("responsable") or "")
        horas = importe(t.get("horas_estimadas"), f"{tid}.horas_estimadas")
        avance = _dec(t.get("avance"))
        if avance is None:
            if t.get("avance") is not None:
                av.append(f"{tid}: avance '{t.get('avance')}' no es numérico, se toma como 0")
            avance = Decimal("0")
        elif not (0 <= avance <= 100):
            av.append(f"{tid}: avance {avance} fuera de 0-100, se ajusta")
            avance = min(max(avance, Decimal("0")), Decimal("100"))
        ti, tf = _fecha(t.get("inicio")), _fecha(t.get("fin"))
        if ti is None or tf is None:
            av.append(f"{tid}: inicio o fin ausentes o no válidos (sin valor planificado)")
        elif tf < ti:
            av.append(f"{tid}: fin anterior a inicio")
        if rol and rol not in tarifas:
            av.append(f"{tid}: el rol '{rol}' no tiene tarifa, se valora a 0")
        if t.get("presupuesto") is not None:
            bac = importe(t.get("presupuesto"), f"{tid}.presupuesto")
        else:
            bac = horas * tarifas.get(rol, Decimal("0"))
        proy.tareas.append(Tarea(tid, str(t.get("titulo") or ""), [str(c) for c in _lista(t.get("controles"))],
                                 str(t.get("accion") or ""), rol, horas, avance, ti, tf,
                                 [str(d) for d in _lista(t.get("depende"))], bac))
    for t in proy.tareas:
        for d in t.depende:
            if d not in ids:
                av.append(f"{t.id}: depende de '{d}', que no existe")

    for i, r in enumerate(_lista(raw.get("imputaciones")), 1):
        if not isinstance(r, dict):
            av.append(f"imputaciones[{i}]: entrada mal formada, se ignora")
            continue
        h = _dec(r.get("horas"))
        if h is None or h < 0:
            av.append(f"imputaciones[{i}]: horas '{r.get('horas')}' no válidas, se ignora")
            continue
        f = _fecha(r.get("fecha"))
        if f is None:
            av.append(f"imputaciones[{i}]: fecha ausente o no válida, se ignora")
            continue
        im = Imputacion(f, str(r.get("rol") or ""), str(r.get("tarea") or ""), h)
        if im.tarea not in ids:
            av.append(f"imputaciones[{i}]: la tarea '{im.tarea}' no existe, se ignora")
            continue
        if im.rol not in tarifas:
            av.append(f"imputaciones[{i}]: el rol '{im.rol}' no tiene tarifa, se valora a 0")
        proy.imputaciones.append(im)

    for i, c in enumerate(_lista(raw.get("costes")), 1):
        if not isinstance(c, dict):
            av.append(f"costes[{i}]: entrada mal formada, se ignora")
            continue
        imp = _dec(c.get("importe"))
        if imp is None:
            av.append(f"costes[{i}]: importe '{c.get('importe')}' no es numérico, se ignora")
            continue
        partida = str(c.get("partida") or "")
        if partida not in PARTIDAS or partida == "horas":
            av.append(f"costes[{i}]: partida '{partida}' no válida (licencias, servicios, formacion), se ignora")
            continue
        f = _fecha(c.get("fecha"))
        if f is None:
            av.append(f"costes[{i}]: fecha ausente o no válida, se ignora")
            continue
        tarea = str(c.get("tarea") or "")
        if tarea and tarea not in ids:
            av.append(f"costes[{i}]: la tarea '{tarea}' no existe, se ignora")
            continue
        proy.costes.append(Coste(str(c.get("proveedor") or ""), str(c.get("concepto") or ""), imp, f, partida, tarea))

    for i, e in enumerate(_lista(raw.get("eventos")), 1):
        if not isinstance(e, dict):
            av.append(f"eventos[{i}]: entrada mal formada, se ignora")
            continue
        f = _fecha(e.get("fecha"))
        if f is None:
            av.append(f"eventos[{i}]: fecha ausente o no válida, se ignora")
            continue
        tipo = str(e.get("tipo") or "hito")
        if tipo not in TIPOS_EVENTO:
            av.append(f"eventos[{i}]: tipo '{tipo}' desconocido, se toma 'hito'")
            tipo = "hito"
        ff = _fecha(e.get("fecha_fin"))
        if ff is not None and ff < f:
            av.append(f"eventos[{i}]: fecha_fin anterior a fecha, se ignora")
            ff = None
        titulo = str(e.get("titulo") or "")
        eid = str(e.get("id") or "EV-" + hashlib.sha1(f"{titulo}|{f}".encode()).hexdigest()[:8])
        proy.eventos.append(Evento(eid, titulo, tipo, f, ff, str(e.get("descripcion") or ""), str(e.get("lugar") or "")))

    for i, r in enumerate(_lista(raw.get("riesgos")), 1):
        if not isinstance(r, dict):
            av.append(f"riesgos[{i}]: entrada mal formada, se ignora")
            continue
        proy.riesgos.append(Riesgo(str(r.get("id") or f"R-{i:02d}"), str(r.get("descripcion") or ""),
                                   str(r.get("probabilidad") or ""), str(r.get("impacto") or ""),
                                   str(r.get("mitigacion") or ""), str(r.get("responsable") or ""),
                                   str(r.get("estado") or "abierto")))
    proy.avisos = av
    return proy


# ---------------------------------------------------------------- cálculo
def _planificado(t: Tarea, hoy: date) -> Decimal:
    """Fracción planificada de la tarea a `hoy`: lineal entre inicio y fin, acotada a 0-1."""
    if t.inicio is None or t.fin is None:
        return Decimal("0")
    if hoy <= t.inicio:
        return Decimal("0")
    if hoy >= t.fin or t.fin <= t.inicio:
        return Decimal("1")
    return Decimal((hoy - t.inicio).days) / Decimal((t.fin - t.inicio).days)


def _ratio(num: Decimal, den: Decimal, nombre: str, av: list[str]) -> Decimal | None:
    if den == 0:
        av.append(f"{nombre} no calculable: denominador 0")
        return None
    return _r2(num / den)


def analizar(proyecto: Proyecto, hoy: date | None = None, assessment: dict | None = None,
             registry=None) -> Analisis:
    """Calcula costes, EVM y alertas a fecha `hoy`.

    `assessment`: evaluación del cliente (opcional); valida `accion` contra su `plan_accion`
    y hereda los controles de la acción. `registry`: registro de tecnologías; suma
    `coste_anual` de las suscripciones vía `smc.tech.suscripciones` (sin recalcular).
    """
    hoy = hoy or date.today()
    av = list(proyecto.avisos)
    tarifa = proyecto.tarifas

    # Solo cuenta lo imputado hasta `hoy` (inclusive).
    imps = []
    for im in proyecto.imputaciones:
        if im.fecha > hoy:
            av.append(f"imputación del {im.fecha} a {im.tarea} es posterior a hoy, no cuenta")
        else:
            imps.append(im)
    costes = []
    for c in proyecto.costes:
        if c.fecha > hoy:
            av.append(f"coste '{c.concepto}' del {c.fecha} es posterior a hoy, no cuenta")
        else:
            costes.append(c)

    # Coste real por partida y por tarea.
    real = {k: Decimal("0") for k in PARTIDAS}
    ac_tarea: dict[str, Decimal] = {t.id: Decimal("0") for t in proyecto.tareas}
    for im in imps:
        imp = im.horas * tarifa.get(im.rol, Decimal("0"))
        real["horas"] += imp
        ac_tarea[im.tarea] += imp
    for c in costes:
        real[c.partida] += c.importe
        if c.tarea:
            ac_tarea[c.tarea] += c.importe

    por_partida = {}
    for k in PARTIDAS:
        pr, rl = proyecto.presupuesto[k], real[k]
        por_partida[k] = {"presupuesto": _r2(pr), "real": _r2(rl), "desviacion": _r2(pr - rl)}
        if rl > pr:
            av.append(f"partida '{k}' por encima del presupuesto en {_r2(rl - pr)}")
    tot_real = sum(real.values(), Decimal("0"))
    total = {"presupuesto": _r2(proyecto.presupuesto_total), "real": _r2(tot_real),
             "desviacion": _r2(proyecto.presupuesto_total - tot_real)}

    # EVM
    pv = sum((t.presupuesto * _planificado(t, hoy) for t in proyecto.tareas), Decimal("0"))
    ev = sum((t.presupuesto * t.avance / 100 for t in proyecto.tareas), Decimal("0"))
    ac = sum(ac_tarea.values(), Decimal("0"))
    bac = sum((t.presupuesto for t in proyecto.tareas), Decimal("0"))
    evm = Evm(_r2(pv), _r2(ev), _r2(ac), _r2(bac), _ratio(ev, ac, "CPI", av), _ratio(ev, pv, "SPI", av))

    # Alertas de tareas
    plan = {}
    if isinstance(assessment, dict):
        from .plan import cargar_plan
        plan = {a.id: a for a in cargar_plan(assessment)}
    retrasadas, sin_control = [], []
    for t in proyecto.tareas:
        if t.fin is not None and t.fin < hoy and t.avance < 100:
            retrasadas.append(t)
        ctrl = list(t.controles)
        if t.accion:
            if assessment is not None and t.accion not in plan:
                av.append(f"{t.id}: la acción '{t.accion}' no existe en el plan_accion de la evaluación")
            elif t.accion in plan:
                ctrl += plan[t.accion].controles
        if not ctrl:
            sin_control.append(t)

    limite = hoy + timedelta(days=30)
    proximos = sorted((e for e in proyecto.eventos if hoy <= e.fecha <= limite), key=lambda e: (e.fecha, e.id))

    horas: dict[str, dict[str, Decimal]] = {}
    for im in imps:
        m = horas.setdefault(im.rol, {})
        m[_mes(im.fecha)] = m.get(_mes(im.fecha), Decimal("0")) + im.horas
    horas = {r: dict(sorted(m.items())) for r, m in sorted(horas.items())}

    susc = None
    if registry is not None:
        from . import tech
        s = tech.suscripciones(registry, hoy)
        eur = Decimal("0")
        otras: dict[str, Decimal] = {}
        for (prov, mon), v in s["coste_por_proveedor"].items():
            d = Decimal(str(v))
            if mon == "EUR":
                eur += d
            else:
                otras[mon] = otras.get(mon, Decimal("0")) + d
        for mon in otras:
            av.append(f"suscripciones en {mon} no se suman al total en EUR")
        av += [f"suscripciones: {a}" for a in s["avisos"]]
        susc = {"coste_anual_eur": _r2(eur), "otras_monedas": {m: _r2(v) for m, v in otras.items()},
                "por_proveedor": {f"{p} ({m})": _r2(Decimal(str(v))) for (p, m), v in s["coste_por_proveedor"].items()}}

    return Analisis(proyecto, hoy, por_partida, total, evm, retrasadas, sin_control, proximos, horas, susc, av)


# ---------------------------------------------------------------- Markdown
def _t(x) -> str:
    """Escapa texto para tablas Markdown/HTML (mismo criterio que gap.py)."""
    s = " ".join(str(x).split())
    return s.replace("<", "&lt;").replace(">", "&gt;").replace("|", "\\|")


def _eur(d: Decimal | None) -> str:
    return "n/d" if d is None else f"{d:,.2f}".replace(",", " ") + " €"


def render_markdown(a: Analisis) -> str:
    p = a.proyecto
    out = [f"# PMO: {_t(p.nombre or p.id)} ({a.hoy})", "",
           f"Cliente: {_t(p.cliente)} · Periodo: {p.inicio or 'n/d'} a {p.fin or 'n/d'}", "",
           "## Presupuesto por partida", "",
           "| Partida | Presupuesto | Real | Desviación |", "|---|---|---|---|"]
    for k, v in a.por_partida.items():
        out.append(f"| {k} | {_eur(v['presupuesto'])} | {_eur(v['real'])} | {_eur(v['desviacion'])} |")
    out.append(f"| **Total** | {_eur(a.total['presupuesto'])} | {_eur(a.total['real'])} | {_eur(a.total['desviacion'])} |")
    e = a.evm
    out += ["", "## Valor ganado (EVM)", "", "| BAC | PV | EV | AC | CPI | SPI |", "|---|---|---|---|---|---|",
            f"| {_eur(e.bac)} | {_eur(e.pv)} | {_eur(e.ev)} | {_eur(e.ac)} | {e.cpi if e.cpi is not None else 'n/d'} | {e.spi if e.spi is not None else 'n/d'} |",
            "", "## Tareas retrasadas", ""]
    out += [f"- {_t(t.id)} {_t(t.titulo)}: fin {t.fin}, avance {t.avance} %" for t in a.tareas_retrasadas] or ["Ninguna."]
    out += ["", "## Tareas sin control asociado", ""]
    out += [f"- {_t(t.id)} {_t(t.titulo)}" for t in a.tareas_sin_control] or ["Ninguna."]
    out += ["", "## Próximos eventos (30 días)", ""]
    if a.proximos_eventos:
        out += ["| Fecha | Tipo | Evento |", "|---|---|---|"]
        out += [f"| {x.fecha} | {_t(x.tipo)} | {_t(x.titulo)} |" for x in a.proximos_eventos]
    else:
        out.append("Ninguno.")
    out += ["", "## Horas por rol y mes", ""]
    if a.horas_rol_mes:
        out += ["| Rol | Mes | Horas |", "|---|---|---|"]
        out += [f"| {_t(r)} | {m} | {h.normalize():f} |" for r, ms in a.horas_rol_mes.items() for m, h in ms.items()]
    else:
        out.append("Sin imputaciones.")
    if p.riesgos:
        out += ["", "## Riesgos del proyecto", "", "| ID | Riesgo | Prob. | Impacto | Estado |", "|---|---|---|---|---|"]
        out += [f"| {_t(r.id)} | {_t(r.descripcion)} | {_t(r.probabilidad)} | {_t(r.impacto)} | {_t(r.estado)} |" for r in p.riesgos]
    if a.suscripciones is not None:
        s = a.suscripciones
        out += ["", "## Suscripciones del registro (fuera del presupuesto del proyecto)", "",
                f"Coste anual en EUR: {_eur(s['coste_anual_eur'])}"]
    if a.avisos:
        out += ["", "## Avisos", ""] + [f"- {_t(x)}" for x in a.avisos]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- iCalendar (RFC 5545)
def _ics_texto(s: str) -> str:
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str(s))
    s = s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return re.sub(r"\r\n|\r|\n", "\\\\n", s)


def _plegar(linea: str) -> list[str]:
    """Pliega a 75 octetos por línea (sin cortar caracteres UTF-8); continuación con un espacio."""
    out, actual, n = [], "", 0
    for ch in linea:
        b = len(ch.encode("utf-8"))
        limite = 75 if not out else 74       # la continuación gasta 1 octeto en el espacio
        if n + b > limite:
            out.append(actual)
            actual, n = "", 0
        actual += ch
        n += b
    out.append(actual)
    return [out[0]] + [" " + x for x in out[1:]]


def _uid(p: Proyecto, e: Evento) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "-", f"{p.id}-{e.id}")
    return f"{base}@smc.pmo"


def eventos_ics(proyecto: Proyecto, hoy: date | None = None) -> str:
    """Eventos del proyecto como iCalendar (eventos de día completo). CRLF, UID estable,
    DTSTAMP = `hoy` a las 00:00:00Z."""
    hoy = hoy or date.today()
    stamp = hoy.strftime("%Y%m%dT000000Z")
    lineas = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN"]
    for e in sorted(proyecto.eventos, key=lambda x: (x.fecha, x.id)):
        fin = (e.fecha_fin or e.fecha) + timedelta(days=1)       # DTEND exclusivo
        lineas += ["BEGIN:VEVENT", f"UID:{_uid(proyecto, e)}", f"DTSTAMP:{stamp}",
                   f"DTSTART;VALUE=DATE:{e.fecha:%Y%m%d}", f"DTEND;VALUE=DATE:{fin:%Y%m%d}",
                   f"SUMMARY:{_ics_texto(e.titulo)}", f"CATEGORIES:{_ics_texto(e.tipo)}"]
        if e.descripcion:
            lineas.append(f"DESCRIPTION:{_ics_texto(e.descripcion)}")
        if e.lugar:
            lineas.append(f"LOCATION:{_ics_texto(e.lugar)}")
        lineas.append("END:VEVENT")
    lineas.append("END:VCALENDAR")
    return "".join(f"{x}\r\n" for l in lineas for x in _plegar(l))


def exportar_ics(proyecto: Proyecto, ruta, hoy: date | None = None) -> Path:
    """Escribe el `.ics` (bytes exactos, sin traducir saltos de línea)."""
    ruta = Path(ruta)
    ruta.write_bytes(eventos_ics(proyecto, hoy).encode("utf-8"))
    return ruta
