"""Registro de tecnologías (caducidades) y seguimiento de vulnerabilidades."""
from __future__ import annotations

import csv
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import yaml

from .catalog import ROOT

POLICY_FILE = ROOT / "vulnerabilities" / "policy.yaml"


def _d(v) -> date | None:
    if not v:
        return None
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def normalizar_severidad(valor) -> str:
    """Minúsculas, sin tildes ni espacios sobrantes: «Crítica » -> «critica»."""
    t = unicodedata.normalize("NFD", str(valor or "").strip().lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def severidad_efectiva(severidad, kev, sla: dict) -> tuple[str, list[str]]:
    """Severidad a efectos de SLA y de semáforo (política `policy.yaml`).

    - Se normaliza (minúsculas, sin tildes).
    - KEV o explotación activa (`priorizacion.kev_o_explotacion_activa`) = crítica.
    - Una severidad fuera de la política cuenta como crítica, con aviso (nunca "sin SLA" = nunca vence).
    Devuelve (severidad, avisos)."""
    sev = normalizar_severidad(severidad)
    avisos = []
    if sev not in sla:
        avisos.append(f"severidad '{severidad}' sin SLA definido: se trata como crítica")
        sev = "critica"
    if str(kev).strip().lower() == "true" and sev != "critica":
        avisos.append(f"KEV con severidad '{sev}': se trata como crítica (policy.yaml)")
        sev = "critica"
    return sev, avisos


def expiring(registry: Path, days: int = 90, today: date | None = None) -> list[tuple[date, str, str, str]]:
    today = today or date.today()
    limit = today + timedelta(days=days)
    data = yaml.safe_load(Path(registry).read_text(encoding="utf-8"))
    items = []
    for t in data["technologies"]:
        cands = [
            ("Licencia", _d((t.get("licencia") or {}).get("vence"))),
            ("Fin de soporte", _d((t.get("soporte_fabricante") or {}).get("fin_soporte"))),
            ("Fin de vida", _d((t.get("soporte_fabricante") or {}).get("fin_vida"))),
        ]
        cands += [(f"Certificado {c.get('cn')}", _d(c.get("vence"))) for c in t.get("certificados") or []]
        for tipo, d in cands:
            if d and d <= limit:
                items.append((d, t["id"], t["nombre"], tipo))
        lic = t.get("licencia") or {}
        if lic.get("contratadas") and lic.get("desplegadas", 0) > lic["contratadas"]:
            items.append((today, t["id"], t["nombre"], "Sobredespliegue de licencias"))
    return sorted(items)


def render_expiring(items, days: int, today: date | None = None) -> str:
    today = today or date.today()
    out = [f"# Caducidades en los próximos {days} días", "", "| Fecha | Días | Tecnología | Elemento |", "|---|---|---|---|"]
    for d, tid, name, tipo in items:
        delta = (d - today).days
        flag = "VENCIDO" if delta < 0 else str(delta)
        out.append(f"| {d} | {flag} | {tid} {name} | {tipo} |")
    if not items:
        out.append("| — | — | Sin caducidades | — |")
    return "\n".join(out) + "\n"


def vulns(tracker: Path, today: date | None = None) -> str:
    today = today or date.today()
    policy = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    sla = policy["sla_remediacion_dias"]
    rows = list(csv.DictReader(Path(tracker).open(encoding="utf-8")))
    abiertas = [r for r in rows if r["estado"] != "remediada"]
    out = ["# Vulnerabilidades", "", f"Total: {len(rows)} · Abiertas: {len(abiertas)}", "",
           "| CVE | Tecnología | Sev. | KEV | Expuesta | Días abierta | SLA | Estado |", "|---|---|---|---|---|---|---|---|"]
    vencidas = 0
    efectivas = {id(r): severidad_efectiva(r["severidad"], r["kev"], sla)[0] for r in abiertas}
    for r in sorted(abiertas, key=lambda r: list(sla).index(efectivas[id(r)])):
        dias = (today - date.fromisoformat(r["detectado"])).days
        limite = sla.get(efectivas[id(r)])
        estado_sla = "VENCIDO" if limite is not None and dias > limite else "ok"
        vencidas += estado_sla == "VENCIDO"
        out.append(f"| {r['cve']} | {r['tecnologia_id']} | {r['severidad']} | {r['kev']} | {r['expuesto_internet']} | {dias} | {estado_sla} ({limite} d) | {r['estado']} |")
    out += ["", f"Fuera de SLA: {vencidas}"]
    return "\n".join(out) + "\n"


# --- v0.5: evaluación de tecnologías, estado de reglas y suscripciones ---

UMBRAL_REGLAS_DIAS = 180
UMBRAL_INFRAUSO = 0.70
CONFIGURACIONES = ("bastionada", "por_defecto", "desconocida")
ESTADOS_REGLAS = ("revisadas", "sin_revisar", "no_evaluable")


def _tecnologias(registry) -> list[dict]:
    """Acepta una ruta al YAML o un dict ya cargado."""
    if isinstance(registry, (str, Path)):
        registry = yaml.safe_load(Path(registry).read_text(encoding="utf-8"))
    techs = (registry or {}).get("technologies") or []
    return [t for t in techs if isinstance(t, dict)]


def _num(v, default=0.0) -> float:
    if isinstance(v, bool):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _numerico(v) -> bool:
    if isinstance(v, bool):
        return False
    try:
        return float(v) == float(v)      # descarta NaN
    except (TypeError, ValueError):
        return False


def evaluar_tecnologias(registry) -> list[dict]:
    """Una fila por tecnología: vertical, cobertura, configuración, madurez y avisos.

    Datos ausentes o inválidos no rompen: dan avisos."""
    filas = []
    for t in _tecnologias(registry):
        ev = t.get("evaluacion") if isinstance(t.get("evaluacion"), dict) else {}
        avisos = []
        if not ev:
            avisos.append("sin evaluación")
        conf = ev.get("configuracion", "desconocida") if ev else "desconocida"
        if conf not in CONFIGURACIONES:
            avisos.append(f"configuracion '{conf}' no válida (se trata como desconocida)")
            conf = "desconocida"
        mad = ev.get("madurez") if ev else None
        if mad is not None and not (isinstance(mad, (int, float)) and 0 <= mad <= 5):
            avisos.append(f"madurez '{mad}' fuera de 0-5")
            mad = None
        filas.append({"id": t.get("id"), "nombre": t.get("nombre"), "vertical": t.get("vertical"),
                      "cobertura_pct": ev.get("cobertura_pct") if ev else None,
                      "configuracion": conf, "madurez": mad, "avisos": avisos})
    return filas


def render_evaluacion(filas: list[dict]) -> str:
    out = ["# Evaluación de tecnologías", "",
           "| Tecnología | Vertical | Cobertura | Configuración | Madurez (0-5) | Avisos |", "|---|---|---|---|---|---|"]
    for f in filas:
        cob = "—" if f["cobertura_pct"] is None else f"{f['cobertura_pct']} %"
        mad = "—" if f["madurez"] is None else f["madurez"]
        out.append(f"| {f['id']} {f['nombre']} | {f['vertical'] or '—'} | {cob} | {f['configuracion']} | {mad} | {'; '.join(f['avisos']) or '—'} |")
    if not filas:
        out.append("| — | — | — | — | — | Sin tecnologías |")
    return "\n".join(out) + "\n"


def reglas(registry, hoy: date | None = None, dias: int = UMBRAL_REGLAS_DIAS) -> dict:
    """Estado de las reglas de los dispositivos.

    Devuelve {'revisadas', 'sin_revisar', 'no_evaluables', 'any_any', 'avisos'}; cada elemento es un dict.
    `any_any` lista todo dispositivo con reglas any-any > 0 con independencia de su estado
    (revisadas, sin_revisar o no_evaluable): una revisión reciente no lo hace aceptable.
    Una tecnología cuenta como `sin_revisar` si su estado lo es, o si estando `revisadas`
    la última revisión supera `dias`. Las `no_evaluable` se listan siempre con su motivo;
    sin motivo se marca en `avisos` (dato inválido). Tecnologías sin bloque `reglas` se ignoran."""
    hoy = hoy or date.today()
    res = {"revisadas": [], "sin_revisar": [], "no_evaluables": [], "any_any": [], "avisos": []}
    for t in _tecnologias(registry):
        r = t.get("reglas")
        if not isinstance(r, dict):
            continue
        estado = r.get("estado")
        base = {"id": t.get("id"), "nombre": t.get("nombre"), "n_reglas": r.get("n_reglas"),
                "reglas_any_any": int(_num(r.get("reglas_any_any"))), "reglas_sin_uso": int(_num(r.get("reglas_sin_uso")))}
        if base["reglas_any_any"] > 0:
            res["any_any"].append({"id": base["id"], "nombre": base["nombre"],
                                   "reglas_any_any": base["reglas_any_any"],
                                   "estado": estado if estado in ESTADOS_REGLAS else "sin_revisar"})
        if estado not in ESTADOS_REGLAS:
            res["avisos"].append(f"{t.get('id')}: estado de reglas '{estado}' no válido (se trata como sin_revisar)")
            estado = "sin_revisar"
        if estado == "no_evaluable":
            motivo = str(r.get("motivo") or "").strip()
            if not motivo:
                res["avisos"].append(f"{t.get('id')}: no_evaluable sin motivo (obligatorio)")
            res["no_evaluables"].append({**base, "motivo": motivo or "SIN MOTIVO"})
            continue
        try:
            ult = _d(r.get("ultima_revision"))
        except ValueError:
            res["avisos"].append(f"{t.get('id')}: ultima_revision no es una fecha válida")
            ult = None
        edad = (hoy - ult).days if ult else None
        fila = {**base, "ultima_revision": ult, "dias_sin_revisar": edad}
        if estado == "sin_revisar" or edad is None or edad > dias:
            res["sin_revisar"].append({**fila, "caducada": edad is None or edad > dias})
        else:
            res["revisadas"].append(fila)
    return res


def render_reglas(res: dict, hoy: date | None = None, dias: int = UMBRAL_REGLAS_DIAS) -> str:
    hoy = hoy or date.today()
    out = [f"# Estado de las reglas de los dispositivos ({hoy})", "", f"Umbral de revisión: {dias} días.", ""]
    if res.get("any_any"):
        out += ["## ATENCIÓN: reglas any-any (con independencia de la revisión)", "",
                "| Dispositivo | Reglas any-any | Estado de las reglas |", "|---|---|---|"]
        out += [f"| {f['id']} {f['nombre']} | **{f['reglas_any_any']}** | {f['estado']} |" for f in res["any_any"]]
        out.append("")
    out += ["## Sin revisar o revisión caducada", "",
            "| Dispositivo | Última revisión | Días | Reglas | any-any | Sin uso |", "|---|---|---|---|---|---|"]
    for f in res["sin_revisar"]:
        aa = f"**{f['reglas_any_any']}**" if f["reglas_any_any"] else "0"
        out.append(f"| {f['id']} {f['nombre']} | {f['ultima_revision'] or 'nunca'} | {f['dias_sin_revisar'] if f['dias_sin_revisar'] is not None else '—'} | {f['n_reglas'] if f['n_reglas'] is not None else '—'} | {aa} | {f['reglas_sin_uso']} |")
    if not res["sin_revisar"]:
        out.append("| — | — | — | — | — | — |")
    out += ["", "## No evaluables (no se puede decir si sus reglas son correctas)", "", "| Dispositivo | Motivo |", "|---|---|"]
    for f in res["no_evaluables"]:
        out.append(f"| {f['id']} {f['nombre']} | {f['motivo']} |")
    if not res["no_evaluables"]:
        out.append("| — | — |")
    out += ["", "## Revisadas", "", "| Dispositivo | Última revisión | Días | Reglas | any-any | Sin uso |", "|---|---|---|---|---|---|"]
    for f in res["revisadas"]:
        out.append(f"| {f['id']} {f['nombre']} | {f['ultima_revision']} | {f['dias_sin_revisar']} | {f['n_reglas'] if f['n_reglas'] is not None else '—'} | {f['reglas_any_any']} | {f['reglas_sin_uso']} |")
    if not res["revisadas"]:
        out.append("| — | — | — | — | — | — |")
    if res["avisos"]:
        out += ["", "## Avisos", ""] + [f"- {a}" for a in res["avisos"]]
    return "\n".join(out) + "\n"


def suscripciones(registry, hoy: date | None = None, dias: int = 90, umbral: float = UMBRAL_INFRAUSO) -> dict:
    """Control de suscripciones: renovaciones en `dias`, infrautilizadas (< umbral),
    sobredespliegue (en uso > contratadas) y coste total por proveedor (por moneda)."""
    hoy = hoy or date.today()
    limite = hoy + timedelta(days=dias)
    res = {"renovaciones": [], "infrautilizadas": [], "sobredespliegue": [], "coste_por_proveedor": {}, "avisos": []}
    for t in _tecnologias(registry):
        s = t.get("suscripcion")
        if not isinstance(s, dict):
            continue
        tid, nombre = t.get("id"), t.get("nombre")
        prov, mon = s.get("proveedor") or "—", s.get("moneda") or "EUR"
        coste = _num(s.get("coste_anual"))
        bruto = s.get("coste_anual")
        if bruto is not None and not _numerico(bruto):
            res["avisos"].append(f"{tid}: coste_anual '{bruto}' no es numérico, se suma como 0")
        clave = (prov, mon)
        res["coste_por_proveedor"][clave] = res["coste_por_proveedor"].get(clave, 0.0) + coste
        try:
            ren = _d(s.get("renovacion"))
        except ValueError:
            res["avisos"].append(f"{tid}: renovacion no es una fecha válida")
            ren = None
        if ren and ren <= limite:
            res["renovaciones"].append({"id": tid, "nombre": nombre, "proveedor": prov, "fecha": ren,
                                        "dias": (ren - hoy).days, "coste_anual": coste, "moneda": mon,
                                        "propietario": s.get("propietario"), "autorrenovacion": bool(s.get("autorrenovacion"))})
        cont, uso = _num(s.get("unidades_contratadas")), _num(s.get("unidades_en_uso"))
        if cont > 0:
            ratio = uso / cont
            if ratio < umbral:
                res["infrautilizadas"].append({"id": tid, "nombre": nombre, "proveedor": prov, "contratadas": cont,
                                               "en_uso": uso, "uso_pct": round(ratio * 100, 1),
                                               "coste_anual": coste, "moneda": mon,
                                               "coste_ocioso": round(coste * (1 - ratio), 2)})
            elif uso > cont:
                res["sobredespliegue"].append({"id": tid, "nombre": nombre, "proveedor": prov, "contratadas": cont,
                                               "en_uso": uso, "exceso": uso - cont})
        else:
            res["avisos"].append(f"{tid}: sin unidades_contratadas, no se evalúa el uso")
    res["renovaciones"].sort(key=lambda r: r["fecha"])
    return res


def render_suscripciones(res: dict, hoy: date | None = None, dias: int = 90, umbral: float = UMBRAL_INFRAUSO) -> str:
    hoy = hoy or date.today()
    out = [f"# Suscripciones ({hoy})", "", f"## Renovaciones en los próximos {dias} días", "",
           "| Fecha | Días | Tecnología | Proveedor | Coste anual | Propietario | Autorrenovación |", "|---|---|---|---|---|---|---|"]
    for r in res["renovaciones"]:
        d = "VENCIDA" if r["dias"] < 0 else r["dias"]
        out.append(f"| {r['fecha']} | {d} | {r['id']} {r['nombre']} | {r['proveedor']} | {r['coste_anual']:.0f} {r['moneda']} | {r['propietario'] or '—'} | {'sí' if r['autorrenovacion'] else 'no'} |")
    if not res["renovaciones"]:
        out.append("| — | — | Sin renovaciones | — | — | — | — |")
    out += ["", f"## Infrautilizadas (uso < {umbral * 100:.0f} %)", "",
            "| Tecnología | Proveedor | En uso / contratadas | Uso | Coste ocioso |", "|---|---|---|---|---|"]
    for r in res["infrautilizadas"]:
        out.append(f"| {r['id']} {r['nombre']} | {r['proveedor']} | {r['en_uso']:.0f} / {r['contratadas']:.0f} | {r['uso_pct']} % | {r['coste_ocioso']:.0f} {r['moneda']} |")
    if not res["infrautilizadas"]:
        out.append("| — | — | — | — | — |")
    out += ["", "## Sobredespliegue (en uso > contratadas)", "", "| Tecnología | Proveedor | En uso / contratadas | Exceso |", "|---|---|---|---|"]
    for r in res["sobredespliegue"]:
        out.append(f"| {r['id']} {r['nombre']} | {r['proveedor']} | {r['en_uso']:.0f} / {r['contratadas']:.0f} | {r['exceso']:.0f} |")
    if not res["sobredespliegue"]:
        out.append("| — | — | — | — |")
    out += ["", "## Coste anual por proveedor", "", "| Proveedor | Coste anual |", "|---|---|"]
    for (prov, mon), c in sorted(res["coste_por_proveedor"].items()):
        out.append(f"| {prov} | {c:.0f} {mon} |")
    if not res["coste_por_proveedor"]:
        out.append("| — | — |")
    if res["avisos"]:
        out += ["", "## Avisos", ""] + [f"- {a}" for a in res["avisos"]]
    return "\n".join(out) + "\n"
