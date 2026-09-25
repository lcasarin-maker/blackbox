---
id: DEBT-BB-USABLE-CIEGO-A-LA-LATENCIA
kind: debt
title: "bb-usable pregunta si la maquina sirve MEMORIA, no si el escritorio responde"
status: open
severity: P2
origin: asserted
satd_family: MISSING_INSTRUMENT
created: 2026-09-25
close_check: {"cmd": "grep -q 'umbral de latencia CALIBRADO' tasks/done/DEBT-BB-USABLE-CIEGO-A-LA-LATENCIA.md", "expect": "exit_zero", "porque": "el paso 1 (observar) ya esta hecho y sus tests pasan, asi que un criterio sobre esos tests cerraria la ficha sin que el sujeto -- que bb-usable sepa contestar si el escritorio responde -- haya cambiado. Mismo patron que DGX-438: cierra cuando alguien ESCRIBE la calibracion, que exige un episodio real."}
---

## Que pasa

`bb-usable` nacio para contestar "si la maquina SIRVE" en vez de "si systemd
sigue vivo", y lo hace por dos caminos, los dos de MEMORIA: una sonda que pide
64 MiB y los toca, y PSI `memory.full` sostenida.

El 2026-09-25 la maquina fue inusable para teclear durante horas con
`psi.mem_full` en 0.00 casi todo el rato. `bb-usable` vio una maquina sana, y
por su propia definicion tenia razon. La pregunta que no sabe hacer es la que
hizo el dueno: **si el escritorio responde**.

Desde este release esa magnitud existe y se esta registrando: `latencia_x` en
cada muestra (4-7 ms sano en esta maquina, con controles negativos para
TIMEOUT, ERROR y AUSENTE). `bb-usable` no la lee.

## Por que no se conecto de una vez, que es la parte importante

Porque `bb-usable` no informa: **actua**. Su unit lleva
`FailureAction=reboot-immediate`. Enchufarle un canal nuevo sin calibrar
significa darle permiso para reiniciar la maquina por un umbral que nadie ha
validado contra un incidente propio -- que es exactamente el error que su
propio encabezado documenta haber cometido ya una vez con la sonda de 64 MiB.

El corte de memoria (UMBRAL=10, SOSTENIDO=5 min) esta calibrado contra cuatro
congelamientos con sus controles sanos. Para la latencia del escritorio hay
**una sola medida sana** (4-7 ms) y **cero episodios malos registrados**. Con
n=0 del lado positivo no hay calibracion posible.

## Como se cierra: por pasos, y el primero NO es actuar

**PASO 1 -- HECHO el 2026-09-25.** `bb-usable` mide la latencia del servidor X
en cada sonda (cada 30 s) y la deja en el journal. **No entra en ninguna
decision**, y eso tiene su propio test: recorre el AST de `main()` y falla si
`xms` aparece en la condicion de un `if` o un `while`. Lo que se guarda ahi es
una AUSENCIA, y una ausencia sin test se pierde en la siguiente edicion.

Cinco controles negativos corridos: un servidor que se cuelga devuelve el
PLAZO entero y no un numero pequeno (si devolviera algo bajo, una grafica
leeria "rapido" justo durante el incidente); sin `DISPLAY` devuelve `None` y no
`0`, porque "no se midio" e "instantaneo" no son lo mismo; un servidor que
rechaza devuelve `None`; y el comando se lee del entorno EN CADA LLAMADA.

Ese ultimo salio de un fallo real de esta misma tarde: ligar el comando al
importar dejaba los casos negativos sin poder montarse -- al cambiar la
variable despues, la funcion seguia llamando al `xset` real y devolvia un
numero donde debia devolver `None`. Lo encontro el control negativo, no leer
el codigo.

**PASO 2 -- pendiente.** Capturar al menos un episodio malo real, con la sonda
puesta. Lo espera `DEBT-SLUGGISH-SIN-CAUSA-PROBADA`.

**PASO 3 -- pendiente.** Solo entonces derivar un corte, y que `bb-usable`
AVISE con el antes de que se le permita actuar.

Linea base acumulada hasta hoy, que es lo unico que el paso 1 compra:
4-7 ms en reposo, 8 ms de mediana y 13 ms el peor caso con 40 quemadores sobre
20 nucleos. **Cero episodios malos.** Con n=0 del lado positivo no hay
calibracion posible: un corte derivado solo de medidas sanas no puede fallar
por el motivo que vigila.

Lo que NO cierra esto: darle un umbral inventado hoy. El `close_check` exige
que alguien escriba la calibracion en `tasks/done/`, con la frase literal
`umbral de latencia CALIBRADO`, porque no hay forma honesta de que un gate
provoque el episodio que falta.
