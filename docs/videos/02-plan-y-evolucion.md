# SMC 2 · Plan de acción y evolución entre evaluaciones

Duración: 1:34. Vídeo: https://youtu.be/I6QSXJhfonM

Todos los datos que aparecen son ficticios (ejemplos del repositorio).

## Capítulos y transcripción

### 0:00 Qué vas a conseguir

Tener la lista de brechas es la mitad. La otra mitad es saber quién las cierra, para cuándo, y demostrar que el cliente mejora de una evaluación a la siguiente. Eso es lo que vas a ver en este vídeo.

### 0:12 El plan en la evaluación

```bash
sed -n '/^plan_accion/,/ENE-02/p' assessments/examples/ejemplo-energia.yaml
```

El plan de acción va dentro de la propia evaluación. Cada acción tiene un identificador, los controles que cubre, qué hay que hacer, un responsable por rol, una fecha objetivo y un estado: pendiente, en curso, hecha o bloqueada.

### 0:28 smc plan

```bash
smc plan assessments/examples/ejemplo-energia.yaml --hoy 2026-11-03 | sed -n 5,10p
smc plan assessments/examples/ejemplo-energia.yaml --hoy 2026-11-03 | tail -2
```

smc plan ordena las acciones por fecha y marca las vencidas. Aquí, probar la restauración de copias en OT tenía que estar el treinta de octubre y sigue en curso. Debajo salen las brechas que nadie tiene asignadas, y un aviso si alguna es P1. Una acción hecha no cierra la brecha: la brecha se cierra cuando el control pasa a implementado.

### 0:50 smc compare

```bash
smc compare assessments/examples/historico/ejemplo-energia-2026-q1.yaml assessments/examples/ejemplo-energia.yaml | sed -n 3,19p
```

Tres meses después vuelves a evaluar. smc compare pone las dos evaluaciones lado a lado: el cumplimiento de cada marco antes y después, y qué controles se han cerrado, cuáles mejoran, cuáles empeoran y cuáles han dejado de evaluarse. NIS2 sube de cincuenta a cincuenta y tres coma tres.

### 1:10 Evolución en el informe

Y si al generar el informe le pasas la evaluación anterior, aparece una sección de evolución, que es justo lo que quiere ver un comité de dirección: si la inversión está moviendo los números.

### 1:22 Resumen

Resumen: smc plan para el seguimiento, smc compare para la evolución. En el siguiente vídeo, el informe completo y el dashboard con todos tus clientes.
