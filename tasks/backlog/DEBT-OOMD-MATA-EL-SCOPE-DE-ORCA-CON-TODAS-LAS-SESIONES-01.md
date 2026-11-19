---
id: DEBT-OOMD-MATA-EL-SCOPE-DE-ORCA-CON-TODAS-LAS-SESIONES-01
kind: task
domain: MEMORY
title: "systemd-oomd mato el scope entero de Orca (70 procesos) el 2026-11-17: decidir la politica de oomd"
status: open
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-18
close_check: {"cmd": "grep -q ManagedOOMPreference=avoid \"adopted/system-config/home_@BB_USUARIO@_.config_systemd_user_app-orca-.scope.d_99-blackbox-oomd-avoid.conf\" && grep -q ensayo_avoid_medido tasks/evidence/DEBT-OOMD-MATA-EL-SCOPE-DE-ORCA-CON-TODAS-LAS-SESIONES-01/ensayo.txt", "expect": "exit_zero", "porque": "Falla hoy: no existe el drop-in versionado ni el ensayo. Voto de Luis 2026-11-18 (DECISIONS.md, entrada de esa fecha): proteger a Orca con ManagedOOMPreference=avoid, ensayado antes en las slices bbtest-oomd*. Cierra cuando el drop-in esta versionado y desplegado (bb drift igual) y ensayo.txt registra, con el comando y la salida literales, que oomd elige otra victima dentro del slice de prueba, con su control negativo (la gemela sin avoid)."}
---

## Medido (2026-11-17 19:51:50, evidencia en `tasks/evidence/DEBT-OOMD-PROBAR-Y-DIAGNOSTICAR-01/medicion.txt`)

systemd-oomd mato `app-orca-1461376.scope` completo (70 procesos, 5 h 22 min de CPU, 32.7G de pico) porque la presion de `user@1000.service` fue 55.26 % > 50 % durante mas de 20 s con reclaim. Orca volvio 16 s despues. earlyoom no actuo (`-m 10`, memoria disponible 20.56 %) y `bb-usable` estaba inactivo. Es la consecuencia que esta ficha de origen anticipo el 2026-10-12 (matar el scope de la app con todas las sesiones) y que Luis acepto como riesgo al votar dejar oomd activo.

## Decision de Luis, 2026-11-18 (boleta /vote): proteger a Orca con `ManagedOOMPreference=avoid`

Registrada en `DECISIONS.md`. Descartadas: desactivar oomd y dejarlo como estaba. Pasos, en orden:

1. **Ensayo contenido en las slices de prueba**, antes de 2026-12-18 (si no alcanza, renovar con ficha: `DEBT-SLICES-OOMD-DE-PRUEBA-CADUCAN-2026-12-18-01`): dentro de `bbtest-oomd.slice` dos scopes hijos que acaparan memoria, uno con `ManagedOOMPreference=avoid` y otro sin el; oomd debe matar el segundo. Control negativo: la slice gemela `bbtest-oomd-neg.slice`, sin propiedad de oomd, no mata nada. Leer la presion de la slice cada segundo (el 2026-10-12 la ruta salio vacia). Salida literal en `ensayo.txt` con la marca `ensayo_avoid_medido`.
2. **Drop-in versionado**: `adopted/system-config/home_@BB_USUARIO@_.config_systemd_user_app-orca-.scope.d_99-blackbox-oomd-avoid.conf` con `[Scope]` y `ManagedOOMPreference=avoid`, mas su fila en el inventario de propiedad de `SPEC.md`.
3. **Despliegue por Luis** en `~/.config/systemd/user/app-orca-.scope.d/` (las sesiones de agente no escriben ahi), y `bb drift` en `igual`.

Costo aceptado y limite: ver la entrada de `DECISIONS.md`.

## No medido

Que habria matado oomd sin ese scope; si `avoid` lo habria desviado; que actividad de Orca produjo la presion (el 2026-11-17 la alerta de bb mostro PSI `full` avg10=22.98 un instante despues).
