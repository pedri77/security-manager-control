"""Análisis de brechas a partir de una evaluación de cliente."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .catalog import Control, load_all
from . import evidencias as _evid

SCORES = {"implementado": 1.0, "parcial": 0.5, "no_implementado": 0.0}
VALID_STATES = set(SCORES) | {"no_aplica"}


from datetime import date
from typing import NamedTuple
import warnings as _warnings

from . import ens as _ens
from . import mapping as _mapping
from . import plan as _plan
from .priority import prioridad


class Brecha(NamedTuple):
    """Brecha evaluada. Los 3 primeros campos coinciden con la tupla histórica (control, estado, notas)."""
    control: Control
    estado: str
    notas: str
    puntuacion: float = 0.0
    nivel: str = "P3"
    refuerzos: tuple = ()


@dataclass
class SinEvaluar:
    control: Control
    puntuacion: float
    nivel: str
    heredado_de: list[tuple[str, str]]   # [(id_equivalente, estado)] ya evaluados; sugerencia, no puntúa
    refuerzos: tuple = ()


@dataclass
class FrameworkResult:
    framework: str
    total: int
    aplicables: int
    puntuacion: float          # 0-100
    sin_evaluar: list[Control]
    brechas: list[Brecha]      # ordenadas por puntuación descendente
    sin_evidencia: list[Control]
    no_aplican: list[Control] = field(default_factory=list)       # ENS: no aplican a la categoría
    sin_evaluar_detalle: list[SinEvaluar] = field(default_factory=list)  # misma lista que sin_evaluar, con prioridad
    evidencia_caducada: list[Control] = field(default_factory=list)  # implementados con todas sus evidencias caducadas; no puntúa


@dataclass
class Analisis:
    """Resultado estructurado de `analyse`. Iterable como (cliente, results, warnings) por compatibilidad."""
    cliente: dict
    results: list[FrameworkResult]
    warnings: list[str]
    hoy: date
    categoria_ens: str | None          # normalizada; None si ENS fuera de alcance
    plan: list[_plan.Accion]
    vencidas: list[_plan.Accion]
    p1_sin_accion: list[str]           # IDs de brechas P1 que ninguna acción abierta cubre
    brechas_sin_accion: list[str]      # IDs de todas las brechas sin acción
    ens_verificar: list[str] = field(default_factory=list)   # IDs de medidas ENS con `verificar: true` (si ENS en alcance)
    verticales: object = None   # smc.verticals.ResultadoVerticales si la evaluación trae `verticales:`; si no, None

    def __iter__(self):
        return iter((self.cliente, self.results, self.warnings))


def frameworks_in_scope(cliente: dict) -> list[str]:
    fws = ["NIS2"]
    if cliente.get("sector_publico") or cliente.get("proveedor_sector_publico"):
        fws.append("ENS")
    fws += ["TRANSVERSAL", "RED"]
    return fws


ETIQUETA_MITRE = "Catálogo de casos de uso del SOC (común a todos los clientes)"
NOTA_VERIFICAR = ("dependen de las dimensiones C/I/T/A/D (aproximadas por la categoría del sistema); las 73 medidas están "
                  "contrastadas con el Anexo II del RD 311/2022 (BOE-A-2022-7191) y faltan las guías CCN-STIC")


def _estado_de(ev) -> object:
    return ev.get("estado") if isinstance(ev, dict) else None


def _heredado(control: Control, evals: dict) -> list[tuple[str, str]]:
    out = []
    for eq in sorted(_mapping.equivalentes(control.id)):
        estado = _estado_de(evals.get(eq))
        if estado in SCORES:
            out.append((eq, estado))
    return out


def analyse(assessment: dict, hoy: date | None = None) -> Analisis:
    hoy = hoy or date.today()
    warnings: list[str] = []
    if not isinstance(assessment, dict):
        warnings.append("La evaluación no es un mapa YAML: se trata como vacía")
        assessment = {}
    cliente = assessment.get("cliente")
    if not isinstance(cliente, dict):
        if cliente is not None:
            warnings.append("'cliente' no es un mapa: se ignora")
        cliente = {}
    evals = assessment.get("evaluaciones")
    if not isinstance(evals, dict):
        if evals:
            warnings.append("'evaluaciones' no es un mapa: se ignora")
        evals = {}
    catalogs = load_all()
    known = {c.id for cs in catalogs.values() for c in cs}
    warnings += [f"Control desconocido en la evaluación: {cid}" for cid in evals if cid not in known]

    scope = frameworks_in_scope(cliente)
    categoria = None
    if "ENS" in scope:
        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always")
            categoria = _ens.normalizar(cliente.get("categoria_ens"))
        warnings += [str(w.message) for w in caught]

    results = []
    for fw in scope:
        controls = catalogs[fw]
        sin_evaluar, brechas, sin_evidencia, no_aplican, detalle, caducadas = [], [], [], [], [], []
        score_sum, aplicables = 0.0, 0
        for c in controls:
            if fw == "ENS" and not _ens.aplica(c, categoria):
                no_aplican.append(c)
                continue
            ref = tuple(_ens.refuerzos(c, categoria)) if fw == "ENS" else ()
            ev = evals.get(c.id)
            estado = _estado_de(ev)
            if ev is not None and not isinstance(ev, dict):
                warnings.append(f"{c.id}: evaluación mal formada (no es un mapa); cuenta como sin evaluar")
                ev = None
            elif ev is not None and estado not in VALID_STATES:
                warnings.append(f"{c.id}: estado no válido '{estado}'; cuenta como sin evaluar")
                ev = None
            if ev is None:
                sin_evaluar.append(c)
                aplicables += 1
                p, n = prioridad(c, None, cliente)
                detalle.append(SinEvaluar(c, p, n, _heredado(c, evals), ref))
                continue
            if estado == "no_aplica":
                continue
            aplicables += 1
            score_sum += SCORES[estado]
            if estado != "implementado":
                p, n = prioridad(c, estado, cliente)
                brechas.append(Brecha(c, estado, ev.get("notas", "") or "", p, n, ref))
            elif not ev.get("evidencias"):
                sin_evidencia.append(c)
            elif _evid.todas_caducadas(ev.get("evidencias"), hoy):
                caducadas.append(c)
        puntuacion = round(100 * score_sum / aplicables, 1) if aplicables else 100.0
        brechas.sort(key=lambda b: (-b.puntuacion, b.control.id))
        detalle.sort(key=lambda d: (-d.puntuacion, d.control.id))
        results.append(FrameworkResult(fw, len(controls), aplicables, puntuacion, sin_evaluar, brechas,
                                       sin_evidencia, no_aplican, detalle, caducadas))

    pa = assessment.get("plan_accion")
    if pa not in (None, []) and not isinstance(pa, list):
        warnings.append("'plan_accion' no es una lista: se ignora")
    plan = _plan.cargar_plan(assessment)
    todas = [b for r in results for b in r.brechas]
    sin_accion = _plan.brechas_sin_accion(todas, plan)
    p1 = [b.control.id for b in todas if b.nivel == "P1" and b.control.id in set(sin_accion)]
    p1.sort(key=lambda i: next(-b.puntuacion for b in todas if b.control.id == i))
    verificar = [c.id for c in catalogs["ENS"] if c.extra.get("verificar")] if "ENS" in scope else []
    vert = None
    if assessment.get("verticales") is not None:
        from . import verticals as _vert
        vert = _vert.evaluar(assessment, estricto=False)
        warnings += [f"verticales: {w}" for w in vert.warnings] + [f"verticales: {e}" for e in vert.errores]
    return Analisis(cliente, results, warnings, hoy, categoria, plan, _plan.vencidas(plan, hoy), p1, sin_accion,
                    verificar, vert)


def url_https(url) -> bool:
    """Solo se enlazan URLs https:// (nada de javascript:, data:, http:)."""
    return isinstance(url, str) and url.startswith("https://") and not any(c.isspace() or c in '<>"' for c in url)


