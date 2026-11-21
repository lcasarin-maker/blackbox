# Criterios fijados antes de comparar Python y Rust

Fecha: 2026-11-21. Base operativa: `systemd/bb-ultimo-aliento.service` en el commit inicial.
SHA antes del primer cambio Rust: `b83ef186a1f34146be6b8f77f497ff2853b9d2ef7250205f4988c40f35229429`.

## Subconjunto observado

Se compara una muestra crítica de `tools/ultimo_aliento.py`: boot ID, timestamp de captura,
PSI `cpu/memory/io` crudo, `MemAvailable/MemFree/SwapTotal/SwapFree/Dirty`, temperaturas
thermal-zone convertidas a °C y `loadavg`. Se omiten del prototipo inventario dinámico, hwmon,
UDP, producción/escritura de `estado_maquina.json`, bloqueo de memoria, supervisión de
`fdatasync` y ciclo del servicio. `--state-check` solo lee una copia fixture para probar el
contrato de frescura; no produce ni publica el snapshot. No se alteran consumidores ni se
presenta esta prueba como paridad del demonio completo.

## Límites predeclarados

- Cadencia de referencia: 250 ms (`INTERVALO_S`); p95 de la operación de captura por fixture
  debe ser <= 25 ms, dejando el resto del período a escritura y planificación.
- RSS máximo del proceso de medición: <= 48 MiB. Es un umbral de RSS de proceso observado,
  no una medición de memoria del cgroup.
- La unidad versionada establece `MemoryMin=48M` y `MemoryMax=96M`; son límites de cgroup
  efectivos para la unidad systemd y no se deducen de RSS. La prueba offline no corre bajo esa
  unidad ni verifica su aplicación.
- Pérdidas permitidas en fixture válido: 0 de 256 muestras. Se cuentan leyendo el anillo
  persistido con el consumidor Python auténtico (`tools.ultimo_aliento.leer_anillo`), nunca a
  partir del `seq` devuelto por el escritor ni del registro en memoria. Todas deben conservar
  la secuencia completa `[0, 1, ..., 255]`, sin huecos ni duplicados.
- Paridad: se leen los 256 registros completos de ambos anillos y se exige igualdad exacta
  por `seq` de boot, timestamp, `tipo`, `ausente`, PSI, meminfo seleccionado, `temp_c` y `loadavg`. El anillo
  debe conservar formato/geometría
  `bb-ultimo-aliento-anillo/1`, 4 MiB, encabezado 4096 B y ranuras 1024 B.
- El archivo de anillo nuevo debe quedar preasignado a 4 MiB; el writer no reutiliza ni pisa
  una ruta existente.
- Controles negativos: una lectura ilegible debe quedar declarada, fuente de estado con sello
  de 6 s debe rechazarse dentro del modo de observación frente al máximo existente de 5 s,
  preservando otros campos capturados, y un destino con padre no-directorio debe informar
  fallo de apertura conservando la muestra parcial por stdout. También se prueba el retorno
  del error real `pwrite` con descriptor de solo lectura. Las aserciones deben detectar cada
  omisión.
- Números `NaN`/infinitos en PSI o loadavg deben marcarse como fuente ilegible en Rust y
  conservar las demás fuentes. Python acepta esos tokens al decodificar/escribir JSON; esa
  divergencia para entradas inválidas queda explícita y no cambia la paridad de entradas válidas.

Las mediciones de Python y Rust se hacen en procesos separados sobre una copia idéntica del
fixture; se guardan por separado antes de comparar. La prueba no reproduce presión real,
hardware, cgroup ni caída eléctrica.

El tramo cronometrado empieza después de abrir/preasignar el anillo e incluye lectura de
fuentes, composición del registro y `pwrite`; excluye `fdatasync` y la lectura de verificación
posterior. El control de padre no-directorio prueba fallo de apertura; el de descriptor
abierto en modo solo lectura prueba fallo `pwrite` del sistema. Se exige el registro parcial
por stdout en el primer caso y retornado por el escritor en el segundo.
La secuencia íntegra y los campos de cada una de las 256 muestras se comparan registro por
registro contra el anillo del baseline Python mediante `leer_anillo`.
La lectura de comparación ocurre tras terminar cada proceso y acredita relectura del anillo,
no durabilidad frente a un corte; el prototipo no sincroniza las muestras con `fdatasync`.
