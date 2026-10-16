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
close_check: {"cmd": "python3 -m tools.verify_apt_critical_removals --cierre --evidence tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD", "expect": "exit_zero", "porque": "El cierre requiere demostrar que una remoción simulada peligrosa se bloquea o se declara antes de aplicar cambios, y que una transacción inocua sigue disponible; un inventario estático de paquetes no demuestra protección."}
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

## Defecto del close_check corregido (2026-10-13)
El CLI daba exit 0 (`status: pass`) mientras su propia salida declara `closure: open` y `open_blockers` (cobertura OEM y guarda APT instalada sin verificar): el `close_check` de esta ficha pasaba con la ficha abierta. Se anade `--cierre` (sale 2 si hay bloqueos abiertos) y el `close_check` lo usa; sin la bandera el comportamiento no cambia (la ficha cerrada `DEBT-CLOSE-CHECK-VERIFY-APT-CRITICAL-REMOVALS-01` sigue reproduciendo). Antes: rc=0; despues: rc=2; control: con `closure: closed` simulado sale 0 (`tests/test_debt_registration_controls.py::test_apt_critical_removals_flag_cierre_no_sale_0_con_bloqueos_abiertos`).

## Avance — guardia por script sellado de root (2026-10-14)

Luis autorizo el 2026-10-14 "un guardia por script sellado de root". Construido, sin desplegar:

- Lista: `data/apt-paquetes-criticos.txt`, 30 nombres medidos hoy en el host (`dpkg -l`, `apt-mark showhold`: `dgx-spark-ota-update-meta`; `GRUB_DEFAULT` = 6.17.0-1032-nvidia): los 8 `nvidia-system-*`, `dgx-release`, `dgx-repo`, `dgx-spark-mlnx-hotplug`, `dgx-spark-ota-update-meta`, `dgxstation-desktop`, `dgxstation-grub`, `gigabyte-oobe-customize`, `linux-image-`/`linux-modules-`/`linux-modules-nvidia-580-open-6.17.0-1032-nvidia`, `nvidia-driver-580-open`, `nvidia-kernel-common-580`, `grub-common`, `grub-efi-arm64`, `-bin`, `-signed`, `grub2-common`, `shim-signed`, `gdm3`, `network-manager`, `ubuntu-desktop`, `ubuntu-desktop-minimal`. Los 30 estan instalados (fila `criticos_instalados` de la captura). La lee `tools/verify_apt_critical_removals.py` (`CRITICAL_PACKAGES`, y el colector `collect_guard.py` de la evidencia); el hook la lleva copiada y un test exige igualdad byte a byte.
- Hook: `adopted/pendiente-de-despliegue/usr_local_sbin_bb-apt-guardia` (bash, solo builtins), registrado por `etc_apt_apt.conf.d_00-bb-apt-guardia` como `DPkg::Pre-Install-Pkgs` con protocolo 3. Sale 1 si una linea `**REMOVE**` nombra un critico (APT aborta antes de dpkg), 0 en otro caso; protocolo distinto de `VERSION 3` o stdin vacio sale 1. Excepcion por transaccion: `-o BB::Apt-Guardia::Permitir=1`. Suspension: renombrar el `.conf` a `.disabled`.
- Instalador: `adopted/root-scripts/apt-guardia-instalar.sh` (manifiesto `apt-guardia-instalar`, timeout 300). Solo escribe sobre ausencia; contenido, dueno o modo desconocido, symlink, directorio no-root o `.disabled` presente: rc 3 sin tocar nada. Valida con APT real tras instalar y borra lo creado si falla (rc 5). Pasos de despliegue en `adopted/pendiente-de-despliegue/LEEME.txt`.
- `apt-get -s` no ejecuta hooks de dpkg, asi que la simulacion no puede probar la guardia. La prueba es una transaccion APT real (`-y remove`) sobre una caja: `APT_CONFIG` que solo carga el `.conf` de la guardia (comprobado con `apt-config` antes de transaccionar), copia de `/var/lib/dpkg/status`, `Dir::Bin::dpkg` = stub que solo anota. Corre sin root.