def md_texto(valor) -> str:
    """Escapa texto libre para una celda o línea de Markdown: `<`, `>` y `|` (y saltos de línea)."""
    t = " ".join(str(valor if valor is not None else "").split())
    return t.replace("<", "&lt;").replace(">", "&gt;").replace("|", "\\|")


def estado_vertical(r) -> str:
    """Texto de estado de una vertical; el paraguas que no puntúa lo dice y dice dónde se detalla."""
    if getattr(r, "puntua", True) is False:
        hijas = ", ".join(i.removeprefix("VRT-") for i in r.detallada_en)
        if len(r.detallada_en) > 1:
            hijas = hijas.rsplit(", ", 1)[0] + " y " + hijas.rsplit(", ", 1)[1]
        return f"no puntúa (detallada en {hijas})"
    return r.estado


def render_verticales_md(res, catalogo=None) -> str:
    """Sección Markdown de verticales: madurez, no evaluables con su motivo y recursos públicos."""
    from .verticals import cargar_verticales
    catalogo = {v.id: v for v in (catalogo if catalogo is not None else cargar_verticales())}
    media = "—" if res.madurez_media is None else f"{res.madurez_media} / 5"
    out = ["## Verticales", "", f"Madurez media de las verticales evaluadas: {media}", "",
           "| Vertical | Estado | Madurez (0-5) | Producto |", "|---|---|---|---|"]
    for r in res.verticales:
        mad = "—" if (r.madurez is None or not r.puntua) else str(r.madurez)
        out.append(f"| {md_texto(r.id)} {md_texto(r.nombre)} | {md_texto(estado_vertical(r))} | {mad} | {md_texto(r.producto) or '—'} |")
    if res.no_evaluables:
        out += ["", "### No evaluables", ""]
        out += [f"- {md_texto(r.id)} {md_texto(r.nombre)}: {md_texto(r.motivo)}" for r in res.no_evaluables]
    enlaces = []
    for r in res.verticales:
        v = catalogo.get(r.id)
        if v and r.estado != "sin_evaluar":
            enlaces += [f"- {r.id}: [{md_texto(x['titulo'])}]({x['url']})" for x in v.recursos if url_https(x.get("url"))]
    if enlaces:
        out += ["", "### Recursos públicos", ""] + enlaces
    if res.warnings or res.errores:
        out += ["", "### Avisos de verticales", ""] + [f"- {md_texto(w)}" for w in res.warnings + res.errores]
    return "\n".join(out) + "\n"


