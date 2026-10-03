# Desarrollo de instrumentos BB — 2026-10-03

Luis eligió desarrollar instrumentos antes de habilitar canarios de laboratorio. Coordinación integra y revisa; tres ejecutores Luna trabajaron en worktrees aislados. Las tandas se generaron desde las 98 fichas, con cinco por tanda y tres en la última. Se conserva el criterio original de cada cierre.

## Resultado concreto

- APT: lectura Deb822 e índices efectivos; conserva arquitectura y tuple OTA/kernel/driver, redacta credenciales y distingue URI inválida. No acredita firma, frescura o compatibilidad OEM por sí sola.
- USB/HID y watchdog: ancestro USB más cercano, serial opcional, velocidad e identidad disponibles; propietario watchdog desconocido, sin abrir el dispositivo.
- Red/RDMA: MTU, carrier, driver/PCI y GID/netdev/firmware cuando sysfs lo ofrece. La conexión física, NCCL y recuperación tras hotplug requieren controles propios.
- Prometheus: preserva nombre exacto, TYPE/HELP, etiquetas, valor y timestamp. No transforma porcentajes en bytes KV.
- SSE: conserva deltas de texto/tool_calls y argumentos parciales; detecta EOF incompleto, JSON inválido y terminación desconocida. No ejecuta herramientas ni infiere cancelación, MTP acceptance o progreso interno.
- OpenClaw: contrasta modelo servido/configurado y presupuesto explícito asociado a checkpoint; separa cap de configuración y tokens de petición. Bloquea solicitudes cuyo max_tokens excede el headroom; no recorta silenciosamente. Entradas caller-supplied siguen sin autenticar.
- Kernel/pstore/netconsole: identidad/configuración y huellas; conserva errores. Configurar un receptor o encontrar pstore vacío no demuestra recepción ni recuperación.
- Respaldo/boot: CLI de identidad exacta mountpoint/dispositivo/UUID; un directorio sin el montaje esperado bloquea. Inventaría DRM y existencia de initrd/vmlinuz actuales, sin declarar bootabilidad. El check no protege contra un desmontaje posterior ni ejecuta copia/restore.

Los cinco módulos Python nuevos son `apt_sources`, `runtime_provenance`, `chat_sse_capture`, `openclaw_contract` y `kernel_capture`; las otras capacidades reutilizan `host_diagnostics`. Los formatos, límites, comandos y controles están documentados en los informes por familia `BB-INSTRUMENTS-*.md` de este directorio.

## Las 98 fichas, sin cierres sintéticos

Comando literal:

```sh
python3 /home/lcasarin/.Codex/tools/triage.py merge --dir tasks/evidence/BB-INSTRUMENTS-2026-10-03/development-verdicts --expected tasks/evidence/BB-INSTRUMENTS-2026-10-03/development-source.json --require status,evidence,reason
```

Salida: `returned: 98 of 98`. IDs únicos 98; faltantes 0; desconocidos 0; duplicados 0. La completitud describe este reparto, no el estado de los sujetos.

| Dictamen de desarrollo | Fichas |
| --- | ---: |
| Desarrollo parcial nuevo | 19 |
| Instrumento existente reutilizado | 24 |
| Captura concreta pendiente | 16 |
| Ensayo de laboratorio diferido por el voto | 25 |
| Contrato/oracle específico pendiente | 8 |
| Observable/captura funcional aún bloqueada | 3 |
| Decisión operativa previamente pendiente | 2 |
| Integración/producción upstream pendiente | 1 |
| Total | 98 |

Cierres experimentales: **0**. Fichas originales abiertas: **98**. Ninguna se cerró por un fixture, existencia de informe o selectores inexistentes. `developed` significa una capacidad parcial nueva que sirve a esa ficha; una herramienta compartida no valida todos sus sujetos.

Las tres bloqueadas requieren MTP acceptance por posición, progreso interno de cola GLM53 y un canario de corrección JSON prolongado. Los dos votos operativos previos siguen pendientes: sincronizar dos archivos desplegados y reiniciar el guardian de proceso. El voto de desarrollo no autoriza esas intervenciones.

Coordinación corrigió el dictamen del threat sweep a `needs_upstream`, preservando `original_status`: su contrato y parche están definidos; falta el productor upstream. El kit fijado 8.9.6 sigue barriendo **0 archivos** de amenazas porque su lista omite `tools/`. Ese cero es un defecto del instrumento. No se editó el bundle generado ni el checkout upstream con trabajo ajeno.

Cada ID tiene capacidad disponible, evidencia y entrada exacta pendiente en `tasks/evidence/BB-INSTRUMENTS-2026-10-03/development-verdicts`. Los informes de factibilidad APT, runtime y devices explican los restantes por tanda. Se mantiene la diferencia entre desarrollar código y probar el comportamiento experimental.

## Validación literal en principal

