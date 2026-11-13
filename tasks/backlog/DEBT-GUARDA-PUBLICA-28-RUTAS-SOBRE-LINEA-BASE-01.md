---
id: DEBT-GUARDA-PUBLICA-28-RUTAS-SOBRE-LINEA-BASE-01
kind: debt
domain: SECURITY
title: "Rojo previo: 28 archivos publicados exceden la linea base de datos privados"
status: open
severity: P1
origin: measured
created: 2026-11-13
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider tests/test_sin_datos_privados.py", "expect": "exit_zero", "porque": "La guarda debe pasar con las siete admisiones B votadas el 2026-11-13 y sin admitir A ni debilitar patron o controles; la ficha permanece abierta hasta reescribir la historia."}
---

## Rojo previo medido

Comando exacto: `python3 -m pytest -q -p no:cacheprovider tests/test_sin_datos_privados.py`.
Salida resumida literal: `1 failed, 4 passed`; codigo `1`.
Falla `test_el_repo_no_gana_datos_privados`: 28 archivos exceden la linea base
`tests/fixtures/datos_privados_baseline.json`. Se documentan rutas y conteos;
el contenido detectado se reserva para una revision separada.

La misma falla aparece en el commit previo a /clean,
`fe1e9cbf1e77d60890a26d3a5c6de55e6a6e308c`: `1 failed, 4 passed in 3.31s`,
codigo `1`, en un clon local independiente de ese commit.
Los cuatro tests restantes comprueban el patron firmado, fixtures limpios y
fixtures que deben disparar la guarda; el comparador devuelve vacio con cuentas
iguales y detecta un archivo nuevo o una cuenta mayor. Ese es el control negativo.

## Rutas y conteos

Las 28 rutas y sus cuentas fueron contrastadas con los blobs de `origin/master`
en `7ae6f669db5c73d51afed87e68dfae6c2f66a8d7`: todas ya estaban publicadas,
con la misma cuenta. Columna "base": ausencia en el JSON equivale a cero.
Una ruta se expresa como patron univoco para que el inventario de rutas no
reintroduzca el nombre que busca la propia guarda; `git ls-files -- '<patron>'`
recupera su nombre exacto. El inventario completo local conserva el nombre literal.

| Ruta | Base | Actual y remoto | Desde (exceso continuo) |
|---|---:|---:|---|
| `DECISIONS.md` | 0 | 2 | `df4925aafb90` |
| `SPEC.md` | 1 | 5 | `abc42f4e875c` (limite: 80 revisiones) |
| `adopted/boton-rojo-keep.txt` | 0 | 3 | `abc42f4e875c` |
| `adopted/gateway/admission_check_wrapper.sh` | 0 | 2 | `7a84acf11c65` |
| `adopted/solo-registro.txt` | 0 | 1 | `e22921e45c21` |
| `adopted/systemd-user/bb-muestreo-corte.service` | 0 | 1 | `e22921e45c21` |
| `bin/bb` | 0 | 6 | `28bfec9ddc79` |
| `logs/memory_gate.jsonl` | 0 | 18 | `c329248f18f1` |
| `tasks/backlog/DEBT-CAIDAS-DURAS-7-0-MODULO-PARCHADO-01.md` | 0 | 7 | `e9eee190d357` |
| `tasks/backlog/DEBT-MEMORIA-GPU-SIN-LIMITE-APLICADO-COLAPSOS-5-Y-6-NOV-01.md` | 0 | 5 | `e9eee190d357` |
| `tasks/backlog/DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01.md` | 0 | 8 | `7a84acf11c65` |
| `tasks/backlog/FEATURE-GATEWAY-VLLM-Y-RIESGOS-DE-MAQUINA-DESDE-CONSUMIDOR-01.md` | 0 | 20 | `fe1e9cbf1e77` |
| `tasks/backlog/FEATURE-PRUEBA-KERNEL-7-0-1025-UNA-VEZ-01.md` | 0 | 1 | `16cd76512f9a` |
| `tasks/backlog/IDEA-DECLARAR-DUENIO-UNICO-DEL-MONITOREO-Y-AREAS.md` | 0 | 1 | `002e4f2d7eff` |
| `tasks/backlog/IDEA-DISTINGUIR-COMANDO-DESCONOCIDO-EN-BB-ROOT-RUN.md` | 0 | 1 | `002e4f2d7eff` |
| `tasks/backlog/IDEA-REENCOLAR-TRABAJO-PERDIDO-TRAS-CAIDA-DE-LA-MAQUINA.md` | 0 | 1 | `8a2d2254094d` |
| `tasks/backlog/IDEA-RESPETAR-MARCA-DE-DIAGNOSTICO-EN-PRUEBAS-DEL-PRODUCTO.md` | 0 | 1 | `002e4f2d7eff` |
| `tasks/backlog/IDEA-TABULAR-BLOQUEADORES-Y-BOLETA-DE-DESBLOQUEO.md` | 0 | 1 | `002e4f2d7eff` |
| `tasks/done/FEATURE-VENTANA-GPU-NOCTURNA-SECUENCIA-01.md` | 0 | 5 | `eb4932585361` |
| `tasks/evidence/FEATURE-VENTANA-GPU-NOCTURNA-SECUENCIA-01/pass.txt` | 0 | 1 | `eb4932585361` |
| `tests/test_bb_wol.py` | 0 | 6 | `4a03ddd8ce1c` |
| `tests/test_boton_rojo.py` | 0 | 24 | `abc42f4e875c` |
| `tests/test_inventario.py` | 0 | 1 | `7a84acf11c65` |
| `tools/boton_rojo.py` | 0 | 2 | `abc42f4e875c` |
| `tools/inventario.py` | 0 | 3 | `7a84acf11c65` |
| `tools/motor_solicitudes.py` | 0 | 2 | `28bfec9ddc79` |
| `tools/testigo/bb_alarma.py` | 0 | 1 | `2d1f92fdeac5` |
| `tools/testigo/bb_wol.py` | 0 | 4 | `4a03ddd8ce1c` |

