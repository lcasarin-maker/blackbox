#!/usr/bin/env bash
# Sale 0 solo si el slice adoptado esta desplegado e identico en la maquina.
# close_check de DEBT-ATOM-SECUNDARIAS-SLICE-SIN-DESPLEGAR-01.
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cmp -s "$RAIZ/adopted/system-config/etc_systemd_system_atom-secundarias.slice" /etc/systemd/system/atom-secundarias.slice
