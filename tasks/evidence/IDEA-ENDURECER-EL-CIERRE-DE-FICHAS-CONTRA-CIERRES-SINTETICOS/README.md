# Medicion pendiente de adjudicacion; politica vigente report-only

Owner: simplecode. ID existente: IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS.
La ficha canonica sigue abierta. No se activa bloqueo ni se declara probado
ningun cierre por el PASS de una politica informativa.

## Candidato de ronda 2

simple.json vuelve a args=[] mediante un cambio hacia adelante: es la misma
politica que emiten el generador y el perfil canonicos. alineacion-r2.json
compara la fila completa pertinente de las tres fuentes. No se regeneraron
filas ajenas ni se elimino la guarda de privacidad local.

close-check-measurement-r2.patch propone exclusivamente dos archivos de pruebas
y anotacion de estado/owner en la ficha canonica. No modifica la politica
productiva, generador, perfil ni binario de simplecode. El repo simplecode
se leyo; no se escribio en el. Su owner debera coordinar la integracion tras
la ultima revision independiente. source-r2.json fija las huellas de entrada.
Cualquier enforce futuro requiere voto concreto, integracion canonica y
corredor compatible; no se admite parche runtime ad hoc.

## Aceptacion y medicion separadas

El close_check existente mantiene tests/policy/test_close_check_lint_block.py.
Ese archivo propuesto ahora tiene aceptaciones rojas de producto: bloqueo
futuro pendiente, rechazo de analisis real y echo confundido con ejecucion.
Resultado: 3 failed in 0.13s. Los criterios reales siguen pendientes, incluido
adjudicar tasa y formular la boleta; estas pruebas rojas no autorizan activar
bloqueo contra el voto vigente. La ficha no queda cerrable por cuatro verdes.

Las cuatro verdes pertenecen a test_close_check_report_measurement.py:
rango explicito y rango del hook, exclusiones de fichas fuera del rango,
Git ausente en repo valido con controles antes/despues, ref inexistente y
producto realmente ejecutado antes del reporte. El reporte no ejecuta el
producto: la prueba comprueba que su efecto no se vuelve a crear.
Resultado: 4 passed in 0.40s. Neutralizar el detector rompe el negativo
(1 failed in 0.13s); conservar Git donde debia retirarse rompe su prueba
(1 failed in 0.18s). Son controles de medicion, no aceptacion de cierre.

## Muestra discriminada, sin extrapolar a la flota

measurement-r2.json conserva comando clasificado, ejecucion del fixture,
control negativo, salidas y adjudicacion. Son seis casos controlados:
dos falsas alarmas de futuro bloqueo, una omision por echo, dos correctos y
uno sin adjudicar (consulta systemctl no ejecutada por alcance).
CNR de esa muestra: 1. No hay tasa representativa ni umbral votado.

## Compatibilidad observada, sin publicar

Corredor instalado con fila nativa report-only y rango valido:
rc=0, pass=1, fail=0, could_not_run=0, pending=0, aunque imprime no_ejecuta=1.
Eso prueba disponibilidad del reporte, nunca ejecucion ni cierre limpio.
Control de rango inexistente: rc=2, could_not_run=1, pass=0, fail=0, pending=0.
No se recompilo ni instalo el corredor. Revision 2 y corredor final quedan
a cargo de coordinacion antes de cualquier publicacion.

## Evidencia historica conservada

medicion.json conserva el falso verde publicado; controles.json y source.json
pertenecen a la propuesta anterior. Esa propuesta se renombro a
propuestas-no-vigentes/close-check-enforce.patch: MANIFEST.json conserva sha256,
modo, caducidad y vigilancia. No esta autorizada para aplicar. La politica
report-only deriva de Boleta 6, 2A y de la instruccion vigente del director.
El alcance mas amplio de la ficha canonica sigue abierto; ninguna huella ni
manifest se presento como producto recapturado.

Las tres fichas de privacidad permanecen open, sin implementar sus arreglos.
Sin servicios, Dell, GPU, historia ni lista privada.
