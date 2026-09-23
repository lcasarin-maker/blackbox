---
id: HARVEST-366436-lm-studio-models-overload-freezes-spark
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (366436-lm-studio-models-overload-freezes-spark)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-366436-lm-studio-models-overload-freezes-spark.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "(pendiente)", "date": "(pendiente)", "trigger": "(pendiente)"}
reason: "REABIERTA 2026-09-23: el trigger de la decision del 2026-09-09 -- 'reabrir si aparece un caso real medido en esta maquina que lo contradiga' -- se cumplio dos veces en 30 horas. Ver 'Por que se reabrio' abajo. La decision anterior queda registrada ahi, no borrada."
---

## Qué es esto

Sugerencia de cosecha, no un defecto. Atlas (la KB compartida de la flota) leyó una fuente
externa y encontró mecanismos que podrían servirle a **este proyecto** específicamente, por
dominio. Nadie de blackbox pidió esta evaluación -- es cosecha pasiva. **La decisión
de adoptar, adaptar o descartar es 100% de este proyecto.**

Cruzada antes de escribirse contra `.simplecode/fork_own.json` de este repo (si existe) para
evitar sugerir algo que ya está vendorizado -- ver DGX-505 en Atlas, donde `own_chats` cazó 3
falsos positivos de este tipo en el primer lote.

## Mecanismos encontrados, con su cita (tal como Atlas los verificó)

- Limitación y carga JIT de un solo modelo: forzar la carga de únicamente un modelo a la vez y usar carga Just-In-Time vía API para maximizar la memoria disponible y prevenir la sobrecarga de VRAM — `knowledge/references/forum_nvidia_366436_lm-studio-models-overload-freezes-spark.md:"Yeah, I'm using JIT model loading right now and use them via API, also force that only one model can be loaded at time…"`
- Monitoreo adaptativo con detección de memoria usable (`sparkview` conmutable a `MemAvailable`): detecta en tiempo de ejecución la discrepancia de NVML en memoria unificada GB10 (donde `nvmlDeviceGetMemoryInfo` reporta ~121 GB pero no considera reservas de kernel ni page cache) y conmuta a `MemAvailable` para reflejar la capacidad asignable real — `knowledge/references/forum_nvidia_366436_lm-studio-models-overload-freezes-spark.md:"sparkview detects this condition at runtime and switches to MemAvailable for memory display."`
- Relación del mecanismo de thrashing de swap con fallas de flota: ataca la categoría de agotamiento de memoria unificada y congelamiento de kernel por contención de almacenamiento en hardware DGX Spark — `knowledge/references/forum_nvidia_366436_lm-studio-models-overload-freezes-spark.md:"El mecanismo de *exhaustión de swap y thrashing del kernel* ataca directamente el problema central reportado en el hilo."`
- Relación de la sobrecarga de memoria con fallas de flota: ataca la categoría de falta de supervisión proactiva de límites de memoria en tiempo real vinculada a Liberation Watchdog — `knowledge/references/forum_nvidia_366436_lm-studio-models-overload-freezes-spark.md:"El mecanismo de *excedente de asignación de VRAM* se relaciona con la necesidad de Watchdogs que monitoreen límites de memoria en tiempo real para prevenir congelamientos del sistema en lugar de solo detectarlos después."`

## Por qué se sugiere para blackbox en concreto

El mecanismo de supervisión proactiva de límites de memoria en tiempo real (thrashing de swap, discrepancia NVML/MemAvailable) se mapeó explícitamente a 'Liberation Watchdog' (nombre falso); el dominio real es monitoreo de hardware/memoria -- blackbox.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/lm-studio-models-overload-freezes-spark/366436
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_366436_lm-studio-models-overload-freezes-spark.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Por qué se reabrió (2026-09-23)

La decisión del 2026-09-09 fue **descartar**, y quedó así:

