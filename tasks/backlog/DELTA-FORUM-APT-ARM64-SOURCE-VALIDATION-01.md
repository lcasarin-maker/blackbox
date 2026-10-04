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

## Negativo APT real con source incompatible — 2026-10-03

El coordinador ejecutó `apt-get update` contra un source Deb822 `https://archive.ubuntu.com/ubuntu`, suite `noble-updates`, componente `main`, arquitectura `arm64`. Configuración, listas, cache y logs se aislaron en un directorio temporal nuevo bajo `/tmp`; `apt-config dump` corroboró ausencia de hooks Pre/Post-Invoke heredados. El comando devolvió rc100 y `404 Not Found` para `binary-arm64/Packages`; `apt-get indextargets` sobre ese estado aislado devolvió rc0 con salida vacía. could_not_run=0. No se modificaron las fuentes del host ni se ejecutó upgrade/install. Se preservaron comandos, stdout/stderr, configuración y hashes antes de limpiar exclusivamente el directorio creado por el ensayo.

Evidencia: `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/wrong-source-canary/run.json`, `canary.sources` e `isolated.conf`. El negativo pendiente ya está reproducido con APT real. La ficha conserva `open`: falta integrar el verificador, sus regresiones y la comprobación completa del perfil/índices admitidos. El ensayo no aprueba automáticamente repositorios de terceros ni acredita integridad/frescura de todos sus índices.

## Firmas Ubuntu ligadas a bytes archivados — 2026-10-03

Se conservaron los cuatro InRelease locales de noble, noble-updates, noble-security y noble-backports y se ejecutó gpgv sobre cada copia archivada, evitando ligar el resultado a una ruta de cache mutable. `ubuntu-index-signatures/archived-run.json` registra argumentos, stdout/stderr, rc, tamaño, SHA256, hash del keyring y campos firmados. Resultado: signature_pass=4, signature_fail=0, could_not_run=0; 634275 bytes archivados. La comprobación posterior de los hashes y las cuatro firmas volvió a pasar.

La firma acredita esos bytes y ese keyring. Los campos Date son observaciones; los cuatro documentos carecen de Valid-Until. La suite base noble conserva su fecha de publicación de 2024. La comprobación adicional registrada en `ubuntu-index-signatures/package-index-hashes.json` compara los 15 índices Ubuntu Packages enumerados por apt-get indextargets con las entradas SHA256/tamaño de esos manifiestos. apt-helper cat-file descomprimió los bytes locales sin modificar el cache: pass=15, fail=0, could_not_run=0. El alcance comprende los índices Packages enumerados, y deja fuera otros tipos de índices y repositorios de terceros. Sigue pendiente fijar el perfil aprobado de repositorios de terceros y validar la política de actualización efectiva. La ficha conserva open.

Control negativo de hash: `ubuntu-index-signatures/package-hash-negative.json` conserva el resultado de leer un Packages mediante apt-helper, comprobar el baseline contra SHA256 firmado y alterar un byte únicamente en memoria. El tamaño permanece igual y el SHA256 alterado se rechaza: pass=2, fail=0, could_not_run=0. No se modificó el índice del host; este control prueba la comparación de hash y deja separado el ensayo de rechazo por APT.

## Simulación vigente — 2026-10-04

`apt-get -s -o Debug::NoLocking=1 upgrade` terminó rc0: 14 upgraded, 0 newly installed, 0 to remove, 1 not upgraded; could_not_run=0. Al finalizar, los SHA256 de los cuatro InRelease locales siguieron coincidiendo con las copias firmadas archivadas. Evidencia literal: `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/current-upgrade-simulation.json`. Solo se simuló; no se actualizaron índices ni se instalaron paquetes. La simulación conserva el paquete retenido visible y deja pendiente la aprobación/frescura de repositorios de terceros.

## Control sano con índices frescos aislados — 2026-10-04

Se ejecutó apt-get update con Ubuntu ports noble-updates/main/arm64 en un directorio temporal nuevo; configuración, listas, cache y logs separados del host. apt-config dump verificó ausencia de hooks heredados. update devolvió rc0; indextargets enumeró un Packages arm64 y gpgv verificó la copia archivada de InRelease con rc0, could_not_run=0. No se instalaron paquetes ni cambiaron fuentes del host; el directorio temporal se eliminó tras preservar stdout/stderr/comandos y el collector con SHA256. Evidencia `healthy-source-canary/run.json` y archivos contiguos. Este positivo corresponde a un scope Ubuntu aislado; la ficha conserva open por integración del verificador y perfil de repositorios de terceros pendiente.

## Rechazo real de hash y firma por APT — 2026-10-04

