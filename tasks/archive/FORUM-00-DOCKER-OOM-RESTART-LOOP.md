---
id: FORUM-00-DOCKER-OOM-RESTART-LOOP
kind: task
domain: HOST_USABILITY
title: "Contener reinicios de workloads que vuelven a dejar inservible el host"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest tests/test_workload_restart_containment.py -q --runxfail", "expect": "exit_zero", "porque": "Prueba pendiente: debe limitar la reincidencia de un workload identificado y permitir recuperación conservando datos, sin bloquear un reinicio sano ni atribuir todo reboot a OOM. 2026-10-30: se agrego --runxfail; sin el, el ciclo real de reinicio corria como xfail y el comando daba rc=0 con el ensayo ausente."}
---

## Trabajo en la ATOM

Contener en la ATOM la reincidencia de un workload que vuelve a dejar inservible el host: politica de intentos persistente (`tools/workload_restart_policy.py`) integrada al arranque, ensayada en un ciclo real con reboot, acceso de gestion, datos preservados y rollback (`restart-cycle`).

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/359196
- https://forums.developer.nvidia.com/t/358326
- https://forums.developer.nvidia.com/t/365028
- https://forums.developer.nvidia.com/t/380721
- https://forums.developer.nvidia.com/t/353014
- https://forums.developer.nvidia.com/t/remote-ssh-rescue-on-spark/382079
- https://forums.developer.nvidia.com/t/new-machine-cat-etc-docker-daemon-json-no-such-file-or-directory/
- https://forums.developer.nvidia.com/t/playbook-submitted-keeping-vllm-up-as-a-long-lived-service-pr-104/380721/1
- https://forums.developer.nvidia.com/t/remote-ssh-rescue-on-spark/382079/1
- https://forums.developer.nvidia.com/t/357004/1
- https://forums.developer.nvidia.com/t/380700

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Brecha y prevención

Los límites de cgroup y `FEATURE-1358-CGROUP-*` investigan contención de memoria; una ruta de arranque/reinicio puede volver a ejecutar la carga problemática antes de que el operador consiga acceso. Reutilizar políticas nativas Docker/systemd de restart, límites de intentos y admisión, para workloads declarados. Verificar cómo se comportan esos contadores a través de un reboot del host: un contador que se reinicia con cada boot puede permitir un ciclo persistente.

Definir una salida de recuperación que detenga únicamente el workload identificado, conserve modelos/datos y permita arrancar servicios de gestión. Separar crash de proceso, presión, reboot de host y actualización; la correlación temporal sola deja pendiente la atribución. Registrar identidad de contenedor/unit, política, boot IDs, eventos OOM/PSI y resultado de cada acción. Las pausas temporales siguen el contrato de suspensión: rename, manifiesto sha256/modo, responsable, caducidad y vigilancia.

## Cierre y riesgos

Probar en un entorno recuperable la reincidencia, un reinicio normal, un reboot ajeno al workload y telemetría ausente. Demostrar acceso de gestión, conservación de datos, reanudación y rollback de la política. La receta de borrar modelos queda como consejo del foro, fuera de la intervención propuesta. Una política demasiado amplia puede dejar servicios sanos detenidos; la memoria CUDA puede escapar del límite ordinario según la API y pila. La suite propuesta está pendiente: registrar controles y ensayo real antes de afirmar prevención.

## Avance de ejecución 2026-10-02

docker ps consultable, inventario de contenedores conservado. Sin target autorizado específico ni intervención. Falta política persistente y ensayo recuperable con reboot, reincidencia, reanudación/rollback y conservación de datos. No atribuir reboot a OOM por proximidad.

Evidencia y pendientes: `tasks/evidence/FORUM-00-DOCKER-OOM-RESTART-LOOP/progress.txt`. Conserva `open`; la captura de estado verifica el instrumento y deja pendiente el ensayo de recuperación/prevención requerido.

## Avance de ejecución 2026-10-03

Se añadió `tools/workload_restart_policy.py`: registra atómicamente intentos por identidad de workload en un archivo persistente, serializa reclamaciones concurrentes, rechaza un reloj retrocedido, permite workloads sanos independientes y limita la reincidencia en una ventana. Los fallos de estado producen `could_not_run` con contadores explícitos. La política no atribuye reboots a OOM ni inicia o detiene contenedores. Falta integrarla con el runtime y validar identidad, conservación de datos, servicio de gestión y recuperación en un entorno con reboot controlado. Estado permanece `open`.

## Control de cierre real integrado — 2026-10-04

El comando original conserva su texto e incluye `test_restart_recovery_close_check_uses_real_cycle_evidence`. El lector liga capturas crudas al ID/digest/PID del contenedor, unidades y gate de inicio, estado persistente y decisiones de política reproducidas, boot IDs y eventos ordenados, acceso de gestión remoto, request/respuesta del servicio, datos preservados y rollback. Rechaza los marcadores de comandos falsos detectados; OOM se conserva como observación, con atribución causal pendiente. El caso sintético completo y su mutación de ruta comprueban el lector en `tmp_path`.

Primary: `python3 -m pytest tests/test_workload_restart_containment.py -q` → `1 failed, 20 passed in 0.47s`. El único fallo es UNKNOWN/CNR por ausencia del bundle físico `tasks/evidence/FORUM-00-DOCKER-OOM-RESTART-LOOP/restart-cycle`. No se reinició el host, contenedor ni servicio. Los 10 tests originales conservaron su AST; la ficha permanece `open`.

Recibo y logs: `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/docker-real-selector-primary-integration.json`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: El selector integrado falla por ausencia del bundle físico restart-cycle; la política unitaria no prueba integración ni recuperación real.
- Evidencia faltante para cierre: bundle crudo ligado a container ID/digest/PID, unit/gate, boot IDs, OOM/PSI, SSH, datos preservados, decisión policy y rollback
- Siguiente acción: Preparar ciclo recuperable para un único workload identificado y reproducir reincidencia, reboot ajeno y reinicio sano; recopilar bundle requerido y salida del selector.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/FORUM-00-DOCKER-OOM-RESTART-LOOP.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_08.json`, `tasks/evidence/FORUM-00-DOCKER-OOM-RESTART-LOOP/progress.txt`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
