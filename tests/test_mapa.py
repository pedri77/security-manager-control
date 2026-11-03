"""T15: mapa de dispositivos (JSON smc-mapa/1)."""
import json
import shutil
import tempfile
from datetime import date
from pathlib import Path

import pytest
import yaml

import smc.mapa as mapa
from smc.cli import main
from smc.mapa import construir_mapa, validar_mapa

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "technologies" / "registry.template.yaml"
INV = ROOT / "resources" / "internal" / "inventory.template.yaml"
TRK = ROOT / "vulnerabilities" / "tracker.template.csv"
ENERGIA = ROOT / "assessments" / "examples" / "ejemplo-energia.yaml"
HOY = date(2026, 11, 3)

def _sin_zonas(origen, clave, destino):
    """Copia de una plantilla sin `zona` ni `capa_osi` (las plantillas ya las traen desde T16)."""
    data = yaml.safe_load(origen.read_text(encoding="utf-8"))
    for e in data[clave]:
        e.pop("zona", None)
        e.pop("capa_osi", None)
    destino.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return destino


_TMP = Path(tempfile.mkdtemp(prefix="smc-mapa-test-"))
REG_SIN = _sin_zonas(REG, "technologies", _TMP / "reg.yaml")
INV_SIN = _sin_zonas(INV, "activos", _TMP / "inv.yaml")

ZONAS_POR_ID = {"TEC-0001": "usuarios", "TEC-0002": "perimetro", "TEC-0003": "perimetro",
                "TEC-0004": "usuarios", "TEC-0005": "nube"}


def registro_con_zonas(tmp_path, sin=()):
    data = yaml.safe_load(REG_SIN.read_text(encoding="utf-8"))
    for t in data["technologies"]:
        z = ZONAS_POR_ID.get(t["id"])
        if z and t["id"] not in sin:
            t["zona"] = z
    p = tmp_path / "reg.yaml"
    p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return p


def por_id(m):
    out = {}
    for z in m["zonas"]:
        for d in z["dispositivos"]:
            out[d["id"]] = d
    for d in m["sin_zona"]:
        out[d["id"]] = d
    return out


def test_esquema_valido_con_plantillas(tmp_path):
    m = construir_mapa(registro_con_zonas(tmp_path), INV_SIN, TRK, ENERGIA, HOY)
    assert validar_mapa(m) == []
    assert m["schema"] == "smc-mapa/1"
    assert m["resumen"]["dispositivos"] == 6 and m["resumen"]["sin_zona"] == 1   # AST-0001 sin zona
    assert [z["id"] for z in m["zonas"]] == list(mapa.ZONAS)


def test_json_serializable_sin_rutas_absolutas(tmp_path):
    m = construir_mapa(registro_con_zonas(tmp_path), INV_SIN, TRK, ENERGIA, HOY)
    texto = json.dumps(m, ensure_ascii=False)
    assert not mapa.contiene_ruta_absoluta(m)
    assert str(ROOT) not in texto and str(tmp_path) not in texto and "/Users/" not in texto


def test_detector_de_rutas_absolutas_detecta():
    assert mapa.contiene_ruta_absoluta({"a": ["/Users/alguien/x"]})
    assert not mapa.contiene_ruta_absoluta({"a": "technologies/registry.template.yaml"})


def test_dispositivo_sin_zona_va_a_sin_zona_y_no_rompe(tmp_path):
    reg = registro_con_zonas(tmp_path, sin=("TEC-0002",))
    m = construir_mapa(reg, None, TRK, None, HOY)
    assert validar_mapa(m) == []
    ids_sin = [d["id"] for d in m["sin_zona"]]
    assert "TEC-0002" in ids_sin
    d = por_id(m)["TEC-0002"]
    assert d["zona"] is None and d["motivo_sin_zona"] == "sin zona asignada"
    assert all(d["id"] != "TEC-0002" for z in m["zonas"] for d in z["dispositivos"])


def test_zona_desconocida_va_a_sin_zona_con_motivo(tmp_path):
    data = yaml.safe_load(REG.read_text(encoding="utf-8"))
    data["technologies"][0]["zona"] = "marte"
    p = tmp_path / "r.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    m = construir_mapa(p, hoy=HOY)
    assert por_id(m)["TEC-0001"]["motivo_sin_zona"] == "zona 'marte' no reconocida"
    assert validar_mapa(m) == []


def test_plantillas_traen_zona_y_nada_cae_en_sin_zona():
    m = construir_mapa(REG, INV, TRK, ENERGIA, HOY)
    assert m["resumen"]["dispositivos"] == 6 and m["resumen"]["sin_zona"] == 0
    assert sum(z["n_dispositivos"] for z in m["zonas"]) == 6
    assert all(d["capa_osi_origen"] == "declarada" for z in m["zonas"] for d in z["dispositivos"])
    assert validar_mapa(m) == []


