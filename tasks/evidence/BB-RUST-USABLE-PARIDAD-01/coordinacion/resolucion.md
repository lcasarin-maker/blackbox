# BB-RUST-USABLE-PARIDAD-01

**Cerrada para observación offline.** Terra de solo lectura auditó el objeto `b5022aa0f59ec8839b3dad4a1e83e99968ea4db1` (padre `d8f363dc89b5b1b1047993b81dd414c5c3610e82`), dictamen `msg_73098bf052fb`. El coordinador incorporó por avance rápido esa entrega a `lcasarin-maker/rust-observacion-coordinacion`. [Despachos, hallazgos y correcciones](despacho.md) conserva los recibos/modelos y los incumplimientos anteriores.

## Resultado y límites

```sh
scratch=$HOME/scratch/blackbox/2026-11-21-usable-revalida-terra-5UfwSe
CARGO_NET_OFFLINE=true CARGO_TARGET_DIR="$scratch/target" TMPDIR="$scratch/tmp" BB_USABLE_TMP="$scratch/worker" BB_USABLE_EVIDENCE="$scratch/evidence" cargo test --locked --test usable_paridad > "$scratch/cargo.txt" 2>&1
```

Comando acreditado por Terra en `msg_dcfb480e50d9`. Salida literal final, `cargo_rc=0`. En los archivos de evidencia se omitieron las líneas vacías al final.

```text
test result: ok. 2 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out; finished in 1.17s
```

El worker marcado como ignorado en Cargo se ejecutó dentro de bwrap por el gate. El `main` real con reloj, PSI, watchdog y efectos simulados coincidió en 11 escenarios y 92 pasos; `paso_confinado` real coincidió también en 27 combinaciones. La transición integrada empezó en 1 después de 41 pasos generales/off, mantuvo el latido simulado hasta 40, lo retuvo en 41, reinició contador al pasar a general u off y volvió a 1 al regresar a confinado. Resultado final: discrepancias 0, intentos del sujeto 0, cuatro clases adversas detectadas, `subject_adverse_could_not_run=0`. [Salida de Cargo](terra-b5022aa0-close-check.log) y [salida del sujeto](terra-b5022aa0-sujeto.log).

Los cuatro intentos sintéticos cubren señal, acceso al watchdog, socket y comando de unidad. El entorno privado impidió llegar a rutas y procesos operativos. El detector se limita a las syscalls y variantes ejercitadas. La prueba de hardware y el cambio de autoridad operativa se mantienen fuera del ensayo.

## Negativos independientes

- El mismo gate ejecutó el loader de Python sobre ruta ausente, después de `ISOLATION_OK`. El worker declaró `FileNotFoundError` y rc=86 `COULD_NOT_RUN`. Sólo fue la entrada adversa instrumental. [Salida literal](terra-b5022aa0-oraculo-ausente.log).
- En copia scratch del SHA auditado, el auditor cambió el umbral de Rust y ejecutó el mismo `cargo test --locked --test usable_paridad`. Cargo salió 101, clasificado `FAIL` con divergencia de paridad. [Salida literal](terra-b5022aa0-mutacion-umbral.log).
- En otra copia scratch, el auditor introdujo el mismo testigo sintético en la rama de sujeto de `isolated_worker`; Cargo salió 101 y el detector encontró las cuatro clases prohibidas. [Salida literal](terra-b5022aa0-intento-sujeto.log).
- La copia superflua del fixture fue retirada. El único fixture histórico mantiene SHA-256 `034cbb7cda48234c4e49821b5f41c3ea38a301d437cdc2aa7659a9cc2d9b24aa` y se incluye desde su ruta canónica. Estado Git con ignorados y búsqueda de .pyc tuvieron salida vacía antes y después.

La sesión auditora informó que consultó continuidad antes de detectar la ausencia del aviso DGX-703. `cat $HOME/data/director-autonomo/canon-local/backlog/DGX-703.md` devolvió `No such file or directory`. El dictamen del código no detectó bloqueantes ni modificación del checkout.
