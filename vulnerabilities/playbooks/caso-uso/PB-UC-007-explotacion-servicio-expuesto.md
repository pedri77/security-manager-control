# PB-UC-007 — Explotación de servicio expuesto a Internet · v1

| Campo | Valor |
|---|---|
| Caso de uso | UC-007 |
| MITRE | T1190 |
| Severidad por defecto | Crítica |
| Tier | N1 triaje → N2 contención → N3 erradicación |

Documento genérico: sin datos reales; sustituir los marcadores (Sistema A, Cuenta X) en cada incidente.

## 1. Detección y triaje (N1, SLA ack según severidad)
1. Identificar el servicio (Aplicación A), la firma o petición explotadora y la IP origen (WAF, IDS, logs).
2. ¿Respuesta con éxito (2xx/5xx anómalo), procesos hijos inesperados, ficheros nuevos?
3. Cruzar con CVE conocidos y con el catálogo KEV.

## 2. Contención (N2)
1. Bloquear el origen y aplicar regla WAF/parche virtual.
2. Si hay indicios de ejecución: aislar el servidor y retirarlo de la publicación.
3. Preservar logs y una imagen forense.

## 3. Erradicación
1. Aplicar el parche o la mitigación del fabricante.
2. Buscar webshells, cuentas y tareas creadas; eliminarlas.
3. Rotar secretos accesibles desde el servidor.

## 4. Recuperación
1. Reconstruir desde imagen limpia y desplegar la versión corregida.
2. Verificar con escaneo de vulnerabilidades antes de republicar.

## 5. Lecciones aprendidas
- Revisar plazos de parcheo para servicios expuestos.
- Mantener inventario actualizado de activos expuestos.

## Notificación NIS2
- Si el incidente es significativo (perturbación grave del servicio o pérdida/daño material o inmaterial considerable): alerta temprana en 24 h desde que se tiene conocimiento, notificación del incidente en 72 h y informe final en 1 mes (art. 23 NIS2). Valorar también RGPD (72 h a la AEPD) si hay datos personales.
- Registrar la decisión de notificar o no, con su motivo, en el incidente.
