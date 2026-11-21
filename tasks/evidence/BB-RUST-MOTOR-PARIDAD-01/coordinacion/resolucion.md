# BB-RUST-MOTOR-PARIDAD-01

**Migración descartada por ahora, tras evaluar el rebase.** La carga sintética de 100 solicitudes rebasó 1.2 s y abrió la evaluación. El descarte no se basa en que el cribado haya pasado. Se adopta por la causa medida y la falta de evidencia de un coste atribuible al lenguaje bajo carga operativa representativa. El operador confirmó esta forma de resolver la condición en `msg_67bfe0082150`.

Terra de solo lectura auditó `a69911dcaf575cf5833c911eb364d14e364b935d`, cuyo padre `9b094d50983d05389f08f9c307181505dfbcf58b` fija los sujetos reales. Dictamen `msg_a84db6355320` y lectura íntegra posterior `msg_2cf386e12d28`. Terra completó la lectura y reportó el worktree auditor limpio, incluidos los archivos ignorados. La decisión excluye datos operativos, presión real y actuación real.

## Evidencia de la evaluación

Los umbrales y las cargas se fijaron y comunicaron antes de correr el sujeto. Huella del criterio `f07a1d99105a58b41e7948d784acc1f761db41a6321d2ac425461fa3a7040dc0`, observada por el coordinador en `msg_1f35518d7578`. El umbral de 1.2 s es de cribado sobre los 120 s de inactividad del timer. La gracia de arranque y la vigencia declarada del latido son de 600 s. Las respuestas HTTP fueron inmediatas por testigo.

```sh
bash tasks/evidence/BB-RUST-MOTOR-PARIDAD-01/ejecucion/ejecutar.sh
```

Salida literal de la reejecución de Terra, rc=0. [Log completo](terra-sane.log).

```text
normal: n=20 p95_s=0.073128 max_s=0.074408 cpu_p95_s=0.059022 cpu_max_s=0.059453
carga_100: n=20 p95_s=2.055991 max_s=2.064993 cpu_p95_s=0.290124 cpu_max_s=0.294061
DECISION p95_normal=0.073128 p95_carga=2.055991 criterio_s=1.2 disparador=True
rc=0
```

La repetición independiente de 20 vueltas por escenario comprobó 53 condiciones, con 0 fallos y `could_not_run=0`. En la carga cada vuelta atendió 100 solicitudes y produjo un único reinicio de testigo por deduplicación de acciones consecutivas exitosas. El mismo sujeto ejercitó rechazo, caducidad, ventana viva que suprime reinicio y gasto, conducta opuesta sin ventana, compensación por vencimiento y tope de tres. El bwrap usó PID/red/IPC y dispositivos privados, repo de solo lectura y testigos de servicio/red.

En [diagnóstico separado](../ejecucion/diagnostic.txt), `strace -f -c -w -e trace=fsync,fdatasync,rename,renameat,renameat2` observó en una vuelta 404 `fsync` y 1.189441 s acumulados, más 302 `renameat` y 0.016433 s. El padre reprodujo 404 sincronizaciones en dos vueltas a 100 frente a 4 a cero. La ruta real escribe la respuesta de aceptación y la final, sincroniza el archivo y su directorio y preserva el latido. Esta evidencia localiza coste de persistencia en una carga sintética. El tiempo trazado es diagnóstico, el p95 se mide aparte y la prueba no identifica ahorro atribuible a Rust. [Dictamen](terra-dictamen.md) y [lectura por archivo](terra-lectura-final.md).

## Controles y reapertura

```sh
bash tasks/evidence/BB-RUST-MOTOR-PARIDAD-01/ejecucion/ejecutar.sh negative-delay
bash tasks/evidence/BB-RUST-MOTOR-PARIDAD-01/ejecucion/ejecutar.sh negative-functional
bash tasks/evidence/BB-RUST-MOTOR-PARIDAD-01/ejecucion/ejecutar.sh negative-unavailable
```

- Rc=0 con `PASS control demora 1.369634 > 1.2`, [salida](terra-negative-delay.log).
- Rc=1 con `FAIL desvio sintetico detectado`, [salida](terra-negative-functional.log).
- Rc=2 con `COULD_NOT_RUN FileNotFoundError: [Errno 2] No such file or directory: '/instrumento-inexistente'`, [salida](terra-negative-unavailable.log).

Una corrida exploratoria con `awk` inaccesible quedó invalidada y se conservó. Con `gawk` real accesible y stderr como fallo de instrumento, las corridas finales de sujeto tienen `could_not_run=0`. Las dos líneas de diagnóstico literal con espacio final se preservaron como salidas del instrumento. El auditor de motor leyó la guía con `orca-ide skills get orca-cli --json` pese a que se había definido `ORCA_CLI_COMMAND`. La acción observada fue lectura de la guía, sin mutación conocida. Después usó el ejecutable indicado. La ruta canónica DGX-703 no existía. Los antecedentes y recibos constan en [despacho](despacho.md).

Reabrir ante una carga representativa medida, presión caracterizada que incumpla un plazo, o fallo de contrato atribuible al control. Al comparar un candidato se mantendrían solicitudes, ventana, compensación, límite, durabilidad y autoridad exclusiva, con actuador simulado. El `close_check` original `cargo test --locked --test contrato_control_motor` se conserva para la rama de implementación. No aplica a esta resolución porque la condición de implementar no se cumplió.
