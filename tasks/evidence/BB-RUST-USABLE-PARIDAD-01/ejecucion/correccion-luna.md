# Corrección acotada Luna

Base verificada: `d8f363dc89b5b1b1047993b81dd414c5c3610e82`.

## Cambios

- Los errores de ejecución/JSON del oráculo, y la traza ilegible, quedan como `COULD_NOT_RUN`.
- El worker comunica `ISOLATION_OK` y el código de salida `86` reservado para fallos técnicos. Una falla del worker con otro código tras la barrera queda como `FAIL`; el texto libre no decide la clase.
- El control ejecutado dentro de `bwrap` conserva el mismo Python y `SourceFileLoader`, pero recibe `/workspace/bin/bb-usable-instrument-missing`. El `FileNotFoundError` pasa por `assert_output_success` y termina en `rc=86`.
- El caso normal usa el `tests/fixtures/bb_usable_caracterizacion.json` canónico. Su blob es `4a5f1d192172c774e91ce33ebda6e191e41c5ae5`; se retiró la copia `tests/fixtures/usable_paridad/caracterizacion.json`.
- El testigo Python adverso usa `#!/usr/bin/python3 -BI`; las invocaciones Python del arnés usan `-B -I`.

## Ejecución

Comando literal, con compilación y destinos bajo scratch privado:

```sh
CARGO_TARGET_DIR=$HOME/scratch/blackbox/2026-11-21-paridad-luna/cargo-target CARGO_NET_OFFLINE=true BB_USABLE_EVIDENCE=$HOME/scratch/blackbox/2026-11-21-paridad-luna/evidence BB_USABLE_TMP=$HOME/scratch/blackbox/2026-11-21-paridad-luna/tmp cargo test --locked --test usable_paridad
```

Salida literal:

```text
   Compiling blackbox-captura v0.1.0 ($HOME/orca/workspaces/blackbox/bb-rust-usable-correccion-luna)
    Finished `test` profile [unoptimized + debuginfo] target(s) in 2.00s
     Running tests/usable_paridad.rs ($HOME/scratch/blackbox/2026-11-21-paridad-luna/cargo-target/debug/deps/usable_paridad-5a1041b70d8baa22)

running 3 tests
test isolated_worker ... ignored, worker sólo corre por close_check dentro de bwrap
test worker_protocol_separates_instrument_failure_from_subject_failure ... ok
test close_check_runs_subject_and_negative_in_private_bwrap ... ok

test result: ok. 2 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out; finished in 1.26s
```

Control negativo capturado por el worker aislado:

```text
ISOLATION_OK mode=oracle-failure
WORKER_STATUS=COULD_NOT_RUN: oráculo verdadero: fallo_oraculo_ausente: rc=Some(1); stdout=; stderr=Traceback (most recent call last):
FileNotFoundError: [Errno 2] No such file or directory: '/workspace/bin/bb-usable-instrument-missing'
```

Protocolo adverso del mismo test:

```text
subject: rc=0 forbidden_attempts=0
adverse: rc=0 blocked_attempts=4/4
synthetic_oracle_failure: rc=86 classification=COULD_NOT_RUN
subject_adverse_could_not_run=0
```

El control de clasificación también comprueba `ISOLATION_OK + rc=101 -> FAIL` y `sin ISOLATION_OK + rc=101 -> COULD_NOT_RUN`. En el recorrido de sujeto/adverso se contaron `could_not_run=0`; el control técnico sintético se reportó por separado como `COULD_NOT_RUN`.

## Desvío observado

La primera ejecución omitió `CARGO_TARGET_DIR` y creó artefactos en `target/`, fuera de `OWNS`. Se dejaron intactos y no se incluirán en stage.

Comando literal de inspección:

```sh
git status --short -- target | head -5
```

Salida literal:

```text
?? target/
```

Todas las ejecuciones posteriores fijaron `CARGO_TARGET_DIR` bajo `$HOME/scratch/blackbox/2026-11-21-paridad-luna/cargo-target`.