Se recorrio `git log --format=%H --max-count=80 origin/master -- <ruta>`
desde la punta y se conto el patron sobre cada blob de `git show <sha>:<ruta>`,
hasta encontrar una cuenta dentro de la base o la creacion del archivo.
"Desde" designa el comienzo del tramo continuo medido que excede la base actual,
no un juicio sobre el criterio de privacidad vigente cuando se escribio el commit.
Para SPEC.md se agoto el limite: el origen exacto queda pendiente de medir.

## Accion pendiente

Remediacion separada con revisor: clasificar cada hallazgo, sanear sin copiar el
contenido sensible a evidencias publicas y volver a correr la guarda y sus controles.
La instruccion original de conservar la base se sustituye por la boleta del
2026-11-13: admitir exclusivamente las siete rutas B por compatibilidad.
La ficha permanece abierta hasta la reescritura publicada y su comprobacion.

## Limpieza hacia adelante — 2026-11-13

Decision de Luis: primero sanear HEAD y obligar la guarda en push; despues
reescribir la historia en una tarea distinta. Esta ficha sigue `open`.
Fuente de clasificacion: evaluacion local 2026-11-13, 21 A y 7 B.
Commits de implementacion: `d5bad497`, `d9967fc9`, `fec92311`.

- A: narrativas y evidencia transformadas; usuario y destinos operativos
  se leen de configuracion externa, con ejemplos sinteticos en `config/`.
  En la primera pasada SPEC.md:380 conservaba una referencia de compatibilidad.
  La revision la sustituye por @BB_GATEWAY@, preservando el inventario mediante
  su expansion; SPEC.md:276 vuelve a la red de diseno del puente. La cuota
  existente de 1 vuelve a corresponder exclusivamente al motivo _LAB.
- B: siete rutas admitidas con cuenta exacta (3, 2, 6, 24, 1, 3, 2),
  total 41; cada una lleva motivo en `MOTIVOS`. Patron y firma conservados.
- Pre-push: `datos-privados-publicacion`, siempre seleccionada; simplecode
  ejecuta pytest en el snapshot Git completo, con `git_context: true`.
- Guarda antes: `1 failed, 4 passed in 3.31s`. Despues:
  `5 passed in 3.32s`. Pruebas de configuracion antes: `4 failed in 0.08s`;
  focal despues: `41 passed in 13.06s`.
- Copia scratch: guarda con dato plantado `1 failed, 4 passed in 4.52s`;
  pre-push limpio `{"could_not_run":0,"fail":0,"pass":5,"pending":0}`;
  commit plantado con disco ya limpio:
  `{"could_not_run":0,"fail":1,"pass":3,"pending":0}`.
  La fila nueva es la que falla. El control demuestra lectura del commit.

### Evidencia transformada, custodia y huellas

Las siguientes huellas se midieron sobre bytes anteriores y transformados.
Los hashes y nombres internos preexistentes que describen otras evidencias
se conservan como referencias historicas; los bytes redactados ya no son el
original. Estos archivos son copias transformadas, no nuevas capturas runtime.

- `logs/memory_gate.jsonl`: SHA256 anterior `da6ffaff00e224f484b3fb87429b1827d40c3e269fa6506c682c39e2f70dba3f`; transformado `5a57d6f24bfa1182462ace6727337348982aaebde696c313ce82dec30cd559ad`.

