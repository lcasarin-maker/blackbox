---
id: DEBT-TERMICA-CORROBORACION-DE-ALARMA-SIEMPRE-DESCARTA-01
kind: task
domain: GPU
title: "bb scan leia mal la alarma de flanco y el sampler no emitia calor sostenido"
status: done
closed_at: 2026-10-11
evidence: {"fail": "tasks/evidence/DEBT-TERMICA-CORROBORACION-DE-ALARMA-SIEMPRE-DESCARTA-01.fail.txt", "pass": "tasks/evidence/DEBT-TERMICA-CORROBORACION-DE-ALARMA-SIEMPRE-DESCARTA-01.pass.txt", "e2e": "tasks/evidence/DEBT-TERMICA-CORROBORACION-DE-ALARMA-SIEMPRE-DESCARTA-01.e2e.txt"}
closure_type: relocated_prior_verification
reason: "el arreglo (estado_termico.json, aviso y gate) aterrizo en a38d157 y dc1e7f4; este commit solo mueve la ficha con su evidencia fail (b088fce, rc=5) y pass (rc=0)"
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "python3 -m pytest -q tests/test_atom_gpu_telemetry.py -k destino_del_aviso", "expect": "exit_zero", "porque": "Los eventos temp_sostenida y temp_sobre_100 ya se emiten y estan probados, pero nadie los lee en tiempo real: el sampler solo escribe al .jsonl. Cierra cuando exista un destino del aviso (decision del dueno) con su test; hoy el test no existe."}
---

## Medido (2026-10-11, `~/.local/share/blackbox/atom_gpu_telemetry.jsonl`)

- `temp_critica` en todo el archivo: **395 eventos, 395 con `corroboracion: descarta`**, 0 `corrobora`, 0 `sin_datos` (por boot: 4, 19, 21, 64, 155, 122, 10).
- Boot `54b71618`, el del corte de las 12:13 CST: 122 alarmas, las 122 descartadas. En esas 240 muestras finales (~20 min) `zmax` va de 89.1 a 96.1 C, con 28 sobre el umbral de 94.8; la racha mas larga del boot con `zmax >= 90 C` dura 161 muestras (13.4 min); el trip critico es 104.8 C.
- `bb scan "14 hours ago"` imprime `eventos termicos REALES: 0` y `picos de sensor descartados: 102 (ruido, no eventos)` para esa misma ventana.

## Causa

`_corroboracion` (`tools/atom_gpu_telemetry.py:1047`) exige que las `DEBOUNCE_MUESTRAS - 1` muestras previas esten calientes. `_alarmas` la llama en el flanco de subida, y su propio docstring dice que ahi las previas estan bajo el umbral "por construccion". La rama `corrobora` es inalcanzable desde ese camino. Un sensor que oscila alrededor del umbral cruza el flanco una y otra vez y cada cruce parece un pico aislado.

## Por que importa

Reporting politics: un gate con cero capturas tras 395 corridas es un defecto del instrumento, no evidencia de que el sujeto esta limpio. Todos los reinicios abruptos bajo carga ocurrieron con la zona caliente entre 93 y 96 C, y el reporte oficial de calor dice 0. El formato de reporte por incidente (ver investigacion del 2026-10-11) necesita calor SOSTENIDO (tiempo sobre umbral y racha mas larga), no eventos de flanco.

## Cierre

Medir el calor como residencia (minutos sobre cada umbral, racha maxima) en la telemetria y en `bb scan`; conservar `descarta` solo para picos aislados reales; test con serie sostenida (corrobora) y serie con un pico (descarta).

## Medido despues (2026-10-11): el historial de throttle tampoco llega al reporte

`bb scan` imprime `razones de throttle activas ahora mismo`, no el historial. El campo `throttle` de la telemetria de 5 s, decodificado con la mascara de `clocks_event_reasons`, da por boot:

| boot | muestras | HW_THERMAL | SW_THERMAL | SW_POWER_CAP |
|---|---|---|---|---|
| 36ebc0d9 | 27718 | 0 | 1 | 1 |
| 0de3e072 | 17000 | 0 | 5 | 0 |
| e651544a | 18081 | 0 | 1 | 6 |
| 295efc0f | 29148 | **13** | 88 | 37 |
| 54b71618 | 15795 | **6** | 66 | 48 |

El throttle termico de hardware aparece solo en los dos boots mas largos y cargados (295efc0f: 7.2 h con GPU >= 80 %; 54b71618), con la GPU entre 79 y 86 C y la zona entre 89.1 y 92.1 C. La ultima muestra con `SW_THERMAL_SLOWDOWN` del boot que murio es 2 min antes de la ultima muestra. Es correlacion con la exposicion a carga sostenida, no una causa demostrada. `tools/incident_report.py` ya imprime este historial (`throttle_del_boot`); falta llevarlo a `bb scan`.

## Pedido de la sesion "declutter atom" (2026-10-11): aviso a mas de 100 C

Medido el 11-oct 16:40 por esa sesion: `thermal_zone0` y `thermal_zone4` en 96 C con trip 104.8 C. Mi telemetria confirma 94.4-96.3 C sostenidos de 11:50 a 12:13 (pico del boot 98.1 C) sin rampa previa al corte. Piden un aviso cuando z0 o z4 pasen de 100 C.

