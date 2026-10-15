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

## Lo que dice el manual instalado (`man systemd-oomd`, `oomd.conf`, 255.4) y por que mis dos primeras pruebas no median nada (2026-10-12)
- Se monitorean los cgroups de unidades con `ManagedOOMMemoryPressure=kill`; al superar el limite durante `DefaultMemoryPressureDurationSec` (20 s) oomd elige un cgroup y le manda SIGKILL a todos sus procesos. **Solo los cgroups DESCENDIENTES son candidatos; la unidad con la propiedad no se mata a si misma**, y solo cuentan las hojas o los cgroups con `memory.oom.group=1`. Mi primera prueba puso la propiedad en el propio scope acaparador: no podia ser candidato.
- Limite por defecto de presion: 60 %; recomiendan ~40 % para `user@UID.service`. `user@.service` ya trae `kill` por un drop-in del paquete (`10-oomd-user-service-defaults.conf`) y `-.slice` trae otro.
- `SwapUsedLimit=90 %`: la accion por swap solo actua si memoria Y swap usados superan el limite; las acciones por swap se ignoran sin swap.
- Aviso explicito del manual: si se activa en `user.slice`/`user-UID.slice`, los programas deben colgar del gestor de usuario o un trabajo pesado hara que oomd mate TODO lo que haya bajo ese cgroup: es exactamente el scope unico de la app de Claude con todas las sesiones.
- Segunda prueba (propiedad en un slice padre `bbtest-oomd.slice` con `MemoryHigh=150M`, hijos de 200 MB y 40 MB, y control negativo en un slice gemelo sin propiedad): ningun hijo murio en 80 s; no se pudo leer la presion del slice (ruta vacia), asi que NO se sabe si se alcanzo el 10 %. Inconcluso, no negativo.
## Que falta (actualizado)
Medir la presion del slice durante la prueba (ruta `/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/<slice>/memory.pressure` o la del padre real), repetirla hasta superar el limite y, solo entonces, concluir. Con root: log de depuracion de oomd y `oomctl`.
## Utilidad para bb (cosecha de diseno, no dependencia)
Senal doble (presion sostenida N s Y holgura), candidatos solo hojas, muerte de un cgroup entero, preferencia por unidad (`ManagedOOMPreference=avoid|omit`) y modo `--dry-run`. Encaja con los cgroups por trabajo del portero: matar el cgroup del trabajo, no el scope de la app.

## Voto de Luis 2026-10-12
Dejar systemd-oomd activo y medir la presion por slice mientras se diagnostica el fallo D-Bus de `oomctl`. Descartado: deshabilitarlo ya (`sudo systemctl disable --now systemd-oomd` sigue disponible y reversible). Riesgo aceptado: puede matar un cgroup entero con presion >60 % durante 20 s.

## Avance 2026-10-13: medicion de solo lectura
`tasks/evidence/DEBT-OOMD-PROBAR-Y-DIAGNOSTICAR-01/medicion-solo-lectura-20261013.txt`: oomd activo, presion del slice del usuario en 0 (some y full avg10/60/300 = 0,00) y `oomctl` con su configuracion (60 % durante 20 s, swap 90 %). La frase `oomd_mata_y_medido` sigue exigiendo un kill medido bajo presion real, que arriesga sesiones y motor; el log de depuracion necesita root.

## Avance 2026-10-14 (lote 'cierra las pendientes conforme a la opcion recomendada'): espera un disparador, no una decision
Disparador doble, ninguno es de solo lectura: (a) el log de depuracion exige un drop-in de root (`sudo systemctl edit systemd-oomd` con `Environment=SYSTEMD_LOG_LEVEL=debug` y `sudo systemctl restart systemd-oomd`; el `edit` recarga systemd, mismo riesgo P1 de la GPU: va en la ventana del motor de 60 min que anuncia Luis); (b) el kill medido arriesga sesiones y motor (la ficha lo dice desde el 2026-10-13): otra vez esa ventana, con Luis presente. Paso exacto que falta: repetir la prueba del slice `bbtest-oomd.slice` leyendo cada segundo su `memory.pressure` hasta que `some avg10` supere el 60 % durante 20 s, anotar que cgroup mata oomd y en cuanto tiempo, y escribir `oomd_mata_y_medido` en `medicion.txt`.
