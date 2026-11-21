# Registro de ejecución

## Alcance y base

- Modelo confirmado por el coordinador: `gpt-6-luna`; sesión Orca `846636bb-359e-407c-a170-b401b772f414`; recibo de selección `1795292057331-05116264a4134fa18682602d144c416c`.
- Base y `HEAD` al iniciar: `1fc0c179624176d94fd0a2bea78dd36e33456e14`.
- Trabajo limitado a prototipo observable; las lecturas PSI, reloj y sonda se inyectan. Las notificaciones son valores simulados. No se ejecutó una actuación real.
- El confinamiento del oráculo, candidato y control adverso usa `bwrap` con namespaces privados PID/red/IPC, `/proc` privado, `/dev` privado y `/run` tmpfs, repositorio solo lectura y scratch privado. El worker confirma namespaces distintos y ausencia de watchdog, sockets systemd y `NOTIFY_SOCKET` antes de las sondas.
- La traza se limita a `kill`, `tkill`, `tgkill`, `pidfd_send_signal`, `connect`, `sendto`, `sendmsg`, `open`, `openat`, `openat2`, `execve` y `execveat`. Clasifica el primer operando de ruta pertinente, normaliza componentes `.`/`..` y resuelve `openat*` contra anotaciones de dirfd de `strace`. No afirma detectar aliases arbitrarios fuera de esas formas observadas.

## Corrida final

Comando literal: [close-check.command.txt](close-check.command.txt). Salida íntegra: [close-check.log](close-check.log). Resultado: `cargo_test_rc=0`, `1 passed; 0 failed; 1 ignored`; el worker ignorado solo se ejecuta explícitamente dentro del `close_check` aislado. `could_not_run=0`.

El `main` real de `bin/bb-usable` corrió junto con el candidato: 11 casos, 92 pasos, 0 discrepancias de decisiones/efectos por paso. `paso_confinado` real se probó con tres clases de presión, tres modos y tres contadores previos: 0 discrepancias. Secuencia del caso de regreso: 41 muestras general/off no acumulan; confinada actuar empieza en 1 con pet simulado, llega a 40 con pet, 41 retiene; general reinicia a 0; confinado reanuda en 1; off reinicia a 0; actuar vuelve a 1. Modo observar cuenta sin pet.

Comparación caso por caso contra el main real:

| Caso | Pasos | Decisiones/efectos | Contadores del stub histórico frente a `paso_confinado` real |
| --- | ---: | --- | --- |
| `bajo_el_umbral` | 3 | 0 discrepancias | ambos sin eventos confinados |
| `confinado_acaricia` | 12 | 0 | ambos 0,1,2 |
| `confinado_habria_acariciado` | 11 | 0 | ambos 0,1 |
| `ilegible_con_colapso_declarado` | 12 | 0 | stub 0,1; real 0,0 |
| `ilegible_en_mitad_de_racha` | 5 | 0 | ambos sin eventos confinados |
| `ilegible_sin_racha` | 2 | 0 | ambos sin eventos confinados |
| `racha_hasta_colapso` | 11 | 0 | stub 0,1; real 0,0 |
| `recuperacion_tras_bajas` | 14 | 0 | ambos 0 |
| `sonda_fuera_de_plazo` | 3 | 0 | ambos sin eventos confinados |
| `una_baja_no_absuelve_colapso` | 12 | 0 | stub 0,1; real 0,0 |
| `una_baja_no_absuelve_racha` | 7 | 0 | ambos sin eventos confinados |

Las tres diferencias de contador son discrepancias de la caracterización histórica: su stub incrementaba en rutas donde la transición real, en modo off o presión general, resetea a cero. La decisión de latido del `main` real y el candidato coincide en esos pasos. La prueba usa la transición real como autoridad. El escalón independiente se ejecuta y registra por separado; queda fuera del contrato de latido y no se implementó una aproximación Rust de otro actuador.

## Detector adverso y controles

La corrida positiva detectó 0 intentos. El control adverso, dentro de la misma barrera y el mismo detector, observó los intentos sintéticos y clasificó las cuatro clases: señal a PID inexistente, watchdog, socket systemd y cambio de unidad. Los accesos fallaron dentro del sandbox (PID `ESRCH`, watchdog/socket `ENOENT`); la unidad fue un ejecutable testigo privado, nunca `systemctl`.

Controles sintéticos del parser: alias de unidad `/bin/systemctl` y normalización de ruta `3/3`; watchdog absoluto/relativo, incluidos `./watchdog0` y `3</dev>`, `3/3`; `execveat` testigo `1/1`; `/dev/watchdog0` presente solo en argv de `echo`, 0 falsos positivos. El resultado completo consta en los `.trace.stderr` y `.trace.stdout` sujetos a revisión.

## RED, errores del instrumento e incumplimientos

- Antes de reparar la transición confinada, la regresión RED dentro de bwrap falló: tras 41 muestras general/off, el candidato llevaba 33; el esperado al entrar a confinado actuar era 1. El recibo y salida de esa corrida permanecen en `cargo-test-red-confinement.txt` del scratch privado.
- `cargo-test-initial` fue comparación preliminar contra caracterización (17 diferencias); no fue oráculo autoritativo. `cargo-test-01`/`02`/`03`/`07` fueron errores de compilación del arnés. `cargo-test-04` buscó en stdout marcas que se habían escrito en stderr. `cargo-test-08` tenía un testigo adverso que terminaba con éxito y por ello esperaba incorrectamente un fallo. No son fallos del sujeto. La corrida actual ejecuta el oráculo y negativo requeridos.
- Incumplimiento de OWNS: al inicio creé `rust/usable.rs`, fuera del alcance autorizado. Siguiendo el ajuste del coordinador, moví ese contenido a `rust/usable/main.rs`; comprobé el traslado en el mismo worktree. No conservé ni añadí el archivo fuera de OWNS.
- Incumplimiento de la barrera: durante un preflight inicial ejecuté una vez `/usr/bin/systemctl set-property bb-rust-paridad-synthetic.service MemoryMax=1G` dentro de bwrap con namespaces privados, `/dev` privado y `/run` tmpfs. La traza observó `execve` del binario real. El socket del host no estaba montado y el sandbox reportó ausencia/errores de socket; no hay evidencia de que se alterara una unidad. El intento no fue autorizado por la instrucción de usar testigo sintético. Se detuvo ese método; el control adverso final usa exclusivamente un testigo sintético en scratch privado y un socket privado ausente.
- Otro preflight temprano creó un archivo `watchdog` en el `/dev` privado porque ese montaje era escribible; el trazo confirmó ese archivo privado. Ningún dispositivo del host estaba montado. Se corrigió el preflight y el worker final aborta antes de sondas si el watchdog o sockets son visibles.

Los preflights y trazas iniciales están en `$HOME/scratch/blackbox/2026-11-21-bb-usable-paridad/`; el preflight coordinador consultado vive en `$HOME/scratch/blackbox/2026-11-21-usable-preflight-padre/`. No se copió scratch de otro agente.
