# Microfase offline: frescura tras restart

Estado: **parcial; ficha abierta**. La prueba sintética confirma que provider y latencia deben pertenecer a la instancia actual después de cada restart válido. No acredita comportamiento del host, GPU física, proveedor OEM ni recuperación/rollback.

## Cambio

- Cada restart válido invalida sólo provider y latencia actuales.
- El historial de proveedores se conserva: una observación CPU de una instancia anterior sigue bloqueando una request GPU y conserva la atribución al worker original.
- Reutilizar un `worker_id` después de un restart es admisible; la identidad se acompaña del PID. Sin provider o latencia nuevos, el resultado es `unknown`, `could_not_run_count=0`.
- Observaciones GPU y latencia nuevas de la instancia actual pasan; una observación CPU actual bloquea.

## Evidencia y controles

- RED: el test nuevo falló porque la secuencia con dos restarts, retorno al `worker_id` inicial y PID nuevo daba `pass` sin observaciones nuevas. Resultado: `1 failed, 18 passed`.
- GREEN, misma orden de pytest: `19 passed`.
- Control negativo en copia scratch del código base: el mismo test falló en esa aserción (`1 failed, 18 passed`); por tanto, la prueba detecta la regresión que restaura el falso verde.
- La primera invocación del control negativo no pudo crear el proceso porque el directorio de trabajo scratch aún no existía (`CreateProcess: No such file or directory`). Se creó el directorio, se verificó que Python importaba el módulo de la copia scratch y se repitió; el control negativo sí corrió.
- Close check canónico, sólo lectura: `status=unknown`, `could_not_run=1`, `fail=0`, `rc=2`. El propio verificador indica que faltan traza real, validación OEM y recuperación/rollback. Esta microfase no produce esa evidencia física.
- `tools/capture_io.py` ya implementa `strict_json_loads` y `read_regular_bytes`. Se cotejaron sus pruebas existentes: claves duplicadas y números no finitos en `tests/test_provider_trace.py`; FIFO, symlink de ancestro y exceso de tamaño también allí; traversal `..` y límite inválido en `tests/test_runtime_capture_io.py`. No se modificaron esos lectores ni se atribuye este cambio a corregirlos.

## Reproducción

Las órdenes literales con rutas absolutas y los recibos completos se conservaron en el scratch privado del dueño. Las trazas usadas son exclusivamente sintéticas. No se consultaron trazas reales, `nvidia-smi`, red, servicios, carga, sudo, contenedores ni cuentas externas. No hubo integración ni publicación.
