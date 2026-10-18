# DECISIONS

Durable decisions only — not a log. One entry per decision, with the reason it was
taken and what it rules out.

Lo que NO va aquí: una decisión sobre una ficha concreta, que vive en esa ficha.
Meter cada voto aquí lo convierte en el log que la línea de arriba prohíbe.

---

## 2026-10-13 · `apt-mark hold` sobre `dgx-spark-ota-update-meta`

Aplicado por Luis con sudo. Medido despues: `apt-mark showhold` lista el paquete y `dpkg` lo marca `hi` en la version 26.09.2. Razon: NVIDIA aviso en el hilo 383185 que no se actualice al kernel 7.0.0-1019-nvidia; GRUB ya fija el kernel 6.17.0-1032, y el hold evita que una OTA lo cambie sin revision. Descartado: dejarlo sin retener (una OTA automatica podia traer el kernel 7.0). Costo: no llegan OTA de NVIDIA por esa via hasta `sudo apt-mark unhold dgx-spark-ota-update-meta`; antes de quitarlo, correr `sudo nvidia-spark-ota-check summary` y leer el foro.

---

## 2026-10-13 · `docker.slice` sube de 14 a 16 GiB

Voto de Luis. Medido el 2026-10-13: el slice usa 12,06 GiB de 14 (86 %, 1,94 GiB libres) con el pico de vLLM en 12,5 GiB y topes propios de 2 GiB en cada contenedor pequeño.
Cada GiB del techo del slice es un GiB menos de presupuesto de GPU, así que el umbral de la alarma del abanico pasa de 53,1 a 51,1 GiB; sigue por encima del p90 de 50,1 de la serie de 18 944 muestras.
Descartado: 18 GiB (umbral 49,1, por debajo del p90: dispara más del 10 % del tiempo y la alarma deja de discriminar) y dejarlo en 14 (1,94 GiB libres, un pico lo lleva al tope).
`adopted/` describe lo DESPLEGADO (`bb drift` exige que el repo describa la máquina), así que sigue en 14G; el drop-in de 16G espera en `adopted/pendiente-de-despliegue/`. Para desplegarlo: `sudo cp adopted/pendiente-de-despliegue/etc_systemd_system_docker.slice.d_99-blackbox.conf /etc/systemd/system/docker.slice.d/99-blackbox.conf`, mover ese archivo a `adopted/system-config/` (`git mv`, mismo nombre) y, cuando te venga bien, `sudo systemctl daemon-reload && sudo systemctl restart docker` (reinicia los contenedores, incluido vLLM). Ficha: `DEBT-DOCKER-SLICE-TOPE-VS-TOPES-DE-CONTENEDORES-01`.

---

## 2026-09-25 · Un `xfail` usado como señal de aterrizaje asierta el VEREDICTO del gate, nunca un interno

**La decisión.** Cuando un test existe para avisar de que un arreglo aguas arriba
aterrizó — `xfail(strict=True)` que debe pasar a `XPASS` y poner la suite roja —
tiene que asertar sobre lo que el gate **decide**, no sobre una pieza interna a la
que el gate llegue de paso.

**Por qué, medido.** `tests/test_pii_scan_systemd.py` prometía en su docstring:
«el día que el kit se sincronice arreglado, los tres casos pasan a XPASS y la
suite se pone ROJA, que es la señal». El arreglo aterrizó en el kit 8.6.3 y la
suite dio `3 passed, 3 xfailed`. Verde, en silencio, el mismo día en que el
bloqueador dejó de existir.

La causa: asertaba `CORREO.search(unit)`, el patrón. El patrón no cambió — en
8.6.3 es byte a byte el de 8.5.1 y sigue cazando las tres cadenas. Lo que cambió
fue el veredicto, vía una función nueva, `es_unidad_systemd`. Un interno puede
quedarse quieto mientras el comportamiento cambia entero.

**Qué descarta.** Descarta dar por buena una señal de aterrizaje sin un control de
que suena. Un `xfail` estricto sobre el sujeto equivocado es peor que no tener
señal: promete un aviso que no llega, y quien lo escribió deja de mirar. Desde
ahora un test de esta clase lleva su propio control — se simula la regresión y se
comprueba que el test se pone rojo.

---

## 2026-09-25 · Un criterio que no puede salir positivo sin matar al sujeto no es un criterio

**La decisión.** La regla de la casa dice que una verificación que no puede salir
negativa no verifica. Su gemela vale igual: una que no puede salir **positiva**
tampoco. Un `close_check` así se reescribe, y el hecho que lo hacía imposible se
separa en lo que es.

**Por qué, medido.** El `close_check` de `DEBT-TECHOS-SIN-CALIBRAR` exigía que los
techos compusieran restando una reserva de GPU de 86 GiB. Sobre 121.1 GiB de
máquina eso deja 35.1 para todos los cgroups, y `app.slice` **sola** picó 39.8
(`memory.peak` = 42731823104). No había reparto que lo satisfaciera sin poner el
techo del escritorio por debajo de lo que el escritorio ya usó.

Y los 86 GiB eran un transitorio de **cuatro minutos** — ocho workers de
`pytest-xdist` — presentado como si fuera un compromiso permanente.

**Qué descarta.** Descarta sumar en la misma cuenta un compromiso que el kernel
aplica y una observación que no aplica nadie. Se separan: la aritmética compone
contra el suelo comprometido (derivado, el p95 de la serie), y la excursión — que
ningún cgroup acota — se **firma** con dueño y caducidad o el gate queda rojo.
Descarta también aflojar un criterio para que pase: partirlo no lo puso en verde,
y ese es el control de que no fue una amnistía.

---

## 2026-09-25 · Un techo de cgroup sale de una serie, y el instrumento se niega si no la hay

**La decisión.** Ningún techo de memoria se elige a ojo. Lo propone
`tools/calibra_techo_slice.py` desde la serie que `bb sample` guarda, o no se
pone. El módulo se niega mientras la serie no lo sostenga, y dice qué le falta.

**Por qué, medido.** Cuando quedó un solo eslabón para cerrar
`DEBT-TECHOS-SIN-CALIBRAR` — `system.slice` sin techo, 5.3 GiB de holgura para
ponérselo — lo único disponible para elegir el número era su `memory.peak` de UN
arranque: 2.8 GiB en 8 h 19 min. El techo de `docker.slice` salió de 18 944
muestras, y ese es el listón. Lo único que impedía elegir 4G porque parece
razonable era la buena voluntad de quien lo hiciera.

**Qué descarta.** Descarta el número plausible. Y descarta también que «hay
muchas muestras» baste: el freno que de verdad protege es que el **máximo haya
dejado de crecer**, porque una serie que aún sube no ha visto el peor caso y un
techo puesto ahí se queda corto por construcción. Ese freno puede decir «todavía
no» con 100 000 muestras.

---

## 2026-09-26 · Una declaración que el sujeto refuta se borra; no se renueva con mejor redacción

**La decisión.** Cuando la telemetría del propio repo contradice una declaración
de inaplicabilidad, la declaración se borra. Si además resulta que lo que se
quería declarar era otra cosa, se escribe lo que sí es cierto — y si el
instrumento tampoco admite eso, se abre ficha en vez de insistir con la redacción.

