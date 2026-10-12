---
id: FEATURE-BB-EVALUAR-CAP-DE-CPU-01
kind: task
domain: HARDWARE
title: "Medir en esta ATOM el efecto de topar la CPU a 2400 MHz sobre la zona termica del SoC"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -q 'scaling_max_freq' tasks/evidence/FEATURE-BB-EVALUAR-CAP-DE-CPU-01/ab.md", "expect": "exit_zero", "porque": "Solo cierra con el A/B medido aqui (misma carga, zona termica y tiempo de pared con y sin cap), con rollback. Hoy el archivo no existe."}
---

Conocimiento en Atlas: `knowledge/investigations/gb10_cortes_2026-10-11/hilos/hilo_380238_*` (L41 y L69): cap de CPU a 2400000 kHz en `cpufreq/policy*/scaling_max_freq`, A/B con la misma carga: zonas sostenidas 92 a 84 C y 85 a 80 C, mismo tiempo de pared (n=2 nodos, Founders Edition). El mismo hilo trae el comando exacto (L212).

Por que aqui: en esta unidad la zona ACPI sostiene 94-96 C con la GPU en 84 C y el trip critico es 104.8 C (telemetria del 11-oct 11:50 a 12:13); el calor esta en el SoC, no en la GPU. Es una palanca que el cap de GPU no toca.

**Decision del dueno antes de aplicar:** cambia un ajuste del sistema (requiere sudo). Medir primero con `atom_gpu_telemetry` una ventana con cap y otra sin, con carga equivalente, y comparar `residencia_termica_del_boot` de `bb incident`.

## Decision del dueno (2026-10-11): medir un A/B aqui antes de aplicar nada

Elegida la opcion "Medir un A/B aqui primero". No se aplica ningun cap permanente.

**Estado medido de esta ATOM (punto de vuelta atras):** 20 policies de cpufreq en gobernador `performance`. 10 policies (`policy0-4`, `10-14`) con `scaling_max_freq = cpuinfo_max_freq = 2808000` kHz y 10 (`policy5-9`, `15-19`) con `3900000` kHz. Un cap uniforme de `2400000` (el del hilo 380238) recorta ~38 % a los nucleos de 3900 MHz y ~15 % a los de 2808 MHz: el efecto no es el mismo que en las Founders Edition del hilo. Rollback exacto: devolver cada policy a su `cpuinfo_max_freq`.

**Protocolo propuesto (lo corre el dueno con sudo, sin tocar produccion hasta tenerlo):** 1) Ventana A, 2 h de carga habitual sin cap; 2) Ventana B, 2 h con el cap, misma carga (mismas peticiones de vLLM); 3) comparar `residencia_termica_del_boot` y `throttle_del_boot` de `bb incident` y el tiempo de pared del trabajo; 4) restaurar y guardar el resultado en `tasks/evidence/FEATURE-BB-EVALUAR-CAP-DE-CPU-01/ab.md`.

La carga debe ser equivalente: el 11-oct el calor del SoC convivio con otros procesos (24 `wineboot` huerfanos de otra sesion de 13:44 a 16:30, `load` 58.8), que contaminan un A/B si no se controlan.
