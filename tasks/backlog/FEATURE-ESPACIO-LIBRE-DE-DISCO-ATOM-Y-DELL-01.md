---
id: FEATURE-ESPACIO-LIBRE-DE-DISCO-ATOM-Y-DELL-01
kind: task
domain: HARDWARE
title: "bb vigila el espacio libre de disco de la ATOM y de la Dell, con tendencia y aviso al teléfono"
status: open
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-25
close_check: {"cmd": "python3 -m pytest -q tests/test_espacio_libre.py", "expect": "exit_zero", "porque": "Mide que el vigilante de espacio libre exista y pase su prueba: umbrales, tendencia en días hasta llenarse, aviso y frescura. Hoy sale distinto de 0: el archivo de prueba no existe (medido 2026-11-25) y ninguna ficha ni unidad de bb vigila el disco como instrumento propio. Un pytest ausente cuenta como fallo, nunca como éxito. No mide el control negativo por mutación ni que el aviso llegue al teléfono: los revisa quien cierre."}
---

## Por qué

El espacio libre es una medición básica y hoy bb no la tiene como instrumento propio. Varias herramientas leen el disco de paso (`statvfs` aparece en `ultimo_aliento.py`, `atom_gpu_telemetry.py` y otras), pero ninguna publica una serie, una tendencia ni un aviso. Una máquina sin espacio libre pierde registros, cachés y evidencia en el peor momento.

## Medido (2026-11-25)

- ATOM, sistema de archivos raíz: 3.7 TB en total, 3.3 TB usados, 219 GB libres, 94 % de uso. El 2026-11-23 el mismo disco estaba al 98 %: el uso varía varios puntos en dos días.
- La Dell tiene dos volúmenes de datos con más de 1 TB libres cada uno.

## Qué hacer

1. **Muestra periódica** del espacio total, usado y libre de cada volumen de la ATOM y de la Dell, publicada en el archivo único de `FEATURE-ESTADO-EXTERNO-UN-SOLO-CANAL-01` y guardada en una serie con retención declarada.
2. **Tendencia.** Días estimados hasta llenarse, con la tasa medida en la ventana, y la ventana declarada. Con pocas muestras sale `NOT_COLLECTED`, nunca una estimación inventada.
3. **Umbrales propuestos (a votar por Luis):** aviso al 85 %, urgente al 92 %, crítico al 96 %, y aviso por días restantes bajo 7. Cada cruce emite un aviso al teléfono con la misma disciplina que `aviso_earlyoom.py`: una ráfaga, un mensaje, sin repetirlo.
4. **Quién llena el disco.** Junto al aviso, los diez directorios de primer nivel que más crecieron en la ventana, sólo como lectura. El análisis por repo y por proceso queda fuera de bb: lo hace el consumidor que gobierna esos repos.
5. **Frescura declarada.** Una lectura que falla se publica como `COULD_NOT_RUN` con su causa. Una Dell que no responde es «sin dato», nunca disco lleno ni disco libre.

## Límites

Sólo lee y avisa. No borra, no mueve y no limpia: liberar espacio lo decide una persona. Depende del archivo único de `FEATURE-ESTADO-EXTERNO-UN-SOLO-CANAL-01` para la Dell. El repo es público: ni direcciones, ni usuarios ni rutas privadas en el archivo publicado ni en las pruebas.

## Control negativo exigido

Pruebas que fallan al mutar: un disco al 97 % no avisa, la tendencia con dos muestras da un número, una lectura fallida se publica como 0 % de uso, un aviso se repite en cada muestra, la Dell caída aparece con espacio libre.
