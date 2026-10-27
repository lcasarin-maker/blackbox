---
id: DEBT-CORRER-FIELDIAG-EN-ESTA-ATOM-01
kind: task
domain: THERMAL
title: "Correr NVIDIA Field Diagnostics (dgx-spark-fieldiag) en esta ATOM y conservar su summary.json"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-26
close_check: {"cmd": "test -s tasks/evidence/DEBT-CORRER-FIELDIAG-EN-ESTA-ATOM-01/fieldiag-summary.json && grep -qE \"PASS|FAIL|RETEST\" tasks/evidence/DEBT-CORRER-FIELDIAG-EN-ESTA-ATOM-01/fieldiag-summary.json", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo no existe hoy. bb lo reconoce como <destino>.fieldiag-summary.json (tools/incident_report.py:975). Cierra con el resumen real de la corrida, sea PASS, FAIL o RETEST."}
---

## Origen

zneill (hilos [386060](https://forums.developer.nvidia.com/t/386060/3) y [378945](https://forums.developer.nvidia.com/t/378945/3)) pide el resultado de los
diagnosticos de campo como linea base. En 378945 un FAIL aprueba el RMA; en 377069 aniculescu repite que un diagnostico
fallido aprueba el RMA automaticamente.

## Estado medido (2026-10-26)

- `dgx-spark-fieldiag 1.0.9-1` instalado el 2026-09-12 con `apt-get install -y dgx-spark-fieldiag=1.0.9-1` (version fijada a
  mano; el repo de NVIDIA ofrece 1.0.7, 1.0.8, 1.0.9 y 2.0.4-1, esta ultima candidata). El motivo de fijar la 1.0.9 esta
  sin registrar.
- Ningun `summary.json` ni log de resultados en la maquina: sin registro de una corrida en esta unidad.
- Secure Boot activo (`mokutil --sb-state`). `tools/incident_report.py` registra que la herramienta exige apagarlo y pasar
  a modo sin gráficos (`sudo init 3`; foro 358951 #12). Incluye pruebas de estres de energia y termicas.
- Unidad con historial: un corte de energia sin causa tras horas con el reloj atascado (hilo 386060) y zonas ACPI de 50 a
  57 C con la GPU a 9 W en una lectura puntual.

## Alcance

1. Obtener de NVIDIA (pregunta pendiente a zneill en 386060) que version quieren: 1.0.9-1 instalada o 2.0.4-1.
2. Ventana de reinicio con el motor vLLM parado, ventiladores comprobados fisicamente antes y durante, y una persona presente.
3. Procedimiento exacto en `/opt/nvidia/dgx-spark-fieldiag/README.txt` y la guia PDF del mismo directorio:
   `sudo ./partnerdiag --field` desde ese directorio. Antes: respaldo de Secure Boot (estado y claves) y plan de rollback.
4. Copiar el `summary.json` a `tasks/evidence/DEBT-CORRER-FIELDIAG-EN-ESTA-ATOM-01/fieldiag-summary.json`.

## Riesgo declarado

Las etapas de estres de energia y termica pueden llevar al equipo cerca de 97 C (trufflebutter, hilo 377069, PowerStress a
97.1 C con ventiladores en silencio). No correr sin supervision ni con el ventilador sin verificar.

## Control negativo exigido

El close_check falla hoy (archivo ausente). Un summary con resultado distinto de PASS no se oculta ni se reintenta hasta
que pase: se registra tal cual.
