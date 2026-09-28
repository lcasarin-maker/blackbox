---
id: DEBT-BB-SAMPLE-SIN-TECHO-DE-TIEMPO-SE-QUEDO-COLGADO-EN-EL-COLAPSO
kind: debt
title: "blackbox-sample.service no tenia TimeoutStartSec: una sola muestra colgada apagaba el instrumento hasta el reinicio"
status: done
closure_type: fixed
closed_at: 2026-09-28
severity: P1
origin: asserted
satd_family: MISSING_COVERAGE
created: 2026-09-28
close_check: {"cmd": "bash -c 'test \"$(systemctl --user show blackbox-sample.service -p TimeoutStartUSec --value)\" != infinity'", "expect": "exit_zero", "porque": "systemctl no esta en .simplecode/build_tools.txt (solo grep y bash), asi que se envuelve en bash -c, el mismo patron ya usado en DEBT-PROCESO-SIN-TECHO. Comprobar el VALOR desplegado, no solo que el archivo del repo lo declare, porque el propio bug de esta ficha es exactamente esa distancia: 'adopted/' puede decir una cosa y la unit real otra si no se recarga."}
evidence:
  pass: tasks/evidence/DEBT-BB-SAMPLE-SIN-TECHO-DE-TIEMPO-SE-QUEDO-COLGADO-EN-EL-COLAPSO/pass.txt
  fail: tasks/evidence/DEBT-BB-SAMPLE-SIN-TECHO-DE-TIEMPO-SE-QUEDO-COLGADO-EN-EL-COLAPSO/fail.txt
reason: "CERRADO 2026-09-28. TimeoutStartSec=45 anadido a blackbox-sample.service en las tres copias (systemd/, adopted/systemd-user/, la unit real), recargado con daemon-reload. Verificado con bb drift: 39 revisados / 0 divergentes. Corroboracion en vivo, NO buscada: mientras se desplegaba el arreglo, con load1 real de 52.40, blackbox-sample.service se colgo DOS VECES seguidas bajo el nuevo techo -- 4.035s y 1.546s de CPU consumidos en 45s de reloj cada vez, confirmando que estaba bloqueado y no calculando -- y se recupero solo en el siguiente disparo del timer (Finished en <1s). Sin el arreglo, esas dos invocaciones habrian dejado el instrumento sin escribir indefinidamente, igual que el 2026-09-28 03:28-03:41. Bajado el pico (load1 22-24), 5 corridas directas con las mismas Nice=19+IOSchedulingClass=idle y un timeout generoso (300s) tardaron 0.71-0.87s cada una: el techo de 45s no le pega a una corrida normal, solo corta el pico transitorio real que se acaba de medir dos veces. Limite declarado: si el proceso esta en D-state de verdad, ni SIGTERM ni un SIGKILL posterior lo sacan de ahi al instante -- el timeout acota el hueco de `infinity` a un maximo conocido, no lo elimina bajo cualquier causa de cuelgue."
---

## Root Cause

### El hallazgo colateral que quedo declarado, no investigado

`bb-guardia-proceso` (armado hoy) y `bb-usable` leen ambos, directa o
indirectamente, lo que `blackbox-sample.timer` escribe cada minuto. Al
recalibrar `tools/calibra_psi.py` contra los dos colapsos de hoy
(`DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES`), `python3 -m
tools.calibra_psi` salio con VEREDICTO CORTE INVALIDO porque el colapso 1
tiene un hueco de datos: la ultima muestra sana fue a las 03:28:58 y el
reinicio ocurrio ~03:39-03:41 -- **entre 10 y 13 minutos sin una sola
muestra**, exactamente la ventana mas critica del incidente. Quedo declarado
en esa ficha, sin perseguir la causa. Esta ficha persigue la causa.

### La causa, medida hoy

```
$ systemctl --user cat blackbox-sample.service
[Service]
Type=oneshot
ExecStart=%h/projects/blackbox/bin/bb sample
Nice=19
IOSchedulingClass=idle
# sin TimeoutStartSec -- systemctl --user show da TimeoutStartUSec=infinity
```

