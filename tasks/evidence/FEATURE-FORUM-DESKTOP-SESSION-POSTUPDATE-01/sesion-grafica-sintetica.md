# Evidencia sintética: sonda de sesión gráfica

Fecha: 2026-11-21. Fixture de compatibilidad informado para systemd
`255.4-1ubuntu8.19`: `loginctl list-sessions --no-legend` entrega ocho columnas
(`SESSION UID USER SEAT TTY STATE IDLE SINCE`). La sonda valida filas con al
menos cinco campos (`ID UID USER SEAT TTY`), UID numérico y campos presentes;
conserva sólo ID numérico o `cNN` y luego consulta cada sesión con
`loginctl show-session <ID> --all -p Active -p Remote -p Type -p Class -p Seat -p Display`.
El runner de prueba exige el argv completo, incluido `--all`.

Los campos vacíos se mantienen por `--all`. Los fixtures X11 y Wayland con
`Display=` vacío cuentan como sesión local observada cuando `Active=yes`,
`Remote=no`, `Seat=seatN` y `Class=user`; no se persisten nombres ni IDs. Una
sesión remota SSH y una TTY no cuentan como escritorio gráfico. Sólo se
clasifica headless cuando `systemctl get-default` declara
`multi-user.target`, GDM se observa inactivo y no aparece un greeter local.
GDM activo sin sesión gráfica local es una categoría observacional. Ninguno de
estos estados prueba que el login funcione, que exista un login loop ni que una
actualización haya causado una falla.

## RED y GREEN

La selección focal se ejecutó con `HOME`, `BLACKBOX_DATA`, `TMPDIR` sintéticos,
autoload/cache/bytecode de pytest desactivados y el flock acordado. En RED se
importó el módulo base desde una copia scratch; los casos discriminantes
fallaron por aserción porque `recoge()` aún no emitía la sonda. En GREEN se
ejercitaron los casos positivos de headless declarado, GDM/greeter, X11,
Wayland, exclusión de SSH/TTY y los controles de errores/ambigüedad:

```text
RED (módulo base): 16 failed, 68 deselected; assertion_count=16; rc=1
GREEN: 18 passed, 66 deselected in 0.13s
pipeline_rc=0
could_not_run=0, skips=0
captura real post-update=COULD_NOT_RUN (CNR operativo 1; lectura viva fuera de alcance)
```

El runner exacto rechaza argv distinto al fixture; los negativos cubren token
de opción e ID inválidos, fila incompleta antes de `show-session`, propiedades duplicadas, denegación
de permisos, estado GDM/target desconocido y salida truncada. Todos devuelven
`NOT_COLLECTED`, nunca un estado sano. La selección actualizó el contrato de
`recoge()` a 18 sondas.

## Delta incremental de presupuesto y filas tabulares

Selección sintética adicional (HOME, BLACKBOX_DATA y TMPDIR sintéticos;
autoload/cache/bytecode desactivados; flock serial; sin lecturas vivas):

```text
python3 -m pytest -p no:cacheprovider tests/test_huella_host.py -k 'recoge_sesion or sonda_sesion or recoge_acepta_fila or recoge_rechaza_fila or presupuesto_completo' -q
RED sobre el padre de este delta (de67): 3 failed, 19 passed, 67 deselected in 0.17s; rc=1
GREEN sobre el delta: 22 passed, 67 deselected in 0.12s; rc=0
ruff check tools/huella_host.py tests/test_huella_host.py
All checks passed!
```

Los tres fallos RED fueron aserciones: la fila `1 x` recibía clasificación
sana pese a sus propiedades de detalle sintéticas; con 51 s y 56 s previos la
sonda gráfica tampoco respetaba el presupuesto del colector. GREEN comprueba
fila tabular de cinco columnas, compatibilidad de ocho columnas y `c21`, el
caso normal con 14 s previos, timeout de 1 s cuando queda un segundo y cero
invocaciones gráficas cuando han transcurrido 56 s. El plazo nuevo sólo limita
esta sonda; no certifica ni altera la duración de las sondas anteriores.
Los logs literales completos se guardan en scratch privado.

## Presupuesto y alcance

`systemd/bb-huella.service` declara `TimeoutStartSec=60`; el helper existente
`host_diagnostics.run_readonly` aplica `timeout=4` por consulta. En `recoge()`,
el plazo gráfico empieza al inicio del colector, vence a los 52 s y limita cada
consulta al tiempo restante. Reserva así 8 s para escritura y salida. Si las
sondas anteriores consumen ese plazo, la sonda devuelve `NOT_COLLECTED` sin
iniciar comandos gráficos; el tiempo de las sondas anteriores no se acota
aquí. El caso sintético normal con 14 s previos observa la sesión; con 1 s
restante, el timeout se acota a 1 s y el resultado es CNR; el fixture de 56 s
previos no inicia ningún comando gráfico. Para una llamada directa se conserva
el límite local de 48 s. El tope de 32 sesiones sigue vigente. Ningún control
esperó en tiempo real ni consultó systemd/loginctl del host.

La fila `1 x`, aunque se acompañe de propiedades de sesión aparentemente
sanas, queda `NOT_COLLECTED` antes de `show-session`. Se validaron formas de
cinco y ocho columnas, incluida la ID `c21`; no se fija el ancho total porque
las columnas posteriores varían por versión.

No se consultaron `/proc` ni `/sys` del host, GPU, journal, red o hardware; la
raíz entregada a `recoge()` y el kernel fueron sintéticos. Tampoco se ejecutaron
servicios ni recuperación. La captura real post-update, validación
OEM, prueba de login funcional y recuperación/rollback siguen pendientes. La
ficha y su `close_check` canónico permanecen abiertos.

Los recibos literales completos RED/GREEN y el runner de baseline se conservan
en scratch privado; este resumen versionado omite rutas locales e identidades.
