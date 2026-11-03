"""RIA (Reglamento (UE) 2024/1689) tras el Ómnibus digital sobre IA (Reglamento (UE) 2026/1744) y seguridad de agentes.

No es asesoramiento jurídico: resume obligaciones por rol, nivel de riesgo y fecha para priorizar el trabajo.

Fuentes (consulta 2026-11-03):
    https://eur-lex.europa.eu/eli/reg/2024/1689/oj   (copia DOUE: https://www.boe.es/buscar/doc.php?id=DOUE-L-2024-81079)
    https://eur-lex.europa.eu/eli/reg/2026/1744/oj   (copia DOUE: https://www.boe.es/doue/2026/1744/L00001-00041.pdf)
    https://genai.owasp.org/llm-top-10/              (OWASP Top 10 for LLM Applications 2025)
    https://atlas.mitre.org/                         (MITRE ATLAS; IDs contrastados con atlas-data v2026.10)

API para integradores (T28):
    cargar_obligaciones(path=None) -> list[Obligacion]
    validar_catalogo(obligaciones=None) -> list[str]                    # errores; vacía si todo correcto
    cargar_inventario(ruta_o_dict) -> dict
    validar_inventario(inventario) -> list[str]                         # errores de esquema (nivel o rol inexistente)
    clasificar(sistema) -> Clasificacion                                # AIActError si nivel o rol no existen
    obligaciones(inventario, hoy=None, estricto=True, catalogo=None) -> ResultadoIA
    es_capitulo_iii(articulo) -> bool                                   # T34: arts. 6-49 (campo `articulo`)
    riesgos_agente(inventario) -> list[HallazgoAgente]
    render_markdown(resultado, hallazgos=None) -> str
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml

from .catalog import ROOT
from .gap import md_texto

AI_ACT_DIR = ROOT / "frameworks" / "ai-act"
OBLIGACIONES_FILE = AI_ACT_DIR / "obligaciones.yaml"
INVENTARIO_TEMPLATE = ROOT / "ai" / "inventario.template.yaml"

ROLES = ("proveedor", "responsable_despliegue", "importador", "distribuidor")
NIVELES = ("prohibido", "alto_riesgo_anexo_iii", "alto_riesgo_anexo_i", "transparencia",
           "uso_general", "uso_general_riesgo_sistemico", "minimo")
FUENTES_ID = ("RIA", "OMNIBUS")
VIGENTE, APLICABLE_DESDE = "vigente", "aplicable_desde"
CUMPLIDA, PENDIENTE, NO_COMPROBABLE = "cumplida", "pendiente", "no_comprobable"

AVISO_JURIDICO = ("Este resumen no es asesoramiento jurídico. Orienta sobre obligaciones del RIA según el rol, "
                  "el nivel de riesgo y la fecha declarados en el inventario; el texto que obliga es el publicado en el DOUE.")

FUENTES = (
    ("RIA, Reglamento (UE) 2024/1689", "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"),
    ("Ómnibus digital sobre IA, Reglamento (UE) 2026/1744", "https://eur-lex.europa.eu/eli/reg/2026/1744/oj"),
    ("OWASP Top 10 for LLM Applications 2025", "https://genai.owasp.org/llm-top-10/"),
    ("MITRE ATLAS", "https://atlas.mitre.org/"),
)


class AIActError(ValueError):
    """Esquema inválido: nivel de riesgo o rol inexistente."""


FECHA_AUTORIDADES_PUBLICAS = date(2030, 8, 2)   # art. 111.2 RIA, último inciso
CAPITULO_III = (6, 49)                          # arts. 6 a 49 del RIA


def es_capitulo_iii(articulo: str) -> bool:
    """True si TODOS los artículos citados en `articulo` están entre el 6 y el 49 (capítulo III del RIA).

    Se leen los números de artículo y se ignoran los de apartado: «art. 26.1» -> 26; «arts. 43, 47 y 48» -> 43, 47, 48;
    «art. 5.1 b bis)» -> 5. Una cita mixta (parte dentro, parte fuera) NO cuenta como capítulo III: no se recorta."""
    nums = [int(n) for n in re.findall(r"(?<![\d.])(\d+)(?!\d)", str(articulo))]
    return bool(nums) and all(CAPITULO_III[0] <= n <= CAPITULO_III[1] for n in nums)


@dataclass
class Obligacion:
    id: str
    articulo: str
    titulo: str
    descripcion: str
    roles: list[str]
    niveles: list[str]
    aplica_desde: date | dict[str, date]
    fuente: str
    supuesto: str = ""
    excepto_supuesto: str = ""
    transitorio: dict = field(default_factory=dict)     # {en_mercado_antes_de: date, aplica_desde: date}
    evidencia: str = ""
    verificar: bool = False
    nota: str = ""
    preexistente: bool = False      # T29 (art. 111.2): solo para sistemas en el mercado antes de la fecha de su nivel

    def fecha(self, nivel: str) -> date | None:
        if isinstance(self.aplica_desde, dict):
            return self.aplica_desde.get(nivel)
        return self.aplica_desde


@dataclass
class Clasificacion:
    nivel: str
    roles: list[str]


@dataclass
class ObligacionAplicable:
    id: str
    articulo: str
    titulo: str
    roles: list[str]              # roles del sistema a los que alcanza
    aplica_desde: date
    estado: str                   # "vigente" | "aplicable_desde"
    cumplimiento: str             # "cumplida" | "pendiente" | "no_comprobable"
    evidencia: str = ""
    verificar: bool = False
    nota: str = ""


@dataclass
class ObligacionTransitoria:
    """Obligación del capítulo III que NO se emite como pendiente por el art. 111.2 (T34)."""
    id: str
    articulo: str
    titulo: str
    roles: list[str]
    aplica_desde: date | None     # 2030-08-02 con autoridad_publica; None = solo con cambios significativos
    condicion: str


@dataclass
class ObligacionesSistema:
    id: str
    nombre: str
    nivel: str
    roles: list[str]
    obligaciones: list[ObligacionAplicable] = field(default_factory=list)
    regimen_transitorio: list[ObligacionTransitoria] = field(default_factory=list)   # T34, art. 111.2

    @property
    def pendientes(self) -> list[ObligacionAplicable]:
        """Obligaciones sin evidencia de cumplimiento (vigentes o futuras)."""
        return [o for o in self.obligaciones if o.cumplimiento == PENDIENTE]

    @property
    def incumplidas(self) -> list[ObligacionAplicable]:
        """Pendientes y ya vigentes en `hoy`."""
        return [o for o in self.pendientes if o.estado == VIGENTE]


@dataclass
class ResultadoIA:
    hoy: date
    organizacion: str
    sistemas: list[ObligacionesSistema]
    no_clasificados: list[dict] = field(default_factory=list)    # {id, nombre, error} (solo estricto=False)
    warnings: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


@dataclass
class HallazgoAgente:
    sistema: str
    agente: str
    id: str                       # AGT-01 .. AGT-06
    titulo: str
    severidad: str                # alta | media
    detalle: str
    owasp: list[str]
    atlas: list[str]              # técnicas AML.Txxxx
    mitigaciones: list[str]       # mitigaciones AML.Mxxxx


# --- Catálogo ---

def _fecha(v) -> date:
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v))


def cargar_obligaciones(path: Path | None = None) -> list[Obligacion]:
    data = yaml.safe_load(Path(path or OBLIGACIONES_FILE).read_text(encoding="utf-8"))
    out = []
    for raw in data["obligaciones"]:
        ad = raw.get("aplica_desde")
        ad = {k: _fecha(v) for k, v in ad.items()} if isinstance(ad, dict) else _fecha(ad)
        tr = raw.get("transitorio") or {}
        if tr:
            tr = {"en_mercado_antes_de": _fecha(tr["en_mercado_antes_de"]), "aplica_desde": _fecha(tr["aplica_desde"])}
        out.append(Obligacion(
            id=raw["id"], articulo=str(raw["articulo"]), titulo=raw["titulo"], descripcion=raw.get("descripcion", ""),
            roles=list(raw.get("roles") or []), niveles=list(raw.get("niveles") or []), aplica_desde=ad,
            fuente=raw.get("fuente", ""), supuesto=raw.get("supuesto") or "", excepto_supuesto=raw.get("excepto_supuesto") or "",
            transitorio=tr, evidencia=raw.get("evidencia") or "", verificar=bool(raw.get("verificar", False)),
            nota=raw.get("nota") or "", preexistente=bool(raw.get("preexistente", False)),
        ))
    return out


def _supuestos_catalogo(path: Path | None = None) -> set[str]:
    data = yaml.safe_load(Path(path or OBLIGACIONES_FILE).read_text(encoding="utf-8"))
    return set((data.get("supuestos") or {}).keys())


def validar_catalogo(obligaciones: list[Obligacion] | None = None) -> list[str]:
    """Errores del catálogo: IDs duplicados, roles o niveles inexistentes, fechas por nivel incompletas,
    fuente desconocida, supuestos no declarados y `verificar` sin nota."""
    obligaciones = obligaciones if obligaciones is not None else cargar_obligaciones()
    supuestos = _supuestos_catalogo()
    ids = [o.id for o in obligaciones]
    errores = []
    for o in obligaciones:
        if ids.count(o.id) > 1:
            errores.append(f"{o.id}: ID duplicado")
        if not o.roles or any(r not in ROLES for r in o.roles):
            errores.append(f"{o.id}: roles no válidos {o.roles}")
        if not o.niveles or any(n not in NIVELES for n in o.niveles):
            errores.append(f"{o.id}: niveles no válidos {o.niveles}")
        if isinstance(o.aplica_desde, dict) and set(o.aplica_desde) != set(o.niveles):
            errores.append(f"{o.id}: aplica_desde por nivel no cubre exactamente sus niveles")
        if o.fuente not in FUENTES_ID:
            errores.append(f"{o.id}: fuente desconocida {o.fuente!r}")
        for s in (o.supuesto, o.excepto_supuesto):
            if s and s not in supuestos:
                errores.append(f"{o.id}: supuesto no declarado {s!r}")
        if o.verificar and not o.nota.strip():
            errores.append(f"{o.id}: verificar sin nota")
    return errores


# --- Inventario ---

def cargar_inventario(inventario) -> dict:
    """Acepta una ruta al YAML o un dict ya cargado; devuelve {} si no es un mapa."""
    if isinstance(inventario, (str, Path)):
        inventario = yaml.safe_load(Path(inventario).read_text(encoding="utf-8"))
    return inventario if isinstance(inventario, dict) else {}


def _sistemas(inv: dict) -> list:
    s = inv.get("sistemas")
    return s if isinstance(s, list) else []


def _roles(sistema: dict) -> list[str]:
    r = sistema.get("rol")
    if r is None:
        return []
    return [str(x) for x in r] if isinstance(r, list) else [str(r)]


def clasificar(sistema: dict) -> Clasificacion:
    """Valida nivel de riesgo y rol(es) del sistema. Lanza AIActError si alguno no existe."""
    if not isinstance(sistema, dict):
        raise AIActError("el sistema no es un mapa")
    sid = sistema.get("id", "?")
    nivel = sistema.get("nivel_riesgo")
    if nivel not in NIVELES:
        raise AIActError(f"{sid}: nivel de riesgo inexistente {nivel!r} (válidos: {', '.join(NIVELES)})")
    roles = _roles(sistema)
    if not roles:
        raise AIActError(f"{sid}: sin rol (válidos: {', '.join(ROLES)})")
    malos = [r for r in roles if r not in ROLES]
    if malos:
        raise AIActError(f"{sid}: rol inexistente {malos} (válidos: {', '.join(ROLES)})")
    if nivel.startswith("uso_general") and "proveedor" not in roles:
        raise AIActError(f"{sid}: un modelo de uso general solo genera obligaciones del capítulo V para su proveedor")
    return Clasificacion(nivel, roles)


def validar_inventario(inventario) -> list[str]:
    """Errores de esquema del inventario (para `smc validate`)."""
    inv = cargar_inventario(inventario)
    errores = []
    if not inv:
        return ["el inventario no es un mapa"]
    if not isinstance(inv.get("sistemas"), list):
        return ["'sistemas' no es una lista"]
    ids = []
    for s in _sistemas(inv):
        try:
            clasificar(s)
        except AIActError as e:
            errores.append(str(e))
        if isinstance(s, dict):
            ids.append(s.get("id"))
        if isinstance(s, dict):
            sid = s.get("id", "?")
            for campo in ("cambios_significativos", "autoridad_publica"):
                if s.get(campo) is not None and not isinstance(s.get(campo), bool):
                    errores.append(f"{sid}: {campo} debe ser true o false (no {s.get(campo)!r})")
            if s.get("en_mercado_desde") not in (None, "") and _fecha_mercado(s.get("en_mercado_desde")) is None:
                errores.append(f"{sid}: en_mercado_desde no es una fecha AAAA-MM-DD ({s.get('en_mercado_desde')!r})")
    errores += [f"{i}: ID de sistema duplicado" for i in sorted({i for i in ids if ids.count(i) > 1}, key=str)]
    return errores


def _fecha_mercado(v) -> date | None:
    """Fecha de `en_mercado_desde`: date (un datetime se reduce a su fecha) o cadena AAAA-MM-DD; si no, None."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v.strip())
        except ValueError:
            return None
    return None


