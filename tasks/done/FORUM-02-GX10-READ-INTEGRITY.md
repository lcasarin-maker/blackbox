---
id: FORUM-02-GX10-READ-INTEGRITY
kind: task
domain: STORAGE
title: "Detectar lecturas corruptas en caché antes de confiar en pesos de modelos"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "Exige un segundo ASUS GX10 alcanzable por SSH como referencia de hashes; este equipo es una GIGABYTE AI TOP ATOM sola, sin ~/.ssh/config y sin otro nodo en /etc/hosts. Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si aparece aqui una lectura buffered que difiera de O_DIRECT o si se anade un segundo nodo."
evidence: {"pass": "tasks/evidence/FORUM-02-GX10-READ-INTEGRITY/pass.txt", "fail": "tasks/evidence/FORUM-02-GX10-READ-INTEGRITY/fail.txt", "e2e": "tasks/evidence/FORUM-02-GX10-READ-INTEGRITY/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/FORUM-02-GX10-READ-INTEGRITY.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m tools.verify_forum_finding --id FORUM-02-GX10-READ-INTEGRITY --evidence tasks/evidence/FORUM-02-GX10-READ-INTEGRITY`, el verificador de hallazgos de foro, que sin captura real del sujeto sale con could_not_run; sin sujeto aqui no hay captura posible."}
---

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/asus-ascent-gx10-changing-file-checksums-cached-reads-differ-from-o-direct/382456
- https://forums.developer.nvidia.com/t/asus-ascent-gx10-changing-file-checksums-cached-reads-differ-from-o-direct/382456/1
- https://forums.developer.nvidia.com/t/349121

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Trabajo

Preparar una comprobación de solo lectura para archivos de prueba o una copia en staging: calcular hashes repetidos con I/O buffered y alineado `O_DIRECT`, comparar contra un manifiesto de confianza generado en otro nodo/medio, y correlacionar con `POSIX_FADV_DONTNEED`, logs del kernel, versión de firmware, `smartctl`/NVMe health y cualquier fuente RAS disponible en el OEM. Registrar lecturas discrepantes, bytes/rangos, versión completa de la pila y errores de colección. No tratar una lectura directa correcta como prueba única de que el resto del hardware está sano.

Si se reproduce en datos inmutables con referencia externa, detener la carga que dependa de esos datos y preparar diagnóstico oficial de ASUS/NVIDIA (incluido Field Diagnostics cuando el fabricante lo indique) y escalación/RMA si persiste. No borrar cachés de producción ni ejecutar escrituras de estrés desde Blackbox. Una corrección de kernel/driver solo se recomienda tras una A/B en equipo recuperable y evidencia de que corrige el resultado.

## Riesgos y cierre

Auditar modelos completos puede usar bastante I/O, memoria y tiempo, y el hash de archivos propietarios puede revelar metadatos operativos. Limitar pruebas iniciales a muestras pequeñas, staging, periodos ociosos y manifiestos fuera del nodo sospechoso. Mantener intactos los archivos originales; no reescribir, eliminar ni descargar de nuevo pesos antes de preservar la evidencia.

Cerrar con control sano (referencia externa idéntica en buffered y `O_DIRECT`), control negativo que altere bytes y sea detectado, salida literal para una región discrepante, límites/coste medidos de la inspección, y una ruta que declare `COULD_NOT_RUN` por acceso insuficiente. Si el OEM no expone señales RAS/EDAC/BERT/NVMe legibles o la prueba no reproduce el caso, conservar esa limitación; no cerrar atribuyendo la causa al disco, RAM o driver sin evidencia independiente.

## Instrumento desarrollado — 2026-10-02

`python3 -m tools.read_integrity ARCHIVO --offset 0 --length 4096 --sha256 DIGEST` compara dos rutas de lectura reales: descriptor buffered separado de descriptor O_DIRECT. Limita región a 1 MiB, alineación 4096 y repeticiones a cinco; conserva errores como could_not_run, comprueba identidad/estabilidad del archivo y requiere digest suministrado por el caller, cuya procedencia no puede autenticar. No altera archivos ni caché global.

Controles de fixture: flags separados, cambio de archivo entre aperturas, O_DIRECT inaccesible con cierre del descriptor previo, digest incorrecto, lectura truncada y errores de acceso. Verificación real de instrumento sobre archivo temporal sano y referencia deliberadamente incorrecta en `tasks/evidence/FORUM-02-GX10-READ-INTEGRITY/read-integrity-instrument.txt`. Esa referencia fue generada para el fixture, no en otro nodo de confianza. Sigue open: faltan dataset/referencia independientes, comparación del incidente y correlación NVMe/RAS/firmware; el instrumento reporta la región discrepante, no el byte exacto.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: La lectura local de instrumento no contrasta bytes de storage con referencia externa ni separa modos de caché/NVMe/firmware.
- Evidencia faltante para cierre: referencia externa confiable y bytes esperados; resultados buffered/O_DIRECT/cache; salud NVMe y evidencia firmware; control corrupto
- Siguiente acción: Preparar ensayo no destructivo con datos de referencia y comparación buffered/O_DIRECT en el GX10, documentando cache/NVMe/firmware y control negativo.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/FORUM-02-GX10-READ-INTEGRITY.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_02.json`, `tasks/evidence/FORUM-02-GX10-READ-INTEGRITY/host-observation.txt`, `tasks/evidence/FORUM-02-GX10-READ-INTEGRITY/read-integrity-instrument.txt`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Root Cause
No aplica a este equipo: la comparacion exige un segundo GX10 como referencia externa de hashes alcanzable por SSH. Aqui hay una sola GIGABYTE AI TOP ATOM, sin `~/.ssh/config` y sin otro nodo en `/etc/hosts`.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. No tenia test xfail propio; su close_check era `tools.verify_forum_finding`, que sigue vivo para las demas fichas de foro (y `tests/test_closure_hardware.py::test_forum_finding_supports_every_original_id` sigue comprobando que el verificador soporta este id).

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido, con control positivo de que las mismas herramientas encuentran lo que si existe) y `e2e` (la decision registrada). Datos de la maquina redactados con el PATRON de `tests/test_sin_datos_privados.py`. Para reabrirla si el sujeto aparece: `git mv tasks/done/FORUM-02-GX10-READ-INTEGRITY.md tasks/backlog/` y `status: open`.
