from datetime import date

import yaml

from smc import mitre
from smc.catalog import ROOT
from smc.soc import mitre_coverage

HOY = date(2026, 11, 3)


def _caso(**kw):
    base = {"id": "UC-X", "nombre": "x", "tactica": "execution", "mitre": ["T1059"],
            "deteccion": "sin", "playbook": "", "estado": "activo", "ultima_prueba": ""}
    base.update(kw)
    return base


def _root(tmp_path, casos, playbooks=()):
    d = tmp_path / "vulnerabilities/playbooks/caso-uso"
    d.mkdir(parents=True)
    for p in playbooks:
        (d / p).write_text("# pb", encoding="utf-8")
    f = tmp_path / "catalog.yaml"
    f.write_text(yaml.safe_dump({"use_cases": casos}), encoding="utf-8")
    return f, tmp_path


PB = "vulnerabilities/playbooks/caso-uso/PB-UC-900.md"


def test_niveles(tmp_path):
    casos = [
        _caso(id="A", mitre=["T1001"], tactica="c2"),
        _caso(id="B", mitre=["T1002"], deteccion="regla"),
        _caso(id="C", mitre=["T1003"], deteccion="regla", playbook=PB),
        _caso(id="D", mitre=["T1004"], deteccion="probada", playbook=PB, ultima_prueba="2026-01-01"),
        _caso(id="E", mitre=["T1005"], deteccion="probada", playbook=PB, ultima_prueba="2026-09-15"),
    ]
    f, r = _root(tmp_path, casos, ["PB-UC-900.md"])
    m = mitre.madurez(f, HOY, r)["casos"]
    assert m == {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}


def test_ventana_90_dias_con_hoy(tmp_path):
    c = _caso(deteccion="probada", playbook=PB, ultima_prueba="2026-08-05")  # 90 d
    f, r = _root(tmp_path, [c], ["PB-UC-900.md"])
    assert mitre.madurez(f, date(2026, 11, 3), r)["casos"]["UC-X"] == 5
    assert mitre.madurez(f, date(2026, 11, 4), r)["casos"]["UC-X"] == 4


def test_playbook_inexistente_no_sube_nivel(tmp_path):
    f, r = _root(tmp_path, [_caso(deteccion="regla", playbook=PB)])
    assert mitre.madurez(f, HOY, r)["casos"]["UC-X"] == 2
    assert mitre.sin_playbook(f, r) == ["UC-X"]


def test_tecnica_toma_el_maximo_y_tactica_el_minimo(tmp_path):   # T17: la táctica pasa de máximo a mínimo
    casos = [_caso(id="A", deteccion="regla"),
             _caso(id="B", deteccion="regla", playbook=PB)]
    f, r = _root(tmp_path, casos, ["PB-UC-900.md"])
    m = mitre.madurez(f, HOY, r)
    assert m["tecnicas"]["T1059"] == 3 and m["tacticas"]["execution"] == 2


def test_retirado_no_cuenta_y_huerfanos(tmp_path):
    casos = [_caso(estado="retirado", deteccion="regla", playbook=PB)]
    f, r = _root(tmp_path, casos, ["PB-UC-900.md"])
    assert mitre.madurez(f, HOY, r)["tecnicas"] == {}
    assert mitre.playbooks_huerfanos(f, r) == [PB]


def test_navigator(tmp_path):
    f, r = _root(tmp_path, [_caso(deteccion="regla")])
    nav = mitre.a_navigator(f, HOY, r)
    assert nav["domain"] == "enterprise-attack" and nav["name"] and "gradient" in nav and "versions" in nav
    assert nav["techniques"] == [{"techniqueID": "T1059", "score": 2, "comment": "Casos: UC-X"}]


# --- catálogo real ---
def test_playbooks_referenciados_existen():
    for u in mitre.cargar():
        pb = u.get("playbook")
        assert pb, f"{u['id']} sin playbook"
        assert (ROOT / pb).is_file(), f"{u['id']}: falta {pb}"
    assert mitre.sin_playbook() == []


def test_catalogo_real_campos_y_sin_huerfanos():
    verticales = {v["id"] for v in yaml.safe_load((ROOT / "soc/verticals.yaml").read_text(encoding="utf-8"))["verticals"]}
    for u in mitre.cargar():
        assert u["deteccion"] in ("sin", "regla", "probada")
        assert u["vertical"] in verticales and u["mitre"]
        assert "ultima_prueba" in u
    assert mitre.playbooks_huerfanos() == []


def test_catalogo_real_navigator_y_cobertura():
    nav = mitre.a_navigator(hoy=HOY)
    assert all("score" in t for t in nav["techniques"])
    assert {t["techniqueID"]: t["score"] for t in nav["techniques"]}["T1110"] == 5
    assert "T1003.001" in mitre_coverage(hoy=HOY)
