"""vigilancia.py y vigilancia.yml (SMC-009, T52).

Fixtures medidos el 2026-11-07 con la imagen fijada en ci.yml (osv-scanner v2.7.0, `scan source -r --format json`):
  - este repo (uv.lock, 11 paquetes): código 0, JSON con `results: []`.
  - carpeta temporal con requirements.txt `django==1.11.0` y `pyyaml==5.3`: código 1, 552 KB de JSON
    (django 49 vulnerabilidades en 30 grupos, pyyaml 4 en 2 grupos); aquí recortado a 2 grupos por paquete,
    sin `details`, `references` ni `versions`. Todas las vulnerabilidades medidas traían versión corregida.
  - carpeta vacía y carpeta con solo pyproject.toml: código 128, stdout vacío, stderr «No package sources found».
  - ruta inexistente u opción desconocida: código 127, stdout vacío.
"""
import copy
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts/vigilancia.py"
WORKFLOW = RAIZ / ".github/workflows/vigilancia.yml"
CI = RAIZ / ".github/workflows/ci.yml"
TITULO = "[vigilancia] vulnerabilidades en dependencias"

OSV_HALLAZGOS = json.loads(r'''{
 "results": [
  {
   "source": {
    "path": "/src/requirements.txt",
    "type": "lockfile"
   },
   "packages": [
    {
     "package": {
      "name": "django",
      "version": "1.11.0",
      "ecosystem": "PyPI",
      "purl": "pkg:pypi/django@1.11.0"
     },
     "groups": [
      {
       "ids": [
        "PYSEC-2017-44",
        "GHSA-9r8w-6x8c-6jr9"
       ],
       "aliases": [
        "CVE-2017-12794",
        "GHSA-9r8w-6x8c-6jr9",
        "PYSEC-2017-44"
       ],
       "max_severity": "6.1"
      },
      {
       "ids": [
        "PYSEC-2018-2",
        "GHSA-5hg3-6c2f-f3wr"
       ],
       "aliases": [
        "CVE-2018-14574",
        "GHSA-5hg3-6c2f-f3wr",
        "PYSEC-2018-2"
       ],
       "max_severity": "6.1"
      }
     ],
     "vulnerabilities": [
      {
       "id": "PYSEC-2017-44",
       "aliases": [
        "CVE-2017-12794",
        "GHSA-9r8w-6x8c-6jr9"
       ],
       "modified": "2023-11-08T03:58:54.215558Z",
       "published": "2017-09-07T13:29:00Z",
       "affected": [
        {
         "package": {
          "ecosystem": "PyPI",
          "name": "django",
          "purl": "pkg:pypi/django"
         },
         "ranges": [
          {
           "events": [
            {
             "introduced": "1.10"
            },
            {
             "fixed": "1.10.8"
            },
            {
             "introduced": "1.11"
            },
            {
             "fixed": "1.11.5"
            }
           ],
           "type": "ECOSYSTEM"
          }
         ]
        }
       ]
      },
      {
       "id": "PYSEC-2018-2",
       "aliases": [
        "CVE-2018-14574",
        "GHSA-5hg3-6c2f-f3wr"
       ],
       "modified": "2023-11-08T03:59:55.770463Z",
       "published": "2018-08-03T17:29:00Z",
       "affected": [
        {
         "package": {
          "ecosystem": "PyPI",
          "name": "django",
          "purl": "pkg:pypi/django"
         },
         "ranges": [
          {
           "events": [
            {
             "introduced": "2.0"
            },
            {
             "fixed": "2.0.8"
            },
            {
             "introduced": "1.11"
            },
            {
             "fixed": "1.11.15"
            }
           ],
           "type": "ECOSYSTEM"
          }
         ]
        }
       ]
      },
      {
       "id": "GHSA-5hg3-6c2f-f3wr",
       "aliases": [
        "CVE-2018-14574",
        "PYSEC-2018-2"
       ],
       "modified": "2024-09-17T15:21:46.347995Z",
       "published": "2018-10-04T21:58:46Z",
       "affected": [
        {
         "package": {
          "ecosystem": "PyPI",
          "name": "django",
          "purl": "pkg:pypi/django"
         },
         "ranges": [
          {
           "events": [
            {
             "introduced": "2.0"
            },
            {
             "fixed": "2.0.8"
            }
           ],
           "type": "ECOSYSTEM"
          }
         ]
        },
        {
         "package": {
          "ecosystem": "PyPI",
          "name": "django",
          "purl": "pkg:pypi/django"
         },
         "ranges": [
          {
           "events": [
            {
             "introduced": "1.11"
            },
            {
             "fixed": "1.11.15"
            }
           ],
           "type": "ECOSYSTEM"
          }
         ]
        }
       ]
      },
      {
       "id": "GHSA-9r8w-6x8c-6jr9",
       "aliases": [
        "CVE-2017-12794",
        "PYSEC-2017-44"
       ],
       "modified": "2024-09-18T16:07:48.238600Z",
       "published": "2019-01-04T17:50:34Z",
       "affected": [
        {
         "package": {
          "ecosystem": "PyPI",
          "name": "django",
          "purl": "pkg:pypi/django"
         },
         "ranges": [
          {
           "events": [
            {
             "introduced": "1.10a1"
            },
            {
             "fixed": "1.10.8"
            }
           ],
           "type": "ECOSYSTEM"
          }
         ]
        },
        {
         "package": {
          "ecosystem": "PyPI",
          "name": "django",
          "purl": "pkg:pypi/django"
         },
         "ranges": [
          {
           "events": [
            {
             "introduced": "1.11a1"
            },
            {
             "fixed": "1.11.5"
            }
           ],
           "type": "ECOSYSTEM"
          }
         ]
        }
       ]
      }
     ]
    },
    {
     "package": {
      "name": "pyyaml",
      "version": "5.3.0",
      "ecosystem": "PyPI",
      "purl": "pkg:pypi/pyyaml@5.3.0"
     },
     "groups": [
      {
       "ids": [
        "PYSEC-2020-96",
        "GHSA-6757-jp84-gxfx"
       ],
       "aliases": [
        "CVE-2020-1747",
        "GHSA-6757-jp84-gxfx",
        "PYSEC-2020-96"
       ],
       "max_severity": "9.8"
      },
      {
       "ids": [
        "PYSEC-2021-142",
        "GHSA-8q59-q68h-6hv4"
       ],
       "aliases": [
        "CVE-2020-14343",
        "GHSA-8q59-q68h-6hv4",
        "PYSEC-2021-142"
       ],
       "max_severity": "9.8"
      }
     ],
     "vulnerabilities": [
      {
       "id": "PYSEC-2020-96",
       "aliases": [
        "CVE-2020-1747",
        "GHSA-6757-jp84-gxfx"
       ],
       "modified": "2026-05-04T08:57:14.897560893Z",
       "published": "2020-03-24T15:15:00Z",
       "affected": [
        {
         "package": {
          "ecosystem": "PyPI",
          "name": "pyyaml",
          "purl": "pkg:pypi/pyyaml"
         },
         "ranges": [
          {
           "events": [
            {
             "introduced": "5.1"
            },
            {
             "fixed": "5.3.1"
            }
           ],
           "type": "ECOSYSTEM"
          }
         ]
        }
       ]
      },
      {
       "id": "PYSEC-2021-142",
       "aliases": [
        "CVE-2020-14343",
        "GHSA-8q59-q68h-6hv4"
       ],
       "modified": "2023-11-08T04:02:26.414885Z",
       "published": "2021-02-09T21:15:00Z",
       "affected": [
        {
         "package": {
          "ecosystem": "PyPI",
          "name": "pyyaml",
          "purl": "pkg:pypi/pyyaml"
         },
         "ranges": [
          {
           "events": [
            {
             "introduced": "0"
            },
            {
             "fixed": "5.4"
            }
           ],
           "type": "ECOSYSTEM"
          }
         ]
        }
       ]
      },
      {
       "id": "GHSA-6757-jp84-gxfx",
       "aliases": [
        "CVE-2020-1747",
        "PYSEC-2020-96"
       ],
       "modified": "2026-05-04T08:57:14.897560893Z",
       "published": "2021-04-20T16:14:24Z",
       "affected": [
        {
         "package": {
          "ecosystem": "PyPI",
          "name": "pyyaml",
          "purl": "pkg:pypi/pyyaml"
         },
         "ranges": [
          {
           "events": [
            {
             "introduced": "5.1b7"
            },
            {
             "fixed": "5.3.1"
            }
           ],
           "type": "ECOSYSTEM"
          }
         ]
        }
       ]
      },
      {
       "id": "GHSA-8q59-q68h-6hv4",
       "aliases": [
        "CVE-2020-14343",
        "PYSEC-2021-142"
       ],
       "modified": "2026-02-04T03:33:10.792778Z",
       "published": "2021-03-25T21:26:26Z",
       "affected": [
        {
         "package": {
          "ecosystem": "PyPI",
          "name": "pyyaml",
          "purl": "pkg:pypi/pyyaml"
         },
         "ranges": [
          {
           "events": [
            {
             "introduced": "0"
            },
            {
             "fixed": "5.4"
            }
           ],
           "type": "ECOSYSTEM"
          }
         ]
        }
       ]
      }
     ]
    }
   ]
  }
 ],
 "experimental_config": {
  "licenses": {
   "summary": false,
   "allowlist": null
  }
 }
}''')
OSV_LIMPIO = {"results": [], "experimental_config": {"licenses": {"summary": False, "allowlist": None}}}


