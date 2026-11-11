---
id: FEATURE-GATEWAY-VLLM-Y-RIESGOS-DE-MAQUINA-DESDE-ATLAS-01
kind: task
domain: INFERENCE
title: "Recibir de Atlas la unit y el main.py del gateway vLLM (voto D3) y los riesgos de maquina R1-R13 (voto D8)"
status: open
severity: P2
origin: asserted
created: 2026-11-10
close_check: {"expect": "exit_zero", "porque": "Se cierra cuando la copia de blackbox esta instalada, el motor responde y Atlas la verifica; la prueba es el codigo de salida del smoke del gateway instalado desde blackbox.", "cmd": "test -f tools/gateway/main.py && test -f tools/gateway/ai-nemotron.service"}
---

## Origen

Luis voto la frontera Atlas<->blackbox el 2026-11-10 (reign-in de Atlas). Verificado en
`~/projects/Atlas/docs/catalogo/VOTOS.md`: **D3** "Unit y main.py del gateway: a blackbox; Atlas
conserva active_engine.json" y **D8** "Riesgos R1-R13: partir por fila entre Aequitas y blackbox"
(de maquina -> blackbox; de servicio -> Aequitas). Ficha espejo en Atlas: DGX-766.
Pedido por la sesion "Reign-in de Atlas" (peer, no Luis); el voto es de Luis y consta en el archivo.

## Alcance D3

Archivos fuente: `~/projects/Atlas/deploy/ai-nemotron/{main.py (153 lineas), ai-nemotron.service,
admission_check_wrapper.sh, README.md, LEEME.md}`. Instalado hoy: `/srv/Atlas/gateway/`.
blackbox es PUBLICO: neutralizar antes de copiar (medido: 1 mencion de Atlas/Aequitas en
main.py linea 7; 3 en la unit, incluidas las rutas `/srv/Atlas/gateway/...`).

## Reglas de la mudanza (sin sorpresas)

1. Copiar y neutralizar en `tools/gateway/`; NO reiniciar `ai-nemotron` ni tocar `/srv/Atlas/gateway`.
2. Instalar la unit desde blackbox solo en una ventana que Luis elija; antes, diff de la unit
   instalada contra la nueva y prueba del motor sano (`/health` 200, chat responde).
3. Atlas no borra su copia hasta que la de blackbox este instalada y verificada.
4. Rutas parametrizadas (variable de entorno o `EnvironmentFile`), no codificadas.

## Alcance D8

Tomar de la matriz R1-R13 las filas de maquina (memoria, energia, cuelgues) y fundirlas con
las fichas `DEBT-*` existentes; las filas de servicio se devuelven a Aequitas.

## Funciones del inventario (EXTERNO:blackbox, 33)

Fuente: `Atlas/docs/catalogo/INVENTARIO_EXTERNO.md`. Incluye diagnostico de reloj y throttle de
la GPU, operacion del host y del motor y ~180 ideas del foro GB10 (detector "power-wedged",
drop_caches antes de cargar el modelo, gpu-memory-utilization como puerta, hold de kernel y
driver con punto de restauracion). Cada una se compara contra lo que blackbox ya tiene antes de
abrir trabajo nuevo.

## Pendiente de medir

Las 33 funciones aun no se han leido una por una; esta ficha registra el pedido, no su cierre.
