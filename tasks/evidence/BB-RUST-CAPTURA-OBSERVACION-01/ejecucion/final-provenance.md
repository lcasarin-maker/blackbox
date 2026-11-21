# Evidencia de la corrección final

La corrección parte del checkout exacto `72b0bd507486105ccb2473e0502d3f5856fe3659`, previamente validado por Sol para `gpt-6-luna` en este worktree. Los artefactos de comparación anteriores se conservan. Esta corrida agrega evidencia con prefijo `final-`, actualiza el recibo del close check y ajusta las recetas/comprobadores Python pertinentes para usar `-B`.

La prueba nueva primero falló contra el comportamiento anterior: el arnés aceptó el destino existente (`rc=0`) donde debía devolver `rc=2`. En verde, rechaza un ring normal preexistente, un lateral `.previo`, un symlink de ring y un symlink colgante `.previo`; comprueba bytes intactos, preservación de enlaces y salida JSON `COULD_NOT_RUN`.

Rust ahora lee el `boot_id` confinado una vez antes de abrir el ring y antes del bucle cronometrado. Reusa la misma cadena en todas las muestras y en la muestra parcial al fallar la apertura. La referencia Python conserva su lectura única previa al cronómetro. La comparación usa el fixture sintético compartido de 256 muestras; cronometra captura y `pwrite` en ambos. Los umbrales existentes y el alcance de durabilidad permanecen iguales.

El close check `cargo test --locked --test captura_observacion` terminó con `19 passed; 0 failed`; la salida literal está en `close-check.txt`, y el comando con `CARGO_TARGET_DIR`, `BB_CAPTURE_SCRATCH`, `TMPDIR`, `CARGO_NET_OFFLINE=true` y `CARGO_INCREMENTAL=0` está en `close-check.command.txt`. La comparación final produjo `PASS`, 256 registros, pérdidas `0/0`, ranuras ilegibles `0/0`, discrepancias estructurales `0`, diferencias de campos `0` y `could_not_run=[]`; resultados en `final-comparison.json`. Los controles adversos del comparador están en `final-negative-controls.txt`.

El control negativo de bytecode mostró `python3 -I` con un `.pyc` creado pese a `PYTHONDONTWRITEBYTECODE=1`, y `python3 -B -I` sin `.pyc`. El inventario del checkout terminó con cero hallazgos. En el control posterior al cierre, `find` contó cero `.pyc` en el checkout y cero bajo `tools/`. Los comandos y salidas están en los archivos `final-pyc-*` y `final-inventory*`.

Sin datos reales ni acceso a hardware/servicios; la medición no certifica durabilidad frente a corte ni el servicio instalado. El SHA del commit local de corrección se registra en `final-sha.txt` después de crearlo.
