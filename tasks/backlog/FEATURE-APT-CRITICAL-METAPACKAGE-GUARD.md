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

## Progreso de preflight (2026-10-02)

Se implementó el chequeo de solo lectura `python3 -m tools.preflight apt <snapshot.json>`; exige código de salida cero, stderr vacío, un resumen APT completo con número de `Remv` coincidente y una lista crítica no vacía. Reconoce sufijos multiarch. El negativo sintético bloquea `nvidia-system-station:arm64`; una transacción cero-remociones pasa. La simulación local con `LC_ALL=C apt-get -s autoremove` propone quitar `nvidia-firmware-580-580.173.02`; la verificación de propiedad/dependencia muestra que el módulo y `nvidia-kernel-common-580` usan `nvidia-firmware-580-580.178.04`, por lo que el plan actual pasa bajo la lista crítica observada. Salidas crudas: `tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/commands.json`; evaluación: `preflight.json` y `validator-run.json`.

La ficha sigue abierta: `aisleriot` no está instalado para reproducir el plan del hilo, `apt-get check` no pudo obtener el lock en esta ejecución, no hay guard integrado en el flujo APT y falta confirmar la cobertura del arreglo entre OEMs mantenidos. No se aplicó ningún cambio de paquetes.
