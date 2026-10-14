---
id: DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01
kind: task
domain: MEMORY
title: "Revisar lo instalado y corriendo contra lo que se usa (LibreChat sin uso desde agosto)"
status: open
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
