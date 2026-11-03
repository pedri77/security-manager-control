# SMC 5 · Tecnologías, vulnerabilidades y mapa 3D de la red

Duración: 1:58. Vídeo: pendiente de publicar.

Todos los datos que aparecen son ficticios (ejemplos del repositorio).

## Capítulos y transcripción

### 0:00 Qué vas a conseguir

Las tecnologías que el cliente ya paga, si están bien configuradas, cuándo caducan, qué vulnerabilidades tienen fuera de plazo, y todo eso pintado en un mapa de la red en tres dimensiones.

### 0:12 Tecnologías y reglas

```bash
smc tech technologies/registry.template.yaml --hoy 2026-11-03 | sed -n 3,19p
```

El registro de tecnologías dice qué hay, con qué cobertura y cómo está configurado. smc tech lo evalúa y revisa las reglas de cada dispositivo. Este firewall tiene seis reglas de cualquier origen a cualquier destino, y eso sale en rojo aunque alguien diga que lo revisó ayer.

### 0:30 Caducidades y suscripciones

```bash
smc expiring technologies/registry.template.yaml --days 90
smc subs technologies/registry.template.yaml --hoy 2026-11-03 | sed -n 11,15p
```

smc expiring avisa de licencias y certificados que caducan en los próximos noventa días. Y smc subs encuentra el dinero parado: aquí, un servicio de acceso a la nube con cien licencias y cuarenta en uso, dieciocho mil euros al año sin aprovechar.

### 0:47 Vulnerabilidades

```bash
smc vulns vulnerabilities/tracker.template.csv
smc protocols TELNET | head -7
```

smc vulns aplica la política de plazos por severidad, y lo que está en la lista KEV de explotación activa cuenta siempre como crítico. Y smc protocols te da, para veintiocho protocolos, su capa, sus riesgos típicos y dónde buscar en las fuentes oficiales.

### 1:05 El mapa

```bash
smc mapa technologies/registry.template.yaml --tracker vulnerabilities/tracker.template.csv --evaluacion assessments/examples/ejemplo-energia.yaml -o mapa.json
smc visor mapa.json -o visor.html
```

smc mapa junta tecnologías, reglas y vulnerabilidades en un mapa por zonas, y smc visor lo convierte en un visor en tres dimensiones: un único fichero, sin servidor y sin cargar nada de internet.

### 1:20 Visor 3D

Cada dispositivo es una esfera con su semáforo. Rojo: una vulnerabilidad crítica fuera de plazo o reglas peligrosas. Ámbar: revisión pendiente. Gris: no se puede evaluar, y nunca pasa a verde. La visita automática recorre las zonas: el perímetro en rojo, los usuarios y la nube en ámbar. Y la vista por capas OSI separa los dispositivos por capa.

### 1:44 Resumen

Resumen: tecnologías, caducidades, suscripciones, vulnerabilidades y el mapa de la red. En el siguiente vídeo, el Reglamento europeo de inteligencia artificial y la seguridad de los agentes.
