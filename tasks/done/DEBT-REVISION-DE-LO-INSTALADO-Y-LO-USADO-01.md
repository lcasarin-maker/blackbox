---
id: DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01
kind: task
domain: MEMORY
title: "Revisar lo instalado y corriendo contra lo que se usa (LibreChat sin uso desde agosto)"
status: done
closed_at: 2026-10-15
closure_type: relocated_prior_verification
reason: "Las limpiezas (docker 144.4 -> 34.68 GB, LibreChat, code y nvidia-ai-workbench) se ejecutaron y verificaron en commits anteriores por voto de Luis; este commit solo registra la ultima boleta (conservar fieldiag, dcgm y editores por uso medido) y mueve la ficha. Control negativo: el close_check sobre el informe de HEAD antes de este commit sale 1, despues sale 0."
evidence: {"pass": "tasks/evidence/DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01/pass.txt", "fail": "tasks/evidence/DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01/fail.txt", "e2e": "tasks/evidence/DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q decisiones_de_revision_votadas tasks/evidence/DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01/informe.txt", "expect": "exit_zero", "porque": "Peticion de Luis 2026-10-12: revisar lo instalado y lo que sigue corriendo contra lo que se usa; hace meses que no se usa LibreChat. Cierra con un informe por servicio, contenedor, timer y paquete grande: dueno, ultimo uso medido, costo en memoria, y decision (mantener, detener, desinstalar) votada por Luis. Medicion hecha el 2026-10-12 (frase revision_instalado_usado en informe.txt); falta que Luis vote cada recomendacion y que se anote la frase decisiones_de_revision_votadas."}
---

## Medido (2026-10-12)
- LibreChat (`ghcr.io/danny-avila/librechat:latest`, red host) y `mongo-librechat`: creados 2026-08-17; BD con 1 usuario, 1 conversacion y 31 mensajes; ultimo mensaje 2026-08-22; 0 mensajes en los ultimos 30 dias. Sus logs de 72 h son solo arranques.
- Lo alimenta Atlas: `atlas-api.service` ("API RAG y endpoint OpenAI-compatible para LibreChat") y su endpoint de retroalimentacion; proyecto-A NO lo usa (solo menciones en informes de auditoria). `proyecto-A-pg` es otro contenedor (BD de proyecto-A).
- Cuestan 187 MiB + 95 MiB de memoria y un puerto en red host.
## Que falta
1. Inventario de servicios de usuario y de sistema, timers, contenedores, imagenes y paquetes grandes, con ultimo uso medido.
2. Para cada uno: quien lo usa (repos, unidades que lo llaman) y decision.
3. Detener o desinstalar lo que la medicion declare sin uso, con respaldo de datos y su inverso documentado.

## Resultado de la medicion (2026-10-12, informe en tasks/evidence/DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01/informe.txt)
- LibreChat y mongo-librechat estan detenidos desde 2026-10-12 06:51 CST: los detuvo la sesion de Atlas (`docker update --restart=no` y parada a las 06:51:29, segun sus transcripciones). El unico alimentador, `atlas-api.service`, esta fallido desde 2026-10-11 22:57:42 (el reinicio por colapso mato su generacion `index.json.inflight`).
- Docker retiene 112 GB de imagenes reclamables (77 % de 144 GB); open-webui parado desde 2026-08-17 y nadie lo referencia.
- Datos grandes: /srv/ai/models 155 GB, /srv/ai/_downloads 40 GB, ~/.cache/uv 34 GB, ~/.cache/pip 15 GB.
- Recomendaciones (cada una con su inverso en el informe) esperan voto de Luis; nada se ha desinstalado.

## Avance 2026-10-14: informe hecho, falta la segunda boleta
`tasks/evidence/DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01/informe.txt` (solo lectura): contenedores con tamano y estado, disco de docker (112.1 GB de imagenes reclamables), timers de usuario y paquetes grandes. LibreChat votado por Luis: ya estaba parado (`RestartPolicy=no`, sin unidad ni timer), queda parado y sin borrar datos. Sin votar y por eso sin la frase `decisiones_de_revision_votadas`: `docker image prune -a`, open-webui parado y los contenedores de pruebas de otro proyecto. Cierra con esa segunda boleta.

## Avance 2026-10-14 (2): segunda boleta votada y ejecutada
Votos de Luis ejecutados (cifras y lo conservado en `DECISIONS.md`): imagenes de docker 144.4 -> 34.68 GB, cache de build 16.43 -> 0 GB, 36 volumenes sin uso, LibreChat/open-webui/sglang/ollama y las imagenes obsoletas de otro proyecto fuera, 347 MiB de datos del foro y de una compilacion vieja del modulo dmem archivados con zstd y verificados. Falta la ultima boleta de este informe: los paquetes grandes (cursor, code, chatgpt, antigravity, dcgm, fieldiag) y los timers de otros proyectos; sin ese voto no lleva la frase `decisiones_de_revision_votadas` y la ficha sigue abierta.

## Cierre 2026-10-15
Ultima boleta votada por Luis (conservar cursor, antigravity, chatgpt, dcgm y fieldiag; los timers ajenos se quedan; criterio: uso medido). El informe lleva la frase `decisiones_de_revision_votadas` con los votos de las tres boletas. close_check ANTES de escribirla: `grep -q decisiones_de_revision_votadas ...informe.txt` salia 1; DESPUES sale 0 (ver tasks/evidence/DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01/).

## Root Cause
Nadie había medido qué de lo instalado y corriendo se usaba: LibreChat llevaba meses parado y sin dueño, docker retenía 112 GB de imágenes reclamables y varios paquetes grandes (code, nvidia-ai-workbench) no tenían uso medido. No había inventario con último uso ni votos sobre él.

## Regression Test
El `close_check` original (`grep -q decisiones_de_revision_votadas` sobre `tasks/evidence/DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01/informe.txt`) exige la frase que sólo escribe el cierre de la última boleta. Control negativo medido: sobre el informe de `ec70ea4a` sale rc=1 (`fail.txt`); sobre el actual sale rc=0 (`pass.txt`).

## Verification Evidence
`tasks/evidence/DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01/`: `fail.txt` (rc=1 antes), `pass.txt` (rc=0 después), `e2e.txt` (`docker system df`: imágenes 34.68 GB, caché de build 0 B; `dpkg -l code nvidia-ai-workbench` ya sin los paquetes) e `informe.txt` con los votos de las tres boletas.
