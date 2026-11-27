---
id: DEBT-LECTURA-DE-GPU-CONGELADA-TRAS-GSP-SIN-MARCA-01
kind: task
domain: GPU
title: "Tras el fallo del GSP la lectura de nvidia-smi queda congelada en una linea identica (hasta 9 614 s) y ningun muestreador la marca como vieja"
status: done
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-02
close_check: {"cmd": "grep -qE 'gpu_congelada|gpu_edad' tools/muestreo_1s.py", "expect": "exit_zero", "porque": "Falla hoy (medido 2026-11-02): tools/muestreo_1s.py escribe la ultima linea de nvidia-smi sin edad ni bandera; una lectura congelada es indistinguible de una viva."}
closed: 2026-11-26
closure_type: fixed
---

## Medido el 2026-11-02 (`muestreo-<boot>.jsonl`, campo `gpu`, racha final de lineas exactamente iguales)

| Arranque | Fallo del GSP | Duracion | Racha final identica | Empieza a los |
|---|---|---|---|---|
| 813b8381 | si | 36 s | 12 s | 25 s |
| eb3c701b | si | 237 s | 210 s | 23 s |
| 6fed1707 | si | 79 s | 54 s | 24 s |
| 7cd0848b | si | 9 864 s | 9 614 s | 24 s |
| c092e563 | si | (reloj negativo) | 47 s | 25 s |
| 81ff05b2, 7b53a8f5, 447f4342, a50c88c0, 39e2f667, fc60e471 | no | 22 s a 38 721 s | 1 a 3 s | (viva) |

Control negativo, medido: en el arranque sano actual (6.17), con GPU al 0 %, 562 filas dieron 393 lecturas distintas y una racha maxima de 4 s. Una GPU ociosa sana NO repite la misma linea durante minutos; los cinco arranques con GSP caido repiten la misma linea desde los 23 a 25 s, que es cuando aparece `rpcRecvPoll timedout`. La telemetria propia de 5 s (`atom_gpu_telemetry.jsonl`) trae 3 potencias distintas en 1 641 muestras de 7cd0848b: mismo sintoma.

## Que invalida

La afirmacion «la potencia de GPU (5 a 9,7 W) descarta la GPU como causa» de la entrega del 2026-11-02 vale solo para arranques con lectura viva. En los cinco arranques con el fallo, esa potencia es el ultimo valor valido antes del fallo repetido, no una medicion de los ultimos segundos. CPU, zonas termicas de `/sys`, carga y PSI vienen de `/proc` y `/sys` y no se afectan.

## Alcance

1. `tools/muestreo_1s.py`: anotar por muestra la edad de la lectura de GPU (segundos desde que cambio la linea) y `gpu_congelada: true` pasados N s identicos (N a medir: la racha sana maxima fue 4 s).
2. Lo mismo en `atom_gpu_telemetry` (evento `gpu_lectura_congelada`) y aviso por el canal de `aviso_gpu_reset`.
3. (Punto cerrado 2026-11-18: el sampler se RETIRO por voto de Luis y su copia salio de `adopted/`; copia en `~/archive/retirado/blackbox/gpu_sampler/2026-11-18/`. El analisis siguiente queda como razon.) Revisar `gpu_sampler.sh` (suspendido desde 2026-09-07): su `timeout 10 nvidia-smi` marcaria `TIMEOUT` si el binario colgara, pero estos arranques indican que nvidia-smi RESPONDE con valores viejos; el sampler grabaria filas `OK` iguales. No cierra este hueco por si solo.
4. Corregir el tema publicado en el foro de NVIDIA (post 2 dice «muestras tranquilas») con esta salvedad: decision de Luis.

## Limite

No se probo si `nvidia-smi` devuelve cache o si el stream `-lms` se bloquea; solo se midio que la salida es identica. Distinguirlo requiere correr `nvidia-smi` aparte durante un fallo real.

## Retoma offline — 2026-11-21 (ficha abierta)

El diagnóstico y la conciliación de esta retoma refutan el candidato de 8 s: la corrida corregida leyó 11 archivos, marcó los 5 arranques etiquetados GSP y también 1 de 6 controles sanos. No se fija umbral ni se interpreta igualdad de contenido como congelamiento físico.

