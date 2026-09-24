---
id: HARVEST-366211-my-gui-is-gone-and-nvidia-smi-is-not-working
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (366211-my-gui-is-gone-and-nvidia-smi-is-not-working)"
status: done
closure_type: adopted_prior_implementation
closed_at: 2026-09-23
evidence: {"verificado_el_destino": "$ # el close_check de la ficha que lleva el trabajo, corrido el 2026-09-23\n$ grep -q 'lsmod.*nvidia\\\\|systemctl status gdm' tasks/done/FEATURE-GUI-KERNEL-VS-USERSPACE.md\nrc=0  (0 = pasa)", "evidencia_del_destino": "Los 3 ficheros de tasks/done/FEATURE-GUI-KERNEL-VS-USERSPACE.md, comprobados presentes el 2026-09-23: tasks/evidence/FEATURE-GUI-KERNEL-VS-USERSPACE/e2e.txt, tasks/evidence/FEATURE-GUI-KERNEL-VS-USERSPACE/fail.txt, tasks/evidence/FEATURE-GUI-KERNEL-VS-USERSPACE/pass.txt", "limite_declarado": "El close_check de FEATURE-GUI-KERNEL-VS-USERSPACE.md es un grep sobre su propio texto: comprueba que la ficha diga lo que dice, no que la funcion sirva. Lo que sostiene el cierre son sus ficheros de evidencia, que traen comando, salida y control negativo.", "e2e": "tasks/evidence/FEATURE-GUI-KERNEL-VS-USERSPACE/e2e.txt", "fail": "tasks/evidence/FEATURE-GUI-KERNEL-VS-USERSPACE/fail.txt", "pass": "tasks/evidence/FEATURE-GUI-KERNEL-VS-USERSPACE/pass.txt"}
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-366211-my-gui-is-gone-and-nvidia-smi-is-not-working.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
reason: "CERRADA 2026-09-23 como adopted_prior_implementation. La adopcion de esta sugerencia se implemento con codigo real en un commit ANTERIOR y ese trabajo vive en tasks/done/FEATURE-GUI-KERNEL-VS-USERSPACE.md, cerrada con su propia evidencia (3 ficheros, los 3 presentes). Esta ficha era la EVALUACION, no el trabajo: su trigger era un puntero a trabajo ya terminado, no una vigilancia, asi que cerrarla no apaga nada. Verificado antes de cerrar: el close_check de FEATURE-GUI-KERNEL-VS-USERSPACE.md corre y pasa."
---

## Qué es esto

Sugerencia de cosecha, no un defecto. Atlas (la KB compartida de la flota) leyó una fuente
externa y encontró mecanismos que podrían servirle a **este proyecto** específicamente, por
dominio. Nadie de blackbox pidió esta evaluación -- es cosecha pasiva. **La decisión
de adoptar, adaptar o descartar es 100% de este proyecto.**

Cruzada antes de escribirse contra `.simplecode/fork_own.json` de este repo (si existe) para
evitar sugerir algo que ya está vendorizado -- ver DGX-505 en Atlas, donde `own_chats` cazó 3
falsos positivos de este tipo en el primer lote.

## Mecanismos encontrados, con su cita (tal como Atlas los verificó)

