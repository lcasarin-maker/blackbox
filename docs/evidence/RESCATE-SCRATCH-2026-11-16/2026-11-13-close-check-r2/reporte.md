# Candidato fijo para ultima revision 2 — close-check

HEAD: `6194cf8fb0bd1ac657935c98c5779e952079fa93`.
Base de esta correccion: `35fdb0e5`. Remoto local observado: dd5b7098.
Arbol limpio. Ningun push, revert, reset, restauracion de HEAD ni historia reescrita.
El commit nuevo repara hacia adelante el contrato local, conservando los anteriores.

## Respuesta a F1–F5

F1: el parche candidato crea dos archivos de prueba distintos. El selector de
la ficha canonica sigue apuntando a test_close_check_lint_block.py, cuyas tres
aceptaciones quedan rojas sobre el producto actual (no errores de coleccion):
report-only devuelve 0 frente al bloqueo futuro pendiente, shellcheck se lee
como no_ejecuta y echo como ejecuta. La tasa adjudicada y voto siguen pendientes;
ninguna prueba de medicion se presenta como aceptacion de cierre. No se cierra
la ficha por un verde parcial ni se debilita su criterio original.

F2: conserva Boleta 6, 2A y la instruccion vigente del director. No hay --enforce
en la fila activa ni cambios productivos en la politica de la dependencia.
La propuesta anterior se renombro a propuestas-no-vigentes/close-check-enforce.patch,
con MANIFEST: SHA256, modo, caducidad 2026-11-27 y vigilancia por coordinacion/
owner simplecode. Hash y modo contrastados; no se borro el archivo.
Medicion controlada de seis casos: dos falsas alarmas para un bloqueo hipotetico
(shellcheck y Python por stdin, con ejecucion y control fallido reales), una
omision (echo pytest), dos correctos y uno sin adjudicar (consulta de servicio
no ejecutada por alcance). measurement-r2.json conserva argv y salidas, con
rutas personales del diagnostico enmascaradas; originales locales fuera del repo.
No se extrapola una tasa para la flota; director formulara boleta si procede.

F3: simple.json pasa de args=[--enforce] a args=[] en un commit nuevo, sin
comandos de reversion. Corredor instalado, fila policy nativa, rango Git real:
rc=0, pass=1, fail=0, could_not_run=0, pending=0; imprime
`fichas_cerradas=1 ejecuta=0 no_ejecuta=1`. Es disponibilidad del reporte,
no prueba de ejecucion ni cierre limpio. Control de rango inexistente:
rc=2, could_not_run=1, pass=0, fail=0, pending=0. Nunca se reetiqueta CNR como PASS.

F4: alineacion-r2.json contrasta fila close-check de contrato local, perfil
blackbox canonico y salida real de generate.text_of('blackbox'): iguales,
args=[], env/git_context/CNR/base/read_only/hooks iguales. Control con --enforce
introducido solo en memoria produce igualdad=False. No se regenera el resto del
contrato ni se toca la guarda de privacidad local. Futuro enforce requiere voto,
integracion canonica y corredor compatible; ningun parche runtime ad hoc.

F5: las cuatro pruebas de medicion ejercen rango explicito y variables del hook,
fichas fuera del rango, Git retirado de un repo que antes da 0 y restaurado da 0,
ref inexistente y producto fixture realmente ejecutado. La prueba borra su efecto
antes del reporte y comprueba que el reporte no lo recrea. Detector neutralizado
rompe la prueba de deteccion (1 failed); conservar Git donde debia retirarse rompe
la prueba CNR (1 failed). No hay falso verde por usar un directorio sin Git.
El modo vigente no tiene una barrera de bloqueo activa: el negativo comprueba
el detector y la aceptacion roja conserva ese hueco, sin fingir que ya bloquea.

## Candidato y propiedad

Parche propuesto: tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/close-check-measurement-r2.patch.
Solo propone:
- tests/policy/test_close_check_report_measurement.py
- tests/policy/test_close_check_lint_block.py
- anotacion/owner de la ficha canonica IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS.

