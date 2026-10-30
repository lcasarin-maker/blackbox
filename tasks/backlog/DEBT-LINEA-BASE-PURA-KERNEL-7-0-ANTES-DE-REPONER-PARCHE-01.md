---
id: DEBT-LINEA-BASE-PURA-KERNEL-7-0-ANTES-DE-REPONER-PARCHE-01
kind: task
domain: GPU
title: "Medir la ATOM en estado puro y actualizado (kernel 7.0, driver 580 de fabrica, meta 26.09.3) antes de reponer el parche memacct"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-28
close_check: {"cmd": "f=tasks/evidence/DEBT-LINEA-BASE-PURA-KERNEL-7-0-ANTES-DE-REPONER-PARCHE-01/estado-puro.txt; test -s $f && grep -qE '^kernel=7[.]0[.]0-[0-9]+-nvidia$' $f && grep -q '^dmem_region_nvidia=0$' $f && grep -q '^ota_meta=26.09.3$' $f", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo no existe hoy, asi que falla. Pasa solo con una foto tomada tras reiniciar en el kernel 7.0 con el meta 26.09.3 y SIN region dmem de nvidia (modulo de fabrica)."}
---

## Decision de Luis 2026-10-28

Partir de un estado puro y lo mas nuevo, medir, y despues reponer lo desarrollado. Elegido: kernel 7.0.0-1019-nvidia con los modulos
580.178.04 de fabrica (lo que instalaria el DGX Dashboard y lo que zneill replicaria). Descartados: 6.17 (no es lo mas nuevo) y driver 615
(el parche no aplica, rc 1; cambia las librerias de usuario de vLLM). Contexto: [386060/6](https://forums.developer.nvidia.com/t/386060/6).

## Ya listo (2026-10-28, sin reiniciar)

- Foto ANTES: `~/.local/share/blackbox/antes-de-actualizar-2026-10-28.txt` (kernel 6.17.0-1032, nvidia.ko parchado sha256 2738c6d7a517..., srcversion
  73BC7E52961D5FE2E16A551, region dmem de 53.8 GB, meta 26.09.2 retenido).
- Parche compilado para el 7.0: `~/.local/share/blackbox/dmem/construidos/580.178.04-7.0.0-1019-nvidia/` (SHA256SUMS; sin firmar, sin cargar). Commit 8f797cfc.
- Llave MOK enrolada y Secure Boot activo (`mokutil`), `sign-file` del 7.0 presente. El modulo parchado del 6.17 queda en `updates/` como retroceso:
  el menu de GRUB (5 s) permite arrancar el 6.17 con la contabilidad dmem.
- Simulacion `apt-get -s`: soltar el hold instala solo `dgx-spark-ota-update-meta` 26.09.3 y `nvidia-spark-cloud-init`; ningun kernel ni driver.

## Cambio 2026-10-30: el kernel 7.0 instalado es el 1024, no el 1019

A las 14:28 un `apt upgrade` instalo `linux-image-7.0.0-1024-nvidia` (con sus modulos `linux-modules-nvidia-580-open-7.0.0-1024-nvidia` de fabrica) y a las 14:31 aptdaemon
quito el 1019 (`/var/log/apt/history.log`). En `/boot` ya no existe `vmlinuz-7.0.0-1019-nvidia`. Consecuencias: el paso 3 de la Fase 1 nombra ahora el 1024; el
`close_check` acepta cualquier `7.0.0-<n>-nvidia` (con el 1019 fijo nunca pasaba); el parche compilado para el 1019 (`construidos/580.178.04-7.0.0-1019-nvidia/`) NO
sirve para el 1024 y la Fase 2 empieza por recompilarlo contra las cabeceras del 1024 (`linux-headers-7.0.0-1024-nvidia` ya instaladas).

## ota-check del 2026-10-30 (paso 1 hecho, antes de soltar el hold)

`sudo nvidia-spark-ota-check summary`: `detected_ota` = `OTA2607`. El candidato mas cercano es `OTA2610` (2026-10-15), `match` 93.5, `torn` 6.5, 145 de 155 pruebas.
Fallan: `dgx-spark-ota-update-meta`, `nvidia-spark-cloud-init`, `kernel` (se corrigen con el paso 2 y el reinicio al 7.0), y tambien `SOCFW`, `EC`, `USBPD`,
`nvidia-mlnx-tools`, `nvidia-system-station-apps`, `nvidia-system-station-games`. Los tres de firmware (SOCFW, EC, USBPD) NO los trae apt: la foto "pura" tras
esta fase quedara en software OTA2610 con firmware anterior. Decision pendiente de Luis: actualizar firmware por el DGX Dashboard en otra ventana de reinicio, y
medir `reloj` antes y despues, porque EC y USBPD son exactamente lo que `pstore/arranque.jsonl` (pd0, pd1, ec, bios) registra.

## Linea base del reloj en estado puro (2026-10-30 16:08-16:15, kernel 7.0.0-1024, modulo de fabrica, motor parado)

`bin/bb reloj --prueba` (15 s de matmul fp16): UNA corrida con la GPU totalmente libre dio 80.3 TFLOP/s, 2080 MHz, 68.6 W, `SANO`, `tflops_valido=true`
(`reloj-puro.txt`, corrida 1). Otras seis, con `rustdesk` (200 MiB, el escritorio remoto de Luis) como unico ocupante, dieron 75.6 a 78.0 TFLOP/s a 2080 MHz y 66.4 a 69.0 W,
`SANO`, `tflops_valido=false` por competencia (`reloj-puro-valido.txt`, a pesar del nombre del archivo: ninguna de sus seis corridas es valida). Linea base citable: 80.3 (n=1) y
un rango 75.6-78.0 con `rustdesk` presente. Un n=1 limpio es poco; la comparacion con el modulo parchado se hace en las mismas condiciones. Algo relanzo `ai-nemotron.service` 31 s despues
de pararlo (16:08:43 -> 16:09:14) y no se identifico quien.

## Fase 1: linea base pura (un reinicio; lo corre Luis con sudo)

1. `sudo nvidia-spark-ota-check summary` (lo pide DECISIONS.md 2026-10-13 antes de quitar el hold) y pegar la salida.
2. Con apt, no con el DGX Dashboard: `sudo apt-mark unhold dgx-spark-ota-update-meta && sudo apt update && sudo apt full-upgrade && sudo apt-mark hold dgx-spark-ota-update-meta`
3. Respaldar y fijar el kernel 7.0: `sudo cp -a /etc/default/grub /etc/default/grub.bb-antes-7.0`; cambiar `GRUB_DEFAULT` a
   `"Advanced options for DGX OS GNU/Linux>DGX OS GNU/Linux, with Linux 7.0.0-1024-nvidia"`; `sudo update-grub`;
   comprobar con `sudo grep -c "with Linux 7.0.0-1024-nvidia'" /boot/grub/grub.cfg` (esperado 1 o mas).
4. `sudo systemctl reboot` cuando no haya trabajo abierto.
5. Despues del arranque Claude toma la foto PURA (bloque de abajo), la compara con la ANTES y corre `bb reloj --prueba`.
   Retroceso si la pantalla o el sistema fallan: elegir el 6.17 en GRUB, o por SSH restaurar `/etc/default/grub.bb-antes-7.0` y `sudo update-grub`.

Foto (sin root; `ETIQUETA` = `puro` o `parchado`):

```bash
ETIQUETA=puro; d=tasks/evidence/DEBT-LINEA-BASE-PURA-KERNEL-7-0-ANTES-DE-REPONER-PARCHE-01; mkdir -p $d; {
echo "kernel=$(uname -r)"; echo "driver=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader)"
echo "modulo=$(modinfo -F filename nvidia)"; echo "srcversion=$(modinfo -F srcversion nvidia)"
echo "dmem_region_nvidia=$(grep -c nvidia /sys/fs/cgroup/dmem.capacity 2>/dev/null)"
echo "ota_meta=$(dpkg-query -W -f='${Version}' dgx-spark-ota-update-meta)"; echo "fieldiag=$(dpkg-query -W -f='${Version}' dgx-spark-fieldiag)"
cat /etc/dgx-release; nvidia-smi -q -d CLOCK,POWER,TEMPERATURE,PERFORMANCE; tail -n 1 /var/lib/blackbox/pstore/arranque.jsonl
} > $d/estado-$ETIQUETA.txt
```

## Fase 2: reponer lo desarrollado (segundo reinicio)

Con el 7.0 ya en marcha, `uname -r` coincide y los scripts usan el `sign-file` correcto:
`sudo bash tools/dmem_modulo.sh firma ~/.local/share/blackbox/dmem/construidos/580.178.04-7.0.0-<kernel>-nvidia (recompilado para el 1024, ver Cambio 2026-10-30) && sudo bash tools/dmem_modulo.sh instala`,
reiniciar con la consola a mano, `sudo bash tools/dmem_modulo.sh verifica` y la foto con `ETIQUETA=parchado`. El 7.0 con el modulo parchado
NO esta probado (solo compilado): `bb-dmem-guardia` retrocede solo si la GPU no responde 120 s tras el arranque.

## Control negativo exigido

La foto PURA debe mostrar `dmem_region_nvidia=0` (en la ANTES la region existia: 53794045952). Una foto tomada en el 6.17 parchado debe fallar el
`close_check` (kernel=6.17.0-1032-nvidia).

## Limite

Una unidad. El kernel 7.0 tiene reportes ajenos de lentitud y pantalla a 800x600 (hilo 383185, usuarios en configuraciones distintas); aqui no esta medido.