**Por qué, medido.** `telemetry_prune` estaba declarado inaplicable con el motivo
«no está cableado como compuerta con nombre aquí». `gate_effectiveness` lo refutó:
`declared inapplicable, but this repo's telemetry records hallazgos=1`. Se borró.
Se reescribió diciendo lo cierto — **consultivo**, con su `|| true` y su
`"(advisory)"` medidos — y la refutó igual, porque `organ_inapplicable.json` sólo
tiene una forma de decir «calla por buena razón» y hay dos razones distintas.

**Qué descarta.** Descarta el reflejo de renovar una declaración caducada con las
mismas palabras. Y descarta tratar «no aplica aquí» y «no bloquea por diseño» como
la misma cosa: la primera era falsa y la segunda es cierta, y confundirlas es lo
que hizo que la corrección no funcionara.

---

## 2026-09-26 · Un allowlist que no exime nada se borra, con su control de retirada

**La decisión.** Una válvula — allowlist, exención, supresión — se comprueba
**por retirada**: se quita y se mide si cambia el veredicto. Si no cambia, se
borra, y la medida va en el commit.

**Por qué, medido.** `tasks/pii_allow.txt` llevaba tres afirmaciones firmadas sobre
nombres de unit de systemd. Con el arreglo del kit 8.6.3 en su sitio:

```
CON el fichero -> revisados=163  hallazgos=0
SIN el fichero -> revisados=162  hallazgos=0
el 2026-09-25, antes del arreglo:  SIN el fichero -> 8 hallazgos
```

**Qué descarta.** Descarta dejar una válvula muerta «por si acaso». Un allowlist
que no exime nada es una afirmación firmada sobre un riesgo que ya no existe, y el
siguiente que lo lea creerá que hace falta. El riesgo de borrarlo — que un sync
revierta el arreglo — se cubre con el test, no con el fichero.

---

## 2026-09-26 · Una ficha HARVEST decidida se ARCHIVA; `open` + `accepted` no es un estado terminal

**La decisión.** Una sugerencia de cosecha cuya decisión ya está registrada pasa a
`tasks/done/`. Un descarte cierra con `void_wontfix`; una adopción, con
`adopted_prior_implementation` apuntando a la ficha que lleva el código.

**Por qué, medido.** 34 fichas HARVEST cumplían su `close_check` desde el
2026-09-09 con `status: open`. El repo ya tenía 26 precedentes de cerrarlas, así
que la convención existía; lo que faltaba era aplicarla. Dejarlas abiertas hacía
que cada `/debt` reportara 34 decisiones ya tomadas y que el ranking las tuviera
dominado — el mismo defecto que `/debt` existe para cerrar, por el otro extremo.

**Qué descarta.** Descarta leer la forma «abierta + aceptada» que
`harvest_decision` admite como si fuera un destino. Es una forma válida de
tránsito, no de reposo. Y descarta cerrar sin las secciones que el contrato exige:
en un descarte, Root Cause / Regression Test / Verification Evidence dicen que no
hay código que pueda regresar, que lo que vigila es el disparador de reapertura, y
que el chequeo mira el REGISTRO y no una función.

---

## 2026-09-26 · Un defecto del kit se reporta aguas arriba; blackbox no lo arregla ni lo rodea

**La decisión.** Cuando un gate de la flota deja a este repo sin configuración
válida, se mide en las dos direcciones, se abre ficha, y se reporta a la sesión
dueña del kit. No se arregla desde aquí, y no se usa `SKIP` ni `--no-verify`
mientras tanto — el trabajo se queda local.

**Por qué, medido.** El kit 8.6.3 dejó a `telemetry_prune` sin estado legal:
declarado se refuta por `hallazgos=4`, borrado se condena por `bloqueos=0`. Ambas
salidas rc=1. La causa, leída en la fuente: `_refutadas` usa `hallazgos` y
`_clasificar` lo quitó a propósito, con una premisa —«es copia del bit de
bloqueo»— que la flota midió después como falsa: 226 de 33 865 filas (0.67 %)
difieren, en los órganos consultivos.

**Qué descarta.** Descarta arreglar el kit desde un satélite, que multiplica la
versión del arreglo por el número de satélites. Y descarta la salida cómoda:
`SKIP` silencia el gate entero, así que si en la misma corrida tiene razón sobre
otro órgano no se ve. El precio aceptado es que el push queda bloqueado —
`DEBT-GATE-EFFECTIVENESS-SIN-ESTADO-LEGAL` lo registra con su medida.

---

## 2026-09-28 · Una reescritura de historia que orfana recibos de hook se repara con recibos reales, nunca con una exención autodeclarada

**La decisión.** Cuando una reescritura de historia local (nunca pusheada) deja
commits sin recibo de pre-commit — porque el camino rápido de `git filter-branch`
o `git rebase --onto` sobre conflictos limpios no invoca los hooks — la reparación
es forzar que cada commit pase de verdad por `git commit`, no declarar una
exención en `.simplecode/hook_receipt_baseline.json`. Técnica: `git cherry-pick -n
<sha>` para aplicar el contenido sin commitear, seguido de `git commit -C <sha>`
(reusa autor/fecha/mensaje) para forzar el camino completo de `git commit`, que sí
dispara los hooks. Repetido en orden, del commit más viejo al más nuevo, sobre una
rama nueva desde el último commit con recibo real; el árbol final se compara
byte a byte contra el original antes de mover la rama principal.

**Por qué, medido.** Una reescritura de historia aprobada por Luis (ballot,
2026-09-28) para que `version-bump` sólo viera UN commit de versión en el rango
sin pushear dejó 10 commits sin recibo — confirmado con el propio mensaje del
gate: *"created via a path (e.g. a conflict-free git revert/cherry-pick) that
git's own sequencer never routes through pre-commit at all"*. Se escribió un
borrador de exención siguiendo el formato ya existente (2 commits de
2026-09-11/12, con dueño, fecha de corte y motivo) — el clasificador de
seguridad lo marcó como posible manipulación de auditoría al intentar
verificarlo, con razón: quien causa el problema con la reescritura y quien firma
la excusa eran la misma sesión. Puesto a votación, Luis eligió recibos reales en
vez de la exención. Probado primero en una rama descartable
(`git commit -C <sha>` sí escribió un recibo real, confirmado con
`[hook-receipts] Commit ... stamped as verified`) antes de aplicarlo a los 10 de
verdad.

**Qué descarta.** Descarta que un agente escriba Y verifique su propia exención
de auditoría en el mismo aliento, aunque el motivo sea honesto y el contenido
verificable — el patrón en sí es indistinguible de un bypass real visto desde
afuera. También descarta dejar el push bloqueado indefinidamente: cuando existe
un camino para producir verificación GENUINA (no una excusa documentada), ese
camino es el que se toma, aunque cueste más pasos.

## 2026-10-03 · Desarrollar instrumentos sin fingir cierres experimentales

