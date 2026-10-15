---
id: DEBT-PORTERO-ADOPCION-CHOCA-CON-PIDS-QUE-SALEN-01
kind: task
domain: MEMORY
title: "Adopciones del portero que chocan con procesos que salen, y seguimiento bajo carga real de 14 dias"
status: open
severity: P3
origin: detected
detector: {"rule": "journalctl --user: bb-portero-suite-*.scope Failed with result 'resources' mientras portero.jsonl registra rc=0", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-14
close_check: {"cmd": "grep -q adopcion_sin_carrera tasks/evidence/DEBT-PORTERO-ADOPCION-CHOCA-CON-PIDS-QUE-SALEN-01/medicion.txt", "expect": "exit_zero", "porque": "Resto declarado al cerrar DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01. Cierra con una medicion que muestre (1) que el portero no da rc=0 cuando systemd deja el scope en failed, con su prueba y control negativo, y (2) 14 dias desde 2026-10-14 sin reinicio por COLAPSO de bb-usable con el portero adoptando suites; escrita con la frase adopcion_sin_carrera. Si hay un COLAPSO en esos 14 dias, la salida es diagnosticarlo, no cerrar."}
---

## Medido (2026-10-14, `tasks/evidence/DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01/medicion.txt`)
- 15 adopciones con efecto (`congelar`/`admitir` con cgroup) en `portero.jsonl` ese dia: 11 con rc=0 y 4 con rc=1 ("Failed to set unit properties: No such process" o `ProcessLookupError`): la suite ya habia salido; sin dano.
- Raiz 1337477: `portero.jsonl` registra `congelar` rc=0 y luego `descongelar` rc=0, pero el journal de usuario dice a la misma hora `bb-portero-suite-1337477.scope: Failed with result 'resources'` ("PID ... vanished before we could move it", "Couldn't move process ... to requested cgroup"). `_adopta` solo comprueba que la RAIZ quedo en el cgroup del scope; no mira el estado de la unidad. Ya no se puede comprobar si esos procesos quedaron bajo el tope (el proceso salio).
- No se midio el estancamiento bajo carga de colapso (PSI full 98 %): provocarlo tumbaria la maquina. Lo que si se puede medir es el tiempo sin colapso con el portero actuando.

## Arreglo propuesto
Tras el job de `StartTransientUnit`, leer `ActiveState`/`Result` de la unidad (`busctl --user get-property` o `systemctl --user show`) y devolver rc distinto de 0 si quedo `failed`, registrando la causa; prueba con un ejecutor falso que devuelve `failed` (control negativo: con `active` sigue dando rc=0). El seguimiento de 14 dias se mide con `last -x reboot` y el journal de `bb-usable` (COLAPSO).

## Parte (1) arreglada (2026-10-14, worktree agent-a0e9d357) -- la parte (2) de 14 dias sigue ABIERTA
Evidencia: `tasks/evidence/DEBT-PORTERO-ADOPCION-CHOCA-CON-PIDS-QUE-SALEN-01/carrera-systemd.txt` (sin la frase de cierre: el close_check sigue rc=2 a proposito).

- Reproducido con systemd real: un hijo que sale y se recoge justo despues de `StartTransientUnit` deja la unidad `failed` (`Result=resources`) con la raiz YA en el cgroup del scope y su `memory.max` puesto. A/B de 40 intentos: codigo viejo 18 failed registrados rc=0; codigo nuevo esos 18 rc=1 y los 22 active rc=0.
- `_adopta` lee `systemctl --user show <unidad> -p ActiveState -p Result` tras ver la raiz en el scope: solo `active`/`success` da rc=0; `failed`, otro estado o lectura imposible dan rc=1 con la causa, y no se congela.
- Antes de adoptar, `aplica` comprueba la raiz por pid E instante de arranque (`Arbol.inicio`): si salio o el pid es otro proceso, fila `no_actua` con `decidida` y el motivo, sin llamar a systemd. Si sale DURANTE la adopcion y systemd falla, tambien `no_actua` (sin rc). Si systemd falla con la raiz viva, sigue siendo rc=1.
- Los hijos que ya salieron no se pasan en `PIDs` (uno muerto hacia fallar la llamada entera con "No such process").
Limites: un scope failed queda cargado con la raiz dentro y su tope (no se hace reset-failed); hijos filtrados solo por existencia; la ventana TOCTOU sigue, lo que cambia es que el rc registrado dice lo que systemd dejo.
