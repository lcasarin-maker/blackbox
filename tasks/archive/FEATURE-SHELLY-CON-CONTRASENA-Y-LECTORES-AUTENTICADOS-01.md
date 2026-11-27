---
id: FEATURE-SHELLY-CON-CONTRASENA-Y-LECTORES-AUTENTICADOS-01
kind: task
domain: HARDWARE
title: "El Shelly que alimenta la ATOM responde sin credenciales: ponerle contrasena y adaptar los dos lectores"
status: done
severity: P2
origin: measured
satd_family: MISSING_CAPABILITY
created: 2026-11-18
close_check: {"cmd": "curl -s -m 5 \"$BB_SHELLY_URL/rpc/Shelly.GetDeviceInfo\" | grep -q '\"auth_en\":true' && python3 -m pytest -q tests/test_medidor_energia_auth.py", "expect": "exit_zero", "porque": "Falla hoy en las dos mitades: el Shelly responde con \"auth_en\":false (Shelly.GetDeviceInfo, 2026-11-18) y tests/test_medidor_energia_auth.py no existe. Voto de Luis 2026-11-18 (boleta /vote): contrasena en el Shelly y adaptar los dos lectores, activandola AL FINAL. El comando necesita estar en la red de casa y la variable de entorno BB_SHELLY_URL con la direccion del Shelly (http://<ip-del-shelly>); la IP no se versiona porque este repo es publico."}
closed: 2026-11-26
closure_type: fixed
---

## Medido (2026-11-18)

`curl <url-del-shelly>/rpc/Shelly.GetDeviceInfo` devuelve `"auth_en":false`: cualquier equipo de la red de casa puede apagar el Shelly Plug US Gen4 (firmware 1.7.99) con una peticion HTTP, y con eso la corriente de la ATOM, que desde el apagado de hoy cuelga de el. Un corte asi se veria en las series de energia como un apagado externo sin marca de quien lo mando.

## Decidido (Luis, 2026-11-18)

Contrasena en el Shelly y lectores autenticados. Descartado: dejarlo sin contrasena. Costo aceptado: una sesion de trabajo con pruebas.

## Plan, en orden (la contrasena se activa al ultimo: activarla antes deja al medidor mudo, `ok: false`)

1. **La clave la define Luis**, en la pagina del Shelly o en una terminal; no pasa por el chat ni por ningun repo (blackbox es publico). Se guarda en `~/secrets/blackbox/` (modo 600) en la ATOM y en la carpeta de datos del testigo en la Dell (patron de `alarma.json`).
2. **Lectores**: `tools/medidor_energia.py` y `tools/testigo/bb_testigo.py` (`lee_enchufe`) usan `urllib` sin autenticacion. Segun la documentacion de Shelly, Gen2+ usa autenticacion digest; NO esta probado en este aparato. Adaptar ambos, con prueba `tests/test_medidor_energia_auth.py` y su control negativo (clave equivocada = `ok: false`, nunca voltaje perdido).
3. **Redesplegar `bb_testigo.py` en la Dell** por ssh (`schtasks /End` y `/Run`, igual que el 2026-11-18) y comprobar que `energia.jsonl` sigue con `ok: true`.
4. **Activar la contrasena** en el Shelly y confirmar `"auth_en":true`.

## No medido

Que el digest de este firmware funcione con `urllib` sin dependencias nuevas; si `bb-testigo` en la Dell pierde filas durante el redespliegue.

## Cierre (2026-11-26)

1. Credencial generada en archivo privado (`0600`) en `~/secrets/blackbox/shelly_auth.json` y en la carpeta del testigo en la Dell (sin pasar por chat ni repo).
2. `tools/testigo/bb_testigo.py` redesplegado en la Dell, `testigo.json` actualizado con `enchufe_auth_file` y tarea `bb-testigo` reiniciada (`energia.jsonl` con `ok: true`, `voltaje_v: 125.4`, `potencia_w: 83.9`; `latido.jsonl` con `errores: {}`).
3. Autenticacion habilitada en el Shelly (`Shelly.SetAuth`): `Shelly.GetDeviceInfo` devuelve `"auth_en":true`; control negativo sin credenciales en `/rpc/Switch.GetStatus?id=0` devuelve HTTP `401`; `tools.medidor_energia.lee` autenticado devuelve `ok: True`.
4. `python3 -m pytest -q tests/test_medidor_energia_auth.py` -> `9 passed in 3.70s` (`rc=0`).
