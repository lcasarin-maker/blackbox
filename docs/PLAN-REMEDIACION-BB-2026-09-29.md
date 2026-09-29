# Plan de remediación adversarial de blackbox — 2026-09-29

Base auditada: `72d190d`. Ocho deudas abiertas: cinco P1 y tres P2.
Estado: registro completo; ocho de ocho fichas cerradas en código. Despliegues pendientes.

## Orden de ejecución

1. **Seguridad de la simulación:** DEBT-TERMICA-DRY-RUN-ACTUA. Separar observación de actuación antes de usar el CLI para validar otras reparaciones.
2. **Guardián de procesos:** DEBT-GUARDIA-REPLAY-HISTORICO y DEBT-GUARDIA-ARCHIVO-TARDIO en un mismo cambio coherente. Resolver cursor, frescura, identidad y ciclo de archivo juntos: recuperar lectura sin proteger el replay agravaría el primer defecto.
3. **Watchdog:** DEBT-WATCHDOG-PSI-ILEGIBLE-REARMA. Preservar política tras colapso y exigir recuperación observada. Puede implementarse independientemente del guardián.
4. **Recuperación térmica:** DEBT-TERMICA-PAUSAS-PERDIDAS. Depende de la separación de actuación del paso 1. Cubrir interrupciones entre persistir y enviar señales, reinicio y PID reutilizado.
5. **Contrato del informe:** DEBT-SCAN-CNR-OMITE-ANALISIS y DEBT-SCAN-VENTANA-INCONSISTENTE. Un lector y un resultado común para análisis de JSONL; reutilizar stdlib y mecanismos existentes antes de agregar abstracciones.
6. **Semántica GPU:** DEBT-SCAN-GPU-PROCESOS-FANTASMA sobre el contrato anterior. Distinguir lista vacía, dato ausente, idle y evidencia de fallback.

## Verificación exigida

Cada ficha especifica un nodo de pytest futuro en `tests/test_auditoria_bb_regresiones.py`.
Los nodos deben ejecutar el comportamiento productivo, incluidos main/bucles y scan completo cuando aplique; copiar algoritmos en el test dejaría el sujeto sin verificar.
Prueba roja contra la base, verde tras la reparación y controles sanos. Usar reloj, sensores, señales y notificaciones simulados; ninguna prueba necesita reiniciar la máquina o matar trabajo real.

La auditoría corrió:

```sh
python3 -m pytest tests/test_bb_guardia_proceso.py tests/test_bb_usable.py tests/test_mitigacion_solo_con_carga.py -q
```

Resultado registrado en la conversación: `2 failed, 53 passed in 1.51s`.
Las dos fallas fueron `PermissionError: [Errno 1] Operation not permitted` al enlazar sockets Unix en el sandbox. **could_not_run: 2** para esas pruebas de integración; no atribuirlas al producto ni presentar la suite como limpia. Repetirlas en entorno que permita sockets antes de certificar esa integración.

## Evidencia conservada y límites

`tasks/evidence/AUDIT-BB-2026-09-29/observed.txt` conserva la salida histórica y `reproduce.py` el arnés, con ruta del repo relativa para portabilidad. Ejecutar desde la raíz con `python3 tasks/evidence/AUDIT-BB-2026-09-29/reproduce.py`.

Correspondencia: H1 replay; H2 archivo tardío; H3 PSI ilegible; H4 ventana; H5 GPU vacía; H6 datos sin campos; H7 pausa perdida; H8 dry-run.
H4/H5/H6 ejecutan bloques extraídos del código, no todo el CLI; H7 simula pérdida de estado, no un reinicio de systemd. Reutilización de PID es riesgo identificado por inspección, pendiente de control específico. H6 usa JSON válido sin campos, pese al rótulo histórico “malformed JSON”.
El arnés imprime observaciones: su exit 0 acredita ejecución, NO corrección ni cierre. No sustituye las pruebas de regresión futuras.

## Despliegue y cierre

