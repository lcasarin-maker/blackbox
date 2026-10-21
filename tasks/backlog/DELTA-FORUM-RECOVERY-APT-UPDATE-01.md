---
id: DELTA-FORUM-RECOVERY-APT-UPDATE-01
kind: task
domain: VERDICT
title: "Validar forum recovery apt update 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider --runxfail tests/test_debt_registration_controls.py::test_delta_forum_recovery_apt_update_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-RECOVERY-APT-UPDATE-01.** Un usuario informa freeze tras actualización APT y luego un bloqueo durante vLLM en Docker con `--restart always`; tras hard resets describe UEFI/USB/SSH poco fiables, flags GRUB/ACPI añadidos por su cuenta y recomendación NVIDIA de recuperación oficial o RMA ([359198](https://forums.developer.nvidia.com/t/359198)). No hay logs suficientes para atribuir causa a APT, Docker o workload. Extender la runbook con captura preservable antes del reset, identificación de último kernel/driver/paquete, vía de consola externa, medio OEM verificado y criterio de recovery/RMA; cualquier rollback de paquetes se ensaya en copia/canary.

Fuentes: tasks/backlog/FEATURE-FORUM-RESCUE-RUNBOOK-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Avance de instrumentación APT — 2026-10-03

Se reutilizó la captura local de fuentes, arquitectura e índices APT para exponer los inputs del host en `tasks/evidence/BB-INSTRUMENTS-2026-10-03/apt-sources-capture.json`. No se ejecutó `apt update`, no hubo fallo/recovery del host ni se probó una consola, medio OEM, rollback o RMA. La captura no discrimina las causas APT/Docker/workload del relato; la ficha permanece abierta.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `user_decision`.
- Impedimento: No hay captura pre-reset, recovery media/rollback ni base para decidir recovery/RMA del sujeto afectado.
- Evidencia faltante para cierre: Logs pre-reset, último kernel/paquetes, ruta recovery y medios OEM, rollback; reproducción controlada que distinga APT/Docker/workload.
- Siguiente acción: Completar solo la runbook de preservación pre-reset y solicitar al operador logs previos; pedir al OEM ruta oficial de recovery/RMA antes de cualquier acción sobre el dispositivo.
- Responsable del siguiente paso: BB; operador Luis decide recuperación del sujeto.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-RECOVERY-APT-UPDATE-01.md`, `tasks/evidence/BB-INSTRUMENTS-2026-10-03/apt-sources-capture.json`, `tools/hardware_batch02_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Avance 2026-10-14: `dmidecode -t system` ya se obtiene sin contrasena
`sudo -n bb-root-run dmidecode-sistema` devuelve fabricante, producto y version de la maquina (rc=0). Sigue sin cerrar porque `_recovery_apt` tambien exige la ruta de consola externa (`ssh <console_route>`, un segundo equipo) y el hash del medio OEM de recuperacion: ambos vienen de fuera de esta maquina.

## Avance 2026-10-14 (lote 'cierra las pendientes conforme a la opcion recomendada'): espera un disparador, no una decision
Disparador: dos datos que solo existen fuera de esta maquina. (1) La ruta de consola externa: un segundo equipo desde el que Luis entre por SSH o consola serie cuando la ATOM no tenga escritorio (el NAS de la LAN ya observa por ping, pero no es consola). (2) El medio de recuperacion OEM de Gigabyte con su sha256 publicado. Paso exacto: Luis anota el equipo de consola y descarga la imagen OEM con su hash; con eso `_recovery_apt` deja de exigir lo que falta.

## Medido 2026-10-20 (boleta de Luis: cerrar void_wontfix solo con AUSENCIA MEDIDA): queda ABIERTA

Regla: `void_wontfix` solo si la ausencia del sujeto se mide en este equipo con control positivo. Solo lectura (sin sudo, sin cargas, sin reiniciar nada). Resultado: el sujeto EXISTE o no es observable desde la maquina, asi que no se cierra.

Sujeto: APT en el host que arranca el motor y la ruta de recovery. APT y su historial existen y estuvieron activos hoy:

```
$ dpkg -l apt | tail -1 | awk '{print $2, $3}'
apt 2.8.3
$ grep -h '^Start-Date' /var/log/apt/history.log | tail -3
Start-Date: 2026-10-19  07:56:08
Start-Date: 2026-10-20  18:13:13
Start-Date: 2026-10-20  21:42:15
$ ls /etc/apt/sources.list.d/ | head -4      (incluye dgx.sources, spark.sources, ubuntu.sources)
ai-workbench-desktop.sources
ai-workbench-desktop.sources.save
antigravity.list
antigravity.list.save
$ docker inspect nemotron-server --format '{{.HostConfig.RestartPolicy.Name}}'
no
```

Ausente (medido): la politica `--restart always` del relato; aqui el contenedor del motor tiene `RestartPolicy=no`. Es una diferencia de configuracion, no la ausencia del sujeto: el hilo trata de un freeze tras actualizacion APT en un GB10, y este es un GB10 con APT activo (tres corridas entre el 19 y el 20-oct) y con las fuentes DGX/Spark.

Veredicto: ABIERTA. El sujeto (APT + DGX OS en GB10 + necesidad de runbook de recovery) existe; ademas la ficha ya declara su disparador (ruta de consola externa y sha256 del medio OEM, ver "Avance 2026-10-14"), que sigue sin llegar.
