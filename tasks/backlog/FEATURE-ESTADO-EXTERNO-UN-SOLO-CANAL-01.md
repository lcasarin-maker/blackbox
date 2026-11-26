---
id: FEATURE-ESTADO-EXTERNO-UN-SOLO-CANAL-01
kind: task
domain: HARDWARE
title: "bb publica el estado del equipo testigo y del enchufe medidor en un solo archivo con sello de tiempo, y la ATOM lo trae cada 30 s"
status: open
severity: P2
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-25
close_check: {"cmd": "bash -c 'set -e; python3 -m pytest -q tests/test_estado_externo.py; find /run/bb-estado-externo/estado_externo.json -mmin -2 | grep -q .'", "expect": "exit_zero", "porque": "Mide las dos mitades del cierre: (1) la prueba del recolector y del esquema pasa y (2) el archivo publicado en la ATOM tiene menos de 2 minutos, es decir, el timer está instalado y corriendo. Hoy sale distinto de 0: `tests/test_estado_externo.py` no existe y `/run/bb-estado-externo/` no existe (medido 2026-11-25). Un pytest ausente cuenta como fallo, nunca como éxito. No mide el control negativo por mutación ni que los valores coincidan con el equipo testigo: los revisa quien cierre."}
---

## Decisión de Luis (2026-11-25)

bb se hace cargo de todas las mediciones del equipo testigo y del enchufe medidor. Los consumidores sólo leen lo que bb publica, por un solo canal. Esta ficha vive en bb y no en el repo de ningún consumidor.

## Medido (2026-11-25)

El equipo testigo mantiene vivos tres procesos (testigo, alarma y receptor de netconsole) y escribe series al segundo. Todos sus archivos tenían menos de 15 s de edad. En una ventana de 1,499 s hubo 1,500 de 1,500 sondeos ICMP y 1,500 de 1,500 sondeos TCP buenos, con RTT TCP de p50 15 ms y p95 16 ms. La alarma vio sus tres caminos (SSH por casa, SSH por Tailscale y escritorio remoto). El enchufe medidor entregó 3,001 de 3,001 lecturas buenas de potencia, voltaje y corriente.

Nada de eso llega a la ATOM con frescura:

1. **Copia vieja.** `externo/testigo/` en la ATOM se modificó por última vez el 2026-11-18, hace 7 días. `tools/observador_ping.py --trae-testigo` sólo corre a demanda desde `bb-reboot-verdict` y ninguna unidad `systemd` lo programa. No existe garantía de frescura.
2. **Traslado pesado.** Cada corrida copia `*.jsonl*` con los rotados: unos 260 MB. No sirve para consultar cada pocos segundos.
3. **La alarma no se trae.** `alarma.jsonl` vive fuera del directorio del testigo y el patrón de copia no lo cubre. El estado de los tres caminos no llega a la ATOM.
4. **Filas ICMP sin latencia.** Las filas `fuente: icmp` traen `ok` y no `rtt_ms`.
5. **Sin energía acumulada.** `tools/medidor_energia.py` y el lector del testigo leen potencia, voltaje y corriente. Ninguno agrega energía por día. bb no emite aviso por consumo: sólo lo usa para clasificar cortes con `ventana_de_corte`.
6. **Sin estado de procesos.** Nada publica si los tres procesos del equipo testigo siguen vivos más allá del latido del testigo.

## Qué hacer

0. **Primero, comparar lo que corre con lo que está en el repo (medido y registrado 2026-11-26).**
   - `tools/testigo/bb_testigo.py`: repo `a1c41fd7749461d3fb7051017bc852741ab7be437d4723461c227ea6909643f8` vs equipo testigo `a677e6baeff388f82f9d49bbd1bd5aab28feef8d1a09d7c179bd01cd37d6e1c7` (55,133 bytes, 2026-11-06). Diff posterior en repo (`2d1f92fd..HEAD`): `6541ea0a` (Digest SHA-256 para enchufe Shelly), `3522a4dc`/`d5bad497` (validación y parametrización sin IPs privadas), `68be422a` (guards de tipos pyright).
   - `tools/testigo/bb_alarma.py`: repo `f1740e1930ca2d061c9975d05f0cc58dc48bd315cd03e82c92b6c7c9ee268065` vs equipo testigo `94e39f1b57176b4ba8bbc9695c7c39c3fb777f930f1805dcd7b0f5f4886dd95e` (6,406 bytes, 2026-11-06).
   - `tools/testigo/bb_wol.py`: repo `8922de06008894ebd42414879174798fba5267cffaba77ba0307dde4311f33d4` vs equipo testigo `ef20aff7939c1663b1e81d7437a81931ab894ac41bd3290007fa31ae988170c2` (2,557 bytes, 2026-11-09).
   - `tools/estado_externo.py` incluye `medir_deriva_despliegue` para publicar la comparación SHA-256 y su edad en `bb-estado-externo/1`. El redespliegue al equipo testigo queda sujeto a autorización expresa de Luis.
