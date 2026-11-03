# SMC 4 · SOC, MITRE ATT&CK, pentest y purple team

Duración: 1:50. Vídeo: pendiente de publicar.

Todos los datos que aparecen son ficticios (ejemplos del repositorio).

## Capítulos y transcripción

### 0:00 Qué vas a conseguir

Cumplir la norma no basta: hay que saber si el SOC detecta y responde a tiempo. En este vídeo mides el SOC, su madurez frente a MITRE ATT&CK, y lo pruebas con pentest y purple team.

### 0:13 Rendimiento del SOC

```bash
smc soc soc/incidents.template.csv
```

smc soc lee la exportación de incidentes en CSV y calcula los tiempos medios de detección, de atención, de contención y de resolución, por severidad y frente al acuerdo de nivel de servicio. También comprueba la alerta temprana de NIS2 en veinticuatro horas: aquí, una de dos en plazo.

### 0:34 Madurez MITRE

```bash
smc mitre | sed -n 28,39p
```

smc mitre cruza los casos de uso del SOC con las técnicas de MITRE ATT&CK. Cada técnica tiene una madurez de cero a cinco, y cada táctica toma la de su caso más débil, para que no se escondan los huecos. También avisa de los casos sin prueba y sin playbook.

### 0:51 Pentest

```bash
smc pentest offensive/examples/ejemplo-pentest.yaml --hoy 2026-11-03 | sed -n 3,18p
```

Los hallazgos de pentest se siguen con el mismo plazo que las vulnerabilidades. Esta inyección SQL crítica lleva cuarenta y nueve días abierta con un plazo de siete. Y si un hallazgo marcado como corregido falla el retest, vuelve a contar como abierto.

### 1:07 Purple team

```bash
smc purple offensive/examples/ejemplo-purple.yaml --hoy 2026-11-03 | sed -n 3,20p
```

Con purple team pruebas si de verdad detectas una técnica concreta. smc purple da la cobertura por táctica, las técnicas que no se detectaron y las mejoras abiertas. Y si pasas los ejercicios a smc mitre, una técnica detectada en un ejercicio reciente sube la madurez del caso de uso, porque está probada.

### 1:27 En el informe

Todo esto aparece también en el informe del cliente, con los hallazgos fuera de plazo, los retest fallidos y la cobertura del purple team.

### 1:36 Resumen

Resumen: smc soc, smc mitre, smc pentest y smc purple. En el siguiente vídeo, las tecnologías del cliente, sus vulnerabilidades y el mapa de la red en tres dimensiones.
