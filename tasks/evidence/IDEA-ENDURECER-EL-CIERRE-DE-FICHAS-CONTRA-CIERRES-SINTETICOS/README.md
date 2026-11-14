# Falso verde medido, propuesta pendiente

Owner: simplecode. ID existente: IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS.
Ficha canonica en repo simplecode, tasks/backlog con ese ID; se conserva abierta.
medicion.json conserva comando y salida literal de la publicacion previa.
controles.json contiene las salidas de la misma politica antes/despues, Git
ausente y detector retirado, sin sustituir el caso real por el fixture.

close-check-enforce.patch propone el modo opt-in --enforce en la dependencia,
cuatro pruebas y el enlace de evidencia en su ficha existente. source.json
fija el SHA256 original del codigo; git apply --check se ejecuto en el repo
dueno sin modificarlo. Blackbox pide ese modo en simple.json.

La propuesta conserva el clasificador existente: analiza el comando de cierre,
no ejecuta cada close_check. El positivo se ejecuto realmente en su fixture,
y despues se midio el comando correspondiente. No acredita ejecucion de todos
los cierres, contenido de los manifiestos ni el alcance mas amplio de la ficha.
No se reescribe ni se sustituye el close_check de la ventana GPU por existencia.

Propuesta en scratch: 64 passed in 0.33s (60 existentes, 4 nuevos).
Antes, no_ejecuta=1 devuelve 0; con --enforce devuelve 1.
Git ausente devuelve 2; detector retirado devuelve 0 y hace fallar el negativo
(1 failed in 0.05s). Producto del fixture ejecutado: ejecuta=1, rc=0.

El binario instalado todavia rechaza --enforce. Contrato de una fila real con
ese modo: rc=2, could_not_run=1, pass=0, fail=0, pending=0. Es requisito pendiente,
no un gate limpio. No se instalo ni se recompilo el corredor. Antes de publicar:
revision de otra familia, integrar propuesta en simplecode, preparar su corredor
y medir el pre-push completo y sus negativos con el binario resultante.

No se publica desde este encargo. Las tres fichas de privacidad se materializaron
por separado desde su JSON y conservan sus aceptaciones rojas, sin cerrarlas.
