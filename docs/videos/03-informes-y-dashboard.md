# SMC 3 · Informe completo y dashboard multicliente

Duración: 1:33. Vídeo: pendiente de publicar.

Todos los datos que aparecen son ficticios (ejemplos del repositorio).

## Capítulos y transcripción

### 0:00 Qué vas a conseguir

Un informe completo por cliente, con todos los módulos, y un panel para ver a todos tus clientes de un vistazo. Ficheros estáticos que abres en el navegador, sin servidor y sin que nada salga de tu equipo.

### 0:13 El informe completo

```bash
smc report --help | sed -n 8,20p
```

smc report admite un fichero por módulo: el registro de tecnologías, el pentest, el purple team, el inventario de inteligencia artificial, el proyecto y la evaluación anterior. Cada fichero que le pases añade su sección. Los que no, simplemente no aparecen.

### 0:31 Recorrido por el informe

Este es el informe con todo: resumen ejecutivo, detalle por marco, verticales, evolución, tecnologías y reglas, suscripciones, hallazgos de pentest, purple team, el reglamento de inteligencia artificial, el proyecto con sus costes, la madurez MITRE y el plan de acción. Todo en un único fichero. El texto de los datos se escapa siempre, y los enlaces solo pueden ser seguros.

### 0:56 Dashboard multicliente

```bash
ls assessments/examples
smc dashboard assessments/examples --hoy 2026-11-03 -o panel
ls panel
```

smc dashboard lee un directorio con las evaluaciones de todos tus clientes y genera un panel estático: un índice, una página por cliente y la cobertura MITRE común.

### 1:08 El panel

En el índice ves a cada cliente con su cumplimiento por marco, sus P1 abiertas, las acciones vencidas y la evidencia caducada. Es lo primero que miras el lunes por la mañana.

### 1:20 Resumen

Resumen: un informe por cliente con los módulos que quieras, y un panel para todos. En el siguiente vídeo, el rendimiento del SOC, la madurez MITRE y los ejercicios de purple team.