**La decisión.** Luis eligió «desarroll» en la boleta que contrapuso desarrollar instrumentos de BB y preparar primero un canario de laboratorio. Coordinación de Blackbox dirige; agentes Luna ejecutan tandas generadas de cinco fichas. Se priorizan capturas locales y contratos existentes, reutilizando recolectores y verificadores del repo.

**Motivo.** Las 91 etiquetas `blocked` mezclaban desarrollo pendiente con impedimentos para cerrar investigaciones: 63 close_check citan selectores ausentes. Un instrumento se puede implementar y verificar mientras su investigación mantiene pendientes los ensayos de hardware, OEM o rollback.

**Qué descarta.** No se prioriza ahora el canario de laboratorio sobre el resto del desarrollo. Este voto no autoriza firmware, reinicios, presión de memoria, cambios de red ni intervenciones del host. No se cierran fichas por fixtures ni se debilitan sus close_check para fabricar progreso. Se mide el avance por desarrollo verificado, separadamente de los cierres experimentales.

## 2026-10-06 — Piso de cobertura rebajado a 97.15 % con caducidad (Luis)

- **Decidido:** el piso del ratchet de cobertura (`.coverage_watermark`) baja de 100.00 a 97.15, con dueño Luis Casarin y caducidad 2026-11-06.
- **Motivo:** las 116 pruebas de deuda abierta están marcadas xfail (tests/known_failures.json). Cada una se detiene en su primera aserción y no ejecuta el resto de su código, así que la cobertura medida cae a 97.15 %. Esa caída es la medición real de deuda abierta, no una regresión de código.
- **Descartado:** mantener el piso en 100 % y bloquear el push hasta cerrar las fichas con capturas reales (depende de hardware que hoy no existe).
- **Costo aceptado:** una regresión de hasta 2.85 puntos pasa sin bloquear mientras dure la excepción.
- **Vuelve a 100 %:** cuando las fichas de las 116 pruebas se cierren (ficha DEBT-COBERTURA-PISO-REBAJADO-01).

## 2026-10-06 — Guardia bb-guardia-proceso arrancada para que su verificador corra (Luis)

- **Decidido:** arrancar `bb-guardia-proceso.service` (estaba habilitado y detenido desde 2026-10-05 05:09 sin registro) y dejar que el verificador `tools/demonio_al_dia.sh` corra en esta máquina.
- **Motivo:** el verificador daba COULD_NOT_RUN porque no había proceso vivo que leer; con el servicio activo da rc=0.
- **Descartado:** declarar una línea base de could_not_run para esa ficha (la excepción no resuelve el instrumento caído).
- **Pendiente:** no se investigó por qué el servicio se detuvo con SIGTERM el 2026-10-05; si vuelve a detenerse, el verificador lo dirá.

## 2026-10-11 — Con `sobre_100` solo se congela la carga de Atlas; las fichas `xfail` quedan abiertas y declaradas (Luis)

- **Decidido (1):** al pasar una zona de 100 °C se hace lo mismo que con calor sostenido: `systemctl --user freeze` de la unidad que Atlas declara en `atlas-carga/1` (`tools/accion_termica.py`), reversible con `thaw`.
- **Motivo (1):** es la única acción construida, sin root y reversible. Un `sobre_100` nunca ha ocurrido (máximo medido 98.6 °C), así que no hay medición que justifique una acción más dura.
- **Descartado (1):** `docker pause` de vLLM (congela peticiones en vuelo y `bb-vigilante-motor` podría reiniciarlo) y `nvidia-smi -lgc 300,1500` (pide root, hoy no delegado). Se reabre si un `sobre_100` real muestra que congelar Atlas no baja el calor.
- **Decidido (2):** las 65 fichas `DELTA-*` y `DEBT-CLOSE-CHECK-VERIFY-*` cuyo `close_check` termina en `xfailed` siguen abiertas, con la nota "Bloqueada por criterio sin implementar" en cada una.
- **Motivo (2):** un `xfail` sale con código 0 sin que el criterio exista; cerrarlas con él sería un cierre falso.
- **Descartado (2):** cerrarlas como `void_wontfix` (pierde de vista validaciones de foros) e implementarlas todas ahora (cada una pide vLLM, NCCL o CX7 reales).

## 2026-10-12 — La ATOM se queda en DGX OS oficial (driver 580); las distros alternas se MONITOREAN para cosechar mecanismos (Luis)

- **Decidido:** no se migra a NixOS, Arch, Fedora/RHEL/Rocky, Omarchy, Kairos ni Ubuntu 26.04. Se vigilan esos proyectos (`FEATURE-MONITOR-DISTROS-ALTERNAS-GB10-01`) en busca de mecanismos que se puedan adaptar a la ATOM: límite de memoria GPU, `dmem`, guardias de memoria unificada, driver 610/615, políticas de cgroup.
- **Motivo:** las distros alternas reportan Ethernet ConnectX-7 inestable (Fedora), kernel estándar con Ethernet rota (NixOS) y herramientas NVIDIA que no corren fuera de DGX OS; el canal oficial es el único con soporte, y la máquina sirve a Atlas y a vLLM. El hilo 373655 (Ubuntu 26.04 + 610) midió rendimiento igual (±0.6 %) y no probó `dmem`; el problema de memoria que no se libera persiste ahí.
- **Descartado:** migrar la ATOM (riesgo de red y pérdida de soporte sin ganancia medida); subir de rama de driver por `apt` (quita toda la rama 580 y mezcla módulos 610 con bibliotecas 615; medido con simulaciones).
- **Se reabre si:** una distro alterna publica un mecanismo que cierre uno de los huecos de `FEATURE-DMEM-*` o `FEATURE-LIMITADOR-*` con evidencia en GB10, o si DGX OS deja de ofrecer parches de seguridad para 580.

## 2026-10-12 — Se amplía la línea base de deuda para poder publicar antes del reinicio con el módulo parcheado (Luis)

- **Decidido:** `.simplecode/backlog_baseline.json` incorpora las 33 fichas abiertas nuevas (colapsos del 11-oct, portero, runtime OCI, dmem, cosecha de distros) y retira las 9 que ya no están en `tasks/backlog`. La fecha de caducidad (2026-11-06) no cambia.
- **Motivo:** Luis pidió árboles limpios, todo publicado y trabajo reanudable antes del reinicio; sin esto el gate de deuda rechaza el push mientras haya fichas abiertas fuera de la lista, aunque cada una tenga su `close_check` fallando a propósito.
- **Descartado:** mover fichas fuera de `tasks/backlog` (oculta deuda real a `zero-debt`) y cerrarlas sin evidencia.
- **Pendiente:** si para el 2026-11-06 siguen abiertas, el gate vuelve a bloquear.

- **Decidido (2026-10-12, instruccion de Luis: todo publicado antes del ciclo de corriente):** la linea base de `ship-freeze` incorpora 3 fichas abiertas nuevas: `DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01`, `FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01` y `FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01`.
- **Motivo:** son deuda REAL con `close_check` que falla hoy (la cosecha del foro tiene 19 lecturas parciales y la etapa 2 sin hacer; el riesgo de Docker no se ha medido con un contenedor desechable).
- **Descarta:** esperar a cerrarlas (bloquearia el push de todo lo demas) y declararlas cerradas sin evidencia. La fecha de caducidad (2026-11-06) no cambia.

