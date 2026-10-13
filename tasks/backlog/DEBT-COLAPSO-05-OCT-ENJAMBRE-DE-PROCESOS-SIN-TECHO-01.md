---
id: DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01
kind: task
domain: MEMORY
title: "Atribuir y acotar el enjambre del scope de Claude Code que colapso la memoria el 04-05 oct"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-10
close_check: {"cmd": "grep -q . tasks/evidence/DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01/quien-lanzo.txt", "expect": "exit_zero", "porque": "Solo cierra con la evidencia de quien lanzo los procesos y con el techo medido que habria acotado el enjambre."}
---

## Medido (2026-10-10, muestras por minuto y journal de bb-usable)

Dos reinicios del 04 y 05-oct fueron colapsos de memoria, no cortes de energia:

- 04-oct 23:53: reinicio por systemd tras PSI memory full entre 57 y 71 % sostenido.
- 05-oct 00:29: PSI memory full entre 57 y 78 % durante mas de 7 min; load1 llego a 166. `bb-usable` declaro COLAPSO a las 00:22:51 y dejo de acariciar el watchdog a proposito; systemd lo mato por ABRT a las 00:29:33 y el boot termino 16 s despues.

En las muestras, los procesos que mas crecieron en esos minutos colgaban del scope `app-com.anthropic.Claude-39185.scope` (una sesion de Claude Code): pytest-xdist con decenas de workers y varios procesos `java` que llegaron a 31-35 GB de tamano virtual cada uno. `at-f002-nli-calib4.service` aparece despues, en el boot siguiente, a 553 % de un nucleo.

## Hueco

Pasa despues del cierre de DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES (2026-09-28). La guardia por proceso mira UN proceso que crece; aqui eran muchos pequenos bajo un mismo scope. Falta medir que techo de scope habria detenido el enjambre antes de 7 min de PSI alto, y quien lanzo los java.

## Avance, 2026-10-10

La auditoría de `tasks/backlog/DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01/evidence/audit-2026-10-10.md` recuperó 18 muestras válidas del `app.slice`: llegó a 40.32 GiB con PSI full de 49.21 % y carga 1 de 153.85. El `MemoryMax=42G` actual no frenó el episodio. El journal retuvo 40 lanzamientos de pruebas/scripts de Atlas en la ventana, pero cero líneas de Java; no atribuye el launcher de esos procesos.

`bin/bb sample` ahora conserva por scope Claude `memory.current`, `memory.peak`, conteo de procesos y estado de disponibilidad. Cuando PSI full cruza el corte calibrado de 10 con un scope presente, escribe un aviso diagnóstico con los scopes candidatos. La ruta solo lee cgroup v2 y emite telemetría: no envía señales ni cambia límites. Los registros rápidos reducidos de una ráfaga siguen sin recorrer cgroups para mantener bajo su coste.

La ficha permanece abierta: la instrumentación aún necesita muestras reales para calibrar un techo, y el launcher Java histórico no se conserva en las fuentes disponibles.

## Avance 2026-10-13

close_check antes: `grep -q . tasks/evidence/.../quien-lanzo.txt` rc=2 (el archivo no existe). Sigue fallando: el launcher de los Java no se conserva en ninguna fuente.

Construido (solo lectura, sin tocar produccion): `tools/atribucion_enjambre.py` y `tests/test_atribucion_enjambre.py` (11 tests, 99 % de cobertura; la linea sin cubrir es el `if __name__`). Uso: `python -m tools.atribucion_enjambre --desde <ISO> --hasta <ISO>`. Los datos del 04-05 oct SIGUEN en `samples` (RETAIN_DAYS no los purgo todavia, 2026-09-28 en adelante).

Medido con el corpus real (comando literal arriba, ventana 2026-10-05 00:00 a 00:31):
- `app.slice` pico 40.32 GiB, maximo con PSI sano en las 16 jornadas 39.66 GiB: margen 0.66 GiB. Un techo de memoria entre ambos cruza 0 s antes del PSI alto; todo techo que avisa con 1269-1328 s de adelanto (30-38 GiB) habria matado carga sana. La memoria agregada del slice no discrimina el enjambre.
- Incidente del 11-oct 22:44 (primer corpus con `claude_scopes`): el scope `Claude-56782` llego a 36.84 GiB contra 32.92 GiB sano (margen 3.92 GiB); un techo de 34 GiB lo cruza con adelanto 0 s, uno de 30 GiB con 60 s pero mata carga sana. Una sola sesion, no calibra nada.
- Quien crecio el 05-oct: `java` 8 pids distintos observados, hasta 34.5 GiB de crecimiento VIRTUAL (no RSS); `python3` 17 pids, `python` 26. Ningun pid coincide con un scope: las muestras no guardan scope por pid.

Falta: el launcher de los Java (sin fuente), y calibrar un techo por scope con mas incidentes (decision de Luis: alertar sin matar, o techo por conteo de procesos, que `claude_scopes.process_count` ya registra pero que este corpus no permite calibrar).

## Decision de Luis y medicion (2026-10-13)
Luis eligio un techo por conteo de procesos en `observar`. Medido con `python3 -m tools.atribucion_enjambre --desde 2026-10-11T22:30:00-06:00 --hasta 2026-10-11T22:56:00-06:00` (clave `conteo`): el scope del colapso llego a 136 procesos y crecio a 74.0 por minuto; un scope sano llego a 224 procesos y crecio a 72.8 por minuto (margen de tasa 1.6 %, de nivel -39.3 %). Un techo por conteo dispararia sobre carga legitima, asi que la accion queda descartada; `process_count` ya se registra cada minuto en las muestras y el calibrador (`conteo`, con tests) queda listo para recalcularse con cada incidente nuevo que traiga `claude_scopes`. Registro durable en `DECISIONS.md` (2026-10-13).
