"""Visor 3D offline del mapa de dispositivos (T20, ADR-003 y ADR-004).

API:
    generar_visor(mapa: dict) -> str     # una sola página HTML autocontenida
    python -m smc.visor mapa.json [-o visor.html]

Lee SOLO el JSON `smc-mapa/1` (ver docs/mapa-3d.md). La página no hace fetch, no carga nada de la red:
three.js (MIT, vendorizado en smc/assets, ver ADR-004) y el código del visor van dentro del HTML.
Seguridad: el JSON va en <script type="application/json"> con '<' escapado; el DOM del visor se rellena
con textContent; la tabla en texto se genera aquí con html.escape.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

from .mapa import SCHEMA, validar_mapa

ASSETS = Path(__file__).parent / "assets"
SEMAFORO_TXT = {"rojo": "ROJO", "ambar": "ÁMBAR", "gris": "GRIS (no se sabe)", "verde": "VERDE"}


def _asset(nombre: str) -> str:
    texto = (ASSETS / nombre).read_text(encoding="utf-8")
    if "</script" in texto.lower():
        raise ValueError(f"el recurso {nombre} contiene '</script' y rompería la página")
    return texto


def json_embebido(mapa: dict) -> str:
    """JSON seguro para un <script type=application/json>: '<' escapado (también cubre '</script' y '<!--')."""
    return json.dumps(mapa, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c") \
        .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def _e(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def _tabla(mapa: dict) -> str:
    cab = ["Zona", "ID", "Dispositivo", "Tipo", "Capa OSI", "Vertical", "Semáforo", "Reglas", "Any-any",
           "Vulns abiertas", "Fuera de SLA", "KEV fuera de SLA", "Motivos"]
    filas = []
    grupos = [(z["nombre"], z["dispositivos"]) for z in mapa["zonas"]] + [("Sin zona", mapa["sin_zona"])]
    for nombre, ds in grupos:
        for d in ds:
            r, v = d.get("reglas") or {}, d.get("vulnerabilidades") or {}
            estado = r.get("estado")
            reglas = f"No evaluable: {r.get('motivo')}" if estado == "no_evaluable" else estado
            sem = SEMAFORO_TXT.get(d.get("semaforo"), SEMAFORO_TXT["gris"])
            motivos = "; ".join(d.get("semaforo_motivos") or [])
            if d.get("motivo_sin_zona"):
                motivos += f" | Sin zona: {d['motivo_sin_zona']}"
            celdas = [nombre, d.get("id"), d.get("nombre"), d.get("tipo"),
                      "desconocida" if d.get("capa_osi") is None else d["capa_osi"], d.get("vertical") or "—", sem, reglas,
                      r.get("reglas_any_any"), v.get("abiertas"), v.get("fuera_sla"), v.get("kev_fuera_sla"), motivos]
            filas.append("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in celdas) + "</tr>")
    cuerpo = "\n".join(filas) or f'<tr><td colspan="{len(cab)}">Sin dispositivos</td></tr>'
    return ('<table><caption>Dispositivos del mapa (la misma información que la vista 3D)</caption><thead><tr>'
            + "".join(f'<th scope="col">{c}</th>' for c in cab) + f"</tr></thead><tbody>\n{cuerpo}\n</tbody></table>")


CSS = """
:root{color-scheme:dark;--bg:#0d1117;--pn:#161b22;--tx:#e6edf3;--mu:#9da7b3;--bd:#30363d;--rojo:#e5484d;--ambar:#f5a524;--gris:#8b949e;--verde:#30a46c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.45 system-ui,sans-serif}
header{padding:10px 16px;border-bottom:1px solid var(--bd)}h1{font-size:18px;margin:0}header p{margin:2px 0 0;color:var(--mu)}
main{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:0}
@media(max-width:800px){main{grid-template-columns:1fr}}
#escena{position:relative;height:min(62vh,640px);min-height:320px;background:#0d1117}
#lienzo{width:100%;height:100%;display:block;touch-action:none}
#sin-webgl{position:absolute;inset:0;padding:24px}
aside{background:var(--pn);border-left:1px solid var(--bd);padding:12px 14px;overflow:auto;max-height:min(62vh,640px);min-height:320px}
aside h3{margin:0 0 6px;font-size:16px}aside h4{margin:12px 0 4px;font-size:14px}
dl{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;margin:4px 0}dt{color:var(--mu)}dd{margin:0;word-break:break-word}
.disp{border-top:1px solid var(--bd);margin-top:8px;padding-top:4px}
.barra{display:flex;flex-wrap:wrap;gap:6px;padding:8px 16px;border-bottom:1px solid var(--bd)}
button{background:#21262d;color:var(--tx);border:1px solid var(--bd);border-radius:6px;padding:5px 10px;font:inherit;cursor:pointer}
button:hover{background:#30363d}button[aria-pressed=true]{outline:2px solid #58a6ff}button:focus-visible{outline:2px solid #58a6ff;outline-offset:2px}
.pt.rojo{color:var(--rojo)}.pt.ambar{color:var(--ambar)}.pt.gris{color:var(--gris)}.pt.verde{color:var(--verde)}
.leyenda{padding:6px 16px;color:var(--mu)}
section.texto{padding:12px 16px;overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border:1px solid var(--bd);padding:4px 8px;text-align:left;vertical-align:top}caption{text-align:left;color:var(--mu);padding:4px 0}
"""


def generar_visor(mapa: dict) -> str:
    """Devuelve el HTML autocontenido del visor para un mapa `smc-mapa/1` ya construido.

    Lanza ValueError si el mapa no cumple el esquema (el visor no dibuja datos que no entiende)."""
    errores = validar_mapa(mapa)
    if errores:
        raise ValueError("mapa no válido: " + "; ".join(errores[:5]))
    r = mapa["resumen"]
    por = r["por_semaforo"]
    sub = (f"Mapa para {_e(mapa['generado_para'])} · {r['dispositivos']} dispositivos "
           f"(rojo {por['rojo']}, ámbar {por['ambar']}, gris {por['gris']}, verde {por['verde']})")
    three, app = _asset("three.bundle.min.js"), _asset("visor-app.js")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:">
<title>SMC · Mapa de la red</title>
<style>{CSS}</style>
</head>
<body>
<header><h1>Mapa de la red (SMC)</h1><p>{sub}</p></header>
<nav class="barra" aria-label="Zonas" id="zonas"></nav>
<nav class="barra" aria-label="Vistas de cámara">
<button type="button" data-vista="general" aria-pressed="true">Vista general</button>
<button type="button" data-vista="planta" aria-pressed="false">Planta</button>
<button type="button" data-vista="capas" aria-pressed="false">Capas OSI</button>
<button type="button" id="b-rojos" aria-pressed="false">Solo rojos</button>
<button type="button" id="b-visita" aria-pressed="false">Visita automática</button>
</nav>
<main>
<div id="escena"><canvas id="lienzo" tabindex="0" role="img" aria-label="Maqueta 3D de la red; la misma información está en la tabla de abajo"></canvas>
<p id="sin-webgl" hidden>No se ha podido iniciar WebGL. La tabla de abajo contiene toda la información.</p></div>
<aside id="panel" aria-live="polite"></aside>
</main>
<p class="leyenda">Semáforo: rojo = vulnerabilidad KEV/crítica fuera de SLA o reglas any-any; ámbar = revisión pendiente o vulnerabilidad fuera de SLA; gris = no se puede evaluar (nunca verde); verde = revisado y sin brechas. Arrastrar para girar, rueda para acercar; cualquier gesto detiene la visita.</p>
<section class="texto" aria-label="Alternativa en texto">
{_tabla(mapa)}
</section>
<script type="application/json" id="smc-data">{json_embebido(mapa)}</script>
<script type="module">
/* three.js r186 (MIT), vendorizado: ver smc/assets/THREE-LICENSE y docs/adr/ADR-004-three-js-vendorizado.md */
{three}
{app}
</script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m smc.visor", description="Genera el visor 3D offline desde un mapa smc-mapa/1")
    ap.add_argument("mapa", help="JSON generado por `smc mapa`")
    ap.add_argument("-o", "--output", help="HTML de salida (por defecto, stdout)")
    args = ap.parse_args(argv)
    try:
        datos = json.loads(Path(args.mapa).read_text(encoding="utf-8"))
        if not isinstance(datos, dict) or datos.get("schema") != SCHEMA:
            raise ValueError(f"no es un mapa '{SCHEMA}'")
        pagina = generar_visor(datos)
    except (OSError, ValueError) as e:  # JSONDecodeError es ValueError
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.output:
        Path(args.output).write_text(pagina, encoding="utf-8")
        print(f"Visor escrito en {args.output} ({len(pagina.encode('utf-8')) // 1024} KiB)", file=sys.stderr)
    else:
        sys.stdout.write(pagina)
    return 0


if __name__ == "__main__":
    sys.exit(main())
