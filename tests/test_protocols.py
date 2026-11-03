"""T11: vulnerabilidades por protocolo y fuentes oficiales."""
import copy
from urllib.parse import urlparse

import pytest

from smc import protocols

EXIGIDOS = {"SMB", "RDP", "SSH", "TELNET", "FTP", "SNMP", "DNS", "NTP", "LDAP", "KERBEROS", "NTLM", "TLS", "HTTP",
            "SMTP", "IMAP_POP3", "SIP", "MQTT", "MODBUS", "S7COMM", "DNP3", "BACNET", "OPCUA"}
from smc.resources import urls_no_publicas


@pytest.fixture
def data():
    return copy.deepcopy(protocols.cargar())


def test_al_menos_20_protocolos_y_los_pedidos(data):
    ids = {p["id"] for p in protocols.protocolos(data)}
    assert len(ids) >= 20
    assert EXIGIDOS <= ids


def test_catalogo_valido():
    assert protocols.validar() == []


def test_capas_1_a_7_y_por_capa():
    capas = protocols.por_capa()
    assert all(1 <= c <= 7 for c in capas)
    assert list(capas) == sorted(capas)
    assert {"SMB", "TLS", "ARP", "ICMP"} <= {p["id"] for ps in capas.values() for p in ps}
    assert any(p["id"] == "ARP" for p in capas[2]) and any(p["id"] == "TLS" for p in capas[6])


def test_toda_url_https_y_de_dominio_permitido(data):
    doms = protocols.dominios_permitidos()
    assert "pedri77.github.io" in doms and "nvd.nist.gov" in doms
    for p in data["protocolos"]:
        for url in p["consulta"].values():
            u = urlparse(url)
            assert u.scheme == "https" and u.hostname in doms
    for a in data["aprendizaje"].values():
        assert urlparse(a["url"]).hostname in doms


def test_fuentes_requeridas():
    nombres = {f["nombre"] for f in protocols.cargar_fuentes()}
    assert {"NVD", "EUVD", "CISA KEV", "CVE Details", "INCIBE-CERT", "CCN-CERT"} <= nombres
    for f in protocols.cargar_fuentes():
        assert {"nombre", "organismo", "url", "tipo", "uso"} <= set(f)


def test_enlaces_de_aprendizaje_a_las_pages_pedidas(data):
    urls = {a["url"] for a in data["aprendizaje"].values()}
    assert {"https://pedri77.github.io/modelo_OSI/", "https://pedri77.github.io/Basicos_Proteccion_Capas_OSI/",
            "https://pedri77.github.io/ics-security-studio/", "https://pedri77.github.io/wafforge/"} <= urls
    assert "waf" in protocols.obtener("HTTP")["aprendizaje"]
    assert "ics" in protocols.obtener("Modbus")["aprendizaje"]


def test_sin_cves_concretos_ni_repos_privados():
    texto = protocols.PROTOCOLS_FILE.read_text(encoding="utf-8")
    import re
    assert not re.search(r"CVE-\d{4}-\d{3,}", texto)
    assert urls_no_publicas(texto) == []


def test_contraprueba_dominio_no_permitido(data):
    data["protocolos"][0]["consulta"]["nvd"] = "https://evil.example.com/search?q=SMB"
    assert any("dominio no permitido" in e for e in protocols.validar(data))


def test_contraprueba_http_no_https(data):
    data["protocolos"][0]["consulta"]["nvd"] = "http://nvd.nist.gov/x"
    assert any("https" in e for e in protocols.validar(data))


def test_contraprueba_control_inexistente(data):
    data["protocolos"][0]["controles"].append("NET-XXX-99")
    assert any("control inexistente NET-XXX-99" in e for e in protocols.validar(data))


@pytest.mark.parametrize("capa", [0, 8, "7", None])
def test_contraprueba_capa_fuera_de_rango(data, capa):
    data["protocolos"][0]["capa_osi"] = capa
    assert protocols.validar(data)


def test_contraprueba_cwe_attack_id_duplicado_y_faltantes(data):
    data["protocolos"][0]["cwe"] = ["CWE-x"]
    data["protocolos"][1]["attack"] = ["T12"]
    data["protocolos"][2]["id"] = data["protocolos"][3]["id"]
    del data["protocolos"][4]["consulta"]["euvd"]
    errs = " | ".join(protocols.validar(data))
    assert "CWE con formato" in errs and "ATT&CK con formato" in errs
    assert "duplicado" in errs and "consulta sin fuente 'euvd'" in errs


def test_render_protocolo():
    md = protocols.render_protocolo("smb")
    assert md.startswith("# SMB / CIFS (capa OSI 7)")
    assert "445/tcp" in md and "https://nvd.nist.gov/" in md and "[Modelo OSI]" in md
    assert "sin puerto" in protocols.render_protocolo("ARP")
    with pytest.raises(ValueError):
        protocols.render_protocolo("NOEXISTE")