Se creó un repositorio file temporal, firmado con una clave RSA de ensayo cuya confianza se limitó al Signed-By del source aislado. Cada fase tuvo listas/cache/config nuevos y apt-config dump verificó ausencia de hooks heredados. APT aceptó el baseline sano (rc0), rechazó un Packages con un byte alterado y tamaño idéntico (rc100, Hash Sum mismatch), y rechazó un InRelease alterado después de firmar (rc100, BADSIG). Resultado de los controles: pass=3, fail=0, could_not_run=0. No se instalaron paquetes ni se cambió la confianza/fuentes del host. El directorio temporal, incluida la clave privada de ensayo, se eliminó. Se archivaron únicamente clave pública, baseline InRelease/Packages, collector y receipt; gpgv volvió a verificar el baseline archivado. Evidencia `signed-integrity-canary/run.json` y archivos contiguos. Es un control local de APT: no reproduce el PPA tercero ni aprueba su perfil.

## Perfil del dueño pendiente de voto — 2026-10-04

Se materializó el inventario efectivo de 19 endpoints en `effective-profile-for-decision.json`, con comando literal, tuplas y could_not_run=0. La presencia en el cache/configuración no equivale a aprobación ni soporte. Se abrió boleta para admitir los 19 endpoints actuales fijando URL/suite/arquitectura/keyring, o limitar el perfil a Ubuntu/ESM y base NVIDIA del sistema, con bloqueo del resto hasta aprobación separada. La boleta define un guard del repo y deja intactas las fuentes del host; respuesta pendiente. El silencio no fija el perfil.

## Comparador de manifiesto integrado en desarrollo — 2026-10-04

Se reutilizó tools/apt_sources.py para parsear entradas SHA256/tamaño/path y comparar los bytes del índice descomprimido. Rechaza secciones duplicadas, rutas repetidas/ambiguas, digest/tamaño inválidos y entradas ausentes; distingue block del índice incoherente de could_not_run del manifiesto incompleto. No autentica la firma por sí mismo. La prueba positiva verifica con gpgv el baseline firmado del ensayo local y el negativo cambia un byte sin cambiar tamaño. Validación focal: 30 passed, 227/227 statements y 96/96 branches, Ruff limpio y gate Pyright canónico 0 errors/warnings/informations. Receipt release-parser-unit-validation.json. La ficha conserva open por perfil pendiente y ensamblaje del verificador completo.

El componente `compare_index_identities` compara conjuntos completos URI/suite/arquitectura/tipo sin aprobarlos: distingue cambios, faltantes y arquitectura Packages sin resolver. Reutiliza el parser existente; no autentica aprobación ni keyrings, no reemplaza validación de fuentes configuradas, firma/frescura/hashes. La prueba focal completa pasa 36 casos con 100% de sentencias y ramas; recibo `index-identity-unit-validation.json`. La ficha y la decisión del perfil permanecen pendientes.

Inventario real adicional: `source-keyring-file-state.json` registra 21 rutas de fuentes convencionales (incluida la ausencia de sources.list si aplica), hashes/modos y 17 keyrings declarados por archivo; apt-config confirma etc/apt, sources.list y sources.list.d. `declared-keyring-fingerprints.json` inspecciona esos 17 keyrings con GPG y home desechable: 0 could_not_run, 0 keyrings cambiados desde el inventario. Se omiten UID y URLs potencialmente autenticadas. Esto no demuestra aprobación, firma de cada repo, confianza global/keys embebidas ni frescura; preserva identidad para comparar posteriormente.

Componente `check_release_freshness` usa fechas del payload separado de autenticación: fechas futuras/caducadas bloquean; fechas ausentes, ambiguas o sin zona y falta de política para Release sin Valid-Until devuelven could_not_run. No se eligió un máximo de edad para repositorios reales. Reutiliza datetime/email.utils de stdlib; 52 pruebas focales pasan y cubren 273 sentencias/118 ramas al 100%. Recibo `release-freshness-unit-validation.json`; aprobación del perfil/política y composición del verificador siguen pendientes.

Captura criptográfica adicional `all-cached-release-signatures/run.json`: 25 InRelease en cache se archivaron antes de verificar contra la unión de 17 keyrings declarados. Primera ejecución: 4 firmas verificadas, 0 fail, 21 could_not_run; una clave ASCII requería conversión GPG nativa a formato binario para gpgv. Se conservó ese resultado y el archivo original, además del derivado/hash. Segunda ejecución: 23 firmas verificadas, 0 fail, 2 could_not_run por clave ausente; 0 keyrings modificados desde inventario. El resultado no liga autorización de keyring a cada repo, ni prueba cobertura de fuentes configuradas, aprobación, frescura o hashes de Packages. Transcripciones con UID no se almacenan: se conservan VALIDSIG, hashes/longitud del output completo y claves/manifiestos exactos para replay. No hubo update/install ni cambio de trust del host.