1. **Archivo único `bb-estado-externo/1`.** El equipo testigo escribe, de forma atómica (`os.replace`), un archivo pequeño con: `ts` y `intervalo_s`; latido del testigo con su edad; vida del testigo, de la alarma y del receptor, cada uno con su propio latido; estado de los tres caminos de la alarma; edad y tamaño del log de netconsole; sondeos de la ventana de 5 minutos (porcentaje bueno, RTT p50 y p95 por TCP y por ICMP); y el enchufe (`ok`, potencia, voltaje, corriente, energía del día en Wh y `energia_fuente`).
2. **RTT en ICMP:** ficha propia, `FEATURE-TESTIGO-RTT-EN-FILAS-ICMP-01`. El archivo único publica ese RTT cuando exista.
3. **Energía acumulada:** ficha propia, `FEATURE-ENERGIA-ACUMULADA-DEL-ENCHUFE-01`. El archivo único publica sus Wh. Otras secciones del archivo con ficha propia: disco libre (`FEATURE-ESPACIO-LIBRE-DE-DISCO-ATOM-Y-DELL-01`) y Tailscale y RustDesk (`FEATURE-ESTADO-ENLACES-TAILSCALE-Y-RUSTDESK-01`).
4. **Traerlo cada 30 s.** Una unidad con timer en la ATOM copia sólo ese archivo, con la misma disciplina que `--trae-testigo` (`scp -s`, temporal hermano, `os.replace`) y lo publica en `/run/bb-estado-externo/estado_externo.json`, igual que `ultimo_aliento` publica `estado_maquina.json`. La copia forense pesada tiene su ficha: `FEATURE-TRAE-TESTIGO-INCREMENTAL-01`.
5. **Frescura declarada.** Si `ts` supera 3 veces `intervalo_s`, el archivo publicado lleva `vigente: false` y el motivo. Un campo que no se pudo medir sale `NOT_COLLECTED`, nunca cero. Esa es la doctrina de `estado_maquina.json` y de `DGX-383`.
6. **Contrato con consumidores.** El archivo es la interfaz. Ningún consumidor importa código de bb (contrato DGX-585). Cada consumidor lo lee por un único punto de contacto propio.

## Dependencias y límites

- Cambiar `bb_testigo.py` exige redesplegarlo en el equipo testigo, igual que el 2026-11-18. Eso modifica otro equipo: requiere orden expresa de Luis, con el motivo y el comando.
- `FEATURE-SHELLY-CON-CONTRASENA-Y-LECTORES-AUTENTICADOS-01` activa la contraseña del enchufe al último. Esta ficha se coordina con ella: el lector del contador de energía usa la misma autenticación cuando exista.
- `FEATURE-MEDIDOR-DE-ENERGIA-EXTERNO-01` y `FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01` siguen siendo las fichas de la medición para clasificar cortes. Esta ficha no las reemplaza: añade la publicación en vivo.
- Repo público: ni direcciones, ni usuarios, ni claves, ni rutas del equipo testigo en el archivo publicado ni en las pruebas.

## Control negativo exigido

Pruebas que fallan al mutar: un archivo de más de 3 intervalos aparece como `vigente: true`, un campo ausente sale como 0, un `os.replace` cortado deja el archivo a medias, un hueco en la energía se rellena con valores inventados, la alarma con un camino caído aparece completa. Registrar comando y salida literales. Todo texto saliente pasa por el filtro de secretos del repo.
