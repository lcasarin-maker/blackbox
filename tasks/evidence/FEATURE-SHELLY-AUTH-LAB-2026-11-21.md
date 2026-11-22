# Evidencia de laboratorio Shelly Digest SHA-256

Alcance: lectores `tools/medidor_energia.py` y `tools/testigo/bb_testigo.py`, sólo servidor HTTP sintético en loopback.
No se consultó dispositivo, configuración ni credencial real. La ficha `FEATURE-SHELLY-CON-CONTRASENA-Y-LECTORES-AUTENTICADOS-01`
permanece abierta para configurar la clave local, redesplegar y activar autenticación en otro momento.

## Verificación

Comando:

```sh
flock -x [RUTA_LOCAL_PRIVADA] python3 -m pytest -q tests/test_medidor_energia_auth.py tests/test_medidor_energia.py tests/test_testigo.py
```

Salida literal:

```text
........................................................                 [100%]
56 passed in 9.52s
```

Los controles negativos dentro de la prueba validan una contraseña incorrecta frente al digest calculado por el servidor,
un archivo de credenciales con permisos POSIX abiertos, JSON incompleto, una FIFO sin escritor (subproceso con timeout de 1 s),
un symlink a credenciales, un `uri` Digest discordante con el request target y un redirect cross-origin después del desafío. El redirect no llega al
segundo servidor. El control de compatibilidad deja a ambos lectores funcionando sin `auth_file`.

Comandos adicionales: `python3 tools/testigo/bb_testigo.py --help >/dev/null` y `git diff --check`; ambos terminaron con
código cero y sin salida. El testigo conserva su modo de script independiente y sólo usa biblioteca estándar.

## Límites de esta evidencia

- **could_not_run=1:** revisión de ACL NTFS en Windows no ejecutada en este host Linux. En Windows se documenta guardar el
  archivo bajo el perfil del usuario con ACL limitada a esa cuenta; el script stdlib no inspecciona ACL de Windows.
- La contraseña y activación del dispositivo, la prueba de red real y el despliegue están fuera de esta microfase.
- Control anterior corregido: el primer simulador sólo buscaba una cabecera `Authorization` y sus resultados RED no
  acreditaban el cálculo Digest. El simulador de esta evidencia verifica SHA-256, `qop=auth`, URI, realm y clave.
- Reproducción contra el SHA auditado `087dba588a5d18b34a46dc21b4d22acb597e6f52`: `carga_credenciales()` quedó bloqueada más
  de 1 s sobre FIFO 0600 sin escritor (`FIFO: TIMEOUT after 1s (reader blocked)`); el servidor de prueba respondió
  `URI mismatch verifier HTTP 200` ante `uri="/forged"`. Tras el arreglo, el test FIFO termina dentro del timeout con error
  de archivo no regular y el negativo de URI exige HTTP 401.