Los dos PPA usan claves Signed-By embebidas en Deb822, fuera del inventario de keyrings por archivo. `all-cached-release-signatures/embedded-key-recheck.json` archiva claves extraídas con continuaciones/dot de Deb822 y verificación específica por source: 2 pass, 0 fail, 0 could_not_run. `composite-status.json` reconcilia los mismos 25 archivos por SHA: 25 firmas verificadas, 0 sin verificar, 0 could_not_run, 0 source configs embebidos cambiados desde inventario. Las 23 firmas anteriores se validaron contra unión de claves; sólo estas 2 contra su key explícita. La autorización de firmantes por repo sigue pendiente para las otras, así como aprobación humana/frescura/índices. No se alteró trust ni config del host.

`all-cached-release-signatures/source-specific-signatures.json` repite la verificación de los 25 manifests con el Signed-By específico de su URI/suite configurada (incluidas las dos claves embebidas). Resultado: 25 pass, 0 fail, 0 could_not_run; hashes de config iguales al inventario. La fuente libnvidia-container requiere expandir el literal APT $(ARCH), registrado con `dpkg --print-architecture` arm64 y sin evaluar shell. Se conserva el intento inicial de binding incompleto. Este mapeo observado de source/key no reemplaza aprobación humana ni política de vigencia, tampoco prueba que todas las fuentes configuradas hayan actualizado o que sus Packages estén íntegros.

`all-effective-package-hashes.json` registra 40 índices Packages efectivos distintos: 39 SHA256/size coinciden con manifests firmados específicos, 0 mismatch, 1 could_not_run. El restante es libnvidia-container: su Release sólo publica SHA512, no SHA256; el parser actual todavía necesita soporte SHA512 sin fallback a hashes débiles. Se conserva collector y SHA (`all-effective-package-hashes-collector.txt`), comandos nativos y hashes/tamaños; contenido de Packages no se guarda. La fecha firmada de ese Release es 2018-04-27; firma válida e integridad no implican vigencia. Se requieren política explícita y validación temporal antes de aprobar upgrades. No se hizo update/install.

Se amplió el parser compartido para SHA256/SHA512, manteniendo API SHA256 previa y rechazando MD5 u otros algoritmos. `sha512-unit-validation.json`: 54 passed in 0.24s, 279 sentencias/120 ramas, 0 missing/partial, 100%; Ruff limpio y Pyright canónico 0/0/0. Nuevo replay nativo `all-effective-package-hashes-with-sha512.json`: 40 índices efectivos, 40 pass, 0 fail, 0 could_not_run. El recibo anterior 39/0/1 se conserva. Esto prueba consistencia de los índices observados con sus manifests exactos firmados; faltan aprobación/política de vigencia y cobertura de fuentes configuradas/fresh update para cerrar.

`signed-date-policy-observation.json` prueba el componente temporal sin umbral inventado: 1 pass, 0 fail, 24 could_not_run porque esos manifests no publican Valid-Until. Años firmados observados: 2018=1, 2024=1, 2025=3, 2026=20. Se abrió boleta de política de vigencia por repo frente a límite estricto14d; no hay respuesta y no se aplica un límite ni se asume aprobación. La suite global nativa tras integración está en ejecución; su resultado se archivará separadamente.

`configured-source-manifest-coverage.json` reconcilia URIs/suites deb habilitados bajo /etc/apt convencional con los 25 manifests verificados por su key específico: 25 esperados, 25 observados, 0 faltantes, 0 inesperados, 0 could_not_run. No cubre todavía deb-src, overrides de rutas ni la totalidad de componentes/arquitecturas declaradas; esos límites son explícitos. Se conserva la expansión ARCH observada, evitando evaluar shell. Aprobación y política de vigencia siguen pendientes.


Avance del parser Deb822 (2026-10-04): las suites con ruta exacta terminada en `/` omiten Components; las suites de distribución los requieren. Se valida también la combinación inválida de ambos formatos. `python3 -m pytest -q tests/test_apt_sources.py --cov=tools.apt_sources --cov-branch --cov-fail-under=100`: **60 passed in 0.19s**, 289 sentencias y 124 ramas, 0 faltantes, 100 %. Ruff: `All checks passed!`; gate Pyright canónico: `0 errors, 0 warnings, 0 informations`. could_not_run=0 en esta validación. Recibo: `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/deb822-exact-path-unit-validation.json`. La ficha sigue abierta: falta el control original compuesto, aprobación de fuentes y política de antigüedad.


