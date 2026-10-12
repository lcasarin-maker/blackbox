"""Anula cada rama de tools/bb_oci_runtime.py y comprueba que su test cae.

uso: python3 mutar.py <repo>
Restaura el fichero original pase lo que pase (finally).
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
MOD = REPO / "tools" / "bb_oci_runtime.py"
TEST = "tests/test_bb_oci_runtime.py"

M = [
    ("M01 rechazo GPU sin reclamo anulado", "        if error:\n            return {**base, \"decision\": \"RECHAZAR\"",
     "        if False:\n            return {**base, \"decision\": \"RECHAZAR\"", "gpu_sin_etiqueta"),
    ("M02 rechazo por suma anulado", "if otros + gib > suelo_gib:", "if False:", "suma_desbordada"),
    ("M03 deteccion de GPU ignorada en decidir", "    if gpu:\n        gib, error", "    if False:\n        gib, error", "gpu_sin_etiqueta"),
    ("M04 inyeccion de memory.limit anulada", "    if not _positivo(memoria.get(\"limit\")):", "    if False:", "dorado"),
    ("M05 inyeccion de swap anulada", "    if not _positivo(memoria.get(\"swap\")):", "    if False:", "dorado"),
    ("M06 inyeccion de pids anulada", "    if not _positivo(pids.get(\"limit\")):", "    if False:", "dorado"),
    ("M07 pisa el limite declarado", "    if not _positivo(memoria.get(\"limit\")):", "    if True:", "mas_estricto"),
    ("M08 spec ilegible deja de registrarse NOT_COLLECTED", "    if error:\n        return {**fila, \"decision\": \"NO_ACTUAR\"",
     "    if False:\n        return {**fila, \"decision\": \"NO_ACTUAR\"", "ilegible"),
    ("M09 rechazo no corta la ejecucion", "if fila[\"decision\"] == \"RECHAZAR\":", "if False:", "rechazo_no_llama"),
    ("M10 recrear el mismo id cuenta doble", "if k != contenedor)", "if True)", "recrear"),
    ("M11 delete no libera", "            vivos.pop(cid, None)", "            pass", "repliega"),
    ("M12 registro roto bloquea la politica", "        _avisa(f\"registro no disponible ({e}); se sigue sin historia\")\n        return None",
     "        raise", "inservible"),
    ("M13 NVIDIA_VISIBLE_DEVICES=void cuenta como GPU", "valor.strip().lower() not in GPU_ENV_VACIO", "valor.strip().lower() in GPU_ENV_VACIO", "sin_gpu or gpu_sin_etiqueta"),
    ("M14 suelo exclusivo (>=)", "if otros + gib > suelo_gib:", "if otros + gib >= suelo_gib:", "justo_en_el_suelo"),
    ("M15 el spec corregido no se escribe", "    if d[\"spec\"] is not None:\n        _escribe_spec", "    if False:\n        _escribe_spec", "corrige_y_delega"),
    ("M16 GPU por dispositivo ignorada", "        if str((dev or {}).get(\"path\", \"\")).startswith(\"/dev/nvidia\"):", "        if False:", "dispositivo_o_hook"),
    ("M17 GPU por hook ignorada", "            if \"nvidia-container\" in str((h or {}).get(\"path\", \"\")):", "            if False:", "dispositivo_o_hook"),
    ("M18 reclamo ilegible aceptado", "    if not gib > 0 or gib == float(\"inf\"):", "    if False:", "etiqueta_ilegible"),
]

orig = MOD.read_text(encoding="utf-8")
vivos = 0
try:
    for nombre, viejo, nuevo, k in M:
        n = orig.count(viejo)
        if n != 1:
            print(f"{nombre}: COULD_NOT_RUN (el texto a mutar aparece {n} veces)")
            vivos += 1
            continue
        MOD.write_text(orig.replace(viejo, nuevo), encoding="utf-8")
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", TEST, "-k", k],
                           cwd=REPO, capture_output=True, text=True, timeout=300)
        ult = (r.stdout.strip().splitlines() or ["(sin salida)"])[-1]
        veredicto = "MUERTO" if r.returncode != 0 else "VIVO"
        vivos += veredicto == "VIVO"
        print(f"{nombre}: {veredicto} (-k {k!r}: {ult})")
finally:
    MOD.write_text(orig, encoding="utf-8")
print(f"mutantes vivos o sin correr: {vivos} de {len(M)}")
sys.exit(1 if vivos else 0)
