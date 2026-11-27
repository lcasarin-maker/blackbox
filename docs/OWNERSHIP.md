# Propiedad de áreas y monitoreo de la máquina (`blackbox`)

`blackbox` es el dueño único del monitoreo de la máquina, la forensia de caídas, los guardrails de memoria/térmica/energía y la telemetría del testigo externo. Quien necesite modificar un área sin ser su dueño debe solicitar traspaso explícito (`OWNS`) antes de editar.

| Área | Dueño único | Qué incluye | Fuentes en el repo |
| :--- | :--- | :--- | :--- |
| Monitoreo de host y forensia | `blackbox` | Muestreo PSI/memoria/térmica, veredicto de reinicios, anillo `ultimo_aliento`, `pstore`/`BERT` | `bin/bb`, `tools/ultimo_aliento.py`, `tools/reboot_verdict.py`, `tools/arranque_forense` |
| Memoria y portero de slices | `blackbox` | Escalón `bb-usable`, `portero` de `app.slice`, topes `dmem.max`, `earlyoom` | `bin/bb-usable`, `tools/portero.py`, `tools/dmem_tope.py`, `adopted/system-config/` |
| GPU, relojes y térmica | `blackbox` | Telemetría GPU, detector de reloj atascado, calibración térmica y freno | `tools/atom_gpu_telemetry.py`, `tools/reloj_atascado.py`, `tools/accion_termica.py` |
| Testigo externo y enchufe | `blackbox` | Sonda externa (`bb_testigo.py`), lector de enchufe (`medidor_energia.py`), canal único | `tools/testigo/bb_testigo.py`, `tools/medidor_energia.py`, `tools/estado_externo.py` |
| Scripts privilegiados y deriva | `blackbox` | Manifiesto sellado `bb-root-run`, instalador privilegiado y vigilancia `bb drift` | `tools/bb_root_manifest.py`, `tools/bb_root_run.py`, `enable-privileged.sh` |
| Gateway y lanzador del motor | `blackbox` | Unit `ai-nemotron.service`, `main.py`, wrapper de admisión (la config del modelo vive en el consumidor) | `tools/gateway/main.py`, `tools/gateway/ai-nemotron.service`, `tools/gateway/admission_check_wrapper.sh` |
| Consolidación, mejora y reinicio | `blackbox` (coordinación) | Gestión de backlog/archivo, puertas Temis y ventanas de reinicio autorizadas | `SPEC.md`, `DECISIONS.md`, `temis.json` |
