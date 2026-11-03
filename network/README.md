# Módulo de Red

Apartado especial del Security Manager Control dedicado a la seguridad de red. Se evalúa siempre, con independencia del marco normativo, y cada control se relaciona con las medidas NIS2/ENS que ayuda a cumplir (`relacion` en `controls.yaml`).

## Dominios

| Dominio | Qué responde | IDs |
|---|---|---|
| Inventario | ¿Sabemos qué red tenemos? | NET-INV-* |
| Segmentación | Si cae un equipo, ¿hasta dónde llega el atacante? | NET-SEG-* |
| Perímetro | ¿Qué expone la organización a Internet y por qué? | NET-PER-* |
| Acceso remoto | ¿Cómo entran empleados y terceros? | NET-ACC-* |
| NAC / Wi‑Fi | ¿Quién puede conectarse físicamente o por radio? | NET-NAC-*, NET-WIFI-* |
| DNS | ¿Se filtra, registra y protege la resolución? | NET-DNS-* |
| Cifrado y bastionado | ¿Protocolos inseguros, credenciales por defecto? | NET-CRY-*, NET-HARD-* |
| Monitorización | ¿Vemos el tráfico y lo correlacionamos? | NET-MON-* |
| OT / IoT | ¿Está separado IT de OT? | NET-OT-* |
| Resiliencia | ¿Hay redundancia y backup de configuraciones? | NET-RES-* |

## Entradas previstas (roadmap)

- Diagramas de red (draw.io / Mermaid) en `network/diagrams/`.
- Exportaciones de reglas de firewall para revisión de reglas *any-any*, sombreadas y sin uso.
- Resultados de EASM / escaneo externo (Shodan, Censys, nmap) para contrastar con la superficie declarada.
- Matriz de flujos permitidos entre zonas.