@pytest.fixture
def vig():
    spec = importlib.util.spec_from_file_location("vigilancia", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ───────────── gh simulado: un ejecutable `gh` en el PATH con estado en un fichero ─────────────
FAKE_GH = r'''#!/usr/bin/env python3
import json, os, sys
estado_f = os.environ["FAKE_GH_STATE"]
est = json.load(open(estado_f))
args = sys.argv[1:]
cuerpo = sys.stdin.read() if "--body-file" in args else None
est["llamadas"].append({"args": args, "stdin": cuerpo})
def fin(rc=0, out=""):
    json.dump(est, open(estado_f, "w"))
    sys.stdout.write(out)
    sys.exit(rc)
if est.get("falla") == args[:2] or est.get("falla") == args[0]:
    sys.stderr.write("gh: simulated failure (HTTP 500)\n")
    fin(1)
if args[:2] == ["issue", "list"]:
    fin(0, json.dumps([{k: i[k] for k in ("number", "title", "body")} for i in est["issues"] if i["state"] == "open"]))
if args[:2] == ["label", "create"]:
    fin(0)
if args[:2] == ["issue", "create"]:
    n = max([i["number"] for i in est["issues"]] + [0]) + 1
    est["issues"].append({"number": n, "title": args[args.index("--title") + 1], "body": cuerpo, "state": "open",
                          "labels": [args[args.index("--label") + 1]]})
    fin(0, "https://github.com/x/y/issues/%d\n" % n)
if args[:2] == ["issue", "edit"]:
    for i in est["issues"]:
        if str(i["number"]) == args[2]:
            i["body"] = cuerpo
    fin(0)
if args[:2] == ["issue", "comment"]:
    for i in est["issues"]:
        if str(i["number"]) == args[2]:
            i.setdefault("comentarios", []).append(cuerpo)
    fin(0)
if args[:2] == ["issue", "close"]:
    for i in est["issues"]:
        if str(i["number"]) == args[2]:
            i["state"] = "closed"
            i["cierre"] = args[args.index("--comment") + 1] if "--comment" in args else None
    fin(0)
sys.stderr.write("fake gh: comando no previsto %r\n" % args)
fin(2)
'''

ESCRITURAS = (["issue", "create"], ["issue", "edit"], ["issue", "comment"], ["issue", "close"], ["label", "create"])


class Entorno:
    def __init__(self, tmp_path, monkeypatch, manifiestos=()):
        self.dir = tmp_path / "repo"
        self.dir.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.dir, check=True)
        for m in manifiestos:
            (self.dir / m).write_text("x\n")
        subprocess.run(["git", "add", "-A"], cwd=self.dir, check=True)
        bin_ = tmp_path / "bin"
        bin_.mkdir()
        gh = bin_ / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        self.estado = tmp_path / "estado.json"
        self.set_estado({"issues": [], "llamadas": []})
        self.env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "FAKE_GH_STATE": str(self.estado),
                    "PYTHONDONTWRITEBYTECODE": "1"}
        self.n = 0

    def set_estado(self, e):
        self.estado.write_text(json.dumps(e))

    def get_estado(self):
        return json.loads(self.estado.read_text())

    def issue_abierta(self, titulo=TITULO, body="viejo\n"):
        e = self.get_estado()
        n = max([i["number"] for i in e["issues"]] + [0]) + 1
        e["issues"].append({"number": n, "title": titulo, "body": body, "state": "open"})
        self.set_estado(e)
        return n

    def correr(self, code, osv=None, crudo=None):
        self.n += 1
        f = self.dir.parent / f"osv{self.n}.json"
        if crudo is not None:
            f.write_text(crudo)
        elif osv is not None:
            f.write_text(json.dumps(osv))
        else:
            f.write_text("")
        return subprocess.run([sys.executable, "-I", str(SCRIPT), "--code", str(code), "--json", str(f)],
                              cwd=self.dir, env=self.env, capture_output=True, text=True)

    def llamadas(self):
        return [c["args"] for c in self.get_estado()["llamadas"]]

    def escrituras(self):
        return [a for a in self.llamadas() if a[:2] in ESCRITURAS]


