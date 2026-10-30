---
id: FEATURE-ARBITRO-MEMORIA-UNIFICADA-POR-PRIORIDAD-01
kind: task
domain: MEMORY
title: "Arbitro de memoria unificada por prioridad: que el vigilante elija a quien ceder la memoria por rango, no por tamano (mecanismo del guardian de Athena's Engine, reubicado desde Atlas DGX-671)"
status: done
closed_at: 2026-10-30
closure_type: fixed
reason: "vigilante_memavail.elige_culpable elige por rango ascendente (data/rangos_memoria.json, respaldo identico exigido por test, lector que nunca lanza) y dentro del rango por memoria; con un solo rango elige lo mismo que antes (test_vigilante_memavail 13/13 sin editar). Control del control: el codigo viejo detiene la suite de 9 GiB en vez del laboratorio de 1 GiB. Solo el rango: la accion es de FEATURE-ESCALERA-CEDER-CONGELAR-DETENER-VERIFICADA-01 y la declaracion de rango de Atlas en atlas-carga/1 sigue pendiente."
evidence: {"pass": "tasks/evidence/FEATURE-ARBITRO-MEMORIA-UNIFICADA-POR-PRIORIDAD-01/pass.txt", "fail": "tasks/evidence/FEATURE-ARBITRO-MEMORIA-UNIFICADA-POR-PRIORIDAD-01/fail.txt", "e2e": "tasks/evidence/FEATURE-ARBITRO-MEMORIA-UNIFICADA-POR-PRIORIDAD-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "python3 -m pytest -q tests/test_arbitro_prioridad_memoria.py", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo de pruebas no existe hoy (rc=4 medido el 2026-10-30), asi que falla. Pasa solo cuando existan las pruebas del arbitro: con el acaparador de menor rango sobre la linea el vigilante lo elige aunque otra unidad de mayor rango tenga mas memoria, y con el control negativo (una unidad de rango alto con mas memoria) no la toca."}
---

## Origen y reubicacion

Reubicada el 2026-10-30 desde `Atlas/tasks/backlog/DGX-671.md` por dictamen de esta sesion y orden de Luis ("evalua la ficha ... determina si es de atlas o de bb"). La cosecha de Athena (Atlas, commit `c177d6b98`) la creo en Atlas porque la ingesta vive ahi; el sujeto es la maquina, no la recuperacion con fuente.

Por que es de bb: `SPEC.md` ("Actuar sobre lo que mide, donde la inaccion cuesta la maquina entera", decision 0006) y la custodia de monitoreo y cuelgue; las manos ya viven aqui (`vigilante_memavail` en `actuar`, `portero` en `actuar`, `accion_termica` sobre la unidad que Atlas declara en `atlas-carga/1`); el arnes con tope de memoria (`bb cap`) es de bb. Atlas conserva solo su parte del contrato de datos (abajo).

## Lo leido de Athena's Engine (`Atlas/knowledge/references/github_com_xangel82_Athena_Engine.md`, solo lectura)

- Es un desarrollo especifico para GB10: requisitos "An NVIDIA GB10 with 128 GB of unified memory, DGX OS" (seccion Requirements) y linaje del fork `DS4-GB10-GX10-DSpark-CUDA`. Las cifras son del autor, sin verificar aqui.
- Prioridad declarada del guardian: voz, luego conversaciones, luego busqueda, luego video; `GET /internal/memory` muestra el mapa (seccion de servicios). Carga cada servicio la primera vez que se pide y lo devuelve tras un rato de reposo.
- Antes de cargar un modelo libera el anterior y comprueba que el espacio existe; si no, no asigna nada y devuelve el modelo previo (seccion "Several models, one engine").
- El prestamo de memoria es cooperativo y desigual: para video Full HD, Qwen puede prestar sus pesos mientras descansa y DeepSeek todavia no.
- Se distribuye como binarios bajo PolyForm Strict 1.0.0: sin fuente, sin versiones modificadas. Solo se puede adoptar el mecanismo descrito, no codigo.

