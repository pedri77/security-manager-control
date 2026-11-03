# Olas 5-6 · revisor-ola v1.1 · revisión T09-T15 (8d0a532..9aa1c87)

Veredicto: APTA con reservas. 195 tests verdes; todos los comandos nuevos rc=0 sobre ejemplos y plantillas. T16 (96616ff) no revisada.

## Hallazgos
1. [V] media · T15 · `smc/mapa.py:122-129, 158-161`: el semáforo solo cuenta KEV/críticas fuera de SLA y usa la severidad declarada; ignora `priorizacion.kev_o_explotacion_activa: critica` de `policy.yaml`. KEV crítica abierta hace 2 días con reglas revisadas da verde.
2. [V] media · T15 · `smc/mapa.py:117-122`: severidad fuera de la política («Crítica» con tilde) deja `limite=None` y nunca vence: verde.
3. [V] media · T10 · `smc/tech.py:164-167, 186-188`: `reglas()` deja como «Revisadas» un dispositivo con any-any si la revisión es reciente; el mapa sí lo pinta en rojo (contradicción).
4. [V] media · T14 · `smc/gap.py:199`, `report_html._verticales`: VRT-NET aparece «evaluada 5» aunque no entra en la media cuando puntúan sus subverticales.
5. [V] media · T09 · `soc/verticals.yaml`: `criterios` es una lista de comprobaciones, no un baremo 0-5.
6. [V] baja · T09: mapeos ENS dudosos (VRT-EDR con mp.eq.3 en lugar de op.exp.6; VRT-ENDUSER con mp.sw.2 en lugar de op.exp.4).
7. [V] baja · T10/T15: firewalls de la plantilla con `vertical: VRT-NET` en lugar de VRT-FW.
8. [V] baja · T13 · `smc/mitre.py:65`, `smc/soc.py:106`: madurez por táctica = máximo (oculta huecos), mezcla casos no activos y no sale en el CLI.
9. [V] baja · T10 · `smc/tech.py:89-93, 208`: `coste_anual` no numérico suma 0 sin aviso.
10. [V] baja · T14: Markdown de verticales conserva `<script>` en `motivo` (el HTML sí escapa).
11. [V] baja · T14: tests de T05/T06 modificados fuera de «Toca» (justificado y anotado).
12. [V] baja · T15: el informe atribuye el gris a TEC-0001; en la ejecución real es AST-0001.
13. [V] baja · T11: INCIBE-CERT y CCN-CERT son listados, no búsquedas; SSH y OPC UA citan ENS-op.exp.10 (discrepancia op.exp.10/11 ya anotada).
14. [D] baja · T11: búsqueda de CVE Details no verificable de forma automática (Cloudflare).

## Comprobado sin defectos
`yaml.safe_load` en todo; sin red ni subprocess; HTML solo con `https://` y escapado; JSON del mapa por lista blanca (sin rutas, propietario ni coste); sin enlaces a repos privados; IDs ATT&CK y CWE correctos; sin CVEs concretos; `no_evaluable` no puntúa ni desaparece; umbrales con `hoy` inyectado y contraprueba real.

## Objetivo
Cubre verticales Threat Hunting, EDR/XDR, MDM, puesto, FW, SASE, ZTNA y capas OSI; reglas con «no evaluable» y motivo; suscripciones; playbooks y madurez MITRE con Navigator; 28 protocolos con fuentes oficiales; 17 RSS con OPML; contrato del mapa. Sin cubrir: visor 3D; tecnologías, reglas, suscripciones y MITRE en el informe HTML y el dashboard; vertical GRC propia; evaluación ZTNA y repo de vulnerabilidades por capa OSI.

Tareas a reabrir: ninguna. Hallazgos 1-10 y 12 van a T17.