def test_plantilla_sin_zonas_todo_en_sin_zona():
    m = construir_mapa(REG_SIN, INV_SIN, TRK, None, HOY)
    assert m["resumen"]["sin_zona"] == m["resumen"]["dispositivos"] == 6
    assert all(z["n_dispositivos"] == 0 and z["semaforo"] == "gris" for z in m["zonas"])
    assert validar_mapa(m) == []


def test_no_evaluable_lleva_motivo_y_es_gris():
    d = por_id(construir_mapa(REG, None, None, None, HOY))["TEC-0001"]
    assert d["reglas"]["estado"] == "no_evaluable"
    assert "sin acceso a la consola" in d["reglas"]["motivo"]
    assert d["semaforo"] == "gris"


def test_no_evaluable_sin_motivo_invalida_el_esquema():
    m = construir_mapa(REG, None, None, None, HOY)
    por_id(m)["TEC-0001"]["reglas"]["motivo"] = ""
    assert any("sin motivo" in e for e in validar_mapa(m))


def test_semaforo_rojo_por_kev_fuera_de_sla():
    d = por_id(construir_mapa(REG, None, TRK, None, HOY))["TEC-0002"]
    assert d["vulnerabilidades"] == {"abiertas": 1, "fuera_sla": 1, "kev_fuera_sla": 1, "kev_o_criticas_abiertas": 1,
                                     "peor_severidad": "critica", "cves_fuera_sla": ["CVE-0000-0001"]}
    assert d["semaforo"] == "rojo"
    # la tecnología tiene además 6 reglas any-any
    assert d["reglas"]["reglas_any_any"] == 6


def test_vuln_remediada_no_cuenta_y_sla_depende_de_hoy():
    # CVE-0000-0002 (alta, SLA 30 d, detectada 2026-10-01): fuera de SLA el 03-11, dentro el 15-10
    m_tarde = construir_mapa(REG, None, TRK, None, HOY)
    m_pronto = construir_mapa(REG, None, TRK, None, date(2026, 10, 15))
    assert por_id(m_tarde)["TEC-0001"]["vulnerabilidades"]["abiertas"] == 1     # la remediada no cuenta
    assert por_id(m_tarde)["TEC-0001"]["vulnerabilidades"]["fuera_sla"] == 1
    assert por_id(m_pronto)["TEC-0001"]["vulnerabilidades"]["fuera_sla"] == 0


def test_sla_estricto_en_el_limite():
    # alta, detectada 2026-10-01 + 30 días = 2026-10-31: justo en el límite NO está fuera
    d = por_id(construir_mapa(REG, None, TRK, None, date(2026, 10, 31)))["TEC-0001"]
    assert d["vulnerabilidades"]["fuera_sla"] == 0
    d = por_id(construir_mapa(REG, None, TRK, None, date(2026, 11, 1)))["TEC-0001"]
    assert d["vulnerabilidades"]["fuera_sla"] == 1


def test_semaforos_de_las_plantillas():
    m = por_id(construir_mapa(REG, INV, TRK, None, HOY))
    assert m["TEC-0003"]["semaforo"] == "verde"          # reglas revisadas, sin vulns
    assert m["TEC-0005"]["semaforo"] == "ambar"          # reglas sin revisar
    assert m["AST-0001"]["semaforo"] == "gris"           # sin datos de reglas
    assert m["AST-0001"]["reglas"]["estado"] == "sin_datos"


def test_semaforo_de_zona_es_el_peor(tmp_path):
    m = construir_mapa(registro_con_zonas(tmp_path), None, TRK, None, HOY)
    z = {z["id"]: z for z in m["zonas"]}
    assert z["perimetro"]["semaforo"] == "rojo"          # TEC-0002 rojo + TEC-0003 verde
    assert z["nube"]["semaforo"] == "ambar"
    assert z["dmz"]["semaforo"] == "gris" and z["dmz"]["n_dispositivos"] == 0


def test_capa_osi_declarada_o_por_vertical():
    m = por_id(construir_mapa(REG_SIN, None, None, None, HOY))
    assert m["TEC-0002"]["capa_osi"] == 4 and m["TEC-0002"]["capa_osi_origen"] == "vertical"   # VRT-FW (T17)
    assert m["TEC-0001"]["capa_osi"] == 7
    data = yaml.safe_load(REG_SIN.read_text(encoding="utf-8"))
    data["technologies"][1]["capa_osi"] = 2
    data["technologies"][0]["capa_osi"] = 9           # inválida: se ignora y cae a la vertical
    m = por_id(construir_mapa(data, None, None, None, HOY))
    assert m["TEC-0002"]["capa_osi"] == 2 and m["TEC-0002"]["capa_osi_origen"] == "declarada"
    assert m["TEC-0001"]["capa_osi"] == 7 and m["TEC-0001"]["capa_osi_origen"] == "vertical"


