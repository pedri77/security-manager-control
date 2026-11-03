# PB-UC-005 — Movimiento lateral por RDP/SMB anómalo · v1

| Campo | Valor |
|---|---|
| Caso de uso | UC-005 |
| MITRE | T1021.001, T1021.002 |
| Severidad por defecto | Alta |
| Tier | N1 triaje → N2 contención → N3 erradicación |

Documento genérico: sin datos reales; sustituir los marcadores (Sistema A, Cuenta X) en cada incidente.

## 1. Detección y triaje (N1, SLA ack según severidad)
1. Identificar origen, destino, cuenta y horario (AD 4624 tipo 10, NDR).
2. ¿Es administración habitual del usuario o del equipo de TI? Contrastar con el CMDB.
3. Mapear el recorrido: otros destinos desde el mismo origen.

## 2. Contención (N2)
1. Aislar el equipo origen y bloquear la cuenta usada.
2. Limitar RDP/SMB entre segmentos con reglas temporales en el firewall interno.
3. Revocar sesiones activas de la cuenta.

## 3. Erradicación
1. Localizar el acceso inicial y la herramienta usada (credenciales robadas, exploit).
2. Eliminar puertas traseras y cuentas creadas en los equipos visitados.
3. Rotar credenciales de toda la ruta.

## 4. Recuperación
1. Restaurar reglas de segmentación definitivas.
2. Reincorporar los equipos tras verificación.

## 5. Lecciones aprendidas
- Segmentar y restringir RDP/SMB a jump hosts.
- Añadir cobertura de detección en la ruta no vista.

## Notificación NIS2
- Si el incidente es significativo (perturbación grave del servicio o pérdida/daño material o inmaterial considerable): alerta temprana en 24 h desde que se tiene conocimiento, notificación del incidente en 72 h y informe final en 1 mes (art. 23 NIS2). Valorar también RGPD (72 h a la AEPD) si hay datos personales.
- Registrar la decisión de notificar o no, con su motivo, en el incidente.
