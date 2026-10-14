#!/usr/bin/env bash
# bb-root-run dmidecode-sistema -- SOLO LECTURA.
# Lee: la tabla SMBIOS tipo 1 (system) via `dmidecode -t system`; las tablas DMI
#      completas solo las lee root.
# Por que: fabricante, producto, version y SKU identifican el equipo frente al hilo del
#      foro sobre la recuperacion de apt update.
# Desbloquea: DELTA-FORUM-RECOVERY-APT-UPDATE-01.
# Aviso: la salida incluye numero de serie y UUID; no se publica sin redactar.
# Escribe: nada fuera de stdout. Sin red, sin argumentos.
set -euo pipefail

dmidecode -t system
