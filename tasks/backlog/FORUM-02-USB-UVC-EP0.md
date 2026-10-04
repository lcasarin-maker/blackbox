---
id: FORUM-02-USB-UVC-EP0
kind: task
domain: USB
title: "Validar y prevenir el cuelgue xHCI por controles UVC EP0 durante streaming"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FORUM-02-USB-UVC-EP0 --evidence tasks/evidence/FORUM-02-USB-UVC-EP0", "expect": "exit_zero", "porque": "Verificador específico pendiente: debe comprobar la reproducción A/B, la versión corregida y la recomendación preventiva para cada OEM probado."}
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