@pytest.fixture
def ent(tmp_path, monkeypatch):
    return Entorno(tmp_path, monkeypatch, manifiestos=("uv.lock",))


# ───────────── lectura del JSON de osv-scanner ─────────────
def test_hallazgos_reales_uno_por_grupo(vig):
    hs = vig.findings(OSV_HALLAZGOS)
    assert [(h["package"], h["version"], h["id"]) for h in hs] == [
        ("django", "1.11.0", "PYSEC-2017-44"), ("django", "1.11.0", "PYSEC-2018-2"),
        ("pyyaml", "5.3.0", "PYSEC-2020-96"), ("pyyaml", "5.3.0", "PYSEC-2021-142")]


def test_hallazgo_trae_version_corregida_medida(vig):
    h = {x["id"]: x for x in vig.findings(OSV_HALLAZGOS)}
    assert h["PYSEC-2017-44"]["fixed"] == ["1.10.8", "1.11.5"]
    assert h["PYSEC-2017-44"]["aliases"][0] == "CVE-2017-12794"


def test_sin_version_corregida_se_dice(vig):
    d = copy.deepcopy(OSV_HALLAZGOS)
    for p in d["results"][0]["packages"]:
        for v in p["vulnerabilities"]:
            for a in v["affected"]:
                for r in a["ranges"]:
                    r["events"] = [e for e in r["events"] if "fixed" not in e]
    assert all(h["fixed"] == [] for h in vig.findings(d))
    cuerpo = vig.render_body(vig.findings(d))
    assert "sin versión corregida" in cuerpo
    assert "1.11.5" not in cuerpo


