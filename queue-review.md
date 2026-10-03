# Revisión de cola LUNA-98 — tandas 12–20

Alcance: 43 fichas fuente, revisadas contra sus textos completos, `remaining-before.json` y capturas por ID. No repetí verificaciones intactas ni ejecuté ensayos host, firmware, GPU, reboot, stress o network. Los campos `after_cmd` en los verdicts indican reutilización de la salida de baseline, no una nueva ejecución. El código de salida y `could_not_run` original quedan junto a cada elemento.

## Resultados por tanda

| Tanda | IDs | Resultado | Bloqueo dominante |
|---|---:|---|---|
| 12 | 5 | 5 blocked | Evidencia comunitaria sin reproducción en stack/OEM fijado: identidad/montaje tras boot, imagen efectiva/offline, fix display, parser DSML y progreso de solicitudes. |
| 13 | 5 | 5 blocked | Falta evidencia de tuple SoC/EC aislado y ensayos reales de MiMo/Ray/cooling; el score/endpoint agregado no acredita fairness, progreso o seguridad. |
| 14 | 5 | 5 blocked | Dos selectores inexistentes; CGROUP 01 tuvo 23 lecturas `dmem.current` imposibles; fases 02–03 carecen de verificador y requieren trazas privilegiadas o compatibilidad upstream. |
| 15 | 5 | 1 already_passed, 4 blocked | APT simuló PASS de upgrade y BLOCK de critical removal con CNR=0, pero reportó closure=open: guard instalado y cobertura OEM pendientes. CGROUP patch/soak, desktop post-update y manifiesto runtime GB10 incompletos. |
| 16 | 5 | 5 blocked | Requiere A/B de clocks, salud GSP, captura netconsole, provider tras worker respawn y prueba pstore/recovery; las capturas actuales son preflight o fixtures. |
| 17 | 5 | 5 blocked | Faltan pruebas de rescate, propietario del watchdog, recuperación Wi-Fi y evidencia kernel/allocator; pstore/trazas protegidas inaccesibles sin privilegio. |
| 18 | 5 | 5 blocked | Cobertura HID post-update, RPM/fan OEM CX7, compatibilidad DRM OTA, residencia térmica y gate initrd/boot; sin aplicar cambios riesgosos al host. |
| 19 | 5 | 5 blocked | A/B EEE, referencia independiente/correlación RAS-NVMe, fix vendor pstore, versión corregida UVC y binding Realtek con controles/rollback incompletos. El detector de lectura existe, pero el evento real aún no está atribuido. |
| 20 | 3 | 2 needs_decision, 1 blocked | Drift host tiene dos diferencias reales; guardián activo ejecuta binario anterior y su close-check da CNR=1 por falta de `ExecMainStartTimestamp`. Ambas operaciones host esperan decisión. Judge requiere revisión upstream; checkout upstream está dirty y el parche preparado no se tocó. |

## Familias y evidencia

- **Selectores o verificadores ausentes:** los rc=4 de tandas 12–14 y el selector del barrido de amenazas indican controles no disponibles en este checkout; no se añadieron selectores ficticios. Los rc=1 de CGROUP, FORUM y otros verificadores son `No module named ...`, no PASS de sujeto.
- **Memoria GPU/cgroups:** la evidencia de `FEATURE-1358-CGROUP-01-REPRO` tiene `could_not_run=23`: falta `dmem.current` en cada scope/fase requerido. La medición CPU no sustituye atribución de memoria GPU. Trazas bpftrace y pruebas de parche/soak quedan pendientes.
- **Host/boot/OEM:** no se cargó driver, cambió clock, provocó panic, reinició, alteró red, instaló paquetes ni usó firmware. El reporte APT cubre únicamente simulaciones y deja el guard real/OEM sin verificar.
- **Operaciones con decisión pendiente:** no sincronizar `/etc/modprobe.d/99-blackbox-uvm.conf` o `/usr/local/bin/nvrm-watch.sh`; no reiniciar `bb-guardia-proceso.service`. Ver salidas originales en `tasks/evidence/DEBT-HOST-DEPLOYED-DRIFT-01/fail.txt`, `tasks/evidence/DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES/fail.txt` y `tasks/evidence/LUNA-98-2026-10-03/guardian-readonly-recheck.txt`.
- **Herramienta upstream:** `DEBT-JUDGE-THREAT-SWEEP-TOOLS-01` necesita que el runtime publicado lea `tools/`, pase sobre archivos limpios y rechace un homoglyph/invisible inyectado. No cambiar el ZIP/runtime local ni el repositorio upstream dirty.

Los verdicts exactos están en `/tmp/bb-luna98-verdict_12.json` hasta `/tmp/bb-luna98-verdict_20.json`. Esta tanda no cerró fichas. El único resultado PASS se identifica como `already_passed` y conserva el estado abierto registrado por su instrumento.
