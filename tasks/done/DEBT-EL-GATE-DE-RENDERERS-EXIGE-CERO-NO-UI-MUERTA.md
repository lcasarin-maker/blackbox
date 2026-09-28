---
id: DEBT-EL-GATE-DE-RENDERERS-EXIGE-CERO-NO-UI-MUERTA
kind: debt
title: "'apps Electron sin renderer' exige cero renderers, y una UI muerta con un hermano vivo pasa limpia"
status: done
closure_type: relocated_prior_verification
closed_at: 2026-09-28
severity: P2
origin: asserted
satd_family: MISSING_INSTRUMENT
created: 2026-09-28
close_check: {"cmd": "python3 -m pytest tests/test_bb_bash.py -k electron_ui_muerta -q", "expect": "exit_zero", "porque": "el cierre exige un test con el caso que HOY pasa limpio -- un main con >=1 renderer vivo y la ventana sin pintar-- y su control negativo, no solo el caso de cero renderers que ya se cubre."}
evidence: {"pass": "tasks/evidence/DEBT-EL-GATE-DE-RENDERERS-EXIGE-CERO-NO-UI-MUERTA/pass.txt", "fail": "tasks/evidence/DEBT-EL-GATE-DE-RENDERERS-EXIGE-CERO-NO-UI-MUERTA/fail.txt", "e2e": "tasks/evidence/DEBT-EL-GATE-DE-RENDERERS-EXIGE-CERO-NO-UI-MUERTA/e2e.txt"}
reason: "CERRADO 2026-09-28 (commit 3a91866). Dos tests con procesos reales en tests/test_bb_bash.py -- el bloque de bin/bb:1099-1116 (dentro de cmd_scan) se copia literal a un script bash temporal para aislarlo de bb scan completo, sin tocar bin/bb. con_hermano_vivo_pasa_limpio documenta el LIMITE conocido (cuenta por zygote, no por ventana) como limite, no como arreglado -- el mecanismo NO cambio, solo quedo instrumentado y declarado. CERO_renderers_SI_dispara_SOSPECHOSO es el control negativo que nunca se habia corrido en la vida del repo, nombrado con el substring que filtra el close_check a proposito (un nombre sin 'electron_ui_muerta' habria dejado ese control negativo sin correr nunca, en verde por omision -- exactamente el modo de fallo que esta ficha senala). python3 -m pytest tests/test_bb_bash.py -k electron_ui_muerta -q: 2 passed, 75 deselected. Suite completa: 77 passed en 128.70s. No cierra el limite estructural (contar por ventana, no por proceso) -- eso sigue siendo trabajo futuro sin coste medido, declarado explicitamente en el docstring del primer test."
---

# Technical Debt: el gate de renderers exige cero, no UI muerta

## Root Cause

El 2026-09-28 11:28:28 el OOM killer mato el renderer de la ventana de
`claude-desktop` (PID 137261, SIGTRAP). La interfaz murio 59 minutos. La ventana
siguio mapeada (`Map State: IsViewable`, 1284x1090) y sobrevivio un renderer
hermano vacio de 49 MB.

`bb scan` sobre esa ventana de tiempo:

```
-- apps Electron sin renderer (proceso vivo, UI muerta) --
  apps sin renderer:           0
```

La causa esta en `bin/bb:1115`: `if [ "$nrend" -eq 0 ]`. Cero estricto. El
comentario de arriba lo dice: *"La firma exacta del cuelgue del 2026-09-07:
proceso principal vivo, ventana mapeada, cero procesos --type=renderer"*. El
gate codifica una firma literal, y la variante del 28 tiene 1, no 0.

## Lo que este mismo escaneo SI hizo bien

El instrumento no fallo entero. La fila de volcados capturo el evento:

```
-- core dumps --
  volcados capturados:         1
         1 x /usr/lib/claude-desktop/claude-desktop
```

El hueco que dio origen al repo -- `ulimit -c` en 0 y sin `systemd-coredump` el
2026-09-07 -- esta cerrado y se demostro en un incidente real. Lo que fallo es
la fila que se titula "proceso vivo, UI muerta".

## Como se cierra

Que el gate deje de preguntar "cuantos renderers hay" y pregunte "hay un
renderer que pinte esta ventana". Dos magnitudes disponibles y ya medidas en
este incidente:

1. **RSS del renderer.** El muerto llevaba ~164 MB anon; el hermano
   superviviente, 49 MB. Tras el relanzamiento sano: 2 renderers, uno de
   **786 MB**. Un renderer de ventana cargada y uno vacio se separan por un
   orden de magnitud.
2. **Correlacion ventana <-> proceso.** `xwininfo` ya da la ventana mapeada, y
   el repo ya sabe leer el servidor X (`x.{estado,ms}` en `bin/bb:761`).

## Limite declarado

El corte de RSS NO esta derivado. Hay tres numeros de UN incidente (49, 164,
786 MB) y eso no es una calibracion: un renderer legitimamente vacio --una
ventana recien abierta, un dialogo-- vive en la misma zona que uno muerto. El
segundo criterio (correlacion con la ventana) no tiene coste medido.

**Y lo que hace falta antes que nada: este gate nunca ha emitido "SOSPECHOSO".**
No se corrio su caso positivo. Un gate con cero capturas tras muchas corridas es
un defecto del instrumento, no evidencia de que el sujeto este limpio. Montar el
caso es barato -- lanzar un Electron y matarle todos los renderers-- y no se
hizo aqui, asi que hoy no hay prueba de que la rama `-eq 0` funcione tampoco.

## Verification Evidence

```
$ python3 -m pytest tests/test_bb_bash.py -k electron_ui_muerta -v
tests/test_bb_bash.py::test_electron_ui_muerta_con_hermano_vivo_pasa_limpio PASSED
tests/test_bb_bash.py::test_electron_ui_muerta_CERO_renderers_SI_dispara_SOSPECHOSO PASSED
2 passed, 80 deselected
```

Procesos reales (bash con `exec -a` marcado `type=zygote`/`type=renderer`),
no mocks de shell -- el bloque bajo prueba es el literal de `bin/bb:1099-1116`
copiado dentro de un script temporal que el test genera. Ver
`tasks/evidence/.../e2e.txt` para la corrida completa y una nota de
fiabilidad: el timeout de limpieza (5.0s) flaqueo una vez bajo carga real de
esta sesion, subido a 15.0s, 3 corridas limpias despues.

## Regression Test

El propio `close_check` (`pytest -k electron_ui_muerta`) es el guardián de
la regresión, con dos direcciones reales: `test_electron_ui_muerta_con_
hermano_vivo_pasa_limpio` documenta el límite conocido (cuenta por zygote,
no por ventana) sin arreglarlo, y `test_electron_ui_muerta_CERO_renderers_
SI_dispara_SOSPECHOSO` es el control negativo que nunca se había corrido en
la vida del repo -- si alguien rompe la rama `-eq 0` de `bin/bb:1115`, este
test lo atrapa. El nombre de ambos tests lleva el substring
`electron_ui_muerta` a propósito: un nombre sin él habría dejado el control
negativo sin correr nunca, en verde por omisión, que es exactamente el modo
de fallo que esta ficha señala.
