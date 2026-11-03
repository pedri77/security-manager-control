# SMC 1 · Tu primera evaluación de ciberseguridad en 5 minutos

Duración: 2:22. Vídeo: pendiente de publicar.

Todos los datos que aparecen son ficticios (ejemplos del repositorio).

## Capítulos y transcripción

### 0:00 Qué vas a conseguir

En cinco minutos vas a pasar del perfil de un cliente a un informe de brechas priorizado: qué le exige la directiva NIS2, qué tiene, con qué evidencia y qué le falta. Todo en tu equipo, sin enviar datos a ningún sitio.

### 0:14 Instalación

```bash
git clone -q https://github.com/pedri77/security-manager-control.git
cd security-manager-control
uv sync -q
uv run smc --version
```

Necesitas Python tres punto diez o superior y uv. Clonas el repositorio, instalas con uv sync y compruebas la versión. La única dependencia es PyYAML.

### 0:34 Catálogos

```bash
smc validate
smc list
```

Primero, valida los catálogos. smc validate comprueba que los controles están bien formados, y smc list te dice cuántos hay en cada marco: quince de NIS2, setenta y tres medidas del Esquema Nacional de Seguridad, veintiún controles transversales y veinte de red.

### 0:52 El perfil del cliente

```bash
sed -n 2,15p assessments/examples/ejemplo-energia.yaml
```

Cada evaluación es un fichero de texto por cliente. Arriba va el perfil: sector, tamaño, si es entidad esencial o importante, y si es sector público, que es lo que decide si aplica el Esquema Nacional de Seguridad. Debajo, cada control con su estado, sus evidencias y sus notas. Este cliente es ficticio: los datos reales nunca van al repositorio.

### 1:15 Informe de brechas

```bash
smc gap assessments/examples/ejemplo-energia.yaml | head -13
```

smc gap calcula el cumplimiento de cada marco. Implementado cuenta uno, parcial cuenta medio, y lo que está sin evaluar cuenta como no cumplido, para que una evaluación a medias no parezca buena. Esta distribuidora está al cincuenta y tres por ciento en NIS2.

### 1:32 Informe HTML

```bash
smc report assessments/examples/ejemplo-energia.yaml --hoy 2026-11-03 -o informe.html
ls -lh informe.html
```

Con smc report sale el mismo análisis como un informe web autocontenido: un único fichero, sin servidor y sin nada cargado de internet, listo para enviárselo al cliente.

### 1:43 Brechas priorizadas

Arriba tienes el resumen ejecutivo por marco y las brechas más urgentes. Debajo, el detalle: cada brecha con su prioridad, P1, P2 o P3, y la nota del evaluador. La prioridad combina el estado del control, su criticidad, el tipo de entidad y cuántos marcos cubre. Aparte salen los controles sin evaluar y las evidencias caducadas, que no se mezclan con las brechas confirmadas.

### 2:08 Resumen

Resumen: smc validate, smc gap y smc report. En el siguiente vídeo convertimos estas brechas en un plan de acción con responsables y fechas. El código es abierto y lo tienes en GitHub.