## Lo que la ficha de Atlas decia y esta lectura corrige

1. "Hoy hay una compuerta de entrada y un monitor sin manos": falso para bb. `interruptores.json` marca `memavail: actuar` y `portero: actuar`; `vigilante_memavail` detiene (`systemctl --user stop`) la unidad elegible de mayor `memory.current`. Lo que falta es el RANGO: hoy elige por tamano y solo distingue protegido o no (`data/procesos_protegidos.json`, que protege `vllm`, `docker`, `containerd`).
2. "DGX-30 es un OOM": no. `DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01` (hecha) lo leyo en Atlas: cuelgue del 2026-07-31 por `NV_ERR_NO_MEMORY` del driver. DGX-201 es el cuelgue del 2026-08-21 (la compuerta miro el nivel, no la pendiente). Los OOM del 2026-08-07 y 08-14 NO se leyeron aqui; candidatos de Atlas que los mencionan: DGX-13, 22, 75, 568, 584.
3. "Ceder y recuperar" no se traslada tal cual. Medido el 2026-10-30 con una unidad transitoria de 300 MiB:

   ```
   antes:     MemoryCurrent=318562304
   congelada: MemoryCurrent=318562304 FreezerState=frozen
   detenida:  MemoryCurrent=[not set] active=inactive
   ```

   Congelar (`cgroup.freeze`, lo que hace el portero) NO devuelve memoria; detener la devuelve y pierde el trabajo. El control negativo es la tercera linea: el mismo instrumento muestra memoria liberada cuando la unidad se detiene. En Athena el video cede en su siguiente paso porque coopera dentro del mismo proceso; con procesos independientes eso no existe.

## Para cerrar

Escalera ponytail, sin componente nuevo (el SPEC declara fuera de alcance duplicar mecanismos que ya cubren el problema):

1. Un campo `rango` por unidad en un fichero hermano de `data/procesos_protegidos.json` (con copia de respaldo identica exigida por test, como la lista actual) y que `vigilante_memavail.elige_culpable` ordene por rango ascendente y despues por memoria, en vez de solo por memoria.
2. La accion segun lo medido arriba (`stop` libera y pierde el trabajo; `freeze` conserva ambos) la resuelve `FEATURE-ESCALERA-CEDER-CONGELAR-DETENER-VERIFICADA-01`; esta ficha solo aporta el rango.
3. Pruebas en `tests/test_arbitro_prioridad_memoria.py` con control negativo, corridas bajo tope de memoria (`bb cap` o scope transitorio): (a) el acaparador de menor rango sobre la linea es el elegido aunque otra unidad de mayor rango tenga mas memoria; (b) negativo: si la de mayor rango es la unica elegible, `REFUSED` o `NOT_COLLECTED`, nunca se detiene; (c) el motor (`vllm`, `docker`) sigue sin ser elegible.
4. Arrancar en `observar` (regla de `interruptores.py`: se decide con aciertos y falsos positivos). Precedente medido: a 16 GiB `memavail` marco 560 muestras y 431 fueron falsas.

## Familia de adaptaciones (voto de Luis 2026-10-30: analizar las ideas y adecuarlas a huecos propios, no solo adoptar)

Las ideas de Athena se adaptan a bb como un observador externo (rango declarado, efecto medido, escalada verificada), cada una atada a un hueco medido de bb:

- Rango: esta ficha.
- `FEATURE-MAPA-DE-MEMORIA-FORENSE-AL-ACTUAR-01`: el mapa por dueno al instante de actuar (hueco de `DEBT-COLAPSO-CONFINADO...`).
- `FEATURE-ADMISION-TODO-O-NADA-CON-HOLGURA-REAL-01`: comprobar el espacio real antes de admitir (la puerta con `memory.current` dejo pasar la suite del 2026-10-16).
- `FEATURE-ESCALERA-CEDER-CONGELAR-DETENER-VERIFICADA-01`: ceder de verdad, con cada escalon medido.
- `FEATURE-RESIDENTES-INACTIVOS-CONTRA-CALOR-01`: descargar tras reposo, solo medir por ahora.

