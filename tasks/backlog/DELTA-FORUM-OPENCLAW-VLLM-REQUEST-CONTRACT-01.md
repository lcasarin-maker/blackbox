---
id: DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01
kind: task
domain: VERDICT
title: "Validar forum openclaw vllm request contract 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_openclaw_vllm_request_contract_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01.** En un DGX Spark con GPT-OSS-120B, OpenClaw devolvió 404 porque el nombre pedido no coincidía con el servido; `--served-model-name gpt-oss-120b` más el mismo ID del cliente corrigió esa fase. Después, una configuración OpenClaw con ventana declarada de 200K para GPT-OSS-120B generó `400 max_tokens ... got -17474`; la respuesta señala límite soportado de 131072 y recomendó no fijar un `maxTokens` estático de 8192 ([360299](https://forums.developer.nvidia.com/t/360299)). El autor reportó 200 OK tras el alias, y luego corrección de ventana/token config; no se auditó el adjunto ni el stack externo. Añadir a canary de compatibilidad un GET `/v1/models`, comparación de model ID servido/configurado, petición chat/completions de control que incluya function/tools si aplica y contexto declarado ≤límite de modelo. Rechazar config con presupuesto de generación calculado <1 antes de lanzar la sesión; almacenar solo códigos/metadata, nunca prompts. No convertir 131072 en límite universal: asociarlo al modelo/checkpoint. Cierre con tests negativos 404, contexto excedido y max_tokens negativo, más control que genera y llama herramienta correctamente.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: parcial, con preflight offline desarrollado para comparar una respuesta guardada GET `/v1/models`, modelo primario/configurado OpenClaw y límite explícitamente ligado al checkpoint. Calcula headroom a partir del cap configurado; presupuesto de una petición concreta permanece unknown sin conteo tokenizado/usage capturado y ligado a modelo/checkpoint. Las entradas se marcan `caller_supplied_unverified`. No hay captura local GET `/v1/models`, config OpenClaw ni token usage; no se lanzó petición. La ficha sigue abierta y el `close_check` original no cambió. Informe: `docs/evidence/BB-INSTRUMENTS-contracts.md`.
