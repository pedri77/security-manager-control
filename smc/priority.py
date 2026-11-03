"""Priorización de brechas por riesgo.

puntuacion = 60*estado + 20*criticidad + 10*entidad + 10*cobertura   (0-100)

- estado: no_implementado 1.0; sin evaluar (None) 0.75; parcial 0.5;
  implementado / no_aplica = sin brecha: puntuación 0 y nivel P3.
- criticidad (campo opcional `criticidad` del control; por defecto media):
  alta 1.0, media 0.5, baja 0.0.
- entidad (cliente.tipo_entidad_nis2): esencial 1.0, importante 0.5, otro 0.0.
- cobertura: normas cubiertas por el control vía mapeo (NIS2, ENS, ISO27001,
  incluida la propia): (n-1)/2, es decir 0 si solo una norma, 1.0 si las tres.
Niveles: >=70 P1, >=40 P2, resto P3.
"""
from __future__ import annotations

from .mapping import normas_cubiertas

ESTADO = {"no_implementado": 1.0, None: 0.75, "parcial": 0.5}
CRITICIDAD = {"alta": 1.0, "media": 0.5, "baja": 0.0}
ENTIDAD = {"esencial": 1.0, "importante": 0.5}
UMBRAL_P1, UMBRAL_P2 = 70, 40


def nivel(puntuacion: float) -> str:
    return "P1" if puntuacion >= UMBRAL_P1 else "P2" if puntuacion >= UMBRAL_P2 else "P3"


def prioridad(control, estado: str | None, cliente: dict) -> tuple[float, str]:
    w = ESTADO.get(estado, 0.0)
    if w == 0.0:
        return 0.0, "P3"
    crit = CRITICIDAD.get(str(control.extra.get("criticidad", "media")).lower(), 0.5)
    ent = ENTIDAD.get(str((cliente or {}).get("tipo_entidad_nis2", "")).lower(), 0.0)
    cob = min(1.0, max(0, len(normas_cubiertas(control.id)) - 1) / 2)
    p = round(60 * w + 20 * crit + 10 * ent + 10 * cob, 1)
    return p, nivel(p)
