---
id: DEBT-CONTRATO-ATLAS-INSTRUMENTOS-EN-BLACKBOX-01
kind: task
domain: HARDWARE
title: "Mover a blackbox la medicion de hardware que hoy vive en Atlas y dejar el vinculo en informacion"
status: done
closed_at: 2026-10-11
evidence: {"fail": "tasks/evidence/DEBT-CONTRATO-ATLAS-INSTRUMENTOS-EN-BLACKBOX-01.fail.txt", "pass": "tasks/evidence/DEBT-CONTRATO-ATLAS-INSTRUMENTOS-EN-BLACKBOX-01.pass.txt", "e2e": "tasks/evidence/DEBT-CONTRATO-ATLAS-INSTRUMENTOS-EN-BLACKBOX-01.e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -q reboots.jsonl /home/lcasarin/projects/Atlas/tools/detect_atom_crash.py", "expect": "exit_zero", "porque": "Hoy detect_atom_crash.py mide por su cuenta (journal, Xid, kdump, SMART). Pasa cuando el detector de Atlas LEE las filas de reboots.jsonl / incidentes/*.json de blackbox en vez de re-medir, que es el vinculo de informacion que Luis decidio el 2026-10-11."}
---

## Medido (2026-10-11)

De todo el codigo de Atlas solo dos archivos mezclan varias mediciones de hardware: `tools/detect_atom_crash.py` (768 lineas: `dmesg/Xid/NVRM`, `journalctl`, `pstore/kdump`, `smart/nvme`) y `tools/liberation_watchdog.py` (3866 lineas: `meminfo`, `nvidia-smi`, que decide cuando correr trabajos). Las unidades `ai-gpu-telemetry`, `ai-memory-monitor` y `nvrm-watch` ya son de blackbox (`adopted/`).

## Alcance (ver la enmienda del 2026-10-11 en SPEC.md, "Contrato con Atlas")

1. `detect_atom_crash.py`: la **medicion** (clasificar el boot caido, contar Xid, leer kdump) la hacen `bb reboots` y `bb incident`. Atlas conserva solo lo que **produce conocimiento**: escribir el dictamen en `docs/agent_findings/` a partir del JSON `bb-incident/1` que blackbox deja en `~/.local/share/blackbox/incidentes/`. Sin `import` cruzado.
2. `liberation_watchdog.py`: sus sondas de memoria y GPU deben leer las muestras de blackbox (`atom_gpu_telemetry.jsonl`, `bb sample`) en lugar de re-medir; la politica de admision se queda en Atlas.
3. Medir antes de mover: la ficha DGX-585 de Atlas ya trato el traspaso de `atom_gpu_telemetry.py` y se sabe que una frontera generalizada sin medir fallo una vez (SPEC.md, "Por que la frontera estaba al reves").

Esta ficha es de dos repos: la parte de Atlas la ejecuta su propio flujo (tests, gates, ficha DGX-N), no un parche desde aqui.

## Correccion del alcance (2026-10-11, por pregunta de Luis: "donde deberia vivir detect_atom_crash")

El alcance de arriba dejaba en Atlas "lo que produce conocimiento". Medido despues sobre `detect_atom_crash.py`: solo importa DOS modulos de Atlas, `tools.durable_log.append_jsonl` y `tools.finding_telemetry.telemetry_block`, y solo para **persistir** (estado, `logs/atom_crashes.jsonl` y el dictamen en `docs/agent_findings/`). Su medicion es autonoma (`journalctl`, `smartctl`, `/sys` de EDAC). Conclusion: **el detector completo debe vivir en blackbox**; lo unico que ata a Atlas es donde escribe, y eso lo reemplaza el esquema de hallazgos (ver propuesta en la conversacion del 2026-10-11).

Lo que `detect_atom_crash.py` hace y `bb` aun no (a absorber en `bb reboots`):

| funcion de Atlas | que mide | en bb hoy |
|---|---|---|
| `historial_de_duraciones` + `tendencia_de_degradacion` | duracion de cada boot y si el uptime se degrada entre boots | no existe |
| `salud_de_almacenamiento` | SMART/NVMe (hoy "permiso denegado, requiere root") | no existe |
| `_edac` | contadores EDAC (hoy "sin controladores registrados") | no existe |
| `_boot_caido_termina_en_panic`, `_vmcore_para` | panic al final del boot y vmcore de kdump | parcial (`PANIC_KERNEL` por journal; sin vmcore) |
| `resumen_eventos_sin_crash_confirmado` | alarmas sin crash confirmado | no existe |
| `xids_del_boot` | Xid por codigo | cubierto (`nvrm_y_xid`) |
| `_boots`, `_boot_actual_declara_uncleanly_shutdown` | clasificar el boot caido | cubierto (`bb reboots`) |

Las sondas de `liberation_watchdog.py` (meminfo, nvidia-smi) no se mueven: se reemplazan por la lectura de las muestras de blackbox; la politica de admision de trabajos se queda en Atlas.

