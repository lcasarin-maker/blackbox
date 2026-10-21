---
id: DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01
kind: task
domain: VERDICT
title: "Validar root display carveout oem fix gate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider --runxfail tests/test_debt_registration_controls.py::test_delta_root_display_carveout_oem_fix_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

## DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01

[Hilo 370458](https://forums.developer.nvidia.com/t/370458): terminales Sway quedan congeladas por `NV_ERR_NO_MEMORY` en la ruta `scanoutcarveout`, con 109 GiB libres. El dueño reproduce el problema tras pasar de driver 580.142 a 580.159.03; bajar de 6K a 4K permite abrir más ventanas pero conserva el fallo. NVIDIA propone la actualización de julio con `Adjustable Display Reserved Memory` y mejoras de manejo UMA. Falta un resultado posterior del dueño; el gist completo y las capturas quedaron sin inspeccionar.

Propuesta: comprobar soporte y valor efectivo de la reserva en el OEM ATOM, registrar versión de driver y repetir aperturas y cierres de ventanas a 6K y 4K, además de presión de caché. Distinguir la asignación de display del agotamiento general de memoria.

Riesgos: la reserva reduce memoria disponible para las cargas; atribuir el fallo a presión global puede matar procesos ajenos. Close check: reproducir el fallo, comprobar que la corrección mantiene sesión y SSH durante el ensayo y restaurar el valor previo mediante rollback verificado.

Fuentes: tasks/backlog/FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El selector original ya está integrado y llama a `tools.hardware_batch03_controls.verify` para este ID exacto. La ejecución del 2026-10-04 devolvió UNKNOWN, fail=0, could_not_run=1 por captura requerida ausente o contrato incompleto. El comando literal y su salida están registrados en `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03-integration/original-selectors-after-reader-hardening.json`. Los tests de fixtures verifican el control; el cierre requiere el sujeto real y su evidencia específica.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `external_oem`.
- Impedimento: Falta matriz OEM autorizada y ensayo reversible para ajuste de carveout; modificar firmware/UEFI puede comprometer arranque.
- Evidencia faltante para cierre: release notes del OEM/modelo; tuple EC/UEFI/OTA; baseline de memoria; canario y rollback OEM
- Siguiente acción: Solicitar a coordinación BB que obtenga matriz/release notes y ventana de canario del OEM; ejecutar solo con rollback confirmado.
- Responsable del siguiente paso: coordinación BB gestiona OEM.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_05.json`, `tasks/evidence/DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: baja · lectura: completa.

El hilo 370458 es un congelado de terminales Sway por NV_ERR_NO_MEMORY en scanoutcarveout con driver 580.159.03; este equipo corre 580.178.04 posterior y no hay evidencia aqui de sesion Sway ni del fallo. La reserva 'Adjustable Display Reserved Memory' es un dato de firmware que sirve leer una vez.

Version para un solo nodo Gigabyte AI TOP ATOM: Registrar en huella_host el valor efectivo de la reserva de display (si el firmware ATOM la expone) y el driver, sin reproducir el fallo ni cambiar la reserva.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Avance (2026-10-14, "cierra todas las pendientes conforme a la opcion recomendada") -- NO se cierra: dudosa

Regla aplicada: `void_wontfix` solo si se mide que el sujeto no existe aqui. El verificador (`tools/hardware_batch03_controls.py::_display_carveout`) llama `_subject(context, vendor="GIGABYTE", product="AI TOP ATOM")`: el OEM del sujeto ES este equipo. Medido:

```
$ cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name
GIGABYTE
AI TOP ATOM
$ command -v sway
rc=1 (no instalado)
$ loginctl show-session <sesion> -p Type
Type=x11
$ for c in /sys/class/drm/card*-*/status; do echo $c $(cat $c); done
/sys/class/drm/card0-Unknown-1/status connected
$ nvidia-smi --query-gpu=driver_version --format=csv,noheader
580.178.04
$ journalctl -k --no-pager -o short-iso | grep -i -E 'NV_ERR_NO_MEMORY|scanoutcarveout'
2026-10-13T14:43:51-06:00 ... NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY] (0x00000051) returned from _memdescAllocInternal(pMemDesc) @ mem_desc.c:1359
$ journalctl -k --no-pager -o short-iso | head -1   (el journal del kernel retenido empieza el 2026-10-13T14:07)
```

- No existe: Sway (la sesion es X11) ni la ruta `scanoutcarveout` en el journal retenido; el driver es 580.178.04, posterior al 580.159.03 del hilo.
- Existe: el OEM exacto que fija el verificador, una pantalla conectada, y UN `NV_ERR_NO_MEMORY` del driver el 2026-10-13 a las 14:43 (en `_memdescAllocInternal`, sin nombrar `scanoutcarveout`). No se puede decir con esta medicion si ese fallo de memoria fue de display o de otra asignacion.
- Falta para cerrar o declarar: atribuir el `NV_ERR_NO_MEMORY` del 13-oct (que proceso pedia memoria a esa hora) y que Luis decida si el sujeto es "Sway + scanoutcarveout" (entonces `void_wontfix`) o "asignaciones del driver que fallan con UMA libre en este OEM" (entonces queda abierta).

## Medido 2026-10-20 (boleta de Luis: cerrar void_wontfix solo con AUSENCIA MEDIDA): queda ABIERTA

Regla: `void_wontfix` solo si la ausencia del sujeto se mide en este equipo con control positivo. Solo lectura (sin sudo, sin cargas, sin reiniciar nada). Resultado: el sujeto EXISTE o no es observable desde la maquina, asi que no se cierra.

Se repitio la medicion del 2026-10-14. Ausente: Sway y la ruta `scanoutcarveout`. Presente: el OEM exacto que fija el verificador, una pantalla conectada y `NV_ERR_NO_MEMORY` del driver, ahora 4 en el journal retenido:

```
$ cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name
GIGABYTE
AI TOP ATOM
$ command -v sway            -> rc=1 (sin salida)
$ command -v Xorg gnome-shell      # control positivo del mismo command -v
/usr/bin/Xorg
/usr/bin/gnome-shell
$ for c in /sys/class/drm/card*-*/status; do echo $c $(cat $c); done
/sys/class/drm/card0-Unknown-1/status connected
$ journalctl -k --no-pager -o short-iso | grep -c -i scanoutcarveout
0           (rc=1)
$ journalctl -k --no-pager -o short-iso | grep -c -E 'NV_ERR_NO_MEMORY'
4
$ journalctl -k --no-pager -o short-iso | grep -E 'NV_ERR_NO_MEMORY' | cut -c1-90
2026-10-19T13:49:04-06:00 <hostname> kernel: NVRM: nvCheckOkFailedNoLog: Check failed:
2026-10-20T16:49:26-06:00 <hostname> kernel: NVRM: nvCheckOkFailedNoLog: Check failed:
2026-10-20T16:49:26-06:00 <hostname> kernel: NVRM: nvCheckOkFailedNoLog: Check failed:
2026-10-20T21:55:31-06:00 <hostname> kernel: NVRM: nvCheckOkFailedNoLog: Check failed:
$ journalctl -k --no-pager -o short-iso | head -1 | cut -c1-60     # el journal retenido empieza aqui
2026-10-19T08:12:28-06:00 <hostname> kernel: Booting Lin
```

Veredicto: ABIERTA. Hay cuatro `NV_ERR_NO_MEMORY` del driver en el journal retenido (desde el 2026-10-19; el del 2026-10-13 ya rotó) en el OEM exacto del sujeto. La ausencia de Sway y de `scanoutcarveout` esta medida, pero el sujeto posible de la ficha es "asignaciones del driver que fallan en este OEM", y eso existe y se repite. Sigue pendiente la atribucion (que proceso pedia memoria) y la decision de Luis sobre cual es el sujeto.
