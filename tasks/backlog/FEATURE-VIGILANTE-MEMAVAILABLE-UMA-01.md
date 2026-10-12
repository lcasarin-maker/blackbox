---
id: FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01
kind: task
domain: MEMORY
title: "Vigilante de MemAvailable para memoria unificada de GB10 que detenga la unidad antes del OOM del kernel"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q vigilante_uma_probado tasks/evidence/FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01/medicion.txt", "expect": "exit_zero", "porque": "Voto de Luis 2026-10-12. Cierra con una medicion: un vigilante que, bajo una linea dura de MemAvailable, detiene la unidad culpable con registro de su origen, probado con un acaparador pequeno en un scope y con su control negativo; y la comparacion con el escalon y `earlyoom` ya presentes."}
---

## Antecedentes (lectura)
evanwtf/local-llm #456 (GB10): ni el `MemoryMax` de systemd ni `docker --memory` acotan las asignaciones CUDA; `earlyoom` es la unica red de seguridad del lado GPU; un guardia externo cada 2 s que detiene la unidad bajo una linea dura de MemAvailable evito OOM del kernel.
## Ya existe aqui
`earlyoom` (global, ve `MemAvailable` y swap) y el escalon de `bb-usable` (PSI + slice, un proceso). Falta decidir si una linea dura de `MemAvailable` anade algo: en los colapsos del 2026-10-11 `MemAvailable` marcaba 15-30 GB mientras el slice estaba estancado, asi que esa senal sola no los habria visto.
## Plan por partes
1. Medir en las muestras (`samples/*.jsonl`) cuantos episodios de estancamiento habria detectado una linea de MemAvailable a distintos valores (por serie, no por intuicion).
2. Si no aporta, documentarlo y cerrar con evidencia; si aporta, implementarlo en el portero.

## Correccion (2026-10-12, Luis: "no quiero descartes superficiales")

La primera medicion comparo una linea de MemAvailable contra PSI en muestras historicas y concluyo "no aporta". Eso descarta por una sola vara. Lo medido (evidence/medicion.txt) sigue valiendo como hecho, pero no cierra: falta ver el efecto REAL de la solucion. Por decision de Luis se implementa cada solucion como INTERRUPTOR con tres modos: `off`, `observar` (registra "habria actuado" sin tocar nada) y `actuar`. Cada interruptor acumula en el registro sus aciertos, sus falsos positivos y el dano que causaria. Se decide con ese registro, no antes.

Dano medido de este vigilante si ACTUARA: a 16 GiB marca 560 muestras, 431 sin colapso (falsas); a 8 GiB marca 46, 23 falsas. Con una accion de matar, cada falsa mata trabajo sano; por eso arranca en `observar`.

## Voto de Luis 2026-10-12
Instalar el interruptor en `observar`. Hecho: `bb-vigilante-memavail.service` activo (usuario, MemoryMax 64M) con `interruptores.json` en `observar`; sin registros todavia porque MemAvailable esta sobre 8 GiB. Descartado: no instalar. Revisar `interruptores/memavail.jsonl` (`resumen('memavail')`) a la semana, 2026-10-19.

## Candidato nuevo de la cosecha de distros (2026-10-12)
`tom-doerr/gpuoom` (MIT, Rust, 2026-09-22): dispara por PSI + MemAvailable y rankea procesos contando memoria GPU por NVML, con `mlockall` para no paginarse y NVML cargado despues del bloqueo (README:34,45-47). Exige PSI activo (este kernel lo tiene). Estudiar su criterio de victima como segundo interruptor junto a `memavail`; sin ejecutarlo hasta leer su codigo (`src/`) y probarlo en un scope de laboratorio. Pendiente.
