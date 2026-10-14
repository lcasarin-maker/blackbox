---
id: DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01
kind: task
domain: MEMORY
title: "El --avoid desplegado de earlyoom no evita 10 nombres de la lista unica de procesos protegidos"
status: open
severity: P3
origin: detected
detector: {"rule": "tests/test_procesos_protegidos.py::test_earlyoom_hueco_medido_es_el_declarado", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-14
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider --runxfail tests/test_procesos_protegidos.py::test_earlyoom_cubre_toda_la_lista", "expect": "exit_zero", "porque": "Sale 1 hoy: el --avoid de adopted/system-config/etc_default_earlyoom (desplegado 2026-10-14) no casa con claude, node, cowork-linux-he, electron, chrome_crashpad, Xwayland, init, dbus, earlyoom ni bb, que data/procesos_protegidos.json protege en los otros cuatro vigilantes. Cierra cuando Luis despliegue un --avoid que los cubra (script de root sellado, como el del 2026-10-14) y se re-adopte el fichero; al cerrar, quitar el xfail y vaciar FALTAN_EN_EARLYOOM en el mismo test."}
---

## Medido
`tests/test_procesos_protegidos.py::test_earlyoom_hueco_medido_es_el_declarado` compara cada `nombre` de
`data/procesos_protegidos.json` contra la regex `--avoid` desplegada (sin anclar, contra `comm`, como earlyoom 1.7).
Faltan 10: `claude`, `node`, `cowork-linux-he`, `electron`, `chrome_crashpad`, `Xwayland`, `init`, `dbus`,
`earlyoom`, `bb`. El de mas peso es `claude`: la regex solo trae `claude-desktop`, asi que el CLI de Claude Code
(comm `claude`, medido en esta maquina con `ps -eo comm`) no recibe el -300 de `--avoid`.

## Al reves (lo que earlyoom evita y la lista unica no)
`journal` (cubierto en la lista por el prefijo `systemd`, salvo `journalctl`/`journal-udp-for`) y `antigravity`.
Decidir si `antigravity` entra en la lista unica es parte de esta ficha.

## Limite que no cambia
`--avoid` solo RESTA 300 al oom_score (DEBT-EARLYOOM-MOTOR-SIGUE-ELEGIBLE-01): aun cubierto, no es una exclusion.

## Por que no se ataca ahora
El fichero es configuracion desplegada como root; cambiarlo es un despliegue de Luis, no un commit.
