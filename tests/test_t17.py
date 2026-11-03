"""T17: endurecimiento v0.5.1 (hallazgos 1-10 y 12 de revisor-ola, olas 5-6). Un test por hallazgo, con contraprueba."""
import copy
import csv
from datetime import date
from pathlib import Path

import pytest
import yaml

from smc import gap, mitre, tech, verticals
from smc.cli import main
from smc.mapa import construir_mapa, validar_mapa
from smc.report_html import render_body
from smc.soc import mitre_coverage

ROOT = Path(__file__).resolve().parent.parent
HOY = date(2026, 11, 3)


def _reg(**reglas):
    base = {"estado": "revisadas", "ultima_revision": "2026-10-20", "n_reglas": 10, "reglas_any_any": 0, "reglas_sin_uso": 0}
    base.update(reglas)
    return {"technologies": [{"id": "T1", "nombre": "FW", "zona": "perimetro", "vertical": "VRT-FW", "reglas": base}]}


def _fila(sev, detectado, kev="false", estado="abierta"):
    return [{"cve": "CVE-0000-0009", "tecnologia_id": "T1", "severidad": sev, "kev": kev, "estado": estado, "detectado": detectado}]


def _dev(m):
    return next(d for z in m["zonas"] for d in z["dispositivos"] if d["id"] == "T1")


# 1 (a): KEV o crítica abierta pone al menos ámbar aunque esté dentro de SLA
def test_h1_kev_abierta_dentro_de_sla_no_es_verde():
    d = _dev(construir_mapa(_reg(), None, _fila("alta", "2026-11-01", kev="true"), hoy=HOY))
    assert d["semaforo"] == "ambar" and d["vulnerabilidades"]["fuera_sla"] == 0
    assert any("KEV o crítica" in x for x in d["semaforo_motivos"])
    d = _dev(construir_mapa(_reg(), None, _fila("critica", "2026-11-01"), hoy=HOY))
    assert d["semaforo"] == "ambar"
    # contraprueba: una alta sin KEV dentro de SLA sigue en verde
    assert _dev(construir_mapa(_reg(), None, _fila("alta", "2026-11-01"), hoy=HOY))["semaforo"] == "verde"


def test_h1_kev_cuenta_como_critica_a_efectos_de_sla():
    # alta con KEV detectada hace 10 días: SLA crítica (7) vencido -> rojo; sin KEV (SLA 30) no vence
    d = _dev(construir_mapa(_reg(), None, _fila("alta", "2026-10-24", kev="true"), hoy=HOY))
    assert d["semaforo"] == "rojo" and d["vulnerabilidades"]["kev_fuera_sla"] == 1
    assert _dev(construir_mapa(_reg(), None, _fila("alta", "2026-10-24"), hoy=HOY))["semaforo"] == "verde"
    # también en el listado `smc vulns`
    csv_ = ROOT / "vulnerabilities" / "tracker.template.csv"
    assert "Fuera de SLA" in tech.vulns(csv_, HOY)


# 2 (b): severidad normalizada; la desconocida cuenta como crítica con aviso
def test_h2_severidad_con_tilde_y_mayusculas():
    m = construir_mapa(_reg(), None, _fila("Crítica ", "2026-10-20"), hoy=HOY)
    d = _dev(m)
    assert d["semaforo"] == "rojo" and d["vulnerabilidades"]["peor_severidad"] == "critica"
    assert not any("sin SLA" in a for a in m["avisos"])


def test_h2_severidad_desconocida_es_critica_con_aviso():
    m = construir_mapa(_reg(), None, _fila("Grave", "2026-10-20"), hoy=HOY)
    assert _dev(m)["semaforo"] == "rojo"
    assert any("Grave" in a and "crítica" in a for a in m["avisos"])
    # contraprueba: severidad válida (con tilde) no genera aviso
    assert not construir_mapa(_reg(), None, _fila("crítica", "2026-11-02"), hoy=HOY)["avisos"]


def test_normalizar_severidad():
    assert tech.normalizar_severidad(" CRÍTICA ") == "critica" and tech.normalizar_severidad(None) == ""


# 3 (c): any_any con independencia del estado
def test_h3_any_any_con_revision_reciente():
    r = tech.reglas(_reg(reglas_any_any=3), HOY)
    assert [f["id"] for f in r["revisadas"]] == ["T1"]            # sigue revisada...
    assert r["any_any"] == [{"id": "T1", "nombre": "FW", "reglas_any_any": 3, "estado": "revisadas"}]   # ...pero se lista
    md = tech.render_reglas(r, HOY)
    assert "ATENCIÓN" in md and "**3**" in md.split("## Sin revisar")[0]
    # no evaluable con any-any también se lista
    ne = tech.reglas(_reg(estado="no_evaluable", motivo="MSSP", reglas_any_any=2), HOY)
    assert ne["any_any"][0]["estado"] == "no_evaluable"
    # contraprueba: sin any-any no hay lista ni sección
    sin = tech.reglas(_reg(), HOY)
    assert sin["any_any"] == [] and "ATENCIÓN" not in tech.render_reglas(sin, HOY)


