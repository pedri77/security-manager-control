import copy
import xml.etree.ElementTree as ET

from smc import resources as R


def test_datos_validos():
    assert R.validar() == []


def test_ids_unicos_y_verificado_coherente():
    rss = R.cargar_rss()
    assert len({f["id"] for f in rss}) == len(rss) >= 15
    # verificado: true solo si hay url_feed (comprobada con red el 2026-11-03);
    # sin url_feed, verificado false y una nota con la alternativa.
    for f in rss:
        if f["verificado"]:
            assert f.get("url_feed"), f["id"]
        if not f.get("url_feed"):
            assert f["verificado"] is False and f.get("nota"), f["id"]


def test_opml_un_outline_por_feed_con_url():
    rss = R.cargar_rss()
    root = ET.fromstring(R.a_opml())
    outlines = root.findall("./body/outline")
    con_feed = [f for f in rss if f["url_feed"]]
    assert root.tag == "opml" and len(outlines) == len(con_feed) > 0
    assert {o.get("xmlUrl") for o in outlines} == {f["url_feed"] for f in con_feed}


def test_opml_escapa():
    xml = R.a_opml([{"nombre": 'a"<b>&', "url_feed": "https://x.example/f?a=1&b=2", "url_web": "https://x.example"}])
    o = ET.fromstring(xml).find("./body/outline")
    assert o.get("text") == 'a"<b>&' and o.get("xmlUrl").endswith("a=1&b=2")


def test_ningun_repo_privado():
    txt = (R.RSS_FILE.read_text() + R.ECO_FILE.read_text() + R.render_markdown()).lower()
    assert not any(p in txt for p in R.PROHIBIDOS)


def test_contraprueba_repo_privado_en_rojo():
    eco = copy.deepcopy(R.cargar_ecosistema())
    eco.append({"id": "X", "nombre": "x", "tipo": "repo", "estado": "publicado", "url": "https://github.com/pedri77/sase-evaluation-pack"})
    assert any("repo privado" in e for e in R.validar(eco=eco))
    rss = copy.deepcopy(R.cargar_rss())
    rss[0]["url_web"] = "https://github.com/pedri77/riskitera-news"
    assert any("repo privado" in e for e in R.validar(rss=rss))


def test_id_duplicado_y_http_y_pendiente_con_url():
    rss = copy.deepcopy(R.cargar_rss()); rss.append(dict(rss[0]))
    assert any("duplicado" in e for e in R.validar(rss=rss))
    rss = copy.deepcopy(R.cargar_rss()); rss[0]["url_feed"] = "http://x.example/f"
    assert any("https" in e for e in R.validar(rss=rss))
    eco = copy.deepcopy(R.cargar_ecosistema())
    pend = next(p for p in eco if p["estado"] == "pendiente"); pend["url"] = "https://x.example"
    assert any("pendiente no lleva URL" in e for e in R.validar(eco=eco))


def test_pendientes_requeridos():
    pend = {p["id"] for p in R.cargar_ecosistema() if p["estado"] == "pendiente"}
    assert pend == {"ECO-ZTNA", "ECO-VULN-OSI", "ECO-MAPA3D"}


def test_markdown():
    md = R.render_markdown()
    assert "pedri77.github.io/edr-visual-app" in md and "sin feed conocido" in md
