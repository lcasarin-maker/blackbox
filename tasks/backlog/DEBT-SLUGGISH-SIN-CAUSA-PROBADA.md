---
id: DEBT-SLUGGISH-SIN-CAUSA-PROBADA
kind: debt
title: "La maquina estuvo inusable para teclear el 2026-09-25 y bb no puede probar por que"
status: open
severity: P1
origin: detected
detector: {"rule": "bb/diagnostico-post-reinicio", "confidence": 1.0}
satd_family: MISSING_INSTRUMENT
created: 2026-09-25
close_check: {"cmd": "grep -q 'SLUGGISH causa probada' tasks/done/DEBT-SLUGGISH-SIN-CAUSA-PROBADA.md", "expect": "exit_zero"}
---

## Que pasa

El 2026-09-25 el dueno reinicio la ATOM a mano a las 05:08 porque estaba
"sumamente sluggish, casi no se podia escribir". **Ningun instrumento de bb
registro nada anormal**, y no por estar caidos: por medir otra cosa.

A las 05:08:01, veinticinco segundos antes del reinicio:

```
load1        0.95  sobre 20 nucleos
mem_avail    65.8 GB de 121
PSI          io 0.00 · cpu 0.00 · mem_full 0.00
nvidia-smi   OK en 22 ms
GPU          util 0-4 %, sin throttle, 39-48 C
journal      sin un solo warning entre las 03:00 y el reinicio
```

Y sobre las 686 muestras del arranque entero: `cpu_some >= 10 %` en el **3.2 %**
de ellas, con la racha mas larga de **3 minutos**. No hubo arrastre de maquina.

El reinicio fue limpio y pedido (`systemd-logind: System is rebooting.`): no
hubo cuelgue, ni OOM, ni panic, ni watchdog.

## Lo que SI se midio, y por que no basta

Del journal, no de bb -- y ese es parte del hallazgo:

| sujeto | CPU consumida | reloj | equivale a |
| --- | --- | --- | --- |
| `snap.antigravity...scope` | 2 h 37 min 14 s | 02:45:59 -> 05:00:57 (2 h 14 min 58 s) | **116.5 % de UN nucleo, sostenido** |
| `app-com.anthropic.Claude-345364.scope` | 15 h 09 min 54 s | arranque entero (14 h 57 min) | 101.4 % de un nucleo |
| `rustdesk.service` | 1 h 08 min 14 s | arranque entero | 7.6 % de un nucleo |
| `org.gnome.Shell`, instancia `x11` | 23 min 51 s | arranque entero | 2.7 % de un nucleo |

Dos aplicaciones interactivas quemando un nucleo cada una, durante horas.
Sobre 20 nucleos eso es el 11 % de la maquina: no mueve `load1`, no mueve
`cpu_some`, no mueve nada de lo que bb miraba. **Un total de maquina no puede
ver un cuello de botella de un solo hilo**, y teclear es un camino de hilos
unicos encadenados -- servidor X, compositor, hilo principal de la aplicacion.

Tambien se midio, y es el unico valor que se movio en una sola direccion toda
la noche: el swap paso de 16383 MiB libres a las 20:51 a 12067 a las 03:28.
**4.3 GB expulsados y nunca recuperados**, con el 53 % de la RAM libre y
`vm.swappiness=15`. Cada pagina que una aplicacion interactiva vuelve a tocar
despues de eso es una lectura de disco. Ese numero hubo que sacarlo del log de
earlyoom porque bb tampoco lo registraba.

## Lo que NO se puede afirmar, y por eso esto queda abierto

Que antigravity fuera lo que impedia teclear. Es el candidato con el numero
mas grande, pero **nadie midio la latencia mientras pasaba**, y sin eso hay al
menos tres explicaciones que los datos no separan:

1. el hilo principal de antigravity saturado -- la aplicacion no atiende el
   teclado aunque el escritorio este sano;
2. el servidor X saturado o bloqueado -- todo el escritorio lento, no una app;
3. el regreso desde swap -- cada pulsacion tocando paginas que estan en disco.