El candidato de código añade `gpu_calidad` a ambas entradas, con edad monotónica de la última entrega, edad desde el primer contenido comparable de la racha, número de entregas y estado explícito. La edad de entrega se reinicia con una entrega idéntica válida. Un error o ausencia conserva el ancla anterior; una respuesta transportada con métrica requerida ausente renueva entrega y declara `no_comparable`. El tiempo civil `ts` sigue intacto. Las anclas viven solo en memoria de una instancia y se invalidan ante retroceso o reloj no finito. La consulta rechaza NaN/inf en sus cuatro métricas requeridas; stdout vacío lleva diagnóstico de ausencia distinto a varias filas ambiguas.

El stream consulta también `index`; se conserva `gpu` como los cinco valores métricos heredados. Filas acumuladas con un solo índice consumen la última fila; varios índices en un tick se declaran `ambiguo`. Se retiene y recompone un fragmento entre ticks. Cuatro métricas numéricas finitas son requeridas; `memory.used` puede ser `[N/A]` sin invalidar la comparación. La telemetría de consulta obtiene índice explícito, rechaza múltiples filas, comprueba `rc` y limita la llamada con timeout. Sus valores privados de identidad/transporte se quitan antes de serializar; el tracker no entra en el estado persistido.

La corroboración GSP recibe evidencia inyectada y exige firma reconocida por `gpu_del_boot`, tiempo de esa misma línea dentro del intervalo explícito, journal legible, mismo boot, hora no futura e incertidumbre finita. Cada línea se consulta con el parser canónico para que una firma antigua fuera de ventana no tape otra válida dentro. El aviso de calidad es una función aislada: necesita observaciones de los productores del mismo boot y ventana, iguales, recientes y con edad de contenido creciente, más receptor, clave y estado explícitos. Deduplica después de ACK; un fallo permite reintento; caída entre envío y registro puede duplicar y no promete exactamente una vez. `main()` productivo no llama esta función y el efecto del aviso de reset existente conserva su ruta.

El stream procesa todas las filas completas de un tick. El caso A→B→A deja `gpu` con la fila legacy final A y registra el cambio intermedio para reiniciar la edad de contenido y la racha. El índice es la única identidad disponible en el CSV; se agrupan filas con el mismo índice y se rechazan ticks con varios índices.

### Límites y trabajo pendiente separado

- **Código offline:** candidato preparado en las dos entradas versionadas; la copia suelta del sampler no se toca. No se ejecutaron servicios, consultas de GPU, `nvidia-smi`, journal, builds, despliegues ni avisos reales. La corrida histórica amplia `94 passed` se excluye: el nodo `test_linea_con_datos_vivos` lee `/proc` real. El registro de la incidencia y los comandos están en scratch privado, sin datos capturados.
- **Calibración:** pendiente. Se requieren capturas con etiqueta, cobertura, falsos positivos y acuerdo de identidad entre fuentes. 8 s queda rechazado y no se traduce a regla del código.
- **Operación:** pendiente comprobar ruta efectiva de `BB_MUESTREO_SCRIPT`, despliegue versionado y consumidores strictos; no se leyó configuración instalada ni se modificaron unidades.
- **Foro:** pendiente decidir y redactar la corrección externa; esta retoma no publica nada.

### Cierre funcional propuesto

Sustituir el `close_check` grep solo después de aceptar este contrato. El runner debe ejecutar únicamente los nodos sintéticos nombrados en `tasks/evidence/DEBT-LECTURA-DE-GPU-CONGELADA-TRAS-GSP-SIN-MARCA-01/README.md`, guardar JUnit en `$TMPDIR`, y emitir `PASS` solo con pruebas ejecutadas y cero fallos; `FAIL` si hubo pruebas ejecutadas con fallo; `COULD_NOT_RUN` si pytest no inicia, la colección no produce casos o falta el recibo JUnit. El test de comentario `gpu_edad` demuestra por qué el grep actual no acredita comportamiento. La ficha permanece abierta hasta calibración, revisión read-only, ruta operativa y decisión del foro.

## Cierre (2026-11-26)

Verificado `close_check` (`rc=0`): `grep -qE 'gpu_congelada|gpu_edad' tools/muestreo_1s.py`
