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

### Simulación local capturada (2026-10-03)

Se repitieron las dos simulaciones que consume `tools.verify_apt_critical_removals.py` en el host arm64 actual. `apt-get -s -o Debug::NoLocking=1 upgrade` produjo cero removals; la simulación inocua pasa. `apt-get -s -o Debug::NoLocking=1 remove nvidia-system-station` programa la remoción del metapaquete; la simulación crítica se clasifica `block`. Capturas crudas y hash: `tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/apt-captures.json` y `apt-captures.sha256`. El verificador retorna `status=pass`, `fail=0`, `could_not_run=0`; esto prueba discriminación del instrumento sobre estos dos planes actuales. La simulación lista componentes del escritorio como candidatos de autoremove al proponer la remoción explícita del metapaquete. La ficha permanece abierta: no existe guard APT integrado y no se ha verificado la cobertura OEM. No se aplicó ninguna transacción.

## Progreso de preflight (2026-10-02)

Se implementó el chequeo de solo lectura `python3 -m tools.preflight apt <snapshot.json>`; exige código de salida cero, stderr vacío, un resumen APT completo con número de `Remv` coincidente y una lista crítica no vacía. Reconoce sufijos multiarch. El negativo sintético bloquea `nvidia-system-station:arm64`; una transacción cero-remociones pasa. La simulación local con `LC_ALL=C apt-get -s autoremove` propone quitar `nvidia-firmware-580-580.173.02`; la verificación de propiedad/dependencia muestra que el módulo y `nvidia-kernel-common-580` usan `nvidia-firmware-580-580.178.04`, por lo que el plan actual pasa bajo la lista crítica observada. Salidas crudas: `tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/commands.json`; evaluación: `preflight.json` y `validator-run.json`.

La ficha sigue abierta: `aisleriot` no está instalado para reproducir el plan del hilo, `apt-get check` no pudo obtener el lock en esta ejecución, no hay guard integrado en el flujo APT y falta confirmar la cobertura del arreglo entre OEMs mantenidos. No se aplicó ningún cambio de paquetes.

### Delta de firmware y kernel en transacciones APT

**DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.** En ASUS GX10 PSID NVD0000000087, el dueño atribuye a `dpkg --configure -a`/`mlnx-fw-updater 25.10-1.7.1.0` un flash CX7 de 28.45.4028 a 28.47.1088; después informa ambas NIC en `pre-init`, timeout `-110` y ninguna recuperación con reinstalación. NVIDIA dice que ingeniería sigue investigando. Los logs, `mstdump` y el diagnóstico adjunto no se leyeron, por lo que mecanismo y causalidad siguen sin confirmación ([373900](https://forums.developer.nvidia.com/t/373900)). Hacer que el preflight detecte escrituras de firmware CX7 invocadas indirectamente, verifique OEM/PSID/versión exacta, prerequisitos BME/DMA y canal firmado autorizado, y falle cerrado si falta evidencia. Ensayar primero en hardware reemplazable con captura pre/post y ruta de recuperación; nunca flashear para reproducir.

Como segundo disparador de la misma ficha: En MSI EdgeXpert, la actualización a kernel 6.17.0-1021 dejó un usuario sin `nvidia.ko`; participantes reportan inestabilidad tras instalar driver 595 y restaurar firmware. NVIDIA indica explícitamente que 595 no está soportado para Spark y recomienda mantener la rama 580 oficial; otro dueño reporta 6.17.0-1021 con 580.159.03 funcional ([371799](https://forums.developer.nvidia.com/t/371799)). Añadir regla por SKU/OEM que compruebe kernel, módulo construido/cargable y driver oficialmente soportado antes de aceptar la transacción. El relato no prueba que 595 causara cada fallo; validar simulación y rollback en canary.

**DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01.** En DGX Spark/Noble arm64, un dueño publicó `ubuntu.sources` mezclando `archive.ubuntu.com` (404 en binary-arm64) y `ports.ubuntu.com`; soporte NVIDIA indicó `ports.ubuntu.com/ubuntu-ports` como fuente Ubuntu esperada. En paralelo, un PPA NVIDIA Vulkan reportó tamaño/hash inesperado durante sincronización de espejo, y otro usuario luego obtuvo `apt update` limpio. El autor dijo que retirar el archivo con source incorrecta restauró apt, pero sincronización y cambio de source no quedan aislados ([355471](https://forums.developer.nvidia.com/t/355471)). Validar perfil de repos aprobado y frescura/integridad de índices antes de upgrades; no borrar fuentes automáticamente ni continuar sobre índices stale.


## Índice de propuestas del lote 00

- `FORUM-00-FIELDDIAG-DOCA-OFED-SPARK-GATE` — [Block FieldDiag DOCA-OFED prerequisites that replace the Spark inbox ConnectX-7 driver stack](https://forums.developer.nvidia.com/t/381767); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-METAPACKAGE-REMOVE-AUTOREMOVE` — [DGX OS removal simulation for metapackage dependency cascades](https://forums.developer.nvidia.com/t/dgx-spark-dont-remove-games/348170); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.

## Revisión de reutilización — 2026-10-03

El nuevo `tools/apt_sources.py` se limita a identidad de fuentes y tuples de índices; el preflight y su verificador existentes siguen siendo los instrumentos para clasificar planes benignos y remociones críticas. La nueva captura no sustituye evidencia de planes, y no se aplicó transacción. Se conserva el estado abierto que ya documenta la falta de guard APT integrado y de cobertura OEM.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `missing_history`.
- Impedimento: El recibo declara que el paquete aisleriot del caso fuente está ausente, apt-get check no pudo correr y no hay recibo de la simulación crítica del caso sujeto; también falta el guard de invocación APT en el repo.
- Evidencia faltante para cierre: Transacción APT peligrosa simulada con remoción crítica interceptada antes de aplicar y transacción inocua permitida, ambas capturadas con salida literal; el simulador usa el estado de paquete/índices pertinente.
- Siguiente acción: Completar el guard de invocación APT en el punto de transacción existente para bloquear/declarar remoción crítica; demostrar con simulación segura del plan peligroso y transacción inocua, conservando evidencia cruda y sin aplicar cambios.
- Responsable del siguiente paso: BB.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD.md`, `tools/preflight.py`, `tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD`, `tools/verify_apt_critical_removals.py`, `tests/test_debt_registration_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Medición del grafo corregido — 2026-10-07

Corrige la sección «Compatibilidad y estado local»: la frase «no indica vulnerabilidad vigente en esta máquina» queda refutada por la medición siguiente.

- Host: Gigabyte AI TOP ATOM, DGX OTA 7.5.0, `nvidia-system-station 2404.26.01-1` del componente `noble-updates/common` de `repo.download.nvidia.com/baseos`. El índice local conserva las dos versiones: `2404.25.10-1` lleva `aisleriot` en `Depends` (el caso del hilo 348170); `2404.26.01-1` delega en `-core`, `-common` y `-utils`, y deja `-games`, `-apps` y `-localization` en `Recommends`.
- Colector: `tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/collect_leaf_cascade.py`. Solo corre `apt-get -s -o Debug::NoLocking=1` y no aplica nada. Genera la lista de hojas desde el grafo: son las dependencias `Depends` directas, instaladas y sin alternativa de los 8 metapaquetes `nvidia-system-*` instalados, 353 en total. Cada plan lo clasifica `tools.preflight.check_apt`. Captura cruda: `leaf-cascade-captures.json`, sha256 `396169018b2a0acbee1a2223078e3d9c07fd3533a5b8ec5b78895d0960ac4886`.
- Resultado: 352 `block`, 1 `pass` (`libjuh-java`), 0 `unknown`. Los controles `upgrade` y `remove tree` dan `pass`, y prueban que el clasificador puede devolver el veredicto contrario. 197 hojas programan `Remv nvidia-system-station`, entre ellas `gparted`, `remmina`, `deja-dup`, `seahorse`, `hplip`, `orca`, `vino` y `modemmanager`. 31 programan `Remv nvidia-system-core`, entre ellas `ipmitool`, `nvme-cli` y `tpm2-tools`. `remove jq` programa 33 remociones que incluyen la cadena `station` completa y `core`.
- Lectura: la corrección de NVIDIA sacó de `Depends` los juegos, las apps y la localización. El patrón del hilo sigue presente: quitar una aplicación ordinaria arrastra el metapaquete de plataforma, y después `autoremove` ofrece el escritorio. Esta medición cae en la rama «Si persiste el riesgo» del criterio de cierre. La rama «corregido upstream, sin mecanismo propio» queda descartada.
- Pendiente de decisión de Luis: instalar o no un guard APT en el sistema. Ninguna opción está medida. `apt-mark hold` bloquearía las actualizaciones de seguridad del metapaquete, el riesgo que ya señala la sección «Riesgos». El campo `Protected:` lo fija el mantenedor, así que es una petición upstream. Un hook `DPkg::Pre-Install-Pkgs` corre antes de dpkg pero no se ejecuta bajo `apt-get -s`, así que demostrarlo exige instalarlo en un canario con transacción real y su rollback.
- OEM: el metapaquete sale del componente compartido `common`. Desde este host no se verificó si los otros OEM consumen ese mismo componente y esa versión.
- Fuente: los archivos `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/threads/348170.{json,txt}` que cita la sección «Fuente» no existen en el repo. Se usó el resumen de `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- Defecto del gate: el `close_check` (`exit_zero`) sale 0 hoy con `"closure": "open"`, porque `tools/verify_apt_critical_removals.py` escribe `closure` y `open_blockers` como literales y su código de salida solo refleja la discriminación del instrumento. Un gate que solo mira el código de salida aceptaría esta ficha como cerrada. No se cambió: `tests/test_debt_registration_controls.py::test_apt_critical_verifier_cli_and_evidence_controls` fija `rc=0` con `closure` abierta (ficha `DEBT-CLOSE-CHECK-VERIFY-APT-CRITICAL-REMOVALS-01`).
