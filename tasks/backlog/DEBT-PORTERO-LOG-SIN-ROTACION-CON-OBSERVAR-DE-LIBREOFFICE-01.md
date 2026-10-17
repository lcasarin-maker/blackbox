---
id: DEBT-PORTERO-LOG-SIN-ROTACION-CON-OBSERVAR-DE-LIBREOFFICE-01
kind: task
domain: MEMORY
title: "El log del portero no rota y observar de LibreOffice lo hace crecer"
status: open
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
