# Instrumento kernel, pstore y netconsole — 2026-10-03

## Alcance y procedencia

`tools/kernel_capture.py` toma lecturas locales readonly de kernel release, boot ID, `panic`, `panic_on_rcu_stall`, parámetro de arranque `netconsole=`, estado del módulo, parámetro estático y atributos de objetivos configfs. Reutiliza `tools.recovery_profile.read` para registrar huellas SHA-256 y señales pstore acotadas, y `tools.host_diagnostics.module_state` para diferenciar módulo ausente, cargado, integrado al kernel o inaccesible. Las rutas de pstore y objetivos se confinan al root de captura, incluidos symlinks.

La fuente cubre el árbol local de captura y no afirma que observe configuraciones externas al root. Los valores de dirección/MAC/cmdline no se guardan; las configuraciones netconsole se representan con hashes. `could_not_run` cuenta checks que declaran ese estado, incluidas filas agregadas con fallos anidados, y puede contar un padre y su hoja. El estado `unavailable` corresponde a ruta ausente y no se convierte en `could_not_run`. Un objetivo con cero atributos legibles se marca `unknown`. La lectura pstore no limita el tamaño de archivo, y la verificación de symlink seguida de lectura no es atómica ante reemplazo concurrente; ambas limitaciones quedan declaradas.

Formatos nativos consultados: [documentación de netconsole del kernel](https://docs.kernel.org/networking/netconsole.html) describe parámetro estático y configuración dinámica configfs; [debugging de shutdown/pstore](https://docs.kernel.org/power/shutdown-debugging.html) describe la disponibilidad de pstore tras reinicio y su interacción con archivado de systemd-pstore. La captura conserva estado/configuración; no demuestra recepción de paquetes, persistencia tras reboot ni recuperación. No se ejecutó panic, reboot, carga de módulo, instalación de paquetes, cambios de host ni servicios.

## Captura local

Archivo raw: `tasks/evidence/BB-INSTRUMENTS-2026-10-03/kernel-capture.json`.

Comando literal: `python3 -m tools.kernel_capture > tasks/evidence/BB-INSTRUMENTS-2026-10-03/kernel-capture.json`

Salida resumida literal del lector: `{"boot_parameter": {"present": false, "status": "read"}, "could_not_run": 1, "exit": 2, "module": {"built_in": false, "loaded": false, "status": "absent"}, "pstore_error": "PermissionError: [Errno 13] Permission denied: '/sys/fs/pstore'", "pstore_status": "could_not_run", "status": "partial"}`. Exit literal del comando: `2`. El resumen conserva el único check inaccesible; `netconsole` ausente y ausencia del parámetro son observaciones, no pruebas de que el mecanismo funcione.

## Controles focales

- `python3 -m coverage run --branch --source=tools.kernel_capture -m pytest -q tests/test_kernel_capture.py` → `15 passed in 0.08s`.
- `python3 -m coverage report -m --include='tools/kernel_capture.py'` → `96` sentencias, `0` faltantes, `26` ramas, `0` parciales, `100%` cobertura.
- `python3 -m ruff check tools/kernel_capture.py tests/test_kernel_capture.py` → `All checks passed!`.
- `python3 -m pyright tools/kernel_capture.py tests/test_kernel_capture.py` → `0 errors, 0 warnings, 0 informations`.

Los controles incluyen estado presente/ausente/denegado, parámetro de arranque, hashes sin endpoint, objetivo sin atributos legibles, lectura/listado denegados, symlinks de directorio y archivo que escapan del root, texto pstore no serializado y salida CLI. La cobertura cubre el módulo nuevo; no certifica entrega al receptor, firma de módulo, Secure Boot, compatibilidad OEM ni recuperación tras panic o freeze.

## Control tardío de confinamiento de atributo — 2026-10-03

Se añadió un control donde `remote_ip` en un target configfs apunta por symlink a un archivo fuera del root de captura. El resultado marca `could_not_run`, no abre el archivo externo y no serializa su contenido. Es un control de la rama de confinamiento; conserva la limitación documentada de que resolve+read no es atómico ante reemplazo concurrente.

La ejecución focal conjunta, cobertura, Ruff, Pyright sobre producción y zero-debt gate quedan registrados en [el addendum APT/URI](BB-INSTRUMENTS-apt.md#controles-tardíos-de-rutas-de-uri--2026-10-03), porque esa misma corrida mide ambos módulos.
