---
id: DEBT-SHELLCHECK-BB-SUBJECT-01
kind: task
domain: VERDICT
title: "Resolver hallazgos del ejecutable completo fuera del alcance previo"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "shellcheck bin/bb", "expect": "exit_zero", "porque": "Reglas actuales pasan sobre el sujeto completo. Preservar semántica, controles sanos y negativos; sin supresión de reglas ni cambios de configuración para ocultar hallazgos."}
---

## Registro automático /0

Hallazgos derivados de la salida JSON literal, no transcritos a mano. Fuente: tasks/evidence/DEBT-SHELLCHECK-BB-SUBJECT-01.fail.txt. 13 hallazgos.

```json
[
  {
    "file": "bin/bb",
    "line": 464,
    "endLine": 464,
    "column": 18,
    "endColumn": 42,
    "level": "info",
    "code": 2009,
    "message": "Consider using pgrep instead of grepping ps output.",
    "fix": null
  },
  {
    "file": "bin/bb",
    "line": 1166,
    "endLine": 1166,
    "column": 46,
    "endColumn": 79,
    "level": "info",
    "code": 2012,
    "message": "Use find instead of ls to better handle non-alphanumeric filenames.",
    "fix": null
  },
  {
    "file": "bin/bb",
    "line": 1176,
    "endLine": 1176,
    "column": 42,
    "endColumn": 61,
    "level": "info",
    "code": 2012,
    "message": "Use find instead of ls to better handle non-alphanumeric filenames.",
    "fix": null
  },
  {
    "file": "bin/bb",
    "line": 1206,
    "endLine": 1206,
    "column": 35,
    "endColumn": 59,
    "level": "info",
    "code": 2009,
    "message": "Consider using pgrep instead of grepping ps output.",
    "fix": null
  },
  {
    "file": "bin/bb",
    "line": 2019,
    "endLine": 2019,
    "column": 22,
    "endColumn": 37,
    "level": "info",
    "code": 1091,
    "message": "Not following: /etc/os-release was not specified as input (see shellcheck -x).",
    "fix": null
  },
  {
    "file": "bin/bb",
    "line": 2025,
    "endLine": 2025,
    "column": 26,
    "endColumn": 79,
    "level": "info",
    "code": 2012,
    "message": "Use find instead of ls to better handle non-alphanumeric filenames.",
    "fix": null
  },
  {
    "file": "bin/bb",
    "line": 2702,
    "endLine": 2702,
    "column": 18,
    "endColumn": 18,
    "level": "warning",
    "code": 1012,
    "message": "\\t is just literal 't' here. For tab, use \"$(printf '\\t')\" instead.",
    "fix": null
  },
  {
    "file": "bin/bb",
    "line": 2702,
    "endLine": 2702,
    "column": 18,
    "endColumn": 20,
    "level": "info",
    "code": 2026,
    "message": "This word is outside of quotes. Did you intend to 'nest '\"'single quotes'\"' instead'? ",
    "fix": null
  },
  {
    "file": "bin/bb",
    "line": 2718,
    "endLine": 2718,
    "column": 8,
    "endColumn": 54,
    "level": "warning",
    "code": 2046,
    "message": "Quote this to prevent word splitting.",
    "fix": null
  },
  {
    "file": "bin/bb",
    "line": 2843,
    "endLine": 2843,
    "column": 17,
    "endColumn": 73,
    "level": "warning",
    "code": 2046,
    "message": "Quote this to prevent word splitting.",
    "fix": null
  },
  {
    "file": "bin/bb",
    "line": 2843,
    "endLine": 2843,
    "column": 19,
    "endColumn": 62,
    "level": "info",
    "code": 2012,
    "message": "Use find instead of ls to better handle non-alphanumeric filenames.",
    "fix": null
  },
  {
    "file": "bin/bb",
    "line": 2859,
    "endLine": 2859,
    "column": 10,
    "endColumn": 10,
    "level": "error",
    "code": 1087,
    "message": "Use braces when expanding arrays, e.g. ${array[idx]} (or ${var}[.. to quiet).",
    "fix": null
  },
  {
    "file": "bin/bb",
    "line": 2859,
    "endLine": 2859,
    "column": 33,
    "endColumn": 33,
    "level": "error",
    "code": 1087,
    "message": "Use braces when expanding arrays, e.g. ${array[idx]} (or ${var}[.. to quiet).",
    "fix": null
  }
]
```

## Criterio

Refactor mínimo y pruebas sobre el ejecutable real. Mantener quoting y estados could_not_run; variantes negativas deben fallar.