Atribuirlo a la primera porque es la de la cifra mas llamativa seria
exactamente la deduccion sin salida contraria que la ley de este repo prohibe.
El episodio queda **sin causa probada**.

## Lo que se hizo, que es instrumento y no respuesta

Tres sondas nuevas en la muestra, cada una con su control negativo corrido:

- `cpu_top` -- los cinco procesos que mas CPU quemaron desde la muestra
  anterior, con su unit de cgroup. Cierra el hueco de atribucion: `cpu_some` y
  `load1` son totales y no nombran a nadie.
- `x.{estado,ms}` -- un ida-y-vuelta completo contra el servidor X. Es la
  pregunta que hace el dueno, traducida a milisegundos. Sano en esta maquina:
  5-7 ms. Separa el caso 2 de los otros dos.
- `swap.{free_kb,total_kb,in_pag_s,out_pag_s}` -- el nivel y sobre todo el
  RITMO. `pswpin` es acumulado desde el arranque, asi que como nivel no dice
  nada; el delta por segundo es lo que cuesta.

Y una seccion en `bb scan` que lista las ventanas de contencion de CPU con su
atribucion y **el hueco maximo entre muestras**, para que dos puntos separados
cuatro horas no se lean igual que una ventana observada minuto a minuto.

## El criterio de cierre, y por que es ese

Mismo patron que `DEBT-DGX-438-SIN-CAUSA-RAIZ`, que esta en la misma
situacion: la ficha cierra cuando alguien **escribe la causa** en
`tasks/done/`, no cuando el repo compila.

El primer criterio que se le puso a esta ficha corria la suite de las sondas
nuevas, y **pasaba el mismo dia de abrirla**. Una ficha abierta cuyo criterio
ya esta satisfecho es una ficha que dice una cosa y mide otra: guardaba el
instrumento, que ya estaba puesto, en vez del sujeto, que sigue sin
explicarse. Se cambio antes de publicarla.

Lo que se pierde diciendolo: este criterio depende de que alguien escriba, no
de una medida automatica. Esa es su debilidad y esta aqui a proposito, igual
que en DGX-438 -- porque la alternativa mecanica exige que la maquina vuelva a
ponerse lenta, y un gate no puede provocar eso. La caducidad de la linea base
es lo que impide que envejezca callada.

Las sondas nuevas SI tienen su propia verificacion, y es un gate distinto:
`python3 -m pytest tests/test_bb_bash.py -k "latencia_x or cpu_top or swap"`,
con sus controles negativos. Borra `latencia_x` y fallan tres. Pero eso
verifica el instrumento; esta ficha es sobre la respuesta.

## Lo que falta, si vuelve a pasar

1. Mirar `x.ms` de las muestras de ese rato: si sube, es el escritorio y no la
   aplicacion.
2. Mirar `cpu_top`: si un solo proceso esta en el 100 % de un nucleo con la
   maquina en reposo, es el caso 1.
3. Mirar `swap.in_pag_s`: si hay trafico de vuelta sostenido, es el caso 3.
4. Los tres pueden ser ciertos a la vez. La ficha se cierra cuando uno queda
   probado sobre un episodio real, no cuando las tres sondas estan puestas.

## Limites de las sondas nuevas, dichos aqui para que nadie los suponga

- `cpu_top` usa `ps -o times=`, que da segundos ENTEROS: el piso de deteccion
  es 1 segundo-nucleo por intervalo -- el 1.7 % de un nucleo con la muestra de
  un minuto. Un proceso que nace y muere dentro del intervalo es invisible.
- `x.ms` no mide la latencia DENTRO de la aplicacion. Un Electron con su hilo
  principal quemado no atiende el teclado aunque X conteste en 5 ms.
- `swap.in_pag_s` cuenta paginas, no dice QUIEN las trajo. La atribucion
  exigiria leer `VmSwap` de ~500 procesos en cada muestra y no se ha medido
  que quepa en el presupuesto de la muestra.
