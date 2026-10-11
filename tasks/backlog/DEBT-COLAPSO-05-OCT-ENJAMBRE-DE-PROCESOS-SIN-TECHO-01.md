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

La auditoría de `tasks/evidence/DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01/audit-2026-10-10.md` recuperó 18 muestras válidas del `app.slice`: llegó a 40.32 GiB con PSI full de 49.21 % y carga 1 de 153.85. El `MemoryMax=42G` actual no frenó el episodio. El journal retuvo 40 lanzamientos de pruebas/scripts de Atlas en la ventana, pero cero líneas de Java; no atribuye el launcher de esos procesos.

`bin/bb sample` ahora conserva por scope Claude `memory.current`, `memory.peak`, conteo de procesos y estado de disponibilidad. Cuando PSI full cruza el corte calibrado de 10 con un scope presente, escribe un aviso diagnóstico con los scopes candidatos. La ruta solo lee cgroup v2 y emite telemetría: no envía señales ni cambia límites. Los registros rápidos reducidos de una ráfaga siguen sin recorrer cgroups para mantener bajo su coste.

La ficha permanece abierta: la instrumentación aún necesita muestras reales para calibrar un techo, y el launcher Java histórico no se conserva en las fuentes disponibles.