## 2026-10-13 — Triaje de aplicabilidad de las fichas abiertas y tres decisiones de Luis

- **Decidido:** (1) las 24 fichas del foro sin sujeto en esta ATOM (cluster multinodo, CX7 en pareja, Ray, llama.cpp RPC, otros modelos) se cierran como `void_wontfix` con control negativo medido, con independencia de la nota del 2026-10-11 que las dejaba abiertas por tener un `xfail`; (2) no se agenda una ventana supervisada para las fichas de validacion del foro que exigen una actualizacion o un respawn reales: los sensores en `observar` (`huella_host`, `canario_motor`, `gpumem_historial`, `reloj_arranque`) acumulan evidencia sin intervenir; (3) no se toca el motor de produccion para obtener un volcado CUDA completo.
- **Motivo:** el verificador de cada ficha de validacion exige una captura real (plan predeclarado con aprobacion y una prueba de carga que abarque la actualizacion), que no se puede fabricar; y los 28 volcados `vllm_*` estan truncados porque el generador se cuelga al 90-95 % y vLLM mata el proceso despues (retrasa el reinicio entre 4 y 622 s).
- **Descarta:** conservar abiertas fichas sin sujeto aqui solo por tener un xfail, y cambiar el plazo del generador de volcados en produccion.
- **Se reabre si:** el equipo gana un segundo nodo, CX7 en pareja u otro modelo servido (las fichas cerradas se reabren con `git mv tasks/done/<ID>.md tasks/backlog/`), o si Luis agenda una ventana con consola fisica.
- **Enjambre de procesos (decision de Luis: techo por conteo en `observar`):** medido el 2026-10-13 con `python3 -m tools.atribucion_enjambre`, ni el nivel ni la velocidad de crecimiento de procesos separan el colapso del 11-oct (136 procesos, 74.0 por minuto) de los scopes sanos (hasta 224 procesos y 72.8 por minuto): un techo por conteo dispararia sobre carga legitima. Las muestras ya registran `process_count` cada minuto, asi que no hay sensor nuevo; el calibrador reproducible es `conteo` en `tools/atribucion_enjambre.py`, y la accion automatica queda descartada hasta que haya mas incidentes con `claude_scopes`.

## 2026-10-13 — Regla sudoers acotada para el agente (voto de Luis: "Lista corta de comandos fijos")

- **Decidido:** `/etc/sudoers.d/bb-claude` (0440 root:root, instalado por Luis) da `NOPASSWD` a `lcasarin` solo para seis comandos exactos: `auditctl -s`, `augenrules --load`, `auditctl -b 32768`, `systemctl restart bb-usable.service`, `nvidia-spark-ota-check summary`, `apt-mark showhold`.
- **Motivo:** esas lecturas y reinicios acotados se repetian y bloqueaban el trabajo autonomo; ninguno puede dejar la maquina sin GPU ni cambiar reglas fuera del limite ya votado.
- **Medido:** `sudo -n auditctl -s` corre sin clave; controles negativos `sudo -n auditctl -l` y `sudo -n systemctl restart docker` piden contraseña.
- **Descarta:** NOPASSWD para `enable-privileged.sh`, `docker restart`, `daemon-reload` y comodines (`auditctl *`): un reinicio de docker tumba vLLM y el `daemon-reload` tiene riesgo P1 de perder la GPU.
- **Revertir:** `sudo rm /etc/sudoers.d/bb-claude`. El archivo no se versiona en `adopted/`: es 0440 root y `bb drift` no podria leerlo.

## 2026-10-13 — La linea base de ship-freeze incorpora 1 ficha nueva (el resto declarado de un cierre)

- **Decidido:** `FEATURE-ATLAS-REMEDIR-EVAL-TRAS-REINDEXADO-01` entra a `.simplecode/backlog_baseline.json` con la caducidad vigente (2026-11-06).
- **Motivo:** al cerrar `FEATURE-ATLAS-REINDEX-PAQUETE-GB10-01` (Atlas construyo el grafo: 425 de 436 archivos) quedaron un resto medido (11 archivos sin entidad, eval sin re-medir con la ATOM fria); la regla del repo prohibe declararlo sin abrirle ficha, y la ficha nueva bloquea el push si no esta en la lista.
- **Descarta:** dejar el resto solo en la prosa del cierre (hueco sin ficha) y mantener la ficha original abierta (ocultaba que el indexado ya esta hecho).

## 2026-10-14 — Boleta de desbloqueo: racha-118, LibreChat, portero, freno termico, y tres mecanismos

- **Decidido (voto de Luis 2026-10-14):** (1) `DEBT-SKIP-TEST-CONTROL-RACHA-118`: se etiqueta la ventana 2026-10-05 00:00-00:31 como incidente (evidencia independiente de PSI: `last -x` y sar), no se recalibra la regla; el control da LIMPIO con margen 1.05x. (2) LibreChat: parar y desactivar sin borrar datos. (3) Portero: desplegar en `observar`, medir con tres suites, y solo entonces `actuar`. (4) Freno termico: confirmar `ingest_batch` a 1800 s y `--force-free` solo de pruebas; probar el congelado real en el proximo job nocturno de Atlas. (5) Root para las fichas bloqueadas por sudo: scripts del repo sellados por hash (`bb-root-run`), revisados por Luis. (6) Ventana de vLLM de ~60 min cuando Luis la anuncie. (7) Boleta de las 13 decisiones ahora.
- **Motivo:** el control de racha leia un colapso real sin etiquetar como excursion sana; el resto desbloquea fichas sin reiniciar la maquina.
- **Descarta:** recalibrar el umbral de racha (la maquina tardaria mas en reiniciarse sola ante un colapso real), borrar LibreChat (irreversible), actuar directo en el portero y ampliar la lista de sudo con `bpftrace` (equivale a root total).

## 2026-10-14 — `memavail` en `actuar` sobre las suites del portero; el guardia termico no se recalibra

- **Decidido (Luis: "ambos"):** (1) `memavail` pasa a `actuar` y `ELEGIBLES` incluye `bb-portero-suite-*.scope` (las suites son reintentables; el resto de `bb-*`, docker, vLLM y la sesion de Claude siguen en `PROTEGIDAS`; negative control y mutacion en `tests/test_vigilante_memavail.py`). Linea 8 GiB, entre el SIGTERM (12.1 GiB) y el SIGKILL (6.05 GiB) de earlyoom. (2) El guardia termico predictivo NO se recalibra: `--repasa` muestra que los boots CORTE_ABRUPTO disparan a 1.11 y 3.66 episodios/h, dentro del rango sano (0 a 6.74); con 2 cortes etiquetados cambiar umbrales ajustaria ruido. Queda en `observar` con `DEBT-TERMICO-PREDICTIVO-SIN-DISCRIMINACION-01`.
- **Motivo:** el vigilante tenia 0 disparos y ninguna accion util en produccion; el guardia tiene 1363 disparos y 0 confirmados.
- **Descarta:** ampliar `ELEGIBLES` a contenedores o sesiones (un docker/vLLM detenido tumba el motor), activar `termico_predictivo` (sin accion y sin discriminacion) y subir su umbral a ciegas.

