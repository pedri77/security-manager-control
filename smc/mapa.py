"""Mapa de dispositivos: exporta el JSON `smc-mapa/1` que consumirá el visor 3D (ver docs/mapa-3d.md).

API:
    construir_mapa(registry, inventario=None, tracker=None, evaluacion=None, hoy=None) -> dict
    validar_mapa(mapa) -> list[str]        # errores del esquema; vacía si es válido

Solo se exportan campos de una lista blanca del registro y del inventario: nada de rutas, de
notas libres ni de campos que no estén descritos en el esquema. Un dispositivo sin zona (o con
una zona desconocida) va a `sin_zona`, nunca rompe. Un dato ausente da estado explícito
(`sin_datos`, `gris`), nunca verde por defecto.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import yaml

from . import tech
from .tech import POLICY_FILE

SCHEMA = "smc-mapa/1"

# Zonas de red (alineadas con NET-SEG-01). Orden = orden de dibujo en el visor.
ZONAS = {
    "perimetro": "Perímetro e Internet",
    "dmz": "DMZ",
    "usuarios": "Usuarios",
    "servidores": "Servidores",
    "gestion": "Gestión",
    "invitados": "Invitados",
    "ot_iot": "OT / IoT",
    "nube": "Nube",
}

SEMAFOROS = ("rojo", "ambar", "gris", "verde")      # de peor a mejor
ESTADOS_REGLAS_MAPA = ("revisadas", "sin_revisar", "no_evaluable", "sin_datos")
SEVERIDADES = ("critica", "alta", "media", "baja")

# Capa OSI por defecto según la vertical, solo si el dispositivo no declara `capa_osi`.
CAPA_POR_VERTICAL = {
    "VRT-NET": 3, "VRT-FW": 4, "VRT-OT": 2,
    "VRT-SASE": 7, "VRT-ZTNA": 7, "VRT-MAIL": 7, "VRT-APP": 7, "VRT-EDR": 7,
    "VRT-MDM": 7, "VRT-ENDUSER": 7, "VRT-HUNT": 7, "VRT-IAM": 7,
}


def _yaml(v) -> dict:
    if isinstance(v, (str, Path)):
        v = yaml.safe_load(Path(v).read_text(encoding="utf-8"))
    return v if isinstance(v, dict) else {}


def _lista(d: dict, clave: str) -> list[dict]:
    v = d.get(clave)
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def _capa(valor, vertical) -> tuple[int | None, str]:
    if isinstance(valor, int) and not isinstance(valor, bool) and 1 <= valor <= 7:
        return valor, "declarada"
    if vertical in CAPA_POR_VERTICAL:
        return CAPA_POR_VERTICAL[vertical], "vertical"
    return None, "desconocida"


def _zona(valor) -> str | None:
    z = str(valor).strip().lower() if valor not in (None, "") else ""
    return z if z in ZONAS else None


def _dispositivos(registry: dict, inventario: dict, avisos: list[str]) -> list[dict]:
    """Une tecnologías del registro y activos del inventario en una lista plana (sin duplicar IDs)."""
    out, vistos = [], set()

    def anadir(d: dict, origen: str, tipo: str):
        did = d.get("id")
        if not did or str(did) in vistos:
            avisos.append(f"{did or '(sin id)'}: dispositivo sin id o duplicado, se ignora")
            return
        vistos.add(str(did))
        vertical = d.get("vertical") if isinstance(d.get("vertical"), str) else None
        capa, origen_capa = _capa(d.get("capa_osi"), vertical)
        zona_decl = d.get("zona")
        zona = _zona(zona_decl)
        item = {"id": str(did), "nombre": str(d.get("nombre") or did), "tipo": tipo, "origen": origen,
                "zona": zona, "capa_osi": capa, "capa_osi_origen": origen_capa, "vertical": vertical}
        item["_zona_decl"] = zona_decl
        out.append(item)

    for t in tech._tecnologias(registry):
        anadir(t, "registro", str(t.get("tipo") or "tecnologia"))
    for a in _lista(inventario, "activos"):
        anadir(a, "inventario", str(a.get("tipo") or "activo"))
    return out


def _vulns(tracker, hoy: date, avisos: list[str]) -> dict[str, dict]:
    """Por tecnologia_id: abiertas, fuera de SLA, KEV y peor severidad."""
    if tracker is None:
        return {}
    policy = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    sla = policy["sla_remediacion_dias"]
    filas = list(csv.DictReader(Path(tracker).open(encoding="utf-8"))) if isinstance(tracker, (str, Path)) else list(tracker)
    res: dict[str, dict] = {}
    for r in filas:
        if (r.get("estado") or "").strip() == "remediada":
            continue
        tid = (r.get("tecnologia_id") or "").strip()
        sev = (r.get("severidad") or "").strip()
        try:
            dias = (hoy - date.fromisoformat((r.get("detectado") or "").strip())).days
        except ValueError:
            avisos.append(f"{r.get('cve') or '?'}: fecha 'detectado' no válida, no se evalúa su SLA")
            dias = None
        limite = sla.get(sev)
        if sev not in sla:
            avisos.append(f"{r.get('cve') or '?'}: severidad '{sev}' sin SLA definido")
        v = res.setdefault(tid, {"abiertas": 0, "fuera_sla": 0, "kev_fuera_sla": 0, "peor_severidad": None, "cves_fuera_sla": []})
        v["abiertas"] += 1
        fuera = dias is not None and limite is not None and dias > limite
        if fuera:
            v["fuera_sla"] += 1
            v["cves_fuera_sla"].append(r.get("cve"))
            if str(r.get("kev")).strip().lower() == "true":
                v["kev_fuera_sla"] += 1
            if sev in SEVERIDADES and (v["peor_severidad"] is None or SEVERIDADES.index(sev) < SEVERIDADES.index(v["peor_severidad"])):
                v["peor_severidad"] = sev
    return res


def _reglas(registry: dict, hoy: date, dias: int) -> dict[str, dict]:
    """Estado de reglas por ID reutilizando tech.reglas; `sin_datos` cuando no hay bloque."""
    r = tech.reglas(registry, hoy, dias)
    res = {}
    for clave, estado in (("revisadas", "revisadas"), ("sin_revisar", "sin_revisar"), ("no_evaluables", "no_evaluable")):
        for f in r[clave]:
            d = {"estado": estado, "n_reglas": f.get("n_reglas"), "reglas_any_any": f["reglas_any_any"],
                 "reglas_sin_uso": f["reglas_sin_uso"], "dias_sin_revisar": f.get("dias_sin_revisar")}
            if estado == "no_evaluable":
                d["motivo"] = f["motivo"]
            if estado == "sin_revisar":
                d["caducada"] = f.get("caducada", False)
            res[f["id"]] = d
    return res


def semaforo(reglas: dict, vulns: dict) -> tuple[str, list[str]]:
    """Reglas del semáforo (documentadas en docs/mapa-3d.md).

    rojo : vulnerabilidad fuera de SLA que es crítica o está en KEV, o reglas any-any > 0.
    ambar: cualquier otra vulnerabilidad fuera de SLA, o reglas sin revisar / revisión caducada.
    gris : sin rojo ni ámbar pero reglas no evaluables o sin datos (no se puede afirmar que esté bien).
    verde: reglas revisadas, sin any-any y sin vulnerabilidades fuera de SLA.
    """
    rojo, ambar = [], []
    if vulns["kev_fuera_sla"]:
        rojo.append(f"{vulns['kev_fuera_sla']} vulnerabilidad(es) KEV fuera de SLA")
    if vulns["peor_severidad"] == "critica":
        rojo.append("vulnerabilidad crítica fuera de SLA")
    if reglas.get("reglas_any_any", 0) > 0:
        rojo.append(f"{reglas['reglas_any_any']} regla(s) any-any")
    if rojo:
        return "rojo", rojo
    if vulns["fuera_sla"]:
        ambar.append(f"{vulns['fuera_sla']} vulnerabilidad(es) fuera de SLA")
    if reglas["estado"] == "sin_revisar":
        ambar.append("reglas sin revisar o con revisión caducada")
    if ambar:
        return "ambar", ambar
    if reglas["estado"] == "no_evaluable":
        return "gris", ["reglas no evaluables: " + reglas.get("motivo", "")]
    if reglas["estado"] == "sin_datos":
        return "gris", ["sin datos de reglas"]
    return "verde", ["reglas revisadas y sin vulnerabilidades fuera de SLA"]


def _peor(valores: list[str]) -> str:
    for s in SEMAFOROS:
        if s in valores:
            return s
    return "gris"


def construir_mapa(registry, inventario=None, tracker=None, evaluacion=None,
                   hoy: date | None = None, dias_reglas: int = tech.UMBRAL_REGLAS_DIAS) -> dict:
    hoy = hoy or date.today()
    reg = _yaml(registry)
    inv = _yaml(inventario) if inventario is not None else {}
    avisos: list[str] = []
    disp = _dispositivos(reg, inv, avisos)
    vul = _vulns(tracker, hoy, avisos)
    reg_reglas = _reglas(reg, hoy, dias_reglas)
    ev_tec = {f["id"]: f for f in tech.evaluar_tecnologias(reg)}

    madurez_v: dict[str, int | None] = {}
    madurez_media = None
    if evaluacion is not None:
        from .verticals import evaluar
        ev = evaluar(_yaml(evaluacion), estricto=False)
        madurez_v = {r.id: r.madurez for r in ev.verticales if r.estado == "evaluada"}
        madurez_media = ev.madurez_media
        avisos += [f"evaluación: {w}" for w in ev.warnings + ev.errores]

    ids = {d["id"] for d in disp}
    avisos += [f"tracker: {tid or '(vacío)'} no es un dispositivo del registro ni del inventario"
               for tid in sorted(vul) if tid not in ids]

    zonas = {z: {"id": z, "nombre": n, "dispositivos": [], "semaforo": "gris"} for z, n in ZONAS.items()}
    sin_zona: list[dict] = []
    for d in disp:
        decl = d.pop("_zona_decl")
        r = reg_reglas.get(d["id"]) or {"estado": "sin_datos", "n_reglas": None, "reglas_any_any": 0,
                                         "reglas_sin_uso": 0, "dias_sin_revisar": None}
        v = vul.get(d["id"]) or {"abiertas": 0, "fuera_sla": 0, "kev_fuera_sla": 0, "peor_severidad": None, "cves_fuera_sla": []}
        sem, motivos = semaforo(r, v)
        e = ev_tec.get(d["id"])
        d.update({
            "reglas": r,
            "vulnerabilidades": v,
            "semaforo": sem,
            "semaforo_motivos": motivos,
            "evaluacion": {"cobertura_pct": e["cobertura_pct"], "configuracion": e["configuracion"], "madurez": e["madurez"]} if e else None,
            "madurez_vertical": madurez_v.get(d["vertical"]) if d["vertical"] else None,
        })
        if d["zona"]:
            zonas[d["zona"]]["dispositivos"].append(d)
        else:
            d["motivo_sin_zona"] = f"zona '{decl}' no reconocida" if decl not in (None, "") else "sin zona asignada"
            sin_zona.append(d)

    lista_zonas = []
    for z in zonas.values():
        ds = z["dispositivos"]
        z["semaforo"] = _peor([d["semaforo"] for d in ds]) if ds else "gris"
        z["n_dispositivos"] = len(ds)
        lista_zonas.append(z)

    todos = [d for z in lista_zonas for d in z["dispositivos"]] + sin_zona
    resumen = {
        "dispositivos": len(todos),
        "sin_zona": len(sin_zona),
        "por_semaforo": {s: sum(1 for d in todos if d["semaforo"] == s) for s in SEMAFOROS},
        "reglas_no_evaluables": sum(1 for d in todos if d["reglas"]["estado"] == "no_evaluable"),
        "vulnerabilidades_abiertas": sum(d["vulnerabilidades"]["abiertas"] for d in todos),
        "vulnerabilidades_fuera_sla": sum(d["vulnerabilidades"]["fuera_sla"] for d in todos),
        "madurez_verticales_media": madurez_media,
    }
    return {
        "schema": SCHEMA,
        "generado_para": hoy.isoformat(),
        "umbral_revision_reglas_dias": dias_reglas,
        "zonas": lista_zonas,
        "sin_zona": sin_zona,
        "resumen": resumen,
        "avisos": avisos,
    }


def validar_mapa(m) -> list[str]:
    """Valida un mapa contra el esquema descrito en docs/mapa-3d.md. Devuelve los errores."""
    err: list[str] = []
    if not isinstance(m, dict):
        return ["el mapa no es un objeto"]
    if m.get("schema") != SCHEMA:
        err.append(f"schema debe ser '{SCHEMA}'")
    for k in ("generado_para", "umbral_revision_reglas_dias", "zonas", "sin_zona", "resumen", "avisos"):
        if k not in m:
            err.append(f"falta '{k}'")
    if err:
        return err
    vistos: set[str] = set()

    def disp(d, donde):
        if not isinstance(d, dict):
            err.append(f"{donde}: no es un objeto")
            return
        for k in ("id", "nombre", "tipo", "origen", "zona", "capa_osi", "capa_osi_origen", "vertical", "reglas",
                  "vulnerabilidades", "semaforo", "semaforo_motivos", "evaluacion", "madurez_vertical"):
            if k not in d:
                err.append(f"{donde}: falta '{k}'")
        if d.get("id") in vistos:
            err.append(f"{donde}: id duplicado {d.get('id')}")
        vistos.add(d.get("id"))
        if d.get("semaforo") not in SEMAFOROS:
            err.append(f"{donde}: semáforo '{d.get('semaforo')}' no válido")
        c = d.get("capa_osi")
        if c is not None and not (isinstance(c, int) and 1 <= c <= 7):
            err.append(f"{donde}: capa_osi fuera de 1-7")
        r = d.get("reglas") or {}
        if r.get("estado") not in ESTADOS_REGLAS_MAPA:
            err.append(f"{donde}: estado de reglas '{r.get('estado')}' no válido")
        if r.get("estado") == "no_evaluable" and not str(r.get("motivo") or "").strip():
            err.append(f"{donde}: no_evaluable sin motivo")
        v = d.get("vulnerabilidades") or {}
        if not (isinstance(v.get("abiertas"), int) and isinstance(v.get("fuera_sla"), int) and 0 <= v["fuera_sla"] <= v["abiertas"]):
            err.append(f"{donde}: vulnerabilidades incoherentes")

    for z in m["zonas"] if isinstance(m["zonas"], list) else []:
        if z.get("id") not in ZONAS:
            err.append(f"zona '{z.get('id')}' no está en el catálogo")
        if z.get("semaforo") not in SEMAFOROS:
            err.append(f"zona {z.get('id')}: semáforo no válido")
        for d in z.get("dispositivos", []):
            disp(d, f"zona {z.get('id')}/{d.get('id') if isinstance(d, dict) else '?'}")
            if isinstance(d, dict) and d.get("zona") != z.get("id"):
                err.append(f"{d.get('id')}: su zona no coincide con la zona que lo contiene")
    for d in m["sin_zona"] if isinstance(m["sin_zona"], list) else []:
        disp(d, f"sin_zona/{d.get('id') if isinstance(d, dict) else '?'}")
        if isinstance(d, dict) and (d.get("zona") is not None or not d.get("motivo_sin_zona")):
            err.append(f"{d.get('id')}: en sin_zona debe llevar zona null y motivo_sin_zona")
    if isinstance(m.get("resumen"), dict) and m["resumen"].get("dispositivos") != len(vistos):
        err.append("resumen.dispositivos no coincide con los dispositivos del mapa")
    return err


def contiene_ruta_absoluta(obj) -> bool:
    """True si algún texto del JSON parece una ruta absoluta de sistema de ficheros."""
    if isinstance(obj, str):
        return obj.startswith(("/Users/", "/home/", "/tmp/", "/var/", "/private/")) or (len(obj) > 2 and obj[1:3] == ":\\")
    if isinstance(obj, dict):
        return any(contiene_ruta_absoluta(v) for v in obj.values())
    if isinstance(obj, list):
        return any(contiene_ruta_absoluta(v) for v in obj)
    return False
