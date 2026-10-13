---
id: FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01
kind: task
domain: GPU
title: "Cosechar las categorias 722 y 723 del foro de NVIDIA (450 temas) que el inventario nunca recorrio"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q cobertura_completa tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/cobertura-final.txt", "expect": "exit_zero", "porque": "El cierre exige una fila por cada tema de inventario.json con veredicto y la prueba de que ninguno quedo sin tocar; hoy no existe cobertura-final.txt."}
---

## Por que
`cobertura-previa.txt`: el inventario del foro recorrio una sola categoria hija (721) de la madre 719. Las otras dos, 722 (anuncios oficiales de NVIDIA: firmware, drivers, avisos) y 723 (proyectos de la comunidad: dgxtop, nvml-unified-shim, controlador de energia, paneles de memoria), nunca se leyeron. Luis tuvo que traer 5 hilos a mano.
## Plan
1. `tools` del colector (`DEBT-RESEARCH-COLLECTOR-BB-FORUM-INVENTORY-01`): inventariar la categoria madre 719 con TODAS sus hijas por `/categories.json?include_subcategories=true`, sin corte por id, y la categoria de Docker (33); fallar si una categoria hija conocida no aparece.
2. Cada tema de `inventario.json` (450 en 722+723) se materializa como ficha-tarea (regla de enjambre: sin materializar no se prueba cobertura); lotes GENERADOS desde la lista, no transcritos.
3. Ejecutores Sonnet, un lote por tanda y sin tocar la CPU de la maquina (solo lectura de red); criterio distinto al de la cosecha anterior: ademas de "explica los cortes", ¿contiene un mecanismo REUTILIZABLE (comando, formula, herramienta, numero)? con licencia del repositorio anotada.
4. Los anuncios de 722 se leen primero: son oficiales y pueden cambiar decisiones de driver, firmware y OTA.
## Limite
La lectura de un tema es un resumen de un modelo; lo que importe se verifica en el repositorio o en la maquina antes de adoptarse (regla de bb).
