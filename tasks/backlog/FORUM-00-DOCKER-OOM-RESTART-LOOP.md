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
close_check: {"cmd": "python3 -m pytest tests/test_workload_restart_containment.py -q", "expect": "exit_zero", "porque": "Prueba pendiente: debe limitar la reincidencia de un workload identificado y permitir recuperación conservando datos, sin bloquear un reinicio sano ni atribuir todo reboot a OOM."}
---

## Evidencia y límites

[359196](https://forums.developer.nvidia.com/t/359196) reporta un freeze al volver a arrancar un contenedor Docker después del login. NVIDIA plantea el OOM conocido como hipótesis y sugiere Safe Mode y retirar archivos de modelo; falta reproducción y confirmación posterior. [358326](https://forums.developer.nvidia.com/t/358326) describe un modelo vLLM en autostart que impide recuperar el acceso. [365028](https://forums.developer.nvidia.com/t/365028) relata una atribución inicial al driver 590 que cambió al aislar contenedores en autostart. Versiones y causa común requieren verificación. Ver los veredictos y findings del swarm para los posts revisados.

## Brecha y prevención

Los límites de cgroup y `FEATURE-1358-CGROUP-*` investigan contención de memoria; una ruta de arranque/reinicio puede volver a ejecutar la carga problemática antes de que el operador consiga acceso. Reutilizar políticas nativas Docker/systemd de restart, límites de intentos y admisión, para workloads declarados. Verificar cómo se comportan esos contadores a través de un reboot del host: un contador que se reinicia con cada boot puede permitir un ciclo persistente.

Definir una salida de recuperación que detenga únicamente el workload identificado, conserve modelos/datos y permita arrancar servicios de gestión. Separar crash de proceso, presión, reboot de host y actualización; la correlación temporal sola deja pendiente la atribución. Registrar identidad de contenedor/unit, política, boot IDs, eventos OOM/PSI y resultado de cada acción. Las pausas temporales siguen el contrato de suspensión: rename, manifiesto sha256/modo, responsable, caducidad y vigilancia.

## Cierre y riesgos

Probar en un entorno recuperable la reincidencia, un reinicio normal, un reboot ajeno al workload y telemetría ausente. Demostrar acceso de gestión, conservación de datos, reanudación y rollback de la política. La receta de borrar modelos queda como consejo del foro, fuera de la intervención propuesta. Una política demasiado amplia puede dejar servicios sanos detenidos; la memoria CUDA puede escapar del límite ordinario según la API y pila. La suite propuesta está pendiente: registrar controles y ensayo real antes de afirmar prevención.

## Servicio non-serving y falso restart

[380721](https://forums.developer.nvidia.com/t/380721) describe /health200 pese a engine sin servir, y el fallo opuesto: probe de generación sin credenciales devolvía401 y un watchdog reiniciaba una instancia sana. Una selección errónea del model id desde el objeto permission causó404. Validar respuesta mínima del modelo real, con auth/config correctas y presupuesto acotado; separar fallo de probe, auth/config, backend y host. Una respuesta200 de health o fallo401/404 deja pendiente la generación efectiva y no autoriza restart por sí sola. Cada intervención necesita target/PID/ownership, cooldown y presupuesto, preservación de evidencia, controles de requests válidos/idle y retorno a servicio. El relato es de un operador y carece de reproducción local BB.

## Avance de ejecución 2026-10-02

docker ps consultable, inventario de contenedores conservado. Sin target autorizado específico ni intervención. Falta política persistente y ensayo recuperable con reboot, reincidencia, reanudación/rollback y conservación de datos. No atribuir reboot a OOM por proximidad.

Evidencia y pendientes: `tasks/evidence/FORUM-00-DOCKER-OOM-RESTART-LOOP/progress.txt`. Conserva `open`; la captura de estado verifica el instrumento y deja pendiente el ensayo de recuperación/prevención requerido.

[353014](https://forums.developer.nvidia.com/t/353014) añade GX10 inicialDockerfailed/restartlimit; responder propone confirmar error BuildKit invalid database y renombrar su directorio preservando contenido. Autor confirma recuperación pero no pega error exacto. Ofrecer esa recuperación solo tras comprobar firma de fallo y estado fresco/datos relevantes; detener daemon afecta otros contenedores. Registrar hash/modo/expiry/watcher y restauración, sin borrar cache ni cambiar grupos/privilegios como receta automática. Es recuperación de servicio distinta de OOM.

[382079](https://forums.developer.nvidia.com/t/remote-ssh-rescue-on-spark/382079) adds the remote-rescue failure mode: a Qwen3.8/SGLang container consumed 64 GiB swap and its Docker restart policy relaunched it after every host reboot. Disabling `docker.service` did not stop an already-running container; enabled `docker.socket` could restart the daemon. A reply proposes waiting for early SSH then disabling restart and stopping the running container before a normal reboot, but the author does not confirm success. Do not run its broad `docker ps -q` command as written: it changes/stops every running container. A canary procedure must identify the one owned unit/container, preserve its data and management services, inspect socket activation and demonstrate recovery before recommending an intervention; prefer orderly reboot during swap thrash to a hard power cut only after access/control state is known.

[357515](https://forums.developer.nvidia.com/t/new-machine-cat-etc-docker-daemon-json-no-such-file-or-directory/) reports Docker start failure and systemd start-limit on an ASUS GX10 after initial setup; absence of `/etc/docker/daemon.json` alone is not evidence of a defect. A reply points to a different case with `invalid database` under `/var/lib/docker/buildkit` and suggests confirming the journal signature before repairing/renaming that state. The original author does not confirm the cause or recovery, and one response's command is truncated in the capture. Extend the existing BuildKit-recovery test with exact signature and preservation/rollback; do not infer OOM or rename data blindly.

