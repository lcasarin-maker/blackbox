# Suspensiones vigentes

Suspender es RENOMBRAR, nunca borrar. Una suspensión sin fecha de caducidad se
vuelve permanente en silencio, así que cada entrada lleva la suya y quién vigila.

## gpu_sampler.sh — suspendido 2026-09-07

| | |
|---|---|
| **Ruta original** | `/srv/ai/gpu_governance/gpu_sampler.sh` |
| **Renombrado a** | `gpu_sampler.sh.suspendido-2026-09-07` |
| **sha256** | `ce823854e9b1dd5da6dd92c6a5a8e69d609b008d97c00a6219f3ce82e5354122` |
| **modo** | `775` |
| **Unit parada** | `ai-gpu-telemetry.service` (disable --now) |
| **Caduca** | **2026-10-07** — si sigue suspendido sin decisión, se revisa |
| **Vigila** | `bb status`, que comprueba la frescura de la telemetría absorbida |

**Por qué.** Sus campos los absorbió `Atlas/tools/atom_gpu_telemetry.py` el
mismo día: `sm_clk_mhz`, `pstate` y `throttle` entran en la misma
invocación de `nvidia-smi` (coste cero), `mem_free_mb`/`mem_avail_mb` salen
de `/proc/meminfo` sin subproceso, y `gpu_procs`/`gpu_mem_total_mib` se
piden 1 de cada 3 muestras para conservar su cadencia de 15 s. Cubierto por 6
tests nuevos en `Atlas/tests/test_atom_gpu_telemetry.py` (105 pasando).

Verificado en producción antes de suspender, no después: la muestra de las
04:14:38Z ya traía los cinco campos, y la de 04:14:33Z traía
`gpu_mem_total_mib=63713`.

**Los datos históricos NO se tocan.** `/srv/ai/logs/gpu/*.csv` sigue donde
estaba; `bb scan` los lee para ventanas anteriores a esta fecha.

**Restaurar:**
```bash
mv /srv/ai/gpu_governance/gpu_sampler.sh.suspendido-2026-09-07 \
   /srv/ai/gpu_governance/gpu_sampler.sh
systemctl --user enable --now ai-gpu-telemetry.service
```

## own-chats-classify.timer — suspendido y REACTIVADO el 2026-09-08

| | |
|---|---|
| **Unit** | `own-chats-classify.timer` → `~/projects/own_chats/daemon/` |
| **Estado** | **REACTIVADO** el mismo día, tras arreglar la causa: `enabled` + `active` |
| **Ficheros del repo** | intactos, nunca se tocaron |
| **Caduca** | **2026-10-08** — o antes, en cuanto ollama vuelva a servir |
| **Vigila** | `bb scan`, sección de core dumps: si reaparece `BUCLE x llama-server` |

**Por qué.** Disparaba un bucle de crash: `classify_fine.py` pedía
clasificaciones a ollama, ollama intentaba cargar el modelo, `llama-server`
abortaba con una excepción C++ no capturada y el ciclo se repetía ~3 veces por
segundo. **14 158 volcados y 2,2 GB** en unas horas.

No se perdió funcionalidad: ya estaba rota. El log mostraba
`1400/1647 (área movida: 0)` con `ollama error: HTTP Error 500` en **cada**
petición — recorría los ítems sin clasificar ninguno, quemando CPU y disco para
producir cero resultados.

Medido al parar: 0 volcados nuevos en 20 s, contra ~3 por segundo antes.

**Cuidado al reactivar:** `systemctl --user disable` sobre esta unit borra el
symlink de instalación además del enlace de arranque, y la unit desaparece
(`not-found`). Pasó el 2026-09-08 y se restauró recreando el symlink.

**Cerrado el mismo día.** La causa era `ollama serve` corriendo con el cwd
borrado (lo heredó de un worktree de agente que luego se limpió), así que cada
`llama-server` moría en `getcwd()`. Relanzado desde `~`, el modelo
carga y responde. Además `own_chats` pasó a usar el gateway ya cargado
(nemotron en `:8000`) en vez de levantar un segundo modelo en ollama, y
`classify_fine.py` corta tras 20 fallos consecutivos.

Verificado: `50/1664 (área movida: 23)` contra los `área movida: 0` anteriores,
0 errores del LLM y 0 volcados nuevos.
