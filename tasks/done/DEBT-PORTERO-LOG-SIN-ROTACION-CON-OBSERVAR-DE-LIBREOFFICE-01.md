---
id: DEBT-PORTERO-LOG-SIN-ROTACION-CON-OBSERVAR-DE-LIBREOFFICE-01
kind: task
domain: MEMORY
title: "El log del portero no rota y observar de LibreOffice lo hace crecer"
status: done
closed_at: 2026-10-17
closure_type: fixed
reason: "_registra rota portero.jsonl a una sola generacion portero.jsonl.1 (os.replace, bajo flock y con chequeo de inodo) al pasar LOG_TOPE_BYTES = 8 MiB, sin lanzar nunca hacia el demonio; bb portero estado lee tambien .1. Las 80 000 filas del close_check dejan 1.07 MB vivos + 8.39 MB en .1 (antes: 26.2 MB en un archivo)."
evidence: {"pass": "tasks/evidence/DEBT-PORTERO-LOG-SIN-ROTACION-CON-OBSERVAR-DE-LIBREOFFICE-01.pass.txt", "fail": "tasks/evidence/DEBT-PORTERO-LOG-SIN-ROTACION-CON-OBSERVAR-DE-LIBREOFFICE-01.fail.txt", "e2e": "tasks/evidence/DEBT-PORTERO-LOG-SIN-ROTACION-CON-OBSERVAR-DE-LIBREOFFICE-01.e2e.txt"}
severity: P3
origin: detected
detector: {"rule": "tests/test_portero_observar_costo.py::test_el_log_del_portero_tiene_cota_de_tamano", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-17
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider --runxfail tests/test_portero_observar_costo.py::test_el_log_del_portero_tiene_cota_de_tamano", "expect": "exit_zero", "porque": "Medido 2026-10-17 por el agente del portero: la clase libreoffice en observar escribe una fila por conversion, 4.86 filas/s (3.4 kB/s) mientras corre un lote; portero.jsonl pesa 2.18 MB hoy y la retencion de 14 dias de bin/bb solo cubre samples, origen y escalon, no este archivo. Un lote de horas lo llevaria a decenas de MB. Cierra cuando el log del portero tiene cota de tamano (rotar a un archivo anterior) o las filas de observar de una clase se agregan por ciclo; el tope de 16 MiB del test es una propuesta que se ajusta con la medicion."}
---

## Medido
- Agente del portero (2026-10-17, solo lectura): en 30 s de un lote real hubo 545 pids, hasta 10 `soffice.bin` a la vez y cada conversion vivio ~1 s; la clase `libreoffice` en `observar` registro 101 195 bytes (4.86 filas/s, 3.4 kB/s).
- `portero.jsonl` mide 2.18 MB y `bin/bb` rota solo `samples`, `origen` y `escalon` (14 dias): este archivo no entra.
- Hermano ya resuelto en el mismo commit que abrio esta ficha: la memoria `ultimo` del demonio crecia una clave por conversion (300 claves tras 300 conversiones); ahora se poda con `tests/test_portero_observar_costo.py::test_ultimo_no_guarda_arboles_que_ya_no_existen`.

## Que falta
Una cota de tamano para el log del portero (rotar a un archivo anterior al pasar el tope) o agregar por ciclo las filas de observar de una clase, con el test de arriba. Hay que decidir el tope con la medicion de un lote completo en observar, una vez Luis reinicie `bb-portero.service`.

## Root Cause

`_registra` anexaba a `portero.jsonl` sin mirar su tamano, y la retencion de 14 dias de `bin/bb` (RETAIN_DAYS) solo
cubre `samples`, `origen` y `escalon`. Con la clase `libreoffice` en `observar` (una fila por conversion, 3.4 kB/s
durante un lote) el archivo no tenia cota. Las 80 000 filas del close_check lo llevan a 26 240 000 bytes (el
comentario del test estimaba ~18 MB; la fila con `ts` mide 328 bytes).

Arreglo, en `tools/portero.py`:
- `LOG_TOPE_BYTES = 8 MiB` por generacion, con la medicion en su comentario. Tras anexar, si el archivo pasa el tope,
  `os.replace(log, portero.jsonl.1)`: pisa la generacion anterior (queda exactamente una), un lector ve el archivo
  viejo entero o el nuevo, y una caida a mitad deja el log vivo o su `.1` completos.
- Escritores concurrentes (el demonio y cada `bb portero run`): `flock` sobre el archivo abierto y, ya con el
  candado, se comprueba que el inodo abierto sigue siendo el de `log`; si otro lo roto entretanto, se reabre (hasta
  3 intentos, para que el demonio no gire). Asi dos rotaciones simultaneas no pisan `.1` con un log recien creado.
- Contrato intacto: nada sale de `_registra`. Si la rotacion falla (directorio de solo lectura) la fila ya esta
  escrita y se dice en stderr `no se pudo rotar`; si la escritura falla, el mensaje de siempre.
- Lectores revisados: en codigo, el unico lector de `portero.jsonl` es `cmd_estado` (`bb portero estado`, ultimos
  10 eventos). Justo tras rotar el vivo tiene menos de 10 filas, asi que ahora lee `.1` + vivo. Ningun otro modulo de
  `tools/`, `bin/` ni `systemd/` lo parsea (`grep -rn portero.jsonl`); los demas usos son comandos ad hoc citados en
  evidencias (conteos desde una fecha), que con dos generaciones conservan 16 MiB de historia.
- Por que 8 MiB: el close_check exige <= 16 MiB en el vivo; 8 MiB deja margen 2x y mantiene en disco <= 16 MiB
  entre las dos generaciones. Fuera de lotes el log crecio 2.53 MB en 5.6 dias (12 al 18-oct, ~450 kB/dia): una
  generacion son ~18 dias y dos ~37, mas que los 14 dias del resto de `$BLACKBOX_DATA`. En un lote continuo de
  LibreOffice en `observar` una generacion dura ~41 min y dos ~82 min: un lote de horas desplaza los eventos de
  `suite` anteriores. Es el coste aceptado; si esa historia hace falta, el camino es agregar por ciclo las filas
  `habria_*` de una clase (la otra salida que nombraba la ficha), no subir el tope.

## Regression Test

`tests/test_portero_log_rotacion.py` (7 pruebas; sobre el codigo sin modificar: 8 failed contando el close_check,
2 passed):
- rota a una sola generacion y lo que cae es lo mas viejo (sufijo contiguo que termina en la ultima fila);
- control negativo: bajo el tope no rota y no pierde nada;
- si la rotacion falla (directorio 0555) no lanza, la fila queda anexada y stderr lo dice;
- dos escritores (4 hilos x 400 filas) no cortan filas ni dejan huecos por hilo;
- `cmd_estado` muestra los ultimos 10 eventos aunque el vivo acabe de rotar;
- carrera determinista: otro escritor rota mientras este espera el candado; la fila va al log nuevo y `.1` conserva
  la generacion vieja;
- la misma carrera con dos procesos reales: el test sostiene el flock y un `_registra` en otro interprete espera
  (bloqueado a 1.5 s), y al soltarse anexa al log nuevo.
Mas el close_check `tests/test_portero_observar_costo.py::test_el_log_del_portero_tiene_cota_de_tamano`, que sale de
`tests/known_failures.json`.

## Verification Evidence

- fail: close_check contra `tools/portero.py` de 82aaa220: exit 1, 26 240 000 bytes > 16 MiB.
- pass: close_check contra el arreglo: exit 0, `1 passed`.
- e2e: suites del portero sin cambios + la nueva + test_sin_datos_privados + test_inventario: 160 passed, could_not_run 1
  (el test de scopes reales, deseleccionado a proposito). Mutaciones: rotacion apagada -> close_check rojo; borrar
  el vivo en vez de os.replace -> 2 rojos; sin chequeo de inodo -> 2 rojos; sin flock -> 2 rojos (3 corridas), uno de ellos la carrera real
  entre procesos; estado sin `.1` -> 1 rojo; rotacion
  fallida que lanza -> 1 rojo; revertido y verificado con `cmp`.
- Despliegue al demonio en marcha: pendiente de Luis (reiniciar `bb-portero.service`); hasta entonces el demonio
  sigue con el `_registra` sin rotacion.
