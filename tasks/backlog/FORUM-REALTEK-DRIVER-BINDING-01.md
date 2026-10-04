---
id: FORUM-REALTEK-DRIVER-BINDING-01
kind: task
domain: NETWORK
title: "Evitar pérdida de Realtek tras warm reboot por binding al driver equivocado"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FORUM-REALTEK-DRIVER-BINDING-01 --evidence tasks/evidence/FORUM-REALTEK-DRIVER-BINDING-01", "expect": "exit_zero", "porque": "Verificador pendiente: prueba binding PCI efectivo y paquete/módulo compatible; warm/cold reboot A/B y rollback con controles de otra NIC, driver ausente y consulta fallida."}
---

## Fuente y fix reportado

[360654](https://forums.developer.nvidia.com/t/360654), enlazado desde [361628](https://forums.developer.nvidia.com/t/361628): autor DGX SparkA.7/BIOSAMI5.36_0ACUM018/Ubuntu24.04.4/kernel6.17-1008/CX7FW28.45.4028 reporta NIC ausente tras warm reboot3/3 y cold unplug30s la recupera. Identifica binding r8169 frente a r8127; modprobe.blacklist=r8169 en GRUB resuelve según autor y relata warm reboot y poweroff repetidos posteriores. Los cinco cuerpos públicos fueron leídos por Luna; falta reproducción local, versión exacta del paquete r8127 y soporte OEM actual. Es evidencia de un fix por stack, distinta de EEE/link flapping.

## Prevención y propuesta

Leer identidad PCI/driver efectivo, alias, versión y proveedor del módulo y kernel candidato antes y después del update. Reutilizar sysfs/lspci/modinfo/package metadata. Preferir paquete/configuración corregida por OEM; si el binding actual ya es r8127 y supera ensayos, registrar upstream corrected sin parche nuevo. Un workaround de blacklist requiere justificar el stack exacto y comprobar que ningún otro adaptador depende de r8169; mantener consola y kernel/config previa recuperables.

## Riesgos y cierre

El blacklist global puede desconectar otra Realtek o dejar el equipo sin módulo si r8127 falta/no carga por firma. Probar canary identificado y A/B warm/cold boots con binding, link, management SSH y paquetes/firma; conservar logs y fechas originales, controles NIC diferente y módulo ausente. Una pérdida de SSH deja estado unknown hasta corroborar host/PCI, sin powercycle automático. Registrar backup de GRUB/config y restauración verificada; suspensión de fichero usa rename/hash/modo/expiry/watcher. La ficha registra la propuesta y el test todavía pendiente; ningún cambio se aplica al host del coordinador.


## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-REALTEK-DRIVER-BINDING-ALT-OS-CORROBORATION`** — On community Fedora 43/NixOS installs, Realtek 8127 was bound to r8169; users reported Ethernet unavailable after warm reboot and hardware absent until full power-off/on. A community NVIDIA-kernel build enabling r8127 plus… Fuente: [349124](https://forums.developer.nvidia.com/t/has-anyone-tried-an-alternative-linux-distro/349124/5).


## Avance de instrumentación 2026-10-03

Se reutilizó `pci_binding` existente; la captura observó `enP7s7` enlazada a `r8127`, versión `11.014.00-NAPI`. No se observaron entradas HID, y este dato no verifica compatibilidad del paquete ni comportamiento tras warm/cold reboot. Evidencia y límites: [BB-INSTRUMENTS-devices](../../docs/evidence/BB-INSTRUMENTS-devices.md). La ficha sigue abierta y el close_check original permanece pendiente.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: Observación local no prueba binding PCI del sujeto Realtek ni warm/cold boot y rollback.
- Evidencia faltante para cierre: PCI ID y driver bound; paquete/módulo compatible; A/B cold/warm; NIC de control y driver ausente; rollback
- Siguiente acción: Capturar PCI ID, paquete y módulo efectivos y ejecutar A/B warm/cold en canario con NIC control y recuperación.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/FORUM-REALTEK-DRIVER-BINDING-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_05.json`, `tasks/evidence/FORUM-REALTEK-DRIVER-BINDING-01/host-observation.txt`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
