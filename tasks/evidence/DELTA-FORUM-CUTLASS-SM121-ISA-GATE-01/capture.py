#!/usr/bin/env python3
"""Recorder for DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01.

Runs each command for real and appends {argv, exit, stdout, stderr, captured_at, phase}
to commands.json. No outcome flag is written; the verifier recomputes everything.
The only derived artifact is canary.json, produced by this script from the real
canary binary's stdout (BB_LOGITS / BB_REFERENCE lines, iteration count, GPU-loop time).
"""
import hashlib, json, os, re, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

EV = Path(__file__).resolve().parent
LAB = Path(os.path.expanduser("~" + os.environ.get("SUDO_USER", ""))) / ".cache" / "bb-trabajo" / "cutlass-lab"  # under sudo, ~ is /root
SRC, CAN = LAB / "cutlass", LAB / "canary"
BUILD = LAB / "canary-build"
REV = "098de2a652cf8f00fd70b2df54051c7eccbb855a"  # v4.8.0
NVCC = "/usr/local/cuda/bin/nvcc"
ITER = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
rows = []


def run(argv, phase=None, cwd=None, timeout=3600):
    p = subprocess.run(argv, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    row = {"argv": argv, "exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr,
           "captured_at": datetime.now(timezone.utc).isoformat()}
    if phase:
        row["phase"] = phase
    rows.append(row)
    return row


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


plan = {"cutlass_revision": REV, "cute_revision": REV, "backend": "cutlass3x_sm120_collective_builder",
        "operation": "nvfp4_bf16_blockscaled_gemm", "model_sha256": sha(CAN / "canary79a.cu"),
        "input_sha256": hashlib.sha256(b"m=n=k=1024 seed=CUTLASS-example-79a-default L=1 alpha=1 beta=0").hexdigest(),
        "batch_size": 1, "concurrency": 1, "soak_seconds": 20, "reference_max_abs_error": 0.0}
(EV / "experiment-plan.json").write_text(json.dumps(plan), encoding="utf-8")
run(["cat", str(EV / "experiment-plan.json")])
run(["uname", "-r"])
run(["dmidecode", "-t", "system"])
run(["nvidia-smi", "--query-gpu=name,compute_cap,driver_version", "--format=csv,noheader"])
run(["git", "-C", str(SRC), "rev-parse", "HEAD"], phase="pin")
run([NVCC, "--version"], phase="toolchain")
run(["rm", "-rf", str(BUILD)])
run(["cmake", "-G", "Ninja", "-S", str(CAN), "-B", str(BUILD), f"-DBB_REV={REV}",
     f"-DCMAKE_CUDA_COMPILER={NVCC}", "-DCMAKE_BUILD_TYPE=Release"], phase="configure")
b = run(["cmake", "--build", str(BUILD), "--", "-v"], phase="build")
exe = BUILD / "canary79a"
run([NVCC.replace("nvcc", "cuobjdump"), "--list-elf", str(exe)])
# canary: one verified GEMM + ITER timed iterations on the real GPU
t0 = time.time()
r = run([str(exe), "--m=1024", "--n=1024", "--k=1024", f"--iterations={ITER}"], phase="canary_run")
wall = time.time() - t0
out = r["stdout"]
lg = next(l for l in out.splitlines() if l.startswith("BB_LOGITS")).split()[1:]
rf = next(l for l in out.splitlines() if l.startswith("BB_REFERENCE")).split()[1:]
m_avg = re.search(r"Avg runtime: ([0-9.eE+-]+) ms", out)
assert m_avg is not None, "la salida del canario no trae Avg runtime"
avg = float(m_avg.group(1))
disp = "Disposition: Passed" in out
completed = ITER if (r["exit"] == 0 and disp) else 0
canary = {"requests": ITER, "completed": completed, "batch_size": 1, "concurrency": 1,
          "duration_seconds": avg * ITER / 1000.0, "wall_seconds": wall,
          "logits": [float(x) for x in lg], "reference_logits": [float(x) for x in rf]}
(EV / "canary.json").write_text(json.dumps(canary), encoding="utf-8")
run(["cat", str(EV / "canary.json")], phase="canary")
# ISA negative control (+ positive control for the same instrument)
(LAB / "isa").mkdir(exist_ok=True)
(LAB / "isa" / "ok.cu").write_text('__global__ void k(){}\nint main(){return 0;}\n', encoding="utf-8")
(LAB / "isa" / "mala_tcgen05.cu").write_text(
    '__global__ void k(){ asm volatile("tcgen05.fence::before_thread_sync;"); }\nint main(){return 0;}\n', encoding="utf-8")
run([NVCC, "-arch=sm_121", "-cubin", "-o", str(LAB / "isa" / "ok.cubin"), str(LAB / "isa" / "ok.cu")], phase="negative_positive_control")
run([NVCC, "-arch=sm_121", "-cubin", "-o", str(LAB / "isa" / "mala.cubin"), str(LAB / "isa" / "mala_tcgen05.cu")], phase="negative")
(EV / "commands.json").write_text(json.dumps({"schema": 1, "id": "DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01",
                                               "experiment_plan": plan, "commands": rows}, indent=1), encoding="utf-8")
print("rows", len(rows), "build exit", b["exit"], "canary", {k: canary[k] for k in ("requests", "completed", "duration_seconds", "wall_seconds")})