def _bandera(s: dict, campo: str, sid: str, warnings: list[str]) -> bool | None:
    """true/false del inventario; ausente = None («no consta»); otro tipo = None con aviso (lo rechaza la validación)."""
    v = s.get(campo)
    if v is None or isinstance(v, bool):
        return v
    warnings.append(f"{sid}: {campo} debe ser true o false (se ignora; cuenta como «no consta»)")
    return None


def _evidencia(valor) -> bool:
    """true, o un mapa con `existe`/`activo` true. Ausente o falso = sin evidencia."""
    if isinstance(valor, dict):
        return valor.get("existe", valor.get("activo")) is True
    return valor is True


def _supuestos(sistema: dict, warnings: list[str], conocidos: set[str]) -> set[str]:
    sup = sistema.get("supuestos") or []
    if not isinstance(sup, list):
        warnings.append(f"{sistema.get('id')}: 'supuestos' no es una lista (se ignora)")
        return set()
    for x in sup:
        if x not in conocidos:
            warnings.append(f"{sistema.get('id')}: supuesto desconocido {x!r} (se ignora)")
    return {x for x in sup if x in conocidos}


def obligaciones(inventario, hoy: date | None = None, estricto: bool = True,
                 catalogo: list[Obligacion] | None = None) -> ResultadoIA:
    """Obligaciones aplicables por sistema, con estado por fecha y cumplimiento según la evidencia del inventario.

    - estado: «vigente» si `hoy` >= fecha de aplicación; si no, «aplicable_desde» (la fecha va en `aplica_desde`).
    - Periodo transitorio: si el sistema declara `en_mercado_desde` anterior al corte, se usa la fecha transitoria;
      sin `en_mercado_desde` se usa la general (la más temprana) con aviso.
    - Obligaciones con `supuesto` solo aplican si el sistema lo declara; en nivel «transparencia» sin supuestos
      se aplican todas las del art. 50 con aviso.
    - cumplimiento: «cumplida» si el campo de `evidencia` es verdadero; «pendiente» si es falso o falta;
      «no_comprobable» si la obligación no tiene campo de evidencia.
    - Nivel o rol inexistente: estricto=True lanza AIActError; estricto=False lo deja en `errores` y en `no_clasificados`.
    """
    hoy = hoy or date.today()
    catalogo = catalogo if catalogo is not None else cargar_obligaciones()
    conocidos = _supuestos_catalogo()
    inv = cargar_inventario(inventario)
    warnings: list[str] = []
    errores: list[str] = []
    if not inv:
        warnings.append("el inventario no es un mapa: sin sistemas")
    elif not isinstance(inv.get("sistemas"), list):
        warnings.append("'sistemas' no es una lista: sin sistemas")
    res: list[ObligacionesSistema] = []
    no_clasificados: list[dict] = []
    for s in _sistemas(inv):
        try:
            cl = clasificar(s)
        except AIActError as e:
            if estricto:
                raise
            errores.append(str(e))
            if isinstance(s, dict):
                no_clasificados.append({"id": s.get("id"), "nombre": s.get("nombre"), "error": str(e)})
            continue
        sid = str(s.get("id") or "?")
        sup = _supuestos(s, warnings, conocidos)
        transparencia_sin_supuestos = cl.nivel == "transparencia" and not sup
        if transparencia_sin_supuestos:
            warnings.append(f"{sid}: nivel transparencia sin supuestos: se aplican todas las obligaciones del art. 50")
        en_mercado = None
        if s.get("en_mercado_desde") not in (None, ""):
            en_mercado = _fecha_mercado(s.get("en_mercado_desde"))
            if en_mercado is None:
                warnings.append(f"{sid}: en_mercado_desde no es una fecha válida (se ignora)")
        cambios = _bandera(s, "cambios_significativos", sid, warnings)
        publica = bool(_bandera(s, "autoridad_publica", sid, warnings))
        aviso_cambios = False
        sistema = ObligacionesSistema(sid, str(s.get("nombre") or ""), cl.nivel, cl.roles)
        for o in catalogo:
            if cl.nivel not in o.niveles:
                continue
            roles = [r for r in cl.roles if r in o.roles]
            if not roles:
                continue
            if o.excepto_supuesto and o.excepto_supuesto in sup:
                continue
            if o.supuesto and o.supuesto not in sup:
                es_art50 = o.articulo.startswith("art. 50")
                if not (transparencia_sin_supuestos and es_art50):
                    continue
            fecha = o.fecha(cl.nivel)
            if fecha is None:
                warnings.append(f"{o.id}: sin fecha para el nivel {cl.nivel} (se omite)")
                continue
            nota = o.nota
            # Art. 111.2 RIA: alto riesgo en el mercado antes de la fecha del capítulo III y SIN cambios significativos
            # de diseño (declarado: cambios_significativos false): las obligaciones del capítulo III (arts. 6-49) no se
            # emiten como pendientes. Dato ausente = «no consta»: no se recorta y se avisa.
            if (cl.nivel.startswith("alto_riesgo") and not o.preexistente and es_capitulo_iii(o.articulo)
                    and en_mercado is not None and en_mercado < fecha and cambios is None and not aviso_cambios):
                aviso_cambios = True
                warnings.append(f"{sid}: en el mercado desde {en_mercado}, antes del capítulo III, y no consta si hay cambios "
                                f"significativos de diseño: se emiten las obligaciones del capítulo III como pendientes; "
                                f"si no los hay, aplicaría el régimen transitorio del art. 111.2 (declare "
                                f"cambios_significativos: false)")
            if (cl.nivel.startswith("alto_riesgo") and not o.preexistente and es_capitulo_iii(o.articulo)
                    and en_mercado is not None and en_mercado < fecha and cambios is False):
                if not publica:
                    sistema.regimen_transitorio.append(ObligacionTransitoria(
                        o.id, o.articulo, o.titulo, roles, None,
                        "solo con cambios significativos de diseño (art. 111.2)"))
                    continue
                if hoy < FECHA_AUTORIDADES_PUBLICAS:
                    sistema.regimen_transitorio.append(ObligacionTransitoria(
                        o.id, o.articulo, o.titulo, roles, FECHA_AUTORIDADES_PUBLICAS,
                        "autoridad pública sin cambios significativos: a más tardar el 2030-08-02 (art. 111.2)"))
                    continue
                fecha = FECHA_AUTORIDADES_PUBLICAS
                nota += " Autoridad pública en régimen del art. 111.2: aplica desde 2030-08-02."
            if o.preexistente:
                # Art. 111.2 RIA (Ómnibus, punto 39 a): solo para alto riesgo ya en el mercado antes de la fecha del capítulo III.
                if en_mercado is None or en_mercado >= fecha:
                    continue
                if cambios is None:
                    nota += (" No consta si hay cambios significativos de diseño (declare cambios_significativos): "
                             "con ellos, el capítulo III le aplica desde la fecha de su nivel.")
                elif cambios:
                    nota += " Declara cambios significativos de diseño: el capítulo III le aplica desde la fecha de su nivel."
                elif publica:
                    fecha = FECHA_AUTORIDADES_PUBLICAS
                    nota += " Sin cambios significativos y destinado a autoridades públicas: medidas a más tardar el 2030-08-02."
                else:
                    nota += " Sin cambios significativos de diseño no está obligado por el capítulo III; si los hay desde esa fecha, sí."
            if o.transitorio:
                corte, f_tr = o.transitorio["en_mercado_antes_de"], o.transitorio["aplica_desde"]
                if en_mercado is None:
                    warnings.append(f"{sid}: sin en_mercado_desde; {o.id} usa la fecha general {fecha} "
                                    f"(si estaba en el mercado antes de {corte}, aplica desde {f_tr})")
                elif en_mercado < corte:
                    fecha = f_tr
            if o.evidencia:
                cumpl = CUMPLIDA if _evidencia(s.get(o.evidencia)) else PENDIENTE
            else:
                cumpl = NO_COMPROBABLE
            sistema.obligaciones.append(ObligacionAplicable(
                id=o.id, articulo=o.articulo, titulo=o.titulo, roles=roles, aplica_desde=fecha,
                estado=VIGENTE if hoy >= fecha else APLICABLE_DESDE, cumplimiento=cumpl,
                evidencia=o.evidencia, verificar=o.verificar, nota=nota,
            ))
        sistema.obligaciones.sort(key=lambda x: (x.aplica_desde, x.id))
        sistema.regimen_transitorio.sort(key=lambda x: x.id)
        res.append(sistema)
    return ResultadoIA(hoy=hoy, organizacion=str(inv.get("organizacion") or ""), sistemas=res,
                       no_clasificados=no_clasificados, warnings=warnings, errores=errores)


