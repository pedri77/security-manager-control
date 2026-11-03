from pathlib import Path

from smc.catalog import load_all, validate
from smc.gap import analyse, frameworks_in_scope, run

EXAMPLE = Path(__file__).resolve().parent.parent / "assessments" / "examples" / "ejemplo-ayuntamiento.yaml"


def test_catalogs_valid():
    assert validate() == []


def test_ens_has_73_measures():
    assert len(load_all()["ENS"]) == 73


def test_scope_private_vs_public():
    assert "ENS" not in frameworks_in_scope({"sector_publico": False})
    assert "ENS" in frameworks_in_scope({"sector_publico": True})
    assert "ENS" in frameworks_in_scope({"proveedor_sector_publico": True})


def test_scoring_and_no_aplica():
    _, results, warnings = analyse(
        {
            "cliente": {"sector_publico": False},
            "evaluaciones": {
                "NIS2-20.1": {"estado": "implementado", "evidencias": ["acta"]},
                "NIS2-20.2": {"estado": "parcial"},
                "NIS2-21.2.a": {"estado": "no_aplica"},
            },
        }
    )
    nis2 = next(r for r in results if r.framework == "NIS2")
    assert nis2.aplicables == nis2.total - 1
    assert nis2.puntuacion == round(100 * 1.5 / nis2.aplicables, 1)
    assert warnings == []


ROOT = EXAMPLE.parent.parent.parent


def test_soc_metrics():
    from smc.soc import soc_metrics
    m = soc_metrics(ROOT / "soc" / "incidents.template.csv")
    assert m["total"] == 5
    assert m["nis2_significativos"] == 2 and m["nis2_en_plazo"] == 1   # INC-0005 notificado a las 32 h
    assert round(m["por_severidad"]["critica"]["mtta"]) == 6


def test_mitre_coverage():
    from smc.soc import mitre_coverage
    assert "T1003.001" in mitre_coverage()


def test_expiring():
    from datetime import date
    from smc.tech import expiring
    items = expiring(ROOT / "technologies" / "registry.template.yaml", 60, today=date(2026, 11, 2))
    tipos = {(i[1], i[3]) for i in items}
    assert ("TEC-0002", "Licencia") in tipos
    assert ("TEC-0002", "Certificado vpn.ejemplo.es") in tipos
    assert all(i[1] != "TEC-0001" for i in items)


def test_vulns_sla():
    from datetime import date
    from smc.tech import vulns
    out = vulns(ROOT / "vulnerabilities" / "tracker.template.csv", today=date(2026, 11, 2))
    assert "Fuera de SLA: 2" in out


def test_refs_valid():
    from smc.refs import validate_refs
    assert validate_refs() == []


def test_refs_for_incident_management():
    from smc.refs import refs_for
    ids = {r["id"] for r in refs_for("NIS2-21.2.b")}
    assert {"CCN-STIC-817", "CCN-CERT-BP-21", "NIS2 art. 21", "RE 2024/2690 Anexo §3"} <= ids


def test_refs_wildcard():
    from smc.refs import refs_for
    ids = {r["id"] for r in refs_for("ENS-mp.if.3")}
    assert "CCN-STIC-804" in ids and "CCN-STIC-808" in ids


def test_example_report_renders():
    report = run(EXAMPLE)
    assert "# Informe de brechas" in report
    assert "| ENS |" in report
