"""vigilancia.py y vigilancia.yml (SMC-009, T52).

Fixtures medidos el 2026-11-07 con la imagen fijada en ci.yml (osv-scanner v2.7.0, `scan source -r --format json`):
  - este repo (uv.lock, 11 paquetes): código 0, JSON con `results: []`.
  - carpeta temporal con requirements.txt `django==1.11.0` y `pyyaml==5.3`: código 1, 552 KB de JSON
    (django 49 vulnerabilidades en 30 grupos, pyyaml 4 en 2 grupos); aquí recortado a 2 grupos por paquete,
    sin `details`, `references` ni `versions`. Todas las vulnerabilidades medidas traían versión corregida.
  - carpeta vacía y carpeta con solo pyproject.toml: código 128, stdout vacío, stderr «No package sources found».
  - ruta inexistente u opción desconocida: código 127, stdout vacío.
T54, medido con `gh` real (solo GET) el 2026-11-07:
  - `gh issue list --json number,title,body,author,labels` en este repo: `author` = {"id","is_bot":false,"login":
    "pedri77","name"}; `labels` = [{"id","name","description","color"}].
  - issue creada por `github-actions[bot]` (repo público happyhappy82/github-trending-notion #1465): `author` =
    {"is_bot":true,"login":"app/github-actions"} (sin `id` ni `name`, y el login NO es `github-actions[bot]`, que es la
    forma de `gh search issues`); `labels` con la misma forma de objetos.
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
BOT = {"is_bot": True, "login": "app/github-actions"}
HUMANO = {"id": "MDQ6VXNlcjEyOTg5Njk0", "is_bot": False, "login": "pedri77", "name": "pedri77"}

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
BOT = {"is_bot": True, "login": "app/github-actions"}
cuerpo = sys.stdin.read() if "--body-file" in args else None
est["llamadas"].append({"args": args, "stdin": cuerpo})
def fin(rc=0, out=""):
    json.dump(est, open(estado_f, "w"))
    sys.stdout.write(out)
    sys.exit(rc)
if est.get("falla") == args[:2] or est.get("falla") == args[0]:
    sys.stderr.write(est.get("stderr") or "gh: simulated failure (HTTP 500)\n")
    fin(1)
if args[:2] == ["issue", "list"]:
    # Misma forma que `gh issue list --json number,title,body,author,labels` medida con gh real.
    fin(0, json.dumps([{"number": i["number"], "title": i["title"], "body": i["body"],
                        "author": i.get("author", BOT),
                        "labels": [{"id": "LA_x", "name": n, "description": "", "color": "D93F0B"}
                                   for n in i.get("labels", ["security"])]}
                       for i in est["issues"] if i["state"] == "open"]))
if args[:2] == ["label", "create"]:
    if est.get("etiqueta_existe") and "--force" not in args:
        # texto real de gh 2.89.0 (pkg/cmd/label/create.go), tras un 422 already_exists
        sys.stderr.write('label with name "%s" already exists; use `--force` to update its color and description\n' % args[2])
        fin(1)
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

    def issue_abierta(self, titulo=TITULO, body="viejo\n", autor=BOT, etiquetas=("security",)):
        e = self.get_estado()
        n = max([i["number"] for i in e["issues"]] + [0]) + 1
        e["issues"].append({"number": n, "title": titulo, "body": body, "state": "open", "author": autor,
                            "labels": list(etiquetas)})
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
    assert "| `django` | `1.11.0` | `PYSEC-2017-44` (`CVE-2017-12794`) | `1.10.8`, `1.11.5` |" in cuerpo
    assert "| `pyyaml` | `5.3.0` | `PYSEC-2020-96`" in cuerpo


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


# ───────────── T54 · N2: solo se adopta la issue del bot con la etiqueta ─────────────
def test_issue_pide_autor_y_etiquetas_a_gh(ent):
    ent.correr(1, OSV_HALLAZGOS)
    lista = next(a for a in ent.llamadas() if a[:2] == ["issue", "list"])
    campos = lista[lista.index("--json") + 1].split(",")
    assert {"number", "title", "body", "author", "labels"} <= set(campos)


def test_issue_ajena_con_el_mismo_titulo_no_se_adopta_ni_se_toca(ent):
    ajena = ent.issue_abierta(autor=HUMANO, body="la abrió un humano\n")
    r = ent.correr(1, OSV_HALLAZGOS)
    assert r.returncode == 1, r.stderr
    e = ent.get_estado()
    por_n = {i["number"]: i for i in e["issues"]}
    assert por_n[ajena]["body"] == "la abrió un humano\n" and "comentarios" not in por_n[ajena]
    assert len(e["issues"]) == 2 and any(a[:2] == ["issue", "create"] for a in ent.llamadas())


def test_issue_ajena_no_se_cierra_cuando_no_hay_hallazgos(ent):
    ent.issue_abierta(autor=HUMANO)
    assert ent.correr(0, OSV_LIMPIO).returncode == 0
    assert ent.escrituras() == []


def test_issue_del_bot_sin_etiqueta_security_no_se_adopta(ent):
    sin = ent.issue_abierta(etiquetas=())
    otra = ent.issue_abierta(etiquetas=("bug",), titulo=TITULO)
    assert ent.correr(1, OSV_HALLAZGOS).returncode == 1
    e = ent.get_estado()
    assert {i["number"]: i["body"] for i in e["issues"]}[sin] == "viejo\n"
    assert {i["number"]: i["body"] for i in e["issues"]}[otra] == "viejo\n"
    assert len(e["issues"]) == 3


def test_humano_con_etiqueta_security_y_mismo_titulo_no_se_adopta(ent):
    ent.issue_abierta(autor=HUMANO, etiquetas=("security",))
    assert ent.correr(0, OSV_LIMPIO).returncode == 0
    assert ent.escrituras() == []


@pytest.mark.parametrize("autor", [
    {"is_bot": False, "login": "app/github-actions"},   # un humano no puede llamarse así, pero is_bot lo dice
    {"is_bot": True, "login": "app/dependabot"},
    {"is_bot": True, "login": "github-actions[bot]"},    # forma de `gh search`, no de `gh issue list`
    {"is_bot": False, "login": "github-actions"},
    {},
])
def test_solo_el_bot_de_actions_medido_cuenta(ent, autor):
    ent.issue_abierta(autor=autor)
    assert ent.correr(0, OSV_LIMPIO).returncode == 0
    assert ent.escrituras() == []


def test_con_ajena_anterior_se_adopta_la_del_bot(ent):
    ajena = ent.issue_abierta(autor=HUMANO)
    propia = ent.issue_abierta()
    assert ent.correr(1, OSV_HALLAZGOS).returncode == 1
    e = ent.get_estado()
    por_n = {i["number"]: i for i in e["issues"]}
    assert por_n[ajena]["body"] == "viejo\n" and "comentarios" not in por_n[ajena]
    assert "django" in por_n[propia]["body"] and len(e["issues"]) == 2
    assert [a[:3] for a in ent.escrituras()] == [["issue", "comment", str(propia)], ["issue", "edit", str(propia)]]


def test_la_issue_propia_se_adopta_en_la_forma_real_de_gh(ent):
    n = ent.issue_abierta()
    assert ent.correr(0, OSV_LIMPIO).returncode == 0
    assert ent.get_estado()["issues"][0]["state"] == "closed" and n == 1


def test_gh_list_sin_author_o_labels_es_error_de_gh(ent):
    # Si gh cambiara la forma, mejor rojo que adoptar a ciegas.
    bin_ = ent.dir.parent / "bin" / "gh"
    bin_.write_text("#!/bin/sh\necho '[{\"number\":1,\"title\":\"%s\",\"body\":\"\"}]'\n" % TITULO)
    assert ent.correr(1, OSV_HALLAZGOS).returncode == 2


# ───────────── T54 · N3: contenido de terceros en una issue pública ─────────────
HOSTILES = {
    "mencion": "@org/team",
    "salto_solo": "a\nb",
    "salto_final": "abc\n",
    "barra": "a|b",
    "salto": "x\n| inyectada | fila | de | tabla |",
    "imagen": "![x](https://evil.example/p.png)",
    "comentario": "<!-- oculto -->",
    "enlace": "[clic](https://evil.example)",
    "url": "https://evil.example/x",
    "html": "<img src=x onerror=1>",
    "issue": "#1234",
    "cr": "a\rb",
    "ceros": "a\u200bb",
    "unicode": "pаypal",          # 'а' cirílica
    "largo": "a" * 300,
    "vacio": "",
    "espacio": "a b",
    "tick": "a`b",
    "cancel": "a\u202eb",
}


def hallazgo(**kw):
    h = {"package": "django", "version": "1.11.0", "ecosystem": "PyPI", "id": "PYSEC-2017-44",
         "aliases": ["CVE-2017-12794"], "fixed": ["1.11.5"]}
    h.update(kw)
    return h


def filas(cuerpo):
    return [l for l in cuerpo.split("\n") if l.startswith("|")]


def fuera_de_codigo(cuerpo):
    return re.sub(r"`[^`\n]*`", "", cuerpo)


@pytest.mark.parametrize("campo", ["package", "version", "id"])
@pytest.mark.parametrize("clave", sorted(HOSTILES))
def test_campo_hostil_no_llega_literal_ni_rompe_la_tabla(vig, campo, clave):
    valor = HOSTILES[clave]
    cuerpo = vig.render_body([hallazgo(**{campo: valor})])
    assert len(filas(cuerpo)) == 3 and all(f.count("|") == 5 for f in filas(cuerpo)), cuerpo
    if valor and not (campo == "package" and clave == "mencion"):    # `@org/team` es un nombre npm válido: va en código
        assert valor not in cuerpo
    plano = fuera_de_codigo(cuerpo)
    assert "@" not in plano and "<!--" not in cuerpo and "![" not in cuerpo and "](" not in cuerpo
    assert "://" not in cuerpo and "<img" not in cuerpo and "#1234" not in cuerpo
    assert "\r" not in cuerpo and "\u200b" not in cuerpo and "\u202e" not in cuerpo


@pytest.mark.parametrize("clave", sorted(HOSTILES))
def test_version_corregida_hostil_no_llega_literal(vig, clave):
    valor = HOSTILES[clave]
    cuerpo = vig.render_body([hallazgo(fixed=["1.0.0", valor])])
    assert len(filas(cuerpo)) == 3 and all(f.count("|") == 5 for f in filas(cuerpo)), cuerpo
    if valor:
        assert valor not in cuerpo
    assert "@" not in fuera_de_codigo(cuerpo) and "<!--" not in cuerpo and "![" not in cuerpo


@pytest.mark.parametrize("clave", sorted(set(HOSTILES) - {"vacio"}))
def test_alias_cve_hostil_no_llega_literal(vig, clave):
    valor = "CVE-" + HOSTILES[clave]
    cuerpo = vig.render_body([hallazgo(aliases=[valor])])
    assert len(filas(cuerpo)) == 3 and all(f.count("|") == 5 for f in filas(cuerpo)), cuerpo
    assert valor not in cuerpo and "@" not in fuera_de_codigo(cuerpo) and "<!--" not in cuerpo


@pytest.mark.parametrize("valor", [5, None, ["a"], {"a": 1}, 1.5])
def test_campos_que_no_son_texto_se_sustituyen(vig, valor):
    cuerpo = vig.render_body([hallazgo(package=valor, version=valor)])
    assert len(filas(cuerpo)) == 3 and "None" not in cuerpo and "{" not in cuerpo


def test_valor_no_valido_se_sustituye_por_marca_fija(vig):
    cuerpo = vig.render_body([hallazgo(package="a|b")])
    assert f"| {vig.INVALID} | `1.11.0` |" in cuerpo
    assert not set(vig.INVALID) & set("@|<>!#`:/\n&")


def test_mencion_de_npm_se_neutraliza_en_codigo_no_se_borra(vig):
    cuerpo = vig.render_body([hallazgo(package="@org/team", id="GHSA-xxxx-yyyy-zzzz")])
    assert "| `@org/team` | `1.11.0` |" in cuerpo
    assert "@" not in fuera_de_codigo(cuerpo)


@pytest.mark.parametrize("nombre", ["@scope/paquete", "@babel/core", "lodash", "github.com/gorilla/mux",
                                    "org.apache.logging.log4j:log4j-core", "serde_json", "Django", "zope.interface",
                                    "golang.org/x/crypto", "libssl1.1", "a", "pkg~beta"])
def test_nombres_legitimos_de_paquete_pasan(vig, nombre):
    cuerpo = vig.render_body([hallazgo(package=nombre)])
    assert f"| `{nombre}` | `1.11.0` |" in cuerpo
    assert "@" not in fuera_de_codigo(cuerpo)


@pytest.mark.parametrize("ident", ["GHSA-9r8w-6x8c-6jr9", "PYSEC-2017-44", "CVE-2017-12794", "GO-2024-0001",
                                   "RUSTSEC-2023-0001", "OSV-2020-1", "MAL-2024-1234", "DSA-5000-1",
                                   "UBUNTU-CVE-2024-1234", "ALPINE-CVE-2024-1"])
def test_identificadores_legitimos_pasan(vig, ident):
    assert f"| `{ident}` |" in vig.render_body([hallazgo(id=ident, aliases=[])])


@pytest.mark.parametrize("version", ["1.11.0", "5.3.0", "2.0.0b1", "1.11rc1", "1.2.3+build.5", "1.0.0-rc.1+meta",
                                     "v0.0.0-20200101000000-abcdef123456", "v2.0.0+incompatible", "1:2.3-4~bpo11+1",
                                     "2024.1", "0"])
def test_versiones_legitimas_pasan_incluido_el_mas(vig, version):
    cuerpo = vig.render_body([hallazgo(version=version, fixed=[version])])
    assert f"| `{version}` | `PYSEC-2017-44` (`CVE-2017-12794`) | `{version}` |" in cuerpo


def test_fixtures_reales_se_renderizan_igual_que_antes(vig):
    cuerpo = vig.render_body(vig.findings(OSV_HALLAZGOS))
    assert "| `django` | `1.11.0` | `PYSEC-2018-2` (`CVE-2018-14574`) | `1.11.15`, `2.0.8` |" in cuerpo


def test_longitud_maxima_de_la_lista_blanca(vig):
    assert f"| `{'a' * 100}` |" in vig.render_body([hallazgo(package="a" * 100)])
    assert f"| {vig.INVALID} |" in vig.render_body([hallazgo(package="a" * 101)])
    assert f"| `{'1' * 64}` |" in vig.render_body([hallazgo(version="1" * 64)])
    assert f"| {vig.INVALID} |" in vig.render_body([hallazgo(version="1" * 65)])


def test_json_hostil_de_punta_a_punta_issue_creada_limpia(ent):
    d = copy.deepcopy(OSV_HALLAZGOS)
    p = d["results"][0]["packages"][0]["package"]
    p["name"] = "@org/team"
    p["version"] = "1.0|![x](https://evil.example/p.png)"
    d["results"][0]["packages"][0]["groups"][0]["ids"][0] = "<!-- x -->\nGHSA-fake"
    r = ent.correr(1, d)
    assert r.returncode == 1, r.stderr
    body = ent.get_estado()["issues"][0]["body"]
    assert "`@org/team`" in body and "evil.example" not in body and "<!--" not in body
    assert "@" not in fuera_de_codigo(body)


# ───────────── T54 · N10: concurrencia y plazo ─────────────
def test_concurrency_sin_cancelar_la_que_corre(wf):
    c = wf["concurrency"]
    assert isinstance(c, dict) and c["group"] and c["cancel-in-progress"] is False


def test_timeout_en_cada_job(wf):
    for nombre, job in wf["jobs"].items():
        t = job.get("timeout-minutes")
        assert isinstance(t, int) and 1 <= t <= 30, nombre


# ───────────── T54 vuelta · todo campo de terceros va entero en código en línea; tope del cuerpo ─────────────
EXTRA = {"www": "www.evil.com/login", "gh": "GH-12", "tachado": "a~~b~~c", "correo": "x@evil.com",
         "negrita": "a__b__c", "ruta": "evil.com/login"}


def celdas(fila):
    return [c.strip() for c in fila.strip().strip("|").split("|")]


def sin_codigo(cuerpo):
    return re.sub(r"`[^`\n]+`", "", cuerpo)


@pytest.mark.parametrize("campo", ["package", "version", "id", "fixed", "alias"])
@pytest.mark.parametrize("clave", sorted(EXTRA))
def test_campo_valido_pero_peligroso_va_entero_en_codigo_en_linea(vig, campo, clave):
    v = EXTRA[clave]
    if campo == "package":
        h = hallazgo(package=v)
    elif campo == "version":
        h = hallazgo(version=v)
    elif campo == "id":
        h = hallazgo(id=v)
    elif campo == "fixed":
        h = hallazgo(fixed=[v])
    else:
        h = hallazgo(aliases=["CVE-" + v])
    fila = filas(vig.render_body([h]))[2]
    resto = sin_codigo(fila)
    # Fuera del código en línea no queda ni rastro del valor: ni www., ni GH-, ni ~~, ni @ de correo.
    for peligro in ("www.", "GH-", "~~", "@", "__", "evil", "login"):
        assert peligro not in resto, (peligro, fila)
    mostrado = "CVE-" + v if campo == "alias" else v
    if campo == "alias":                       # un alias que no cumple la lista blanca se omite
        assert "CVE-" + v not in resto
    elif "@" not in v or campo == "package":       # el valor, si se muestra, va en bloque completo
        assert f"`{mostrado}`" in fila or vig.INVALID in fila, fila


def test_www_evil_com_login_en_el_paquete_se_muestra_como_codigo(vig):
    fila = filas(vig.render_body([hallazgo(package="www.evil.com/login")]))[2]
    assert fila.startswith("| `www.evil.com/login` |")


def test_cada_celda_de_datos_es_un_codigo_en_linea_o_la_marca(vig):
    cuerpo = vig.render_body(vig.findings(OSV_HALLAZGOS))
    for f in filas(cuerpo)[2:]:
        c = celdas(f)
        assert len(c) == 4
        for celda in c[:3]:
            assert re.fullmatch(r"`[^`]+`( \(`[^`]+`\))?", celda), celda
        assert all(re.fullmatch(r"`[^`]+`", x) for x in c[3].split(", ")) or c[3] == "sin versión corregida"


def test_la_lista_blanca_sigue_sin_comilla_invertida_ni_barra(vig):
    for rx in (vig.NAME_RE, vig.VERSION_RE, vig.ID_RE):
        assert not rx.fullmatch("a`b") and not rx.fullmatch("a|b") and not rx.fullmatch("a\nb")


def enorme(n, fixed=1):
    return [hallazgo(package=f"paquete-{i:06d}", version="1.0.%d" % i, id=f"GHSA-{i:04d}-aaaa-bbbb",
                     aliases=[f"CVE-2024-{i:05d}"], fixed=["2.0.%d" % k for k in range(fixed)]) for i in range(n)]


def test_cuerpo_enorme_se_recorta_bajo_el_limite_de_github_y_lo_dice(vig):
    cuerpo = vig.render_body(enorme(3000))
    assert len(cuerpo) < 65536 and len(cuerpo) <= vig.MAX_BODY
    assert "Lista recortada" in cuerpo
    m = re.search(r"se muestran (\d+) de 3000 hallazgos", cuerpo)
    assert m and int(m.group(1)) == len(filas(cuerpo)) - 2 and 0 < int(m.group(1)) < 3000
    assert "3000 vulnerabilidades" in cuerpo


def test_cuerpo_que_cabe_no_se_recorta(vig):
    cuerpo = vig.render_body(enorme(50))
    assert "Lista recortada" not in cuerpo and len(filas(cuerpo)) == 52


def test_una_fila_con_miles_de_versiones_corregidas_tambien_se_acota(vig):
    cuerpo = vig.render_body([hallazgo(fixed=["1.%d" % i for i in range(5000)])])
    assert len(cuerpo) < 5000 and "más" in cuerpo


def test_cuerpo_enorme_de_punta_a_punta_issue_bajo_limite_y_en_rojo(ent):
    d = copy.deepcopy(OSV_HALLAZGOS)
    base = d["results"][0]["packages"][0]
    base["groups"] = [{"ids": [f"GHSA-{i:04d}-aaaa-bbbb"], "aliases": []} for i in range(3000)]
    base["vulnerabilities"] = [{"id": f"GHSA-{i:04d}-aaaa-bbbb"} for i in range(3000)]
    d["results"][0]["packages"] = [base]
    r = ent.correr(1, d)
    assert r.returncode == 1, r.stderr
    body = ent.get_estado()["issues"][0]["body"]
    assert len(body) < 65536 and "Lista recortada" in body


def test_comentario_de_actualizacion_tambien_cabe(ent):
    ent.correr(1, OSV_HALLAZGOS)
    d = copy.deepcopy(OSV_HALLAZGOS)
    base = d["results"][0]["packages"][0]
    base["groups"] = [{"ids": [f"GHSA-{i:04d}-aaaa-bbbb"], "aliases": []} for i in range(3000)]
    base["vulnerabilities"] = [{"id": f"GHSA-{i:04d}-aaaa-bbbb"} for i in range(3000)]
    assert ent.correr(1, d).returncode == 1
    i = ent.get_estado()["issues"][0]
    assert len(i["comentarios"][0]) < 65536 and len(i["body"]) < 65536


# ───────────── T54 tercera vuelta · lo recortado queda en un artefacto, no en el log ─────────────
def paso_artefacto(wf):
    pasos = [p for j in wf["jobs"].values() for p in j["steps"] if "upload-artifact" in p.get("uses", "")]
    assert len(pasos) == 1, "debe haber un único paso upload-artifact"
    return pasos[0]


def test_workflow_sube_el_json_del_escaner_como_artefacto(wf, vig):
    p = paso_artefacto(wf)
    assert p["uses"] == "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
    assert p["with"]["name"] == vig.ARTIFACT == "osv-vigilancia"
    assert p["with"]["path"] == "${{ runner.temp }}/osv.json"
    assert p["with"]["retention-days"] == 90


def test_artefacto_se_sube_tambien_con_el_job_en_rojo(wf):
    assert str(paso_artefacto(wf)["if"]).replace(" ", "") == "always()"


def test_artefacto_no_falla_si_el_escaner_no_escribio_el_fichero(wf):
    assert paso_artefacto(wf)["with"]["if-no-files-found"] == "ignore"


def test_mismo_sha_de_upload_artifact_que_pr_meta():
    sha = lambda f: re.search(r"actions/upload-artifact@([0-9a-f]{40})", f.read_text()).group(1)
    assert sha(WORKFLOW) == sha(RAIZ / ".github/workflows/pr-meta.yml")


def test_el_artefacto_es_el_ultimo_paso_y_el_script_no_imprime_hallazgos(wf, vig, ent):
    pasos = next(iter(wf["jobs"].values()))["steps"]
    assert "upload-artifact" in pasos[-1]["uses"]
    r = ent.correr(1, OSV_HALLAZGOS)
    assert "PYSEC" not in r.stdout + r.stderr and "django" not in r.stdout + r.stderr


def test_aviso_de_recorte_nombra_el_artefacto_y_no_el_log(vig):
    cuerpo = vig.render_body(enorme(3000))
    aviso = cuerpo[cuerpo.index("Lista recortada"):].split("\n")[0]
    assert f"`{vig.ARTIFACT}`" in aviso and "artefacto" in aviso
    assert "salida del job" not in cuerpo and "log" not in aviso.lower().replace("catalog", "")


# ───────────── T55 · N15: los errores de gh no pueden formar comandos de workflow ─────────────
INYECCION = "falló\n::error::inyectado\r::set-output name=x::y\n::warning::otro"


def _lineas_de_comando(r):
    return [l for l in (r.stdout + r.stderr).splitlines() if l.lstrip().startswith("::")]


def test_n15_el_stderr_de_gh_con_saltos_no_forma_lineas_de_comando(ent):
    s = ent.get_estado()
    s["falla"], s["stderr"] = ["issue", "list"], INYECCION
    ent.set_estado(s)
    r = ent.correr(1, OSV_HALLAZGOS)
    assert r.returncode == 2
    assert len(_lineas_de_comando(r)) == 1 and _lineas_de_comando(r)[0].startswith("::error::")
    assert "inyectado" in r.stdout and "\r" not in r.stdout


@pytest.mark.parametrize("sep", ["\n", "\r", "\r\n", "\u2028", "\x1b", "\x00"])
def test_n15_cualquier_separador_o_control_se_aplana(ent, sep):
    s = ent.get_estado()
    s["falla"], s["stderr"] = ["issue", "list"], f"a{sep}::error::b"
    ent.set_estado(s)
    r = ent.correr(1, OSV_HALLAZGOS)
    assert len(_lineas_de_comando(r)) == 1
    assert len(r.stdout.strip().splitlines()) == 1


def test_n15_la_ruta_ilegible_del_json_con_saltos_no_forma_lineas_de_comando(ent):
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--code", "1", "--json", str(ent.dir / "no\n::error::falso\nexiste.json")],
                       cwd=ent.dir, env=ent.env, capture_output=True, text=True)
    assert r.returncode == 2 and len(_lineas_de_comando(r)) == 1 and len(r.stdout.strip().splitlines()) == 1


def test_n15_flat_deja_el_texto_normal_igual(vig):
    assert vig.flat("gh issue list falló (1): gh: Not Found (HTTP 404)") == "gh issue list falló (1): gh: Not Found (HTTP 404)"
    assert "\n" not in vig.flat("a\nb\r\nc") and vig.flat("a\nb") == "a b"


# ───────────── T55 · N16: sin `--force` en `gh label create`, y tolera que la etiqueta exista ─────────────
def test_n16_label_create_no_lleva_force(ent):
    assert ent.correr(1, OSV_HALLAZGOS).returncode == 1
    crea = [a for a in ent.llamadas() if a[:2] == ["label", "create"]]
    assert len(crea) == 1 and "--force" not in crea[0] and "-f" not in crea[0] and "security" in crea[0]
    assert "--force" not in SCRIPT.read_text(encoding="utf-8").replace("`--force`", "")


def test_n16_si_la_etiqueta_ya_existe_se_sigue_y_se_crea_la_issue(ent):
    s = ent.get_estado()
    s["etiqueta_existe"] = True
    ent.set_estado(s)
    r = ent.correr(1, OSV_HALLAZGOS)
    assert r.returncode == 1 and "issue creada" in r.stdout
    e = ent.get_estado()
    assert len(e["issues"]) == 1 and e["issues"][0]["labels"] == ["security"]
    assert [a[:2] for a in ent.llamadas()].count(["issue", "create"]) == 1


def test_n16_otro_fallo_de_label_create_sigue_siendo_rojo_y_no_crea_issue(ent):
    s = ent.get_estado()
    s["falla"], s["stderr"] = ["label", "create"], "gh: Forbidden (HTTP 403)\n"
    ent.set_estado(s)
    r = ent.correr(1, OSV_HALLAZGOS)
    assert r.returncode == 2 and ent.get_estado()["issues"] == []


def test_n16_un_texto_que_solo_cita_already_exists_en_otro_fallo_no_se_traga(ent):
    s = ent.get_estado()
    s["falla"], s["stderr"] = ["label", "create"], "gh: algo falló (HTTP 500) already exists\n"
    ent.set_estado(s)
    assert ent.correr(1, OSV_HALLAZGOS).returncode == 2