Después de pruebas y gates pertinentes: actualizar documentación, revisar diff, desplegar las piezas modificadas y comprobar que las unidades ejecutan el código nuevo mediante el comprobador existente `tools/demonio_al_dia.sh`. Registrar salud y frescura de datos. Coordinar cualquier reinicio de servicios que conserve pausas con la recuperación del paso 4; evitar pérdida de propiedad de procesos pausados.
Cerrar cada deuda solo con su close_check pasando y evidencia real del comportamiento, incluidos límites del despliegue. Este plan no modifica umbrales ni suspende guardias para conseguir un resultado verde.

## Avance secuencial

1. **Cerrada:** DEBT-TERMICA-DRY-RUN-ACTUA. `--dry-run` ahora imprime `mitigacion_simulada` sin enviar señales ni alterar estado. `close_check`: 2 passed; suite térmica relacionada: 121 passed. Evidencia roja, verde y suite: `tasks/evidence/DEBT-TERMICA-DRY-RUN-ACTUA/`. Despliegue del servicio pendiente.
2. **Cerrada:** DEBT-GUARDIA-REPLAY-HISTORICO. El lector ignora historia preexistente, descarta telemetría vieja y valida boot e identidad PID/starttime; limita cada poll a una muestra. `close_check`: 1 passed; regresión guardián: 21 passed. Evidencia: `tasks/evidence/DEBT-GUARDIA-REPLAY-HISTORICO/`. Despliegue del servicio y del productor `bb sample` pendiente.
3. **Cerrada:** DEBT-GUARDIA-ARCHIVO-TARDIO. Reintenta archivos ausentes y detecta cambio de día, truncado y reemplazo sin replay de contenido previo. `close_check`: 1 passed; regresión del guardián: 22 passed. Evidencia: `tasks/evidence/DEBT-GUARDIA-ARCHIVO-TARDIO/`. Despliegue del servicio y del productor pendiente.
4. **Cerrada:** DEBT-WATCHDOG-PSI-ILEGIBLE-REARMA. PSI ilegible tras declarar colapso deja de enviar latidos; recuperación exige las dos lecturas bajas existentes. `close_check`: 1 passed. Suite: 26 passed, 2 `could_not_run` por bind Unix EPERM. Evidencia: `tasks/evidence/DEBT-WATCHDOG-PSI-ILEGIBLE-REARMA/`. Despliegue pendiente.
5. **Cerrada:** DEBT-TERMICA-PAUSAS-PERDIDAS. Estado durable por boot y starttime; intención previa a SIGSTOP permite conciliar caída entre señal y confirmación, y el enfriamiento reanuda tras validar identidad. `close_check`: 1 passed; suites térmicas: 122 passed. Evidencia: `tasks/evidence/DEBT-TERMICA-PAUSAS-PERDIDAS/`. Despliegue pendiente.
6. **Cerradas:** DEBT-SCAN-VENTANA-INCONSISTENTE y DEBT-SCAN-CNR-OMITE-ANALISIS. `bb scan` analiza únicamente JSONL dentro de la ventana, limita tasas al boot más reciente, y propaga datos inválidos, faltantes y errores de análisis a CNR. Ambos `close_check` pasaron con integración del CLI. Evidencia bajo `tasks/evidence/DEBT-SCAN-*`.
7. **Cerrada:** DEBT-SCAN-GPU-PROCESOS-FANTASMA. La lista vacía o inválida borra la caché; la ausencia de campo mantiene su distinción con TTL; idle no se llama fallback y la confirmación exige solicitudes activas más CPU positivo del mismo PID y boot. Sin correlación, `bb scan` imprime CNR. `close_check`: 1 passed; regresiones de cierre: 10 passed; suites térmicas: 121 passed. Evidencia: `tasks/evidence/DEBT-SCAN-GPU-PROCESOS-FANTASMA/`. Despliegue de `bb scan` y productor térmico pendiente.

## Ejecución Luna interrumpida

La primera ola de cuatro agentes Luna terminó por límite de uso: 0 cierres, 8 fichas abiertas y 8 resultados ausentes en triage merge. Se conserva el informe y el punto de reanudación en [SWARM-LUNA-2026-09-29](../tasks/evidence/SWARM-LUNA-2026-09-29/README.md). La suite inicial dio 475 passed, 30 failed, 4 skipped; requiere diagnóstico antes de certificar integración. Se detuvo según la regla de /0 para una ola con cero cierres.
