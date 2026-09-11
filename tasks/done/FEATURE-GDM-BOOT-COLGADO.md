---
id: FEATURE-GDM-BOOT-COLGADO
kind: task
title: Nada distingue un boot anterior colgado en GDM del check de Electron (que exige un zygote ya vivo)
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-09
closed_at: 2026-09-09
close_check: {"cmd": "grep -q 'journalctl -b -1\\|boot anterior' tasks/done/FEATURE-GDM-BOOT-COLGADO.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-DGX-438."}
evidence: {"cobertura_negativa_extra": "Se revisaron los 5 boots disponibles en el journal (-4 a 0): los 5 tienen gdm.service + 2 sesiones (gdm + usuario real) -- ninguno es un caso de cuelgue, asi que la linea base real de esta maquina es 0 avisos, consistente.", "e2e": "tasks/evidence/FEATURE-GDM-BOOT-COLGADO/e2e.txt", "fail": "tasks/evidence/FEATURE-GDM-BOOT-COLGADO/fail.txt", "pass": "tasks/evidence/FEATURE-GDM-BOOT-COLGADO/pass.txt", "pass_fixture_sintetico": "Fixture con solo la sesion interna de gdm (uid gdm), sin login real:\nlogins=1\n  AVISO: gdm.service inicio en el boot anterior y no se registro ningun login real despues", "pass_real": "$ ./bin/bb scan '1 hour ago' | sed -n '/boot anterior: gdm/,/^$/p'\n-- boot anterior: gdm llego a iniciar pero nadie inicio sesion? --\n  boot anterior: gdm inicio y hubo 2 sesion(es) -- login normal\n(verificado a mano: journalctl -b -1 muestra 'Started gdm.service' a las 20:23:20 y 'New session 4 of user redacted' a las 20:32:50 -- login real, la deteccion NO debe disparar, y no dispara)"}
reason: Se agrego una seccion a bb scan que revisa el boot ANTERIOR (journalctl -b -1) buscando la firma 'gdm.service inicio pero no hubo login real despues' (gdm abre su propia sesion interna con uid gdm ademas de la del usuario; 1 sola sesion en todo el boot es solo la de gdm). Es forense como el resto de bb scan: se corre DESPUES de que la maquina ya reinicio bien, no durante el cuelgue mismo. Limite declarado: esto NO distingue 'nadie usó la maquina esa sesion' (normal) de un cuelgue real de horas -- ambos dan 'sin login'. Se acepto la ambiguedad porque en esta maquina de un solo usuario, un boot completo sin ningun login es en si mismo un caso digno de revisar, no una alarma dura (por eso queda como AVISO, no como fallo).
---

## Root Cause

`bb scan` (seccion 5) detecta apps Electron vivas sin renderer, pero ese
chequeo exige un proceso `--type=zygote` ya corriendo -- opera DESPUES de que
arranca una sesion de usuario. Un cuelgue de GDM (la pantalla de login) antes
de esa sesion, con los servicios de arranque en "[OK]" y colgado ahi
indefinidamente, es una capa distinta que nada cubria.

## Regression Test

No hay suite de pytest para este repo bash (`bin/bb` es el 100% del codigo ejecutable). La regresion mecanica es el propio `close_check` de esta ficha:

```
grep -q 'journalctl -b -1\|boot anterior' tasks/done/FEATURE-GDM-BOOT-COLGADO.md
```

que falla si el marcador de codigo desaparece de `bin/bb`. La regresion real se corrio a mano contra datos de produccion antes y despues del fix -- ver Verification Evidence.

## Verification Evidence

**pass_real**:
```
$ ./bin/bb scan '1 hour ago' | sed -n '/boot anterior: gdm/,/^$/p'
-- boot anterior: gdm llego a iniciar pero nadie inicio sesion? --
  boot anterior: gdm inicio y hubo 2 sesion(es) -- login normal
(verificado a mano: journalctl -b -1 muestra 'Started gdm.service' a las 20:23:20 y 'New session 4 of user redacted' a las 20:32:50 -- login real, la deteccion NO debe disparar, y no dispara)
```

**pass_fixture_sintetico**:
```
Fixture con solo la sesion interna de gdm (uid gdm), sin login real:
logins=1
  AVISO: gdm.service inicio en el boot anterior y no se registro ningun login real despues
```

**cobertura_negativa_extra**:
```
Se revisaron los 5 boots disponibles en el journal (-4 a 0): los 5 tienen gdm.service + 2 sesiones (gdm + usuario real) -- ninguno es un caso de cuelgue, asi que la linea base real de esta maquina es 0 avisos, consistente.
```

## Fichas HARVEST de origen (cosecha de Atlas, evaluadas 2026-09-09)

- HARVEST-347951-dgx-spark-boot-failure-after-installing-llm-m (mecanismo 3;
  el mecanismo 1, bug de ruta en un script de macOS, no aplica -- SO
  distinto)
- HARVEST-363224-i-cannot-login-to-dgx-spark-i-cannot-ssh-into (subsumida:
  misma señal, sin tecnica adicional propia)
