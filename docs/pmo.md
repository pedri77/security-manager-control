# PMO: horas, costes y valor ganado

Módulo `smc/pmo.py`. Entrada: un YAML de proyecto (plantilla en `pmo/proyecto.template.yaml`, ejemplo ficticio en `pmo/examples/ejemplo-energia.yaml`). Los datos reales no se versionan (ADR-005).

## Datos

- `proyecto`: id, nombre, cliente, inicio, fin, `presupuesto_total` y `presupuesto` por partida (`horas`, `licencias`, `servicios`, `formacion`). Si `presupuesto_total` no coincide con la suma de partidas, aviso.
- `tarifas`: euros por hora y rol.
- `tareas`: id, título, `controles` (IDs de controles o brechas SMC), `accion` (id del `plan_accion` de la evaluación, opcional), `responsable` (rol), `horas_estimadas`, `avance` (0-100), `inicio`, `fin`, `depende`, `presupuesto` (opcional).
- `imputaciones`: fecha, rol, tarea, horas. Es la **única fuente** de horas reales: el coste laboral es horas × tarifa del rol.
- `costes`: costes no laborales (proveedor, concepto, importe, fecha, partida distinta de `horas`, tarea opcional).
- `eventos` (comité, auditoría, renovación, entrega, hito) y `riesgos`.

Dato mal formado = aviso y se ignora o se toma como 0; nunca excepción. Ejemplos: imputación a una tarea que no existe (se ignora), importe no numérico (se ignora o vale 0), rol sin tarifa (vale 0), avance fuera de 0-100 (se ajusta), imputaciones o costes con fecha posterior a `hoy` (no cuentan).

## Importes

Todo en `Decimal`. Las sumas se hacen sin redondeo intermedio y se redondea una vez a 2 decimales (mitad hacia arriba). CPI y SPI también a 2 decimales.

## Valor ganado (EVM) simple

- **Presupuesto de la tarea (BAC)** = `presupuesto` de la tarea si existe; si no, `horas_estimadas` × tarifa del `responsable`.
- **PV** = suma de (BAC × % planificado a `hoy`). El % planificado es lineal por días entre `inicio` y `fin` de la tarea: 0 hasta `inicio`, 1 desde `fin`. Sin fechas válidas, 0.
- **EV** = suma de (BAC × `avance` / 100).
- **AC** = horas imputadas × tarifa del rol, más los costes no laborales imputados a la tarea. Los costes sin tarea cuentan en el coste real por partida, pero no en AC (no hay valor ganado al que oponerlos).
- **CPI** = EV / AC. **SPI** = EV / PV. División por cero = `None` con aviso. CPI < 1: sobrecoste; SPI < 1: retraso.

Caso a mano (el mismo del test): tarea A, BAC 1 000 €, 10 al 20 de enero, avance 50 %; tarea B, BAC 500 €, 15 al 25 de enero, avance 20 %; `hoy` = 15 de enero. PV = 1 000 × 5/10 + 500 × 0 = 500. EV = 500 + 100 = 600. AC = 450. CPI = 600/450 = 1,33; SPI = 600/500 = 1,20.

## Otros cálculos

- **Coste real por partida** (`horas` con las imputaciones, el resto con `costes`), presupuesto y desviación (presupuesto menos real; negativa = sobrecoste, con aviso).
- **Tarea retrasada**: `fin` < `hoy` y avance < 100.
- **Tarea sin control asociado**: sin `controles` propios ni los de su `accion` en el `plan_accion` (si se pasa la evaluación). Una `accion` inexistente da aviso.
- **Próximos eventos**: de `hoy` a `hoy` + 30 días, ambos incluidos.
- **Horas por rol y mes** (AAAA-MM).
- **Suscripciones** (opcional): con un registro de tecnologías, suma el `coste_anual` en EUR que ya calcula `smc.tech.suscripciones`. Se muestra aparte, no entra en el presupuesto ni en AC. Otras monedas, aviso.

## API

```python
from smc.pmo import cargar_proyecto, analizar, render_markdown, eventos_ics, exportar_ics
p = cargar_proyecto("pmo/examples/ejemplo-energia.yaml")
a = analizar(p, hoy=date(2026, 11, 3), assessment=evaluacion_dict, registry="registry.yaml")
print(render_markdown(a))
exportar_ics(p, "eventos.ics", hoy=date(2026, 11, 3))
```

## iCalendar

`eventos_ics` genera RFC 5545 sin dependencias: líneas terminadas en CRLF, plegado a 75 octetos sin partir caracteres UTF-8, escape de `\`, `;`, `,` y saltos de línea en los textos, un `UID` estable por evento (`<proyecto>-<evento>@smc.pmo`), `DTSTAMP` = `hoy` a las 00:00:00Z y eventos de día completo (`DTEND` exclusivo). Los eventos sin `id` reciben uno derivado de título y fecha.

El `.ics` lleva datos del cliente: no se versiona (ADR-005).
