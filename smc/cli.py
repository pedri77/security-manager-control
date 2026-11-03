"""CLI de Security Manager Control."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .catalog import load_all, validate
from .gap import run, run_plan


def _fecha(v: str):
    from datetime import date
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise argparse.ArgumentTypeError(f"fecha no válida '{v}' (AAAA-MM-DD)")


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

    soc = sub.add_parser("soc", help="Métricas del SOC (MTTD/MTTA/MTTC/MTTR, SLA) desde CSV de incidentes")
    soc.add_argument("incidents", type=Path)
    sub.add_parser("mitre", help="Cobertura MITRE ATT&CK de los casos de uso")
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
    if args.cmd == "mitre":
        from .soc import mitre_coverage
        print(mitre_coverage())
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
        errors = validate() + validate_refs()
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
