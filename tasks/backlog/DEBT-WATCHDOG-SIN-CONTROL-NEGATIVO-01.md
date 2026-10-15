---
id: DEBT-WATCHDOG-SIN-CONTROL-NEGATIVO-01
kind: task
domain: HARDWARE
title: "Probar que el watchdog SBSA reinicia la ATOM ante un cuelgue (hoy solo esta configurado)"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -qE 'bootstatus=[1-9]' tasks/evidence/DEBT-WATCHDOG-SIN-CONTROL-NEGATIVO-01/prueba.md", "expect": "exit_zero", "porque": "El argumento 'no fue cuelgue porque el watchdog lo habria reiniciado' descansa en la configuracion, que nunca se probo. La prueba es provocar un cuelgue y leer /sys/class/watchdog/watchdog0/bootstatus distinto de cero en el arranque siguiente."}
---

## Por que

Config medida el 2026-10-11: `RuntimeWatchdogUSec=1min`, `/dev/watchdog0` (SBSA), `kernel.panic=10`, panics por lockup activados; `bootstatus=0` tras el arranque por boton. El diagnostico de los cortes abruptos (FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01) usa que un cuelgue se habria reiniciado solo. Es una suposicion hasta tener el caso positivo.

## Procedimiento (ventana controlada, lo corre Luis)

Con vLLM y los jobs parados y los datos guardados: `echo c | sudo tee /proc/sysrq-trigger` provoca un panic y verifica `kernel.panic=10`; para el watchdog puro, congelar el pet de systemd. Tras el arranque, guardar en `tasks/evidence/DEBT-WATCHDOG-SIN-CONTROL-NEGATIVO-01/prueba.md` la linea `bootstatus=N` leida de sysfs y el tiempo medido hasta el reinicio.

## Avance 2026-10-14 (lote 'cierra las pendientes conforme a la opcion recomendada'): espera un disparador, no una decision
Disparador: un reinicio provocado por Luis en ventana controlada (vLLM y trabajos parados). Hoy `bootstatus=0` y `boot_id` 934fa20f-d0ee-4d90-af73-d42abee3e09e (medido). El panic de `echo c | sudo tee /proc/sysrq-trigger` prueba `kernel.panic=10`, no el watchdog: para el caso que exige el close_check hay que congelar el pet de systemd (por ejemplo `sudo kill -STOP 1`) y esperar el reset del SBSA (timeout 60 s). Tras el arranque: `cat /sys/class/watchdog/watchdog0/bootstatus` (el bit 0x20 es reset por watchdog) en `prueba.md` como `bootstatus=N`, y en la misma sesion `sudo -n bb-root-run watchdog-propietario` y `sudo -n bb-root-run arranque-forense`: el mismo reinicio alimenta FEATURE-FORUM-SBSA-WATCHDOG-STATE-01, FEATURE-FORUM-RCU-PANIC-PSTORE-01 y FEATURE-LECTOR-PSTORE-BERT-ROOT-01.