# --- Seguridad de agentes (OWASP Top 10 for LLM Applications 2025 y MITRE ATLAS) ---

PERMISOS_SENSIBLES = frozenset({"escritura", "ejecucion", "borrado", "pagos", "administracion", "envio"})
PERMISOS_SALIDA = frozenset({"red", "envio"})

# id -> (titulo, severidad, OWASP, técnicas ATLAS, mitigaciones ATLAS)
COMPROBACIONES = {
    "AGT-01": ("Herramienta sin límite de invocaciones", "media",
               ["LLM10:2025", "LLM06:2025"], ["AML.T0034", "AML.T0034.002", "AML.T0029"], ["AML.M0036", "AML.M0004"]),
    "AGT-02": ("Permisos excesivos en herramientas", "alta",
               ["LLM06:2025"], ["AML.T0053", "AML.T0101"], ["AML.M0028", "AML.M0026", "AML.M0037"]),
    "AGT-03": ("Sin supervisión humana", "alta",
               ["LLM06:2025"], ["AML.T0053"], ["AML.M0029"]),
    "AGT-04": ("Sin registro de la actividad del agente", "media",
               ["LLM06:2025", "LLM10:2025"], [], ["AML.M0024"]),
    "AGT-05": ("Prompt injection sin mitigación", "alta",
               ["LLM01:2025"], ["AML.T0051", "AML.T0051.001"], ["AML.M0020", "AML.M0030", "AML.M0033"]),
    "AGT-06": ("Exfiltración posible: datos personales, entrada no confiable y salida a red", "alta",
               ["LLM02:2025", "LLM01:2025", "LLM06:2025"], ["AML.T0086"], ["AML.M0030", "AML.M0028"]),
}