def test_versiones_corregidas_mezcladas_no_rompen_la_ordenacion(vig):
    # Con el JSON completo medido (53 vulnerabilidades) la primera versión lanzó TypeError (int con str al ordenar).
    d = copy.deepcopy(OSV_HALLAZGOS)
    ev = d["results"][0]["packages"][0]["vulnerabilities"][0]["affected"][0]["ranges"][0]["events"]
    ev[:] = [{"introduced": "0"}, {"fixed": "1.11rc1"}, {"fixed": "2.0.0"}, {"fixed": "1.10.8"}, {"fixed": "2.0.0b1"}]
    h = {x["id"]: x for x in vig.findings(d)}["PYSEC-2017-44"]
    assert {"1.11rc1", "2.0.0", "1.10.8", "2.0.0b1"} <= set(h["fixed"])
    assert vig.classify(1, json.dumps(d))[0] == "findings"


def test_cuerpo_lista_paquete_version_id_y_corregida(vig):
    cuerpo = vig.render_body(vig.findings(OSV_HALLAZGOS))
    assert "| django | 1.11.0 | PYSEC-2017-44 (CVE-2017-12794) | 1.10.8, 1.11.5 |" in cuerpo
    assert "| pyyaml | 5.3.0 | PYSEC-2020-96" in cuerpo


def test_cuerpo_determinista_y_sin_orden_de_entrada(vig):
    d = copy.deepcopy(OSV_HALLAZGOS)
    d["results"][0]["packages"].reverse()
    assert vig.render_body(vig.findings(d)) == vig.render_body(vig.findings(OSV_HALLAZGOS))


