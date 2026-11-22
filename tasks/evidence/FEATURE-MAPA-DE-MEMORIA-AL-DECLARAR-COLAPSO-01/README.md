# Evidencia de `FEATURE-MAPA-DE-MEMORIA-AL-DECLARAR-COLAPSO-01`

La salida completa con rutas locales se conserva en scratch privado del dueño. Los comandos versionados usan
`$HOME` como marcador y las salidas omiten rutas del checkout.

## Close check focal

```text
flock -x "$HOME/scratch/blackbox/2026-11-21-deuda-retoma-director/pruebas.lock" python3 -m pytest -q tests/test_mapa_memoria_colapso.py
............ [100%]
12 passed in 4.13s
rc=0
```

## Caracterización conjunta

```text
flock -x "$HOME/scratch/blackbox/2026-11-21-deuda-retoma-director/pruebas.lock" python3 -m pytest -q tests/test_mapa_memoria_colapso.py tests/test_bb_usable_caracterizacion.py
............................. [100%]
29 passed in 4.23s
rc=0
git diff --exit-code -- tests/fixtures/bb_usable_caracterizacion.json
fixture_diff_rc=0
```

## Control negativo semántico

El test genera una copia temporal de `bin/bb-usable`, quita la llamada del camino de declaración y conserva el helper.
Después invoca `reaccion_colapso` y verifica que falla la aserción que exige la publicación. Esa `AssertionError` queda
capturada por `pytest.raises`; el control pasa solo si el mutante deja ausente el efecto real.

```text
flock -x "$HOME/scratch/blackbox/2026-11-21-deuda-retoma-director/pruebas.lock" python3 -m pytest -q -vv tests/test_mapa_memoria_colapso.py::test_mutante_semantico_sin_llamada_falla_asercion_de_efecto
tests/test_mapa_memoria_colapso.py::test_mutante_semantico_sin_llamada_falla_asercion_de_efecto PASSED [100%]
1 passed in 0.05s
rc=0
```

## Aislamiento y casos

Las pruebas focales fijan `HOME`, `BLACKBOX_DATA`, `TMPDIR`, `CGROUP_ROOT` y `PROC_ROOT` bajo `tmp_path`; origen y
confinamiento están stubbeados. El arnés de caracterización también usa raíces sintéticas. Sus escenarios, aserciones
y el fixture golden permanecen intactos. No se leen `/proc`, cgroups ni configuración real.

La prueba de enumeración construye dos ramas falsas y hace fallar una en la frontera `_subdirectorios`; el capturador
recibe `None` y registra `NOT_COLLECTED`, sin cambiar permisos reales. Hay cobertura de declaración, transición tardía
desde confinamiento, recuperación con dos bajas, siguiente episodio, timeout, worker activo, cola saturada y `_anexar`
que escribe antes de fallar. La cola conserva como `NOT_COLLECTED` con timestamp original una captura contemporánea
imposible; nunca atribuye una lectura tardía al instante original. Fecha y timestamp salen de una llamada a
`time.localtime()` por declaración.

La cola admite cuatro recibos pendientes, no crea workers superpuestos y avisa si se satura. Un error de publicación
se informa sin reintento, ya que el append anterior pudo haber escrito.

La auditoría independiente Terra `9f459a67` aprobó el SHA `95828b0a8f56e1f7b33435e5acc363936b223ccf` con 12 close-check y 17 casos de caracterización. En este cierre local se repiten 12 pruebas focales y 29 pruebas combinadas.

Límites de runtime: el mapa cubre cgroups de `app.slice` y `dmem` cuando existe; memoria CUDA que no se cobra al cgroup queda fuera. Captura y append tienen plazo de un segundo. Si el worker anterior sigue activo, la nueva transición conserva un recibo `NOT_COLLECTED` con timestamp original en una cola de cuatro entradas; la saturación se anuncia y deja ese recibo sin persistir. Un error de append no se reintenta. El servicio no se desplegó y requiere reinicio de `bb-usable.service`.

Linaje local privado: `f9c3865897ce1cada021061e8c159ed0a83de62c`. No publicar ese commit ni su evidencia histórica.