`python3 .simplecode/run.py simplecode.verification.coverage_target -q`:

```text
1096 passed in 107.76s (0:01:47)
1096 deselected in 0.72s
[coverage] phase 2: no test carries the `mutates_real_source` marker here; the serial lane is empty, not failing. Phase 1's coverage stands on its own.
[coverage-ratchet] OK: Current coverage 100.00% meets watermark 100.00%.
```

Scope: 34 módulos Python trackeados en `tools/`; `4882/4882` sentencias cubiertas, faltantes `0`, líneas excluidas existentes `16`. `bin/bb-usable` extensionless conserva medición separada; esta cifra no representa todo Bash ni todo ejecutable del repo.

La primera corrida pasó 1094 pruebas y cubrió 4875/4882 sentencias (99,8566%). Se añadieron controles de URI inválida/redacción IPv6 y atributo netconsole por symlink exterior; la segunda corrida arriba cubre los siete caminos faltantes. No se cambió el umbral, scope o exclusiones para obtener el resultado.

| Instrumento | Salida |
| --- | --- |
| `python3 -m ruff check .` | `All checks passed!` |
| `python3 -m pyright` | `0 errors, 0 warnings, 0 informations` |
| `ledger_schema --root .` | checked 283, passed 283, failed 0, unverified 0, avisos 0, could_not_run 0 |
| `backlog_verifier --root . --gate` | frauds 0, could_not_run 0, contract_breaches 0, unverified 0; incluye 178 dictámenes cacheados, no 178 ejecuciones nuevas |
| `zero_debt --root . --mode zero --gate` | PASSED 89, CONVICTED 0, COULD_NOT_RUN 0, violations 0 |
| `adversarial_judge --root . --gate` | mock/source audit: HALLAZGOS 0; threat sweep: 0 archivos, defecto arriba |
| H1 audit gate | not-clean reasons 0; 12 claims actuales selladas |
| `finding_backlog --root . --gate` | exit 1, HALLAZGOS 98, could_not_run 0; bloquea publicación |

El juez adversarial capturó una prueba CLI que observaba sólo SystemExit; ahora verifica también el JSON real. El gate de deuda rechazó write_text sin encoding en los nuevos tests de respaldo; se corrigieron todas a UTF-8. No se agregaron exenciones, baselines, skip ni bypass.

H1: nueve IDs se movieron por filas nuevas del inventario. La extracción nativa demostró texto sin cambios en las 12 afirmaciones y hashes nativos iguales de todos sus archivos citados. `h1-movement-proof.json` conserva la prueba; se registraron nueve revisiones sin inventar una nueva medida del host.

Los hooks registraron skipped reales: sintaxis Bash en commits sin Bash; en commits documentales también Ruff, angry-path y zero-debt staged sin entradas. Los tests focales en worktrees tuvieron fallos de resolución de pytest en Pyright y restricciones IPC en una corrida inicial; están declarados en sus informes. La validación global principal arriba sí ejecutó Pyright y la suite completa. El reporte de observaciones físicas sigue parcial.

## Lecturas físicas y límites

`native-readonly-command.txt` conserva el comando literal posterior de red/boot/versiones GPU, ejecutado fuera de las restricciones IPC/dispositivos del sandbox con el mismo UID. El JSON está en `native-readonly-capture.json`.

Se observaron 17 entradas `ip` y 16 interfaces sysfs, sin interfaces sysfs faltantes en `ip`, y cero HCA RDMA. `nvidia-smi` devolvió rc 0: NVIDIA GB10, driver 580.178.04, CUDA anunciada 13.0. El error rc9 anterior era de la captura restringida y no acredita ausencia de GPU. Estas lecturas no ejecutaron workloads ni validan otro driver, generación, NCCL o contención.

La captura nativa conserva **5 nodos could_not_run**: modeset DRM denegado y los nodos anidados del inventario/Wi-Fi por carrier ilegible y versión de módulo ausente. Incluye padres e hijos; no son cinco consultas independientes. Se conserva la captura anterior y no se suman sus contadores.

Capturas separadas: APT CNR 0; pstore CNR 1; el lector Prometheus sin scrape nativo CNR 1; SSE sin stream nativo CNR 1; OpenClaw sin sus seis observaciones de entrada CNR 6. Estas son mediciones de sujetos/entradas distintos, no un contador agregado de fallos del host. Persisten también las 23 observaciones dmem.current faltantes y tres eventos históricos sin stdout/stderr originales; sus dictámenes no se sustituyen por datos nuevos.

No hubo escritura de host, reinicio, instalación, firmware, hotplug, panic, reboot, envío de mensajes, peticiones de generación ni ejecución de tools de modelos. Los nuevos instrumentos quedan listos para obtener datos con los que cerrar las fichas correctamente. Ship-freeze mantiene la publicación bloqueada por las 98 abiertas.
