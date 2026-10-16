---
id: FEATURE-1358-CGROUP-03-NATIVO
kind: task
domain: GPU
title: "Evaluar la contabilidad nativa de NVIDIA y dmem en GB10"
status: done
closed_at: 2026-10-16
closure_type: relocated_prior_verification
reason: "La pregunta (sirve la contabilidad nativa dmem de NVIDIA 615 en GB10?) se contesto sin ejecutar el 615: la fuente 615 exige modulos, GSP y espacio de usuario de la misma version (comparison.txt), asi que se hizo el backport reversible de memacct a 580.178.04, que esta cargado y medido (FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01)."
evidence: {"pass": "tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO.pass.txt", "fail": "tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO.fail.txt", "e2e": "tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO.e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "grep -q 268435456 tasks/evidence/FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01/medicion.txt", "expect": "exit_zero", "porque": "La verificacion se relocalizo a FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01 (voto de Luis 2026-10-16). Comprueba el marcador de su medicion; no re-ejecuta el experimento ni acredita la autenticidad del origen. Control negativo: el mismo grep contra un marcador inexistente da rc 1."}
---

## Contexto y dependencias

Plan derivado de [la corrección del README](../../README.md#a-measured-cgroup-accounting-gap-on-this-gb10-stack) y [el informe histórico corregido](../evidence/nvidia-1358-comment.md). Fuente de colaboración: [NVIDIA #1358](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358).

Dependencias: FEATURE-1358-CGROUP-01-REPRO, FEATURE-1358-CGROUP-02-TRAZA.

## Alcance

Evaluar la integración dmem y los cargos existentes en NVIDIA 615.71.09 frente a la pila 580 medida. Primero revisar compatibilidad GB10, kernel, GSP y espacio de usuario; una versión visible en el repositorio necesita validación de soporte. Preparar la comparación con versiones fijadas y retorno a la pila original antes de cualquier despliegue.

Reutilizar el arnés de 01. Comprobar registro de región, cargos por propietario, límites independientes de memory y dmem, rechazo controlado, liberación, compartición y dos cgroups. Distinguir asignación, residencia y migración para evitar doble cargo. Registrar operaciones no soportadas o no ejecutadas.

## Criterio de cierre

Informe comparativo respaldado por resultados reales del arnés y controles negativos: límite inferior a una asignación, segundo cgroup independiente y liberación. Demostrar el mecanismo que contiene cada API o delimitar el hueco que persiste. could_not_run debe imprimirse junto a los resultados; una evaluación incompleta conserva la ficha abierta. El despliegue del driver queda como acción separada que requiere autorización concreta.

El comando close_check queda especificado para su implementación con el trabajo. Hoy el verificador y sus evidencias están pendientes; esta ficha registra el plan, no resultados ejecutados. Debe rechazar evidencias ausentes y datos fabricados, y tener un control negativo que pruebe que detecta el defecto de su sujeto.

## Avance del swarm — 2026-10-02

Ejecutor: Luna; coordinación: Codex. Preparado: inspección de soporte, ABI e integración dmem.
Evidencia: `tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO/comparison.txt`.
Pendiente para cierre: driver 615 ejecutado con stack alineado; cargos, límites, compartición y liberación.
La ficha conserva status open; el informe distingue observaciones estáticas
y resultados runtime. El verificador de cierre permanece pendiente.

## Compatibilidad de compilación — 2026-10-02

NVIDIA 615.71.09 compiló contra headers 6.17.0-1032-nvidia (`make modules -j2`, rc0) dentro de scope limitado. Cinco módulos producidos, sin instalar/cargar. Metadatos, SHA256, advertencias y BTF omitido: `tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO/build-615.json` y `build-modules.json`. Los módulos locales carecen de firma; con Secure Boot activo el ensayo exige firma/trust y stack GSP/userspace alineado. La compilación deja pendiente runtime, límites, ownership y rollback, por lo que conserva open.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: La compilación de módulos pasó, pero runtime de driver 615, límites, ownership, cgroup independiente y liberación no se han probado.
- Evidencia faltante para cierre: runtime con stack alineado; cgroup secundario; caso bajo límite y negativo; liberación; firma/trust y rollback
- Siguiente acción: Ejecutar arnés runtime en lab con stack firmado/alineado y cgroup canary; comprobar límite, aislamiento/liberación y rollback sin instalar en host de producción.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/FEATURE-1358-CGROUP-03-NATIVO.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_08.json`, `tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO/build-615.json`, `tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO/build-modules.json`, `tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO/comparison.txt`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

Compara el driver 615.71.09 contra el 580.178.04 de este host; el modulo 615 compilo contra 6.17.0-1032-nvidia, pero FEATURE-DMEM-PREENROLAMIENTO-LISTA-01 indica que el parche dmem aplica a 580 y no a 615, y con Secure Boot exige firma. Cargar 615 en produccion es riesgoso.

Version para un solo nodo Gigabyte AI TOP ATOM: Reducir a informe estatico de compatibilidad 615 y rechazo documentado, sin cargar el driver; la contabilidad nativa se evalua con el modulo 580 parcheado (tools/dmem_*).

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Criterios ejecutables de `tools.verify_cgroup_plan` (2026-10-14)
Los criterios ejecutables de `tools.verify_cgroup_plan` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-CGROUP-PLAN-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.

## Avance 2026-10-14 (lote 'cierra las pendientes conforme a la opcion recomendada'): espera un disparador, no una decision
Disparador: cargar el driver 615 en un arranque de prueba (instalacion firmada para Secure Boot y reinicio, ambos de Luis), o en otro equipo GB10 de laboratorio. Hoy corre 580.178.04 con el modulo dmem parcheado; los modulos 615 compilados no se instalaron. Paso exacto tras ese arranque: el arnes de 01 con limite inferior a una asignacion, segundo cgroup y liberacion, y `python3 -m tools.verify_cgroup_plan --phase 03-nativo --evidence tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO`; rollback al 580.

## Root Cause
La ficha se abrio el 2026-10-02 como plan de un swarm (Luna/Codex): sus verificadores (`tools.verify_cgroup_plan --phase ...`) nunca recibieron capturas y daban `unknown`. Entre tanto el 2026-10-12 el modulo NVIDIA parcheado se cargo y se midio por otra ruta; la pregunta de esta ficha quedo contestada ahi. Leccion: un plan con verificador pendiente no es un cierre; esta ficha queda cerrada solo por la verificacion relocalizada de abajo.

## Regression Test
Ninguno propio: la verificacion vive en `FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01` (su close_check y su evidencia). El control negativo de arriba prueba que el comprobador distingue un marcador presente de uno ausente.

## Verification Evidence
- pass: `tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO.pass.txt`
- fail: `tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO.fail.txt`
- e2e: `tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO.e2e.txt`

## Limite declarado (cierre del 2026-10-16, voto de Luis)
El driver 615 nunca se ejecuto con la pila alineada: no se midio su cobro, ni sus limites independientes, ni la comparticion. Solo se evaluo por lectura de fuente y por compatibilidad. Si NVIDIA publica un 615 para GB10, la comparacion queda por hacer.
