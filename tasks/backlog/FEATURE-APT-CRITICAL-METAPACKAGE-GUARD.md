---
id: FEATURE-APT-CRITICAL-METAPACKAGE-GUARD
kind: task
domain: OS
title: "Validar protección frente a autoremove de paquetes críticos"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_apt_critical_removals --evidence tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD", "expect": "exit_zero", "porque": "El cierre requiere demostrar que una remoción simulada peligrosa se bloquea o se declara antes de aplicar cambios, y que una transacción inocua sigue disponible; un inventario estático de paquetes no demuestra protección."}
---

## Fuente

NVIDIA forum, [DGX Spark - don't remove games?](https://forums.developer.nvidia.com/t/dgx-spark-don-t-remove-games/348170), posts 5, 7, 8, 11, 13, 17 y 18. Fetch íntegro: `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/threads/348170.json` y `.txt`.

## Problema

En una instalación DGX OS reportada, `apt remove aisleriot` propone retirar también `nvidia-system-station`. El usuario conserva la transacción y observa que `apt autoremove` ofrecería eliminar el escritorio y decenas de componentes Ubuntu/NVIDIA. Un representante de NVIDIA confirma que `nvidia-system-station` depende de `aisleriot`; anuncia que separarían los metapaquetes en una actualización futura. El hilo no documenta versión exacta del bundle que contiene el arreglo ni una verificación posterior del arreglo.

La consecuencia reportada es pérdida de sesión/desktop tras cambios ordinarios de paquetes. Blackbox captura estado de pantalla y salud del host, pero hoy no hace preflight del plan APT ni advierte que una operación propuesta borra paquetes de plataforma esenciales. `bb drift` protege archivos adoptados, no el conjunto de paquetes del sistema.

## Compatibilidad y estado local

El hilo no fija el OEM ni versión del bundle del equipo afectado. En esta máquina, `nvidia-system-core` y `nvidia-system-station` están instalados en `2404.26.01-1`; `nvidia-system-desktop` y `aisleriot` no están instalados (`rc2`). La consulta local del grafo muestra que `nvidia-system-station` depende de `nvidia-system-station-core`, `-common` y `-utils`; `-games`, `-apps` y `-localization` aparecen como recomendaciones. `aisleriot` ya no es dependencia directa. El estado actual es consistente con la corrección que NVIDIA anunció en el hilo y no indica vulnerabilidad vigente en esta máquina.

## Alcance propuesto

Reproducir la resolución del hilo con una simulación de APT y verificar el mismo plan contra el grafo local vigente. Confirmar si la actualización anunciada corrigió el caso en los OEM/bundles que mantiene este proyecto. Solo si queda un caso vulnerable, evaluar controles nativos de APT antes de diseñar un guard propio. No asumir que `apt-mark manual` en `nvidia-system-station` basta: el grafo permite que una remoción explícita de un paquete requerido quite el metapaquete.

Registrar el plan de remoción, lista de paquetes críticos afectados, OS/OEM, versión del bundle DGX OS, versión del `nvidia-system-station` y resultado de cada consulta. Mantener simulación de solo lectura por defecto. Si se propone un hook bloqueante, documentar cómo se instala, deshabilita temporalmente y revierte; no interceptar transacciones con lógica opaca.

## Riesgos y validación

Un guard específico puede bloquear actualizaciones de seguridad legítimas o duplicar la protección incorporada en el paquete corregido. Validar primero con el plan vulnerable reproducido en el foro, el estado corregido de esta máquina, una remoción inocua y un control negativo; mantener el caso destructivo en simulación.

## Criterio de cierre

La evidencia determina si la versión OEM actualizada resuelve la vulnerabilidad del hilo y si hay otros paquetes críticos expuestos al mismo patrón. Si el grafo actual y las simulaciones están protegidos, registrar la decisión de no añadir mecanismo propio y cerrar la ficha. Si persiste el riesgo, la ficha define un mecanismo mínimo con simulación previa, control de falso positivo y rollback antes de proponer aplicación en sistema.

[350340](https://forums.developer.nvidia.com/t/350340) añade autoremove y simulación de instalación Flatpak con lista que incluía metapaquetes de plataforma, GRUB, NetworkManager y desktop. El autor mezcla sospechas sobre Brave y varios recoveries sin probar causa. Validar grafo actual/simulación nativa antes de decidir guard: este caso amplía cobertura de transacciones destructivas, pero no demuestra que la dependencia actual del host reproduzca el fallo. Mantener first action apt simulation sobre copia y cerrar upstream corrected si corresponde.

## Índice de propuestas del lote 00

- `FORUM-00-FIELDDIAG-DOCA-OFED-SPARK-GATE` — [Block FieldDiag DOCA-OFED prerequisites that replace the Spark inbox ConnectX-7 driver stack](https://forums.developer.nvidia.com/t/381767); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-METAPACKAGE-REMOVE-AUTOREMOVE` — [DGX OS removal simulation for metapackage dependency cascades](https://forums.developer.nvidia.com/t/dgx-spark-dont-remove-games/348170); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.

## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.

### DELTA-FORUM-CX7-FW-UPDATE-GUARD-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-CX7-FW-UPDATE-GUARD-01",
    "title": "Block unapproved unattended ConnectX firmware writes",
    "source_threads": [
      "373900",
      "371799"
    ],
    "failure": "One ASUS GX10 owner reports dpkg --configure triggering mlnx-fw-updater 25.10-1.7.1.0 from DOCA baseos8-latest, changing CX7 PSID NVD0000000087 from 28.45.4028 to 28.47.1088 despite a BME/DMA prerequisite warning; both devices then stayed in pre-init timeout -110 through OS reinstalls. NVIDIA says engineering had not reproduced. Separately, NVIDIA explicitly says driver 595 is unsupported on Spark after users report kernel/driver loss and failed boot during apt transitions.",
    "current_coverage": "APT critical package guard and kernel/initrd gate cover package graph and module presence; the reported DOCA firmware updater could flash firmware during generic package configuration, before users approve an OEM-specific update.",
    "gap_or_complement": "Fail closed on firmware writes invoked by general apt/dpkg/unattended upgrades. Allow only exact OEM/PSID/version/source combinations, enforce BME/DMA/driver readiness, block on any prerequisite warning, verify flash target and recovery bundle, and stage a tested fallback. Apply the same supported-version allowlist to driver series and require matching modules for next boot.",
    "evidence_level": "High that apt kernel/driver mismatch can remove nvidia.ko and NVIDIA stated 595 unsupported; low-to-medium for CX7 flash-to-brick causality until unread mstdump/nvidia-bug-report and engineering reproduction.",
    "risks": [
      "A firmware guard that blocks valid signed OEM updates can delay security/reliability fixes.",
      "Unofficial manual flash or package-purge recipes can strand device or void warranty."
    ],
    "closure": "Simulate apt/dpkg transactions with unsupported driver and firmware package; verify no firmware write starts, target kernel has matching supported module, unsupported OEM/PSID/version and BME-not-ready cases fail closed, approved transaction writes exact signed image, and recovery/RMA evidence is retained.",
    "backlog_card": "tasks/backlog/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD.md",
    "merge_into": "FEATURE-APT-CRITICAL-METAPACKAGE-GUARD"
  }
]
```

### DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01",
    "title": "Validate Noble arm64 APT sources and repository freshness before upgrades",
    "source_threads": [
      "355471"
    ],
    "failure": "DGX Spark Noble arm64 owners report archive.ubuntu.com arm64 404 from a mixed source file and NVIDIA PPA mirror size/hash mismatch during sync. NVIDIA support says expected Ubuntu source is ports.ubuntu.com/ubuntu-ports; owner reports apt update recovered after removing the bad sources file, while another success occurred after mirror state changed.",
    "current_coverage": "APT guard checks critical package removal and package graph; it does not verify distro-architecture source identity or repository-index freshness before upgrade.",
    "gap_or_complement": "Check approved OEM source profile for Ubuntu Noble arm64 and `ports.ubuntu.com/ubuntu-ports`, verify signed Release/index freshness and fail closed on hash/size mismatch; surface transient mirror sync separately from wrong source URI. Never auto-delete/replace sources or proceed with stale indexes.",
    "evidence_level": "High for quoted source mismatch and apt update errors; medium for recovery association, because repository sync and source removal are confounded. No package installation failure was shown.",
    "risks": [
      "Overly strict allowlist can block valid OEM/NVIDIA repositories or delay security fixes.",
      "Automatically rewriting sources could remove essential NVIDIA/ESM/other approved repositories."
    ],
    "closure": "Test exact Noble arm64 source profile on OEM canary; malformed archive URI, stale index, mirror size mismatch, invalid signature and normal transient recovery must all be distinct. Verify apt upgrade is blocked while indexes are inconsistent, approved repos remain intact, and rollback restores the prior source snapshot.",
    "backlog_card": "tasks/backlog/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD.md",
    "merge_into": "FEATURE-APT-CRITICAL-METAPACKAGE-GUARD"
  }
]
```
