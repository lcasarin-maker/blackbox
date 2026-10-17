---
id: DEBT-PORTERO-NO-CLASIFICA-TANDAS-DE-LIBREOFFICE-DE-OTROS-PROYECTOS-01
kind: task
domain: MEMORY
title: "El portero no clasifica las tandas de LibreOffice de otros proyectos"
status: open
severity: P2
origin: detected
detector: {"rule": "tests/test_portero_clase_trabajo_ajeno.py::test_una_conversion_de_libreoffice_headless_tiene_clase", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-17
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider --runxfail tests/test_portero_clase_trabajo_ajeno.py::test_una_conversion_de_libreoffice_headless_tiene_clase", "expect": "exit_zero", "porque": "Medido 2026-10-17: el portero clasifica por forma (pytest y hooks pre-push/pre-commit de cualquier proyecto -> suite), pero una tanda de 13 procesos soffice --headless de otro proyecto no tiene clase y entra sin cola ni tope; con la memoria libre en 15 % earlyoom mato workers de pytest de un push (journal 23:36:28). Cierra cuando clasifica() le da clase a una conversion de LibreOffice headless y la cola la admite de una en una, entrando primero en observar."}
---

## Medido
- 2026-10-17, tras 3 pushes fallidos: `ps` mostro 13 procesos `soffice.bin --headless` (perfiles `soffice_perfil_preparacion_*`, tanda del proyecto otro proyecto) mas las suites `pre-push` de Atlas y Twiner. Carga 27-31 y `MemAvailable` 15 %.
- `journalctl -u earlyoom` 23:36:28: SIGTERM a un `python` de 1522 MiB (worker de xdist del push de este repo). Dos pushes cayeron por `worker crashed`, sin que ningun test fallara (pasan solos).
- `tools/portero.py::clasifica` clasifica por la forma del comando: pytest y hooks pre-push/pre-commit -> `suite`, de cualquier proyecto. `soffice` devuelve `None`: sin clase, sin cola y sin tope.

## Voto de Luis 2026-10-17
Abrir esta ficha. Entra primero en `observar` (registra lo que haria, como el resto del portero), no en `actuar`. Descartado: dejar que cada proyecto se autorregule (cada push sigue expuesto a que earlyoom mate sus workers).

## Que falta
Una clase para conversiones de LibreOffice headless (por forma, no por nombre de proyecto), con su tope y turnos, la prueba de `clasifica` de arriba y, antes de pasar a `actuar`, medir una tanda real. Riesgo a vigilar: congelar un trabajo ajeno puede alargarlo; el portero ya excluye lo que sostiene `index.lock`.
