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

## Trabajo en la ATOM

Sonda de solo lectura en `tools/huella_host.py` (`loginctl list-sessions` y estado de `gdm.service`) que distinga headless intencional de greeter sin sesion tras una actualizacion, con NOT_COLLECTED si falta permiso; sin reinicio automatico de GDM.

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/356359
- https://forums.developer.nvidia.com/t/357519
- https://forums.developer.nvidia.com/t/359973
- https://forums.developer.nvidia.com/t/gnome-oh-no-something-has-gone-wrong-on-dgx-spark/347829
- https://forums.developer.nvidia.com/t/connect-spark-to-apple-studio-display/348163
- https://forums.developer.nvidia.com/t/347829/1
- https://forums.developer.nvidia.com/t/dgx-spark-hdmi-display-stops-working-every/351461/1
- https://forums.developer.nvidia.com/t/364008/1
- https://forums.developer.nvidia.com/t/370458

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Delta y prevención/resolución

FEATURE-GUI-KERNEL-VS-USERSPACE ya captura módulos NVIDIA y gdm.service. El delta es distinguir greeter activo de sesión usable, relacionar cambios de paquetes y ofrecer una recuperación específica sin reiniciar todo el host.

Reutilizar loginctl, estado GDM y journal. Perfil headless explícito; clasificar fallo de sesión frente a fallo host. Preservar trabajo de escritorio y evidencia antes de ofrecer reinicio GDM o ajuste Wayland compatible con OEM.

## Validación, riesgo y cierre

headless intencional, greeter activo con login loop, escritorio sano, SSH vivo y caída total. Validar recuperación reversible en un OEM identificado, incluyendo sesiones terminadas y rollback; cada consulta fallida cuenta como could_not_run.

El verificador de close_check todavía debe implementarse; ejecutar esta ficha exige evidencia adicional y deja registradas las consultas que no pueden correr. Ningún cambio del host se aplica al registrar la propuesta. Detalle fuente preservado en tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_*.json y threads/.

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

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

DGX OS con GDM corre aqui y huella_host ya captura OTA/kernel/driver/apt, pero ninguna sonda distingue greeter activo de sesion usable; los casos de Apple Studio Display, HDMI switch y RDP del foro no aplican. El equipo parece de uso headless/SSH, lo que baja la probabilidad.

Version para un solo nodo Gigabyte AI TOP ATOM: Anadir a huella_host una sonda de solo lectura (loginctl list-sessions y estado de gdm.service) que clasifique headless intencional vs greeter sin sesion tras una actualizacion, con NOT_COLLECTED si falta permiso; sin reinicio de GDM automatico.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Criterios ejecutables de `tools.verify_forum_finding` (2026-10-14)
Los criterios ejecutables de `tools.verify_forum_finding` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.