def test_limpio_real_sin_hallazgos(vig):
    assert vig.findings(OSV_LIMPIO) == []


# ───────────── clasificación: código de salida + JSON ─────────────
def estado(vig, code, texto):
    return vig.classify(code, texto)[0]


def test_codigo_0_json_limpio(vig):
    assert estado(vig, 0, json.dumps(OSV_LIMPIO)) == "clean"


def test_codigo_1_con_hallazgos(vig):
    assert estado(vig, 1, json.dumps(OSV_HALLAZGOS)) == "findings"


def test_codigo_128_sin_paquetes_stdout_vacio(vig):
    assert estado(vig, 128, "") == "no_packages"


@pytest.mark.parametrize("code", [2, 3, 126, 127, 130, 137, 255, -1])
def test_otros_codigos_son_error_del_escaner(vig, code):
    assert estado(vig, code, json.dumps(OSV_LIMPIO)) == "error"
    assert estado(vig, code, "") == "error"


@pytest.mark.parametrize("texto", ["", "no es json", "{", '{"results": [', "[]", "null", '{"otra": 1}',
                                   '{"results": 5}', '{"results": [5]}'])
@pytest.mark.parametrize("code", [0, 1])
def test_json_ilegible_es_error_no_limpio(vig, code, texto):
    assert estado(vig, code, texto) == "error"


def test_codigo_0_con_hallazgos_es_incoherente(vig):
    assert estado(vig, 0, json.dumps(OSV_HALLAZGOS)) == "error"


def test_codigo_1_sin_hallazgos_es_incoherente(vig):
    assert estado(vig, 1, json.dumps(OSV_LIMPIO)) == "error"


# ───────────── el script completo con gh simulado ─────────────
def test_limpio_sin_issue_abierta_no_escribe(ent):
    r = ent.correr(0, OSV_LIMPIO)
    assert r.returncode == 0, r.stderr
    assert ent.escrituras() == []


def test_limpio_cierra_la_issue_abierta_con_comentario(ent):
    n = ent.issue_abierta()
    otra = ent.issue_abierta(titulo="[vigilancia] otra cosa")
    r = ent.correr(0, OSV_LIMPIO)
    assert r.returncode == 0, r.stderr
    e = ent.get_estado()
    por_n = {i["number"]: i for i in e["issues"]}
    assert por_n[n]["state"] == "closed" and por_n[n]["cierre"]
    assert por_n[otra]["state"] == "open"
    assert [a[:3] for a in ent.escrituras()] == [["issue", "close", str(n)]]


def test_limpio_no_cierra_issue_de_titulo_parecido(ent):
    ent.issue_abierta(titulo=TITULO + " y más")
    ent.issue_abierta(titulo=TITULO.upper())
    assert ent.correr(0, OSV_LIMPIO).returncode == 0
    assert ent.escrituras() == []


def test_hallazgos_crean_issue_con_etiqueta_y_salen_en_rojo(ent):
    r = ent.correr(1, OSV_HALLAZGOS)
    assert r.returncode == 1, r.stderr
    e = ent.get_estado()
    assert len(e["issues"]) == 1
    i = e["issues"][0]
    assert i["title"] == TITULO and i["labels"] == ["security"]
    assert "PYSEC-2017-44" in i["body"] and "django" in i["body"] and "1.11.5" in i["body"]
    crea = [a for a in ent.llamadas() if a[:2] == ["issue", "create"]]
    assert len(crea) == 1 and "--label" in crea[0]


def test_hallazgos_busca_la_abierta_antes_de_crear(ent):
    ent.correr(1, OSV_HALLAZGOS)
    ll = ent.llamadas()
    i_list = next(k for k, a in enumerate(ll) if a[:2] == ["issue", "list"])
    i_create = next(k for k, a in enumerate(ll) if a[:2] == ["issue", "create"])
    assert i_list < i_create
    assert "open" in ll[i_list]


