#!/usr/bin/env bash
# Sale 0 solo si la lista de excepciones de datos privados no nombra ninguna ruta de tasks/evidence/.
# close_check de DEBT-DATOS-PRIVADOS-EN-EVIDENCIA-HISTORICA-01 (el verificador no admite `bash -c` ni `test` en linea).
! grep -qF tasks/evidence/ "$(dirname "$0")/../tests/fixtures/datos_privados_baseline.json"