# 4 (d): VRT-NET no puntúa si hay subverticales evaluadas
def _analisis():
    ass = yaml.safe_load((ROOT / "assessments" / "examples" / "ejemplo-energia.yaml").read_text(encoding="utf-8"))
    return gap.analyse(ass, HOY), ass


def test_h4_vrt_net_no_puntua_en_markdown_y_html():
    an, _ = _analisis()
    net = next(r for r in an.verticales.verticales if r.id == "VRT-NET")
    assert net.puntua is False and net.detallada_en == ["VRT-FW", "VRT-SASE", "VRT-ZTNA", "VRT-OSI"]
    texto = "no puntúa (detallada en FW, SASE, ZTNA y OSI)"
    md = gap.render_verticales_md(an.verticales)
    fila = next(l for l in md.splitlines() if l.startswith("| VRT-NET"))
    assert texto in fila and "evaluada" not in fila and "| 5 |" not in fila
    html = render_body(an)
    assert texto in html


def test_h4_contraprueba_sin_subverticales_vrt_net_puntua():
    r = verticals.evaluar({"verticales": {"VRT-NET": {"madurez": 5}}})
    net = next(x for x in r.verticales if x.id == "VRT-NET")
    assert net.puntua is True
    fila = next(l for l in gap.render_verticales_md(r).splitlines() if l.startswith("| VRT-NET"))
    assert "evaluada" in fila and "| 5 |" in fila


# 5 (e): baremo 0-5 por vertical
def test_h5_cada_vertical_tiene_6_niveles_concretos():
    vs = verticals.cargar_verticales()
    assert len(vs) == 19
    for v in vs:
        assert sorted(v.niveles) == [0, 1, 2, 3, 4, 5], v.id
        assert all(len(d) > 25 for d in v.niveles.values()), v.id
        assert len(set(v.niveles.values())) == 6, v.id          # ningún descriptor repetido
    assert verticals.validar_catalogo(vs) == []


def test_h5_contraprueba_baremo_incompleto_o_vacio_falla():
    vs = verticals.cargar_verticales()
    del vs[0].niveles[3]
    assert any("6 niveles" in e and vs[0].id in e for e in verticals.validar_catalogo(vs))
    vs = verticals.cargar_verticales()
    vs[1].niveles[2] = "  "
    assert any("sin descriptor" in e for e in verticals.validar_catalogo(vs))
    vs = verticals.cargar_verticales()
    vs[2].niveles = {}
    assert any(vs[2].id in e for e in verticals.validar_catalogo(vs))


# 6 (f): mapeos ENS
def test_h6_mapeos_ens():
    v = {x.id: x for x in verticals.cargar_verticales()}
    assert "ENS-op.exp.6" in v["VRT-EDR"].controles and "ENS-mp.eq.3" not in v["VRT-EDR"].controles
    assert "ENS-op.exp.4" in v["VRT-ENDUSER"].controles and "ENS-mp.sw.2" not in v["VRT-ENDUSER"].controles
    assert verticals.validar_catalogo() == []        # los IDs existen en el catálogo ENS
    # contraprueba: un ID ENS inexistente sí lo detecta el validador
    v["VRT-EDR"].controles.append("ENS-op.exp.99")
    assert any("ENS-op.exp.99" in e for e in verticals.validar_catalogo(list(v.values())))


# 7 (g): firewalls de la plantilla en VRT-FW
def test_h7_firewalls_de_la_plantilla_son_vrt_fw():
    techs = {t["id"]: t for t in yaml.safe_load((ROOT / "technologies" / "registry.template.yaml").read_text(encoding="utf-8"))["technologies"]}
    assert techs["TEC-0002"]["vertical"] == "VRT-FW" and techs["TEC-0003"]["vertical"] == "VRT-FW"
    assert not [t for t in techs.values() if t["vertical"] == "VRT-NET"]       # el paraguas no es de dispositivos
    # contraprueba: la capa declarada (3) manda sobre la de la vertical (4)
    m = construir_mapa(ROOT / "technologies" / "registry.template.yaml", hoy=HOY)
    d = next(d for z in m["zonas"] for d in z["dispositivos"] if d["id"] == "TEC-0002")
    assert d["capa_osi"] == 3 and d["capa_osi_origen"] == "declarada" and d["vertical"] == "VRT-FW"


# 8 (h): madurez por táctica = mínimo de los activos; no activos aparte; visible en el CLI
def _uc(tmp_path, casos):
    (tmp_path / "vulnerabilities/playbooks/caso-uso").mkdir(parents=True)
    f = tmp_path / "catalog.yaml"
    f.write_text(yaml.safe_dump({"use_cases": casos}), encoding="utf-8")
    return f


