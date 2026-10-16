---
id: FEATURE-1358-CGROUP-02-TRAZA
kind: task
domain: GPU
title: "Identificar el camino de asignación y el propietario del cargo"
status: done
closed_at: 2026-10-16
closure_type: relocated_prior_verification
reason: "La pregunta (por que camino entra una asignacion CUDA y quien paga) se contesto por otra via el 2026-10-12: el barrido de ioctl (barrido-ioctl-20261012.txt) mostro que cudaMalloc entra por la clase RM 0x3e (NV01_MEMORY_SYSTEM) y no por video_mem.c, y el parche cobra ahi (sysmemConstruct_IMPL). La traza dinamica de memcg/flags que pedia esta ficha no se hizo."
evidence: {"pass": "tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA.pass.txt", "fail": "tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA.fail.txt", "e2e": "tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA.e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "grep -q \"class=0x3e\" tasks/evidence/FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01/barrido-ioctl-20261012.txt", "expect": "exit_zero", "porque": "La verificacion se relocalizo a FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01 (voto de Luis 2026-10-16). Comprueba el marcador de su medicion; no re-ejecuta el experimento ni acredita la autenticidad del origen. Control negativo: el mismo grep contra un marcador inexistente da rc 1."}
---

## Contexto y dependencias

Plan derivado de [la corrección del README](../../README.md#a-measured-cgroup-accounting-gap-on-this-gb10-stack) y [el informe histórico corregido](../evidence/nvidia-1358-comment.md). Fuente de colaboración: [NVIDIA #1358](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358).

Dependencias: FEATURE-1358-CGROUP-01-REPRO.

## Alcance

Sobre la pila de la reproducción, localizar la entrada CUDA y su camino por RM/UVM/allocador del kernel. Reutilizar fuentes y herramientas de trazado disponibles; registrar símbolos, versión y límites de observabilidad. Verificar qué memcg está activo, qué flags se usan y cuándo el trabajo cambia de contexto o pasa a un worker.

Comparar los helpers memcg y __GFP_ACCOUNT existentes en 580.178.04 con la ruta realmente observada. Separar NV_ALLOC_PAGES_NODE_SKIP_RECLAIM y RmNumaAllocSkipReclaimPercent del mecanismo de cargo. Una interpretación de ensamblador debe quedar identificada como inferencia.

## Criterio de cierre

Mapa respaldado por trazas de la asignación real, con archivos/líneas de la versión correspondiente y dueño del cargo. Contrastar una asignación CPU contabilizada y una ejecución sin la llamada GPU. Declarar lo que no pudo trazarse. La mera presencia de helpers en el código no demuestra que la ruta los ejecute.

El comando close_check queda especificado para su implementación con el trabajo. Hoy el verificador y sus evidencias están pendientes; esta ficha registra el plan, no resultados ejecutados. Debe rechazar evidencias ausentes y datos fabricados, y tener un control negativo que pruebe que detecta el defecto de su sujeto.

## Avance del swarm — 2026-10-02

Ejecutor: Luna; coordinación: Codex. Preparado: mapa estático y comprobación de símbolos.
Evidencia: `tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA/trace-map.txt`.
Pendiente para cierre: traza dinámica de memcg/flags/worker; el acceso a probes requiere privilegios root.
La ficha conserva status open; el informe distingue observaciones estáticas
y resultados runtime. El verificador de cierre permanece pendiente.

## Avance de instrumentación — 2026-10-02

Disponible un probe preparatorio en `tools/kernel_charges.bt`, con firmas que
coinciden con los headers 6.17 instalados. El mapa y el control negativo offline
están en `tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA/trace-map.txt` y
`tasks/evidence/FEATURE-MEMORYSAVER-02-TRAZADOR/abi-check.txt`. El probe etiqueta
cgroup del ejecutor y reporta el owner como desconocido; `set_active_memcg(mm)`
impide equiparar ambas identidades. No hubo parse/attach/captura por la barrera
de root. Dueño real, flags observados y transición a worker siguen pendientes;
esta ficha conserva status open.

**FEATURE-FORUM-UVM-TRACE-CAPABILITY-01 (delta del foro 357848).** En GB10/SM121 con driver 580.95.05, CUDA 13.1 y Nsight Systems 2026.1.1, un operador no pudo capturar page faults/migraciones UVM y NVIDIA respondió que el perfilado UVM no está soportado en Spark en esa combinación ([357848](https://forums.developer.nvidia.com/t/357848)). Reusar el mapa de traza de esta ficha para anotar capacidad/no-capacidad por versión; no inferir migraciones UVM a partir de memoria host, faults CPU agregados o `nvidia-smi`, ni abrir un probe separado que Blackbox no usa. Una alternativa solo se admite tras soporte del proveedor y una prueba conocida de UVM contra control host.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `privileged_access`.
- Impedimento: El mapa estático y ABI probe están disponibles; la captura dinámica quedó sin ejecutar por barrera root.
- Evidencia faltante para cierre: Traza memcg/flags/worker con dueño real, transición observada y control negativo en kernel 6.17; identidad del stack.
- Siguiente acción: Solicitar al operador captura acotada del probe en lab con privilegios root, identidad kernel, owner/flags/transición worker y control negativo; preservar stderr y resultado de attach.
- Responsable del siguiente paso: BB; operador Luis para acceso root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FEATURE-1358-CGROUP-02-TRAZA.md`, `tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA/trace-map.txt`, `tools/kernel_charges.bt`, `tools/verify_cgroup_plan.py`, `tests/test_closure_kernel_selectors.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Criterios ejecutables de `tools.verify_cgroup_plan` (2026-10-14)
Los criterios ejecutables de `tools.verify_cgroup_plan` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-CGROUP-PLAN-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.

## Avance 2026-10-14 (lote 'cierra las pendientes conforme a la opcion recomendada'): espera un disparador, no una decision
Disparador: una captura con bpftrace que corre Luis en persona (bpftrace es root total: no se sella en bb-root-run). Paso exacto: en una ventana de laboratorio, `sudo bpftrace tools/kernel_charges.bt` mientras corre `python3 -m tools.cgroup_repro`, guardando stdout y stderr en `tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA/`; despues `python3 -m tools.verify_cgroup_plan --phase 02-traza --evidence tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA`. La misma captura sirve a FEATURE-MEMORYSAVER-02-TRAZADOR.

## Root Cause
La ficha se abrio el 2026-10-02 como plan de un swarm (Luna/Codex): sus verificadores (`tools.verify_cgroup_plan --phase ...`) nunca recibieron capturas y daban `unknown`. Entre tanto el 2026-10-12 el modulo NVIDIA parcheado se cargo y se midio por otra ruta; la pregunta de esta ficha quedo contestada ahi. Leccion: un plan con verificador pendiente no es un cierre; esta ficha queda cerrada solo por la verificacion relocalizada de abajo.

## Regression Test
Ninguno propio: la verificacion vive en `FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01` (su close_check y su evidencia). El control negativo de arriba prueba que el comprobador distingue un marcador presente de uno ausente.

## Verification Evidence
- pass: `tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA.pass.txt`
- fail: `tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA.fail.txt`
- e2e: `tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA.e2e.txt`

## Limite declarado (cierre del 2026-10-16, voto de Luis)
No se hizo la traza dinamica (kprobes/bpftrace de memcg, flags y worker); el camino se infirio de un barrido de ioctl del espacio de usuario y se confirmo midiendo el cobro con el modulo cargado. Una interpretacion de ensamblador sigue siendo inferencia.
