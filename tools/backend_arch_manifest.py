"""Backend kernel/PTX architecture manifest for the pinned engine image.

`capture` runs cuobjdump & friends inside a disposable, GPU-less, network-less
`docker run --rm` of the pinned image and writes the raw command output.
`analyze` (pure, no I/O) turns listings into per-backend coverage of a target
compute capability; `manifest_fields` produces what tools.preflight.check_runtime
reads (backend_arches, backend_manifest_complete).

Coverage rules (CUDA binary/PTX compatibility):
  * cubin sm_MN       runs on cc X.Y iff X == M and Y >= N         (native)
  * cubin sm_MNa      runs only on cc M.N exactly                  (arch-specific)
  * cubin sm_MNf      runs on cc X.Y iff X == M and Y >= N         (family-specific)
  * PTX  compute_MN   JIT-compiles on any cc >= M.N                (forward compat)
  * PTX  compute_MNa  only on cc M.N exactly; PTX compute_MNf: same major, Y >= N
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

IMAGE = "vllm/vllm-openai:v0.27.1"
# Backends whose coverage decides backend_manifest_complete / backend_arches.
CORE_VLLM_LIBS = ("_C_stable_libtorch.abi3.so", "_moe_C_stable_libtorch.abi3.so")
_TOKEN = re.compile(r"^(\d+?)(\d)([af]?)$")


def parse_token(token: str) -> tuple[int, int, str]:
    """'121a' -> (12, 1, 'a'); '80' -> (8, 0, ''); '100f' -> (10, 0, 'f')."""
    m = _TOKEN.match(token)
    if not m:
        raise ValueError(f"unparseable arch token: {token!r}")
    return int(m.group(1)), int(m.group(2)), m.group(3)


def parse_cc(cc: str) -> tuple[int, int]:
    major, minor = cc.split(".")
    return int(major), int(minor)


def elf_covers(token: str, cc: tuple[int, int]) -> bool:
    major, minor, suffix = parse_token(token)
    if suffix == "a":
        return (major, minor) == cc
    return major == cc[0] and cc[1] >= minor


def ptx_covers(token: str, cc: tuple[int, int]) -> bool:
    major, minor, suffix = parse_token(token)
    if suffix == "a":
        return (major, minor) == cc
    if suffix == "f":
        return major == cc[0] and cc[1] >= minor
    return cc >= (major, minor)


def backend_verdict(elf: Iterable[str], ptx: Iterable[str], cc: str) -> dict[str, Any]:
    """Classify one backend (set of cubin archs + PTX archs) against a target cc."""
    target = parse_cc(cc)
    elf, ptx = sorted(set(elf)), sorted(set(ptx))
    native = [t for t in elf if elf_covers(t, target)]
    jit = [t for t in ptx if ptx_covers(t, target)]
    if not elf and not ptx:
        status = "no_gpu_code"
    elif native:
        status = "native"
    elif jit:
        status = "ptx_forward_compat"
    else:
        status = "NOT_COVERED"
    return {"status": status, "elf": elf, "ptx": ptx, "native_match": native, "ptx_match": jit}


def covered_caps(verdicts: list[dict[str, Any]], candidates: Iterable[str]) -> list[str]:
    """Candidate caps covered (native or PTX) by EVERY backend that carries GPU code."""
    carrying = [v for v in verdicts if v["elf"] or v["ptx"]]
    out = []
    for cc in candidates:
        if carrying and all(backend_verdict(v["elf"], v["ptx"], cc)["status"] in ("native", "ptx_forward_compat")
                            for v in carrying):
            out.append(cc)
    return out


def _cc_of(token: str) -> str:
    major, minor, _ = parse_token(token)
    return f"{major}.{minor}"


def analyze(probe: dict[str, Any], gpu_cc: str) -> dict[str, Any]:
    """Per-backend verdicts and the preflight fields, from a probe document."""
    fams = {f["family"]: f for f in probe.get("families", [])}
    per_backend: dict[str, dict[str, Any]] = {}
    core: list[dict[str, Any]] = []
    missing: list[str] = []

    def add(name: str, elf: Iterable[str], ptx: Iterable[str], is_core: bool, rcs_ok: bool = True) -> None:
        verdict = backend_verdict(elf, ptx, gpu_cc)
        verdict["core"] = is_core
        verdict["rcs_ok"] = rcs_ok
        per_backend[name] = verdict
        if is_core:
            core.append(verdict)

    vf = fams.get("vllm_native_extensions")
    if vf and vf.get("per_file"):
        for row in vf["per_file"]:
            base = row["path"].rsplit("/", 1)[-1]
            add("vllm:" + base, row["elf"], row["ptx"], base in CORE_VLLM_LIBS,
                row["state"] != "error")
        for lib in CORE_VLLM_LIBS:
            if "vllm:" + lib not in per_backend:
                missing.append("vllm:" + lib)
    else:
        missing.extend("vllm:" + lib for lib in CORE_VLLM_LIBS)
    tf = fams.get("torch_cuda_libs")
    if tf and tf.get("per_file"):
        for row in tf["per_file"]:
            base = row["path"].rsplit("/", 1)[-1]
            add("torch:" + base, row["elf"], row["ptx"], base == "libtorch_cuda.so",
                row["state"] != "error")
        if "torch:libtorch_cuda.so" not in per_backend:
            missing.append("torch:libtorch_cuda.so")
    else:
        missing.append("torch:libtorch_cuda.so")
    for name in ("nvidia_wheel_libs", "triton_native", "flashinfer_jit_cache", "flashinfer_cubin"):
        f = fams.get(name)
        if f:
            add(name, f["elf"], f["ptx"], False, f.get("errors", 1) == 0)
    flagged = sorted(n for n, v in per_backend.items() if v["status"] == "NOT_COVERED")
    candidates = sorted({_cc_of(t) for v in per_backend.values() for t in v["elf"] + v["ptx"]} | {gpu_cc},
                        key=parse_cc)
    complete = (not missing and len(core) >= 3 and all(v["rcs_ok"] for v in core)
                and all(v["elf"] or v["ptx"] for v in core))
    return {
        "gpu_cc": gpu_cc,
        "per_backend": per_backend,
        "missing_core": missing,
        "flagged_not_covered": flagged,
        "backend_arches": covered_caps(core, candidates) if complete else [],
        "backend_manifest_complete": complete,
    }


def preflight_snapshot_fields(result: dict[str, Any]) -> dict[str, Any]:
    return {"backend_arches": result["backend_arches"],
            "backend_manifest_complete": result["backend_manifest_complete"]}


def build_evidence(capture_path: Path, evidence: Path, gpu_cc: str = "12.1") -> dict[str, Any]:
    """Fold a raw capture into the evidence dir the forum verifier reads. Never invents an arch."""
    from tools import preflight

    record = json.loads(capture_path.read_text(encoding="utf-8"))
    pre_path, cmd_path = evidence / "preflight.json", evidence / "commands.json"
    doc = json.loads(pre_path.read_text(encoding="utf-8"))
    cmds = json.loads(cmd_path.read_text(encoding="utf-8"))
    if record["exit_code"] != 0:
        doc["could_not_run"] = ["backend_arch_probe: container exited %d" % record["exit_code"]]
        doc["could_not_run_count"] = 1
        pre_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return {"status": "could_not_run"}
    result = analyze(json.loads(record["stdout"]), gpu_cc)
    doc["snapshot"].update(preflight_snapshot_fields(result))
    doc["backend_manifest"] = {
        "image": IMAGE, "method": "docker run --rm --network none --memory 4g, no GPU, no mounts; cuobjdump --list-elf/--list-ptx",
        "core_backends": sorted(n for n, v in result["per_backend"].items() if v["core"]),
        "flagged_not_covered": result["flagged_not_covered"],
        "per_backend": {n: {k: v[k] for k in ("status", "elf", "ptx", "core")} for n, v in result["per_backend"].items()},
    }
    doc["preflight_result"] = preflight.CHECKS["runtime"](doc["snapshot"])
    doc["unverified"] = [
        "Tested model-kernel result, OEM support, soak/output comparison and rollback remain unavailable.",
        "Flagged (no sm_121-compatible cubin/PTX): " + ", ".join(result["flagged_not_covered"]) + ".",
        "Triton's bundled ptxas is CUDA 12.8 and lists no sm_121 target; whether the running engine overrides it was not read.",
    ]
    doc["open_blockers"] = [
        "Static manifest proves code is present for 12.1 in the core backends; it does not prove those kernels execute correctly on GB10. "
        "No tested model-kernel result, OEM support, soak/output comparison or rollback evidence."]
    cmds["commands"] = [c for c in cmds["commands"] if c.get("cmd") != " ".join(record["argv"])]
    cmds["commands"].append({"cmd": " ".join(record["argv"]), "argv": record["argv"], "exit": record["exit_code"],
                             "stdout": record["stdout"], "stderr": record["stderr"]})
    pre_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    cmd_path.write_text(json.dumps(cmds, indent=2) + "\n", encoding="utf-8")
    return {"status": doc["preflight_result"]["status"], "flagged": result["flagged_not_covered"],
            "backend_arches": result["backend_arches"]}


def capture(out: Path, container: str = "bb-archprobe") -> int:
    """Run the in-container probe (disposable, no GPU, no network, no mounts) and save its JSON."""
    probe_src = (Path(__file__).parent / "_backend_arch_container_probe.py").read_bytes()
    argv = ["docker", "run", "--rm", "-i", "--name", container, "--memory", "4g", "--network", "none",
            "-e", "NVIDIA_VISIBLE_DEVICES=void", "--entrypoint", "python3", IMAGE, "-"]
    r = subprocess.run(argv, input=probe_src, capture_output=True, timeout=3600)
    record = {"argv": argv, "exit_code": r.returncode, "stderr": r.stderr.decode("utf-8", "replace"),
              "stdout": r.stdout.decode("utf-8", "replace")}
    out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return r.returncode


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("analyze")
    a.add_argument("--capture", type=Path, required=True)
    a.add_argument("--gpu-cc", default="12.1")
    b = sub.add_parser("build-evidence")
    b.add_argument("--capture", type=Path, required=True)
    b.add_argument("--evidence", type=Path, required=True)
    args = p.parse_args(argv)
    if args.cmd == "capture":
        return capture(args.out)
    if args.cmd == "build-evidence":
        print(json.dumps(build_evidence(args.capture, args.evidence), sort_keys=True))
        return 0
    record = json.loads(args.capture.read_text(encoding="utf-8"))
    if record["exit_code"] != 0:
        print(json.dumps({"status": "could_not_run", "reason": "probe container exited non-zero"}))
        return 2
    print(json.dumps(analyze(json.loads(record["stdout"]), args.gpu_cc), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
