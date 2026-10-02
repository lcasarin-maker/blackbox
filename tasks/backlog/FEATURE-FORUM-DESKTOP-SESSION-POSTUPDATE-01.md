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
