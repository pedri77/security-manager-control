"""T33: evidencias con fecha, caducidad y huella."""
import hashlib
import os
from datetime import date
from pathlib import Path

import pytest
import yaml

from smc import evidencias as ev
from smc import gap

HOY = date(2026, 11, 3)
ROOT = Path(__file__).resolve().parent.parent


def test_cuatro_estados():
    assert ev.estado({"ref": "a", "fecha": "2026-01-01", "caduca": "2027-06-01"}, HOY) == "vigente"
    assert ev.estado({"ref": "a", "fecha": "2026-01-01", "caduca": "2026-11-20"}, HOY) == "caduca_pronto"
    assert ev.estado({"ref": "a", "caduca": date(2026, 11, 3)}, HOY) == "caduca_pronto"  # el día mismo aún vale
    assert ev.estado({"ref": "a", "fecha": "2025-01-01", "caduca": "2026-11-02"}, HOY) == "caducada"
    assert ev.estado("texto plano", HOY) == "sin_fecha"
    assert ev.estado({"ref": "a"}, HOY) == "sin_fecha"


def test_vigencia_dias_y_normalizar():
    n = ev.normalizar({"ref": "r", "fecha": "2025-11-03", "vigencia_dias": 365})
    assert n["caduca"] == date(2026, 11, 3) and not n["avisos"]
    assert ev.estado({"ref": "r", "fecha": "2025-01-15", "vigencia_dias": 365}, HOY) == "caducada"
    # contraprueba: datos malos no rompen, avisan
    for malo in ({"ref": "r", "vigencia_dias": 30}, {"ref": "r", "fecha": "x"}, {"ref": "r", "fecha": "2025-01-01", "vigencia_dias": -1},
                 {"ref": "r", "sha256": "zz"}, {"fecha": "2025-01-01"}):
        assert ev.normalizar(malo)["avisos"]
        ev.estado(malo, HOY)
    assert ev.normalizar("hola")["ref"] == "hola"


def _ass(ref, sha):
    return {"evaluaciones": {"NIS2-20.1": {"estado": "implementado", "evidencias": [{"ref": ref, "sha256": sha}]}}}


def test_huella_correcta_e_incorrecta(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_bytes(b"contenido ficticio" * 10000)
    h = hashlib.sha256(f.read_bytes()).hexdigest()
    assert ev.verificar_huellas(_ass("doc.txt", h), tmp_path)[0]["resultado"] == "ok"
    assert ev.verificar_huellas(_ass("doc.txt", h.upper()), tmp_path)[0]["resultado"] == "ok"
    r = ev.verificar_huellas(_ass("doc.txt", "0" * 64), tmp_path)[0]
    assert r["resultado"] == "discrepancia" and r["aviso"]
    assert ev.verificar_huellas(_ass("nada.txt", h), tmp_path)[0]["resultado"] == "no_encontrada"
    assert ev.verificar_huellas(_ass("doc.txt", None), tmp_path) == []  # sin huella declarada no se lee


def test_rutas_peligrosas_no_se_leen(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    (tmp_path / "secreto.txt").write_text("fuera")
    h = hashlib.sha256(b"fuera").hexdigest()
    os.symlink(tmp_path / "secreto.txt", base / "enlace.txt")
    os.symlink(tmp_path, base / "dirfuera")
    (base / "dentro.txt").write_text("fuera")
    os.symlink(base / "dentro.txt", base / "enlace_ok.txt")
    for ref in ("../../etc/passwd", "../secreto.txt", "/etc/passwd", str(tmp_path / "secreto.txt"), "a/../../secreto.txt",
                "enlace.txt", "dirfuera/secreto.txt", "~/x", "C:\\x", "..\\x", "a\x00b", ""):
        r = ev.verificar_huellas(_ass(ref, h), base)[0]
        assert r["resultado"] == "rechazada", ref
        assert "no se lee" in r["aviso"]
    # un enlace que queda dentro de base sí vale
    assert ev.verificar_huellas(_ass("enlace_ok.txt", h), base)[0]["resultado"] == "ok"


def test_render_markdown(tmp_path):
    a = {"evaluaciones": {"NIS2-20.1": {"estado": "implementado", "evidencias": [
        "texto", {"ref": "<script>x</script>", "fecha": "2025-01-01", "caduca": "2025-12-31"},
        {"ref": "../x", "sha256": "a" * 64}]}}}
    md = ev.render_markdown(a, HOY, base=tmp_path)
    assert "caducada" in md and "sin_fecha" in md and "<script>" not in md and "&lt;script&gt;" in md
    assert "rechazada" in md


def _implementado(evs):
    return {"cliente": {"nombre": "Ejemplo", "tipo_entidad_nis2": "esencial"},
            "evaluaciones": {"NIS2-20.1": {"estado": "implementado", "evidencias": evs}}}


def _nis2(an):
    return next(r for r in an.results if r.framework == "NIS2")


def test_gap_lista_caducada_sin_cambiar_puntuacion():
    cad = {"ref": "x", "fecha": "2024-01-01", "vigencia_dias": 100}
    base = _nis2(gap.analyse(_implementado(["texto"]), HOY))
    con = _nis2(gap.analyse(_implementado([cad]), HOY))
    assert [c.id for c in con.evidencia_caducada] == ["NIS2-20.1"] and not base.evidencia_caducada
    assert con.puntuacion == base.puntuacion and not con.sin_evidencia
    md = gap.render_markdown(gap.analyse(_implementado([cad]), HOY))
    assert "Evidencia caducada (1)" in md and "NIS2-20.1" in md
    # contraprueba: si queda una evidencia vigente o de texto, no se lista
    for evs in ([cad, "texto"], [cad, {"ref": "y", "caduca": "2030-01-01"}]):
        assert not _nis2(gap.analyse(_implementado(evs), HOY)).evidencia_caducada
    assert "Evidencia caducada" not in gap.render_markdown(gap.analyse(_implementado(["t"]), HOY))


def test_ejemplo_energia_y_plantilla():
    ass = yaml.safe_load((ROOT / "assessments/examples/ejemplo-energia.yaml").read_text(encoding="utf-8"))
    an = gap.analyse(ass, HOY)
    assert [c.id for c in _nis2(an).evidencia_caducada] == ["NIS2-21.2.a"]
    # misma puntuación que con el texto plano original
    plano = yaml.safe_load((ROOT / "assessments/examples/ejemplo-energia.yaml").read_text(encoding="utf-8"))
    for k in ("NIS2-21.2.a", "NIS2-21.2.f"):
        plano["evaluaciones"][k]["evidencias"] = ["texto"]
    assert [r.puntuacion for r in gap.analyse(plano, HOY).results] == [r.puntuacion for r in an.results]
    assert yaml.safe_load((ROOT / "assessments/assessment.template.yaml").read_text(encoding="utf-8"))
