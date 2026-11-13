# Configuracion local

Los archivos `.example` son sinteticos. Copiar fuera del repo y completar localmente.
WoL lee `BB_WOL_CONFIG` (JSON con mac y broadcast); los argumentos explicitos prevalecen.
El boton de emergencia lee `BB_ROJO_USUARIO` o `BB_ROJO_CONFIG` (por defecto `/etc/blackbox/rojo.json`).
La unit de muestreo lee `%h/.config/blackbox/muestreo.env` con `BB_MUESTREO_SCRIPT` absoluto.
La alarma ya lee `alarma.json` del directorio indicado por `--datos`; conservar esa configuracion privada.
Configurar los destinos antes de desplegar las copias nuevas; faltantes bloquean la ejecucion.
