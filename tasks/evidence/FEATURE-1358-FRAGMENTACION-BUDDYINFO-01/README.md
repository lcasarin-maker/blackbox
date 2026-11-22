# Microfase offline

Base declarada: `226654b1ae025fbd8602f9a7739d163593826051`.

- El parser distingue observado, faltante, fallido e incompleto; reporta órdenes buddy como bloques, por nodo y suma.
- Pageblocks se extraen únicamente de `Number of blocks type`; se ignoran el desglose de páginas libres y `Number of mixed blocks`.
- `bb sample` conserva `NOT_COLLECTED` por defecto. La lectura opt-in se ejecuta bajo la misma invocación y no usa sudo. Su costo sobre el kernel real queda sin medir; por eso no se activa de forma predeterminada ni se afirma que `timeout` pueda interrumpir una lectura kernel ininterrumpible.
- El reporte conserva `UEFI After Power Loss` y `kernel.panic_on_rcu_stall` como `NOT_COLLECTED` y adjunta la muestra solo si boot ID y tiempo coinciden.
- El lector vive en `tools/incident_report.py` y el muestreo opt-in lo invoca como módulo en un subshell situado en la raíz del repo; el cwd de `bb sample` no cambia.
- Las pruebas (bwrap y unitarias) cubren dos nodos, cabeceras repetidas, tabla mixed presente/ausente, conteos distintos antes/después, fuente malformada y captura desactivada. La corrida compartida inicial se excluyó porque sus `cp` quedaron fuera del lock; el recibo válido usa una copia aislada por variante. No acredita costo ni comportamiento operativo del kernel.
- El control de contador decimal excesivo falla solo en buddyinfo y conserva pagetypeinfo. El primer pre-commit rechazó el módulo nuevo por falta de inventario; la fila SPEC se autorizó y pasó los hooks, luego se retiró junto con el módulo al integrar el parser en `incident_report.py` para volver al OWNS inicial.
- Terra encontró en `219fd311` una cabecera pageblocks repetida vacía que daba falso `ok`. RED CLI: con buddy válido y tabla Normal válida seguida de una cabecera vacía, el estado de pagetypeinfo fue `ok`; GREEN: la sección vacía al EOF o seguida por un delimitador pasa a `COLLECTION_FAILED`, conservando buddy `ok`. Se cuentan filas completas de cualquier zona para cerrar sección y solo Normal entra al agregado.
- Decisión posterior: reusar `tools/incident_report.py` para el parser/CLI; se retiró el módulo dedicado y su fila de SPEC. `bb sample` llama `python -m tools.incident_report --fragmentacion` solo dentro de la opción opt-in y en un subshell con cwd del repo.
- Ficha abierta: falta captura real antes/después de carga y control operativo descrito en su `close_check`.

Comando y salida de la ejecución local se conservan en scratch privado fuera del repositorio.
