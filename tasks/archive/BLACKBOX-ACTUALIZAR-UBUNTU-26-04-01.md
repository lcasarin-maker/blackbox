---
id: BLACKBOX-ACTUALIZAR-UBUNTU-26-04-01
kind: task
title: "Actualizar la ATOM de Ubuntu 24.04.5 LTS a 26.04.1 LTS, con respaldo, ensayo y ruta de regreso"
status: done
severity: P2
origin: asserted
created: 2026-11-23
depende_de: []
carril: opus
close_check: {"cmd":"bash -c '. /etc/os-release; [ \"$VERSION_ID\" = \"26.04\" ]'","expect":"exit_zero","porque":"Hoy la ATOM está en Ubuntu 24.04.5 LTS (kernel 6.17.0-1032-nvidia) y el comando sale con 1. Sólo sale con 0 cuando el sistema reporta 26.04 tras la actualización."}
closed: 2026-11-26
closure_type: void_wontfix
---

## Qué es

Ubuntu ofrece actualizar a **26.04.1 LTS** (aviso de «Actualización de software»,
2026-11-23). Luis lo dejó pendiente: el aviso se cerró con «No actualizar ahora»;
puede retomarse desde Actualización de software > «Actualizar».

La ficha registra la actualización. **No se ejecuta todavía.**

## Estado medido (2026-11-23)

- `lsb_release -ds`: Ubuntu 24.04.5 LTS.
- `uname -r`: 6.17.0-1032-nvidia (kernel de NVIDIA).

## Hallazgo del 2026-11-23, 18:43: ya hay un kernel nuevo instalado y sin cargar

Al instalar `rclone`, `needrestart` informó que el kernel en ejecución es
`6.17.0-1032-nvidia` y el instalado es `7.0.0-1025-nvidia` (paquete
`linux-image-nvidia-hwe-24.04`). **Corrección (mismo día):** el próximo reinicio NO arranca
el 7.0. La capa `/etc/default/grub.d/zzz-bb-grub-default-guardado.cfg` fija
`GRUB_DEFAULT=saved` con `GRUB_SAVEDEFAULT=false`, y `/boot/grub/grubenv` tiene
`saved_entry=…gnulinux-6.17.0-1032-nvidia-advanced-…`. El 7.0 sólo arranca si alguien lo
elige en el menú o cambia `saved_entry` con `grub-set-default`. Nadie ha probado esa
combinación con el controlador de GPU de esta máquina. Medido 2026-11-23: `/lib/modules/7.0.0-1025-nvidia/kernel/nvidia-580-open/`
contiene `nvidia.ko`, `nvidia-modeset.ko` y `nvidia-uvm.ko` (precompilados; `dkms` no
está instalado), y el controlador en uso es 580.178.04. Existen los módulos, pero
**no se ha probado que carguen ni que la GPU funcione con 7.0**. Antes de reiniciar la
ATOM por cualquier motivo: tener a mano elegir el kernel anterior (6.17.0-1032) en el
arranque (GRUB) y medir `nvidia-smi` justo después.

## Por qué no es un clic

Es una actualización mayor de sistema en una máquina de producción que ya se reinicia
por OOM y que sostiene GPU, servicios de usuario y datos del consumidor de conocimiento. Riesgos a medir antes:

1. **Controlador y pila NVIDIA/CUDA.** El kernel `-nvidia` y el controlador vienen del
   proveedor. No se ha verificado que NVIDIA publique ruta de actualización a 26.04
   para esta máquina. Sin esa confirmación, una actualización puede dejar la GPU sin
   controlador. Comprobar en la documentación del proveedor antes de decidir.
2. **Modelos y motores locales** (`/srv/ai/models`, servicios `ai-nemotron*`):
   versiones de Python, CUDA y bibliotecas cambian bajo ellos.
3. **Python y entornos.** `/opt/miniforge3` y los `.venv` de `~/projects/*` enlazan
   contra bibliotecas del sistema; revisar los que no sean autocontenidos.
4. **Docker.** Siete contenedores de un proyecto externo siguen suspendidos (contrato con vencimiento 2026-12-07). Resolver esa ficha antes o
   dejar anotado su estado.
5. **Servicios y temporizadores de usuario** (consumidores externos, blackbox): comprobar que arrancan
   tras el reinicio.
6. **Herramienta de monitoreo de esta ficha:** blackbox mide arranques, memoria y
   reinicios; la actualización cambia la línea base. Registrar la medición previa.

## Qué hay que hacer antes de ejecutar

1. Respaldo verificado de lo que no se reconstruye: `~/data`, `~/projects`,
   `~/archive`, `~/secrets`, `/srv` (servicios) y la lista de paquetes
   (`apt-mark showmanual`). La base del consumidor de conocimiento ya tiene respaldo F0 pero no es el único.
2. Medir y anotar la línea base: `nvidia-smi`, `systemctl --user list-units --failed`,
   `docker ps -a`, versiones de Python/CUDA, espacio libre (el disco estaba al 97 %
   el 2026-11-23; la actualización necesita holgura).
3. Ensayo: si es posible, en otra máquina o en una copia; si no, declarar que no hubo
   ensayo.
4. Ventana acordada con Luis (la ATOM queda fuera de servicio durante la
   actualización) y ruta de regreso escrita: qué se hace si no arranca.
5. Suspender lo que no deba correr a mitad de la actualización con el contrato de
   suspensión (renombrar, con vencimiento y vigilante).

## Condiciones de cierre

- Línea base previa y posterior, con comandos y salidas literales.
- La GPU, los servicios de usuario y los temporizadores en el mismo estado que antes
  (o la diferencia explicada).
- Control negativo: una comprobación que habría fallado si el controlador de GPU no
  hubiera cargado (`nvidia-smi` con rc distinto de cero).
- Lo que quedó sin medir se declara por escrito.

## Notas

- Origen: aviso de Ubuntu del 2026-11-23, mostrado a Luis.
- Esta ficha no verifica que 26.04.1 sea compatible con la máquina; lo declara como
  pregunta abierta.

## Voto de Luis 2026-11-26 (/vote): cierre como void_wontfix

- **Decidido:** cerrar como `void_wontfix`.
- **Motivo:** conforme a `DECISIONS.md` (2026-10-12 y 2026-10-13), la ATOM permanece en DGX OS 24.04 oficial con kernel `6.17.0-1032-nvidia` y driver 580 mientras NVIDIA no publique OTA oficial sobre Ubuntu 26.04.
- **Descartado:** mantener la ficha abierta en el backlog con su `close_check` permanentemente en `rc=1`.
