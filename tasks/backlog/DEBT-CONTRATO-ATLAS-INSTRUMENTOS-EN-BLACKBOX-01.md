---
id: DEBT-CONTRATO-ATLAS-INSTRUMENTOS-EN-BLACKBOX-01
kind: task
domain: HARDWARE
title: "Mover a blackbox la medicion de hardware que hoy vive en Atlas y dejar el vinculo en informacion"
status: open
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
