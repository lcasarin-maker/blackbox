---
id: DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01
kind: task
domain: VERDICT
title: "Validar forum apt arm64 source validation 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_apt_arm64_source_validation_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01.** En DGX Spark/Noble arm64, un dueño publicó `ubuntu.sources` mezclando `archive.ubuntu.com` (404 en binary-arm64) y `ports.ubuntu.com`; soporte NVIDIA indicó `ports.ubuntu.com/ubuntu-ports` como fuente Ubuntu esperada. En paralelo, un PPA NVIDIA Vulkan reportó tamaño/hash inesperado durante sincronización de espejo, y otro usuario luego obtuvo `apt update` limpio. El autor dijo que retirar el archivo con source incorrecta restauró apt, pero sincronización y cambio de source no quedan aislados ([355471](https://forums.developer.nvidia.com/t/355471)). Validar perfil de repos aprobado y frescura/integridad de índices antes de upgrades; no borrar fuentes automáticamente ni continuar sobre índices stale.

Fuentes: tasks/backlog/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Inspección local de solo lectura (2026-10-03)

En el host actual, `dpkg --print-architecture` devuelve `arm64`; `/etc/apt/sources.list.d/ubuntu.sources` usa `http://ports.ubuntu.com/ubuntu-ports/` para Noble y sus pockets. `apt-get indextargets` lista índices Ubuntu arm64. `gpgv --keyring /usr/share/keyrings/ubuntu-archive-keyring.gpg ...noble-updates_InRelease` verifica la firma del índice local, cuyo campo `Date` dice 2026-10-03; `apt-get -s -o Debug::NoLocking=1 upgrade` termina con rc=0 y cero paquetes por remover. El control negativo altera `Suite` en una copia temporal del mismo InRelease; `gpgv` devuelve rc=1 y `BAD signature`. Comandos y stdout crudos: `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/commands.json`. Esta observación demuestra configuración local de Ubuntu apta para arm64 e integridad de la firma de ese índice, sin fijar un cutoff de frescura arbitrario ni afirmar que la matriz de repositorios de terceros sea aprobada. No se cambió la configuración ni se ejecutó `apt update`. El close_check aún no existe y la ficha sigue abierta: queda sin reproducir el negativo de source Ubuntu incompatible que describe el foro.

## Avance de instrumento — 2026-10-03

`tools/apt_sources.py` parsea el archivo Deb822 activo, lee la arquitectura nativa y los tuples efectivos de `apt-get indextargets`. Diagnostica solo la contradicción de endpoint Ubuntu ya observada (`archive.ubuntu.com/ubuntu` con `arm64`); conserva los endpoints desconocidos como no evaluados. La captura local `tasks/evidence/BB-INSTRUMENTS-2026-10-03/apt-sources-capture.json` salió `observed`, `could_not_run_count=0`, 54 tuples efectivos, cuatro tuples configurados de Ubuntu ports y 26 tuples de índices no evaluados. Los valores gpgv previos siguen limitados al `InRelease` de `noble-updates` y al keyring Ubuntu que muestran `commands.json`; el capturador nuevo no afirma verificar firmas ni frescura. Sin fallo reproducido en APT real ni negativo source configurado en un sujeto canary, permanece abierta.
