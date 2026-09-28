---
id: DEBT-BB-USABLE-NUNCA-MIDIO-SU-PROPIA-LATENCIA
kind: debt
title: "el canal de latencia de bb-usable lleva 5339 'sin DISPLAY' y cero mediciones"
status: open
severity: P2
origin: measured
satd_family: MISSING_INSTRUMENT
created: 2026-09-28
close_check: {"cmd": "systemctl show bb-usable -p Environment --no-pager | grep -q 'DISPLAY='", "expect": "exit_zero", "porque": "el defecto es que la unit de sistema no declara DISPLAY, asi que la sonda devuelve None en cada llamada; el cierre exige que la unit lo declare."}
evidence: {"medicion": "tasks/evidence/DEBT-BB-USABLE-NUNCA-MIDIO-SU-PROPIA-LATENCIA/medicion-2026-09-28.txt"}
---

# Technical Debt: bb-usable nunca midio la latencia que dice observar

## Finding

```
$ journalctl -u bb-usable | grep -c 'latencia del escritorio'              -> 5339
$ journalctl -u bb-usable | grep -c 'latencia del escritorio.*sin DISPLAY' -> 5339
$ journalctl -u bb-usable | grep 'latencia del escritorio' | grep -cE '[0-9]+ ?ms' -> 0
```

5339 intentos, cero numeros. `systemctl show bb-usable -p Environment` devuelve
`Environment=` vacio: es una unit de SISTEMA y no hereda el entorno de la sesion
grafica, que esta en `:1`.

CONTROL NEGATIVO de que el 0 es un hecho sobre el sujeto y no del instrumento --
los otros dos canales del MISMO demonio si escriben numeros:

```
$ journalctl -u bb-usable | grep -oE 'sonda [0-9]+ ms|avg10=[0-9.]+' | sort | uniq -c | sort -rn | head -3
    451 avg10=99.0
    197 sonda 17 ms
    167 sonda 18 ms
```

## Por que esto no lo cubre la ficha ya cerrada

`tasks/done/DEBT-BB-USABLE-CIEGO-A-LA-LATENCIA.md` (cerrada `void_wontfix` el
2026-09-27) declara el PASO 1 -- observar -- como HECHO, y su evidencia es
*"bin/bb:761 escribe el canal en cada muestra y el corpus tiene 2389 muestras
con los dos canales OK"*.

Esas 2389 muestras son de `bin/bb`, el muestreador de USUARIO, que corre bajo
`systemd --user` y si tiene `DISPLAY`. `bb-usable` es **otro proceso**, unit de
sistema, y su canal propio lleva 5339 ceros. La evidencia de cierre mide un
sujeto distinto del que la ficha dice haber arreglado.

La ficha cerrada ya contiene la frase de este defecto: *"Una fila ARMADO sobre
un demonio que corre codigo viejo es la forma mas silenciosa de este defecto."*
Aqui el codigo no es viejo. Corre, y devuelve `None` cada vez.

## El caso que lo hizo visible

El 2026-09-28 11:28:27 el OOM killer mato el renderer de `claude-desktop` y el
escritorio quedo sin interfaz 59 minutos (window mapeada, `Map State:
IsViewable`, renderer muerto). `bb-usable` no actuo y por su diseno tenia razon:
sus dos caminos que SI actuan son memoria y PSI, y la maquina si servia memoria.
El canal que habria sabido decirlo es el que lleva 5339 `sin DISPLAY`.

`enable-privileged.sh:357` asigna este caso explicitamente a este demonio:
*"Quien cubre eso es bb-usable, no earlyoom."* Ver
`DEBT-EARLYOOM-DESARMADO-POR-EL-AND-DEL-SWAP`.

## Como se cierra, y por que es barato y seguro

Declarar el entorno en la unit:

```
Environment=DISPLAY=:1
Environment=XAUTHORITY=/run/user/1000/gdm/Xauthority
```

Esto **no** toca la ruta de reinicio, y eso no es una opinion: la ficha cerrada
dejo un test que recorre el AST de `main()` y falla si `xms` aparece en la
condicion de un `if` o un `while`. Mientras ese test pase, arreglar la
observacion no puede provocar un `reboot-immediate`. Es la mitad barata del
problema y la ficha cerrada ya la declaraba como el PASO 1.

## Limite declarado

Arreglar esto NO deriva el corte. Los PASOS 2 y 3 de la ficha cerrada siguen
donde estaban, y su trigger de reapertura sigue siendo
`python3 -m tools.calibra_latencia_x` saliendo 0. Lo unico que compra es que el
canal del demonio empiece a tener datos, que hoy es n=0 dentro de bb-usable.

`DISPLAY=:1` cableado en la unit es fragil: si la sesion grafica cambia de
numero de display, la sonda vuelve a devolver `None` en silencio -- el mismo
fallo con otra causa. No se midio cual es la forma robusta (leer de
`loginctl`, o un drop-in generado). Un `Environment=DISPLAY=:1` sin un gate que
compruebe que el canal produce numeros reproduce este ticket entero.