> `accepted.by`: the maintainer + Claude, revision de deuda 2026-09-09
> `accepted.date`: 2026-09-09
> `accepted.trigger`: revisado a fondo (codigo + fuente citada) y sin valor incremental hoy --
> **reabrir si aparece un caso real medido en esta maquina que lo contradiga**
> `reason`: Verificado en codigo: el mecanismo de sparkview (usar MemAvailable cuando NVML
> miente en memoria unificada) YA esta implementado literalmente como PSI (bin/bb,
> psi_campo()), misma fuente citada en el README. La vigilancia preventiva que pide el
> mecanismo 3 es mitigacion activa, dominio de Atlas.

Su propio trigger se cumplió dos veces en 30 horas, en esta máquina, medido:

| | congelamiento 1 | congelamiento 2 |
|---|---|---|
| inicio → reset duro | 2026-09-22 05:45 → 23:30 | 2026-09-22 23:49 → 2026-09-23 05:44 |
| duración | 17 h 45 min | 5 h 55 min |
| `%system` (20 núcleos) | 99.72 | 99.75 |
| `%iowait` | 0.01 | 0.01 |
| PSI memory **full** | 98.7 – 99.0 | 98.2 – 99.0 |
| load1 | 120 – 152 | 134 – 177 |
| pgpgin/s · majflt/s · pgsteal/s | 78 000 · 660 · 20 000 | 79 000 · 660 · 20 000 |

Fuentes: `~/.local/share/blackbox/samples/2026-09-2{2,3}.jsonl` (muestra por minuto),
`/var/log/sysstat/sa202609{22,23}` (`sar -u`, `sar -q`, `sar -B`), `journalctl -b -1`.
Ambos terminaron en reset duro por el operador: no hay registro `shutdown` en `last -x`.

**Qué contradice, exactamente.** El descarte se apoyó en dos afirmaciones, y las dos caen:

1. *"sparkview (usar MemAvailable cuando NVML miente) YA está implementado como PSI"* -- lo
   que está implementado es la **lectura**, y la lectura funcionó: PSI marcó 98-99 % los dos
   días. Nadie la consumió. `bb` la registra; ningún gate la mira antes de dejar arrancar
   trabajo. Un instrumento que mide y no frena no es la mitigación que pedía el mecanismo 3.
2. *"La vigilancia preventiva es mitigación activa, dominio de Atlas"* -- la frontera puede
   seguir siendo correcta, pero el costo de dejarla sin dueño ya está medido: 23 h 40 min de
   máquina en 30 h. Si el dominio es de Atlas, la ficha se cierra **moviéndola allá**, no
   declarándola sin valor incremental.

**Hay un hecho nuevo que ninguna de las dos fuentes anticipaba** y que la próxima decisión
tiene que cargar: **pasado el precipicio la máquina no vuelve sola**. earlyoom mató el gateway
de 33 GiB a las 05:51:40, `MemAvailable` subió de 31 a 44 GiB, y PSI memory full siguió en
99 % **seis horas más**. Liberar la memoria no la suelta. Eso descarta cualquier diseño basado
en reaccionar tarde: si la guarda no impide entrar, no sirve, porque no hay salida que ofrecer.

**Lo que ya se hizo y NO cierra esta ficha.** El 2026-09-23 se acotó el abanico en el origen
(`simplecode.utils.tool_limits.UNIFIED_MEMORY_WORKER_CAP = 6`), que es la causa medida de los
dos casos. Eso tapa el disparador conocido, no el hueco: nada cuenta globalmente los procesos
que reservan memoria unificada, así que un pytest a mano o cualquier otra herramienta repite
el cuadro. Esta ficha es ese hueco.

**Qué NO se midió, y por eso no se afirma.** No se tomaron temperaturas ni se revisó
throttling en ninguno de los dos casos, así que esta ficha no descarta ni sostiene una
componente térmica; lo que sí consta es que el kernel siguió escribiendo journal, corriendo
timers y aceptando systemd durante las 17 y las 6 horas, o sea que no fue un hard-freeze de
protección de hardware (esa es la razón por la que no se reabrió HARVEST-379195).

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