Alcance a agregar al cierre: ademas del arreglo de la corroboracion, un evento `temp_sobre_100` (z0/z4, con debounce) y la residencia sostenida como alarma (por ejemplo, mas de 5 min sobre 94.8 C). El destino del aviso es una decision del dueno: el sampler solo escribe eventos al `.jsonl`; hoy nadie los lee en tiempo real.


## CORRECCION (2026-10-11, tarde): el defecto estaba en `bb scan`, no en la corroboracion del sampler

Al ir a "arreglar la corroboracion" lei el docstring de `_alarmas` (DGX-396): en el flanco de subida `descarta` es **por diseno** y se lee "en este instante el gate todavia no bloquearia", nunca "esto fue ruido"; quien mitiga lee `carga_gpu`. Tocar su semantica reabriria la divergencia que ese diseno cerro, asi que **no se toco**. Lo que estaba mal:

1. **`bb scan` leia `descarta` como ruido** ("picos de sensor descartados (ruido, no eventos)") e imprimia 0 eventos reales: **corregido**; ahora imprime calor sostenido y throttle decodificado (`incident_report.residencia_ventana`).
2. **El sampler no tenia ningun evento de calor sostenido**: **agregado**, aditivo y sin cambiar `_alarmas` ni lo que recibe `mitigar`: `temp_sostenida` / `temp_sostenida_fin` (ventana de 60 lecturas, banda umbral-5 C = 89.8 C, 80 %) y `temp_sobre_100` (pedido de la sesion declutter atom).

**Calibracion y su limite:** la primera version (banda umbral-2 C) no disparo nunca en la reproduccion sobre los datos reales; con la banda a umbral-5 C marca 65.8 min de las 22 h del boot del corte (3 episodios, uno 33 min antes del corte). Es UN boot: constantes provisionales, a re-medir con mas boots y con un boot SANO bajo carga pesada, que hoy no existe en los datos.

**Medido (n=8 boots):** el calor sostenido de la zona 0 estaba ACTIVO al morir en los 4 cortes abruptos (06, 07, 08 y 11-oct) y en el poweroff del 10-oct; no lo estaba en los 3 boots de poca carga. Pero el boot actual, vivo, tambien tuvo episodios, y los minutos activos por boot van de 7.7 a 516: es un indicador de estado de riesgo, no un predictor de cuando. No hay control de boot sano bajo carga.

**Falta:** el destino del aviso. El sampler solo escribe al `.jsonl`; hoy nadie recibe un `temp_sobre_100` en tiempo real.


## Destino del aviso (decidido por Luis el 2026-10-11, implementado)

**Aviso en pantalla** (`tools/aviso_termico.py`, servicio `bb-aviso-termico`) leyendo `estado_termico.json` que publica el sampler en cada muestra. Notifica solo al cambiar de estado y recuerda cada 10 min sobre 100 C; el texto de la notificacion dice que hacer (`bb who`, detener lo que no sea esencial). Entrega probada: `notify-send` salio con 0 desde un servicio de usuario.

**Correccion sobre Atlas:** se habia propuesto que Atlas consultara el archivo para frenar trabajos. Medido el mismo dia: el freno que Atlas YA usa (`tools/bb_consulta.py` llama a `--gate-termico`) habria bloqueado el 100 % de las lecturas calientes de los periodos A, B y el pre-corte, y el 93 % del periodo C, incluso con la GPU consumiendo 32-46 W de media, porque mira el pico de potencia de una ventana corta. Un consumidor nuevo en Atlas no aportaria nada, y no se construyo.

**Limites:** el aviso es manual: nadie lo atiende si no mira la pantalla, y `sostenida` ocurre varias veces por boot (3 episodios en las 22 h del boot del 11-oct), asi que puede avisar seguido. `sobre_100` no sono en ningun corte medido (maximo historico de zona: 98.6 C). Falta una prueba del aviso con un estado real de `sobre_100`, que no ha ocurrido.

El `close_check` de esta ficha pide un test `destino_del_aviso` que hoy no existe; cuando se escriba, la ficha cierra.

## Root Cause

`bb scan` leyo el campo `corroboracion` de la alarma de flanco (`descarta` por diseno, DGX-396) como "sin calor", y el sampler no emitia ningun evento de calor sostenido ni publicaba estado para que alguien lo leyera en tiempo real.

## Regression Test

`tests/test_atom_gpu_telemetry.py -k destino_del_aviso` (recorrido del sampler al aviso) mas los tests de `temp_sostenida`/`temp_sobre_100` y de `tests/test_aviso_termico.py`; cada rama con su caso negativo (mutacion que quita el manejo de OSError, y el gate sin llamada al estado).

## Verification Evidence

`tasks/evidence/DEBT-TERMICA-CORROBORACION-DE-ALARMA-SIEMPRE-DESCARTA-01.fail.txt` (commit b088fce: rc=5, el test no existe) y `.pass.txt` (rc=0, 1 passed).
