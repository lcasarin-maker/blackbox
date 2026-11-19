---
id: FEATURE-BB-TECHO-MEMORIA-PARA-EL-CONSUMIDOR-01
kind: task
domain: MEMORY
title: "bb techo: los techos de memoria del kernel los lee blackbox y el consumidor de conocimiento consume su salida"
status: done
closure_type: fixed
closed_at: 2026-11-18
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-11-18
close_check: {"cmd": "python3 -m pytest -q tests/test_techo_memoria.py", "expect": "exit_zero"}
evidence:
  pass: tasks/evidence/FEATURE-BB-TECHO-MEMORIA-PARA-EL-CONSUMIDOR-01/pass.txt
  patch: tasks/evidence/FEATURE-BB-TECHO-MEMORIA-PARA-EL-CONSUMIDOR-01/parche_consumidor_idle_skill_candidates.patch
reason: "CERRADO del lado de blackbox el 2026-11-18. Falta el lado del consumidor (aplicar el parche propuesto a su tools/idle_skill_candidates.py), que no se edita desde este repo."
---

## Contrato para el consumidor

`~/projects/blackbox/bin/bb techo --pid <pid> --max-gib 2 --sin-swap`. Una linea JSON `bb-techo-memoria/1` en stdout con `cgroup`, `memory_max_bytes`, `memory_swap_max_bytes` (entero, `max` o `NOT_COLLECTED: <motivo>`) y `veredicto`. rc 0 = ACOTADO; rc 1 = NO_ACOTADO; rc 2 = NOT_COLLECTED (dato ilegible o verbo ausente): quien consume trata cualquier rc != 0 como "no corras". Criterio identico a la guarda `_bounded` del consumidor (cgroup hoja, `memory.max` finito <= 2 GiB, `memory.swap.max` 0), con la equivalencia probada en 12 combinaciones.

## Lo que queda para el consumidor

Aplicar `parche_consumidor_idle_skill_candidates.patch` (probado con `patch --dry-run` sobre una copia del original y rechazado sobre la ya parcheada). Hasta que este cambio aterrice en `master` de blackbox el verbo no existe en `~/projects/blackbox` y la funcion parcheada falla cerrada (rc 2 -> RuntimeError). El consumidor no puede aplicar su parche antes de que blackbox aterrice.

## No cubierto

El consumidor crea sus scopes con su propio `tools/memory_cgroup.scope_prefix` (systemd-run con `MemorySwapMax=0`, `CPUQuota=50%`, `Nice=19`); `bb cap` pone `MemorySwapMax` igual al techo, no 0, y no tiene CPUQuota. Migrar la CREACION de techos a bb es otra pieza y no estaba en el test que fallaba.
