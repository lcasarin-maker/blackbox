# Contrato de rectificaciones de `reboots.jsonl`

## Validez

- Una fila normal conserva el `boot_id` no vacio despues de normalizarlo. Puede
  llevar `anula: false`, pero `anula: 0` y cualquier otro tipo se rechazan.
- Una rectificacion valida lleva `anula: true` y `corrige_linea` entero positivo,
  anterior a su propia linea, que apunta a la fila vigente previa del mismo
  `boot_id` en el mismo archivo.
- Una relacion a otro boot, a una linea inexistente, futura o ya no vigente se
  rechaza. La fila anterior sigue vigente y el aviso identifica archivo y linea.
- Una reposicion es una fila normal posterior para el mismo `boot_id`. La ultima
  reposicion valida es la vigente. Las filas originales y las anulaciones se
  conservan byte por byte; ningun lector reescribe el historial.

## Fallos por consumidor

- `tools/reboot_verdict.py::_ya_escritos`: archivo ausente al inicio significa
  historial vacio. Un error de E/S, Unicode, JSON o relacion invalida levanta
  `LedgerReadError`; `--escribe` termina con `rc=2` y no abre el ledger en modo
  append.
- `tools/calibra_calor.py::leer_veredictos`: usa el lector comun, conserva una
  fila valida si una posterior esta incompleta y agrega el aviso a
  `could_not_run`.
- `tools/punto_restauracion.py::arranque_anterior`: usa solo filas vigentes.
- `bb status`: el lector devuelve `0` si existe sucesor vigente, `1` si no
  existe, y cualquier otro rc se muestra como `COULD_NOT_READ` y produce
  `FALTA`. Una fila supersedida no cuenta.

## Evidencia operativa solo lectura

Comando:

```sh
SCRATCH_DIR="${SCRATCH_DIR:?ruta privada en scratch}"
BLACKBOX_LEDGER_PATH="${BLACKBOX_LEDGER_PATH:?ruta privada del ledger}"
sha256sum "$BLACKBOX_LEDGER_PATH" | tee "$SCRATCH_DIR/reboots-ledger.sha256"
```

Salida antes y después de la inspeccion: `c898f917b32bc40469bc1e65a09f9f36f9b5a54cce7048e7004d393b4737e686`.
La ruta concreta se mantiene privada en `BLACKBOX_LEDGER_PATH`; la salida se
guarda en `SCRATCH_DIR`.

El archivo tenia 61 lineas y 3,041,762 bytes. Las lineas originales 23 y 24
apuntaban a `cd2e65eee13846249fc0d5a7145aa565`; las anulaciones 25 y 26
referenciaban respectivamente 23 y 24. Las filas vigentes verificadas fueron:

- `7cd0848b8fc742e982970cc9697c34e9` →
  `2f73178e2f3c4e4084ba38a6012c56ab`.
- `fc60e471d9c149648b0d1ea922fc9e57` →
  `e0666a39e3194129be9bcb663dc0891e`.

No se modifico el ledger operativo.
