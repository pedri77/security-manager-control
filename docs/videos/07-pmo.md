# SMC 7 · PMO: tareas, horas, costes y presupuesto

Duración: 1:26. Vídeo: pendiente de publicar.

Todos los datos que aparecen son ficticios (ejemplos del repositorio).

## Capítulos y transcripción

### 0:00 Qué vas a conseguir

Cerrar brechas es un proyecto, con tareas, horas, costes y un presupuesto que hay que defender. En este vídeo llevas ese proyecto con smc pmo, ligado a las mismas brechas.

### 0:13 Presupuesto y valor ganado

```bash
smc pmo pmo/examples/ejemplo-energia.yaml --hoy 2026-11-03 | sed -n 5,19p
```

smc pmo compara el presupuesto de cada partida con el gasto real: horas, licencias, servicios y formación. Y calcula el valor ganado. El índice de coste, cero coma sesenta y tres, dice que por cada euro gastado se ha avanzado sesenta y tres céntimos. El de plazo, uno coma once, dice que se va por delante del calendario.

### 0:36 Retrasos y horas

```bash
smc pmo pmo/examples/ejemplo-energia.yaml --hoy 2026-11-03 | sed -n 21,37p
```

Debajo, las tareas retrasadas, las que no están ligadas a ningún control, los próximos comités y auditorías, y las horas imputadas por rol y por mes.

### 0:47 Calendario

```bash
smc pmo pmo/examples/ejemplo-energia.yaml --hoy 2026-11-03 --ics hitos.ics > /dev/null
head -13 hitos.ics
```

Con la opción --ics exportas comités, auditorías, renovaciones y entregas a un calendario que se importa en Outlook, Google o cualquier otro. Las tarifas, las horas y el presupuesto son datos del cliente: nunca van al repositorio.

### 1:04 En el informe

Y en el informe del cliente, la misma información con avisos: partidas desviadas, tareas retrasadas, o costes sin presupuesto asignado.

### 1:14 Resumen

Resumen: presupuesto, valor ganado, retrasos y calendario. En el último vídeo, lo que le entregas al auditor: la declaración de aplicabilidad y las evidencias.
