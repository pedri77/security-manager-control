# SMC 6 · Reglamento europeo de IA y seguridad de agentes

Duración: 1:33. Vídeo: https://youtu.be/_0o6j21jd_M

Todos los datos que aparecen son ficticios (ejemplos del repositorio).

## Capítulos y transcripción

### 0:00 Qué vas a conseguir

Qué te exige el Reglamento europeo de inteligencia artificial, para cada sistema, y desde qué fecha. Y si tus agentes con herramientas tienen límites, supervisión y defensas contra la inyección de instrucciones.

### 0:13 El inventario

```bash
sed -n 26,40p ai/inventario.template.yaml
```

Todo parte de un inventario: cada sistema con su finalidad, el rol de la organización, que puede ser proveedor o responsable del despliegue, el nivel de riesgo y las evidencias que ya tiene, como la supervisión humana o el registro de actividad.

### 0:29 Obligaciones por sistema

```bash
smc ai ai/inventario.template.yaml --hoy 2026-11-03 | sed -n 17,22p
```

smc ai cruza el inventario con treinta y una obligaciones del reglamento y te dice cuáles aplican, desde cuándo y cuáles faltan por evidencia. Las fechas ya incluyen el Ómnibus Digital: el alto riesgo del anexo tres pasa a diciembre de dos mil veintisiete. Un sistema de alto riesgo que ya estaba en el mercado y no cambia entra en el régimen transitorio, pero solo si lo declaras.

### 0:53 Seguridad de agentes

En el informe, cada sistema con sus obligaciones, y para los agentes con herramientas, las comprobaciones de seguridad basadas en el top diez de OWASP para aplicaciones con modelos de lenguaje y en MITRE ATLAS: herramientas sin límite de llamadas, permisos de más, sin aprobación humana, o contenido de terceros sin mitigación contra la inyección de instrucciones. Importante: esto orienta, no es asesoramiento jurídico.

### 1:19 Resumen

Resumen: inventario, obligaciones del reglamento con sus fechas y seguridad de agentes. En el siguiente vídeo, la gestión del proyecto: tareas, horas, costes y presupuesto.
