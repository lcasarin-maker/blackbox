---
id: FEATURE-METRICAS-LOG-Y-CORRELACION-CONSUMO-CARGA-01
kind: task
domain: HARDWARE
title: "Log alineado de métricas de la ATOM y correlación entre consumo eléctrico y carga"
status: done
severity: P2
origin: asserted
satd_family: MISSING_CAPABILITY
created: 2026-11-25
close_check: {"cmd": "python3 -m pytest -q tests/test_correlacion_consumo_carga.py", "expect": "exit_zero", "porque": "Mide que el log alineado y el informe de correlación existan y pasen su prueba. Hoy sale distinto de 0: el archivo de prueba no existe (medido 2026-11-25). Un pytest ausente cuenta como fallo, nunca como éxito. No mide que la correlación sea causal ni que los umbrales sean los correctos: lo revisa quien cierre."}
closed: 2026-11-26
closure_type: fixed
---

## Qué se quiere saber

Si el consumo eléctrico de la ATOM sigue a su carga, cuánto cuesta en watts cada tipo de carga y cuál es el consumo en reposo. Para eso hace falta un monitor y un log que pongan en la misma línea de tiempo lo que hoy vive en archivos separados.

## Qué hacer

1. **Log alineado.** Una fila cada 5 s (intervalo a votar) con, por instante: potencia, voltaje y corriente del enchufe; potencia, uso y relojes de la GPU; presión de CPU, memoria e io (PSI); `MemAvailable` y temperaturas por zona; y de la capa de inferencia, peticiones en curso y en espera, caché KV y tokens por segundo derivados. Campos como `NOT_COLLECTED` cuando falten, nunca cero.
2. **Presupuesto de disco declarado.** Con 5 s por fila y unos 300 bytes por fila, la estimación es del orden de 5 MB por día. La ficha fija una retención y compresión antes de activarlo. Dada la presión de disco (`FEATURE-ESPACIO-LIBRE-DE-DISCO-ATOM-Y-DELL-01`), el log no puede crecer sin tope.
3. **Informe de correlación**, a demanda y programado: por ventana, correlación de Pearson y de Spearman entre potencia del enchufe y cada métrica de carga, con barrido de desfase de ± algunos segundos, y n de muestras. Con muestras insuficientes declara `COULD_NOT_RUN` en lugar de un coeficiente.
4. **Consumo en reposo.** Línea base: potencia mínima sostenida con carga baja, con el criterio de «reposo» declarado. Vatios por encima de la línea base por unidad de carga y, cuando exista, vatios por mil tokens.
5. **Regímenes.** Separar reposo, carga de CPU, carga de GPU y mixta antes de correlacionar: un coeficiente global mezcla regímenes y engaña. Declarar variables de confusión conocidas (temperatura y ventiladores).
6. **Sin conclusiones causales.** El informe describe la asociación medida y el rango, no su causa.

## Dependencias

`FEATURE-ESTADO-EXTERNO-UN-SOLO-CANAL-01` (energía fresca en la ATOM) y `FEATURE-ENERGIA-ACUMULADA-DEL-ENCHUFE-01`. Reutiliza las muestras de `muestreo_1s.py`, `atom_gpu_telemetry.py` y `gpumem_historial.py` sin duplicar su captura. Los consumidores externos sólo leen el informe publicado, nunca el código de bb. El repo es público: el log y el informe no llevan datos personales.

## Control negativo exigido

Pruebas que fallan al mutar: dos series sin relación dan un coeficiente alto, una serie con una sola muestra da coeficiente, los regímenes se mezclan y el coeficiente cambia, un campo ausente entra como cero, el desfase se ignora y una correlación retardada se pierde.

## Cierre (2026-11-26)

Verificado `close_check` (`rc=0`):
- Comando: `python3 -m pytest -q tests/test_correlacion_consumo_carga.py`
- Salida literal: `..                                                                       [100%]
2 passed in 0.04s`
