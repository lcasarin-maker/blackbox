---
id: DEBT-BB-STATUS-DICE-FALTA-SOBRE-UN-INSTRUMENTO-ARMADO
kind: debt
title: "`bb status` reporta FALTA sobre earlyoom armado 1 de cada 6 corridas"
status: open
severity: P2
origin: detected
detector: {"rule": "auditoria de claims de SPEC 2026-09-27", "confidence": 1.0}
satd_family: FLAKY_GATE
created: 2026-09-27
close_check: {"cmd": "bash tools/status_estable.sh", "expect": "exit_zero", "porque": "el sujeto es la ESTABILIDAD del veredicto, no su valor: un solo `bb status` que salga bien no distingue arreglado de afortunado -- fue justo lo que paso al encontrarlo, con la version previa diciendo FALTA y la actual diciendo armado en la misma maquina. El script repite el chequeo y falla si el veredicto se mueve. No existe todavia: escribirlo es parte de cerrar esto, y la ficha NO se cierra sin el."}
---

## Que pasa

`bb status` clasifica `earlyoom con la punteria puesta` como **FALTA** mientras el
instrumento está demostrablemente armado. Medido el 2026-09-27, seis corridas
seguidas en la misma máquina, sin tocar nada entre ellas:

```
  corrida 1: armado: 15  falta: 0   (lineas 'Preferring' que devuelve journalctl: 1)
  corrida 2: armado: 14  falta: 1   (lineas 'Preferring' que devuelve journalctl: 1)
  corrida 3: armado: 15  falta: 0   (1)
  corrida 4: armado: 15  falta: 0   (1)
  corrida 5: armado: 15  falta: 0   (1)
  corrida 6: armado: 15  falta: 0   (1)
```

**1 de 6.** Y la columna de la derecha es el control: la misma consulta, corrida
en el mismo bucle desde el shell, devolvió la línea las seis veces.

## El sujeto está bien, y eso es lo que hace esto un defecto

Las tres pruebas, corridas el mismo día:

```
config:        --prefer '(pytest|python3|triton)'
proceso VIVO:  /usr/bin/earlyoom -r 60 -m 10 -s 10 --avoid (...) --prefer (pytest|python3|triton)
journal:       2026-09-26T15:43:05 earlyoom[2195]: Preferring to kill process names that match regex '(pytest|python3|triton)'
               2026-09-26T15:43:05 earlyoom[2195]: Will avoid killing process names that match regex '(...)'
```

`earlyoom` arrancó a las 15:43:05 del 2026-09-26, que es el arranque actual
(`-b 0`), así que la evidencia que el chequeo busca está donde la busca.

## Como se encontro, que importa

No lo encontró una revisión: lo encontró la **auditoría de claims** que
`version-bump` exige. Al verificar la fila de SPEC sobre instrumentos que dejan
de escribir en silencio, `bb status` dio `armado: 14 falta: 1` donde una hora
antes había dado `15 / 0`.

Y la primera hipótesis fue **falsa**: supuse que mis propios cambios a `bin/bb`
lo habían roto. Medido contra la versión anterior (`git show 223bc37:bin/bb`),
salió al revés — la versión PREVIA dijo FALTA y la ACTUAL dijo armado, en la
misma máquina, minutos después. No es una regresión de código: se mueve entre
corridas.

## Por que importa mas que un flake cualquiera

`bb status` es el informe que contesta «está la máquina instrumentada». Su
resumen (`armado: N  falta: M  ciego: K`) es el número que un lector usa para
decidir si hace falta correr `sudo ./enable-privileged.sh`. Un FALTA espurio
manda a alguien a re-aplicar configuración que ya está puesta, y —peor— entrena
a leer los FALTA como ruido, que es exactamente lo contrario de lo que este
informe existe para lograr.

Es además la clase de fallo que este repo ya pagó tres veces el 2026-09-26: un
veredicto que depende de la carga de la máquina y no del sujeto.

## Como se cierra

1. Averiguar por qué la consulta del chequeo vuelve vacía dentro de `bin/bb`
   mientras la misma consulta desde el shell devuelve la línea. El candidato es
   la latencia de `journalctl -b 0 -u earlyoom.service` bajo carga (662 líneas en
   el arranque actual), pero **eso no está medido** y no se escribe como causa
   hasta que lo esté.
2. Que el chequeo no dependa de una consulta que puede volver vacía sin decirlo:
   una consulta cuya salida vacía es indistinguible de «el instrumento no tiene
   punteria» necesita un tercer veredicto, `COULD_NOT_RUN`, que `bb` ya sabe
   emitir (`cannot_run`).
3. Y el criterio de cierre es de ESTABILIDAD, no de valor: repetir y comprobar
   que el veredicto no se mueve.

## Limite declarado

Esto no dice que el chequeo esté mal escrito ni que `earlyoom` esté mal
configurado: dice que el veredicto se mueve entre corridas con el sujeto quieto,
medido 1 de 6. No se midió con la máquina en reposo ni con carga controlada, así
que la tasa real es desconocida y el 1/6 es una sola muestra de seis, no una
frecuencia calibrada.
