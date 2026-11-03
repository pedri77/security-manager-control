# Normativa y guías de referencia

Biblioteca de referencia del SMC. Cada norma o guía se enlaza a los controles que ayuda a cumplir, de forma que desde cualquier control se pueda llegar a su base legal y a la guía práctica para implantarlo:

```bash
smc refs NIS2-21.2.b      # normas y guías asociadas a un control
smc refs ENS-mp.s.1
```

## NIS2 (`nis2/nis2.yaml`)

Se incluye el marco europeo completo **aunque España aún no lo haya transpuesto**:

| Norma | Efecto en España (nov. 2026) |
|---|---|
| Directiva (UE) 2022/2555 | Vincula al Estado; las obligaciones para entidades llegan con la ley de transposición (anteproyecto en tramitación). España incumplió el plazo del 17/10/2024 |
| Reglamento de Ejecución (UE) 2024/2690 | **Directamente aplicable** desde el 7/11/2024 a los proveedores digitales de su ámbito (DNS, TLD, cloud, CPD, CDN, MSP, MSSP, marketplaces, buscadores, redes sociales, trust services) |
| Guía técnica de ENISA (junio 2025) | No vinculante; aporta evidencias de ejemplo y correspondencias con estándares |

Incluye: artículos clave, sectores de los Anexos I y II, régimen sancionador y la estructura de 13 secciones del Anexo del Reglamento 2024/2690 enlazada con las medidas del art. 21.2.

> Para clientes que no estén obligados, NIS2 se usa como **marco de buenas prácticas**: es la línea base del SMC para todos.

## CCN-CERT (`ccn-cert/guias.yaml`)

| Bloque | Contenido |
|---|---|
| Serie CCN-STIC 800 | Guías del ENS: implantación (804), verificación (808), métricas (815), ciberincidentes (817), nube (823), INES (824/844), EELL (883), perfiles de cumplimiento 890 y 892 |
| Series 500/600 y 1400 | Bastionado y empleo seguro de productos |
| Serie 100 | Catálogo CPSTIC (105) y taxonomía (140) |
| Informes BP | 17 informes de buenas prácticas: correo, móviles, ransomware, IoT, navegadores, HTTPS, CDN, WiFi, teletrabajo, cibercrisis, Kubernetes, desarrollo seguro… |
| Instrucciones técnicas | Notificación de incidentes, INES, Guía Nacional de Notificación |

Puntos a seguir de cerca:

- **CCN-STIC 892** (perfil de cumplimiento para entidades del Reglamento 2024/2690 + ENS): la versión anterior se retiró y hay una nueva en preparación. Es la guía puente entre NIS2 y ENS.
- **CCN-STIC 890** se actualizó el 29/07/2025, pensando en la transposición de NIS2: pasa de 35 a 38 medidas para la categoría Básica.
- `verificado: false` marca las guías cuyo número y título hay que contrastar con el portal antes de citarlas a un cliente.
