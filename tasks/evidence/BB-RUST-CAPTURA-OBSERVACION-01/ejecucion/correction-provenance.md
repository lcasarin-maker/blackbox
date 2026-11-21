# Evidencia de corrección y procedencia

La línea base Python y los criterios de aceptación previos al prototipo Rust se conservan en `baseline_python.py`, `baseline-python.json` y `close-check.command.txt`, todos presentes desde el candidato `9698522abcae05534db84dc12be1ba432e8e8070`. Los umbrales continúan en p95 ≤ 25 ms y RSS ≤ 48 MiB. La comparación posterior y sus controles usan `comparison_negative.py`; el comando y recibo están en `comparison-negative.command.txt` y `correction-comparison-negative.txt`. El caso válido completo está en `correction-comparison.json`.

La receta anterior se conserva byte por byte como `comparison_negative_9698522.py`, extraída con:

```sh
git show 9698522abcae05534db84dc12be1ba432e8e8070:tasks/evidence/BB-RUST-CAPTURA-OBSERVACION-01/ejecucion/comparison_negative.py
```

SHA-256 de la copia: `cfc88f7d8f521fd94519dda6294e93308ef94bef34694e1a8cd52e3682e7a6aa`. Su recibo anterior se conserva en `comparison-negative-9698522.txt`. El control sustituto incluye invalidación de ambas métricas en ambos informes, límite válido excedido, pérdida de `seq=17` y alteración de campo con secuencias completas.

También se conserva `compare_rings_9698522.py` (SHA-256 `61b2fac6b993801fac0f9d05b39e0ab9dfde73848e90844e5139f20bb919e687`) para el control RED contra el comparador anterior. Con `latency_ms.p95=-1` y `peak_rss_mib=true` produjo `PASS`, `failures=[]`, rc=0 (`red-baseline-comparator.json` y `.rc.txt`). El capturador Rust compilado desde el mismo commit, con salida aislada bajo scratch, retornó rc=0 y escribió `ts` `[1e+308,null]` (`red-baseline-timestamp.json`). Un symlink de PSI a un archivo sintético exterior retornó rc=0 e incorporó `avg10=42.0` (`red-baseline-symlink.json`). Esos controles acreditan el defecto original; la versión corregida rechaza esos casos.

Los binarios y las pruebas viven en `~/scratch/blackbox/2026-11-21-captura-correccion-luna/`; los anillos de comparación final, en `~/scratch/blackbox/2026-11-21-captura-correccion-luna-final-4/`. No se usa `/tmp`, `TMPDIR` ni el checkout para binarios/anillos. En la aplicación, `BB_CAPTURE_SCRATCH` selecciona un subdirectorio ya existente bajo `~/scratch/blackbox`; las pruebas y el comparador usan ese mismo override y crean temporales con nombre exclusivo.

Las pruebas regresivas se añadieron tras el cambio inicial. Para demostrar RED sin tocar el checkout principal, se copió el test actual al scratch y se compiló el capturador de `9698522abcae05534db84dc12be1ba432e8e8070`; `red-test-timestamp.txt`, `red-test-marker.txt`, `red-test-psi.txt` y `red-test-scratch.txt` muestran la falla de cada caso en el código base. Esta secuencia acredita el comportamiento detectado, aunque no establece que las pruebas precedieron cronológicamente a la edición inicial.
