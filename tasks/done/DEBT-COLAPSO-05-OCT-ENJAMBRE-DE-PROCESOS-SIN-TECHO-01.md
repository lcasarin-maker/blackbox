---
id: DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01
kind: task
domain: MEMORY
title: "Atribuir y acotar el enjambre del scope de Claude Code que colapso la memoria el 04-05 oct"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "Acotado, sin atribucion (Luis 2026-10-14, reabrible): quien lanzo el enjambre del 05-oct es irrecuperable (el launcher de los java no se conserva en ninguna fuente; el journal retenido de la ventana tiene 9136 lineas y ninguna de java). La clase del enjambre queda acotada: el portero adopta cada suite pesada de app.slice en un scope con MemoryMax=20G y le da turno de una en una, el escalon y los demas actores comparten una lista unica de protegidos (data/procesos_protegidos.json) y la ventana 2026-10-05 00:00-00:31 es un incidente etiquetado en tools/calibra_psi.py."
evidence: {"pass": "tasks/evidence/DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01/pass.txt", "fail": "tasks/evidence/DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01/fail.txt", "e2e": "tasks/evidence/DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01/e2e.txt"}
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-10
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a `grep -q . tasks/evidence/DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01/quien-lanzo.txt`, que no puede cumplirse porque la atribucion es irrecuperable."}
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

## Root Cause
Un enjambre de procesos (pytest-xdist y java) bajo un scope de sesion de Claude Code llevo `app.slice` a 40.32 GiB con PSI full 49 % y el reinicio por watchdog. La guardia por proceso miraba un proceso, no muchos bajo un scope. El lanzador de los java no quedo en ninguna fuente, por eso la mitad de atribucion no puede cerrarse con evidencia.

## Regression Test
Ninguno: la ficha no tenia test por ficha; su close_check era un grep sobre `quien-lanzo.txt`. La cota de la clase la prueban `tests/test_portero.py`, `tests/test_procesos_protegidos.py` y `tests/test_calibra_psi.py`. La auditoria original sigue en `tasks/backlog/DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01/evidence/audit-2026-10-10.md` (no se mueve: la guarda de datos privados la cuenta por esa ruta).

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (las tres piezas citadas por `grep`/`git log` (portero con 20G y turnos=1, lista unica de protegidos leida por los cuatro actores, ventana etiquetada en calibra_psi), el control positivo del journal y el limite medido: las unidades que leen la lista no se han reiniciado desde que llego (reinicio pendiente por voto de Luis)) y `e2e` (la decision registrada). Para reabrirla si el sujeto aparece: `git mv tasks/done/DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01.md tasks/backlog/` y `status: open`.