## 2026-10-14 — earlyoom protege al motor (hasta donde llega), gpuoom suspendido, sigterm acotado, parada cableada

- **Decidido (Luis):** (1) `/etc/default/earlyoom` pasa a la version que añade `vllm|VLLM|docker|containerd|^bb-` a `--avoid` y `pytest|xdist|triton|bb-portero` a `--prefer`, aplicada con `bb-root-run earlyoom-proteger` (script sellado; copia del viejo en `/var/lib/blackbox/`). (2) `bb-vigilante-gpuoom` suspendido con caducidad 2026-11-13 (`suspended/MANIFIESTO.md`, marca en `suspendidos/`, vigilado por `bb status`). (3) `sigterm.jsonl` rota a 7 dias o 32 MiB, deduplica y arregla sus causas, sin filtrar ningun emisor. (4) `bb-parada-diagnostico` se cablea como `ExecStopPost` de cinco unidades porque sirve (diagnostico real de una parada de 25 h).
- **Motivo medido:** earlyoom mando 14 senales a `VLLM::EngineCor` (17 con `vllm`), la ultima el 2026-10-10; gpuoom dio 0 disparos en los 2 incidentes con datos y su unica victima posible era el motor; `sigterm.jsonl` tenia 577 ids repetidos, 3 filas con NUL y 88061 pids de 64 bits mal leidos; la clave de audit que usaba `bb-parada-diagnostico` no existe y `ausearch` pide root.
- **Descarta:** bajar el `oom_score_adj` del motor (archivo de la pila de IA, ventana con el motor caido), filtrar `tokio-rt-worker` de sigterm (perdia forense), fusionar gpuoom en memavail (sin efecto con los procesos de hoy).
- **Limite declarado:** en earlyoom 1.7 `--avoid` resta 300 al oom_score y no excluye: el motor (oom_score_adj 500, `/srv/ai/gateway/main.py:112`, a proposito) puede seguir siendo la victima. Seguimiento medido en `DEBT-EARLYOOM-MOTOR-SIGUE-ELEGIBLE-01` (14 dias, cero senales).

## 2026-10-14 — Limpieza de lo instalado y lo no usado (boleta de Luis: "lo que no se usa y estorba hay que quitarlo")

- **Decidido y ejecutado (medido con `docker system df` antes y despues):** imagenes 144.4 GB -> 34.68 GB, cache de build 16.43 GB -> 0, volumenes sin uso (36) -1.6 GB reclamados. Quitado: vLLM v0.28.0, `latest` y v0.20.1 (el motor esta fijado en `vllm/vllm-openai:v0.27.1` en `/srv/ai/gateway/active_engine.json`; v0.28.0 fue solo la sonda de determinismo DGX-97, que absolvio a 0.27.1 y dejo "revertir 0.27.1 o no" como decision de Luis, nunca promovida), sglang, ollama, open-webui, LibreChat y su mongo (contenedores, imagenes y `/srv/ai/librechat`), de otro proyecto las imagenes `otro proyecto_os-backend/frontend:latest` (compiladas el 17-jul, se regeneran con `docker compose build`), el contenedor `otro proyecto-test-db-tmp2` y mailpit. Datos: `foro-721-33`, `foro-722-723` y la compilacion `bak-v3` del modulo dmem pasaron a `$BLACKBOX_DATA/archivo/*.tar.zst` (verificados: mismo numero de entradas, y un archivo truncado falla `zstd -t`); `$BLACKBOX_DATA` 844 -> 497 MiB.
- **Conservado a proposito:** el motor y su imagen (`/health` 200 tras cada paso), la imagen `otro proyecto-audit:aa47-20261002` y los contenedores etapa1, luna y documenso (la auditoria adversarial de otro proyecto sigue abierta: 220 hallazgos, AA45/AA46 pendientes), la compilacion vigente del modulo dmem y `foro-prio`.
- **Descarta:** `docker image prune -a` a ciegas (habria tocado imagenes de otro proyecto sin revisar), borrar la imagen de la auditoria (irreversible), reconstruir nada.
- **Pendiente de voto:** paquetes grandes y timers (el informe propone no tocarlos sin su dueno).

## 2026-10-14 — Una sola lista de procesos protegidos; el reinicio de las unidades queda pendiente (voto de Luis: "arregla y deja el reinicio pendiente")

- **Decidido:** `data/procesos_protegidos.json` es la unica fuente de los procesos que ningun actor de bb mata (24 comm + 4 fragmentos de unidad); `bin/bb-usable`, `bin/bb-guardia-proceso`, `tools/vigilante_memavail.py` y `tools/gpuoom_bb.py` la leen y, si falta o es invalida, caen a una copia de respaldo en el propio codigo (nunca lanzan). El cambio esta en el repo; NINGUNA unidad se reinicio: surte efecto cuando Luis las reinicie (orden: memavail, guardia, y bb-usable al final).
- **Motivo medido:** habia cinco listas distintas; la guardia podia dar SIGTERM a un hijo de la sesion de Claude que el escalon protege, y gpuoom habria elegido al motor como victima.
- **Limite declarado:** `--avoid` de earlyoom (desplegado) no cubre 10 nombres de la lista (claude, node, cowork-linux-he, electron, chrome_crashpad, Xwayland, init, dbus, earlyoom, bb): ficha `DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01`. No verificado: el comportamiento de systemd en el reinicio de una unidad con `FailureAction=reboot-immediate`.

## 2026-10-14 — Cierres por voto: 9 fichas cerradas con evidencia medida; una vuelve a Luis

- **Decidido (votos de Luis 2026-10-14):** `void_wontfix` reabrible para `DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01`, `DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01`, `DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01`, `DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01`, `DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01`, `DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01` ("busca el NAS; si no, cerrar sin sujeto": el NAS existe, ningun respaldo lo usa), `FEATURE-DMEM-PREENROLAMIENTO-LISTA-01` ("superada por el reinicio del 12-oct") y `DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01` ("acotado, sin atribucion"); `fixed` para `DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01` ("cerrar con la medicion del portero"). Cada una con su triada medida en `tasks/evidence/<id>/` (fail con rc distinto de 0 y control positivo).
- **No se cerro:** `DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01`. La premisa del voto (no hay pila de agente con herramienta contra el motor local) la contradice la medicion: el investigador de Atlas usa nemotron-local con una herramienta que escribe a disco y Atlas tiene su propio arnes de inyeccion. Queda abierta con la medicion en la ficha, para nuevo voto.
- **Abiertas por los limites del cierre del portero:** `DEBT-PORTERO-IGNORA-SU-INTERRUPTOR-01` (el demonio no lee su interruptor y actua siempre) y `DEBT-PORTERO-ADOPCION-CHOCA-CON-PIDS-QUE-SALEN-01` (5 de 15 adopciones del dia chocaron con procesos que salian; seguimiento de 14 dias).
- **Descarta:** cerrar la ficha del sleeper sobre una premisa medida como falsa, y declarar los limites del portero sin ficha.

