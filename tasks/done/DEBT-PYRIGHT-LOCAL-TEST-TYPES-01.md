---
id: DEBT-PYRIGHT-LOCAL-TEST-TYPES-01
kind: task
domain: VERDICT
title: "Alinear tipos locales de fixtures CUDA, cgroup y captura"
status: done
severity: P2
origin: detected
detector: {rule: "pyright: reportIndexIssue, reportArgumentType y reportAttributeAccessIssue en pruebas locales", confidence: 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-03
closed_at: 2026-10-03
closure_type: fixed
close_check: {"cmd": "python3 -c 'import subprocess; subprocess.run([\"pyright\", \"tests/test_cgroup_repro.py\", \"tests/test_debt_registration_controls.py\", \"tests/test_memory_capture_and_cuda_integrity.py\", \"tests/test_cuda_integrity_cli.py\", \"tools/cuda_integrity.py\"], check=True); subprocess.run([\"python3\", \"-m\", \"pytest\", \"-q\", \"tests/test_memory_capture_and_cuda_integrity.py::test_profile_value_rejects_non_object_section\"], check=True)'", "expect": "exit_zero", "porque": "El guard rechaza un objeto JSON con una sección que no sea mapa; Pyright debe aceptar los tipos de los fakes, callbacks, perfiles y la interfaz CUDA en los cinco archivos focales. El control negativo del HEAD original reproduce 27 errores; el cierre no cubre scan_samples ni los cuatro hallazgos rawforum pendientes."}
evidence: {"pass": "tasks/evidence/DEBT-PYRIGHT-LOCAL-TEST-TYPES-01/pass.txt", "fail": "tasks/evidence/DEBT-PYRIGHT-LOCAL-TEST-TYPES-01/fail.txt", "e2e": "tasks/evidence/DEBT-PYRIGHT-LOCAL-TEST-TYPES-01/e2e.txt"}
reason: "La anotación de memory_profile.capture exponía cada subsección como object y los fakes modelaban callbacks/módulos dinámicos sin tipos compatibles; además run_worker aceptaba CDLL aunque su contrato observable es un conjunto de cinco funciones CUDA y ctypes no publica esos símbolos dinámicos en el stub. Se añadió un guard pequeño de mapas JSON, un Protocol de interfaz CUDA y estrechamientos para las asignaciones dinámicas/valores opcionales, sin alterar comportamiento."
---

## Registro y responsable

Deuda detectora Pyright del gate de tipos. Responsable: coordinación de Blackbox.

## Root Cause

`memory_profile.capture` publica `dict[str, object]`, por lo que Pyright no permite indexar secciones anidadas sin probar que cada valor es un objeto mapa. Los tests pasaban fakes estructuralmente válidos a `run_worker`, cuya firma `CDLL` describía el cargador ctypes en vez de los cinco símbolos que consume; el stub de `CDLL` tampoco enumera símbolos dinámicos. Los callbacks y atributos dinámicos de ModuleType conservaron nombres/valores con tipos imprecisos.

## Regression Test

El close_check valida que `profile_value` rechace una sección que sea lista en vez de objeto y corre Pyright sobre los cinco archivos focales. El control negativo usa el HEAD original `274f6351c60592bca7969e84f6d461e4e9282f1e`, donde Pyright reproduce 27 errores. Las pruebas de cgroup/CUDA, controles de registro y perfiles ejercitan el comportamiento con fixtures; no cargan una GPU real.

## Verification Evidence

`pass.txt` registra Pyright focal con 0 errores, Ruff y el selector negativo del guard con 1 pasada. `e2e.txt` registra el subconjunto completo con 136 pruebas aprobadas, la prueba final de perfiles con 31 aprobadas y el primer intento bloqueado por el kit ignorado y permisos de socket antes de su reejecución correcta. `fail.txt` conserva la salida literal de 27 errores del control original. El error independiente de `scan_samples.py` y cuatro hallazgos rawforum quedan fuera del alcance de esta ficha.