def test_hallazgos_dos_veces_no_duplica(ent):
    assert ent.correr(1, OSV_HALLAZGOS).returncode == 1
    assert ent.correr(1, OSV_HALLAZGOS).returncode == 1
    e = ent.get_estado()
    assert len([i for i in e["issues"] if i["title"] == TITULO]) == 1
    assert len([a for a in ent.llamadas() if a[:2] == ["issue", "create"]]) == 1


def test_hallazgos_sin_cambios_no_comenta(ent):
    ent.correr(1, OSV_HALLAZGOS)
    ent.correr(1, OSV_HALLAZGOS)
    assert [a for a in ent.llamadas() if a[:2] in (["issue", "comment"], ["issue", "edit"])] == []


def test_hallazgos_distintos_comentan_y_actualizan_la_abierta(ent):
    ent.correr(1, OSV_HALLAZGOS)
    menos = copy.deepcopy(OSV_HALLAZGOS)
    menos["results"][0]["packages"] = menos["results"][0]["packages"][:1]
    r = ent.correr(1, menos)
    assert r.returncode == 1, r.stderr
    e = ent.get_estado()
    assert len(e["issues"]) == 1
    i = e["issues"][0]
    assert len(i["comentarios"]) == 1 and "pyyaml" not in i["body"]
    assert "django" in i["comentarios"][0]
    assert len([a for a in ent.llamadas() if a[:2] == ["issue", "create"]]) == 1


def test_hallazgos_con_issue_cerrada_crea_nueva(ent):
    e = ent.get_estado()
    e["issues"].append({"number": 1, "title": TITULO, "body": "x", "state": "closed"})
    ent.set_estado(e)
    assert ent.correr(1, OSV_HALLAZGOS).returncode == 1
    assert len(ent.get_estado()["issues"]) == 2


@pytest.mark.parametrize("code,crudo", [(2, None), (127, None), (137, None), (130, None),
                                         (0, "no es json"), (1, "{"), (0, ""), (1, "")])
def test_error_del_escaner_rojo_y_no_toca_issues(ent, code, crudo):
    ent.issue_abierta()
    r = ent.correr(code, OSV_LIMPIO if crudo is None else None, crudo=crudo)
    assert r.returncode not in (0, 1), r.stdout
    assert ent.escrituras() == []
    assert ent.get_estado()["issues"][0]["state"] == "open"


def test_error_del_escaner_no_crea_issue(ent):
    assert ent.correr(127).returncode == 2
    assert ent.escrituras() == []


def test_hallazgos_y_codigo_distinto_de_1_no_crea(ent):
    assert ent.correr(2, OSV_HALLAZGOS).returncode == 2
    assert ent.escrituras() == []


def test_codigo_128_sin_manifiesto_es_verde_y_no_toca(tmp_path, monkeypatch):
    e = Entorno(tmp_path, monkeypatch, manifiestos=("README.md",))
    e.issue_abierta()
    r = e.correr(128)
    assert r.returncode == 0, r.stderr
    assert e.escrituras() == []


@pytest.mark.parametrize("manifiesto", ["pyproject.toml", "package.json", "go.mod", "Cargo.toml",
                                         "sub/dir/package.json"])
def test_codigo_128_con_manifiesto_sin_lockfile_rojo(tmp_path, monkeypatch, manifiesto):
    e = Entorno(tmp_path, monkeypatch)
    p = e.dir / manifiesto
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x\n")
    subprocess.run(["git", "add", "-A"], cwd=e.dir, check=True)
    e.issue_abierta()
    r = e.correr(128)
    assert r.returncode == 3, r.stdout + r.stderr
    assert "lockfile" in r.stdout + r.stderr
    assert e.escrituras() == []


def test_manifiesto_no_versionado_no_cuenta(tmp_path, monkeypatch):
    e = Entorno(tmp_path, monkeypatch)
    (e.dir / "pyproject.toml").write_text("x\n")  # sin git add
    assert e.correr(128).returncode == 0


def test_gh_list_falla_con_hallazgos_rojo_y_no_crea(ent):
    s = ent.get_estado()
    s["falla"] = ["issue", "list"]
    ent.set_estado(s)
    r = ent.correr(1, OSV_HALLAZGOS)
    assert r.returncode == 2
    assert ent.escrituras() == []


