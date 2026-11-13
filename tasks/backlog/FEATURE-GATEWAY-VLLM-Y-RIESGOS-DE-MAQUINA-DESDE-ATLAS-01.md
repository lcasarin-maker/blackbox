---
id: FEATURE-GATEWAY-VLLM-Y-RIESGOS-DE-MAQUINA-DESDE-proyecto-local-01
kind: task
domain: INFERENCE
title: "Recibir de proyecto-local la unit y el main.py del gateway vLLM (voto D3) y los riesgos de maquina R1-R13 (voto D8)"
status: open
severity: P2
origin: asserted
created: 2026-11-10
close_check: {"expect": "exit_zero", "porque": "Se cierra cuando la copia de blackbox esta instalada, el motor responde y proyecto-local la verifica; la prueba es el codigo de salida del smoke del gateway instalado desde blackbox.", "cmd": "test -f tools/gateway/main.py && test -f tools/gateway/ai-nemotron.service"}
---

## Origen

Luis voto la frontera proyecto-local<->blackbox el 2026-11-10 (reign-in de proyecto-local). Verificado en
`~/projects/proyecto-local/docs/catalogo/VOTOS.md`: **D3** "Unit y main.py del gateway: a blackbox; proyecto-local
conserva active_engine.json" y **D8** "Riesgos R1-R13: partir por fila entre proyecto-local y blackbox"
(de maquina -> blackbox; de servicio -> proyecto-local). Ficha espejo en proyecto-local: DGX-766.
Pedido por la sesion "Reign-in de proyecto-local" (peer, no Luis); el voto es de Luis y consta en el archivo.

## Alcance D3

Archivos fuente: `~/projects/proyecto-local/deploy/ai-nemotron/{main.py (153 lineas), ai-nemotron.service,
admission_check_wrapper.sh, README.md, LEEME.md}`. Instalado hoy: `/srv/proyecto-local/gateway/`.
blackbox es PUBLICO: neutralizar antes de copiar (medido: 1 mencion de proyecto-local/proyecto-local en
main.py linea 7; 3 en la unit, incluidas las rutas `/srv/proyecto-local/gateway/...`).

## Reglas de la mudanza (sin sorpresas)

1. Copiar y neutralizar en `tools/gateway/`; NO reiniciar `ai-nemotron` ni tocar `/srv/proyecto-local/gateway`.
2. Instalar la unit desde blackbox solo en una ventana que Luis elija; antes, diff de la unit
   instalada contra la nueva y prueba del motor sano (`/health` 200, chat responde).
3. proyecto-local no borra su copia hasta que la de blackbox este instalada y verificada.
4. Rutas parametrizadas (variable de entorno o `EnvironmentFile`), no codificadas.

## Alcance D8

Tomar de la matriz R1-R13 las filas de maquina (memoria, energia, cuelgues) y fundirlas con
las fichas `DEBT-*` existentes; las filas de servicio se devuelven a proyecto-local.

## Funciones del inventario (EXTERNO:blackbox, 33)

Fuente: `proyecto-local/docs/catalogo/INVENTARIO_EXTERNO.md`. Incluye diagnostico de reloj y throttle de
la GPU, operacion del host y del motor y ~180 ideas del foro GB10 (detector "power-wedged",
drop_caches antes de cargar el modelo, gpu-memory-utilization como puerta, hold de kernel y
driver con punto de restauracion). Cada una se compara contra lo que blackbox ya tiene antes de
abrir trabajo nuevo.

## Pendiente de medir

Las 33 funciones aun no se han leido una por una; esta ficha registra el pedido, no su cierre.

## Cosecha de /clean (2026-11-13)

La rama local `codex/h3-gateway-receiver` conserva el contrato pendiente en
`bff519044561d4898107940436a0ab9e217b0da2`
(`wip(cosecha): conservar contrato pendiente del handoff del gateway`).
Contiene solo `tests/test_gateway_handoff.py`, cosechado sin modificar.

Comando: `python3 -m pytest -q -p no:cacheprovider tests/test_gateway_handoff.py`.
Salida: `8 failed in 0.08s`, codigo `1`: faltan el lanzador, la unit y el
adaptador de admision de `tools/gateway/`. La prueba detecta esa ausencia.

Por instruccion del coordinador, esta es la unica rama que se conserva a
proposito: queda sin aterrizar hasta implementar el alcance D3 de esta ficha.
El worktree secundario se retira despues de conservar el commit; el trabajo se
retoma creando un worktree de esa rama. /clean no implementa el gateway ni
modifica servicios instalados.
