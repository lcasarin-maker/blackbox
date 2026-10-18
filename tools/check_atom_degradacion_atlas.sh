#!/usr/bin/env bash
# Criterio de cierre de DEBT-ATOM-DEGRADACION-ACELERADA-DE-BOOTS-01: el comando de DGX-464 tal cual,
# corrido desde Atlas (usa `-m tools.*` y necesita su cwd). El rc viaja intacto: 0 resuelta, 1 NO, 2 COULD_NOT_RUN.
cd /home/lcasarin/projects/Atlas || exit 3
exec python -m tools.atom_degradacion_resuelta