```
$ journalctl --user -u blackbox-sample.service --since "2026-09-28 03:25:00" --until "2026-09-28 03:42:00"
sep 28 03:27:01 ... Starting blackbox-sample.service ...
sep 28 03:27:02 ... Finished blackbox-sample.service ...
sep 28 03:28:09 ... Starting blackbox-sample.service ...
-- Boot ce37bdb68c044ef28bbe4126623d61be --
sep 28 03:41:52 ... Starting blackbox-sample.service ...
sep 28 03:41:56 ... Finished blackbox-sample.service ...
```

La invocacion que arranco a las 03:28:09 **nunca imprimio "Finished"**. No hay
kill, no hay timeout, no hay fallo registrado para ella en ningun lado del
journal entre esa linea y el reinicio. `Type=oneshot` mas `TimeoutStartSec`
sin declarar (=`infinity`) significa que systemd espera esa invocacion **para
siempre**; y mientras la unit sigue "activating", el siguiente disparo del
timer (`OnCalendar=*:0/1`, cada minuto) no arranca una instancia nueva porque
la unit ya esta activa. Un solo `bb sample` colgado apaga el instrumento
entero hasta que algo externo lo resuelva -- en este caso, el reinicio forzado
por `bb-usable` a las 03:39:21 (`bb-usable.service: Watchdog timeout (limit
6min)!`, funcionando como estaba disenado).

**Por que se colgo esa invocacion en particular, no confirmado a fondo:** a
las 03:28:19, diez segundos despues de que arrancara, el kernel mato por OOM
a un proceso `python` (pid 1463473, cgroup `bb-cap-python-1463463.scope`) --
un proceso DISTINTO, no `bb sample` mismo. La hipotesis mas simple, no
verificada con un repro controlado, es que `bin/bb sample` -- un script bash
que hace fork/exec de varios binarios (`ps`, `nvidia-smi`, lecturas de
`/proc`) -- se quedo bloqueado tratando de hacer fork bajo la misma presion de
memoria que produjo ese OOM kill, posiblemente en estado D (uninterruptible
sleep) esperando IO o memoria para el fork. **No se investigo mas alla de
esto**: no hay traza de pila del proceso colgado, no se reproduce el colapso
a proposito. Declarado, no cerrado.

## Como se cierra

Añadir `TimeoutStartSec=<N>` a `blackbox-sample.service` en las tres copias
(`systemd/`, `adopted/systemd-user/`, la unit real desplegada), para que una
invocacion colgada se mate y libere el proximo disparo del timer en vez de
bloquear indefinidamente.

**Limite declarado del propio arreglo, medido hoy en vivo con
`systemd-run --user --property=TimeoutStartSec=3 sleep 30`:** el timeout
manda SIGTERM (confirmado: `Main PID ... code=killed, signal=TERM`, `Failed
with result 'timeout'`, 3.0s medidos). Si el proceso esta de verdad en estado
D (uninterruptible), ni SIGTERM ni un SIGKILL posterior lo sacan de ahi hasta
que el kernel libere el recurso que espera -- el timeout ACOTA el hueco de
`infinity` a un maximo conocido, no lo elimina por completo bajo cualquier
causa de cuelgue. Sigue siendo estrictamente mejor que hoy: pasa de "hasta el
reinicio" (10-13 min medidos) a "como mucho N segundos, casi siempre".

## Corroboracion en vivo, no buscada

Al desplegar el arreglo y recargar systemd, con la maquina bajo carga real de
esta misma sesion (`load average: 52.40, 60.86, 34.76`), `blackbox-sample.service`
se colgo dos veces seguidas bajo el nuevo `TimeoutStartSec=45`, consumiendo
solo 1.5-4.0s de CPU en los 45s de reloj cada vez -- exactamente el patron
descrito arriba, reproducido sin proponerselo, minutos despues de escribir la
hipotesis. El timer se recupero solo en el siguiente disparo. Ver
`tasks/evidence/.../pass.txt` para las lineas literales del journal.

Esto cambia el marco del hallazgo: no es solo un riesgo de la ventana exacta
de un colapso por OOM, es cualquier pico de contencion suficientemente agudo
-- y en esta maquina, con sesiones de agentes corriendo pytest en paralelo,
esos picos ocurren en operacion normal, no solo en incidentes.
