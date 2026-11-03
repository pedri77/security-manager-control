# PB-TEC-XXX — <Tecnología> · v1

| Campo | Valor |
|---|---|
| Tecnología | TEC-XXXX |
| Propietario | |
| Última revisión | YYYY-MM-DD |

## 1. Activación
Nuevo CVE crítico/alto, aviso del fabricante, CCN-CERT/INCIBE-CERT, o incidente que afecta a la tecnología.

## 2. Evaluación (≤ 4 h para críticas)
- [ ] ¿Versión afectada según el registro de tecnologías?
- [ ] ¿Expuesta a Internet? ¿En KEV? ¿EPSS?
- [ ] ¿Hay indicios de explotación en SIEM/EDR? (lanzar hunting)

## 3. Mitigación inmediata
- Workaround del fabricante / bloqueo en WAF/IPS / restricción de acceso.

## 4. Remediación
- Ventana de cambio · procedimiento de actualización · verificación · **rollback**.

## 5. Verificación y cierre
- [ ] Reescaneo sin hallazgo
- [ ] Registro de tecnologías actualizado (versión)
- [ ] Tracker de CVEs cerrado con fecha

## 6. Comunicación
- ¿Incidente significativo? → flujo NIS2 Art. 23 (24 h / 72 h / 1 mes).
