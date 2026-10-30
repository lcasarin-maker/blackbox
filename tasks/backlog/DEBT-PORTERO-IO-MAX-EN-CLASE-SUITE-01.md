---
id: DEBT-PORTERO-IO-MAX-EN-CLASE-SUITE-01
kind: task
domain: MEMORY
title: "El portero debe poner tope de disco (io.max) a la clase suite, midiendo que el pre-push no se alargue de mas"
status: open
severity: P2
origin: detected
detector: {"rule": "ficha DEBT-IO-NO-DELEGADO-AL-USUARIO-LAS-SUITES-SATURAN-EL-DISCO-01: io delegado pero sin topes", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-18
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider tests/test_portero.py -k io_max && grep -qx prepush_io_max_medido tasks/evidence/DEBT-PORTERO-IO-MAX-EN-CLASE-SUITE-01/medicion.txt", "expect": "exit_zero", "porque": "Hoy el controlador io esta delegado pero ningun scope de suite lleva IOReadBandwidthMax/IOWriteBandwidthMax. El planificador NVMe es none: IOWeight no sirve, io.max si. Medir antes/despues io_some y duracion del pre-push (hoy ~275-300 s). Riesgo: acotar el disco alarga cada push. 2026-10-30: el titulo exige medir que el pre-push no se alargue; los tests de io_max pasan sin esa medicion, asi que se exige tambien medicion.txt con la linea prepush_io_max_medido."}
---
Seguimiento de DEBT-IO-NO-DELEGADO-AL-USUARIO-LAS-SUITES-SATURAN-EL-DISCO-01.

## Medido 2026-10-18 (tras delegar io)
- `systemd-run --user --scope -p "IOWriteBandwidthMax=/dev/nvme0n1 500M"` + `dd oflag=direct`: 5.1 GB/s con tope y 5.5 GB/s sin tope. El scope NO tiene `io.max`: el tope no se aplico.
- Causa: `user@1000.service` ya ofrece `io` (cgroup.controllers = cpu io memory pids) pero su `subtree_control` y el de `app.slice` no lo activan; el gestor de usuario detecto los controladores al arrancar, antes del drop-in. Escribir `+io` a mano en ambos `cgroup.subtree_control` tampoco basto (systemd no lo adopta).
- Falta: reiniciar el gestor de usuario (cierra la sesion grafica) o reiniciar la ATOM; despues repetir este mismo dd. Solo con `io.max` presente tiene sentido tocar el portero.
- Dispositivo: nvme0n1 (259:0), planificador none.

## Medido 2026-10-27 (tras el reinicio)
- Scope con `-p "IOWriteBandwidthMax=/dev/nvme0n1 500M"`: `io.max: 259:0 rbps=max wbps=500000000 riops=max wiops=max`; sin la propiedad, `io.max` vacio.
- `dd if=/dev/zero bs=1M count=1024 oflag=direct`: 509 MB/s con tope, 4.0 GB/s sin tope. El tope ya funciona en scopes de usuario.

## Implementado (opt-in, apagado por defecto): falta medir pre-push e io_some

Commit `e8123820a6ca2686f408ddee5221edb7e4cbeab0` (rama del worktree, sin push). Decision de Luis 2026-10-27: opt-in por interruptor, apagado por defecto.

- Interruptor nuevo `portero_io` en `interruptores.json` (`tools/interruptores.py`; ausente, ilegible o desconocido vale `off`). El demonio lo relee en cada vuelta.
- `off`: no deriva dispositivo, no pone propiedades IO, la fila queda como antes. `observar`: la fila de la adopcion (y la fila `fin` de `bb portero run`) lleva `"io": {"modo": "observar", "dispositivo", "maj_min", "IOReadBandwidthMax", "IOWriteBandwidthMax", "puesto": false}`. `actuar`: el scope lleva `IOReadBandwidthMax`/`IOWriteBandwidthMax` (`a(st)` en `StartTransientUnit`, `-p` en `systemd-run`), `"puesto": true`, y en la adopcion el portero relee `io.max` del scope y escribe `"io_max"` y `"confirmado"`.
- Solo la clase `suite` lleva tope (`Clase.io_read_bps`/`io_write_bps`); `libreoffice` no. Topes PROVISIONALES, sin calibrar: lectura 2 000 000 000 B/s, escritura 1 000 000 000 B/s (`IO_SUITE_READ_BPS`/`IO_SUITE_WRITE_BPS` en `tools/portero.py`).
- Dispositivo: `st_dev` del directorio de trabajo de la raiz (`/proc/<pid>/cwd`; en `run`, el cwd) -> `/sys/dev/block/<maj:min>` -> padre si es particion -> nodo `/dev/<disco>` de bloques con el mismo maj:min. Rechaza tmpfs/overlay (sin nodo en /sys), dm/md/loop y nodos que no cuadran: no pone tope y escribe `"estado": "NOT_COLLECTED"` con el motivo. En vivo (solo lectura): `/`, `.`, `/tmp` y `/boot/efi` -> `/dev/nvme0n1` `259:0`; `/dev/shm` -> NOT_COLLECTED (0:31); `/snap/antigravity/53` -> NOT_COLLECTED (loop0 apilado).

Evidencia de tests (close_check):
- Antes: `python3 -m pytest -q -p no:cacheprovider tests/test_portero.py -k io_max` -> `46 deselected`, rc=5.
- Despues: `21 passed, 46 deselected`, rc=0.
- Control negativo 1: los 21 tests nuevos contra `tools/portero.py` de master (worktree limpio en `558c8445`) -> `21 failed`, rc=1.
- Control negativo 2 (mutaciones del codigo nuevo, cada una rompe al menos un test): tope sobre la particion -> 10 fallan; observar pone el tope -> 3; off deriva y registra -> 4; `run` sin propiedades IO -> 1; `confirmado` siempre true -> 1; dm apilado aceptado -> 1; sin mutar -> 21 passed.

### Procedimiento de medicion (lo corre Luis)

0. Aterrizar el commit en master y reiniciar el demonio para que cargue el codigo (el interruptor no exige reinicio, el codigo si): `systemctl --user restart bb-portero.service`.
1. Linea base con el interruptor en `off` (hoy esta ausente = off):
   `python3 -c "from tools import interruptores as i;print(i.modo('portero_io'))"` -> `off`.
   En una terminal, muestrear io_some cada 2 s: `while sleep 2; do echo "$(date +%T) $(grep some /proc/pressure/io)"; done | tee /tmp/io_some_off.txt`
   En otra, cronometrar un push real: `cd ~/projects/blackbox && /usr/bin/time -f "push %e s" git push`
   Repetir 3 veces (hoy ~275-300 s). Cortar el muestreo con Ctrl-C.
   Limite: el hook de tests es `simplecode.verification.test_impact`, que elige tests segun el diff; `pre-commit run --hook-stage pre-push --all-files` sobre un arbol limpio NO equivale a un push (no se corrio aqui). Comparar pushes de tamano parecido y anotar cuantos tests corrio cada uno (`N passed` de la salida).
2. Pasar a `observar` y confirmar que el dispositivo derivado es el disco:
   `python3 -c "import json,pathlib;p=pathlib.Path.home()/'.local/share/blackbox/interruptores.json';d=json.loads(p.read_text());d.setdefault('modos',{})['portero_io']='observar';p.write_text(json.dumps(d,indent=2)+'\n')"`
   Correr un pre-push y leer la fila: `grep '"io"' ~/.local/share/blackbox/portero.jsonl | tail -1 | python3 -m json.tool` -> `dispositivo` `/dev/nvme0n1`, `maj_min` `259:0`, `puesto` false.
3. Pasar a `actuar` (mismo one-liner con `'actuar'`) y repetir el paso 1 tres veces, muestreando a `/tmp/io_some_actuar.txt`.
   Mientras corre la suite, leer el tope del scope vivo:
   `for d in /sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/app.slice/bb-portero-suite-*.scope; do echo "$d: $(cat "$d/io.max")"; done`
   -> `259:0 rbps=2000000000 wbps=1000000000 riops=max wiops=max`. Y la fila: `grep '"io"' ~/.local/share/blackbox/portero.jsonl | tail -1 | python3 -m json.tool` -> `puesto` true, `confirmado` true.
   Control negativo de la lectura: en el paso 1 (off) el mismo `for` imprime `io.max` vacio en el scope de la suite.
   Limite: el demonio adopta la suite cuando su RSS pasa `UMBRAL_RSS_SUITE_KB` (4.87 GB), unos segundos despues de arrancar; el tope rige desde ahi, no desde el primer segundo. Si el `for` no encuentra scope, la suite no fue adoptada y la corrida no mide el tope.
4. Comparar: duracion media off vs actuar, y `avg10` de io_some (maximo y media) de los dos archivos. Si el pre-push se alarga de mas, subir `IO_SUITE_WRITE_BPS`/`IO_SUITE_READ_BPS` y repetir 3.
5. Volver a `off` (mismo one-liner con `'off'`), sin reiniciar nada: el demonio lo relee en la siguiente vuelta (2 s) y los scopes nuevos ya no llevan tope. Los scopes vivos conservan su `io.max` hasta que terminan.

Pendiente para cerrar: los numeros de los pasos 1 y 3 y la decision de dejar `actuar` o calibrar.
