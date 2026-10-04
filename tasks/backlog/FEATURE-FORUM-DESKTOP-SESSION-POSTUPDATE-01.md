---
id: FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01
kind: task
domain: USABILITY
title: "Distinguir login gráfico roto de host accesible y ofrecer recuperación acotada"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01 --evidence tasks/evidence/FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01", "expect": "exit_zero", "porque": "Verificador propuesto pendiente: requiere evidencia del caso positivo, controles negativos, compatibilidad OEM y recuperación/rollback; la ficha registra trabajo abierto."}
---

## Fuente y evidencia

[356359](https://forums.developer.nvidia.com/t/356359), [357519](https://forums.developer.nvidia.com/t/357519), [359973](https://forums.developer.nvidia.com/t/359973). Los autores reportan pantalla negra o login loop con SSH vivo. Desactivar Wayland/reiniciar GDM ayudó a un usuario; desactivar blanking/lock ayudó a otro con HDMI switch, a coste de seguridad. Versiones y causas incompletas; conservar estos fixes como hipótesis por stack, sin desactivar bloqueo de pantalla por defecto.

## Delta y prevención/resolución

FEATURE-GUI-KERNEL-VS-USERSPACE ya captura módulos NVIDIA y gdm.service. El delta es distinguir greeter activo de sesión usable, relacionar cambios de paquetes y ofrecer una recuperación específica sin reiniciar todo el host.

Reutilizar loginctl, estado GDM y journal. Perfil headless explícito; clasificar fallo de sesión frente a fallo host. Preservar trabajo de escritorio y evidencia antes de ofrecer reinicio GDM o ajuste Wayland compatible con OEM.

## Validación, riesgo y cierre

headless intencional, greeter activo con login loop, escritorio sano, SSH vivo y caída total. Validar recuperación reversible en un OEM identificado, incluyendo sesiones terminadas y rollback; cada consulta fallida cuenta como could_not_run.

El verificador de close_check todavía debe implementarse; ejecutar esta ficha exige evidencia adicional y deja registradas las consultas que no pueden correr. Ningún cambio del host se aplica al registrar la propuesta. Detalle fuente preservado en tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_*.json y threads/.

[347829](https://forums.developer.nvidia.com/t/gnome-oh-no-something-has-gone-wrong-on-dgx-spark/347829) adds several Spark reports where GNOME cannot create a session after model load/reboot while TTY or SSH remains available; NVIDIA requests `journalctl` and `nvidia-bug-report.sh`. One author posts a `apt purge/reinstall gdm3` procedure without a reported verification. Keep the recovery route non-destructive until NVIDIA validates package repair, and test shell/SSH reachability separately from display/DRM health. The proposed purge may remove DGX desktop customization. The user also reports a wireless receiver keyboard could not reach UEFI while a wired keyboard did.

[348163](https://forums.developer.nvidia.com/t/connect-spark-to-apple-studio-display/348163) resolves a distinct black-display-after-logo case: NVIDIA identifies the Apple Studio Display 5K as a tiled monitor whose primary tile is missing over Spark USB-C, and a Mutter/Canonical fix handles that case. The user confirms success after updating `mutter`, `mutter-common`, and `libmutter-14-0` to `46.2-1ubuntu0.24.04.13`; NVIDIA later confirms the fix is available through the normal Ubuntu package path. Do not recommend pulling all of `noble-proposed`; NVIDIA warns that it contains untested packages. Keep intermittent display wake as a separate unresolved symptom. During triage, check host/SSH and a known-good HDMI display before treating black video as failed OS or reflashing.


## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-GNOME-SESSION-RECOVERY`** — DGX Spark on multiple owner reports loses GNOME after model load/reboot while TTY/SSH persist; journal mentions GNOME shell/DRM no GPU and D-Bus/IBus errors. Fuente: [347829](https://forums.developer.nvidia.com/t/347829/1).
- **`BB-HDMI-LOSS-HEADLESS-RECOVERY-CAPTURE`** — An owner reports HDMI output loss with no signal every 1–2 days during overnight/idle use; local input could not wake it, SSH was not configured, and hard restart restored display but lost ongoing work. The owner returned the system… Fuente: [351461](https://forums.developer.nvidia.com/t/dgx-spark-hdmi-display-stops-working-every/351461/1).


## Índice de propuestas del lote 00

- `FORUM-00-RDP-UPDATE-REGRESSION` — [Smoke-test and preserve remote administration across desktop package updates](https://forums.developer.nvidia.com/t/364008/1); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.

## DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01

[Hilo 370458](https://forums.developer.nvidia.com/t/370458): terminales Sway quedan congeladas por `NV_ERR_NO_MEMORY` en la ruta `scanoutcarveout`, con 109 GiB libres. El dueño reproduce el problema tras pasar de driver 580.142 a 580.159.03; bajar de 6K a 4K permite abrir más ventanas pero conserva el fallo. NVIDIA propone la actualización de julio con `Adjustable Display Reserved Memory` y mejoras de manejo UMA. Falta un resultado posterior del dueño; el gist completo y las capturas quedaron sin inspeccionar.

Propuesta: comprobar soporte y valor efectivo de la reserva en el OEM ATOM, registrar versión de driver y repetir aperturas y cierres de ventanas a 6K y 4K, además de presión de caché. Distinguir la asignación de display del agotamiento general de memoria.

Riesgos: la reserva reduce memoria disponible para las cargas; atribuir el fallo a presión global puede matar procesos ajenos. Close check: reproducir el fallo, comprobar que la corrección mantiene sesión y SSH durante el ensayo y restaurar el valor previo mediante rollback verificado.

### Revisión de adjuntos — 372173 y 362204

372173: la captura de recovery muestra OOBE/cloud-init y `Started gdm.service`; ningún error explícito. Separar arranque, disponibilidad de sesión y resultado del recovery antes de recomendar reinicio/reimagen. El borrado correcto no quedó confirmado.

362204: seis TXT leídos y log inspeccionado en 79/79 snapshots (0 no parseados), todos P8, GPU 35–55 °C y sin remote-desktop en lista. Los TXT atribuyen causa a GDM/RDP y proponen llvmpipe, pero sus propios relatos declaran persistencia o verificación pendiente tras reboot. Mantener canario pre-login/post-login del mismo stack y conservar RDP; ni editar Wayland ni apagar RDP constituye fix demostrado por estos adjuntos. Evidencia con sha256 en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/attachments-root/manifest.json`.

## Avance de reutilización — 2026-10-03

La captura APT reutiliza `tools.host_diagnostics.run_readonly` para ejecutar consultas fijas acotadas; no se modificó `host_diagnostics.py` ni se añadió detección de sesión gráfica. El nuevo reporte no mide GDM, RDP o resultado de login post-update. No hay reproducción del fallo de escritorio; la ficha sigue abierta.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: La observación local no prueba sesión gráfica funcional tras actualización ni recuperación/rollback en el OEM citado.
- Evidencia faltante para cierre: stack/OEM y versiones; caso positivo y negativo post-update; sesión/telemetría y rollback capturados
- Siguiente acción: Diseñar un canario de actualización reversible con sesión local/remota verificada y recuperación; recoger stack exacto y controles negativos.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_02.json`, `tasks/evidence/FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01/host-observation.txt`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
