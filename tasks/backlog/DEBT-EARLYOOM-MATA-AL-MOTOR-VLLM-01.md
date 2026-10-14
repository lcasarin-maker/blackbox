---
id: DEBT-EARLYOOM-MATA-AL-MOTOR-VLLM-01
kind: task
domain: MEMORY
title: "earlyoom mata al motor vLLM: --avoid no lo nombra y el contenedor tiene oom_score_adj 500"
status: open
severity: P1
origin: detected
detector: {"rule": "journalctl -u earlyoom: sending SIGTERM to process ... VLLM::EngineCor", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-14
close_check: {"cmd": "grep -qF '|vllm|VLLM|docker|containerd|^bb-)' /etc/default/earlyoom", "expect": "exit_zero", "porque": "Cierra cuando el /etc/default/earlyoom desplegado lleva la regex --avoid nueva. Basta el fichero porque earlyoom-proteger solo lo deja nuevo si earlyoom quedo active tras el reinicio (si no, restaura el viejo); que el proceso vivo la lleve se comprueba a mano con el paso 3 de adopted/pendiente-de-despliegue/LEEME.txt. Control negativo: hoy sale 1; el mismo grep sobre adopted/pendiente-de-despliegue/etc_default_earlyoom sale 0."}
---

## Medicion (2026-10-14)

- `journalctl -u earlyoom --no-pager | grep -cE 'to process.*VLLM'` = 14 (17 con `(VLLM|vllm)`) en el journal retenido hoy, que empieza el 2026-09-01 (el orquestador conto 26 en una lectura anterior; la diferencia no esta explicada). Primero: `sep 08 07:41:02 ... "VLLM::EngineCor": badness 988, VmRSS 58 MiB` (la badness la pone el oom_score_adj, no la memoria). Ultimo: `oct 10 18:16:47 ... sending SIGTERM to process 559895 uid 0 "VLLM::EngineCor": badness 1038, VmRSS 8154 MiB`.
- `cat /proc/<pid>/oom_score_adj`: `vllm` 500, `VLLM::EngineCor` 500, `docker` 200.
- argv vivo de earlyoom (`/proc/<pid>/cmdline`): `-r 60 -m 10 -s 100,100 --avoid (claude-desktop|pipewire|wireplumber|dbus-daemon|gnome-shell|gnome-session|Xorg|gdm|sshd|systemd|journal|xdg-|antigravity) --prefer (pytest|triton)`. systemd quita las comillas simples de EARLYOOM_ARGS.
- `ps -eo comm | sort -u`: `vllm`, `VLLM::EngineCor`, `docker`, `dockerd`, `docker-proxy`, `containerd`, `containerd-shim`. Ningun proceso vivo tiene comm que empiece por `bb-`: los servicios bb-* corren como `python3`.
- earlyoom 1.7 (`man earlyoom`): `--avoid` resta 300 al oom_score y `--prefer` suma 300; la regex (POSIX extendida, sin anclar) se compara contra el comm (15 caracteres).

## Arreglo propuesto

`adopted/root-scripts/earlyoom-proteger.sh` (via `sudo -n bb-root-run earlyoom-proteger`) escribe `adopted/pendiente-de-despliegue/etc_default_earlyoom`: `--avoid` suma `vllm|VLLM|docker|containerd|^bb-`, `--prefer` suma `xdist|bb-portero`; umbrales sin cambio. Pasos en `adopted/pendiente-de-despliegue/LEEME.txt`.

## Limite declarado

`--avoid` no es una exclusion: con badness 1038 el motor queda en 738, y con 988 (el caso de 58 MiB) en 688. Si en el proximo episodio ningun otro proceso pasa de esa badness (con el +300 de `--prefer` incluido), earlyoom lo vuelve a elegir; el journal solo registra a la victima, no a las demas candidatas, asi que cuanto margen hay no esta medido. Cerrar de verdad el riesgo pide ademas bajar el oom_score_adj del contenedor (hoy 500) o un earlyoom con exclusion absoluta; eso es decision de Luis y queda fuera de este script. `bb-portero` en `--prefer` no casa ningun comm hoy (los scopes `bb-portero-*` son cgroups, no nombres de proceso), y un comm `bb-portero...` casaria tambien `^bb-` en `--avoid`: neto 0.
