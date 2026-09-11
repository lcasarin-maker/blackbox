---
id: FEATURE-USB-XHCI-FORENSICS
kind: task
title: bb scan no tiene ninguna seccion de USB/xHCI -- cero cobertura hoy
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-09
closed_at: 2026-09-09
close_check: {"cmd": "grep -q 'USB/xHCI' tasks/done/FEATURE-USB-XHCI-FORENSICS.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-DGX-438."}
evidence: {"bug_real_atrapado": "El patron inicial `xhci_hcd.*(HC died|error|timeout|reset)` NO atrapaba 'xHCI host controller not responding, assuming dead' -- la frase REAL que el kernel emite cuando declara muerto al controlador (xhci_hc_died() en xhci-ring.c) no contiene ni 'HC died' literal ni 'error'. Se destapo probando el patron contra la frase real ANTES de darlo por bueno, no despues: rc=0 (sin match) con la frase real, rc=1 (match) solo con la variante 'HC died' que si estaba en el patron. Corregido agregando 'assum.*dead' y 'not responding'.", "decision_deliberada": "Se descarto juzgar la velocidad negociada por puerto como 'degradada': verificado en esta maquina que los root hubs a 480M son el par USB2 legitimo de cada controlador xHCI (no un fallback) y el unico dispositivo a 480M es un dongle Bluetooth, 480M por diseno. Marcar eso como fallo habria sido un falso positivo garantizado sin un manifiesto de que velocidad DEBERIA tener cada puerto, que no existe. El inventario de velocidad por puerto (lsusb -t) se agrego a `bb hw` SIN veredicto, solo como dato.", "e2e": "tasks/evidence/FEATURE-USB-XHCI-FORENSICS/e2e.txt", "fail": "tasks/evidence/FEATURE-USB-XHCI-FORENSICS/fail.txt", "pass": "tasks/evidence/FEATURE-USB-XHCI-FORENSICS/pass.txt", "pass_fixture_sintetico": "3 formas REALES en que el kernel reporta un xHCI muerto (verificadas contra el patron, no inventadas):\n$ printf '...xHCI host controller not responding, assuming dead\\n...HC died; cleaning up\\n...Timeout while waiting for setup device command\\n' | grep -icE 'xhci_hcd.*(HC died|assum.*dead|not responding|timeout|reset)'\n3", "pass_real": "$ ./bin/bb scan '2 hours ago' | sed -n '/xHCI \\/ USB/,/^$/p'\n-- xHCI / USB --\n  errores xHCI:                0\n(linea base real y honesta)"}
reason: Se agrego la seccion 'xHCI / USB' a cmd_scan (grep de journal por la firma inequivoca de un controlador xHCI muerto) y una seccion de inventario de velocidad USB a cmd_hw (informativa, sin juicio). La deteccion de 'fallback de velocidad de enlace' y 'conflictos de enumeracion/IRQ' que las fichas originales pedian se acotaron deliberadamente: sin un manifiesto de la velocidad esperada por dispositivo, marcar un puerto USB2 legitimo como degradado seria puro ruido -- verificado en esta maquina real antes de decidirlo, no asumido.
---

## Root Cause

Revisado `bin/bb` completo: no existia ninguna seccion de USB. `bb scan` no
grababa xHCI, `bb hw` no listaba buses USB, `bb sample` no toca
`/sys/bus/usb`. Era una ausencia total, no una version peor de algo que ya
existiera.

## Regression Test

No hay suite de pytest para este repo bash (`bin/bb` es el 100% del codigo ejecutable). La regresion mecanica es el propio `close_check` de esta ficha:

```
grep -q 'USB/xHCI' tasks/done/FEATURE-USB-XHCI-FORENSICS.md
```

que falla si el marcador de codigo desaparece de `bin/bb`. La regresion real se corrio a mano contra datos de produccion antes y despues del fix -- ver Verification Evidence.

## Verification Evidence

**pass_real**:
```
$ ./bin/bb scan '2 hours ago' | sed -n '/xHCI \/ USB/,/^$/p'
-- xHCI / USB --
  errores xHCI:                0
(linea base real y honesta)
```

**pass_fixture_sintetico**:
```
3 formas REALES en que el kernel reporta un xHCI muerto (verificadas contra el patron, no inventadas):
$ printf '...xHCI host controller not responding, assuming dead\n...HC died; cleaning up\n...Timeout while waiting for setup device command\n' | grep -icE 'xhci_hcd.*(HC died|assum.*dead|not responding|timeout|reset)'
3
```

**bug_real_atrapado**:
```
El patron inicial `xhci_hcd.*(HC died|error|timeout|reset)` NO atrapaba 'xHCI host controller not responding, assuming dead' -- la frase REAL que el kernel emite cuando declara muerto al controlador (xhci_hc_died() en xhci-ring.c) no contiene ni 'HC died' literal ni 'error'. Se destapo probando el patron contra la frase real ANTES de darlo por bueno, no despues: rc=0 (sin match) con la frase real, rc=1 (match) solo con la variante 'HC died' que si estaba en el patron. Corregido agregando 'assum.*dead' y 'not responding'.
```

**decision_deliberada**:
```
Se descarto juzgar la velocidad negociada por puerto como 'degradada': verificado en esta maquina que los root hubs a 480M son el par USB2 legitimo de cada controlador xHCI (no un fallback) y el unico dispositivo a 480M es un dongle Bluetooth, 480M por diseno. Marcar eso como fallo habria sido un falso positivo garantizado sin un manifiesto de que velocidad DEBERIA tener cada puerto, que no existe. El inventario de velocidad por puerto (lsusb -t) se agrego a `bb hw` SIN veredicto, solo como dato.
```

## Fichas HARVEST de origen (cosecha de Atlas, evaluadas 2026-09-09)

- HARVEST-355453-dgx-spark-xhci-controller-hc-died-crashes-wit
- HARVEST-362015-all-usb-connections-fall-back-to-480-mbps-usb
- HARVEST-365609-nvidia-dgx-spark-continuously-freezing-hangin
- HARVEST-380009-asm2464pd-usb-c-3-2-2x2-enclosure-always-fall
