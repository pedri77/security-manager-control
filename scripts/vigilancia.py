#!/usr/bin/env python3
"""vigilancia.py — vigilancia diaria de dependencias (SMC-009).

Solo usa la librería estándar y la CLI `gh`. Lee la salida de `osv-scanner scan source -r --format json` y el código
de salida con el que terminó, y mantiene una única issue abierta con el título `[vigilancia] vulnerabilidades en
dependencias`.

Uso (lo llama .github/workflows/vigilancia.yml):
  python3 scripts/vigilancia.py --code "$code" --json osv.json

Código de salida de osv-scanner (medido con la imagen fijada, v2.7.0):
  0    sin hallazgos; stdout lleva `{"results": [], ...}`.
  1    con hallazgos; `results[].packages[].{package, groups, vulnerabilities}`.
  128  sin paquetes que escanear (stdout vacío). Misma regla que `sca`: un manifiesto versionado sin lockfile es rojo.
  otro (127 ruta u opción inválida, 130, 137...) o JSON ilegible o incoherente con el código: error del escáner.
       Nunca se toma por «sin hallazgos» y no toca ninguna issue.

Código de salida de este script:
  0 limpio · 1 hallazgos (issue creada o actualizada) · 2 error del escáner o de `gh` · 3 manifiesto sin lockfile.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

TITLE = "[vigilancia] vulnerabilidades en dependencias"
LABEL = "security"
# Autor de la issue que crea este flujo con GITHUB_TOKEN, medido con `gh issue list --json author` en un repo público:
# {"is_bot": true, "login": "app/github-actions"}. (`gh search issues` lo muestra como `github-actions[bot]`.)
BOT_LOGIN = "app/github-actions"
# Listas blancas de los campos que vienen del escáner (tercero) y acaban en una issue pública. Solo ASCII, sin espacios,
# sin saltos de línea ni caracteres de control, y nada de `|` (tabla), `` ` ``, `<`, `>`, `!`, `[`, `]`, `(`, `)`, `#`,
# `&` ni `\`. `@` solo en el nombre del paquete (npm: `@scope/paquete`) y se muestra siempre en código.
NAME_RE = re.compile(r"[A-Za-z0-9@][A-Za-z0-9._+:/~@-]{0,99}")
VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+:~-]{0,63}")
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}")
INVALID = "(valor no válido)"
MANIFEST = re.compile(r"(^|/)(pyproject\.toml|package\.json|go\.mod|Cargo\.toml)$")


class Error(Exception):
    pass


def _fixed(vulns, name):
    out = set()
    for v in vulns:
        for a in v.get("affected", []):
            if a.get("package", {}).get("name", name) != name:
                continue
            for r in a.get("ranges", []):
                for e in r.get("events", []):
                    if "fixed" in e:
                        out.add(str(e["fixed"]))
    # (0, número) antes que (1, texto): mezclar «1.11rc1» y «2.0.0» no debe comparar int con str.
    return sorted(out, key=lambda s: [(0, int(x), "") if x.isdigit() else (1, 0, x) for x in re.split(r"[.\-]", s)])


def _sort_key(h):
    return (h["package"], h["version"], h["id"])


def findings(data):
    """Un hallazgo por grupo de osv-scanner (alias de un mismo problema), ordenado y sin datos del entorno."""
    out = []
    for res in data["results"]:
        for pk in res["packages"]:
            p = pk["package"]
            by_id = {v["id"]: v for v in pk.get("vulnerabilities", [])}
            for g in pk.get("groups", []):
                vs = [by_id[i] for i in g["ids"] if i in by_id]
                aliases = sorted({a for a in g.get("aliases", []) if a != g["ids"][0]},
                                 key=lambda a: (not a.startswith("CVE-"), a))
                out.append({"package": p["name"], "version": p["version"], "ecosystem": p.get("ecosystem", ""),
                            "id": g["ids"][0], "aliases": aliases, "fixed": _fixed(vs, p["name"])})
    return sorted(out, key=_sort_key)


def _cell(value, rx):
    """Valor del escáner apto para una celda: pasa la lista blanca y va ENTERO dentro de código en línea, o se sustituye.

    En código en línea GitHub no forma menciones (`@org/team`), ni enlaces automáticos (`www.evil.com/login`, que no lleva
    `://`), ni referencias a issues (`GH-12`), ni formato (`a~~b~~c`), ni notifica. Por eso la lista blanca ya no puede
    contener la comilla invertida (cerraría el código) ni `|` (rompería la tabla). Lo que no cumple se sustituye por
    INVALID, que es texto fijo nuestro.
    """
    if not isinstance(value, str) or not rx.fullmatch(value) or "://" in value:
        return INVALID
    return f"`{value}`"


ARTIFACT = "osv-vigilancia"   # artefacto del workflow con el JSON completo de osv-scanner (90 días)
MAX_FIXED = 10          # versiones corregidas por fila; el resto se resume
MAX_BODY = 60000        # por debajo de los 65 536 caracteres de una issue o comentario de GitHub


def _row(h):
    ident = _cell(h["id"], ID_RE)
    cve = h["aliases"][0] if h["aliases"] and isinstance(h["aliases"][0], str) \
        and h["aliases"][0].startswith("CVE-") else None
    if cve is not None and _cell(cve, ID_RE) != INVALID:
        ident += f" ({_cell(cve, ID_RE)})"
    if h["fixed"]:
        fixed = ", ".join(_cell(f, VERSION_RE) for f in h["fixed"][:MAX_FIXED])
        if len(h["fixed"]) > MAX_FIXED:
            fixed += f" y {len(h['fixed']) - MAX_FIXED} más"
    else:
        fixed = "sin versión corregida"
    return f"| {_cell(h['package'], NAME_RE)} | {_cell(h['version'], VERSION_RE)} | {ident} | {fixed} |"


def render_body(fs):
    head = f"`osv-scanner` encuentra {len(fs)} vulnerabilidades en las dependencias de la rama principal.\n\n"
    tail = ("\n\nLa excepción, si procede, va en `osv-scanner.toml` con `reason` e `ignoreUntil`. "
            "Esta issue la mantiene `vigilancia.yml`: se actualiza sola y se cierra cuando ya no hay hallazgos.\n")
    rows = ["| Paquete | Versión | Identificador | Versión corregida |", "|---|---|---|---|"]
    size = len(head) + len(tail) + sum(len(r) + 1 for r in rows) + 200     # 200: margen para el aviso de recorte
    shown = 0
    for h in fs:
        r = _row(h)
        if size + len(r) + 1 > MAX_BODY:
            break
        rows.append(r)
        size += len(r) + 1
        shown += 1
    note = ""
    if shown < len(fs):
        note = (f"\n\nLista recortada: se muestran {shown} de {len(fs)} hallazgos por el tope de tamaño de la issue; "
                f"el JSON completo de osv-scanner está en el artefacto `{ARTIFACT}` de la ejecución de `vigilancia.yml`.")
    return head + "\n".join(rows) + note + tail


def classify(code, text):
    """(estado, hallazgos): clean | findings | no_packages | error."""
    if code == 128:
        return "no_packages", []
    if code not in (0, 1):
        return "error", []
    try:
        data = json.loads(text)
        fs = findings(data)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError):
        return "error", []
    if code == 0 and not fs:
        return "clean", []
    if code == 1 and fs:
        return "findings", fs
    return "error", []


def gh(args, stdin=None):
    r = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True)
    if r.returncode != 0:
        raise Error(f"gh {' '.join(args[:2])} falló ({r.returncode}): {r.stderr.strip()}")
    return r.stdout


def _mine(i):
    """Solo se adopta la issue que creó el bot de Actions y lleva la etiqueta: el título lo puede copiar cualquiera."""
    a = i["author"]
    return (a.get("is_bot") is True and a.get("login") == BOT_LOGIN
            and any(l["name"] == LABEL for l in i["labels"]))


def open_issue():
    raw = gh(["issue", "list", "--state", "open", "--json", "number,title,body,author,labels", "--limit", "1000"])
    try:
        issues = json.loads(raw)
        match = [i for i in issues if i["title"] == TITLE and _mine(i)]
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise Error(f"gh issue list: salida ilegible: {e}")
    return min(match, key=lambda i: i["number"]) if match else None


def manifest_without_lock():
    r = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    if r.returncode != 0:
        raise Error(f"git ls-files falló: {r.stderr.strip()}")
    return any(MANIFEST.search(f) for f in r.stdout.splitlines())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--code", type=int, required=True, help="código de salida de osv-scanner")
    ap.add_argument("--json", required=True, help="stdout de osv-scanner --format json")
    a = ap.parse_args(argv)
    try:
        with open(a.json, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        print(f"::error::No se puede leer la salida del escáner: {e}")
        return 2
    state, fs = classify(a.code, text)
    try:
        if state == "error":
            print(f"::error::Error del escáner (código {a.code}, JSON ilegible o incoherente): no se toca ninguna issue")
            return 2
        if state == "no_packages":
            if manifest_without_lock():
                print("::error::Hay manifiesto de dependencias pero ningún lockfile versionado: nada escaneado")
                return 3
            print("Sin dependencias declaradas: nada que escanear")
            return 0
        issue = open_issue()
        if state == "clean":
            if issue:
                gh(["issue", "close", str(issue["number"]), "--comment",
                    "Sin hallazgos en la última vigilancia: se cierra."])
                print(f"Sin hallazgos: issue #{issue['number']} cerrada")
            else:
                print("Sin hallazgos")
            return 0
        body = render_body(fs)
        if issue is None:
            gh(["label", "create", LABEL, "--color", "D93F0B", "--description", "Seguridad", "--force"])
            gh(["issue", "create", "--title", TITLE, "--label", LABEL, "--body-file", "-"], stdin=body)
            print(f"::error::{len(fs)} vulnerabilidades: issue creada")
        elif (issue.get("body") or "").strip() != body.strip():
            gh(["issue", "comment", str(issue["number"]), "--body-file", "-"], stdin="Los hallazgos han cambiado.\n\n" + body)
            gh(["issue", "edit", str(issue["number"]), "--body-file", "-"], stdin=body)
            print(f"::error::{len(fs)} vulnerabilidades: issue #{issue['number']} actualizada")
        else:
            print(f"::error::{len(fs)} vulnerabilidades: issue #{issue['number']} sin cambios")
        return 1
    except Error as e:
        print(f"::error::{e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
