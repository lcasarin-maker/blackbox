---
id_origen: IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS
owner: simplecode
status: open
kind: documentary_evidence
created: 2026-11-13
---

# Suplemento documental del hallazgo existente

El ID canónico ya existe en tasks/backlog del dueño. Este documento conserva evidencia propia sanitizada y deja el backlog canónico intacto. La discrepancia de bases del corredor queda conciliada por SPEC: una base de selección inválida activa fallback; una base de fila inválida produce CNR.

La omisión del clasificador sí permanece: `echo pytest` se considera ejecución aunque solo imprime texto. Aceptación roja parcial, ejecutable desde la raíz de simplecode:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -I -c 'import sys; sys.path.insert(0,"policy"); from simple_policy.close_check_lint import classify; actual=classify("echo pytest")[0]; print("actual="+actual+" expected=no_ejecuta"); raise SystemExit(0 if actual == "no_ejecuta" else 1)'
```

La corrida equivalente con ruta de fuente explícita consta literalmente en `EVIDENCIA.md`, etiqueta canonical-red-echo: stdout `actual=ejecuta expected=no_ejecuta`, rc=1. Control contrario corrido con `grep x README.md`: stdout `actual=no_ejecuta expected=no_ejecuta`, rc=0. El control demuestra que la aceptación puede devolver ambos códigos; representa una cláusula del clasificador, y el cierre requiere todas las cláusulas canónicas y R1–R3 de la revisión anterior.

Aceptación pendiente del dueño: clasificar echo como no_ejecuta, conservar positivos reales, acordar opt-in/default con sus suites, cubrir commit con código y árbol anterior, y resolver la muestra systemctl por procedimiento autorizado. La política report-only sigue vigente; cambiar el bloqueo pertenece a la coordinación y al voto correspondiente. Evidencia fuente: simplecode cc482aa2; SHA256 close_check_lint.py bee585a24f25cf94e59cf98b75b9bb5d8c9f7f034019d5339d96b4612020cbd5.
