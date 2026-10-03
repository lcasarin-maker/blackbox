# Revisión de la nota Atlas sobre potencia GB10 — 2026-10-03

Se incorpora la revisión en la ficha abierta FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION, que ya contiene BB-POWER-TELEMETRY-BOUNDARY. El hallazgo del modelo local se trata como propuesta. La validación automática de seis citas no acredita comparabilidad física, aritmética ni causalidad.

## Magnitudes contrastadas

| Valor | Magnitud y sujeto | Fuente primaria y condición |
|---|---|---|
| 140 W | TDP del SoC GB10 | [NVIDIA, requisitos de potencia](https://docs.nvidia.com/dgx/dgx-spark/hardware.html#power-requirements), también sección 2.3.5.1 de la guía preservada en Atlas |
| 240 W | Potencia nominal de la fuente externa incluida de DGX Spark | Misma guía; presupuesto declarado de 100 W disponible para otros componentes |
| 233,2 W | Maximum Power declarado para DGX Spark modelo P4242 | [NVIDIA, información regulatoria](https://docs.nvidia.com/dgx/dgx-spark/compliance.html#commission-regulation-eu-no-617-2013-technical-information), metodología IEC 62623/EN 62623, 230 V/50 Hz |
| ~164 W | Medición atribuida a Level1Techs en otra síntesis local | Instrumento, punto de medición, integración temporal y carga completa pendientes de comprobar; no se usa para atribuir potencia del SoC |

Los 100 W disponibles son un presupuesto publicado, no consumo observado simultáneo de los auxiliares. Los 233,2 W corresponden al modelo y ensayo declarados; no se extrapolan a AI TOP ATOM, ASUS GX10 o MSI sin documentación y medición OEM propia.

## Inferencias rechazadas

1. 233,2−140=93,2 W es aritmética correcta sobre magnitudes distintas. Para atribuir auxiliares hacen falta potencia real del SoC y potencia del conjunto medidas simultáneamente, con puntos AC/DC, pérdidas e intervalos identificados. El TDP no proporciona esa lectura. Los 93,2 W quedan sin atribución física.
2. 240−140−100=0 W. Los 36 W de reserva de la nota son un error aritmético. Tampoco se acredita margen eléctrico restando potencia nominal de salida de la fuente y un dato de un ensayo de sistema con otro punto de medición.
3. ~164 W del equipo completo no prueba que el SoC exceda 140 W. La procedencia y frontera de esa lectura siguen desconocidas. El mismo problema impide atribuir diferencias a firmware a partir de cifras de foro aisladas.

Comando ejecutado:

```python
from decimal import Decimal
print('233.2 - 140 =', Decimal('233.2') - Decimal('140'))
print('240 - 140 - 100 =', Decimal('240') - Decimal('140') - Decimal('100'))
print('164 - 140 =', Decimal('164') - Decimal('140'),
      ' (arithmetic only; measurement boundary unverified)')
```

Salida literal:

```
233.2 - 140 = 93.2
240 - 140 - 100 = 0
164 - 140 = 24  (arithmetic only; measurement boundary unverified)
```

## Aplicación a Blackbox y límites

Mantener diferenciadas especificaciones, límites configurados y observaciones. Las muestras deben identificar fuente/contador, dominio GPU/SoC/sistema, punto AC/DC, unidades, timestamp/intervalo, OEM y workload. Si un dato no está expuesto, registrar unknown/could_not_run. El power.draw de nvidia-smi permanece como lectura reportada por NVIDIA; su captura no sustituye un medidor del sistema ni demuestra margen del adaptador. No convertir estas cifras en umbrales de admisión o mitigación.

Documentación y aritmética contrastadas; ensayo eléctrico local realizado: 0; validación de la medición externa de ~164 W: could_not_run=1 (registro primario e instrumento ausentes). El acceso web al hilo 349668 devolvió error; el PDF oficial superó el límite de lectura de la herramienta (14862482 bytes), por lo que se contrastaron HTML/búsqueda de NVIDIA y el texto preservado de la guía. Esos límites se conservan explícitos. La ficha mantiene status open y su close_check original: este documento no valida un canario ni cierra la investigación.

## Procedencia

Documento de entrada recibido desde Atlas, sin modificar el original:

`/home/lcasarin/projects/Atlas/knowledge/investigations/2026-10-03_tdp_gb10_140w_soc_vs_233_2w_sistema_completo_conexi_n_verificada_entre_especific.md`

SHA-256 del contenido leído: `34af980bd22333c62cc3f589e127b831a507224d525e4f031cb5c9826096b9f3`.

Fuentes locales auxiliares: knowledge/hardware/dgx_spark_user_guide.md, líneas 454–457; knowledge/investigations/2026-07-31_dgx_spark_electrical_consumption_and_cooling_specifications.md, líneas 59–68. Ambas están bajo /home/lcasarin/projects/Atlas. La síntesis anterior contiene la misma inferencia de 36 W; su repetición no constituye confirmación independiente.
