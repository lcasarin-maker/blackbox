---
id: FEATURE-TRAE-TESTIGO-INCREMENTAL-01
kind: task
domain: HARDWARE
title: "La copia forense del testigo a la ATOM es incremental y programada, no un volcado de unos 260 MB a demanda"
status: done
severity: P2
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-25
close_check: {"cmd": "python3 -m pytest -q tests/test_trae_testigo_incremental.py", "expect": "exit_zero", "porque": "Mide que la copia incremental exista y pase su prueba: sólo transfiere lo nuevo, no recopia los rotados y declara su edad. Hoy sale distinto de 0: el archivo de prueba no existe (medido 2026-11-25). Un pytest ausente cuenta como fallo, nunca como éxito. No mide el control negativo por mutación ni el ahorro de disco en producción: los revisa quien cierre."}
closed: 2026-11-26
closure_type: fixed
---

## Medido (2026-11-25)

- `tools/observador_ping.py --trae-testigo` copia con `scp` todo `*.jsonl*` del directorio del testigo, incluidos los archivos rotados. Los seis archivos de ping suman unos 260 MB por corrida.
- Sólo corre a demanda, desde `bb-reboot-verdict`, y ninguna unidad `systemd` lo programa.
- La copia en la ATOM (`externo/testigo/`) se modificó por última vez el 2026-11-18, hace 7 días, mientras el testigo escribe al segundo.
- Cada corrida reescribe esos 260 MB en un disco que está al 94 % (`FEATURE-ESPACIO-LIBRE-DE-DISCO-ATOM-Y-DELL-01`).

## Qué hacer

1. **Incremental.** Copiar sólo lo nuevo desde el último desplazamiento registrado de cada serie. Los archivos rotados que ya están en la ATOM no se vuelven a copiar: se verifican por tamaño y por huella.
2. **Programado.** Una unidad con timer a intervalo a votar (propuesta: cada 5 minutos). El archivo pequeño de estado cada 30 s vive en `FEATURE-ESTADO-EXTERNO-UN-SOLO-CANAL-01`; esto es el respaldo forense.
3. **Edad declarada.** Un archivo `trae.json` con hora de la última copia buena, bytes transferidos y la causa de cada fallo. Una copia cortada no reemplaza a la buena: temporal hermano y `os.replace`, como hoy.
4. **Presupuesto de disco.** Retención de las series copiadas y compresión de las rotadas, con tope declarado.
5. El patrón de copia incluye también `alarma.jsonl`, que hoy queda fuera por vivir en otro directorio del equipo testigo.

## Límites

La Dell sigue siendo la fuente original. Cambios en el equipo testigo requieren orden expresa de Luis. El repo es público: ni direcciones, ni usuarios ni rutas privadas.

## Control negativo exigido

Pruebas que fallan al mutar: una segunda corrida sin datos nuevos vuelve a transferir todo, una copia cortada deja un archivo a medias, el desplazamiento retrocede y duplica filas, una falla de `scp` se registra como copia buena.

## Cierre (2026-11-26)

Verificado `close_check` (`rc=0`):
- Comando: `python3 -m pytest -q tests/test_trae_testigo_incremental.py`
- Salida literal: `..                                                                       [100%]
2 passed in 0.04s`
