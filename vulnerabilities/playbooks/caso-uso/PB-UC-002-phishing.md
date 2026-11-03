# PB-UC-002 — Phishing con adjunto o enlace malicioso · v1

| Campo | Valor |
|---|---|
| Caso de uso | UC-002 |
| MITRE | T1566.001, T1566.002 |
| Severidad por defecto | Alta |
| Tier | N1 triaje → N2 contención → N3 erradicación |

Documento genérico: sin datos reales; sustituir los marcadores (Sistema A, Cuenta X) en cada incidente.

## 1. Detección y triaje (N1, SLA ack según severidad)
1. Identificar mensaje, remitente, asunto, adjunto/URL y destinatarios (Buzón A, Buzón B).
2. ¿Alguien abrió el adjunto o pulsó el enlace? Consultar telemetría de proxy y EDR.
3. Detonar la URL o el adjunto en sandbox; reputación de dominio y hash.
4. Si hubo interacción o credenciales introducidas → escalar a N2.

## 2. Contención (N2)
1. Retirar el mensaje de todos los buzones (purga masiva) y bloquear remitente, dominio y URL en gateway y proxy.
2. Si se introdujeron credenciales: revocar sesiones, reset de contraseña y comprobar MFA y reglas de reenvío del buzón.
3. Aislar en EDR el equipo que ejecutó el adjunto.

## 3. Erradicación
1. Eliminar persistencia y artefactos del adjunto en el equipo afectado (Equipo A).
2. Buscar el mismo IoC en el resto de la flota y del correo (hunting).
3. Revocar tokens de aplicación OAuth concedidos por error.

## 4. Recuperación
1. Reincorporar el equipo aislado tras reimagen o limpieza verificada.
2. Restablecer accesos y confirmar con el usuario afectado.

## 5. Lecciones aprendidas
- ¿Por qué pasó el filtro? Ajustar reglas del gateway.
- Reforzar la concienciación y el botón de reporte de phishing.
- Registrar los IoC en la inteligencia de amenazas.

## Notificación NIS2
- Si el incidente es significativo (perturbación grave del servicio o pérdida/daño material o inmaterial considerable): alerta temprana en 24 h desde que se tiene conocimiento, notificación del incidente en 72 h y informe final en 1 mes (art. 23 NIS2). Valorar también RGPD (72 h a la AEPD) si hay datos personales.
- Registrar la decisión de notificar o no, con su motivo, en el incidente.
