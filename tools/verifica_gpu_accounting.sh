#!/usr/bin/env bash
# Sale 0 solo si el accounting mode de la GPU esta encendido.
# close_check de DEBT-GPU-ACCOUNTING-MODE-APAGADO-01.
[ "$(nvidia-smi --query-gpu=accounting.mode --format=csv,noheader 2>/dev/null)" = "Enabled" ]
