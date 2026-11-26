---
id: DEBT-SAMPLE-JSON-ESCAPE-SYSTEMD-UNIT
kind: debt
title: "El escape de systemd corrompe las muestras JSONL"
status: done
closed_at: 2026-09-29
closure_type: fixed
evidence:
  pass: tasks/evidence/DEBT-SAMPLE-JSON-ESCAPE-SYSTEMD-UNIT/pass.txt
  fail: tasks/evidence/DEBT-SAMPLE-JSON-ESCAPE-SYSTEMD-UNIT/fail.txt
  e2e: tasks/evidence/DEBT-SAMPLE-JSON-ESCAPE-SYSTEMD-UNIT/e2e.txt
severity: P2
origin: detected
detector: {"rule": "production-verification/jsonl-parse", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-09-29
close_check: {"cmd": "python3 -m pytest tests/test_bb_bash.py::test_sample_escapa_backslash_de_la_unit_en_json -q", "expect": "exit_zero"}
---

## Hallazgo

`systemd` representa puntuación dentro de nombres de cgroup con secuencias literales como `\x2d`. `bin/bb sample` insertaba `comm` y `unit` directamente entre comillas JSON, así que una muestra real podía quedar inválida y perder todos sus campos para los analizadores posteriores.

## Root Cause

Los campos de texto dinámicos en las listas de procesos no escapaban barras inversas, comillas ni caracteres de control antes de serializar JSON.

## Plan de remediación

Escapar texto dinámico en un helper Bash mínimo antes de componer `comm` y `unit`; conservar el contenido lógico al volver a leer JSON y probar con un cgroup que contenga `\x2d`.

## Regression Test

`python3 -m pytest tests/test_bb_bash.py::test_sample_escapa_backslash_de_la_unit_en_json -q`: ejecuta `bin/bb sample` con una raíz `/proc` temporal cuyo cgroup trae `\x2d`, parsea la muestra y verifica el valor recuperado.

## Verification Evidence

El control rojo previo y la salida verde final están en `tasks/evidence/DEBT-SAMPLE-JSON-ESCAPE-SYSTEMD-UNIT/`. Una muestra aislada ejecutada con el código actual produjo una fila JSONL válida con `swap` presente.
