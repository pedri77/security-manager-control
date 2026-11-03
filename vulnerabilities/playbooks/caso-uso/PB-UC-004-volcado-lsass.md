# PB-UC-004 — Volcado de LSASS · v1

| Campo | Valor |
|---|---|
| Caso de uso | UC-004 |
| MITRE | T1003.001 |
| Severidad por defecto | Crítica |
| Tier | N1 triaje → N2 contención → N3 erradicación |

Documento genérico: sin datos reales; sustituir los marcadores (Sistema A, Cuenta X) en cada incidente.

## 1. Detección y triaje (N1, SLA ack según severidad)
1. Identificar el proceso que accede a LSASS (Sysmon 10, EDR) y su firma/ruta.
2. Descartar herramientas de seguridad autorizadas.
3. Si no es legítimo: tratar como compromiso de credenciales y escalar a N2 de inmediato.

## 2. Contención (N2)
1. Aislar el equipo (Servidor A) en EDR.
2. Considerar comprometidas todas las cuentas con sesión en ese equipo: reset y revocación de tickets Kerberos.
3. Si hay cuentas privilegiadas, rotar también la cuenta de servicio del dominio según criticidad.

## 3. Erradicación
1. Eliminar la herramienta de volcado y la vía de entrada que la trajo.
2. Habilitar Credential Guard / protección LSA donde falte.
3. Hunting de uso de credenciales robadas (inicios de sesión inusuales).

## 4. Recuperación
1. Reconstruir o reimaginar el equipo.
2. Reincorporar con credenciales nuevas y monitorización reforzada.

## 5. Lecciones aprendidas
- Reducir cuentas privilegiadas con sesión en equipos de usuario.
- Revisar el modelo de administración por niveles.

## Notificación NIS2
- Si el incidente es significativo (perturbación grave del servicio o pérdida/daño material o inmaterial considerable): alerta temprana en 24 h desde que se tiene conocimiento, notificación del incidente en 72 h y informe final en 1 mes (art. 23 NIS2). Valorar también RGPD (72 h a la AEPD) si hay datos personales.
- Registrar la decisión de notificar o no, con su motivo, en el incidente.
