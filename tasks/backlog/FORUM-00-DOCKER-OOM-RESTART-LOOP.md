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

## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-VLLM-GENERATION-LIVENESS-PROBE`** — A 24/7 GB10 vLLM author reports `/health` can return 200 while the engine has stopped serving. Their unauthenticated active probe received 401 with no `choices`, misclassified the healthy service as wedged and restarted it on a… Fuente: [380721](https://forums.developer.nvidia.com/t/playbook-submitted-keeping-vllm-up-as-a-long-lived-service-pr-104/380721/1).
- **`BB-DOCKER-SSH-RESCUE-WINDOW`** — SGLang container with restart policy repeatedly consumes memory/swap after host reboot; disabling docker.service does not stop active container and docker.socket may reactivate it. SSH arrives earlier than model load, but proposed broad… Fuente: [382079](https://forums.developer.nvidia.com/t/remote-ssh-rescue-on-spark/382079/1).
- **`BB-OOM-BOOT-RESCUE-USER-DATA`** — A DGX Spark desktop reportedly freezes during login after a user-started local model/container began autostarting; the owner eventually used a brief NVIDIA Sync/SSH window to disable Docker and retrieve data. NVIDIA says improved OOM… Fuente: [357004](https://forums.developer.nvidia.com/t/357004/1).


## Índice de propuestas del lote 00

- `FORUM-00-MODEL-CONTEXT-STARTUP-ADMISSION` — [Validate advertised model context and colocated UMA budget before auto-restarting model containers](https://forums.developer.nvidia.com/t/380700); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.

## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.