- Mecanismo 1 (Alternancia y fijación de targets de systemd): en el script `mode_switcher.sh`, `systemctl set-default multi-user.target` o `graphical.target` y `systemctl isolate` definen el objetivo del sistema para aislar fallas gráficas y forzar modo texto o GUI de forma persistente. Ataca la categoría de falla "inoperabilidad del sistema por corrupción de la capa de interfaz gráfica". A nuestra escala se reduce a un script local de conmutación de runlevel/target. Nombra la práctica de disponer de un mecanismo de arranque en modo rescate/consola pura — `knowledge/references/forum_nvidia_366211_my-gui-is-gone-and-nvidia-smi-is-not-working.md:107-131`
- Mecanismo 2 (Reensamblado y encadenamiento explícito de dependencias systemd para servicios de display): mediante `systemctl add-wants graphical.target gdm.service` y `systemctl restart nvidia-persistenced`, se inyecta la dependencia del gestor de ventanas directamente sobre el target gráfico y se reanuda el demonio de persistencia. Ataca la categoría de falla "desincronización de dependencias de arranque entre controlador de hardware y servicios de usuario". A nuestra escala equivale a un archivo de unidad o drop-in local de systemd. Nombra la reactivación idempotente de servicios acoplados al hardware — `knowledge/references/forum_nvidia_366211_my-gui-is-gone-and-nvidia-smi-is-not-working.md:121-129`
- Mecanismo 3 (Diagnóstico escalonado de integridad de módulos del kernel antes de servicios de espacio de usuario): verificación con `sudo lsmod | grep nvidia` y consulta de estado `systemctl status gdm.service` para desacoplar si la falla proviene de la inserción de módulos en el kernel o del gestor de sesiones. Ataca la categoría de falla "falla en cascada indistinguible entre capa de kernel y servicios de espacio de usuario". A nuestra escala es una heurística secuencial de healthcheck previo al servicio. Nombra las sondas de pre-vuelo de controladores — `knowledge/references/forum_nvidia_366211_my-gui-is-gone-and-nvidia-smi-is-not-working.md:209-224`
- El veredicto técnico es `COS`, justificado por documentar la mitigación de fallos de inicialización y recuperación de entorno gráfico frente a extensiones o drivers rotos, con disparador de reevaluación orientado a estabilizar el arranque post-reboot y prevenir la corrupción del entorno gráfico por extensiones de terceros — `knowledge/references/forum_nvidia_366211_my-gui-is-gone-and-nvidia-smi-is-not-working.md:23-25`

## Por qué se sugiere para blackbox en concreto

Los mecanismos (conmutación de targets systemd, encadenamiento de dependencias gdm/nvidia-persistenced, sondas de pre-vuelo de módulos de kernel) son monitoreo/recuperación de servicios systemd y salud de hardware -- dominio de blackbox; el dictamen sólo mencionó 'Liberation Watchdog' (fake) en 'lo que no se pudo determinar' sin considerar el miembro real.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/my-gui-is-gone-and-nvidia-smi-is-not-working/366211
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_366211_my-gui-is-gone-and-nvidia-smi-is-not-working.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.

## Root Cause

Atlas cosecho un mecanismo de una fuente externa y lo sugirio para blackbox por
dominio. **Nadie de blackbox pidio esta evaluacion** -- es cosecha pasiva, y la
ficha existe para dejar constancia de la DECISION, no para hacer el trabajo.

La decision fue ADOPTAR. El trabajo real se escribio como codigo y vive en
`tasks/done/FEATURE-GUI-KERNEL-VS-USERSPACE.md`, cerrada por su cuenta y con su propia evidencia. Esta
ficha no tenia codigo que escribir: su entregable era decidir, y decidio.

Por eso el `closure_type` es `adopted_prior_implementation` y no
`void_wontfix` (seria falso: SI se hizo trabajo) ni `duplicate` (no lo es: la
evaluacion y la implementacion son cosas distintas) ni
`relocated_prior_verification` (presupone que esta ficha ya estaba `done` en un
commit anterior, y seguia abierta).

## Regression Test

El de la ficha que lleva el trabajo, que es donde vive el sujeto:

```
grep -q 'lsmod.*nvidia\\|systemctl status gdm' tasks/done/FEATURE-GUI-KERNEL-VS-USERSPACE.md
```

Corrido el 2026-09-23 antes de cerrar esta: **pasa**. Si esa verificacion
dejara de pasar, la que se reabre es `FEATURE-GUI-KERNEL-VS-USERSPACE.md` -- ahi esta el codigo --, no esta
evaluacion, que no tiene nada que arreglar.

## Verification Evidence

La de `tasks/done/FEATURE-GUI-KERNEL-VS-USERSPACE.md`, comprobada presente el 2026-09-23 (3 de 3 ficheros):

- `tasks/evidence/FEATURE-GUI-KERNEL-VS-USERSPACE/e2e.txt`
- `tasks/evidence/FEATURE-GUI-KERNEL-VS-USERSPACE/fail.txt`
- `tasks/evidence/FEATURE-GUI-KERNEL-VS-USERSPACE/pass.txt`

LIMITE DECLARADO: el `close_check` de `FEATURE-GUI-KERNEL-VS-USERSPACE.md` es un `grep` sobre su propio
texto en la mayoria de estas fichas, o sea que comprueba que la ficha diga lo
que dice, no que la funcion sirva. Lo que sostiene el cierre de verdad son sus
ficheros de evidencia, que traen comando, salida y control negativo. Se dice
en vez de presentar el `grep` como si fuera una prueba funcional.
