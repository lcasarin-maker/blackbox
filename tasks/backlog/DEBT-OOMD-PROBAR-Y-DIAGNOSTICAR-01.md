---
id: DEBT-OOMD-PROBAR-Y-DIAGNOSTICAR-01
kind: task
domain: MEMORY
title: "Probar systemd-oomd en esta maquina, diagnosticar su fallo de registro y medir que mataria"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q oomd_mata_y_medido tasks/evidence/DEBT-OOMD-PROBAR-Y-DIAGNOSTICAR-01/medicion.txt", "expect": "exit_zero", "porque": "Peticion de Luis 2026-10-12: medir (no inferir), diagnosticar oomctl y buscar correcciones. Cierra con una medicion que diga si oomd mata un cgroup bajo presion en esta maquina, a cual y en cuanto tiempo, y su convivencia con earlyoom y el escalon de bb-usable."}
---

## Medido (2026-10-12)
- Instalado por Luis: `systemd-oomd 255.4-1ubuntu8.17`, activo, `Status: Processing requests...`.
- `oomctl` falla: `Failed to activate service 'org.freedesktop.oom1': timed out`. `busctl` lista `org.freedesktop.oom1` como solo (activatable); `BusName=org.freedesktop.oom1`, `Type=notify`. El journal de oomd solo muestra Started: sin actividad.
- Prueba con acaparador de ~200 MB en un scope de usuario con `ManagedOOMMemoryPressure=kill`, limite 10 %, `MemoryHigh=120M`: presion `some` hasta 98 % y NO hubo kill en 85 s; el control negativo (sin la propiedad) tampoco. Repetida tras `systemctl --user daemon-reexec` (para que el gestor de usuario se reconectara a oomd): mismo resultado, sin kill.
- `user@1000.service` ya trae `ManagedOOMMemoryPressure=kill` por defecto (Ubuntu): oomd vigilaria la presion agregada de `user@1000`, no scopes sueltos. Inferencia, no medicion.
## Que falta
1. Log de depuracion de oomd (`SYSTEMD_LOG_LEVEL=debug` en un drop-in del servicio: requiere root) para ver a quien monitorea y por que no actua.
2. Diagnosticar por que no toma el nombre D-Bus (`oomctl` expira).
3. Medir que cgroup mataria bajo presion agregada de `user@1000` sin arriesgar las sesiones: en un laboratorio o con `ManagedOOMPreference` en scopes desechables.
4. Decidir convivencia con earlyoom (global) y el escalon de bb-usable (60 s, un proceso): oomd mataria un cgroup entero, posiblemente el scope de la app de Claude con todas las sesiones.
