---
id: FORUM-02-GX10-READ-INTEGRITY
kind: task
domain: STORAGE
title: "Detectar lecturas corruptas en caché antes de confiar en pesos de modelos"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FORUM-02-GX10-READ-INTEGRITY --evidence tasks/evidence/FORUM-02-GX10-READ-INTEGRITY", "expect": "exit_zero", "porque": "Verificador específico pendiente: debe demostrar detección de datos alterados con una referencia externa y diferenciar lecturas buffered, O_DIRECT, caché, salud NVMe y evidencia de firmware."}
---

## Fuente y evidencia

Hilo NVIDIA [382456](https://forums.developer.nvidia.com/t/asus-ascent-gx10-changing-file-checksums-cached-reads-differ-from-o-direct/382456), post [1](https://forums.developer.nvidia.com/t/asus-ascent-gx10-changing-file-checksums-cached-reads-differ-from-o-direct/382456/1).

En un ASUS Ascent GX10 con DGX OS 7.5.0, kernel `6.17.0-1032-nvidia` y driver `580.173.02`, un usuario comparó dos nodos mientras los contenedores NIM estaban detenidos. En el worker, lecturas buffered repetidas de shards safetensors devolvieron hashes y bytes distintos; cinco lecturas `O_DIRECT` alineadas coincidieron con la referencia del nodo head. `POSIX_FADV_DONTNEED` hizo que una región volviera a leerse correctamente, pero auditorías posteriores encontraron diferencias en otros shards. No se reportaron Xid, errores explícitos de NVMe, ni informes de memoria incorregible; el autor no concluye que el SSD sea la causa. El worker había requerido antes un power-cycle, relación que tampoco se probó.

Blackbox no compara integridad de datos leídos, ni informa una ruta de salud RAS/EDAC/BERT/NVMe que permita distinguir corrupción de caché/memoria, problema de software o medio persistente. La única observación positiva publicada apunta a lecturas buffered frente a `O_DIRECT`; la fuente no establece causa física ni generalidad fuera de ese ASUS GX10.

## Trabajo

Preparar una comprobación de solo lectura para archivos de prueba o una copia en staging: calcular hashes repetidos con I/O buffered y alineado `O_DIRECT`, comparar contra un manifiesto de confianza generado en otro nodo/medio, y correlacionar con `POSIX_FADV_DONTNEED`, logs del kernel, versión de firmware, `smartctl`/NVMe health y cualquier fuente RAS disponible en el OEM. Registrar lecturas discrepantes, bytes/rangos, versión completa de la pila y errores de colección. No tratar una lectura directa correcta como prueba única de que el resto del hardware está sano.

Si se reproduce en datos inmutables con referencia externa, detener la carga que dependa de esos datos y preparar diagnóstico oficial de ASUS/NVIDIA (incluido Field Diagnostics cuando el fabricante lo indique) y escalación/RMA si persiste. No borrar cachés de producción ni ejecutar escrituras de estrés desde Blackbox. Una corrección de kernel/driver solo se recomienda tras una A/B en equipo recuperable y evidencia de que corrige el resultado.

## Riesgos y cierre

Auditar modelos completos puede usar bastante I/O, memoria y tiempo, y el hash de archivos propietarios puede revelar metadatos operativos. Limitar pruebas iniciales a muestras pequeñas, staging, periodos ociosos y manifiestos fuera del nodo sospechoso. Mantener intactos los archivos originales; no reescribir, eliminar ni descargar de nuevo pesos antes de preservar la evidencia.

Cerrar con control sano (referencia externa idéntica en buffered y `O_DIRECT`), control negativo que altere bytes y sea detectado, salida literal para una región discrepante, límites/coste medidos de la inspección, y una ruta que declare `COULD_NOT_RUN` por acceso insuficiente. Si el OEM no expone señales RAS/EDAC/BERT/NVMe legibles o la prueba no reproduce el caso, conservar esa limitación; no cerrar atribuyendo la causa al disco, RAM o driver sin evidencia independiente.
