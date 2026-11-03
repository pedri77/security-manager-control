# PB-UC-001 — Fuerza bruta / password spraying · v1

| Campo | Valor |
|---|---|
| Caso de uso | UC-001 |
| MITRE | T1110, T1110.003 |
| Severidad por defecto | Alta |
| Tier | N1 triaje → N2 contención |

## N1 — Triaje (SLA ack según severidad)
1. Identificar IP(s) origen, cuentas objetivo, número de intentos y ventana temporal.
2. ¿Algún inicio de sesión **exitoso** tras los fallos? → escalar a N2 como posible compromiso.
3. Reputación de la IP (TI) y geolocalización.

## N2 — Contención
1. Bloquear IP/rango en firewall/WAF o acceso condicional.
2. Si hay éxito: revocar sesiones, reset de credenciales, verificar MFA registrado y reglas de buzón.
3. Hunting: misma IP contra otros servicios (VPN, OWA, SaaS).

## Cierre
- Clasificar: FP / intento fallido / compromiso.
- Si compromiso con impacto significativo → evaluar notificación NIS2.
- Lecciones: ¿falta MFA en algún servicio? → abrir brecha en NIS2-21.2.j.