Medido hoy, sin root, con el hook del repo (`python3 tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/collect_guard.py --out tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD`, captura `apt-guard-captures.json` + `.sha256`):

```
criticos_instalados: rc=0 dpkg_remove=False
config: rc=0 dpkg_remove=False
autoremove_simulado: rc=0 dpkg_remove=False
remove_critico: rc=100 dpkg_remove=False
remove_inocuo: rc=0 dpkg_remove=True
```

`remove nvidia-system-station` aborta con rc 100 y "bb-apt-guardia: esta transaccion quita paquetes criticos de la plataforma: nvidia-system-station", y el stub de dpkg no recibe `--remove`. `remove tree` (control: no critico) llega al stub con `--remove tree:arm64`. `apt-get -s autoremove` con la configuracion real: 0 remociones, `check_apt` = pass. `caja-strace.txt` (colector `strace_caja.py`): en las dos transacciones, 0 escrituras fuera de la caja salvo 25 `O_TMPFILE` anonimos en `/tmp`; el dpkg real solo se invoca como `dpkg --print-foreign-architectures`. Control negativo del filtro: `touch <fuera>` da 1 escritura detectada.

Verificador: `python3 -m tools.verify_apt_critical_removals --evidence tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD` sale 0 con `checks.installed_guard = "pre_deployment"` y dos `open_blockers` (OEM; guardia instalada sin verificar). `--cierre` sale 2. El campo nuevo `checks.installed_guard` solo dice `verified` con una captura `instalado: true` que leyo `/etc/apt/apt.conf.d/00-bb-apt-guardia` y `/usr/local/sbin/bb-apt-guardia`, con sha256 iguales a los del script sellado, la configuracion real registrando el hook, y las dos transacciones discriminando. Doce mutaciones de una captura instalada valida mantienen el bloqueo (`tests/test_apt_guardia.py::test_control_negativo_verificador_cada_prueba_faltante_mantiene_el_bloqueo`); seis danos de formato dan `unknown` con `could_not_run=1`.

Tests: `tests/test_apt_guardia.py` (53: hook alimentado con el protocolo 3, 12 casos; script ejecutado sobre tmp_path con APT real; verificador) y la clase estatica de `apt-guardia-instalar.sh` en `tests/test_bb_root_manifest.py` (38 formas sembradas que se cazan, 9 permitidas). Mutaciones: 18 de 18 mueren, cada una por un test de comportamiento (se excluyo el test de propuesta vieja, que mataria cualquier cambio): 11 del script, 5 del hook, 2 del verificador.

Queda abierto:
1. Guardia instalada: requiere el sudo de Luis (LEEME pasos 1-2). Despues, sin sudo: `python3 tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/collect_guard.py --instalado --out tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD` y el verificador debe dar `checks.installed_guard = "verified"`.
2. Cobertura OEM: el grafo de metapaquetes de otros OEM no se observa desde este host. `open_blockers` conserva esa fila y `--cierre` sigue en 2 aunque la guardia quede verificada.
3. La lista nombra versiones (kernel 6.17.0-1032, rama 580). `test_el_kernel_fijado_en_grub_esta_en_la_lista` falla cuando `adopted/system-config/etc_default_grub` fije otro kernel.

