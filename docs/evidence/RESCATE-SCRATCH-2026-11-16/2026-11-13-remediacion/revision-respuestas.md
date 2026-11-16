# Respuestas a la primera revision Claude

Commits nuevos sobre fec92311; historia conservada, push pendiente de aprobacion.
La ficha de privacidad sigue abierta para la segunda parte.

| Punto | Commit de correccion | Evidencia |
|---|---|---|
| 1: red de diseno y cuota SPEC | bcba6b19 | SPEC:276 vuelve a su red de diseno; :380 usa @BB_GATEWAY@. Inventario expande solo esa plantilla al destino existente; cuota SPEC=1 y _LAB coherentes. Plantilla valida pasa, nombre ajeno produce 2 hallazgos en test_inventario. |
| 2: id y nombre de ficha | bcba6b19 | Nombre e id cambian juntos a FEATURE-GATEWAY-VLLM-Y-RIESGOS-DE-MAQUINA-DESDE-CONSUMIDOR-01. Pointer actualizado en ficha de privacidad. |
| 3: configuracion de emergencia | 3522a4dc | ConfiguracionError incluye archivo, clave usuario, propietario root y modo 0600. Panic hace preflight antes de actuar; suspension/restauracion y los dos entrypoints de los timers devuelven 2 con COULD_NOT_RUN. docs/PANIC.md paso 0 exige crear configuracion antes de instalar copias. Tests para JSON sin clave y los tres entrypoints sin archivo; instalaciones intactas. |
| 4: snapshot publicado | 247d661b | ls-tree y cat-file leen blobs HEAD; la base tambien sale de HEAD. Tres pruebas ejercen disco limpio, archivo borrado e indice limpio, con base del disco adulterada; bloquean y luego pasan tras un commit limpio. Control externo con el commit plantado y disco limpio: falla la fila nueva. |
| 5: concatenacion de MAC | 3522a4dc | Los dos operandos son literales sinteticos completos con guiones, uno en mayusculas y otro en minusculas; ninguna concatenacion para ocultar el literal. |
| 6: motivos y politica | 247d661b | Siete motivos distintos, cada uno nombra su contrato y boleta 2026-11-13. Politica: crecer solo mediante voto fechado, clase y motivo por archivo. Misma regex, firma y cuentas. |
| 7: tema ntfy adivinable | 3522a4dc | El ejemplo lleva un marcador sin https; carga lo rechaza antes de la red. Control con URL HTTPS sintetica lo admite sin enviarla. |
| 8: WoL doc y JSON lista | 3522a4dc | Uso con BB_WOL_CONFIG documentado, blancos reducidos, JSON no-objeto produce error de argumentos y rc=2. Prueba de lista vacia pasa. |
| 9: transformaciones, despliegues y rutas | c9f28ae5 y dd5b7098 | Huellas reales anterior/transformada de memory_gate.jsonl y pass.txt, despliegues pendientes y timers dependientes anotados. Cinco nombres de ruta iniciales: uno renombrado junto con id; cuatro quedan para segunda parte, enumerados mediante patrones sin copiar valores. |

## Pruebas y controles