- `tasks/evidence/FEATURE-VENTANA-GPU-NOCTURNA-SECUENCIA-01/pass.txt`: SHA256 anterior `ae17b1b6b0d264ce0718e82f1deb7c1178e43008c0f934c71c6cfee4d714db18`; transformado `2218392d122b75a1425490f1ef99c7c6fab2e46e90bbaec48ce5dc3e67e7d975`.

### Despliegues pendientes, sin tocar instalaciones

- Copia root `/usr/local/lib/blackbox/tools/boton_rojo.py`: configurar
  `/etc/blackbox/rojo.json` (o BB_ROJO_CONFIG/BB_ROJO_USUARIO) antes de desplegar.
- Unit de usuario `bb-muestreo-corte.service`: crear configuracion local
  `%h/.config/blackbox/muestreo.env` con BB_MUESTREO_SCRIPT antes de actualizar.
  Conserva el script instalado hasta que su ficha resuelva la migracion.
- Copia autonoma de `bb_wol.py` en la Dell: configurar BB_WOL_CONFIG con
  JSON privado de mac/broadcast antes de reemplazarla. La ubicacion de la
  copia instalada queda por comprobar en el despliegue.
- `bb_alarma.py`: solo cambia el ejemplo documental; ya lee alarma.json
  privado mediante --datos. Su copia distribuida conserva el ejemplo previo.
- `adopted/solo-registro.txt`: comentario neutralizado; conservar instalada
  la copia de registro hasta revisar el drift de esta transformacion.

### Historia preparada, segunda parte pendiente

Se recorrio `git log -p --all --no-ext-diff --format=COMMIT_PRIVACIDAD:%H`,
sin limite de revisiones ni archivos, buscando la misma regex firmada en
lineas agregadas y retiradas; dos fixtures sinteticos explicitos se excluyeron.
Lista privada modo 600 en scratch de reescritura, nunca versionada:
78 valores distintos: MAC=33, IP_LAN=25, USUARIO=1, HOST=1, KB=2, PROYECTO=16;
682 commits afectados por alguna coincidencia retenida, incluyendo retiradas
(recorrido tras corregir revision: 682; tras documentar: 681; primero: 679).
Marcas: A-confirmado=13, A-historico=10, candidato-sintetico=55.
A-confirmado procede de coincidencias de los archivos A de la evaluacion
(SPEC restringido al usuario); A-historico identifica tokens privados del
patron retirados; IP/MAC restantes quedan por adjudicar, incluidos posibles
datos reales antiguos. Las variantes de mayusculas conservan su identidad
exacta para el reemplazo. Esto prepara candidatos; no ejecuta reescritura.

Memoria de continuidad: entrega pendiente al coordinador por la restriccion
de cero escrituras fuera del repo y scratch. No se invoco el servicio.

### Suite completa y limites operativos

Comando: `PYTHONDONTWRITEBYTECODE=1 TMPDIR=$HOME/scratch/blackbox/r13 python3 -m pytest -q -p no:cacheprovider --basetemp=$HOME/scratch/blackbox/r13/suite`.
Salida literal: `17 failed, 4570 passed, 8 skipped, 3 deselected, 1 warning in 618.35s (0:10:18)`; rc=1.
Comparacion de nodos contra los 18 de DEBT-SUITE-PREVIA-ROJA-2026-11-13-01:
17 persistentes, 0 nuevos; solo deja de fallar
`tests/test_sin_datos_privados.py::test_el_repo_no_gana_datos_privados`.
Los dos fallos de entorno anotados en esa ficha reaparecen en esta pasada;
se conservan en el total de 17, sin convertirlos en aprobados.
Control del comparador: nuevos_real=0; agregar un nodo sintetico produce
nuevos_control=1. Reporte detallado local: suite-comparacion.json.

No se pudo correr (guarda, controles y gates de privacidad): 0.
Omisiones de suite: 8; deseleccionados por configuracion habitual: 3.
La suite sigue roja; la reescritura y el despliegue siguen pendientes.

### Correccion documental y omision conservada

El comando de suite se documento inicialmente con dos apariciones del usuario
local en la ruta absoluta; el gate de c9f28ae5 las detecto. Se corrigieron en
5d49599c mediante HOME, en un commit nuevo; esa incorporacion/retirada entra
en los 681 commits candidatos a purga y se conserva en la historia hasta la
segunda parte votada. El gate sobre c9f28ae5 informo fail=2, pass=3,
could_not_run=0 (guarda y pytest fallaron por la misma linea documental).