## Avance 2026-10-15: primera corrida real como root; la validacion fallo y se deshizo sola (reanudable)
Luis aprobo el manifiesto y corrio `sudo -n bb-root-run apt-guardia-instalar` dos veces (la segunda ya con el script que imprime el motivo). Ambas: `rc=5`, `VALIDACION FALLIDA`, y el script BORRO lo que habia creado (`/etc/apt/apt.conf.d/00-bb-apt-guardia`, `/usr/local/sbin/bb-apt-guardia` no existen: medido con `ls`). Lo que funciono: la remocion simulada de `nvidia-system-station` en la caja quedo bloqueada con el mensaje del gancho. Lo que fallo: la remocion inocua de `tree` devolvio rc 100 sin llegar al stub de dpkg; el error literal es `E: Sub-process dpkg --set-selections returned an error code (100)` / `E: Couldn't record the approved state changes as dpkg selection states`. Como usuario (donde se probo todo) APT no llega a `--set-selections`; como root si, y la caja NO lo aisla: ese paso pasa por un `dpkg` que no es el stub. Peligro anotado: si ese `dpkg --set-selections` real hubiera tenido exito habria marcado `tree` como `deinstall` en la base de dpkg REAL. Medido tras las dos corridas: `dpkg --get-selections tree nvidia-system-station` = `install` ambos (no se alcanzo el estado real). Siguiente paso: reproducir como root-en-namespace (`unshare -r`) la caja del script, hallar que `dpkg` ejecuta APT en `--set-selections`, aislarlo (la opcion de APT que desactiva el registro de selecciones o `PATH` con el stub delante en la caja) y anadir un test que corra la caja con `unshare -r` si el kernel lo permite; despues reaprobar el manifiesto y volver a correr. No instalar hasta que la caja demuestre aislamiento como root.

## Avance 2026-10-15: causa del rc 100 hallada y corregida (falta re-aprobar el manifiesto y correr como root)
Causa medida: `findmnt -no OPTIONS /run` = `rw,nosuid,nodev,noexec,...`. La caja estaba en `/run/bb-apt-guardia.XXXXXX`; como root APT llega a `dpkg --set-selections` y a `--remove` y los ejecuta por `Dir::Bin::dpkg` = el stub de la caja, que en un montaje noexec no se puede ejecutar: APT sale con 100 (su codigo cuando falla el exec), sin que el stub escriba nada. Como usuario APT no llega a ese paso, por eso solo falla como root. NO hubo riesgo para la base real: bajo `fakeroot` (que no puede escribir /var/lib/dpkg) el `--set-selections` SI pasa por el stub (`dpkg.log` lo registra), asi que nunca toca el dpkg real. Medido tras las dos corridas reales: `dpkg --get-selections tree nvidia-system-station` = `install` ambos.
Arreglo: la caja ahora es `/var/lib/bb-apt-guardia.XXXXXX` (exec permitido, directorio de root) y el script ejecuta el stub una vez (`--print-architecture`) antes de transaccionar; si no corre, falla con el motivo en vez de un rc 100 opaco. Control negativo: el mismo stub en `/run/lock` (noexec, escribible) da rc 126; en disco da rc 0. Tests: 320 pasan (apt_guardia, bb_root_manifest, bb_root_run). Siguiente paso: Luis re-aprueba el manifiesto (hash nuevo) y corre `sudo -n bb-root-run apt-guardia-instalar`.

## Avance 2026-10-16: guardia instalada y verificada; la ficha sigue abierta solo por la cobertura OEM
Luis aprobo el manifiesto de 11 scripts (`bb_root_manifest --check`: iguales 11, cambios 0) y corrio `sudo -n bb-root-run apt-guardia-instalar` (rc 0, salida en `/var/lib/bb-root-run/apt-guardia-instalar-20261016T193603.317157Z.txt`): creo `/usr/local/sbin/bb-apt-guardia` (sha256 `a7396902…`) y `/etc/apt/apt.conf.d/00-bb-apt-guardia`, y la validacion en caja paso: `remove nvidia-system-station` rc 100 abortado antes de dpkg, `remove tree` rc 0 con el stub recibiendo `--remove tree:arm64`. Recogida sin sudo (`collect_guard.py --instalado`): `remove_critico` rc 100 sin llegar a dpkg, `remove_inocuo` rc 0 con dpkg_remove, `apt-config dump` trae 3 referencias a la guardia. `verify_apt_critical_removals --cierre`: `installed_guard = verified`, `captured_critical_removal = block`, `captured_upgrade = pass`; `--cierre` sale 2 (closure: open) porque `open_blockers` conserva "OEM coverage unverified: other OEM bundles' metapackage graphs are not observable from this host". Ese limite sigue vigente: la lista de paquetes criticos sale de ESTE equipo (kernel 6.17.0-1032, rama 580) y otros OEM podrian traer metapaquetes distintos.
