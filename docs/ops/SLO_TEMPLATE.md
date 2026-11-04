# SLO — <servicio>

**Versión:** v1 · **Owner:** engineering · **Revisión:** trimestral

| SLI | Medición | Objetivo (SLO) | Ventana | Presupuesto de error |
|---|---|---|---|---|
| Disponibilidad | % peticiones no-5xx en `/api/*` | 99,5 % | 30 días | 3 h 36 min |
| Latencia | p95 de `/api/*` | < 500 ms | 30 días | 5 % de peticiones |
| Frescura (si aplica) | retraso de ingesta | < 5 min | 7 días |  |

## Alertas
| Alerta | Condición | Severidad | Canal | Runbook |
|---|---|---|---|---|
| Quema rápida | 2 % del presupuesto en 1 h | SEV2 | on-call | docs/ops/runbooks/<servicio>.md |
| Quema lenta | 10 % del presupuesto en 3 días | SEV3 | issue automática |  |

## Política de presupuesto agotado
Congelar features del servicio; solo `fix`/`sec`/`perf` hasta recuperar el SLO.

## Objetivos de continuidad
- RTO: <h> · RPO: <min> · Último restore_drill: YYYY-MM-DD (resultado: RTO real __, RPO real __)
