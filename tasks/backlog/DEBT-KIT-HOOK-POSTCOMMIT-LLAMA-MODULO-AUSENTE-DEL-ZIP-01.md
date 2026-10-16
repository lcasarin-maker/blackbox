---
id: DEBT-KIT-HOOK-POSTCOMMIT-LLAMA-MODULO-AUSENTE-DEL-ZIP-01
kind: task
domain: VERDICT
title: "El hook post-commit llama a coverage_attestation, que el runtime.zip del kit 10.1.2 no trae"
status: open
severity: P3
origin: detected
detector: {"rule": "python .simplecode/run.py simplecode.verification.coverage_attestation --help sale 1 con ImportError (el modulo no esta en runtime.zip)", "confidence": 1.0}
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
