"""Prepara un bundle rootless minimo (de `runc spec --rootless`) para el nivel 1.

uso: python3 l1_prep.py <bundle> <cgroupsPath> <modo>
modo: none | estricto | gpu | gpuok | gpuover | roto
El rootfs es casi vacio: /usr del host montado en solo lectura, bin y lib enlazados.
"""
import json
import sys
from pathlib import Path

b, cg, modo = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
r = b / "rootfs"
for d in ("usr", "proc", "dev", "tmp"):
    (r / d).mkdir(parents=True, exist_ok=True)
for n, t in (("bin", "usr/bin"), ("lib", "usr/lib")):
    if not (r / n).is_symlink():
        (r / n).symlink_to(t)
cfg = b / "config.json"
c = json.loads(cfg.read_text(encoding="utf-8"))
c["process"]["terminal"] = False
c["process"]["args"] = ["sleep", "20"]
c["root"]["readonly"] = True
c["mounts"].append({"destination": "/usr", "type": "bind", "source": "/usr", "options": ["rbind", "ro"]})
c["linux"]["cgroupsPath"] = cg
if modo == "estricto":
    c["linux"]["resources"] = {"memory": {"limit": 67108864, "swap": 67108864}, "pids": {"limit": 16}}
if modo in ("gpu", "gpuok", "gpuover"):
    c["process"]["env"].append("NVIDIA_VISIBLE_DEVICES=all")
if modo in ("gpuok", "gpuover"):
    c["annotations"] = {"bb.gpu_budget_gib": "36" if modo == "gpuok" else "60"}
texto = json.dumps(c, indent=1)
if modo == "roto":
    texto = '{"ociVersion": "1.2.1", "linux": '
cfg.write_text(texto, encoding="utf-8")
print("ok", b, modo)