No se escribio en simplecode. El owner debe coordinar e integrar esos archivos
tras revision; su politica productiva, perfil, generador y binario no se alteraron.
source-r2.json fija sus huellas; la politica leida sigue con el mismo SHA256.
La propuesta vieja queda como evidencia no vigente. Los commits dd8ec17c y
35fdb0e5 y el trabajo previo permanecen en la historia.

## Comandos, salidas y negativos

Preparacion de casos: `PYTHONDONTWRITEBYTECODE=1 python3 "$HOME/scratch/blackbox/2026-11-13-close-check-r2/medir_clasificador.py"`.
Resumen literal:
`{"controlled_cases": 6, "false_alarms": 2, "missed_no_product": 1, "unadjudicated": 1, "could_not_run": 1, "scope": "controlled sample, not a fleet rate; no blocking threshold voted"}`.
Comandos/argv, rc, stdout/stderr y negativos completos en measurement-r2.json.

Pruebas de medicion aisladas:
`POLICY_SOURCE="$HOME/projects/simplecode/policy" PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider "$HOME/scratch/blackbox/2026-11-13-close-check-r2/test_close_check_report_measurement.py"`.
Salida: `4 passed in 0.40s`.
Negativos reales: `PYTHONDONTWRITEBYTECODE=1 python3 "$HOME/scratch/blackbox/2026-11-13-close-check-r2/negativos.py"`:
`detector_neutralizado_rc=1 1 failed in 0.13s`;
`git_presente_control_rc=1 1 failed in 0.18s`.

Paquete aplicado solo en copia scratch, sin POLICY_SOURCE/PYTHONPATH de override:
`python3 -m pytest -q -p no:cacheprovider tests/policy/test_close_check_lint.py tests/policy/test_close_check_report_measurement.py`
→ `64 passed in 0.68s`, rc=0.
Close_check real de la ficha, en esa misma copia:
`python3 -m pytest -q -p no:cacheprovider tests/policy/test_close_check_lint_block.py`
→ `3 failed in 0.10s`, rc=1. Es aceptacion roja de producto, separada del verde de medicion.
Logs: canonical-measurement.txt y canonical-acceptance.txt en este directorio.

Compatibilidad y CNR por el corredor instalado:
`PYTHONDONTWRITEBYTECODE=1 python3 "$HOME/scratch/blackbox/2026-11-13-close-check-r2/runner_report.py"`;
invoca `simplecode verify --hook pre-push --no-observe --fresh` en una copia de
una fila con args=[] y un rango real. Casos y salidas en runner-r2.json:
normal `{could_not_run:0, fail:0, pass:1, pending:0}`, rc=0;
rango invalido `{could_not_run:1, fail:0, pass:0, pending:0}`, rc=2.
No es el corredor completo del candidato; coordinacion lo despachara despues.

`git -C "$HOME/projects/simplecode" apply --check "$HOME/projects/blackbox/tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/close-check-measurement-r2.patch"`: rc=0.
`ruff check` sobre los dos archivos de prueba propuestos: `All checks passed!`.
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_sin_datos_privados.py tests/test_guarda_snapshot.py`:
`8 passed in 3.38s`.

## Deudas, CNR y alcance conservados

Tres fichas de privacidad: open, sin cambios desde 35fdb0e5; tampoco cambia su
archivo de aceptacion. `git diff --quiet 35fdb0e5 HEAD -- <tres fichas y tasks/checks/test_revision_privacidad.py>` dio rc=0.
Se mantienen sus cuatro aceptaciones rojas ya documentadas; no se implemento ninguna.
La deuda de falso verde sigue abierta. El reporte no prueba ejecucion.

CNR de muestra: 1 (consulta systemctl no ejecutada, queda sin adjudicar).
Corredor normal aislado: CNR=0; control deliberado de rango invalido: CNR=1.
Git ausente en repo valido: rc=2 esperado; restaurado: rc=0.
No se corrio suite completa ni corredor completo del candidato; faltan ultima
revision 2 Opus y corredor que despachara coordinacion. No autoaprobacion.
Sin servicios, Dell, GPU, despliegues ni lista privada. No publicacion.

`git rev-parse HEAD origin/master`:

```text
6194cf8fb0bd1ac657935c98c5779e952079fa93
dd5b7098b3714219a3a5fc6a2c17964c0baa4d7f
```
