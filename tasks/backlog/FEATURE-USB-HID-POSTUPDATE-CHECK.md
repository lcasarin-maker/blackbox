---
id: FEATURE-USB-HID-POSTUPDATE-CHECK
kind: task
domain: USB
title: "Detect USB-HID perdido tras actualización de kernel o driver"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_usb_hid_postupdate --evidence tasks/evidence/FEATURE-USB-HID-POSTUPDATE-CHECK", "expect": "exit_zero", "porque": "El cierre debe separar fallo USB-HID real, máquina headless, módulo integrado en kernel y telemetría inaccesible; comprobar que el servicio sigue activo no demuestra que el teclado ni el acceso remoto funcionen."}
---

## Fuente y alcance de la evidencia

NVIDIA forum, [DGX Spark: Keyboard and Mouse Not Working After NVIDIA Driver Upgrade / DPKG Interruption](https://forums.developer.nvidia.com/t/dgx-spark-keyboard-and-mouse-not-working-after-nvidia-driver-upgrade-dpkg-interruption/348453), posts 1–3. El autor original reporta DGX Spark con DGX OS basado en Ubuntu 22.04; al ejecutar `apt-get upgrade`, `dpkg --configure -a` y `apt --fix-broken install`, observó errores de dependencias en `linux-modules-nvidia-550-open`, `nvidia-hwe` y `nvidia-driver-580-open`. Tras reiniciar, la pantalla de login funcionaba, pero USB HID y SSH no. Otro usuario reporta un síntoma similar y dice que `modprobe usbhid; modprobe hid_generic; reboot` lo corrigió. No fija la versión completa de OS/kernel/driver ni demuestra causa común para ambos casos.

## Hueco de Blackbox

`FEATURE-USB-XHCI-FORENSICS` busca muerte del controlador xHCI y enumera velocidades USB. Esa señal no detecta por sí sola que falten `usbhid`/`hid_generic` mientras el host llega al login. La ficha 348453 describe una pérdida simultánea de interacción local y red, que puede dejar al operador sin forma de recuperar la máquina. Blackbox todavía no identifica un USB-HID ausente como síntoma separado ni ata fallos de módulos a una transacción de actualización.

## Prevención y corrección candidatas

Reutilizar el estado de DPKG/APT, journal del kernel y sysfs existentes para registrar paquetes en estado incompleto, errores de carga HID y presencia de dispositivos de entrada. Evaluar una comprobación de salida tras actualizaciones de kernel/driver: dependencias consistentes, módulos disponibles para el kernel que arrancará y recuperación mediante el kernel anterior cuando una actualización deja módulos esenciales sin resolver. El paquete y firmware son específicos del OEM; el relato disponible corresponde a DGX Spark y no valida la receta para ASUS GX10, Gigabyte AI TOP ATOM ni para la pila actual de esta máquina.

`modprobe usbhid`/`hid_generic` es una pista de recuperación del segundo usuario, no una solución general verificada. No auto-cargar, purgar ni reinstalar drivers hasta probar que el módulo está ausente y que el kernel/device realmente lo requiere.

## Riesgos y criterio de cierre

Un host sin teclado (headless) puede ser normal; algunos kernels integran controladores en vez de exponerlos en `lsmod`. Una regla que exija siempre módulos visibles o teclado local produciría falsas alarmas. Prueba controlada en fixtures de módulo cargado, módulo integrado, módulo ausente, no hay dispositivo de entrada conectado, DPKG roto y kernel sano. Incluye una actualización segura en laboratorio y un caso negativo de xHCI vivo con HID ausente. Para cualquier corrección automática, registra disparador, escalada segura, rollback al kernel anterior y resultado del acceso local/remoto; no prueba la protección con interrupciones destructivas en el equipo de uso.


## Avance de instrumentación 2026-10-03

`tools.host_diagnostics` ahora relaciona entradas HID con el USB ancestro más cercano y conserva fallos de telemetría como `could_not_run`; la captura disponible no observó entradas HID. El avance y la limitación están documentados en [BB-INSTRUMENTS-devices](../../docs/evidence/BB-INSTRUMENTS-devices.md). La ficha sigue abierta y el close_check original permanece pendiente.


## Defecto de entrada CLI detectado (2026-10-04)

La ejecución literal del close_check termina con código 0 y stdout vacío porque el módulo tiene API `verify` pero carece de entrada `main/__main__`. La llamada API sobre la misma captura devuelve UNKNOWN; el código de salida actual no acredita cierre. Recibo: `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/direct-29-original-close-current-run.json`.

El agente hardware tiene asignada la entrada CLI con JSON literal y códigos 0/1/2 para PASS/FAIL/UNKNOWN, respectivamente; el código 0 exige could_not_run=0. Se requieren pruebas de proceso real para la captura ausente, argumentos y controles positivos/negativos. El close_check se conserva y la ficha sigue abierta.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: El estado de host no demuestra teclado/HID operativo post-update ni distingue módulo integrado/headless/telemetría inaccesible.
- Evidencia faltante para cierre: dispositivo HID conectado/descriptor; interacción local/remota; kernel/module binding; estado headless y rollback
- Siguiente acción: En un nodo canary con acceso alternativo, probar HID sano y controles headless/módulo/telemetría después de update y guardar recuperación.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/FEATURE-USB-HID-POSTUPDATE-CHECK.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_05.json`, `tasks/evidence/FEATURE-USB-HID-POSTUPDATE-CHECK/host-observation.txt`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
