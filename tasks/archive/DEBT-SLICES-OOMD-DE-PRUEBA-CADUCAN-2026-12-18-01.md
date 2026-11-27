---
id: DEBT-SLICES-OOMD-DE-PRUEBA-CADUCAN-2026-12-18-01
kind: task
domain: SYSTEM
title: "Las slices de prueba de oomd (bbtest-oomd, bbtest-oomd-neg) caducan el 2026-12-18: retirarlas o renovarlas con ficha"
status: done
severity: P2
origin: asserted
satd_family: PROCESS_DEBT
created: 2026-11-18
close_check: {"cmd": "! test -e adopted/systemd-user/bbtest-oomd.slice && ! test -e adopted/systemd-user/bbtest-oomd-neg.slice", "expect": "exit_zero", "porque": "Falla hoy (las dos estan versionadas). Voto de Luis 2026-11-18: versionarlas con caducidad de 30 dias en vez de retirarlas, porque ensayar ManagedOOMPreference en un slice aislado sigue siendo util mientras DEBT-OOMD-MATA-EL-SCOPE-DE-ORCA-CON-TODAS-LAS-SESIONES-01 siga abierta. Cierra al retirarlas (git rm de adopted/systemd-user/ y de ~/.config/systemd/user/, con MANIFEST en ~/archive/retirado/_maquina/)."}
closed: 2026-11-26
closure_type: fixed
---

## Por que existen

Fixtures del experimento de `DEBT-OOMD-PROBAR-Y-DIAGNOSTICAR-01` (2026-10-12): `bbtest-oomd.slice` (`MemoryHigh=150M`, `MemorySwapMax=0`, `ManagedOOMMemoryPressure=kill` al 10 %) y su gemela `bbtest-oomd-neg.slice` sin la propiedad, de control negativo. La medicion que ellas iban a dar la dio un evento real (2026-11-17). Se versionaron para que el auditor de canon del consumidor de conocimiento (`tools/auditar_canon.py`) deje de reportar `unit_sin_fuente=2` y se les puso fecha.

## Caducidad

2026-12-18, vigilada por `tests/test_caducidad_slices_oomd.py` (se pone roja ese dia) y escrita en las dos filas de propiedad de `SPEC.md`. Renovar exige otra ficha y mover la fecha del test y de las filas a la vez (un test lo comprueba).

## Contenido (copia exacta, sha256 en `bb drift`)

```
bbtest-oomd.slice       [Slice] MemoryHigh=150M MemorySwapMax=0 ManagedOOMMemoryPressure=kill ManagedOOMMemoryPressureLimit=10%
bbtest-oomd-neg.slice   [Slice] MemoryHigh=150M MemorySwapMax=0
```

## Cierre (2026-11-26)

Verificado `close_check` (`rc=0`): `! test -e adopted/systemd-user/bbtest-oomd.slice && ! test -e adopted/systemd-user/bbtest-oomd-neg.slice`
