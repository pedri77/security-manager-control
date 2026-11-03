"""CLI de Security Manager Control."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from . import __version__
from .catalog import load_all, validar_v05, validar_v07, validate
from .gap import run, run_plan


def _fecha(v: str):
    from datetime import date
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise argparse.ArgumentTypeError(f"fecha no válida '{v}' (AAAA-MM-DD)")


_ERRORES_DATOS = (ValueError, OSError, yaml.YAMLError)   # OffensiveError y AIActError son ValueError


def _error(ruta, exc) -> int:
    print(f"ERROR: {ruta}: {exc}", file=sys.stderr)
    return 2


def _comando_v07(args) -> int:
    """smc pentest | purple | ai | pmo. rc 0 correcto, 2 fichero o datos no válidos."""
    from . import ai_act, offensive, pmo
    ruta = args.fichero if args.cmd in ("pentest", "purple") else getattr(args, "inventario", None) or args.proyecto
    try:
        if args.cmd == "pentest":
            print(offensive.render_markdown(pentest=offensive.estado_hallazgos(ruta, args.hoy)), end="")
        elif args.cmd == "purple":
            print(offensive.render_markdown(purple_res=offensive.purple(ruta, args.hoy)), end="")
        elif args.cmd == "ai":
            res = ai_act.obligaciones(ruta, args.hoy, estricto=False)
            print(ai_act.render_markdown(res, ai_act.riesgos_agente(ruta)), end="")
        else:
            from .gap import _load
            for nombre in ("registry", "assessment"):
                r = getattr(args, nombre)
                if r is not None and not r.is_file():
                    return _error(r, "no existe")
            ass = _load(args.assessment) if args.assessment else None
            proyecto = pmo.cargar_proyecto(ruta)
            print(pmo.render_markdown(pmo.analizar(proyecto, args.hoy, ass, args.registry)), end="")
            if args.ics:
                pmo.exportar_ics(proyecto, args.ics, args.hoy)
                print(f"Calendario escrito en {args.ics}", file=sys.stderr)
    except _ERRORES_DATOS as exc:
        return _error(ruta, exc)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="smc", description="Security Manager Control")
    parser.add_argument("--version", action="version", version=f"smc {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate", help="Valida los catálogos de controles")
    sub.add_parser("list", help="Muestra el número de controles por marco")
    gap = sub.add_parser("gap", help="Genera el informe de brechas de una evaluación")
    gap.add_argument("assessment", type=Path)
    gap.add_argument("-o", "--output", type=Path, help="Fichero Markdown de salida")
    gap.add_argument("--hoy", type=_fecha, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    pl = sub.add_parser("plan", help="Plan de acción: acciones, vencidas y brechas sin acción")
    pl.add_argument("assessment", type=Path)
    pl.add_argument("--hoy", type=_fecha, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")

    rp = sub.add_parser("report", help="Informe HTML autocontenido de una evaluación")
    rp.add_argument("assessment", type=Path)
    rp.add_argument("-o", "--output", type=Path, required=True, help="Fichero HTML de salida")
    rp.add_argument("--hoy", type=_fecha, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    rp.add_argument("--registry", type=Path, help="Registro de tecnologías YAML: añade tecnologías, reglas y suscripciones")
    rp.add_argument("--pentest", type=Path, help="Seguimiento de pentest (YAML): añade la sección de hallazgos")
    rp.add_argument("--purple", type=Path, help="Ejercicios purple team (YAML): añade la sección y cuenta los detectados en la madurez MITRE")
    rp.add_argument("--ai", type=Path, help="Inventario de IA (YAML): añade RIA y seguridad de agentes")
    rp.add_argument("--pmo", type=Path, help="Proyecto PMO (YAML): añade costes, EVM y alertas")

    db = sub.add_parser("dashboard", help="Dashboard estático multicliente desde un directorio de evaluaciones")
    db.add_argument("directorio", type=Path)
    db.add_argument("-o", "--output", type=Path, required=True, help="Directorio de salida")
    db.add_argument("--hoy", type=_fecha, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")

    soc = sub.add_parser("soc", help="Métricas del SOC (MTTD/MTTA/MTTC/MTTR, SLA) desde CSV de incidentes")
    soc.add_argument("incidents", type=Path)
    mi = sub.add_parser("mitre", help="Cobertura y madurez MITRE ATT&CK de los casos de uso")
    mi.add_argument("--navigator", action="store_true", help="Exporta la capa ATT&CK Navigator (JSON)")
    mi.add_argument("-o", "--output", type=Path, help="Fichero de salida del export Navigator")
    mi.add_argument("--hoy", type=_fecha, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    mi.add_argument("--purple", type=Path, help="Ejercicios purple team (YAML): un ejercicio detectado cuenta como prueba del caso de uso")
    pt = sub.add_parser("pentest", help="Hallazgos de pentest: abiertos, fuera de SLA, retest pendiente")
    pt.add_argument("fichero", type=Path)
    pt.add_argument("--hoy", type=_fecha, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    pu = sub.add_parser("purple", help="Ejercicios purple team: cobertura por táctica, no detectadas, mejoras")
    pu.add_argument("fichero", type=Path)
    pu.add_argument("--hoy", type=_fecha, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    ia = sub.add_parser("ai", help="RIA (Reglamento (UE) 2024/1689) y seguridad de agentes desde un inventario de IA")
    ia.add_argument("inventario", type=Path)
    ia.add_argument("--hoy", type=_fecha, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    pm = sub.add_parser("pmo", help="PMO: presupuesto, horas, EVM y alertas de un proyecto")
    pm.add_argument("proyecto", type=Path)
    pm.add_argument("--ics", type=Path, help="Exporta los eventos a un fichero iCalendar (.ics)")
    pm.add_argument("--registry", type=Path, help="Registro de tecnologías YAML: suma las suscripciones")
    pm.add_argument("--assessment", type=Path, help="Evaluación del cliente (YAML): valida las acciones y hereda controles")
    pm.add_argument("--hoy", type=_fecha, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    vt = sub.add_parser("verticals", help="Madurez por vertical y por medida NIS2 de una evaluación")
    vt.add_argument("assessment", type=Path)
    te = sub.add_parser("tech", help="Evaluación de tecnologías y estado de reglas")
    te.add_argument("registry", type=Path)
    te.add_argument("--hoy", type=_fecha, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    te.add_argument("--days", type=int, default=180, help="Días sin revisar las reglas (180)")
    sb = sub.add_parser("subs", help="Suscripciones: renovaciones, infrautilización y coste")
    sb.add_argument("registry", type=Path)
    sb.add_argument("--hoy", type=_fecha, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    sb.add_argument("--days", type=int, default=90, help="Ventana de renovaciones en días (90)")
    pr = sub.add_parser("protocols", help="Vulnerabilidades por protocolo (lista por capa OSI o detalle de un ID)")
    pr.add_argument("id", nargs="?")
    rs = sub.add_parser("rss", help="Catálogo de fuentes RSS y ecosistema; --opml exporta OPML")
    rs.add_argument("--opml", action="store_true")
    rs.add_argument("-o", "--output", type=Path, help="Fichero de salida del OPML")
    mp = sub.add_parser("mapa", help="Exporta el mapa de dispositivos (JSON smc-mapa/1) para el visor 3D")
    mp.add_argument("registry", type=Path)
    mp.add_argument("--inventario", type=Path, help="Inventario de recursos internos (YAML)")
    mp.add_argument("--tracker", type=Path, help="Seguimiento de vulnerabilidades (CSV)")
    mp.add_argument("--evaluacion", type=Path, help="Evaluación (YAML) para la madurez por vertical")
    mp.add_argument("-o", "--output", type=Path, help="Fichero JSON de salida (por defecto, stdout)")
    mp.add_argument("--hoy", type=_fecha, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    mp.add_argument("--days", type=int, default=180, help="Días sin revisar las reglas (180)")
    vi = sub.add_parser("visor", help="Visor 3D offline (HTML autocontenido) desde un mapa smc-mapa/1")
    vi.add_argument("mapa", type=Path, help="JSON generado por `smc mapa`")
    vi.add_argument("-o", "--output", type=Path, required=True, help="Fichero HTML de salida")
    exp = sub.add_parser("expiring", help="Caducidades del registro de tecnologías")
    exp.add_argument("registry", type=Path)
    exp.add_argument("--days", type=int, default=90)
    vul = sub.add_parser("vulns", help="Estado de CVEs y SLA de remediación")
    vul.add_argument("tracker", type=Path)
    ref = sub.add_parser("refs", help="Normativa NIS2 y guías CCN-CERT asociadas a un control")
    ref.add_argument("control")

    args = parser.parse_args(argv)

    if args.cmd == "refs":
        from .refs import render_refs
        print(render_refs(args.control))
        return 0

    if args.cmd == "soc":
        from .soc import render_soc, soc_metrics
        print(render_soc(soc_metrics(args.incidents)))
        return 0
    if args.cmd in ("pentest", "purple", "ai", "pmo"):
        return _comando_v07(args)
    if args.cmd == "mitre":
        purple = None
        if args.purple:
            from . import offensive
            try:
                purple = offensive.cargar_purple(args.purple)
            except _ERRORES_DATOS as exc:
                return _error(args.purple, exc)
        if args.navigator:
            import json
            from .mitre import a_navigator
            texto = json.dumps(a_navigator(hoy=args.hoy, purple=purple), ensure_ascii=False, indent=2) + "\n"
            if args.output:
                args.output.write_text(texto, encoding="utf-8")
                print(f"Capa Navigator escrita en {args.output}")
            else:
                print(texto, end="")
            return 0
        from .soc import mitre_coverage
        print(mitre_coverage(hoy=args.hoy, purple=purple))
        return 0
    if args.cmd == "verticals":
        from .gap import _load, render_verticales_md
        from .verticals import VerticalesError, evaluar
        try:
            res = evaluar(_load(args.assessment))
        except VerticalesError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        print(render_verticales_md(res))
        return 0
    if args.cmd in ("tech", "subs"):
        from . import tech
        if args.cmd == "tech":
            print(tech.render_evaluacion(tech.evaluar_tecnologias(args.registry)))
            print(tech.render_reglas(tech.reglas(args.registry, args.hoy, args.days), args.hoy, args.days))
        else:
            print(tech.render_suscripciones(tech.suscripciones(args.registry, args.hoy, args.days), args.hoy, args.days))
        return 0
    if args.cmd == "mapa":
        import json
        from . import mapa
        for nombre in ("registry", "inventario", "tracker", "evaluacion"):
            ruta = getattr(args, nombre)
            if ruta is not None and not ruta.is_file():
                print(f"ERROR: no existe {ruta}", file=sys.stderr)
                return 2
        try:
            m = mapa.construir_mapa(args.registry, args.inventario, args.tracker, args.evaluacion, args.hoy, args.days)
        except Exception as exc:  # YAML/CSV mal formados
            print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        texto = json.dumps(m, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(texto, encoding="utf-8")
        else:
            print(texto, end="")
        return 0
    if args.cmd == "visor":
        import json
        from .visor import generar_visor
        try:
            datos = json.loads(args.mapa.read_text(encoding="utf-8"))
            if not isinstance(datos, dict):
                raise ValueError("el JSON no es un objeto smc-mapa/1")
            pagina = generar_visor(datos)
        except (OSError, ValueError) as exc:  # JSONDecodeError y UnicodeDecodeError son ValueError
            print(f"ERROR: {args.mapa}: {exc}", file=sys.stderr)
            return 2
        args.output.write_text(pagina, encoding="utf-8")
        print(f"Visor escrito en {args.output} ({len(pagina.encode('utf-8')) // 1024} KiB)")
        return 0
    if args.cmd == "protocols":
        from . import protocols
        if args.id:
            try:
                print(protocols.render_protocolo(args.id))
            except ValueError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 2
            return 0
        for capa, lista in protocols.por_capa().items():
            print(f"Capa {capa}: " + ", ".join(p["id"] for p in lista))
        return 0
    if args.cmd == "rss":
        from . import resources
        if args.opml:
            texto = resources.a_opml()
            if args.output:
                args.output.write_text(texto, encoding="utf-8")
                print(f"OPML escrito en {args.output}")
            else:
                print(texto, end="")
        else:
            print(resources.render_markdown())
        return 0
    if args.cmd == "expiring":
        from .tech import expiring, render_expiring
        print(render_expiring(expiring(args.registry, args.days), args.days))
        return 0
    if args.cmd == "vulns":
        from .tech import vulns
        print(vulns(args.tracker))
        return 0

    if args.cmd == "validate":
        from .refs import validate_refs
        errors = validate() + validate_refs() + validar_v05() + validar_v07()
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        if not errors:
            print("Catálogos OK")
        return 1 if errors else 0

    if args.cmd == "list":
        for fw, controls in load_all().items():
            print(f"{fw:12} {len(controls):3} controles")
        return 0

    if args.cmd == "plan":
        print(run_plan(args.assessment, args.hoy))
        return 0

    if args.cmd == "report":
        from .report_html import cargar_registry, run_html
        try:
            reg = cargar_registry(args.registry) if args.registry else None
        except ValueError as exc:
            print(f"ERROR: --registry {args.registry}: {exc}", file=sys.stderr)
            return 2
        try:
            html = run_html(args.assessment, args.hoy, reg, args.pentest, args.purple, args.ai, args.pmo)
        except _ERRORES_DATOS as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        args.output.write_text(html, encoding="utf-8")
        print(f"Informe escrito en {args.output}")
        return 0

    if args.cmd == "dashboard":
        from .dashboard import generar
        if not args.directorio.is_dir():
            print(f"ERROR: {args.directorio} no es un directorio", file=sys.stderr)
            return 2
        res = generar(args.directorio, args.output, args.hoy)
        for a in res.avisos:
            print(f"AVISO: {a.fichero}: {a.motivo}", file=sys.stderr)
        print(f"Dashboard escrito en {args.output / 'index.html'} ({len(res.filas)} cliente(s), {len(res.avisos)} aviso(s))")
        return 0

    if args.cmd == "gap":
        report = run(args.assessment, args.hoy)
        if args.output:
            args.output.write_text(report, encoding="utf-8")
            print(f"Informe escrito en {args.output}")
        else:
            print(report)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
