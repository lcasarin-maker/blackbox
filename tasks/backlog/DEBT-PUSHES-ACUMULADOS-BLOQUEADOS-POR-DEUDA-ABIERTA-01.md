---
id: DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01
kind: task
domain: SECURITY
title: "Commits de bb y Atlas sin publicar: el pre-push bloquea por deuda y por riesgo de memoria"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q repositorio_publicado tasks/evidence/DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01/publicacion.txt", "expect": "exit_zero", "porque": "El push de /clean no termino (lo mato el reinicio) y despues se pidio no repetirlo hasta tener el portero. Cierra cuando el repo este publicado (0 commits adelante de origin/master, medido con git rev-list --count origin/master..master) tras el despliegue del portero y la decision sobre el baseline de ship-freeze con dueno y fecha; frase obligatoria en publicacion.txt: repositorio_publicado."}
---

## Medido
bb: 38 commits adelante de origin/master al 2026-10-12; Atlas informa 39 locales sin empujar. `zero-debt-repo` bloquea con 100+ fichas abiertas. El pre-push corre la suite completa: solo bajo el portero (una a la vez, scope con tope).
