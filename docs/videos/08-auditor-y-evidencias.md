# SMC 8 · Declaración de aplicabilidad y evidencias para el auditor

Duración: 1:34. Vídeo: https://youtu.be/2d7SAYrAee8

Todos los datos que aparecen son ficticios (ejemplos del repositorio).

## Capítulos y transcripción

### 0:00 Qué vas a conseguir

El auditor no abre una web: quiere una tabla con cada control, si aplica, por qué no, su estado y la evidencia, y quiere saber que la evidencia está vigente. Eso es lo que vas a generar.

### 0:13 Declaración de aplicabilidad

```bash
smc soa assessments/examples/ejemplo-ayuntamiento.yaml --formato xlsx -o soa.xlsx
smc soa assessments/examples/ejemplo-ayuntamiento.yaml --formato csv -o soa.csv
smc soa assessments/examples/ejemplo-ayuntamiento.yaml --formato html -o soa.html
head -3 soa.csv | cut -c1-90
```

smc soa genera la declaración de aplicabilidad de la evaluación en tres formatos: Excel, CSV o una página imprimible a PDF. El Excel trae dos hojas, aplicabilidad y evidencias. Y las celdas que podrían ejecutarse como fórmulas se neutralizan.

### 0:32 Aplicabilidad ENS

Este ayuntamiento está en categoría media del Esquema Nacional de Seguridad. Cada medida dice si aplica, y si no, por qué: la justificación sale de la categoría o de la nota del evaluador. También el estado, la evidencia, los refuerzos que exige la categoría y su equivalencia en NIS2 e ISO 27001.

### 0:51 Evidencias

```bash
smc evidencias assessments/examples/ejemplo-energia.yaml --hoy 2026-11-03 | sed -n 3,10p
```

Una evidencia puede ser un texto o una ficha con su fecha, su caducidad y la huella del fichero. smc evidencias dice cuáles están vigentes, cuáles caducan pronto y cuáles han caducado. Este análisis de riesgos caducó en enero: sale avisado, pero no cambia la puntuación. Y con la opción base comprueba que cada fichero de evidencia no se ha modificado.

### 1:14 Resumen de la serie

Con esto tienes la herramienta completa: evaluación, brechas y plan; SOC, MITRE y pruebas ofensivas; tecnologías y red; inteligencia artificial; el proyecto; y lo que le entregas al auditor. Todo en tu equipo, con datos que no salen de él. El código es abierto y está en GitHub.
