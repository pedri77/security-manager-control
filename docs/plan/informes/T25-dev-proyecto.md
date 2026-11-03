# T25 · dev-proyecto · Verticales de identidad, dato, IA y seguridad ofensiva

Rama `t25-v07`. Sin push. Plan no marcado.

## Hecho
- `soc/verticals.yaml`: 4 verticales nuevas con nis2, controles existentes, criterios y `niveles` 0-5 (6 descriptores distintos). Total 24.
- Plantilla y los dos ejemplos ficticios con las 4 (ayuntamiento: IDSEC 2, DSPM 2, OFF 1, AI `no_evaluable` con motivo; energía: IDSEC 4, DSPM 3, AI 2, OFF 3).
- `soc/README.md` y tests de cifras a 24; `tests/test_verticals_v07.py` (7 tests nuevos).

## Decisión a revisar: colisión de IDs
`VRT-IAM` y `VRT-DATA` YA existían (desde v0.5, 4 controles y 4 criterios cada una). Reutilizar esos IDs no daba 24. Se crearon `VRT-IDSEC` (seguridad de la identidad: IGA, PAM, NHI, ITDR, AD/Entra) y `VRT-DSPM` (seguridad del dato) y se dejaron IAM y DATA intactas. Consecuencia: solapan en NIS2 21.2.i/h y se promedian en la agregación NIS2 (sin paraguas `agrupa`). Alternativa si se prefiere: fusionar en IAM/DATA y quedarían 22. Decide David/coordinador.

## Controles por vertical
- VRT-IDSEC (nis2 21.2.i, 21.2.j): NIS2-21.2.i, NIS2-21.2.j, TRV-ID-01, TRV-ID-02, ENS-op.acc.1 a op.acc.6.
- VRT-DSPM (nis2 21.2.h, 21.2.i): NIS2-21.2.h, NIS2-21.2.i, TRV-DATA-01, TRV-RGPD-01, ENS-mp.info.1, .2, .5, .6, ENS-mp.com.2, ENS-mp.si.2, ENS-mp.si.5.
- VRT-AI (nis2 21.2.a, 21.2.e): NIS2-21.2.a, NIS2-21.2.e, TRV-AI-01, TRV-GOB-01, TRV-GOB-02, TRV-RGPD-01, ENS-op.pl.1. Sin catálogo RIA (lo hace T26). `estado_recursos` pendiente sin URL.
- VRT-OFF (nis2 21.2.e, 21.2.f): NIS2-21.2.e, NIS2-21.2.f, TRV-VUL-01, TRV-VUL-02, ENS-op.exp.4. `estado_recursos` pendiente sin URL.
Ninguna lleva `recursos`. `URLS_PUBLICAS` no se toca.

## Verifica
- `uv run --extra dev pytest -q`: 370 passed (363 + 7).
- `smc validate`: Catálogos OK. `smc verticals` sobre ambos ejemplos muestra las 4 (AI como no_evaluable con motivo en ayuntamiento).
- Cambio justificado en `test_ejemplo_energia_valores`: NIS2-21.2.a 3.33 a 3.0 (entra AI=2), 21.2.j 1 a 2.5 (entra IDSEC=4), sin FW/ZTNA 3.67 a 3.25.

## Contraprueba (ejecutada)
`TRV-AI-01` cambiado por `TRV-AI-99` en VRT-AI: 10 failed; restaurado: 370 passed. Además `test_contraprueba_control_inexistente_en_vrt_ai_falla` y recurso fuera de lista en VRT-OFF.

## Queda
- Descriptores a validar por el Security Manager. README raíz (fuera de Toca) sigue diciendo 20 verticales: lo actualiza T28.