## Parte de Atlas (contrato de datos, sin importar codigo)

Que Atlas declare el rango de sus unidades en `atlas-carga/1` (`$BLACKBOX_DATA/atlas_carga.json`). Ficha propia en Atlas; esta no edita ese repo mas alla de la nota de reubicacion en DGX-671.

## Limites declarados

- Memoria de CPU y unificada visible en `memory.current`; la memoria CUDA no contabilizada por cgroup sigue fuera (`FEATURE-1358-CGROUP-*`).
- No se leyeron DGX-673 ni DGX-674 de Atlas, ni los OOM del 2026-08-07 y 08-14.

## Cierre (2026-10-30): solo el rango

Hecho:

- `data/rangos_memoria.json`, hermano de `data/procesos_protegidos.json`: cinco clases de menor a mayor rango, laboratorio (`bb-lab-*.scope`, 0), suites (`bb-portero-suite-*.scope`, 1), atlas (2, sin patrones), sesion (`app-*.scope`, `session-*.scope`, 3) y motor (`*vllm*`, `*docker*`, `*containerd*`, 4). Globs `fnmatch` sin distinguir mayusculas.
- `tools/vigilante_memavail.py`: `RESPALDO_RANGOS` (identico al fichero, lo exige `test_el_respaldo_es_identico_al_fichero`), `cargar_rangos` (nunca lanza; con el fichero ausente o mal formado usa el respaldo y avisa por stderr con `logging`, igual que `cargar_protegidos`) y `elige_culpable` filtra las elegibles al rango minimo y dentro de el aplica el mismo `max` de antes. El veredicto lleva ahora el campo `rango`.
- Decisiones documentadas en el `_doc` del fichero: una unidad que casa con varias clases toma la de MENOR rango, y una sin clase toma el rango mas bajo declarado; el rango alto se gana declarandolo, nunca por omision. El rango solo ordena: lo protegido sigue saliendo `REFUSED` si es lo elegido, como antes.
- Pruebas: `tests/test_arbitro_prioridad_memoria.py` (24 casos, incluido el control del control contra el codigo de `c891d9a2`).

NO hecho y pendiente:

- **La parte de Atlas**: declarar el rango de sus unidades en `atlas-carga/1` (`$BLACKBOX_DATA/atlas_carga.json`). La clase `atlas` existe con la lista de patrones vacia porque bb no sabe los nombres de unidad de Atlas (`tools/accion_termica.py`); hasta que Atlas los declare, sus unidades caen en el rango mas bajo. Falta la ficha en Atlas y el lector en bb que lleve esa declaracion al arbitro.
- **La accion** (ceder, congelar o detener a la elegida) depende de `FEATURE-ESCALERA-CEDER-CONGELAR-DETENER-VERIFICADA-01`. Hoy la accion sigue siendo `systemctl --user stop`, sin cambios.
- Las pruebas son puras con fixtures; no se corrieron bajo `bb cap` ni scope transitorio (paso 3 de "Para cerrar"), porque esta ficha no ejecuta ninguna accion.
- El interruptor `memavail` sigue en el modo en que estaba (no se toco). Si esta en `actuar`, el orden nuevo rige desde el despliegue: con `ELEGIBLES` por defecto, un `bb-lab-*` se detiene antes que una `bb-portero-suite-*` aunque tenga menos memoria.
- Medido en `e2e.txt`: 58 de 69 unidades reales no tienen clase. Con `ELEGIBLES` por defecto no importa; si alguien ampliara `ELEGIBLES`, antes hay que declarar su rango.