Ejecutor de regresiones antes de cambiar implementacion:
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_guarda_snapshot.py tests/test_config_privacidad.py` (basetemp en scratch).
Salida previa: `8 failed, 4 passed in 0.48s`.
Mismo conjunto corregido: `12 passed in 0.78s`.
Focal de seis archivos tras corregir: `114 passed in 33.48s`.
Inventario del repo: `[inventario] HALLAZGOS: 0`.
Guarda antes de la limpieza: `1 failed, 4 passed in 3.31s`; despues de la primera limpieza: `5 passed in 3.32s`; guarda actual: `5 passed in 3.51s`.
Ruff instalado, `ruff check` sobre los archivos Python tocados: `All checks passed!`.
El intento `python3 -m ruff` carecia de modulo en ese interprete; se sustituyo
por el CLI instalado que tambien usan los hooks, sin instalar dependencias.

Control externo: `PYTHONDONTWRITEBYTECODE=1 python3 "$HOME/scratch/blackbox/2026-11-13-remediacion/control-revision.py"`.
El ejecutor corre literalmente `simplecode verify --hook pre-push` en la copia,
primero limpia y despues con dato sintetico en HEAD y texto limpio en disco.

revision-gate-limpio: `{"could_not_run": 0, "fail": 0, "pass": 5, "pending": 0}`.
datos-privados-publicacion=pass, pytest=pass, bb-cobertura-piso=pass, ceremony=pass, close-check=pass.

revision-gate-head-disco-limpio: `{"could_not_run": 0, "fail": 1, "pass": 4, "pending": 0}`.
datos-privados-publicacion=fail, pytest=pass, bb-cobertura-piso=pass, ceremony=pass, close-check=pass.

revision-guarda-head-disco-limpio: `1 failed, 4 passed in 3.32s`.

revision-guarda-head-disco-borrado: `1 failed, 4 passed in 3.31s`.

No se pudo correr en estas guardas y gates: 0; pending=0.
No se ejecuto ningun despliegue, reinicio ni operacion sobre servicios.
La primera suite completa sigue roja: 17 fallos de los 18 anteriores, 0 nuevos;
solo deja de fallar la guarda, 8 skipped, 3 deselected. La segunda suite adjunta prevalece para el codigo corregido.

Segunda suite: `17 failed, 4579 passed, 8 skipped, 3 deselected, 2 warnings in 522.43s (0:08:42)`.
Nuevos: 0; persistentes: 17; nodos que dejan de fallar: tests/test_sin_datos_privados.py::test_el_repo_no_gana_datos_privados.

Historia conservadora, clases: `{"HOST": 1, "IP_LAN": 25, "KB": 2, "MAC": 33, "PROYECTO": 16, "USUARIO": 1, "commits_afectados": 682}`.

Marcas: `{"A-confirmado": 13, "A-histórico": 10, "candidato-sintético": 55}`.

Archivo privado `~/scratch/blackbox/2026-11-13-reescritura/valores-a-purgar.NO-PUBLICAR.txt`,
con 78 valores, modo 600; adjudicacion de candidatos en segunda
parte. Contenido privado fuera del reporte. Cuatro nombres de ruta y las tres
coberturas historicas con usuario son residuos previos anotados para seguimiento;
la guarda mide contenido, no nombres. Sin ampliar regex ni cuotas historicas.
Close-check del repo puede informar no_ejecuta=1 sobre la ficha historica de
ventana GPU; el reporte principal conserva esa omision junto a los counts.
Warnings: la primera pasada mostraba una en
`tests/test_portero_efectos.py::test_cmd_demonio_sin_contenedores_no_llama_a_docker_y_duerme_entre_ciclos`;
la segunda muestra dos, en `test_cmd_run_lanza_con_tope_en_todo_modo_y_solo_actuar_hace_esperar`
y `test_cmd_demonio_una_vez_corre_un_ciclo_y_con_contenedores_aplica` del mismo archivo.
Son excepciones de hilo gpuoom-gpu; se conservan como advertencias, sin resolverlas aqui.
Los 17 nodos fallidos siguen listados en suite-revision-comparacion.json.
Memoria de continuidad: entrega pendiente al coordinador por restriccion de escrituras.

Commits observados:

d5bad497 fix(privacy): parametrizar destinos locales y sanear clase A
d9967fc9 test(privacy): admitir siete contratos de compatibilidad clase B
fec92311 gate(privacy): exigir guarda del snapshot completo en cada push
c9f28ae5 docs(privacy): registrar controles, transformaciones y reescritura pendiente
5d49599c docs(privacy): expresar rutas del comando con HOME
cdd9e1a9 docs(privacy): conciliar inventario final y omision del close-check
bcba6b19 fix(privacy): conservar red de diseno y alinear identidad del inventario
3522a4dc fix(emergencia): rechazar configuracion invalida con instrucciones claras
247d661b fix(privacy): medir blobs y linea base de HEAD sin leer disco ni indice
dd5b7098 docs(privacy): responder revision y conciliar suite y controles finales

`git rev-parse master origin/master`:

dd5b7098b3714219a3a5fc6a2c17964c0baa4d7f
dc1b544284c19cbea5f31db8b5c5b2a4863a07f9