def test_madurez_de_vertical_desde_la_evaluacion():
    m = por_id(construir_mapa(REG, None, None, ENERGIA, HOY))
    assert m["TEC-0001"]["madurez_vertical"] == 4          # VRT-EDR del ejemplo
    assert por_id(construir_mapa(REG, None, None, None, HOY))["TEC-0001"]["madurez_vertical"] is None


def test_id_duplicado_y_tracker_huerfano_dan_aviso(tmp_path):
    data = yaml.safe_load(REG.read_text(encoding="utf-8"))
    data["technologies"].append(dict(data["technologies"][0]))
    csv_ = tmp_path / "t.csv"
    csv_.write_text("cve,tecnologia_id,severidad,estado,detectado,kev\nCVE-X,TEC-9999,alta,abierta,2026-01-01,false\n", encoding="utf-8")
    m = construir_mapa(data, None, csv_, None, HOY)
    assert any("duplicado" in a for a in m["avisos"])
    assert any("TEC-9999" in a for a in m["avisos"])
    assert validar_mapa(m) == []


def test_entradas_mal_formadas_no_rompen():
    assert validar_mapa(construir_mapa({"technologies": "texto"}, {"activos": 5}, None, None, HOY)) == []
    assert validar_mapa(construir_mapa({}, None, None, None, HOY)) == []


def test_validador_detecta_esquema_roto(tmp_path):
    m = construir_mapa(registro_con_zonas(tmp_path), INV_SIN, TRK, None, HOY)
    m["schema"] = "otro/1"
    assert validar_mapa(m)
    m = construir_mapa(registro_con_zonas(tmp_path), INV_SIN, TRK, None, HOY)
    por_id(m)["TEC-0002"]["semaforo"] = "azul"
    assert any("azul" in e for e in validar_mapa(m))
    m = construir_mapa(registro_con_zonas(tmp_path), INV_SIN, TRK, None, HOY)
    m["sin_zona"][0]["zona"] = "dmz"
    assert any("sin_zona" in e for e in validar_mapa(m))
    assert validar_mapa([]) and validar_mapa({"schema": "smc-mapa/1"})


def test_solo_campos_de_la_lista_blanca():
    d = por_id(construir_mapa(REG, None, None, None, HOY))["TEC-0001"]
    permitidos = {"id", "nombre", "tipo", "origen", "zona", "capa_osi", "capa_osi_origen", "vertical", "reglas",
                  "vulnerabilidades", "semaforo", "semaforo_motivos", "evaluacion", "madurez_vertical"}
    assert set(d) <= permitidos | {"motivo_sin_zona"}
    texto = json.dumps(d)
    for secreto in ("propietario", "coste_anual", "Proveedor A", "cpe"):
        assert secreto not in texto


# --- CLI ---

def test_cli_mapa_escribe_json_valido(tmp_path, capsys):
    out = tmp_path / "mapa.json"
    rc = main(["mapa", str(registro_con_zonas(tmp_path)), "--inventario", str(INV), "--tracker", str(TRK),
               "--evaluacion", str(ENERGIA), "--hoy", "2026-11-03", "-o", str(out)])
    assert rc == 0
    m = json.loads(out.read_text(encoding="utf-8"))
    assert validar_mapa(m) == [] and m["generado_para"] == "2026-11-03"
    assert not mapa.contiene_ruta_absoluta(m)


def test_cli_mapa_stdout_y_determinista(tmp_path, capsys):
    args = ["mapa", str(REG), "--hoy", "2026-11-03"]
    assert main(args) == 0
    a = capsys.readouterr().out
    assert main(args) == 0
    assert a == capsys.readouterr().out
    assert json.loads(a)["schema"] == "smc-mapa/1"


def test_cli_mapa_fichero_inexistente_rc2(tmp_path, capsys):
    assert main(["mapa", str(tmp_path / "no.yaml")]) == 2
    assert "no existe" in capsys.readouterr().err
    assert main(["mapa", str(REG), "--tracker", str(tmp_path / "no.csv")]) == 2


def test_cli_mapa_yaml_roto_rc2(tmp_path, capsys):
    p = tmp_path / "roto.yaml"
    p.write_text("a: [1, 2\n", encoding="utf-8")
    assert main(["mapa", str(p)]) == 2
    assert "ERROR" in capsys.readouterr().err