def _num_md(x, dec: int = 0) -> str:
    import math
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        return "—"
    return f"{x:.{dec}f}"


def render_v06_md(registry=None, hoy: date | None = None, mitre_datos: dict | None = None) -> str:
    """Secciones v0.6 en Markdown: tecnologías, reglas y suscripciones (si hay `registry`, dict o ruta) y
    madurez MITRE (siempre). Cálculo en `smc.tech` y `smc.mitre`. Texto libre por `md_texto`."""
    from . import mitre, tech
    hoy = hoy or date.today()
    out: list[str] = []
    if registry is not None:
        if isinstance(registry, (str, Path)):
            registry = _load(Path(registry))
        if not isinstance(registry, dict) or not isinstance(registry.get("technologies"), list):
            raise ValueError("no es un registro de tecnologías (falta la lista 'technologies')")
        filas = tech.evaluar_tecnologias(registry)
        out += ["## Tecnologías evaluadas", "", "| Tecnología | Vertical | Cobertura | Configuración | Madurez (0-5) | Avisos |",
                "|---|---|---|---|---|---|"]
        for f in filas:
            cob = "—" if f["cobertura_pct"] is None else f"{_num_md(f['cobertura_pct'])} %"
            out.append(f"| {md_texto(f['id'])} {md_texto(f['nombre'])} | {md_texto(f['vertical']) or '—'} | {cob} | "
                       f"{md_texto(f['configuracion'])} | {_num_md(f['madurez'], 1) if f['madurez'] is not None else '—'} | "
                       f"{md_texto('; '.join(f['avisos'])) or '—'} |")
        r = tech.reglas(registry, hoy)
        out += ["", "## Estado de las reglas", "",
                f"Revisadas: {len(r['revisadas'])} · Sin revisar o caducadas: {len(r['sin_revisar'])} · "
                f"No evaluables: {len(r['no_evaluables'])} · Con any-any: {len(r['any_any'])}"]
        if r["any_any"]:
            out += ["", "**ATENCIÓN: reglas any-any**", ""]
            out += [f"- {md_texto(f['id'])} {md_texto(f['nombre'])}: {f['reglas_any_any']} (estado: {md_texto(f['estado'])})"
                    for f in r["any_any"]]
        if r["sin_revisar"]:
            out += ["", "### Sin revisar o revisión caducada", ""]
            out += [f"- {md_texto(f['id'])} {md_texto(f['nombre'])}: última revisión {f['ultima_revision'] or 'nunca'}"
                    for f in r["sin_revisar"]]
        if r["no_evaluables"]:
            out += ["", "### No evaluables", ""]
            out += [f"- {md_texto(f['id'])} {md_texto(f['nombre'])}: {md_texto(f['motivo'])}" for f in r["no_evaluables"]]
        if r["avisos"]:
            out += ["", "### Avisos de reglas", ""] + [f"- {md_texto(a)}" for a in r["avisos"]]
        sb = tech.suscripciones(registry, hoy)
        tot: dict[str, float] = {}
        for (_p, mon), c in sb["coste_por_proveedor"].items():
            tot[mon] = tot.get(mon, 0.0) + (c if _num_md(c) != "—" else 0.0)
        out += ["", "## Suscripciones", "",
                "Coste anual total: " + (" + ".join(f"{_num_md(v)} {md_texto(m)}" for m, v in sorted(tot.items(), key=lambda kv: str(kv[0]))) or "—"), "",
                "### Vencen en 90 días", ""]
        out += [f"- {x['fecha']} · {md_texto(x['id'])} {md_texto(x['nombre'])} ({md_texto(x['proveedor'])}, "
                f"{_num_md(x['coste_anual'])} {md_texto(x['moneda'])})" for x in sb["renovaciones"]] or ["- Ninguna"]
        out += ["", f"### Uso bajo el umbral del {_num_md(tech.UMBRAL_INFRAUSO * 100)} %", ""]
        out += [f"- {md_texto(x['id'])} {md_texto(x['nombre'])}: {_num_md(x['uso_pct'], 1)} % en uso"
                for x in sb["infrautilizadas"]] or ["- Ninguna"]
        if sb["avisos"]:
            out += ["", "### Avisos de suscripciones", ""] + [f"- {md_texto(a)}" for a in sb["avisos"]]
        out.append("")
    datos = mitre_datos if mitre_datos is not None else {"madurez": mitre.madurez(hoy=hoy), "sin_playbook": mitre.sin_playbook()}
    m = datos["madurez"]
    out += ["## Madurez MITRE ATT&CK", "", f"**{ETIQUETA_MITRE}.** No describe al cliente: es la cobertura del SOC.", "",
            f"Técnicas con caso de uso: {len(m['tecnicas'])} · Casos de uso: {len(m['casos'])}", "",
            "| Táctica | Madurez (0-5) |", "|---|---|"]
    out += [f"| {md_texto(t)} | {n} |" for t, n in m["tacticas"].items()]
    out += ["", f"### Casos sin playbook ({len(datos['sin_playbook'])})", ""]
    out += [f"- {md_texto(i)}" for i in datos["sin_playbook"]] or ["- Ninguno"]
    return "\n".join(out) + "\n"