Ampliación de integridad nativa (2026-10-04): `python3 tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/all-effective-index-hashes-collector.txt` produjo `{"indices": 137, "pass": 137, "fail": 0, "could_not_run_count": 0}`. Se verificaron todos los tipos de índices efectivos enumerados, sin filtrar sólo Packages, contra METAKEY/hash/tamaño de los manifiestos archivados y verificados por su Signed-By específico; se comprobó estabilidad del archivo durante lectura. El recibo conserva comandos y hash del collector. No prueba aprobación, vigencia, actualización fresca ni cobertura completa de índices configurados pero ausentes. La ficha sigue abierta.


Componente criptográfico reutilizable (2026-10-04): `verify_release_signature` en tools/apt_sources.py copia entradas regulares acotadas a 8 MiB, sin seguir symlink final ni bloquear en FIFO, y ejecuta gpgv con keyrings explícitos sobre esos bytes. Las copias temporales se eliminan al salir; sólo conserva VALIDSIG y hashes, sin UID. Firma inválida bloquea; clave ausente, proceso inaccesible/salida truncada o formato incompleto producen could_not_run. No concede aprobación ni vigencia. Unit validation: 75 passed in 0.27s, 337 sentencias/138 ramas, 0 missing/partial, 100%; Ruff y Pyright canónico pasan. Replay del componente sobre los mismos 25 manifiestos archivados: pass=25, fail=0, could_not_run=0, changed_manifests=0. Recibos signature-component-unit-validation.json y signature-component-native-replay.json. Original close_check aún pendiente; ficha open.


Aislamiento de confianza (2026-10-04): gpgv ahora usa homedir temporal explícito además de los keyrings proporcionados. Un negativo real intenta verificar el baseline firmado con la clave NVIDIA ajena: devuelve could_not_run=1, fail=0, ningún VALIDSIG y comprueba eliminación del home temporal. El suite focal da 76 passed in 0.27s, 337 sentencias y 138 ramas al 100%; Ruff pasa. Replay tras cambio:25 pass,0 fail,0 could_not_run,0 changed_manifests. Recibos signature-isolated-trust-unit-validation.json y signature-isolated-trust-native-replay.json. La clave ajena es un negativo esperado del test, separado de la ejecución válida del suite; aprobación y vigencia siguen pendientes.


Componente de ensayos APT aislados (2026-10-04): check_isolated_update_control recalcula aceptación o rechazo desde argv/rc/stdout/stderr, con apt-config dump sin hooks, directorios bajo raíz propia /tmp, Error-Mode=any, arquitectura arm64 y rechazo explícito de repos inseguros. Rechaza índices residuales en negativos y cambios de comando hacia install. Receipt authors, source bytes/trust/timing/cleanup siguen siendo gates separados. Recomputación de cinco ensayos archivados (Ubuntu sano, fuente incorrecta, file sano, hash y firma alterados):5 pass,0 fail,0 could_not_run. Suite focal:95 passed in 0.31s,377 sentencias/162 ramas,0 missing/partial,100%; Ruff pasa. Recibos isolated-update-control-replay.json e isolated-update-control-unit-validation.json. Original close_check compuesto sigue pendiente, ficha open.


Matriz integral de cierre: docs/evidence/APT-ARM64-CLOSURE-CRITERIA-2026-10-04.md identifica los12 requisitos y los límites de cada receipt. native-subject-stack.json registra OEM/BIOS/kernel/arquitectura y versiones APT/GPG/keyring actuales con could_not_run=0, sin atribuir retrospectivamente ese sujeto a capturas anteriores. Selector original aún pendiente; ficha open.


Capturas truncadas (2026-10-04): check_isolated_update_control ahora conserva could_not_run cuando config/update/targets declara stdout o stderr truncado, aunque el prefijo tenga rc100 y el marcador esperado. Seis negativos baseline-first cubren los tres receipts y ambas salidas. Suite:101 passed in 0.32s,377 sentencias/162 ramas,0 missing/partial,100%; Ruff pasa. Recibo isolated-update-truncation-unit-validation.json. Cierre integral sigue pendiente.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `user_decision`.
- Impedimento: El perfil aprobado de repositorios externos y la política de frescura siguen pendientes de decisión; la evidencia de APT local no aprueba terceros.
- Evidencia faltante para cierre: decisión registrada de URLs/suites/arquitecturas/keyrings admitidos y cutoff de frescura; ensamblaje/verificación completa posterior
- Siguiente acción: Aplicar la decisión de perfil ya abierta en la boleta y después integrar el verificador con cobertura de fuentes, firmas y frescura.
- Responsable del siguiente paso: Luis para decisión; coordinación BB para implementación.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_02.json`, `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/all-effective-index-hashes-collector.txt`, `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/all-effective-index-hashes.json`, `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/all-effective-package-hashes-collector.txt`, `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/all-effective-package-hashes-with-sha512-collector.txt`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
