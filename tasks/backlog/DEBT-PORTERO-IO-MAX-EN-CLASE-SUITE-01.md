---
id: DEBT-PORTERO-IO-MAX-EN-CLASE-SUITE-01
kind: task
domain: MEMORY
title: "El portero debe poner tope de disco (io.max) a la clase suite, midiendo que el pre-push no se alargue de mas"
status: open
severity: P2
origin: detected
detector: {"rule": "ficha DEBT-IO-NO-DELEGADO-AL-USUARIO-LAS-SUITES-SATURAN-EL-DISCO-01: io delegado pero sin topes", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-18
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider tests/test_portero.py -k io_max", "expect": "exit_zero", "porque": "Hoy el controlador io esta delegado pero ningun scope de suite lleva IOReadBandwidthMax/IOWriteBandwidthMax. El planificador NVMe es none: IOWeight no sirve, io.max si. Medir antes/despues io_some y duracion del pre-push (hoy ~275-300 s). Riesgo: acotar el disco alarga cada push."}
---
Seguimiento de DEBT-IO-NO-DELEGADO-AL-USUARIO-LAS-SUITES-SATURAN-EL-DISCO-01.

## Medido 2026-10-18 (tras delegar io)
- `systemd-run --user --scope -p "IOWriteBandwidthMax=/dev/nvme0n1 500M"` + `dd oflag=direct`: 5.1 GB/s con tope y 5.5 GB/s sin tope. El scope NO tiene `io.max`: el tope no se aplico.
- Causa: `user@1000.service` ya ofrece `io` (cgroup.controllers = cpu io memory pids) pero su `subtree_control` y el de `app.slice` no lo activan; el gestor de usuario detecto los controladores al arrancar, antes del drop-in. Escribir `+io` a mano en ambos `cgroup.subtree_control` tampoco basto (systemd no lo adopta).
- Falta: reiniciar el gestor de usuario (cierra la sesion grafica) o reiniciar la ATOM; despues repetir este mismo dd. Solo con `io.max` presente tiene sentido tocar el portero.
- Dispositivo: nvme0n1 (259:0), planificador none.
