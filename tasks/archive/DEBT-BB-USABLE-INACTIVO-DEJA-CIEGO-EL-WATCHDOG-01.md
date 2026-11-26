---
id: DEBT-BB-USABLE-INACTIVO-DEJA-CIEGO-EL-WATCHDOG-01
kind: task
domain: MONITORING
title: "bb-usable esta cargado pero inactivo: el watchdog de hardware sigue ciego ante una maquina inservible"
status: open
severity: P2
origin: detected
detector: {"rule": "bin/bb status", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-11-18
close_check: {"cmd": "out=$(bin/bb status 2>&1) && printf '%s\\n' \"$out\" | grep -E '^  ARMADO +bb-usable ' && printf '%s\\n' \"$out\" | grep -x 'could_not_run: 0' && { if printf '%s\\n' \"$out\" | grep -E '^  (FALTA +bb-usable|CIEGO +(bb-usable|watchdog de hardware|configuracion del watchdog de hardware))'; then false; else [ \"$?\" -eq 1 ]; fi; }", "expect": "exit_zero", "porque": "Exige status exitoso, latido ARMADO, cero consultas sin ejecutar y ausencia de ceguera relevante. Ademas requiere evidencia operativa autorizada."}
---

## Medido (2026-11-18)
- `bin/bb status` (con acceso al bus de systemd): `FALTA bb-usable ... ActiveState=inactive: sudo ./enable-privileged.sh`, y `CIEGO watchdog de hardware (1min)` cuyo remedio dice armar bb-usable.
- Armarlo exige `sudo ./enable-privileged.sh`; un agente no usa sudo. Lo ejecuta Luis tras leer el script.

## Preparación local (2026-11-21)
La unidad de sistema es `bb-usable.service`: `After=multi-user.target` ordena su arranque y `WantedBy=multi-user.target` permite habilitarla; no declara `Requires=`. `WatchdogSec=360` y `FailureAction=reboot-immediate` permiten un reinicio inmediato. El watchdog de hardware supervisa PID 1; la indisponibilidad de bb-usable deja sin esa vía la detección de presión sostenida que vuelve inservible la máquina aunque PID 1 responda.

Antes de una ventana autorizada, cotejar la unidad instalada, su `ExecStart`, configuración efectiva, estado y latido en journal con la plantilla versionada. El instalador completo cambia otras piezas; su `--revert` también, por lo que no constituye reversión acotada. Preparar copia y restauración exacta de la unidad y habilitación previas para la ventana; la reversión debe devolver el estado original y comprobarlo. Validar activo y latido reciente con `bin/bb status`, cero `could_not_run`, y configuración efectiva; documentar evidencia y efectos antes de cerrar. La ficha sigue abierta hasta esa evidencia operativa.

Control sintético sobre el comando de esta ficha: `python3 -m pytest -q -p no:cacheprovider --basetemp="$HOME/scratch/blackbox/2026-11-21-bb-usable-close-check/focal" tests/test_bb_usable_inactive_close_check.py` → `7 passed in 0.10s`. Incluye salida sana y negativos: status rc 1, bus ilegible, unidad inactiva, configuración ciega, watchdog ciego y salida vacía. El patrón anterior se reprodujo con `bash -c 'set +e; out=$(printf "bus inaccessible\n"; exit 1); printf "status_rc=%s\n" "$?"; ! printf "%s\n" "$out" | grep -E "FALTA +bb-usable|CIEGO +watchdog"; printf "original_close_check_rc=%s\n" "$?"'` → `status_rc=1` y `original_close_check_rc=0`.

La corrida conjunta con `tests/test_status_bus_unknown.py` dio `1 failed, 20 passed in 0.41s`: `test_status_prints_unknown_count_even_zero` busca dentro de 18000 caracteres y el resumen está fuera de ese corte. Esa prueba existente queda pendiente; los ensayos de clasificación del bus de esa corrida pasaron.

Retoma: el archivo `bin/bb` de la base `226654b1` sitúa el resumen en el carácter 18112 desde `cmd_status`, fuera del corte 18000. La prueba ahora delimita hasta `cmd_install` y comprueba que quitar el resumen provoca fallo. Casos adicionales aíslan `could_not_run: 1` con latido aparente y ausencia de latido con unidad activa. Sin invocar `bin/bb status` real:

```text
flock -x [RUTA_LOCAL_PRIVADA] python3 -m pytest -q -p no:cacheprovider --basetemp=[RUTA_LOCAL_PRIVADA] tests/test_bb_usable_inactive_close_check.py
.........                                                                [100%]
9 passed in 0.12s

flock -x [RUTA_LOCAL_PRIVADA] python3 -m pytest -q -p no:cacheprovider --basetemp=[RUTA_LOCAL_PRIVADA] tests/test_bb_usable_inactive_close_check.py tests/test_status_bus_unknown.py
.......................                                                  [100%]
23 passed in 0.25s
```

Control del fallo del instrumento: con solo el último `grep` forzado a rc 2, `flock -x [RUTA_LOCAL_PRIVADA] python3 -m pytest -q -p no:cacheprovider --basetemp=[RUTA_LOCAL_PRIVADA] tests/test_bb_usable_inactive_close_check.py::test_last_grep_failure_cannot_pass` dio `1 failed in 0.07s`, con `assert 0 != 0`: el comando anterior aceptaba el error. El comando corregido acepta únicamente rc 1 como ausencia. Repetición sintética:

```text
flock -x [RUTA_LOCAL_PRIVADA] python3 -m pytest -q -p no:cacheprovider --basetemp=[RUTA_LOCAL_PRIVADA] tests/test_bb_usable_inactive_close_check.py tests/test_status_bus_unknown.py
........................                                                 [100%]
24 passed in 0.26s
```

## Aparte, sin ficha propia hoy
`CIEGO earlyoom ante agotamiento de memoria unificada`: su umbral lee MemAvailable, que marco 56 % durante los congelamientos del 2026-09-22/23 (ver `bin/bb status`). Es un limite conocido del instrumento; si se quiere cerrar, abrir ficha con un umbral que no dependa de MemAvailable.
