# Complemento de lectura íntegra — BB-RUST-MOTOR-PARIDAD-01

Este complemento sustituye únicamente la limitación de lectura truncada del dictamen.md vecino. Se leyó cada archivo abajo en tramos de 80 líneas o menos. El diff base..HEAD consiste en los 13 archivos de ejecución abajo; son adiciones y se leyeron íntegros. No se repitió la corrida. El dictamen sigue siendo descartar por ahora la migración, fuera del descarte condicionado del cribado (el p95 de carga lo superó). Reabrir ante carga representativa o presión caracterizadas, plazos incumplidos o falla contractual atribuible al control, con durabilidad y exclusividad equivalentes.

Sujetos y unidades:
- bin/bb-vigilante-motor: atiende solicitudes primero; gracia y sonda; evita reinicio ante ventana; ante fallo de consulta o presupuesto reinicia y registra; tope y alerta.
- tools/motor_solicitudes.py: escrituras atómicas con fsync de archivo y directorio; latidos, flock, solicitudes huérfanas, plazos y compensación; deduplica acciones consecutivas exitosas en la misma vuelta, no deduplicación universal.
- tools/workload_restart_policy.py: presupuesto por unidad y ventana, cerrojo y persistencia durable; error devuelve could_not_run.
- adopted/systemd-user/ai-nemotron-vigilante.service: oneshot que invoca el vigilante.
- adopted/systemd-user/ai-nemotron-vigilante.timer: inicio tras 5 min, OnUnitInactiveSec 2 min y AccuracySec 10 s.

Evidencia ejecución, cada archivo:
- README.md: interpretación, límites y controles declarados.
- criterio.md: umbral >1.2 s abre evaluación; descarte del cribado exige ambos p95 dentro; no autoriza migración.
- diagnostic.txt: 404 fsync 1.189441 s acumulados trazados, 302 renameat; no p95.
- diagnostico-invalido.txt: muestra awk ausente pese a PASS; inválido.
- efectos.txt: testigos de unidad ficticia, tres reinicios, un snapshot y aviso en el caso final.
- ejecutar.sh: preflight de base y diff, testigos, bwrap aislado, repositorio solo lectura.
- medir.py: 20 vueltas por carga; casos funcionales y negativos; stderr en tick invalida. Negativo de demora ejercita exceeds, no el flujo final completo; la comprobación adicional aislada de la expresión de decisión se describe en dictamen.md.
- negative-delay.txt: demora detectada, rc 0.
- negative-functional.txt: desvío detectado, rc 1.
- negative-unavailable.txt: COULD_NOT_RUN deliberado, rc 2.
- resultado-invalido.txt: corrida invalidada por ausencia de awk; no sustenta decisión.
- resultado-previo.txt: medición posterior a reparación y anterior al ajuste de identidad; no es la corrida principal.
- resultado.txt: medición registrada n=20, p95 0.068481 s normal y 1.824724 s carga; disparador verdadero.

La lectura no cambia el alcance: pruebas sintéticas no acreditan carga operativa ni todas las trayectorias de interrupción, ni ventaja Rust. Canon, plan y ficha se leyeron; el close_check de una implementación inexistente no se ejecutó. No hay bloqueo técnico restante para esta lectura. Sigue pendiente continuidad: el pre-requisito DGX-703 no está en la ruta canónica, con error literal en dictamen.md. Se mantiene informado el incumplimiento propio de elección inicial de ejecutable Orca descrito allí.

Al terminar, `git rev-parse HEAD` → `a69911dcaf575cf5833c911eb364d14e364b935d`; `git status --short --ignored` → salida vacía. El dictamen.md contiene resultados y controles de la repetición anterior.
