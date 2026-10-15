---
id: FORUM-02-USB-UVC-EP0
kind: task
domain: USB
title: "Validar y prevenir el cuelgue xHCI por controles UVC EP0 durante streaming"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "No hay dispositivo UVC aqui: lsusb muestra solo hubs raiz y el Bluetooth, uvcvideo no esta cargado y el journal del kernel retenido (desde 2026-10-13) no tiene firmas HC died / xhci halt / uvcvideo error. Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si se conecta una camara UVC y deja HC died o errores EP0 en el journal."
evidence: {"pass": "tasks/evidence/FORUM-02-USB-UVC-EP0/pass.txt", "fail": "tasks/evidence/FORUM-02-USB-UVC-EP0/fail.txt", "e2e": "tasks/evidence/FORUM-02-USB-UVC-EP0/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/FORUM-02-USB-UVC-EP0.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m tools.verify_forum_finding --id FORUM-02-USB-UVC-EP0 --evidence tasks/evidence/FORUM-02-USB-UVC-EP0`, que sin captura real del sujeto no puede pasar; sin sujeto aqui no hay captura posible."}
---

## Fuente y evidencia

Hilo NVIDIA [355453](https://forums.developer.nvidia.com/t/dgx-spark-xhci-controller-hc-died-crashes-with-realsense-d435i-streaming-30fps-depth-rgb/355453), en particular posts [11](https://forums.developer.nvidia.com/t/dgx-spark-xhci-controller-hc-died-crashes-with-realsense-d435i-streaming-30fps-depth-rgb/355453/11), [12](https://forums.developer.nvidia.com/t/dgx-spark-xhci-controller-hc-died-crashes-with-realsense-d435i-streaming-30fps-depth-rgb/355453/12) y [13–15](https://forums.developer.nvidia.com/t/dgx-spark-xhci-controller-hc-died-crashes-with-realsense-d435i-streaming-30fps-depth-rgb/355453/13).

Un usuario con DGX Spark, host xHCI MediaTek MT8901 y kernel `6.17.0-1021-nvidia` reportó que una transferencia de control UVC EP0 después de iniciar el stream provoca la firma `HC died`. Otro flujo que no envía controles EP0 después de iniciar transmisión corrió 37 minutos. El autor informó una reproducción camera-agnostic con `usbmon` y tracepoints de xHCI. NVIDIA dijo que el problema estaba corregido en una actualización de julio; un usuario dijo que aún podía reproducirlo tras reinstalar DGX OS 7.5.0-2 y actualizar paquetes, y NVIDIA pidió distinguir unidad OEM de Spark FE. La versión efectiva de la corrección sigue sin identificarse.

Blackbox ya detecta la firma de controlador muerto en `FEATURE-USB-XHCI-FORENSICS`; esa capacidad detecta el fallo después de ocurrir. No verifica qué combinación de kernel, driver, firmware y OEM contiene la corrección, ni propone un control preventivo para la secuencia UVC que dispara el cuelgue.

## Trabajo

Identificar el cambio de driver/firmware y la versión soportada que NVIDIA considera corregida. Registrar OEM, board, BIOS/EC, DGX OS, kernel, driver y cámara. En un Spark de prueba, comparar el stream sin controles posteriores a `STREAMON` con la secuencia UVC que envía controles EP0 después de iniciarlo; capturar `usbmon`, tracepoints, journal y el resultado de `bb scan`. Comprobar separadamente Spark FE y cada OEM GB10 disponible.

Si la pila actual reproduce el cuelgue, evaluar una medida preventiva acotada, como fijar los controles de cámara antes de iniciar el stream o desactivar solo los controles EP0 posteriores durante el streaming, siempre que preserve la función requerida. Si NVIDIA ofrece una versión corregida, verificarla frente a una pila anterior antes de recomendar actualización. No aplicar parches ni cambiar la máquina protegida desde esta ficha.

## Riesgos y cierre

Desactivar controles UVC puede impedir ajustar exposición, ganancia u otras funciones de la cámara. Actualizar firmware/kernel puede introducir regresiones distintas entre Spark FE y equipos OEM. Mantener una imagen/configuración recuperable y documentar el retorno exacto a la versión previa.

El post 11 reportó un stream limpio de 37 minutos como una observación de ese ensayo, no como un umbral universal de soak. Cerrar con identificación verificable de la versión corregida o una mitigación reproducible, A/B que reproduzca el cuelgue en la pila afectada y pase en la corregida/mitigada, y una duración de soak declarada antes de ejecutar, adecuada al patrón de reproducción y respaldada por repeticiones/control sano. Conservar los datos de diagnóstico y una instrucción explícita de compatibilidad OEM. Si no se dispone de la pila afectada o del OEM necesario, conservarlo como `could_not_run` y dejar abierta la ficha.

El cuerpo completo del hilo confirma el alcance de la falla y que sigue habiendo incertidumbre de versión: el reporte inicial del RealSense D435i puede disparar el controlador al alternar RGB/depth; otro usuario vio la misma firma en una capturadora UVC USB 3 y en el propio acceso de escritorio, mientras USB 2 funcionaba a menor resolución. La observación detallada del post 11 separa control EP0 de ancho de banda/alimentación: una transferencia después de `STREAMON` no completa, expira el Stop Endpoint y el controlador desmonta todos sus dispositivos. El autor dice que un reset eléctrico del dispositivo USB permitió volver a abrir stream, pero eso no recupera necesariamente el host ni demuestra recuperación general. Un powered hub no eliminó el caso de USB3 para ese usuario.

La confirmación NVIDIA del “July update” todavía no identifica versión/paket; un usuario volvió a reproducirlo tras reinstalar DGX OS 7.5.0-2 y `apt full-upgrade`. La respuesta posterior requiere actualizar por Dashboard, distinguir FE/OEM y capturar `nvidia-bug-report`; por tanto no marcar corregido por OS release string o apt success. Conservar `usbmon`/tracepoints detallados del post 11 como reproducción de referencia comunitaria, con bug report adjunto pendiente de lectura.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: No existe traza UVC EP0 en combinación cámara/xHCI afectada ni captura de versión corregida.
- Evidencia faltante para cierre: USB/UVC/firmware/kernel exactos; reproducción A/B, versión corregida, control sin EP0 afectado y rollback.
- Siguiente acción: Solicitar al dueño de hardware captura usbmon/trace de reproducción y versión corregida, control sin EP0 y rollback sobre MT8901/cámara compatibles.
- Responsable del siguiente paso: BB; operador Luis para hardware/peer.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FORUM-02-USB-UVC-EP0.md`, `tools/forum_hardware_subjects.py`, `tools/forum_finding.py`, `tests/test_debt_registration_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: baja · lectura: completa.

Cuelgue xHCI por controles UVC EP0 reportado con RealSense y xHCI MT8901; este host tiene una Logitech C920 (UVC) y un hub USB (lsusb), y huella_host ya recoge USB y velocidad, mas FEATURE-USB-XHCI-FORENSICS detecta HC died. Sin RealSense ni evidencia local del fallo.

Version para un solo nodo Gigabyte AI TOP ATOM: Mantener solo la deteccion de firma HC died y la huella de kernel/OEM; no reproducir A/B salvo que se use la C920 en streaming con controles EP0.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Criterios ejecutables de `tools.verify_forum_finding` (2026-10-14)
Los criterios ejecutables de `tools.verify_forum_finding` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.

## Root Cause
No aplica a este equipo: el cuelgue xHCI exige una camara UVC en streaming con controles EP0; hoy `lsusb` muestra solo hubs raiz y el Bluetooth, `uvcvideo` no esta cargado, y el journal del kernel retenido (desde 2026-10-13T14:07) no tiene firmas HC died / xhci halt / uvcvideo error.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. No tenia test xfail propio; su close_check era `tools.verify_forum_finding`, que sigue vivo para las demas fichas de foro (y `tests/test_closure_hardware.py::test_forum_finding_supports_every_original_id` sigue comprobando que el verificador soporta este id).

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido, con control positivo de que las mismas herramientas encuentran lo que si existe) y `e2e` (la decision registrada). Datos de la maquina redactados con el PATRON de `tests/test_sin_datos_privados.py`. Para reabrirla si el sujeto aparece: `git mv tasks/done/FORUM-02-USB-UVC-EP0.md tasks/backlog/` y `status: open`.
