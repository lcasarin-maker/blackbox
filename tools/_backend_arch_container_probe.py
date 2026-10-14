"""In-container, GPU-less, read-only probe. Piped to `python3 -` by tools.backend_arch_manifest.

Runs cuobjdump / ptxas --help / torch introspection and prints ONE JSON document:
{"commands": [{"argv","exit_code","stdout","stderr", "stdout_truncated"?}], "families": [...]}.
Stdlib only. Every arch value in the document is parsed from command output; none is typed here.
"""
import hashlib
import json
import os
import re
import site
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

SP = site.getsitepackages()[0]
CUOBJDUMP = "/usr/local/cuda/bin/cuobjdump"
RAW_LIMIT = 20000  # bytes of stdout kept verbatim per command; the rest is summarised by sha256
ARCH = re.compile(r"\.(sm|compute)_(\d+[af]?)\.(cubin|ptx)\b")
COMMANDS = []


def run(argv, keep=True):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=900)
        row = {"argv": argv, "exit_code": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
    except (OSError, subprocess.SubprocessError) as exc:
        row = {"argv": argv, "exit_code": -1, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}
    if keep:
        shown = dict(row)
        if len(row["stdout"]) > RAW_LIMIT:
            shown["stdout"] = row["stdout"][:RAW_LIMIT]
            shown["stdout_truncated"] = {"total_bytes": len(row["stdout"]),
                                         "sha256": hashlib.sha256(row["stdout"].encode()).hexdigest()}
        COMMANDS.append(shown)
    return row


def archs(text):
    elf, ptx = set(), set()
    for line in text.splitlines():
        m = ARCH.search(line)
        if not m:
            continue
        (elf if m.group(3) == "cubin" else ptx).add(m.group(2))
    return elf, ptx


def listing(path, keep):
    """cuobjdump --list-elf and --list-ptx on one file -> parsed arch sets plus the two rcs."""
    e = run([CUOBJDUMP, "--list-elf", path], keep)
    p = run([CUOBJDUMP, "--list-ptx", path], keep)
    elf, _ = archs(e["stdout"])
    _, ptx = archs(p["stdout"])
    def state(row):
        if row["exit_code"] == 0:
            return "ok"
        if "does not contain device code" in row["stdout"] + row["stderr"]:
            return "no_device_code"
        return "error"
    return {"path": path, "elf": sorted(elf), "ptx": sorted(ptx), "rc_elf": e["exit_code"], "rc_ptx": p["exit_code"],
            "state": "error" if "error" in (state(e), state(p)) else
                     "no_device_code" if "no_device_code" in (state(e), state(p)) else "ok"}


def walk(root, suffixes):
    out = []
    for dp, _, fs in os.walk(os.path.join(SP, root)):
        for f in fs:
            if f.endswith(suffixes) or (".so." in f and ".so" in suffixes):
                out.append(os.path.join(dp, f))
    return sorted(out)


def family(name, paths, keep, aggregate_only=False):
    if aggregate_only:
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(lambda p: listing(p, False), paths))
    else:
        rows = [listing(p, keep) for p in paths]
    union_elf = sorted({a for r in rows for a in r["elf"]})
    union_ptx = sorted({a for r in rows for a in r["ptx"]})
    combos = {}
    for r in rows:
        key = "elf=" + ",".join(r["elf"]) + ";ptx=" + ",".join(r["ptx"])
        combos[key] = combos.get(key, 0) + 1
    return {"family": name, "files": len(rows), "elf": union_elf, "ptx": union_ptx,
            "combos": combos, "errors": sum(1 for r in rows if r["state"] == "error"),
            "no_device_code": sum(1 for r in rows if r["state"] == "no_device_code"),
            "per_file": None if aggregate_only else rows,
            "listing_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()}


def main():
    families = []
    run([CUOBJDUMP, "--version"])
    run(["/usr/local/cuda/bin/nvcc", "--version"])
    run(["python3", "-c",
         "import vllm,torch;print(vllm.__version__,torch.__version__,torch.version.cuda,torch.cuda.get_arch_list())"])
    run(["env"], keep=False)
    for ptxas in ("/usr/local/cuda/bin/ptxas",
                  os.path.join(SP, "triton/backends/nvidia/bin/ptxas")):
        run([ptxas, "--version"])
        run([ptxas, "--help"])
    families.append(family("vllm_native_extensions", walk("vllm", (".so",)), True))
    torch_libs = [p for p in walk("torch/lib", (".so",)) if re.search(r"libtorch_cuda|libc10_cuda|libcaffe2_nvrtc|libtorch_nvshmem", p)]
    families.append(family("torch_cuda_libs", torch_libs, True))
    families.append(family("nvidia_wheel_libs", walk("nvidia", (".so",)), True))
    families.append(family("triton_native", walk("triton", (".so",)), True))
    families.append(family("flashinfer_jit_cache", walk("flashinfer_jit_cache", (".so",)), False, True))
    families.append(family("flashinfer_cubin", walk("flashinfer_cubin", (".cubin",)), False, True))
    print(json.dumps({"commands": COMMANDS, "families": families, "site_packages": SP}))


if __name__ == "__main__":
    sys.exit(main())