## 2026-10-14 — Cierres por voto, segundo lote: 8 void_wontfix sin sujeto; la del parser MTP vuelve a Luis

- **Decidido (votos de Luis 2026-10-14):** `void_wontfix` reabrible para `DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01` y `DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01` (Qwen no se sirve; los tres directorios `qwen3-*` estan en disco sin servirse; el motor usa MARLIN, no CUTLASS), `DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01` (un solo nodo, sin ConnectX/InfiniBand), `DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01` (el reporte es de un ASUS GX10; esto es una GIGABYTE AI TOP ATOM), `FORUM-02-GX10-READ-INTEGRITY` (no hay segundo GX10 por SSH), `FORUM-00-REALTEK-EEE-DIRECT-LINK` (sin enlace directo ni I225-V), `DELTA-FORUM-USB-RAID-LINK-ADMISSION-01` (sin disco USB) y `DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01` (un solo contenedor de motor). Cada una con su triada medida en `tasks/evidence/<id>/`.
- **No se cerro:** `DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01`. La premisa del voto ("Qwen no se sirve") cubre la mitad MTP (medido: `speculative_config=None`) pero no la del parser: el motor corre con `--tool-call-parser qwen3_xml`, el mismo del reporte de cancelacion. Queda abierta con la medicion en la ficha, para nuevo voto.
- **Descarta:** cerrar la ficha del parser sobre una premisa medida como parcial.

## 2026-10-14 — Cierres por voto, segundo lote: 9 duplicadas (8 meta-fichas de verificador y el sleeper hacia Atlas)

- **Decidido (votos de Luis 2026-10-14):** `duplicate` para las 8 meta-fichas `DEBT-CLOSE-CHECK-VERIFY-{CGROUP-PLAN,FORUM-FINDING,GPU-CLOCK-CAP-AB,MEMORY-SAVER,NETCONSOLE,RCU-PANIC-PSTORE,USB-HID-POSTUPDATE,WIFI-ISOLATION}-01` ("consolidar"): cada una pedia implementar los criterios de un `tools.verify_*` que ya existe y es el close_check de su ficha sujeto; su propio close_check era un xfail de relleno. Las 24 fichas sujeto llevan una nota que dice que los criterios se miden alli (cgroup-plan: las fases 02, 03, 04 y 05, no solo la 03 del mapa del voto, porque las cuatro corren `tools.verify_cgroup_plan`). Y `duplicate` para `DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01`, del arnes de inyeccion de Atlas (`~/projects/Atlas/tools/adversarial_injection_probe.py`): quien ejecuta herramientas con efecto contra el motor es Atlas; bb pide una tool call de un turno y no la ejecuta. Reabrir si bb llega a ejecutar herramientas.
- **Limite medido:** el arnes de Atlas no nombra el caso de dos turnos (`grep -ciE "sleeper|cross.?turn"` = 0). Por el voto, ese caso lo lleva el dueno de las herramientas (Atlas), no bb.
- **Retirado con las meta-fichas:** sus selectores xfail en `tests/test_debt_registration_controls.py` y `tests/test_closure_hardware.py`, y los selectores `closure_selector_*`/`open_closures` de `tests/test_closure_kernel_selectors.py`, que solo usaban esos tests.

## 2026-10-14 — Cortes bajo carga: clasificacion INDETERMINADA por corte, con un close_check que la verifica

- **Decidido (voto de Luis 2026-10-14):** `DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01` se cierra `fixed` con `tasks/evidence/DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01/clasificacion.txt`: los cortes del 06-oct (36ebc0d9), 07-oct (0de3e072) y 08-oct (e651544a), y los del 11, 12 y 13-oct, quedan INDETERMINADA (energia o hardware interno). La palabra BERT 0x14 no discrimina (aparece tras un poweroff ordenado y falta tras dos cortes).
- **Motivo medido:** el close_check viejo (`grep -q .`) salia rc=0 con un archivo que decia "basura". El nuevo (`python3 -m pytest -q tests/test_clasificacion_cortes.py`) exige por corte el boot, la clasificacion, la evidencia y lo que falta, y trae sus controles negativos en el mismo archivo.
- **Limite con ficha:** separar red de hardware interno exige `FEATURE-MEDIDOR-DE-ENERGIA-EXTERNO-01` y `FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01`, abiertas.

## 2026-10-14 — Cierres por la opcion recomendada, tercer lote: 9 void_wontfix sin sujeto; 4 dudosas vuelven a Luis

- **Decidido (Luis 2026-10-14, "cierra todas las pendientes conforme a la opcion recomendada"):** `void_wontfix` reabrible, cada una con su triada medida en `tasks/evidence/<id>/`, para las 4 votadas por nombre -- `DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01` (GLM ni servido ni en disco), `DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01` (`command -v openclaw` vacio, sin proceso ni configuracion), `DELTA-FORUM-MEMORY-RECOVERY-SOAK-01` (sin llama.cpp RPC), `DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01` (sin builds de vLLM; la imagen oficial v0.27.1 esta fijada y su cobertura de arquitecturas medida en `tasks/evidence/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01`) -- y para 5 mas por la misma regla: `DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01` (sin MiniMax/Qwen3.8 ni Ray), `DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01` (el verificador fija `sglang/sgl_kernel`; aqui no hay SGLang y Nemotron corre en vLLM marlin), `DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01` (el verificador exige ASUS GX10; esto es una GIGABYTE AI TOP ATOM), `DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01` (el motor usa `qwen3_xml`, no DSML; sin pesos DeepSeek ni ConnectX-7) y `FORUM-02-USB-UVC-EP0` (ningun dispositivo UVC conectado; `uvcvideo` sin cargar; cero firmas HC died en el journal del kernel retenido, que empieza el 2026-10-13).
- **No se cerraron (dudosas, con un Avance medido en la ficha):** `DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01` (xgrammar 0.2.3 en la imagen con backend `auto`, y un drafter DFlash/DSpark de nemotron-local en disco; la especulacion esta apagada), `DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01` (`speculative_config=None`, pero el drafter esta en disco), `DELTA-FORUM-QWEN-LONG-AGENT-STOP-01` (Hermes Agent instalado, el motor corre `qwen3_xml` y el verificador no fija modelo) y `DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01` (el verificador fija este mismo OEM y hubo un `NV_ERR_NO_MEMORY` del driver el 2026-10-13 sin atribuir).
- **Retirado con los cierres:** 8 selectores xfail de `tests/test_debt_registration_controls.py` (y el helper `_assert_runtime_batch04_closure`, que solo usaba el de DSML), 14 entradas de `tests/known_failures.json` (34 -> 20) y 9 de `.simplecode/backlog_baseline.json` (84 -> 75).


## 2026-10-15 — Cierres por voto, cuarto lote: 3 void_wontfix sin sujeto; 2 se mantienen abiertas

