from pathlib import Path
import json,subprocess
p=Path('tests/test_bb_wol.py');s=p.read_text().replace('"48:21:0b:95:41"','"02-00-00-00-00"').replace('"zz:21:0b:95:41:f1"','"zz-00-00-00-00-01"');s=s.replace('assert wol.paquete_magico("02-00-00-00-00-01") == wol.paquete_magico("02-00-00-00-00-01")','assert wol.paquete_magico("02-AB-00-00-00-01") == wol.paquete_magico("02" + ":ab:00:00:00:01")');p.write_text(s)
p=Path('.gitignore');p.write_text(p.read_text()+'\n# Configuracion operativa local: solo ejemplos versionados.\nconfig/*.json\nconfig/*.env\n')
Path('config/README.md').write_text('''# Configuracion local

Los archivos `.example` son sinteticos. Copiar fuera del repo y completar localmente.
WoL lee `BB_WOL_CONFIG` (JSON con mac y broadcast); los argumentos explicitos prevalecen.
El boton de emergencia lee `BB_ROJO_USUARIO` o `BB_ROJO_CONFIG` (por defecto `/etc/blackbox/rojo.json`).
La unit de muestreo lee `%h/.config/blackbox/muestreo.env` con `BB_MUESTREO_SCRIPT` absoluto.
La alarma ya lee `alarma.json` del directorio indicado por `--datos`; conservar esa configuracion privada.
Configurar los destinos antes de desplegar las copias nuevas; faltantes bloquean la ejecucion.
''')