def test_gh_list_falla_sin_hallazgos_rojo(ent):
    s = ent.get_estado()
    s["falla"] = ["issue", "list"]
    ent.set_estado(s)
    assert ent.correr(0, OSV_LIMPIO).returncode == 2


def test_gh_create_falla_rojo(ent):
    s = ent.get_estado()
    s["falla"] = ["issue", "create"]
    ent.set_estado(s)
    assert ent.correr(1, OSV_HALLAZGOS).returncode == 2


def test_gh_close_falla_rojo(ent):
    ent.issue_abierta()
    s = ent.get_estado()
    s["falla"] = ["issue", "close"]
    ent.set_estado(s)
    assert ent.correr(0, OSV_LIMPIO).returncode == 2


def test_gh_list_devuelve_json_ilegible_rojo(ent, tmp_path):
    bin_ = tmp_path / "bin2"
    bin_.mkdir()
    gh = bin_ / "gh"
    gh.write_text("#!/bin/sh\necho 'no es json'\n")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    ent.env["PATH"] = f"{bin_}:{ent.env['PATH']}"
    assert ent.correr(1, OSV_HALLAZGOS).returncode == 2


def test_cuerpo_va_por_stdin_no_por_argumento(ent):
    ent.correr(1, OSV_HALLAZGOS)
    crea = next(c for c in ent.get_estado()["llamadas"] if c["args"][:2] == ["issue", "create"])
    assert "PYSEC-2017-44" in crea["stdin"]
    assert not any("PYSEC" in a for a in crea["args"])


# ───────────── el workflow ─────────────
@pytest.fixture(scope="module")
def wf():
    return yaml.safe_load(WORKFLOW.read_text())


def osv_image(path):
    m = re.search(r"^\s*OSV_IMAGE:\s*(\S+)\s*$", path.read_text(), re.M)
    assert m, f"sin OSV_IMAGE en {path}"
    return m.group(1)


def test_misma_imagen_osv_que_ci():
    assert osv_image(WORKFLOW) == osv_image(CI)


def test_imagen_osv_con_version_y_digest():
    assert re.fullmatch(r"ghcr\.io/google/osv-scanner:v\d+\.\d+\.\d+@sha256:[0-9a-f]{64}", osv_image(WORKFLOW))


def test_disparadores_programado_diario_y_manual(wf):
    on = wf.get("on", wf.get(True))
    assert "workflow_dispatch" in on
    crons = [s["cron"] for s in on["schedule"]]
    assert len(crons) == 1 and re.fullmatch(r"\d+ \d+ \* \* \*", crons[0])
    assert "pull_request" not in on and "pull_request_target" not in on and "push" not in on


def test_permisos_minimos(wf):
    assert wf["permissions"] == {"contents": "read"}
    for job in wf["jobs"].values():
        assert job["permissions"] == {"contents": "read", "issues": "write"}


def test_actions_fijadas_por_sha():
    usos = re.findall(r"^\s*-?\s*uses:\s*(\S+)", WORKFLOW.read_text(), re.M)
    assert usos
    for u in usos:
        assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", u), u


def test_checkout_sin_credenciales_persistentes():
    assert "persist-credentials: false" in WORKFLOW.read_text()


def test_run_no_interpola_expresiones():
    for job in yaml.safe_load(WORKFLOW.read_text())["jobs"].values():
        for paso in job["steps"]:
            assert "${{" not in paso.get("run", ""), paso


def test_workflow_escanea_la_rama_principal_y_llama_al_script(wf):
    txt = WORKFLOW.read_text()
    assert "scripts/vigilancia.py" in txt
    assert "scan source -r" in txt and "--format json" in txt
    assert "ref: main" in txt or "ref: ${{ github.event.repository.default_branch }}" in txt


def test_workflow_no_traga_el_codigo_del_escaner():
    run = "\n".join(p.get("run", "") for j in yaml.safe_load(WORKFLOW.read_text())["jobs"].values()
                    for p in j["steps"])
    assert "|| true" not in run and "continue-on-error" not in WORKFLOW.read_text()
    assert re.search(r"code=\$\?", run) or "|| code=$?" in run


def test_workflow_gh_usa_token_por_entorno(wf):
    txt = WORKFLOW.read_text()
    assert "GH_TOKEN: ${{ github.token }}" in txt or "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in txt
