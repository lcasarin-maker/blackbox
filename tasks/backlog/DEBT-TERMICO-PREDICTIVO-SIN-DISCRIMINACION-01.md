---
id: DEBT-TERMICO-PREDICTIVO-SIN-DISCRIMINACION-01
kind: task
domain: HARDWARE
title: "El guardia termico predictivo dispara igual en boots sanos y en cortes: no discrimina"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-14
close_check: {"cmd": "grep -q termico_discrimina_medido tasks/evidence/DEBT-TERMICO-PREDICTIVO-SIN-DISCRIMINACION-01/medicion.txt", "expect": "exit_zero", "porque": "Medido el 2026-10-14: 1363 disparos y 0 confirmados en `observar`; con `--repasa` los boots CORTE_ABRUPTO disparan a 1.11 y 3.66 episodios/h de la senal corta, dentro del rango de los boots sanos (0 a 6.74). Con 2 cortes etiquetados no se puede calibrar un umbral. Cierra con una medicion que repita la comparacion con al menos 5 CORTE_ABRUPTO etiquetados por un observador de corriente externo (FEATURE-MEDIDOR-DE-ENERGIA-EXTERNO-01) y declare con la frase termico_discrimina_medido si alguna regla separa cortes de arranques sanos, o que ninguna lo hace y el guardia se retira."}
---

## Medido
`tasks/evidence/FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01/discriminacion-termico.txt` (comando: `python3 -m tools.guardia_termico_predictivo --repasa` mas las etiquetas de `bb reboots`). No se cambiaron umbrales: ajustarlos con 2 cortes seria ajustar ruido.

## Por que no se ataca ahora
Necesita mas cortes etiquetados y, para que la etiqueta no dependa de la propia temperatura, el observador de corriente externo.
