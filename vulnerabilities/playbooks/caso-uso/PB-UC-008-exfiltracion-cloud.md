# PB-UC-008 — Exfiltración a servicio cloud no corporativo · v1

| Campo | Valor |
|---|---|
| Caso de uso | UC-008 |
| MITRE | T1567.002 |
| Severidad por defecto | Alta |
| Tier | N1 triaje → N2 contención → N3 erradicación |

Documento genérico: sin datos reales; sustituir los marcadores (Sistema A, Cuenta X) en cada incidente.

## 1. Detección y triaje (N1, SLA ack según severidad)
1. Identificar usuario, volumen, destino y tipo de datos (Proxy, CASB, DLP).
2. ¿Servicio autorizado o uso personal? Contrastar con la política de uso aceptable.
3. Clasificar los datos afectados; si son sensibles, escalar a N2.

## 2. Contención (N2)
1. Bloquear el destino en proxy/CASB y suspender la sesión del usuario.
2. Revocar tokens de aplicación y accesos a los repositorios implicados.
3. Preservar evidencias para RR. HH. y Legal.

## 3. Erradicación
1. Solicitar el borrado de los datos en el servicio externo y obtener confirmación escrita.
2. Eliminar la herramienta de sincronización no autorizada.

## 4. Recuperación
1. Restablecer el acceso del usuario con permisos revisados.
2. Monitorización reforzada de su actividad.

## 5. Lecciones aprendidas
- Ajustar las reglas DLP y la lista de servicios permitidos.
- Reforzar la formación sobre tratamiento de datos.

## Notificación NIS2
- Si el incidente es significativo (perturbación grave del servicio o pérdida/daño material o inmaterial considerable): alerta temprana en 24 h desde que se tiene conocimiento, notificación del incidente en 72 h y informe final en 1 mes (art. 23 NIS2). Valorar también RGPD (72 h a la AEPD) si hay datos personales.
- Registrar la decisión de notificar o no, con su motivo, en el incidente.
- Si hay datos personales: valorar notificación a la AEPD (72 h) y comunicación a los interesados.
