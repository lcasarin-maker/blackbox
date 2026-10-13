---
id: FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01
kind: task
domain: GPU
title: "Cosechar las categorias 722 y 723 del foro de NVIDIA (450 temas) que el inventario nunca recorrio"
status: done
closed_at: 2026-10-13
closure_type: relocated_prior_verification
reason: "Las 450 temas de las categorias 722/723 tienen resultado con lectura completa y cobertura verificada sobre el sujeto (cobertura-final.txt: 450 descargados, 0 sin resultado, 0 parciales; control negativo sin un resultado da rc=1). Los 19 parciales de la ola 1 se completaron el 2026-10-13. La etapa 2 de la ola 2 (lectura por mecanismo de 756 candidatos) se escindio a FEATURE-COSECHA-FORO-ETAPA2-LECTURA-POR-MECANISMO-01."
evidence: {"pass": "tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/pass.txt", "fail": "tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/fail.txt", "e2e": "tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q '^cobertura_completa: True' tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/cobertura-final.txt", "expect": "exit_zero", "porque": "(endurecido el 2026-10-13: antes bastaba que la palabra apareciera, tambien en una linea que dice False) El cierre exige una fila por cada tema de inventario.json con veredicto y la prueba de que ninguno quedo sin tocar; hoy no existe cobertura-final.txt."}
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

## Estado (2026-10-12, medido con `tools/verifica_cosecha_foro.py`)
- Inventario: 3043 temas = 722 (35) + 723 (415) + 721 (2198) + Docker/NGC (395), con el texto completo bajado (237 MB): descarga 3043 de 3043, 0 fallos.
- Oleada 1 (722+723, lectura por tema con esquema completo): 450 de 450 resultados validos (`ola1-resultados/`, `ola1-verificacion.json`); 208 mecanismos, 39 de utilidad alta, 75 media; **19 lecturas parciales por completar** (admitidas por los agentes o con tramo material sin leer).
- Oleada 2 etapa 1 (721 + Docker, triaje corto): 2593 de 2593 resultados validos (`ola2-triaje/`, `ola2-verificacion.json`, cobertura_completa true): 416 si, 340 quizas, 1837 no. La lectura de los hilos largos es por muestra (mensaje 1, staff y mensajes con comandos): un `no` en un hilo largo significa "no lo vi en lo leido".
- Incidencias de proceso medidas: varios agentes pisaron scripts del scratchpad compartido (se detecto por los informes y el verificador valido el esquema de todos los archivos); un resultado con enumeracion invalida corregido (365572); 3 agentes declararon mas mensajes leidos de los que el tema tiene (diferencia de 1, tolerancia de 2 en el verificador).
- Los agrupamientos por tema (`grupos-de-candidatos.json`) son por expresiones regulares y estan INFLADOS: sirven de orientacion, no de medida.
## Etapa 2 (pendiente, por mecanismo y no por hilo)
Leer completos: (a) los `si` con respuesta de personal de NVIDIA, (b) un representante por mecanismo distinto, (c) los 19 parciales de la oleada 1 y los hilos de mas de 40 mensajes marcados si/quizas. Cada mecanismo se implementa con interruptor off/observar/actuar y medicion antes de adoptarse.
## Hallazgos ya accionados
- Reloj atascado: `bb reloj` (detector + prueba activa), confirmado en esta maquina; remedio con respaldo de personal de NVIDIA (hilos 370304 y 369673): desconectar el equipo y la fuente de la pared.
- Docker en cgroup systemd: `DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01` y `dmem_modulo.sh` sin recarga.
- `bb gpumem`: memoria de GPU por contenedor desde dmem (ningun hilo la resuelve).

## Avance 2026-10-13 (lecturas parciales de la ola 1 completadas)
Las 19 lecturas parciales de la ola 1 se releyeron completas (cinco agentes Sonnet, un lote cada uno, mensaje por mensaje hasta el ultimo `POST n |`). Verificado sobre el sujeto con `python3 -m tools.verifica_cosecha_foro` (ola 1): `cobertura_completa: true`, 0 parciales, 0 `lectura_declarada_de_mas`, 0 invalidos (antes: 19 parciales, `cobertura_completa: false`). Defecto del instrumento hallado y corregido: `mensajes_reales` contaba cualquier linea que empezara por `POST ` (un cuerpo con "POST /v1/chat/completions" sumaba uno de mas); ahora cuenta la marca exacta `POST n |` (`tests/test_verifica_cosecha_foro.py::test_mensajes_reales_no_cuenta_un_cuerpo_que_empieza_por_POST`). Limite: `valida_resultado` solo revisa el esquema y no contrasta `posts_leidos` con el texto; esa comparacion la hace `verifica()` (control corrido: `posts_leidos=999` pasa el validador y falla `verifica`). Hallazgo de seguridad ajeno: el post 13 del hilo 366326 publica un token de HuggingFace dentro de un `docker run`; no se copio a ningun resultado. Sigue faltando de esta ficha: lectura completa por mecanismo de la ola 2 (candidatos si/quizas) y la entrega de la ola 1 actualizada a Atlas (no se hizo: es otro repo).

## Root Cause
El inventario de las categorias 722 y 723 (450 temas) nunca se recorrio; la cosecha previa del foro cubria solo 721 y parte de Docker.

## Regression Test
`tools/verifica_cosecha_foro.py` y `tests/test_verifica_cosecha_foro.py` (28 tests, 99 %), incluido el conteo exacto de mensajes `POST n |`.

## Verification Evidence
fail.txt: el close_check endurecido sobre una copia con `cobertura_completa: False` sale 1; pass.txt: sobre cobertura-final.txt sale 0; e2e.txt: el verificador sobre los 450 temas da cobertura completa, 0 parciales, 0 sin resultado. Pendiente (ficha nueva): etapa 2 de la ola 2.
