<div align="center">

<a href="https://pedri77.github.io/smc-cinematica/"><img src="docs/img/radar.gif" alt="Radar de SMC barriendo el perímetro de una organización mientras se encienden los controles NIS2" width="100%"></a>

# Security Manager Control

**Todo el perímetro, en una sola pantalla.**

Qué exige la normativa a cada cliente, qué tiene ya implantado, con qué evidencias y qué falta, priorizado.<br>
NIS2 · ENS · ISO 27001 · SOC · tecnologías · vulnerabilidades. En local, sin servidor y sin que los datos salgan de tu equipo.

[![versión](https://img.shields.io/badge/versión-0.4.1-3cf58a?style=for-the-badge&labelColor=07090c)](CHANGELOG.md)
[![tests](https://img.shields.io/badge/tests-78%20en%20verde-3cf58a?style=for-the-badge&labelColor=07090c)](tests/)
[![python](https://img.shields.io/badge/python-3.10+-3cf58a?style=for-the-badge&logo=python&logoColor=3cf58a&labelColor=07090c)](pyproject.toml)
[![dependencias](https://img.shields.io/badge/dependencias-solo%20PyYAML-3cf58a?style=for-the-badge&labelColor=07090c)](pyproject.toml)

[![NIS2](https://img.shields.io/badge/NIS2-15%20controles-ffb020?style=flat-square&labelColor=07090c)](frameworks/nis2/controls.yaml)
[![ENS](https://img.shields.io/badge/ENS-73%20medidas-ffb020?style=flat-square&labelColor=07090c)](frameworks/ens/controls.yaml)
[![Transversal](https://img.shields.io/badge/ISO%2027001%20·%20RGPD%20·%20DORA%20·%20CIS-21%20controles-ffb020?style=flat-square&labelColor=07090c)](frameworks/transversal/controls.yaml)
[![Red](https://img.shields.io/badge/red-20%20controles-ffb020?style=flat-square&labelColor=07090c)](network/controls.yaml)
[![MITRE](https://img.shields.io/badge/MITRE%20ATT%26CK-cobertura%20por%20táctica-ff4d4d?style=flat-square&labelColor=07090c)](soc/use-cases/catalog.yaml)
[![soberanía](https://img.shields.io/badge/soberanía-ejecución%20local%20UE-5ad1ff?style=flat-square&labelColor=07090c)](docs/adr/ADR-001-catalogos-como-datos-y-datos-de-cliente-fuera-del-repo.md)

[**Ver la web**](https://pedri77.github.io/smc-cinematica/) · [Empezar en 1 minuto](#empezar-en-1-minuto) · [Comandos](#comandos) · [PRD](docs/prd/PRD-SMC-001-v1.md) · [Changelog](CHANGELOG.md)

</div>

---

## El problema

El Security Manager, el CISO o el consultor GRC que lleva varios clientes no tiene una vista única que responda a cuatro preguntas: **¿qué me exige la normativa, qué tengo, con qué evidencia y qué me falta?** La respuesta está repartida entre hojas de cálculo, informes de auditoría, consolas de seguridad y contratos con proveedores.

SMC lo junta en un único sitio: catálogos de controles versionados como datos, una evaluación por cliente y un CLI que calcula el cumplimiento, cruza marcos, prioriza brechas y entrega el informe.

<p align="center">
  <img src="docs/img/brechas.png" alt="Brechas detectadas como ecos rojos en el radar y ordenadas por prioridad P1, P2 y P3" width="100%">
</p>

## Cómo funciona

```mermaid
flowchart LR
    A["🧭 Perfil del cliente<br/><sub>sector · tamaño · sector público · categoría ENS</sub>"] --> B["📚 Marcos aplicables<br/><sub>NIS2 siempre · ENS si aplica<br/>transversal · red</sub>"]
    B --> C["✅ Evaluación con evidencias<br/><sub>implementado · parcial<br/>no implementado · no aplica</sub>"]
    C --> D["🚨 Brechas priorizadas<br/><sub>P1 · P2 · P3</sub>"]
    D --> E["🗓️ Plan de acción<br/><sub>responsable · fecha · vencidas</sub>"]
    E --> F["📊 Informe HTML<br/>y dashboard multicliente"]

    style A fill:#0d1117,stroke:#5ad1ff,color:#e6edf3
    style B fill:#0d1117,stroke:#5ad1ff,color:#e6edf3
    style C fill:#0d1117,stroke:#3cf58a,color:#e6edf3
    style D fill:#0d1117,stroke:#ff4d4d,color:#e6edf3
    style E fill:#0d1117,stroke:#ffb020,color:#e6edf3
    style F fill:#0d1117,stroke:#3cf58a,color:#e6edf3
```

<p align="center">
  <img src="docs/img/flujo.png" alt="Pista de circuito con los seis pasos: perfil, marcos, evaluación, brechas, plan e informe" width="100%">
</p>

1. **Alcance.** Copia `assessments/assessment.template.yaml` y rellena el perfil del cliente.
2. **Marcos.** NIS2 siempre; ENS si `sector_publico` o `proveedor_sector_publico`, filtrado por su categoría (BÁSICA, MEDIA, ALTA); transversal y red siempre.
3. **Evaluación.** Estado de cada control y sus evidencias. Un control `implementado` sin evidencia sale como aviso: evidencia antes que checkbox.
4. **Brechas.** `smc gap` calcula el cumplimiento por marco y ordena lo que falta por prioridad.
5. **Plan.** `plan_accion:` en la evaluación y `smc plan` para ver acciones vencidas y brechas P1 sin acción.
6. **Entrega.** `smc report` para dirección (HTML imprimible a PDF) y `smc dashboard` para todos tus clientes.

## Tres marcos, una sola rejilla

Evalúa una vez y reutiliza. El mapeo `mappings/nis2-ens-iso27001.csv` cruza cada control NIS2 con sus medidas ENS y los controles del Anexo A de ISO 27001:2022. Si un control no está evaluado pero su equivalente sí, el informe lo marca como **heredado** para que no se te escape.

<p align="center">
  <img src="docs/img/marcos.png" alt="Las rejillas de NIS2, ENS e ISO 27001 superpuestas con un control común iluminado" width="100%">
</p>

| Bloque | Base | Cuándo aplica |
|---|---|---|
| **NIS2** | Directiva (UE) 2022/2555, art. 20, 21 y 23 + Reglamento de Ejecución (UE) 2024/2690 | Línea base para **todos** los clientes (entidad esencial, importante o como referencia voluntaria) |
| **ENS** | Real Decreto 311/2022, Anexo II (73 medidas) con categoría mínima y refuerzos | Sector público y sus proveedores |
| **Transversal** | ISO/IEC 27001:2022, RGPD/LOPDGDD, DORA, CIS Controls v8 | Cualquier organización |
| **Red** | Módulo propio | Segmentación, perímetro, acceso remoto, DNS, Wi‑Fi, OT, monitorización |
| **Normativa** | NIS2 completa + CCN-CERT | Directiva, RE 2024/2690, guía de ENISA, anteproyecto español; guías CCN-STIC, BP e ITS enlazadas a controles (`smc refs`) |

### Priorización

```
prioridad = 50·estado + 30·criticidad + 10·entidad + 10·cobertura multinorma
P1 ≥ 75 · P2 ≥ 40 · P3 resto
```

Estado: no implementado 1, sin evaluar 0,75, parcial 0,5. Entidad: esencial 1, importante 0,5, otra 0. Un no implementado de criticidad alta en una entidad esencial es P1; uno de criticidad media en una entidad importante sin cobertura multinorma, P2.

## Toda la sala, no solo el cumplimiento

<p align="center">
  <img src="docs/img/modulos.png" alt="Carrete de módulos: SOC, tecnologías, vulnerabilidades, red, normativa y dashboard" width="100%">
</p>

| Módulo | Qué mide | Dónde |
|---|---|---|
| 🛰️ **SOC** | SLA por severidad y tier, MTTD, MTTA, MTTC, MTTR | `smc soc` |
| 🎯 **MITRE ATT&CK** | Cobertura de casos de uso por táctica | `smc mitre` |
| 🧩 **Verticales** | 12 verticales (EDR/XDR, IAM, red, correo, cloud, datos, copias, OT…) clasificadas por medida NIS2 21.2 | `soc/verticals.yaml` |
| 🔑 **Tecnologías** | Licencias, fin de soporte, certificados, sobredespliegue | `smc expiring` |
| 🩹 **Vulnerabilidades** | CVEs con SLA de remediación (KEV, EPSS, CVSS) y playbooks por tecnología y caso de uso | `smc vulns` |
| ⚖️ **Normativa** | Base legal y guías CCN-CERT de cualquier control | `smc refs` |

## Lo que entregas

<table>
  <tr>
    <td width="50%"><img src="docs/img/informe.png" alt="Informe HTML de brechas con resumen ejecutivo, barras de cumplimiento y top de brechas P1"></td>
    <td width="50%"><img src="docs/img/dashboard.png" alt="Dashboard multicliente con cumplimiento por marco, brechas P1, acciones vencidas y semáforo"></td>
  </tr>
  <tr>
    <td><b>Informe HTML</b> para dirección (responsabilidad NIS2 art. 20): resumen ejecutivo, brechas P1, plan de acción y avisos. Un solo fichero, imprimible a PDF.</td>
    <td><b>Dashboard multicliente</b>: cumplimiento por marco, brechas P1, acciones vencidas y semáforo por cliente. Estático, sin servidor.</td>
  </tr>
</table>

<sub>Capturas generadas con los dos ejemplos ficticios del repositorio. Salen en rojo porque la mayoría de sus controles están sin evaluar, que puntúan como no cumplidos.</sub>

## Empezar en 1 minuto

```bash
git clone https://github.com/pedri77/security-manager-control.git
cd security-manager-control
pip install -e .

smc validate                                                     # catálogos OK
smc gap assessments/examples/ejemplo-ayuntamiento.yaml           # brechas en Markdown
smc report assessments/examples/ejemplo-ayuntamiento.yaml -o /tmp/informe.html
smc dashboard assessments/examples -o /tmp/panel                 # abre /tmp/panel/index.html
```

## Comandos

```bash
smc validate                                              # valida catálogos
smc list                                                  # controles por marco
smc gap <evaluación.yaml> [-o informe.md] [--hoy AAAA-MM-DD]
smc plan <evaluación.yaml> [--hoy AAAA-MM-DD]             # vencidas y brechas sin acción
smc report <evaluación.yaml> -o informe.html [--hoy AAAA-MM-DD]
smc dashboard <dir_evaluaciones> -o <dir_salida> [--hoy AAAA-MM-DD]
smc soc soc/incidents.template.csv                        # MTTD/MTTA/MTTC/MTTR y % SLA
smc mitre                                                 # cobertura ATT&CK
smc expiring technologies/registry.template.yaml --days 90
smc vulns vulnerabilities/tracker.template.csv            # CVEs abiertos y fuera de SLA
smc refs NIS2-21.2.b                                      # normativa y guías CCN-CERT
smc --version
```

Estados de control: `implementado` (1,0) · `parcial` (0,5) · `no_implementado` (0) · `no_aplica` (excluido) · sin evaluar (0, listado aparte; un estado no válido se trata igual, con aviso). Una acción `bloqueada` o `hecha` no cubre una brecha abierta.

## Los datos del cliente no salen de tu equipo

<p align="center">
  <img src="docs/img/cierre.png" alt="Muro de controles en verde y bloque de soberanía del dato" width="100%">
</p>

- **Datos de clientes fuera del repositorio** ([ADR-001](docs/adr/ADR-001-catalogos-como-datos-y-datos-de-cliente-fuera-del-repo.md)). `.gitignore` excluye evaluaciones reales, `*.html` y `dashboard/` como red de seguridad. Escribe las salidas fuera del repo.
- **Ejecución local u on-prem en la UE.** Sin llamadas de red, sin telemetría.
- **Informes autocontenidos** ([ADR-002](docs/adr/ADR-002-informes-html-y-dashboard-estatico.md)): CSS en línea, sin JavaScript, fuentes ni recursos externos. Todo texto de la evaluación se escapa.
- **Catálogos como datos.** Actualizar un marco es un PR sobre YAML, revisable sin tocar código. Los IDs (`NIS2-21.2.a`, `ENS-op.acc.6`, `TRV-RGPD-01`, `NET-SEG-01`) son contrato: no se renombran, se deprecan.

## Estructura

```
security-manager-control/
├── frameworks/          nis2 · ens · transversal (controls.yaml)
├── mappings/            nis2-ens-iso27001.csv
├── network/             módulo de red
├── normativa/           NIS2 completa · guías CCN-CERT
├── soc/                 SLA · métricas · verticales · casos de uso MITRE
├── technologies/        registro de tecnologías
├── vulnerabilities/     política · tracker · playbooks
├── resources/           inventario interno y de terceros
├── assessments/         plantilla + ejemplos ficticios
├── smc/                 CLI (gap, plan, report, dashboard, soc, mitre…)
├── tests/               78 tests
└── docs/                PRD · ADR · plan del enjambre · imágenes
```

## Hoja de ruta

| Versión | Entregable | Estado |
|---|---|---|
| v0.1 | Catálogos YAML, plantillas, `smc gap` | ✅ |
| v0.2 | Aplicabilidad ENS por categoría, priorización por riesgo, mapeos completos | ✅ |
| v0.3 | Informe HTML/PDF y plan de acción | ✅ |
| v0.4 | Dashboard multicliente (estático, local) | ✅ |
| v0.5 | Verticales ampliadas (Threat Hunting, MDM, puesto, SASE/ZTNA), evaluación de tecnologías y suscripciones, vulnerabilidades por protocolo, madurez MITRE con playbooks, conectores de evidencias, ingesta NVD/KEV/EPSS | 🛠️ |

## Limitaciones conocidas

> [!WARNING]
> **ENS pendiente de contrastar.** 39 de las 73 medidas llevan `verificar: true`: su categoría mínima y sus refuerzos se rellenaron sin la tabla del Anexo II del RD 311/2022 delante. Los informes las marcan con «(verificar)» y avisan en el resumen. Hay además una posible discrepancia de ID (`op.exp.10` / `op.exp.11`) y de numeración en `mp.info`.

- Las criticidades NIS2 son un juicio inicial sin fuente normativa: afectan al orden de prioridad, no al cumplimiento.
- «Sin evaluar» puntúa como no cumplido: una evaluación incompleta sale en rojo. Es lo esperado; el informe separa las brechas evaluadas de las pendientes.
- La ley española de transposición de NIS2 (*Anteproyecto de Ley de Coordinación y Gobernanza de la Ciberseguridad*) sigue en tramitación: revisar el catálogo cuando se publique en el BOE.

---

<div align="center">

<a href="https://pedri77.github.io/smc-cinematica/"><img src="https://img.shields.io/badge/ver%20la%20sala%20de%20control-pedri77.github.io%2Fsmc--cinematica-3cf58a?style=for-the-badge&labelColor=07090c" alt="Ver la web"></a>

<sub>Hecho por <a href="https://github.com/pedri77">pedri77</a>. Construido con un enjambre de agentes: el plan y los informes de cada tarea están en <a href="docs/plan/">docs/plan</a>.</sub>

</div>