def _lista(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _limite(v) -> int | None:
    if isinstance(v, bool):
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _hallazgo(sistema, agente, cid, detalle) -> HallazgoAgente:
    titulo, sev, owasp, atlas, mit = COMPROBACIONES[cid]
    return HallazgoAgente(sistema, agente, cid, titulo, sev, detalle, list(owasp), list(atlas), list(mit))


def riesgos_agente(inventario) -> list[HallazgoAgente]:
    """Comprueba cada agente del inventario. Datos ausentes cuentan como «no consta» (hallazgo), nunca como cumplidos.

    AGT-01 herramienta con `limite_llamadas` ausente, 0 o no numérico.
    AGT-02 herramienta con permisos sensibles (escritura, ejecucion, borrado, pagos, administracion, envio)
           sin `requiere_aprobacion: true`, o agente con `permisos_minimos` distinto de true.
    AGT-03 `supervision_humana` del agente distinta de true.
    AGT-04 `registro` del agente distinto de true.
    AGT-05 `entrada_no_confiable` distinto de false y `mitigacion_prompt_injection` vacía.
    AGT-06 sistema con datos personales + entrada no confiable + herramienta con salida (red o envio) sin aprobación.
    """
    inv = cargar_inventario(inventario)
    out: list[HallazgoAgente] = []
    for s in _sistemas(inv):
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id") or "?")
        for ag in _lista(s.get("agentes")):
            if not isinstance(ag, dict):
                out.append(_hallazgo(sid, "?", "AGT-03", "entrada de agente mal formada: no consta supervisión"))
                continue
            aid = str(ag.get("id") or ag.get("nombre") or "?")
            herramientas = [h for h in _lista(ag.get("herramientas")) if isinstance(h, dict)]
            sin_limite = [str(h.get("nombre") or "?") for h in herramientas if _limite(h.get("limite_llamadas")) is None]
            if sin_limite:
                out.append(_hallazgo(sid, aid, "AGT-01", "sin límite: " + ", ".join(sin_limite)))
            sensibles = [
                f"{h.get('nombre') or '?'} ({', '.join(sorted(PERMISOS_SENSIBLES & set(map(str, _lista(h.get('permisos'))))))})"
                for h in herramientas
                if PERMISOS_SENSIBLES & set(map(str, _lista(h.get("permisos")))) and h.get("requiere_aprobacion") is not True
            ]
            if sensibles or ag.get("permisos_minimos") is not True:
                partes = []
                if sensibles:
                    partes.append("sin aprobación humana: " + ", ".join(sensibles))
                if ag.get("permisos_minimos") is not True:
                    partes.append("no consta mínimo privilegio (permisos_minimos)")
                out.append(_hallazgo(sid, aid, "AGT-02", "; ".join(partes)))
            if not _evidencia(ag.get("supervision_humana")):
                out.append(_hallazgo(sid, aid, "AGT-03", "el agente actúa sin supervisión humana declarada"))
            if not _evidencia(ag.get("registro")):
                out.append(_hallazgo(sid, aid, "AGT-04", "no consta registro de prompts, llamadas a herramientas y resultados"))
            no_confiable = ag.get("entrada_no_confiable") is not False
            mitig = [m for m in _lista(ag.get("mitigacion_prompt_injection")) if str(m).strip()]
            if no_confiable and not mitig:
                out.append(_hallazgo(sid, aid, "AGT-05", "procesa entrada no confiable (o no consta) sin mitigación declarada"))
            salida = [str(h.get("nombre") or "?") for h in herramientas
                      if PERMISOS_SALIDA & set(map(str, _lista(h.get("permisos")))) and h.get("requiere_aprobacion") is not True]
            if s.get("datos_personales") is True and no_confiable and salida:
                out.append(_hallazgo(sid, aid, "AGT-06", "salida sin aprobación: " + ", ".join(salida)))
    return out


# --- Render ---

def _fmt_estado(o: ObligacionAplicable) -> str:
    return "vigente" if o.estado == VIGENTE else f"aplicable desde {o.aplica_desde}"


def render_markdown(resultado: ResultadoIA, hallazgos: list[HallazgoAgente] | None = None) -> str:
    """Informe Markdown. Todo texto del inventario pasa por `md_texto` (escapa `|`, `<`, `>`)."""
    r = resultado
    out = [f"# RIA (Reglamento (UE) 2024/1689) y seguridad de agentes ({r.hoy})", ""]
    if r.organizacion:
        out += [f"Organización: {md_texto(r.organizacion)}", ""]
    out += [f"> **Aviso.** {AVISO_JURIDICO}", "",
            "Fechas vigentes tras el Ómnibus digital sobre IA (Reglamento (UE) 2026/1744). "
            "Las obligaciones marcadas «verificar» tienen fecha o alcance pendientes de contrastar.", "",
            "Fuentes:", ""]
    out += [f"- {t}: {u}" for t, u in FUENTES]
    out += ["", "## Resumen", "", "| Sistema | Nivel | Rol | Obligaciones | Pendientes | Pendientes ya vigentes |", "|---|---|---|---|---|---|"]
    for s in r.sistemas:
        out.append(f"| {md_texto(s.id)} {md_texto(s.nombre)} | {s.nivel} | {', '.join(s.roles)} | "
                   f"{len(s.obligaciones)} | {len(s.pendientes)} | {len(s.incumplidas)} |")
    if not r.sistemas:
        out.append("| — | — | — | 0 | 0 | 0 |")
    for s in r.sistemas:
        out += ["", f"## {md_texto(s.id)} {md_texto(s.nombre)}", "",
                "| Obligación | Artículo | Rol | Estado | Cumplimiento | Nota |", "|---|---|---|---|---|---|"]
        for o in s.obligaciones:
            nota = ("**verificar** " if o.verificar else "") + md_texto(o.nota)
            cumpl = f"**{o.cumplimiento}**" if o.cumplimiento == PENDIENTE else o.cumplimiento
            out.append(f"| {o.id} {md_texto(o.titulo)} | {md_texto(o.articulo)} | {', '.join(o.roles)} | "
                       f"{_fmt_estado(o)} | {cumpl} | {nota.strip() or '—'} |")
        if not s.obligaciones:
            out.append("| — | — | — | — | — | Sin obligaciones específicas |")
        if s.regimen_transitorio:
            out += ["", "Régimen transitorio (art. 111.2 RIA): obligaciones del capítulo III que no se emiten como pendientes.", "",
                    "| Obligación | Artículo | Rol | Pasaría a aplicar | Condición |", "|---|---|---|---|---|"]
            out += [f"| {t.id} {md_texto(t.titulo)} | {md_texto(t.articulo)} | {', '.join(t.roles)} | "
                    f"{t.aplica_desde or 'solo con cambios significativos'} | {md_texto(t.condicion)} |" for t in s.regimen_transitorio]
    if r.no_clasificados:
        out += ["", "## Sistemas no clasificados", "", "| Sistema | Error |", "|---|---|"]
        out += [f"| {md_texto(n.get('id'))} {md_texto(n.get('nombre'))} | {md_texto(n.get('error'))} |" for n in r.no_clasificados]
    if hallazgos is not None:
        out += ["", "## Seguridad de agentes (OWASP Top 10 LLM 2025, MITRE ATLAS)", "",
                "| Sistema | Agente | Comprobación | Severidad | Detalle | OWASP | ATLAS | Mitigaciones ATLAS |",
                "|---|---|---|---|---|---|---|---|"]
        for h in hallazgos:
            out.append(f"| {md_texto(h.sistema)} | {md_texto(h.agente)} | {h.id} {h.titulo} | {h.severidad} | "
                       f"{md_texto(h.detalle)} | {', '.join(h.owasp)} | {', '.join(h.atlas) or '—'} | {', '.join(h.mitigaciones)} |")
        if not hallazgos:
            out.append("| — | — | Sin hallazgos | — | — | — | — | — |")
    avisos = r.warnings + r.errores
    if avisos:
        out += ["", "## Avisos", ""] + [f"- {md_texto(a)}" for a in avisos]
    return "\n".join(out) + "\n"
