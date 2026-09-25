---
id: DEBT-SIN-ARNES-DE-MUTACION
kind: debt
title: El gate termico llego sin sus dos arneses de mutacion, y este repo no tiene con que correrlos
status: open
severity: P2
origin: asserted
satd_family: LOST_VERIFICATION
created: 2026-09-25
close_check: {"cmd": "grep -q atom_gpu_telemetry tools/run_mutacion.py", "expect": "exit_zero"}
---

## Que pasa

Con `tools/atom_gpu_telemetry.py` vinieron de Atlas sus dos arneses de
mutacion -- `run_mitigacion_carga_mutation.py` y `run_alarm_mark_mutation.py`
-- que rompen el modulo a proposito, una mutacion por vez, y exigen que la
suite MUERA. Un test que pasa igual con el codigo roto no prueba nada, y esos
arneses son lo unico que lo comprueba sobre la compuerta de carga y sobre el
marcado de alarmas termicas.

**No pueden correr aqui.** Los dos importan
`tools/run_injection_mutation.py`, que son 617 lineas de infraestructura
COMPARTIDA de Atlas: la usan unos 50 arneses de aquel repo. Traerla seria
duplicar infraestructura ajena, que es exactamente lo que DGX-585 vino a
quitar. Y dejarlos aqui sin ella los volvia codigo muerto que ademas rompia
`pyright` (2 errores, medidos el 2026-09-25 en el push).

Asi que se retiran de este repo y se dice por que, en vez de dejarlos
importando un modulo inexistente.

## Lo que se pierde, dicho sin adornos

La verificacion por mutacion de dos caminos del gate termico. No eran gates de
CI -- se corren a mano -- pero eran lo unico que respondia "¿estos tests
cazarian el bug?" sobre la mitigacion. Lo que queda son 137 tests y el 100 % de
cobertura de lineas, que es otra pregunta: cobertura dice que se EJECUTO, no
que se comprobaria un fallo.

Los ficheros viven en la historia de Atlas, recuperables:

```
git -C ~/projects/Atlas show 82b27781^:tools/run_mitigacion_carga_mutation.py
git -C ~/projects/Atlas show 82b27781^:tools/run_alarm_mark_mutation.py
git -C ~/projects/Atlas show HEAD:tools/run_injection_mutation.py
```

## Como se cierra

Con un `tools/run_mutacion.py` propio de este repo -- no una copia del de
Atlas, sino lo minimo que este repo necesita, que es bastante menos: mutar un
fichero en sitio, `compile()` antes de gastar maquina, correr pytest, exigir
`failed` y no `error`, y restaurar verificando por sha256. Las cuatro defensas
de aquel estan documentadas en su cabecera y se pueden derivar sin copiarlo.

Control negativo obligatorio: un mutante que la suite NO caza tiene que
reportarse como superviviente. Un arnes donde todos los mutantes mueren
siempre no discrimina un test bueno de uno decorativo.