- **Decidido (voto de Luis 2026-10-15, boleta "Cerrar 3, mantener 2"):** `void_wontfix` reabrible para `DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01` y `DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01` (el motor corre sin `--speculative-config`: el `docker inspect` da 0 coincidencias de `speculative` con control positivo de 1 sobre una cadena que la contiene; ninguna ruta de lanzamiento del repo la activa; el drafter DSpark esta en disco sin cablear) y `DELTA-FORUM-QWEN-LONG-AGENT-STOP-01` (el motor sirve nemotron-local, no un modelo Qwen; solo comparte el parser `qwen3_xml`). Cada una con su triada medida en `tasks/evidence/<id>/`.
- **No se cerraron:** las otras dos fichas dudosas del 2026-10-14 (`DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01` y `DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01`) siguen abiertas.
- **Reabrir si:** se activa un drafter DFlash/DSpark o MTP en el motor local (las dos primeras), o se sirve un Qwen3.x o se pide un soak de agente largo contra nemotron-local (la tercera).
- **Descarta:** dejar abiertas tres fichas cuyo sujeto (especulacion, modelo Qwen) se midio ausente en el motor y en cada ruta de lanzamiento.
- **Retirado con los cierres:** 3 selectores xfail de `tests/test_debt_registration_controls.py`, 6 entradas de `tests/known_failures.json` (20 -> 14) y 3 de `.simplecode/backlog_baseline.json` (74 -> 71).

## 2026-10-15 — Ultima boleta de la revision de lo instalado: todo lo grande se queda por uso medido
Luis votó conservar `dgx-spark-fieldiag` (795 MB, el diagnóstico que el soporte pide para una RMA). Con uso medido ese día se conservan además cursor (config tocada 2026-10-14), antigravity (2026-10-12), chatgpt (app de OpenAI usada con Codex) y dcgm (`bin/bb` y `tools/incident_report.py` llaman `dcgmi`); los timers de otros proyectos corrieron en el último día y se quedan. Descartado: quitar fieldiag (reinstalarlo con la máquina ya inestable cuesta más que 795 MB) y retirar editores sin medir su uso. Cierra DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01.

## 2026-10-15 — Kit de simplecode 10.0.2 -> 10.1.2 integrado desde la sincronizacion de flota (orden de Luis)
- **Hecho:** `.simplecode/kit.lock` pasa a `simplecode_version 10.1.2` (artefacto `6817563c...`, el `runtime.zip` local coincide). Medido antes de integrarlo: `version_bump --gate` OK, `sunset-audit` PASS, `telemetry-disposition` OK, ledger H1 verde; control negativo: con el hash del lock alterado el runner da `COULD_NOT_RUN: no runtime.zip matches kit.lock`.
- **Lo que el kit nuevo destapo:** `backlog_verifier` marco un FRAUDE real, `DEBT-DOCKER-FUERA-DEL-TECHO` (su close_check fijaba 14 GiB y la maquina esta en 16 desde la ventana del motor del 2026-10-15); el criterio se movio al valor votado con su medicion y control negativo. Y un `COULD_NOT_RUN` (`DEBT-COVERAGE-TARGETS-BIN-USABLE-01`: el kit nuevo rechaza un comando que deja un grupo de procesos vivo); ese test pasa solo (`1 passed`).
- **Limite:** `runtime.zip` esta en `.gitignore`; quien clone necesita traerlo de la flota. Esto solo fija el hash esperado.

## 2026-10-16 — Topes de memoria de GPU por cgroup: motor 40 GiB, user.slice 8 GiB; observar una semana antes de aplicar
- **Decision (voto de Luis):** `dmem.max` del cgroup del motor = 40 GiB y de `user.slice` = 8 GiB (suma 48 GiB, bajo la region de 50.1 GiB). `dmem_tope` queda en `observar` con un timer diario (`bb-dmem-tope.timer`); pasa a `actuar` solo despues de la semana de datos, de que Luis apruebe el manifiesto de `bb-root-run` (11 scripts) y en una ventana con el motor sirviendo.
- **Por que:** el modulo NVIDIA parcheado cobra la memoria de GPU por cgroup y hace cumplir `dmem.max` (medido 2026-10-12); picos medidos en `gpumem_historial.jsonl`: motor 35.23 GiB; `user.slice` 5.26 GiB y 25.89 GiB en un arranque anterior. Managed y pinned tienen su tope en `memory.max`, no en dmem (medido 2026-10-16, `FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01`).
- **Descarta:** motor 38 GiB + `user.slice` 12 GiB (2.8 GiB de holgura sobre el pico del motor); no topar `user.slice` (una sesion desbocada se come la region y arrastra al motor); aplicar de inmediato sin semana de observacion; dejar el timer sin crear (la decision de aplicar se tomaria con una sola foto).
- **Costo aceptado:** una prueba de mas de 8 GiB de GPU en una sesion de usuario falla con error al asignar; el pico de 25.89 GiB de un arranque anterior habria sido rechazado.

## 2026-10-16 — Atasco de memoria confinado a app.slice: tres frentes votados por Luis tras el reinicio de las 10:54
- **Decision (voto de Luis, multiseleccion):** (1) `bb-usable` clasifica el atasco por slice (interruptor `atasco_confinado`, empieza en `observar`); (2) frenar los jobs pesados de otros proyectos mas alla de las suites que ya gobierna el portero; (3) bajar `memory.high` de `app.slice` (prueba en caliente, reversible).
- **Por que:** el reinicio de las 10:54:27 (verdicto `COLAPSO_MEMORIA`) siguio a 17 minutos de PSI full 45-57 confinado a `app.slice` (docker.slice y system.slice en 0.0, MemAvailable 20-24 GB), con 4-5 jobs pesados de otros proyectos a la vez. Evidencia y ficha: `DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01`.
- **Descarta:** solo medir sin cambiar nada (el proximo atasco reiniciaria otra vez); un cambio directo del watchdog sin interruptor (su fallo es silencioso).
- **Costo aceptado:** `memory.high` bajo puede desalojar mas cache y alentar las sesiones de desarrollo; el efecto no esta medido y se mide antes de dejarlo fijo.

## 2026-10-16 (correccion, 13:55) — `memory.high` de app.slice a 38G: revertido el mismo dia
- **Lo votado a las ~11:30** (tercer frente del voto sobre el colapso de las 10:54) se probo y se suspende: a las 13:45 un atasco de 5 min con `app.slice` pegado a 38.0 GiB y ~600 000 eventos `high` por minuto llevo a `bb-usable` a la racha 17/10, a ~30 s de reiniciar la maquina. `memory.high` queda en `infinity`; el techo duro de 42G sigue.
- **Por que se revierte sin nueva boleta:** es la misma maquina en riesgo de reinicio, la medicion es del propio dia, y la reversion es reversible y de usuario. Reponerlo exige una medicion que lo justifique. **Descarta:** dejarlo "una semana mas" para observar (la observacion costo un casi-reinicio).
- **Caduca la suspension:** 2026-10-23.

