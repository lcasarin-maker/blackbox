# bb-testigo: el testigo externo de la ATOM

Todo lo que vigila la ATOM corre dentro de ella, y cuando la ATOM se apaga de golpe se lleva consigo lo que estaba
anotando. El testigo es un programa pequeño que corre en **otro** equipo de la casa (Linux, macOS o Windows) y anota, con
la hora exacta, todo lo que la ATOM alcanza a decir y si sigue viva. Así, después de un corte, queda evidencia de qué pasó.

Es **un solo archivo**, `bb_testigo.py`, y no necesita instalar nada más que Python.

Qué anota, segundo a segundo:

- **Los últimos mensajes de la ATOM** (netconsole, el diario del sistema y la telemetría de la GPU) que llegan por la red
  al puerto UDP 6666.
- **Si la ATOM responde**: toca su puerto 22 cada segundo, y también hace `ping` si el equipo lo tiene.
- **Cuánta electricidad consume la ATOM**, si hay un enchufe con medidor (Shelly o Tasmota). Es opcional.
- **Su propio latido**, para saber si el que se apagó fue el testigo o la ATOM.

## Lo que necesitas

1. Un equipo que se quede **encendido** y conectado a la **misma red de casa** que la ATOM (mejor por cable).
2. **Python 3.8 o más nuevo** en ese equipo.
3. **La IP de la ATOM** en la red de casa. En este documento aparece como `<IP-DE-LA-ATOM>`: escribe la tuya en su lugar.
   Si la ATOM no arranca, búscala en la lista de equipos conectados de la página del router. Conviene reservarle esa IP
   en el router (reserva DHCP), y también la del equipo testigo.

## Paso 1. Python

- **Linux**: ya viene instalado. Compruébalo con `python3 --version`.
- **macOS**: abre la app **Terminal** y escribe `python3 --version`. Si no lo tienes, instálalo desde python.org.
- **Windows**: instálalo desde **python.org**. En la primera pantalla del instalador marca **«Add python.exe to PATH»**.
  No uses el Python de Microsoft Store, porque guarda los archivos en otra carpeta y el servicio no los encontraría.

## Paso 2. Copia el archivo

Copia `tools/testigo/bb_testigo.py` a la carpeta **Descargas** del equipo testigo. Puedes pasarlo por USB, por correo o
desde la página del repositorio: abre el archivo, pulsa «Raw» y luego «Guardar como».

## Paso 3. Instala, con el comando de tu sistema

Primero puedes ver lo que va a hacer sin que toque nada: añade `--dry-run` al final del comando. Cuando estés conforme,
córrelo sin `--dry-run`.

**Linux** (abre una Terminal):

```bash
cd ~/Descargas    # o ~/Downloads, según el idioma del sistema
python3 bb_testigo.py install --host <IP-DE-LA-ATOM>
```

El testigo queda como servicio de usuario de systemd y arranca solo al encender el equipo. Para que corra también cuando
nadie ha iniciado sesión, ejecuta una vez `loginctl enable-linger`. Si el equipo tiene cortafuegos, el instalador te
muestra el comando para abrir el puerto UDP 6666 (`ufw` o `firewalld`, los dos piden `sudo`).

**macOS** (abre la app Terminal):

```bash
cd ~/Downloads
python3 bb_testigo.py install --host <IP-DE-LA-ATOM>
```

El testigo queda como agente de launchd en `~/Library/LaunchAgents/local.bb-testigo.plist`. Si macOS pregunta si Python
puede aceptar conexiones entrantes o buscar dispositivos en la red local, responde **Permitir**.

**Windows** (en el menú Inicio busca «Terminal» o «PowerShell», haz clic derecho y elige **Ejecutar como administrador**):

```powershell
cd $env:USERPROFILE\Downloads
py bb_testigo.py install --host <IP-DE-LA-ATOM>
```

El instalador hace dos cosas. Crea una tarea programada, `bb-testigo`, que arranca al iniciar sesión, sin ventana, sin
límite de 72 horas y también con batería. Y añade una regla al firewall de Windows que deja entrar el UDP 6666. Las dos
**piden una terminal de administrador**: si la abriste normal, verás «Acceso denegado».

