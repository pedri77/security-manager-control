# PB-UC-003 — Ejecución de PowerShell ofuscado · v1

| Campo | Valor |
|---|---|
| Caso de uso | UC-003 |
| MITRE | T1059.001, T1027 |
| Severidad por defecto | Media |
| Tier | N1 triaje → N2 contención → N3 erradicación |

Documento genérico: sin datos reales; sustituir los marcadores (Sistema A, Cuenta X) en cada incidente.

## 1. Detección y triaje (N1, SLA ack según severidad)
1. Revisar la línea de comandos, el proceso padre y el usuario (Sysmon 1, PowerShell 4104).
2. Decodificar el contenido (base64, cadenas concatenadas) en entorno aislado.
3. ¿Es administración legítima conocida (script firmado, tarea programada)? Si no, escalar a N2.

## 2. Contención (N2)
1. Aislar el equipo en EDR si el script descarga o ejecuta carga adicional.
2. Bloquear dominios/IP contactados y finalizar el proceso.
3. Preservar el script y la memoria antes de limpiar.

## 3. Erradicación
1. Eliminar tareas programadas, claves de ejecución y ficheros persistentes.
2. Rotar credenciales usadas en el equipo.
3. Buscar el patrón en otros equipos.

## 4. Recuperación
1. Reimagen si hay dudas sobre la integridad.
2. Monitorización reforzada del equipo durante 7 días.

## 5. Lecciones aprendidas
- Activar Constrained Language Mode y registro de bloques de script si faltaban.
- Ajustar la regla para excluir administración legítima documentada.

## Notificación NIS2
- Si el incidente es significativo (perturbación grave del servicio o pérdida/daño material o inmaterial considerable): alerta temprana en 24 h desde que se tiene conocimiento, notificación del incidente en 72 h y informe final en 1 mes (art. 23 NIS2). Valorar también RGPD (72 h a la AEPD) si hay datos personales.
- Registrar la decisión de notificar o no, con su motivo, en el incidente.