Close-check informa `fichas_cerradas=1 ejecuta=0 no_ejecuta=1` sobre la ficha
historica de ventana GPU, cuyo comando compuesto carece de ejecutor admitido.
Se registra la omision junto a los contadores del gate; el estado done previo
de esa ficha no acredita que el close-check haya podido ejecutarla ahora.

## Revision Claude, correcciones de la primera ronda

- Bloqueantes 1 y 2, commit bcba6b19: red de diseno de SPEC.md:276 restaurada;
  @BB_GATEWAY@ en su tabla y expansion limitada en inventario; se conserva
  cuota SPEC=1 y su motivo _LAB. Prueba de inventario: la plantilla correcta
  pasa y un nombre de archivo ajeno devuelve dos hallazgos. La ficha del
  gateway cambia nombre e id juntos a la ruta neutra indicada en la tabla.
- Bloqueante 3 y menores 5, 7 y 8, commit 3522a4dc: error de configuracion
  con archivo e instrucciones (root, modo 0600) en lugar de traceback;
  manejo en panic, suspension/restauracion y los dos entrypoints de los timers.
  docs/PANIC.md exige configuracion antes de actualizar; instalaciones intactas.
  WoL documenta BB_WOL_CONFIG, rechaza JSON no objeto y sus fixtures usan
  literales sinteticos completos; ejemplo ntfy sin https, rechazado por carga.
  Unit de muestreo exige que el script configurado exista antes de arrancar.
- Bloqueante 4 y menor 6, commit 247d661b: medir usa ls-tree y cat-file de HEAD;
  la propia base tambien sale de HEAD. Disco, indice o base sin commit no
  pueden blanquearlo. Motivo especifico y voto fechado para cada B.
  Regresiones antes: 8 failed, 4 passed in 0.48s; despues, pasada focal:
  114 passed in 33.48s. Los tres casos de HEAD contaminado (disco limpio,
  borrado e indice limpio) bloquean y, tras un commit limpio, pasan.
- Menor 9: transformaciones y despliegues anotados arriba desde c9f28ae5.
  Los puntos de restauracion root tambien dependen del archivo privado nuevo.

### Nombres de ruta fuera del alcance de la regex

El revisor encontro inicialmente cinco rutas con nombres internos, que la
regex de contenido no mide. La ficha gateway ya se renombro junto con su id.
Quedan cuatro, para la segunda parte (patrones que preservan su privacidad):
`docs/evidence/INVESTIGACION-GB10-2026-10-11/entrega_*.json` (2),
`tasks/evidence/FEATURE-*-RECOLECTOR-HALLAZGOS-BB-01/e2e.txt` (1),
`tasks/evidence/FEATURE-COSECHA-FORO-*/entrega_*_manifiesto.sha256` (1).
`git ls-files -- '<patron>'` recupera cada sujeto sin copiar aqui los valores.
Ademas, tres archivos .coverage historicos ya admitidos por la base contienen
usuario local; son residuo previo fuera de las 21 A de esta tarea. La ficha
sigue abierta y el reporte no afirma ausencia global de A en toda la base.
La ampliacion del patron a otras formas de MAC y la reduccion de cuotas
historicas vacias requieren trabajo separado; el patron firmado se conserva.

### Resultado final de la correccion de revision

Segunda suite completa (mismos argumentos, basetemp suite-revision en scratch):
`17 failed, 4579 passed, 8 skipped, 3 deselected, 2 warnings in 522.43s (0:08:42)`;
rc=1. Comparacion con los 18 originales: nuevos=0, persistentes=17;
solo deja de fallar la guarda. Las nueve pruebas nuevas de esta revision pasan.
Las dos warnings son excepciones de hilo gpuoom-gpu durante los tests de portero
`test_cmd_run_lanza_con_tope_en_todo_modo_y_solo_actuar_hace_esperar` y
`test_cmd_demonio_una_vez_corre_un_ciclo_y_con_contenedores_aplica`.

Control externo, comando literal `simplecode verify --hook pre-push` en clon:
limpio `{"could_not_run":0,"fail":0,"pass":5,"pending":0}`;
HEAD con dato sintetico y disco limpio
`{"could_not_run":0,"fail":1,"pass":4,"pending":0}`.
Solo falla datos-privados-publicacion; guarda directa con disco limpio:
`1 failed, 4 passed in 3.32s`; disco borrado:
`1 failed, 4 passed in 3.31s`. Guarda corregida limpia:
`5 passed in 3.51s`. No se pudo correr en estos controles: 0.
Faltan aprobacion de ultima revision y push normal, segun instruccion del
coordinador; la historia, los despliegues y la adjudicacion siguen pendientes.