**WSL no sirve.** Si estás en Windows, no instales el testigo dentro de WSL2: su red no deja entrar los mensajes UDP que
manda la ATOM. Usa el Python normal de Windows, como se explica arriba. El instalador te avisa si detecta WSL.

### Con enchufe con medidor (opcional)

Conecta el enchufe **entre la pared y el adaptador de la ATOM**, reserva su IP en el router y añade dos opciones al
comando de instalación:

```bash
python3 bb_testigo.py install --host <IP-DE-LA-ATOM> --enchufe-tipo shelly2 --enchufe-url http://<IP-DEL-ENCHUFE>
```

El valor de `--enchufe-tipo` depende del enchufe: `shelly1` para un Shelly de primera generación (Plug, Plug S, 1PM),
`shelly2` para un Shelly Plus, Pro o de generación 3, y `tasmota` para un enchufe con Tasmota. Puedes añadir el enchufe más
tarde: vuelve a correr `install` con estas opciones y el testigo conserva lo que ya estaba configurado.

## Paso 4. Comprueba que funciona

Espera un minuto y corre el comando de tu sistema:

| Sistema | Comando                                                                         |
|---------|---------------------------------------------------------------------------------|
| Linux   | `python3 ~/.local/share/bb-testigo/bb_testigo.py status`                        |
| macOS   | `python3 ~/Library/Application\ Support/bb-testigo/bb_testigo.py status`        |
| Windows | `py "$env:LOCALAPPDATA\bb-testigo\bb_testigo.py" status`                        |

La última línea dice **VEREDICTO**, que puede ser uno de estos:

| Veredicto                   | Qué quiere decir                                                                            |
|-----------------------------|---------------------------------------------------------------------------------------------|
| `ATOM_RESPONDE`             | Todo bien: la ATOM contesta.                                                                |
| `ATOM_CALLADA`              | La ATOM dejó de contestar. Dice desde qué hora y, si hay enchufe, por qué.                  |
| `SIN_RESPUESTA_REGISTRADA`  | La ATOM no ha contestado ni una vez: está apagada o la IP está mal.                         |
| `TESTIGO_SIN_LATIDO`        | El testigo no está corriendo. Mientras siga así, no dice nada de la ATOM.                   |
| `RED_DEL_TESTIGO`           | El equipo testigo se quedó sin red. El problema es suyo, no de la ATOM.                     |
| `SONDEO_DETENIDO`           | El testigo late, pero dejó de tocar a la ATOM. Mira los errores que muestra `status`.       |

Cuando el veredicto es `ATOM_CALLADA`, la causa aparece al lado:

- `CORTE_ENERGIA`: la electricidad se fue antes de que la ATOM callara, o a la vez.
- `CUELGUE`: la ATOM siguió consumiendo pero no contestaba.
- `APAGADO_TRAS_SILENCIO`: primero se colgó y después se apagó o se reinició.
- `ENCHUFE_MUDO`: el enchufe calló a la vez que la ATOM. Lo más probable es que se fuera la luz de la pared, pero también
  puede ser el Wi-Fi del enchufe.
- `SIN_ENCHUFE` o `NO_CONCLUYENTE`: falta información para saber la causa.

## Paso 5. Que la ATOM le hable al testigo (cuando vuelva a arrancar)

El testigo escucha. Para que tenga qué escuchar, la ATOM tiene que mandarle sus mensajes a `<IP-DEL-TESTIGO>:6666`
(`<IP-DEL-TESTIGO>` es la IP del equipo donde instalaste el testigo):

- **netconsole** (los mensajes del kernel, hasta el último instante): en la ATOM,
  `sudo modprobe netconsole netconsole=@/<interfaz>,6666@<IP-DEL-TESTIGO>/`.
  Es el procedimiento de la ficha `FEATURE-FORUM-NETCONSOLE-01`.
