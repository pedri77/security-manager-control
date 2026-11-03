# PB-UC-006 — Borrado de copias de sombra / preparación de ransomware · v1

| Campo | Valor |
|---|---|
| Caso de uso | UC-006 |
| MITRE | T1490, T1486 |
| Severidad por defecto | Crítica |
| Tier | N1 triaje → N2 contención → N3 erradicación |

Documento genérico: sin datos reales; sustituir los marcadores (Sistema A, Cuenta X) en cada incidente.

## 1. Detección y triaje (N1, SLA ack según severidad)
1. Confirmar comandos de borrado de shadow copies o desactivación de recuperación (Sysmon 1, EDR).
2. Buscar cifrado en curso: renombrados masivos, notas de rescate.
3. Declarar incidente crítico y activar el comité de crisis.

## 2. Contención (N2)
1. Aislar de la red los equipos afectados y los recursos compartidos accesibles desde ellos.
2. Desconectar las copias de seguridad en línea y proteger el repositorio inmutable.
3. Deshabilitar las cuentas implicadas; bloquear C2 conocido.

## 3. Erradicación
1. Identificar el acceso inicial y el alcance completo de la intrusión.
2. Eliminar el malware, la persistencia y las cuentas del atacante.
3. Cerrar la vulnerabilidad o credencial de entrada.

## 4. Recuperación
1. Restaurar desde copia verificada y limpia, por orden de criticidad del negocio.
2. Validar la integridad antes de reconectar a la red.
3. Monitorización reforzada durante al menos 30 días.

## 5. Lecciones aprendidas
- Probar la restauración periódicamente y mantener copias inmutables y fuera de línea.
- Revisión posincidente con la dirección.
- Actualizar el análisis de riesgos.

## Notificación NIS2
- Si el incidente es significativo (perturbación grave del servicio o pérdida/daño material o inmaterial considerable): alerta temprana en 24 h desde que se tiene conocimiento, notificación del incidente en 72 h y informe final en 1 mes (art. 23 NIS2). Valorar también RGPD (72 h a la AEPD) si hay datos personales.
- Registrar la decisión de notificar o no, con su motivo, en el incidente.