def _c(i, det, estado="activo", tactica="execution"):
    return {"id": i, "nombre": i, "tactica": tactica, "mitre": [f"T{1000 + len(i)}"], "deteccion": det,
            "playbook": "", "estado": estado, "ultima_prueba": ""}


def test_h8_tactica_es_el_minimo_de_los_activos(tmp_path):
    f = _uc(tmp_path, [_c("A", "sin"), _c("BB", "regla")])        # 1 y 2
    assert mitre.madurez(f, HOY, tmp_path)["tacticas"] == {"execution": 1}      # el máximo daría 2
    # contraprueba: con un solo caso, mínimo = máximo
    f = _uc(tmp_path / "x", [_c("BB", "regla")])
    assert mitre.madurez(f, HOY, tmp_path / "x")["tacticas"] == {"execution": 2}


def test_h8_no_activos_aparte_y_no_cuentan(tmp_path):
    f = _uc(tmp_path, [_c("BB", "regla"), _c("C", "sin", estado="en_desarrollo"), _c("D", "sin", "propuesto", "c2")])
    m = mitre.madurez(f, HOY, tmp_path)
    assert m["tacticas"] == {"execution": 2}                       # el en_desarrollo (nivel 1) no la baja
    assert set(m["no_activos"]) == {"C", "D"} and m["no_activos"]["C"]["estado"] == "en_desarrollo"
    assert "c2" not in m["tacticas"]                                # táctica solo con no activos: no aparece
    assert m["casos"]["C"] == 1


def test_h8_cli_expone_madurez_por_tactica(tmp_path, capsys):
    f = _uc(tmp_path, [_c("A", "sin"), _c("BB", "regla"), _c("C", "sin", estado="propuesto", tactica="c2")])
    txt = mitre_coverage(f, HOY)
    assert "| execution | 1 |" in txt and "Casos no activos" in txt and "C (propuesto" in txt
    assert main(["mitre", "--hoy", "2026-11-03"]) == 0
    assert "mínimo de casos activos" in capsys.readouterr().out


# 9 (i): coste_anual no numérico avisa
def test_h9_coste_no_numerico_avisa():
    def reg(coste):
        return {"technologies": [{"id": "T1", "nombre": "x", "suscripcion": {
            "proveedor": "P", "coste_anual": coste, "unidades_contratadas": 1, "unidades_en_uso": 1}}]}
    for malo in ("mucho", "18.000 EUR", True, ""):
        r = tech.suscripciones(reg(malo), HOY)
        assert any("coste_anual" in a and "no es numérico" in a for a in r["avisos"]), malo
        assert r["coste_por_proveedor"][("P", "EUR")] == 0
    # contraprueba: números (y cadenas numéricas) no avisan
    for ok in (18000, 18000.5, "18000", 0):
        assert not any("coste_anual" in a for a in tech.suscripciones(reg(ok), HOY)["avisos"])


# 10 (j): escape en el Markdown de verticales
def test_h10_markdown_escapa_html_y_pipes():
    ass = {"verticales": {"VRT-EDR": {"madurez": 3, "producto": "X<script>alert(1)</script>|y"},
                          "VRT-HUNT": {"madurez": "no_evaluable", "motivo": "<img src=x onerror=1> a|b\nlinea"}}}
    md = gap.render_verticales_md(verticals.evaluar(ass))
    assert "<script>" not in md and "<img" not in md and "</script>" not in md
    assert "&lt;script&gt;" in md and "a\\|b" in md and "y" in md
    fila = next(l for l in md.splitlines() if l.startswith("| VRT-EDR"))
    assert fila.count("|") - fila.count("\\|") == 5                # la celda no rompe la tabla
    # contraprueba: texto normal queda igual
    assert gap.md_texto("Cobertura 97 %") == "Cobertura 97 %"


# 12 (k): atribución del informe T15
def test_h12_informe_t15_atribuye_el_gris_a_ast_0001():
    t = (ROOT / "docs" / "plan" / "informes" / "T15-dev-proyecto.md").read_text(encoding="utf-8")
    assert "1 gris (AST-0001" in t and "1 gris (TEC-0001" not in t
    m = construir_mapa(ROOT / "technologies" / "registry.template.yaml", ROOT / "resources" / "internal" / "inventory.template.yaml",
                       ROOT / "vulnerabilities" / "tracker.template.csv", hoy=HOY)
    grises = [d["id"] for z in m["zonas"] for d in z["dispositivos"] if d["semaforo"] == "gris"] + \
             [d["id"] for d in m["sin_zona"] if d["semaforo"] == "gris"]
    assert grises == ["AST-0001"]            # lo que dice el informe es lo que da la ejecución real
    assert validar_mapa(m) == []