- **journal-udp-forward**: el destino dentro de `/usr/local/bin/journal-udp-forward.sh` debe ser `<IP-DEL-TESTIGO>`.
- **Telemetría de la GPU**: `BLACKBOX_UDP_DESTINATION=<IP-DEL-TESTIGO>:6666`.

Mientras la ATOM no arranque, el testigo igual sirve: anota que no responde y cuánta electricidad consume.

## Cuando la ATOM se caiga

1. **No apagues ni desinstales el testigo.**
2. Corre `status` (paso 4) y guarda lo que muestra.
3. Copia **la carpeta de datos entera**: `~/.local/share/bb-testigo` en Linux, `~/Library/Application Support/bb-testigo`
   en macOS o `%LOCALAPPDATA%\bb-testigo` en Windows. Dentro están `netconsole.jsonl`, `ping.jsonl`, `energia.jsonl` y
   `latido.jsonl`, más sus rotaciones `.1`, `.2`, etc.

## Que el equipo no se duerma

Un equipo dormido no ve nada. Desactiva la suspensión mientras esté enchufado:

- **Windows**: Configuración, Sistema, Inicio/apagado y batería, «Al estar enchufado, suspender después de: Nunca».
- **macOS**: Ajustes del Sistema, Batería (o Ahorro de energía), «Evitar el reposo automático con la pantalla apagada».
- **Linux**: en la configuración de energía, suspensión automática apagada.

## Desinstalar

Usa el mismo comando de instalación cambiando `install` por `uninstall`: `python3 bb_testigo.py uninstall` (en Windows,
`py bb_testigo.py uninstall` desde una terminal de administrador). Se quitan el servicio, la tarea, la regla del firewall,
la copia del programa y la configuración. **Los datos se conservan**, porque son la evidencia. Para borrarlos también,
añade `--borrar-datos`. Lo mismo que con la instalación, `--dry-run` muestra lo que haría sin tocar nada.

## Lo que todavía no está verificado

- La instalación se probó de verdad solo en **Linux**. Lo que se genera para macOS (plist) y Windows (XML de la tarea,
  `schtasks`, `netsh`) está comprobado por pruebas, pero no en un Mac ni en un Windows de verdad. Tampoco se probó WSL.
- Los campos que se leen de Shelly y Tasmota salen de la documentación de cada fabricante. No se probaron con un
  enchufe real. Si un campo no viene, el testigo anota «sin lectura»; nunca inventa un cero.
- En Windows, `ping` y el puerto cerrado tardan más que en Linux: por eso el sondeo TCP espera 2 s.
- En macOS reciente, el permiso de «red local» puede bloquear el sondeo cuando el testigo corre como servicio. Si
  `status` muestra `inalcanzable` y desde la Terminal la ATOM sí responde, revisa Ajustes del Sistema, Privacidad y
  seguridad, Red local.

## Para quien programa

La configuración vive en `testigo.json`, dentro de la carpeta de datos. Tiene `atom_host`, `atom_puerto`, `udp_puerto`,
`sondeo_s`, `tcp_timeout_s`, `icmp`, `enchufe_tipo`, `enchufe_url`, `enchufe_s`, `latido_s`, `rota_mb` y `rota_copias`.
`BB_TESTIGO_DATA` cambia la carpeta de datos.

Cada línea de los `.jsonl` se escribe con `fsync`. `ping.jsonl` sigue el esquema de `externo/ping.jsonl` (`ts`, `epoch`,
`ok`), y `ok` significa lo mismo que ahí: «la ATOM contestó». Lleva dos campos más:

- `fuente`: `tcp` o `icmp`.
- `estado`: `abierto`, `rechazado`, `timeout`, `inalcanzable`, `sin_red`, `sin_nombre`, `eco` o `sin_eco`. En TCP,
  `rechazado` (un RST) cuenta como `ok`: el kernel de la ATOM está vivo aunque `sshd` no lo esté.

`energia.jsonl` sigue el esquema de `energia.jsonl` de `tools/medidor_energia.py`. La diferencia es que `voltaje_v` puede
ser `null`, porque los Shelly de primera generación no miden voltaje. Pruebas: `tests/test_testigo.py`.
