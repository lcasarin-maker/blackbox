---
id: DEBT-IO-NO-DELEGADO-AL-USUARIO-LAS-SUITES-SATURAN-EL-DISCO-01
kind: task
domain: MEMORY
title: "Las suites saturan el disco y el usuario no puede acotarlo: io no esta delegado"
status: open
severity: P2
origin: detected
detector: {"rule": "tests/test_io_delegado_al_usuario.py::test_io_esta_delegado_al_manager_del_usuario", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-17
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider --runxfail tests/test_io_delegado_al_usuario.py::test_io_esta_delegado_al_manager_del_usuario", "expect": "exit_zero", "porque": "Medido 2026-10-17: la ATOM iba lenta con la maquina ociosa (carga 0.4-2, 47 GiB libres, sin presion de CPU ni memoria) y las muestras de bb solo registran presion de disco: io_some 16 % a las 15:42, 33 % a las 16:30 y 12 % a las 16:48, con procesos python de las suites creciendo 0.6-1.6 GB y un prek (pre-push) a las 16:50. El portero acota memoria, tareas y turnos de las suites, pero no su disco: el controlador io existe en la raiz y en user.slice y NO esta en user-1000.slice (cgroup.controllers = cpu memory pids), asi que ningun proceso del usuario puede acotarlo sin root."}
---

## Medido (2026-10-17, antes del reinicio de las 17:05)
- Muestras de `bb` (`samples/2026-10-17.jsonl`), 15:30-17:00: carga 0.4-2.1, `MemAvailable` 47-48 GiB, PSI de memoria y de CPU en 0. Unico indicador alto: `io_some` 16.27 % (15:42), 32.7 % (16:30), 12.23 % (16:48).
- En esos minutos `pidio` nombra `python` del scope de la app de Claude con `crecio_kb` 580 MB-1.6 GB y un `prek` (el `pre-push` de este repo) con 1.6 GB a las 16:50. `bb-usable` midio la latencia de X en 4 ms (max 8): su sonda es ciega a la lentitud que se siente.
- `cat /sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/cgroup.controllers` = `cpu memory pids`. La raiz ofrece `cpuset cpu io memory hugetlb pids rdma misc dmem`. `Delegate=yes` en `user@1000.service`, pero `io` no esta en el `subtree_control` de `user-1000.slice`.
- El planificador del NVMe es `none`: `IOWeight` no tendria efecto sin BFQ o `io.cost`; `io.max` (tope de ancho de banda) funciona con cualquier planificador.

## Que falta (es un despliegue de root de Luis)
Delegar `io` al arbol del usuario con un drop-in (`Delegate=cpu memory pids io` en `user@.service.d/`, via script sellado de `bb-root-run`), y despues que el portero ponga `IOWriteBandwidthMax`/`IOReadBandwidthMax` en el scope de la clase `suite`. Medir antes con una corrida del `pre-push` que la presion `io_some` baje y que la suite no se alargue mas de lo aceptable. Riesgo: acotar el disco alarga cada push.
