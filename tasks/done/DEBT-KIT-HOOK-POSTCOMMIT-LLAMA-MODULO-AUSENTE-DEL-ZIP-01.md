---
id: DEBT-KIT-HOOK-POSTCOMMIT-LLAMA-MODULO-AUSENTE-DEL-ZIP-01
kind: task
domain: VERDICT
title: "El hook post-commit llama a coverage_attestation, que el runtime.zip del kit 10.1.2 no trae"
status: done
closed_at: 2026-10-17
closure_type: relocated_prior_verification
reason: "el kit 10.2.4 (commit 7eb17af5, aplicado por sync-satellites) trae pyright_attestation en runtime.zip; el hook post-commit ya no da ImportError. Este commit solo mueve la ficha"
evidence: {"pass": "tasks/evidence/DEBT-KIT-HOOK-POSTCOMMIT-LLAMA-MODULO-AUSENTE-DEL-ZIP-01.pass.txt", "fail": "tasks/evidence/DEBT-KIT-HOOK-POSTCOMMIT-LLAMA-MODULO-AUSENTE-DEL-ZIP-01.fail.txt", "e2e": "tasks/evidence/DEBT-KIT-HOOK-POSTCOMMIT-LLAMA-MODULO-AUSENTE-DEL-ZIP-01.e2e.txt"}
severity: P3
origin: detected
detector: {"rule": "python .simplecode/run.py simplecode.verification.pyright_attestation --help sale 1 con ImportError (el modulo no esta en runtime.zip)", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-15
close_check: {"cmd": "python .simplecode/run.py simplecode.verification.coverage_attestation --help", "expect": "exit_zero", "porque": "Hoy sale 1 con ImportError: No module named simplecode.verification.coverage_attestation. Cierra cuando el kit empaquete el modulo (o el hook deje de invocarlo) y el comando salga 0."}
---

## Medido (2026-10-15)
Cada `git commit` de este repo imprime `ImportError: No module named simplecode.verification.coverage_attestation` tras estampar el recibo. `.git/hooks/post-commit:34` y `post-merge:34` ejecutan `$RUNNER simplecode.verification.coverage_attestation --root . --background`, y `.simplecode/runtime.zip` (kit 10.1.2, `kit.lock`) no contiene ese modulo (`unzip -l .simplecode/runtime.zip | grep -ci coverage_attest` = 0). En el repo fuente `~/projects/simplecode` el modulo existe desde el commit `062387f5` (2026-10-15 19:45), es decir, posterior al empaquetado del kit.

## Consecuencia
El hook termina con `exit 0`, asi que no bloquea nada, pero la atestacion de cobertura en segundo plano no corre despues de ningun commit ni merge: un instrumento caido sin aviso mas alla de la traza.

## Bloqueador
Otro repo: el empaquetado del kit (simplecode). Aqui solo se puede re-sincronizar el kit cuando una version nueva traiga el modulo; editar el hook instalado o el zip a mano rompe el sello de `kit.lock`.

## Medido (2026-10-16, actualizacion)
El sync del kit (8441a71e) ya trae `coverage_attestation`: `python .simplecode/run.py simplecode.verification.coverage_attestation --help` sale 0. El mismo hook (`.git/hooks/post-commit:35` y `post-merge:35`) llama ahora a `simplecode.verification.pyright_attestation`, que el runtime.zip tampoco trae: `ImportError: No module named simplecode.verification.pyright_attestation` en cada commit. El defecto es el mismo (modulo que el hook invoca y el zip no empaqueta) con otro modulo, asi que el close_check pasa a ese modulo en vez de cerrar la ficha sobre el primero. Sigue siendo del kit (simplecode): aqui solo se re-sincroniza cuando una version nueva lo traiga.

## Root Cause
El runtime.zip del kit 10.1.x no incluia `simplecode.verification.pyright_attestation`, que el hook post-commit generado llama en su linea 35.

## Regression Test
El close_check de la ficha (`coverage_attestation --help`) y la comprobacion `pyright_attestation --help` de la evidencia; el arreglo es del kit upstream, no de este repo.

## Verification Evidence
Triada en tasks/evidence/: fail (0 coincidencias en el zip, ImportError en cada commit), pass (kit 10.2.4, modulo presente, `--help` rc 0) y e2e (commit real sin ImportError).
