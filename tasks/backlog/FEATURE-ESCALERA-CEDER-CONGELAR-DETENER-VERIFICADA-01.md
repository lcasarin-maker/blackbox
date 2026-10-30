---
id: FEATURE-ESCALERA-CEDER-CONGELAR-DETENER-VERIFICADA-01
kind: task
domain: MEMORY
title: "Escalera ceder, congelar, detener con cada escalon verificado por la caida medida de memory.current (idea de ceder y recuperar de Athena's Engine, adaptada a un observador externo)"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "python3 -m pytest -q tests/test_escalera_ceder.py", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo de pruebas no existe hoy (rc=4 medido el 2026-10-30), asi que falla. Pasa solo cuando una unidad de laboratorio con tope de memoria recorra los tres escalones y la prueba demuestre que cada escalon escala solo si memory.current no cayo, con el control negativo de una unidad que cede al primer escalon y no se congela."}
---

## Idea de origen y por que no se copia tal cual

En Athena el guardian reparte por prioridad y el video "devuelve su memoria en su siguiente paso" cuando alguien mas importante la necesita; para video Full HD, Qwen puede prestar sus pesos mientras descansa y DeepSeek todavia no (`Atlas/knowledge/references/github_com_xangel82_Athena_Engine.md`). Funciona porque el guardian es DUENO de los servicios y ellos cooperan dentro del mismo proceso. bb es un observador externo.

Medido el 2026-10-30 con una unidad transitoria de 300 MiB (`systemd-run --user`, luego `systemctl --user freeze` y `stop`):

```
antes:     MemoryCurrent=318562304
congelada: MemoryCurrent=318562304 FreezerState=frozen
detenida:  MemoryCurrent=[not set] active=inactive
```

Congelar (lo unico que hace hoy el portero) no devuelve memoria; detener la devuelve y pierde el trabajo. Un arbitro que solo congela no cede nada.

## Adaptacion: escalera con verificacion

1. **Ceder**: la unidad que declara ser cooperante en `atlas-carga/1` (`$BLACKBOX_DATA/atlas_carga.json`) recibe la peticion por el canal que declare (archivo o senal) y descarga lo que pueda. Atlas pone la parte de declarar; el vinculo es de datos, sin importar codigo (`SPEC.md`, "Inventario de propiedad").
2. **Congelar** (`cgroup.freeze`): detiene el avance y NO libera memoria; solo sirve para ganar tiempo y para evitar que siga creciendo.
3. **Detener** (`systemctl --user stop`): libera y pierde el trabajo; solo para unidades elegibles segun rango (`FEATURE-ARBITRO-MEMORIA-UNIFICADA-POR-PRIORIDAD-01`) y nunca las de `data/procesos_protegidos.json`.

Regla central: cada escalon se da por logrado solo si `memory.current` de la unidad cayo en lo esperado dentro de su plazo; si no cayo, se escala. Un escalon sin medicion de su efecto no cuenta como cesion.

## Para cerrar

1. Calibrar plazos y caida minima con la unidad de laboratorio, no por intuicion; los valores quedan en el interruptor.
2. `tests/test_escalera_ceder.py` (bajo tope de memoria): recorre los tres escalones; (a) escala solo si no hubo caida; (b) negativo: una unidad que cede al primer escalon no se congela ni se detiene; (c) una protegida nunca llega al tercero.
3. Arranca en `observar` (registra "habria escalado"), como el resto de los interruptores.

## Limites declarados

Memoria fijada o gestionada de CUDA no se carga a cgroup (`FEATURE-1358-CGROUP-*`); ceder sobre ella no se mide con `memory.current`. Detener pierde trabajo y puede reiniciar solo si la unidad tiene `Restart=` (revisar por unidad antes de elegirla).
