# BB-RUST-CAPTURA-OBSERVACION-01

**Cerrada para observación offline.** El objeto auditado fue `61aa1bff1c505a605b539a76e3507d9311fff18b`. Su descendiente directo `21a9e3979166517e59c751185483991aa9d0434e` añade sólo `ejecucion/final-sha.txt`. Sol llevó ambos por avance rápido a `lcasarin-maker/rust-observacion-coordinacion` después del dictamen independiente. El plan y su ficha original permanecen como fuentes del checkout principal, leído en solo lectura.

## Dictamen independiente sobre el SHA

Terra `gpt-6.1-terra`, OWNS de escritura vacío, `bb-rust-captura-cierre-terra`, base exacta `61aa1bff1c505a605b539a76e3507d9311fff18b`, chat `orca_session_id:ae6ab1e5-7c6b-4a58-86b1-f5a58899dace`, lanzamiento `1795291855482-7655b30161334875aad65f87a735f0c1`, prompt `journaled` `1795291856758-1d29bd769d664a55bbfe7b947de3a043`. Parámetros `--setup skip --agent codex --model gpt-6.1-terra --surface chat`. Modelo confirmado en `turn_context` de `01a1ffbb-c0ff-79d0-8c7e-15571871f7c1`. Dictamen `msg_a45063c5f92f`, sin bloqueantes dentro del alcance.

Comandos informados desde el checkout del auditor:

```sh
D=$HOME/scratch/blackbox/2026-11-21-auditoria-captura/terra-final-cs4BBp7F
E=tasks/evidence/BB-RUST-CAPTURA-OBSERVACION-01/ejecucion
BB_CAPTURE_SCRATCH="$D/capture" CARGO_TARGET_DIR="$D/target" TMPDIR="$D/tmp" CARGO_NET_OFFLINE=true CARGO_INCREMENTAL=0 cargo test --locked --test captura_observacion
```

Salida final literal, rc=0:

```text
test result: ok. 19 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.27s
```

La prueba ejercitó PSI ilegible, sello atrasado, error real de `pwrite`, fallo de apertura, captura parcial, fuentes no finitas y destinos de prueba preexistentes. Se rechazaron enlaces externos y entradas de tiempo que desbordan.

```sh
python3 -B -I "$E/baseline_python.py" --fixture tests/fixtures/captura_observacion --ring "$D/capture/python.bin" --samples 256 > "$D/python.json"
BB_CAPTURE_SCRATCH="$D/capture" "$D/target/debug/captura-observacion" --fixture tests/fixtures/captura_observacion --ring "$D/capture/rust.bin" --samples 256 --ts-base 1000000000 --step-seconds 0.25 > "$D/rust.json"
python3 -B -I "$E/compare_rings.py" --python-ring "$D/capture/python.bin" --rust-ring "$D/capture/rust.bin" --python-report "$D/python.json" --rust-report "$D/rust.json"
```

Códigos de salida 0/0/0. [JSON literal de Terra](comparacion-terra-61aa1bff.json). Comparó 256 registros, con pérdidas 0/0, ranuras ilegibles 0/0, diferencias 0 y discrepancias de secuencia 0. Midió latencia p95 y pico de RSS de proceso; el límite prefijado para Rust fue 25 ms y 48 MiB. El perfil Rust fue debug. El tramo común medido incluye captura y `pwrite`; boot se lee una vez antes de cronometrar. La relectura ocurre tras la salida de los procesos. El ensayo cubre el subconjunto sintético de captura descrito en los criterios y deja fuera la durabilidad ante corte, la presión real y la equivalencia del servicio completo.

```sh
BB_CAPTURE_SCRATCH="$D/capture" python3 -B -I "$E/comparison_negative.py"
```

Rc=0 en la repetición válida. Terra reportó un primer intento rc=1 por `FileNotFoundError`, antes de generar los anillos. La repetición detectó 17 informes inválidos con rc=2, exceso válido con rc=1, pérdida de una secuencia en uno y en ambos anillos y alteración de un campo. La salida literal versionada de ese instrumento se preserva en [controles de Luna](../ejecucion/final-negative-controls.txt). Cierre final de Terra `could_not_run=0`, intento recuperado 1, bloqueantes abiertos 0.

### Preservación y contraste con el padre Git

Sobre dos archivos sintéticos que ya existían, Terra ejecutó:

```sh
python3 -B -I "$E/baseline_python.py" --fixture tests/fixtures/captura_observacion --ring "$D/new-ring.bin" --samples 1
```

Rc=2. Salida literal:

```json
{"error":"destino o .previo preexistente; se conserva evidencia","status":"COULD_NOT_RUN"}
```

Centinelas literales reportados tras el comando: `ring sentinel` y `previous sentinel`. Un `.previo` que era enlace colgante también devolvió rc=2, con destino de `readlink` intacto y sin crear el anillo. En una copia del padre obtenida con `git archive 72b0bd507486105ccb2473e0502d3f5856fe3659 | tar -x -C "$D/old"`, el mismo caso dio `old_rc=0 previous=ring sentinel`: el centinela anterior se había reemplazado.

El padre de chat corroboró el boot con `strace -qq -s 300 -e trace=openat,openat2 -o "$trace"` para ocho muestras por binario y `rg -c 'openat2?\([^,]+, "[^"]*boot_id"' "$trace"`. Resultado informado en Orca `msg_382acd0f7fbb`: una apertura en Python nuevo, una en Rust nuevo, ocho en Rust de `72b0bd50`. Terra corroboró leyendo el código que ambas lecturas están antes del reloj.

```sh
python3 -B -I tools/inventario.py --check
HOME="$D/home" TMPDIR="$D/tmp" python3 -B -I "$E/inventory_negative.py"
```

Primer comando rc=0, `[inventario] HALLAZGOS: 0`. Segundo comando rc=0 con la negativa interna observada, `[inventario] HALLAZGOS: 1` y `[negative-control] PASS: el gate bloqueó la herramienta omitida`. `git status --short --ignored` y `find . -name '*.pyc' -print` tuvieron salida vacía antes y después. El control separado de Luna registró 1 caché con `-I` y 0 con `-B -I`. Los incumplimientos de corridas previas y sus efectos constan en el [registro](registro.md).
