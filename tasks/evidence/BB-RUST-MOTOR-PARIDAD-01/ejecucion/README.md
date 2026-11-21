# Medición del motivo para evaluar el motor

Resultado acotado: **disparador para evaluación**, no autorización para migrar ni actuar. El cribado fijado antes de medir fue p95 local > 1,2 s. En 20 vueltas sin solicitudes fue 0,068481 s (máximo 0,072953; CPU p95 0,057545); en 20 vueltas con 100 solicitudes válidas por vuelta fue 1,824724 s (máximo 1,838667; CPU p95 0,253392; máximo CPU 0,255086). Cada vuelta de carga procesó 100 respuestas y produjo una sola acción restart testigo por deduplicación. No son 100 actuaciones. El conjunto de 100 es una carga sintética acotada, no una frecuencia real medida. El temporizador espera 120 s después de inactividad; 600 s de gracia y 600 s declarados del latido son cosas distintas del timeout HTTP de 120 s. El testigo HTTP responde inmediatamente; no mide espera de red ni presión real.

La corrida diagnóstica separada `diagnostic.txt` usó `strace -f -c -w` y registró 404 `fsync` en 1,189441 s acumulados y 302 `renameat` en 0,016433 s acumulados. Es tiempo de pared trazado en una vuelta, no el p95; el trazado altera el comportamiento temporal. Es evidencia de costo de persistencia en este caso; no demuestra costo atribuible al lenguaje ni ahorro por Rust. Se preservó la durabilidad.

`resultado.txt` registra el comando exacto, base, SHA de arnés, salida y rc: 53 comprobaciones PASS, 0 FAIL y 0 COULD_NOT_RUN en la corrida principal. Incluye ventana viva que impide reinicio y gasto, caso opuesto, vencimiento con compensación, rechazo, plazo, deduplicación, presupuesto y alertas secas. `efectos.txt` conserva el log de testigos del último caso de esa corrida, con unidad ficticia. Cada ejecución usó destino scratch y namespace privado de PID, red, IPC y dispositivos; el repo montado solo lectura. Las pruebas no representan datos operativos ni presión real.

Controles negativos del instrumento, ejecutados con `ejecutar.sh` y el argumento indicado:

- `negative-delay`: `PASS control demora 1.380341 > 1.2`, rc=0; detectó una demora sintética de 1,3 s mediante el mismo umbral de p95.
- `negative-functional`: `FAIL desvio sintetico detectado`, rc=1; alteró una respuesta sintética de rechazo antes de comprobarla.
- `negative-unavailable`: `COULD_NOT_RUN FileNotFoundError: [Errno 2] No such file or directory: '/instrumento-inexistente'`, rc=2.

La primera configuración del arnés omitió el destino de `awk` y el proceso lo silenció: `resultado-invalido.txt` y `diagnostico-invalido.txt` conservan esa evidencia y no sustentan el resultado. Se reparó usando el `gawk` del sistema y se convirtió stderr en fallo del instrumento; se repitió. `resultado-previo.txt` es una corrida posterior a esa reparación pero anterior al ajuste de identidad del arnés.

La condición para reabrir o profundizar incluye carga representativa mayor, presión real caracterizada, plazos incumplidos o incumplimiento contractual atribuible al control. El `close_check` original `cargo test --locked --test contrato_control_motor` permanece intacto y no aplica como cierre de implementación inexistente. Sol decide y un auditor independiente revisa el resultado.

Identidad: base `9b094d50983d05389f08f9c307181505dfbcf58b`. El arnés exige que sea ancestro y que el diff de los tres sujetos y la unidad/timer esté vacío. El control negativo del operador de ancestro fue `git merge-base --is-ancestor HEAD HEAD^` → rc=1; el positivo `git merge-base --is-ancestor HEAD^ HEAD` → rc=0. La comparación de archivos sobre la base devolvió rc=0. Los SHA de criterio y arnés figuran en las salidas. Las estadísticas de proceso incluyen CPU de hijos; el restante tiempo de pared incluye espera de almacenamiento y planificación, no identifica por sí solo una causa.