def _plan_section(an: Analisis) -> str:
    todas = [b for r in an.results for b in r.brechas]
    md = _plan.render_plan_md(an.plan, an.hoy, todas)
    if an.p1_sin_accion:
        md += (f"\n**AVISO: {len(an.p1_sin_accion)} brecha(s) P1 sin acción:** "
               + ", ".join(an.p1_sin_accion) + "\n")
    return md


def _marca(c: Control) -> str:
    return " (verificar)" if c.extra.get("verificar") else ""


def render_markdown(an: Analisis | dict, results=None, warnings=None, registry=None) -> str:
    if not isinstance(an, Analisis):   # compatibilidad con la firma antigua (cliente, results, warnings)
        an = Analisis(an, results, warnings or [], date.today(), None, [], [], [], [])
    cliente, results, warnings = an.cliente, an.results, an.warnings
    out = [f"# Informe de brechas — {cliente.get('nombre', 'cliente')}", ""]
    out.append(
        f"- Sector: {cliente.get('sector', '—')} · Entidad NIS2: {cliente.get('tipo_entidad_nis2', '—')}"
        f" · Sector público: {'sí' if cliente.get('sector_publico') else 'no'}"
        + (f" · Categoría ENS: {an.categoria_ens}" if an.categoria_ens else "")
    )
    out.append(f"- Fecha: {cliente.get('fecha', '—')}")
    out += ["", "## Resumen", "", "| Marco | Controles | Aplicables | Cumplimiento | Brechas | Sin evaluar | No aplican |",
            "|---|---|---|---|---|---|---|"]
    for r in results:
        out.append(f"| {r.framework} | {r.total} | {r.aplicables} | {r.puntuacion}% | {len(r.brechas)} | "
                   f"{len(r.sin_evaluar)} | {len(r.no_aplican)} |")
    if an.ens_verificar:
        out += ["", f"> **Aviso ENS:** {len(an.ens_verificar)} medidas ENS {NOTA_VERIFICAR} "
                "(`verificar`); «no aplica» y los refuerzos por categoría pueden variar según esas dimensiones. "
                "Se marcan con (verificar)."]
    for r in results:
        out += ["", f"## {r.framework}"]
        if r.brechas:
            out += ["", "### Brechas (por prioridad)", "", "| P | Control | Título | Estado | Refuerzos ENS | Notas |",
                    "|---|---|---|---|---|---|"]
            for b in r.brechas:
                out.append(f"| {b.nivel} | {b.control.id}{_marca(b.control)} | {b.control.titulo} | {b.estado} | "
                           f"{', '.join(b.refuerzos) or '—'} | {b.notas} |")
        if r.sin_evidencia:
            out += ["", "### Implementados sin evidencia (revisar)", ""]
            out += [f"- {c.id} — {c.titulo}" for c in r.sin_evidencia]
        if r.evidencia_caducada:
            out += ["", f"### Evidencia caducada ({len(r.evidencia_caducada)})", "",
                    "> **Aviso:** todas las evidencias de estos controles han caducado; renovarlas. "
                    "No afecta a la puntuación de cumplimiento.", ""]
            out += [f"- {c.id} — {c.titulo}" for c in r.evidencia_caducada]
        if r.sin_evaluar_detalle:
            out += ["", f"### Sin evaluar ({len(r.sin_evaluar)})", ""]
            for d in r.sin_evaluar_detalle:
                line = f"- {d.nivel} · {d.control.id}{_marca(d.control)} — {d.control.titulo}"
                if d.refuerzos:
                    line += f" · refuerzos: {', '.join(d.refuerzos)}"
                if d.heredado_de:
                    line += " · heredado (sugerencia, no puntúa): " + ", ".join(f"{i} {e}" for i, e in d.heredado_de)
                out.append(line)
        if r.no_aplican:
            out += ["", f"### No aplican a la categoría {an.categoria_ens} ({len(r.no_aplican)})", ""]
            out += [f"- {c.id}{_marca(c)} — {c.titulo} (mínima {c.extra.get('categoria_minima', '—')})"
                    for c in r.no_aplican]
    if an.verticales is not None:
        out += ["", render_verticales_md(an.verticales).rstrip("\n")]
    out += ["", render_v06_md(registry, an.hoy).rstrip("\n")]
    out += ["", _plan_section(an).rstrip("\n")]
    if warnings:
        out += ["", "## Avisos", ""] + [f"- {w}" for w in warnings]
    return "\n".join(out) + "\n"


def _load(path: Path) -> dict:
    texto = Path(path).read_text(encoding="utf-8")
    try:
        return yaml.safe_load(texto)
    except (KeyError, IndexError, AttributeError) as exc:
        # Un escalar que no cumple su tag explicito (a: !!bool abc) escapa de PyYAML sin ser YAMLError.
        raise ValueError("el YAML no es válido (valor que no cumple su tag explícito)") from exc


def run(path: Path, hoy: date | None = None, registry=None) -> str:
    return render_markdown(analyse(_load(path), hoy), registry=registry)


def run_plan(path: Path, hoy: date | None = None) -> str:
    return _plan_section(analyse(_load(path), hoy))