## Cierre (2026-10-11)

Hecho el alcance 1 (el que mide el `close_check`): la medicion de `detect_atom_crash.py` se fusiono en `tools/reboot_verdict.py` (no se copiaron 768 lineas: `recoge()` ya leia el journal del boot y del siguiente). Cada fila de `reboots.jsonl` lleva ahora el esquema `bb-reboot/1` y los campos forenses: `journal_danado`, `panic_linea`, `cierre_pid1`, `crash_confirmado`, `lineas_diagnostico`, `xids`, `vmcore`, `hora_inicio`, `hora_fin_registrada`, `duracion_s`, `boot_id_siguiente` y `almacenamiento` (SMART/EDAC). Atlas (`ecdf88cc8`) conserva solo el redactor: lee esas filas sin `import` cruzado, aplica el mismo criterio y escribe `logs/atom_crashes.jsonl`, la alarma de racha y el dictamen.

Tabla de la "Correccion del alcance", fila por fila:

| funcion de Atlas | donde queda |
|---|---|
| `historial_de_duraciones` + `tendencia_de_degradacion` | bb mide `duracion_s` y `crash_confirmado` por boot; la racha es lectura del historial de 22 filas que solo Atlas tiene (desde 2026-08-30) y la usa `atom_degradacion_resuelta.py`: se queda en Atlas como UNA sola copia del criterio, no dos |
| `salud_de_almacenamiento`, `_edac` | bb (`salud_de_almacenamiento`, `_edac`), una foto por corrida en `almacenamiento` |
| `_boot_caido_termina_en_panic`, `_vmcore_para` | bb (`panic_linea`, `vmcore_en`). Cambio deliberado: Atlas atribuia el volcado MAS NUEVO a cualquier crash; bb solo el escrito en el hueco entre el ultimo registro del boot caido y el primero del siguiente |
| `resumen_eventos_sin_crash_confirmado` | lee el historial de Atlas: se queda en Atlas |
| `xids_del_boot`, patrones de diagnostico | bb (`xids_del_boot`, `PATRONES_DIAGNOSTICO`) |
| `_boot_actual_declara_uncleanly_shutdown`, `_boot_caido_declara_cierre_limpio` | bb (`journal_danado`, `cierre_pid1`) |

Escindido, no enterrado: el alcance 2 (sondas de memoria de `liberation_watchdog.py`, `medir_consumo_de_job.py`, `dgx401_medicion_pareada_dos_motores.py`) es `DEBT-CONTRATO-ATLAS-SONDAS-DE-MEMORIA-01`. El despliegue del timer de `atom-crash-detector` a 4 min (despues de `bb-reboot-verdict`, cuya fila ahora lee) es `DEBT-ATOM-CRASH-DETECTOR-TIMER-SIN-DESPLEGAR-01`: la copia versionada ya cambio, la instalada no se toco.

## Root Cause

La frontera de 2026-09-24 dejo `detect_atom_crash.py` en Atlas porque escribia dictamenes en la KB, y con el se quedo tambien la medicion (journal, kdump, SMART, EDAC). La enmienda del 2026-10-11 separa medir de redactar: la medicion es de blackbox y Atlas consume su salida por archivo con esquema.

## Regression Test

- bb, `tests/test_reboot_verdict.py`: patrones de diagnostico (ruido de boot normal vs eventos reales), Xid con pid, `crash_confirmado` (journal corrupto o panic, nada mas), SMART/EDAC declarados cuando no se pueden leer, vmcore solo dentro del hueco del corte, `recoge()` con journal falso (crash, cierre limpio, journal ilegible a `could_not_run`), y `main --escribe` con fila `bb-reboot/1`. Cinco mutantes de la medicion, los cinco cazados.
- Atlas, `tests/test_detect_atom_crash.py`: registro por diagnostico, limpio solo con `cierre_pid1` True, `None` no es limpio, idempotencia, `COULD_NOT_RUN` sin `reboots.jsonl` o con filas ilegibles sin registrar, racha y dictamen, y una guarda de que el modulo no vuelve a medir (con infractor plantado). Cinco mutantes del redactor, los cinco cazados.

## Verification Evidence

- `.fail.txt`: `close_check` antes, rc=1.
- `.pass.txt`: `close_check` despues, rc=0; control negativo sobre el detector anterior rc=1; suites tocadas 58 passed (bb) y 76 passed (Atlas).
- `.e2e.txt`: equivalencia boot por boot sobre los 11 boots reales (0 diferencias; la fila mutada da 2, rc=1); cadena completa bb -> Atlas con `BLACKBOX_DATA` temporal (7 crashes redactados, los mismos 7 y con el mismo diagnostico que ya estaban en el historial real de Atlas); los diez mutantes. Declarado ahi mismo lo que no se ejercito en vivo: rama panic, vmcore real y SMART legible.
