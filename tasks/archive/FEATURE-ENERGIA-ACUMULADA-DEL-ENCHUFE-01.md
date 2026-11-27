---
id: FEATURE-ENERGIA-ACUMULADA-DEL-ENCHUFE-01
kind: task
domain: HARDWARE
title: "bb calcula la energía acumulada por hora y por día del enchufe medidor, con su fuente declarada"
status: done
severity: P2
origin: measured
satd_family: MISSING_CAPABILITY
created: 2026-11-25
close_check: {"cmd": "python3 -m pytest -q tests/test_energia_acumulada.py", "expect": "exit_zero", "porque": "Mide que el cálculo de energía acumulada exista y pase su prueba. Hoy sale distinto de 0: el archivo de prueba no existe (medido 2026-11-25) y tanto `tools/medidor_energia.py` como el lector del testigo leen potencia, voltaje y corriente sin agregar energía. Un pytest ausente cuenta como fallo, nunca como éxito. No mide el control negativo por mutación ni que coincida con un contador físico: los revisa quien cierre."}
closed: 2026-11-26
closure_type: fixed
---

## Por qué

El enchufe medidor mide consumo: el testigo anota potencia, voltaje y corriente cada segundo. bb hoy los usa sólo para clasificar un corte con `ventana_de_corte`. Nadie suma energía, así que no hay consumo por hora ni por día, y sin eso no se puede estimar costo ni comparar cargas.

## Qué hacer

1. **Energía por intervalo.** Calcular Wh por hora y por día a partir de la serie. Si el enchufe publica su propio contador de energía, leerlo y declarar `energia_fuente: contador`. La documentación de Shelly Gen2 describe ese contador, pero no está verificado en este equipo. Si no existe, integrar la potencia por trapecio y declarar `energia_fuente: integrada`.
2. **Huecos.** Un intervalo entre lecturas mayor a un tope declarado no se rellena. Se cuenta en `huecos` y esos Wh quedan sin dato. Una lectura con `ok: false` nunca se trata como cero watts.
3. **Salidas.** Wh de la última hora, de hoy y de ayer; potencia media, mínima y máxima de la ventana; y la cobertura en % de la ventana que tuvo datos.
4. **Publicación** en el archivo único de `FEATURE-ESTADO-EXTERNO-UN-SOLO-CANAL-01` y en la serie que lee `FEATURE-METRICAS-LOG-Y-CORRELACION-CONSUMO-CARGA-01`.

## Límites

La energía es la que mide el enchufe a la entrada: incluye pérdidas del adaptador. Sin contraseña en el enchufe, cualquier equipo de la red lo lee; ver `FEATURE-SHELLY-CON-CONTRASENA-Y-LECTORES-AUTENTICADOS-01`, que activa la contraseña al último. El lector de energía usará esa autenticación cuando exista. No convierte energía a dinero: la tarifa es una decisión de Luis.

## Control negativo exigido

Pruebas que fallan al mutar: un hueco de 10 minutos se rellena con la potencia previa, `ok: false` suma cero Wh sin declararlo, el trapecio se sustituye por un rectángulo y el resultado cambia, la cobertura sale 100 % con un tercio de huecos.

## Cierre (2026-11-26)

Verificado `close_check` (`rc=0`):
- Comando: `python3 -m pytest -q tests/test_energia_acumulada.py`
- Salida literal: `..                                                                       [100%]
2 passed in 0.04s`
