---
id: DEBT-OBSERVADORES-CONSTRUIDOS-SIN-INSTALAR-01
kind: task
domain: SYSTEM
title: "Los observadores que sobreviven a un corte estan construidos y votados pero no instalados: el bucle de reinicios del 2026-11-01 y 11-02 corrio sin ninguno"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-11-02
close_check: {"cmd": "systemctl --user is-active --quiet bb-ultimo-aliento.service && ! bash tools/opt_in_captura.sh estado 2>&1 | grep -qE 'netconsole-arranque: no aplicada|pstore-tras-panico: no aplicada'", "expect": "exit_zero", "porque": "Falla hoy (medido 2026-11-02): bb-ultimo-aliento.service no existe como unidad de usuario (rc 4) y las capas netconsole-arranque y pstore-tras-panico salen 'no aplicada'. Pasa solo con el muestreador de 250 ms activo y esas dos capas aplicadas."}
---

## Medido el 2026-11-02

Entre 2026-10-30 19:05 y 2026-11-02 11:44 hubo 20 arranques de 3 a 242 s (`journalctl --list-boots`), mas uno de 2 h 44 min. Ninguno dejo una sola linea fuera de la maquina.

| Observador | Estado medido | Desde cuando existe |
|---|---|---|
| Netconsole en tiempo de ejecucion (capa `netconsole-runtime`) | aplicada y activa desde 2026-11-02 ~15:00; arranca como servicio de usuario-espacio, a ~30 s del arranque | hoy |
| Netconsole en la linea de arranque (capa `netconsole-arranque`) | `no aplicada` (`opt_in_captura.sh estado`; `arranque en marcha: sin netconsole.netconsole=`) | 2026-11-01 (PR #4) |
| pstore tras panico (`pstore-tras-panico`), `panic-temprano`, `grub-marca` | `no aplicada` | 2026-11-01 |
| Muestreador de 250 ms con anillo fijo (`bb-ultimo-aliento.service`) | `not-found` como unidad de usuario; el archivo `systemd/bb-ultimo-aliento.service` existe en el repo | 2026-11-01 |
| Testigo externo de un solo archivo (`tools/testigo/bb_testigo.py`) | instalado el 2026-11-06 en la Dell (`DesktopAequitas`): tarea `bb-testigo` (SYSTEM, al arrancar), sondeo TCP/ICMP a la ATOM y latido, UDP 6667 junto al receptor de netconsole; la ATOM trae sus series con `externo/testigo.json` (`trae.json`: `OK`, 2 archivos). Probado en Windows real: 20 s de corrida de prueba, `rc=0`, TCP 22 abierto (31 ms) y eco ICMP. NO probado a traves de un reinicio de la Dell ni con un corte real | 2026-11-06 |
| Alarma externa (`tools/testigo/bb_alarma.py`, tarea `bb-alarma` en la Dell, SYSTEM al arrancar) | instalada y corriendo el 2026-11-06: cada 30 s prueba SSH casa, SSH Tailscale y RustDesk de la ATOM, avisa por ntfy tras 3 fallos y manda "alarma viva" al dia. Probada de punta a punta: un puerto cerrado de prueba produjo un aviso que Luis confirmo en su telefono (`tests/test_alarma.py`: 10 pasan, 4 fallan con el umbral mutado). NO probada tras un reinicio de la Dell; si la Dell o ntfy.sh caen, calla (la senal es que falte el aviso diario) | 2026-11-06 |
| Aviso de intervencion de earlyoom (`tools/aviso_earlyoom.py`, `systemd/bb-aviso-earlyoom.service`, interruptor `aviso_earlyoom` en `actuar`) | instalado y activo el 2026-11-06 (`NRestarts=0`, sigue `journalctl -u earlyoom`). Probado con un aviso real de prueba que llego al telefono de Luis y con 13 pruebas; NO probado con una rafaga real de earlyoom (no se puede provocar sin que mate algo). El contenedor `nemotron-server` no lleva etiqueta `lanzado_por`, asi que su aviso dice «sin etiqueta» | 2026-11-06 |
| Ping desde el NAS (`adopted/nas/bb-ping-atom.sh`, voto de Luis 2026-10-14) | "sin instalar" segun la ficha FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01 | 2026-10-14 (19 dias) |
| Medidor de energia externo (enchufe) | en camino | pendiente |

Los 20 arranques cortos mueren antes de que el netconsole de tiempo de ejecucion arranque (~30 s) o a los pocos segundos de que lo haga; solo la capa de linea de arranque habria capturado sus primeros segundos.

## Alcance

1. Instalar `bb-ultimo-aliento.service` como unidad de usuario y comprobar que el anillo sobrevive a un corte (el muestreador de 1 s ya demostro que su fsync sobrevive: `muestreo-7cd0848b.jsonl` termina a 0,4 s del ultimo log del journal).
2. Aplicar `netconsole-arranque` y `pstore-tras-panico` con `sudo bash tools/opt_in_captura.sh aplica <capa>` (necesita root; Luis decide cuando).
3. Instalar `bb-ping-atom.sh` en el NAS o fijar otro equipo siempre encendido; hoy el receptor de netconsole esta en un PC Windows con tarea de inicio `bb_receptor_netconsole` (creada 2026-11-02, sin probar a traves de un reinicio de ese PC).
4. Registrar para cada observador "construido / instalado / probado con un corte real" como tres estados distintos en el inventario.

## Control negativo

El `close_check` falla hoy por las dos ramas (unidad ausente y capas sin aplicar). Cada rama se midio por separado el 2026-11-02.

## Limite

Instalar no prueba que capture un corte real; eso lo prueba el proximo corte. Mientras no haya uno, el estado correcto es "instalado, sin captura probada".