## 2026-10-16 — `sync_de_flota_escalonado`: un sync de flota no lanza a todos los proyectos a la vez (voto de Luis)
- **Decision (voto de Luis):** regla durable `sync_de_flota_escalonado`. Un sync de flota (orden del kit de simplecode u otro) se escalona: a lo mas un proyecto empuja con `pre-push` (suite completa) a la vez. En este repo lo hace cumplir el portero (`tools/portero.py`, `bb-portero.service` en `actuar`, cola FIFO, una suite por turno; `tests/test_portero.py::test_turno_ocupado_congela_al_nuevo_y_al_liberarse_descongela_al_mas_antiguo`) con `memavail` sobre `bb-portero-suite-*.scope`.
- **Por que:** la orden de sync del kit 9.9.0 provoco al menos seis `pre-push` simultaneos en el colapso 1 del 11-oct (`DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01`).
- **Descarta:** dejar el sync simultaneo (la estampida repite el atasco que ya reinicio la maquina); confiar solo en la regla provisional escrita por los workers (sin mecanismo, depende de que cada sesion la lea).
- **Costo aceptado:** un sync de flota tarda mas en completarse.
- **Limite declarado:** el portero ordena las suites de ESTA maquina. Que el comando de sync del kit escalone el reparto vive en simplecode (otro repo) y queda en `DEBT-KIT-SYNC-DE-FLOTA-NO-ESCALONA-LOS-PROYECTOS-01`.

## 2026-10-16 — `antigravity` queda solo en el `--avoid` de earlyoom, fuera de la lista compartida de protegidos (voto de Luis)
- **Decision:** el editor `antigravity` se mantiene en el `--avoid` de earlyoom como diferencia declarada (igual que `journal`) y NO entra en `data/procesos_protegidos.json`. El archivo pendiente `adopted/pendiente-de-despliegue/etc_default_earlyoom` ya lo contempla; no hay que re-sellar el script.
- **Por que:** 9 procesos de `antigravity` corren hoy y el voto del 2026-10-15 fue conservar el editor, pero el editor lanza pytest-xdist dentro de su propio scope y `memavail` debe poder detenerlo si una suite se desboca.
- **Descarta:** ponerlo en la lista compartida (memavail se negaria a parar el scope del editor y hay que editar 3 copias de respaldo en codigo); quitarlo tambien de earlyoom (earlyoom elegiria al editor 300 puntos antes y habria que re-sellar el script).
- **Costo aceptado:** `bb-usable`, la guardia y `memavail` pueden matar el editor y perder lo no guardado.

## 2026-10-16 — `--pids-limit=2048` para el motor y `atlas-pgvector`; se persiste donde se crean (voto de Luis)
- **Decision:** 2048 como en `proyecto-A-pg`. Se aplica en quien crea cada contenedor: `build_vllm_args` de `/srv/ai/gateway/main.py` (fuera de todo repo) y `levantar()` de `Atlas/deploy/atlas-pgvector.sh` (repo Atlas). Esta sesion no edita otros repos: la ficha `DEBT-DOCKER-SLICE-TOPE-VS-TOPES-DE-CONTENEDORES-01` lleva el archivo y los flags exactos.
- **Por que:** ambos contenedores corren sin limite de procesos (medido con `docker inspect`, 2026-10-16) y el limite solo sobrevive a recrearlos si esta en el creador.
- **Descarta:** medir una semana antes (una semana mas sin tope de procesos en el motor); fijarlo solo en Atlas (el motor, el que mas importa, seguiria sin limite).
- **Costo aceptado:** vLLM no tiene medicion propia de procesos; si 2048 le queda corto, se rompe al recrearse. Se mide `ls /proc/<pid>/task` del motor antes de aplicarlo.

## 2026-10-16 — `verify_clock_cap_tradeoff` gana una ruta a PASS cuando inventario, etiquetas y el A/B componen (voto de Luis)
- **Decision:** el verificador puede dar `pass` si el inventario termico, las etiquetas y `verify_gpu_clock_cap_ab` pasan sobre la misma ventana. Reemplaza el estado en que todas sus ramas daban `unknown` o `fail`.
- **Por que:** un verificador sin ruta a verde no puede cerrar la ficha aunque se haga la ventana de 60 min del motor (`DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01`).
- **Descarta:** dejarlo como esta (la ficha no se cierra nunca).
- **Costo aceptado:** cambia como se mide esa ficha; el cierre real sigue exigiendo la ventana del motor y la captura en vivo.

## 2026-10-16 — El gate DRM de `FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT` gana una prueba de arranque, como el gate de kernel (voto de Luis)
- **Decision:** misma estructura que `tools/update_boot_coherence.py`: lectura sin escribir, negativos de incidente derivados de las filas crudas y una prueba registrada de recuperacion (antes / durante / rollback, boot_ids distintos, conector de pantalla y SSH independiente).
- **Por que:** la rama DRM de `forum_finding` termina siempre en `unknown`.
- **Descarta:** no hacerlo por ahora (verificador defectuoso hasta decidir que lee la prueba).
- **Costo aceptado:** codigo nuevo; el cierre exige tu consola y un reinicio.

## 2026-10-17 — El portero se extiende a las tandas de LibreOffice de otros proyectos, primero en `observar` (voto de Luis)
- **Decision:** ficha `DEBT-PORTERO-NO-CLASIFICA-TANDAS-DE-LIBREOFFICE-DE-OTROS-PROYECTOS-01`. El portero clasifica por forma de comando; las conversiones `soffice --headless` no tienen clase y entran sin cola ni tope. Entra en `observar` antes de `actuar`.
- **Por que:** el 2026-10-17 una tanda de 13 `soffice` mas las suites de Atlas y Twiner dejaron la memoria libre en 15 % y earlyoom mato workers del push de este repo (2 pushes caidos por `worker crashed`, sin test fallido).
- **Descarta:** que cada proyecto se autorregule (cada push sigue expuesto a que earlyoom lo mate cuando otro proyecto llena la memoria).
- **Costo aceptado:** congelar un trabajo ajeno puede alargarlo; se excluye lo que sostiene `index.lock` y se mide una tanda real antes de pasar a `actuar`.

## 2026-10-17 — El tope de 42 GiB de `app.slice` no se toca hasta medir la recarga de cache (voto de Luis)
- **Decision:** medir primero. Las muestras de `bb` pasan a registrar los contadores acumulados de recarga de cache y de recuperacion directa de `app.slice`; el tope se revisa el 2026-10-23 junto con `memory.high`.
- **Por que:** medido en esta ATOM con 60 GiB libres en la maquina: `memory.max` 42 GiB, `memory.current` 38.7 GiB de los que 15.6 eran `inactive_file`; `memory.events max` 55 588 choques en 3 h; `pgscan_direct` 308 M contra `pgscan_kswapd` 2.9 M (99 % recuperacion directa); `workingset_refault_file` 47.8 M (unos 182 GB de cache releida). La presion de memoria de la slice se mantuvo en ~0, asi que el efecto visible es disco, no memoria.
- **Descarta:** subir `memory.max` a 56 GiB ya (el 2026-10-16 un cambio de topes sin medicion empeoro un atasco); quitar el tope duro (contradice el presupuesto de slices del 2026-09-27 y pierde el techo que contiene a las suites).
- **Costo aceptado:** unos dias mas con el tope actual y la posible lentitud asociada.
- **Hecho aparte, sin voto:** el portero medía la holgura sobre `memory.current` con la cache inactiva incluida (veia 3.3 GiB donde habia 19) y congelaba suites sin necesidad; ahora usa la memoria de trabajo.
