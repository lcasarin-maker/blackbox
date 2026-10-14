"""Negative controls for the backend kernel/PTX manifest (FEATURE-FORUM-GB10-RUNTIME-COMPAT-01)."""

import copy
import json
from pathlib import Path

import pytest

from tools import backend_arch_manifest as m
from tools import preflight

EVIDENCE = Path(__file__).resolve().parents[1] / "tasks/evidence/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"


def _file(name, elf, ptx, state="ok"):
    return {"path": f"/x/{name}", "elf": elf, "ptx": ptx, "rc_elf": 0, "rc_ptx": 0, "state": state}


def _probe(vllm_c, vllm_moe, torch_cuda, extra_vllm=()):
    return {"families": [
        {"family": "vllm_native_extensions", "per_file": [
            _file("_C_stable_libtorch.abi3.so", *vllm_c), _file("_moe_C_stable_libtorch.abi3.so", *vllm_moe),
            *[_file(n, *a) for n, a in extra_vllm]]},
        {"family": "torch_cuda_libs", "per_file": [_file("libtorch_cuda.so", *torch_cuda)]},
    ]}


def _snapshot(result):
    return {"host_arch": "aarch64", "image_arch": "arm64", "image_digest": "sha256:" + "0" * 64,
            "driver_version": "580", "image_driver_constraint": "cuda>=13.0", "gpu_arch": "12.1",
            "driver_compatibility": "pass", **m.preflight_snapshot_fields(result)}


def test_sm100_cubin_without_ptx_is_flagged_not_covered() -> None:
    verdict = m.backend_verdict(["100"], [], "12.1")
    assert verdict["status"] == "NOT_COVERED"
    assert m.backend_verdict(["90a", "100"], [], "12.1")["status"] == "NOT_COVERED"  # flashmla shape


@pytest.mark.parametrize("elf,ptx,status", [
    (["120"], [], "native"),                 # same major, minor 0 <= 1
    (["121a"], [], "native"),                # exact arch-specific
    (["120a"], [], "NOT_COVERED"),           # arch-specific other minor: not portable
    (["80"], ["80"], "ptx_forward_compat"),  # PTX JIT forward
    (["80"], ["90a"], "NOT_COVERED"),        # arch-specific PTX does not forward
    ([], [], "no_gpu_code"),
])
def test_verdict_rules(elf, ptx, status) -> None:
    assert m.backend_verdict(elf, ptx, "12.1")["status"] == status


def test_manifest_lacking_12_1_makes_preflight_block() -> None:
    good = m.analyze(_probe((["120"], []), (["120"], []), (["121a"], [])), "12.1")
    assert "12.1" in good["backend_arches"] and good["backend_manifest_complete"]
    assert preflight.check_runtime(_snapshot(good))["status"] == "pass"
    bad = m.analyze(_probe((["120"], []), (["100"], []), (["121a"], [])), "12.1")  # one core backend only sm_100
    assert bad["backend_manifest_complete"] and "12.1" not in bad["backend_arches"]
    result = preflight.check_runtime(_snapshot(bad))
    assert result["status"] == "block"
    assert "excludes the detected GPU architecture" in result["findings"][0]


def test_incomplete_manifest_is_unknown_not_pass() -> None:
    probe = _probe((["120"], []), (["120"], []), (["121a"], []))
    probe["families"] = probe["families"][:1]  # torch family missing
    result = m.analyze(probe, "12.1")
    assert not result["backend_manifest_complete"] and result["missing_core"] == ["torch:libtorch_cuda.so"]
    assert preflight.check_runtime(_snapshot(result))["status"] == "unknown"
    errored = _probe((["120"], []), (["120"], []), (["121a"], []))
    errored["families"][1]["per_file"][0]["state"] = "error"
    assert not m.analyze(errored, "12.1")["backend_manifest_complete"]


def test_optional_backend_without_12_1_is_flagged_but_not_core() -> None:
    probe = _probe((["120"], []), (["120"], []), (["121a"], []), extra_vllm=[("_flashmla_C.abi3.so", (["90a", "100"], []))])
    result = m.analyze(probe, "12.1")
    assert result["flagged_not_covered"] == ["vllm:_flashmla_C.abi3.so"]
    assert result["backend_manifest_complete"] and "12.1" in result["backend_arches"]


def _recorded_probe():
    commands = json.loads((EVIDENCE / "commands.json").read_text(encoding="utf-8"))["commands"]
    rows = [c for c in commands if isinstance(c.get("argv"), list) and "--entrypoint" in c["argv"]]
    assert len(rows) == 1 and rows[0]["exit"] == 0
    return json.loads(rows[0]["stdout"])


def test_recorded_evidence_recomputes_from_raw_probe() -> None:
    doc = json.loads((EVIDENCE / "preflight.json").read_text(encoding="utf-8"))
    result = m.analyze(_recorded_probe(), "12.1")
    assert doc["snapshot"]["backend_arches"] == result["backend_arches"]
    assert doc["snapshot"]["backend_manifest_complete"] is result["backend_manifest_complete"] is True
    assert doc["backend_manifest"]["flagged_not_covered"] == result["flagged_not_covered"]
    assert "vllm:_flashmla_C.abi3.so" in result["flagged_not_covered"]


def test_recorded_evidence_negative_control_dropping_12x_cubins_blocks() -> None:
    probe = copy.deepcopy(_recorded_probe())
    for fam in probe["families"]:
        for row in fam.get("per_file") or []:
            if row["path"].endswith("libtorch_cuda.so"):
                row["elf"] = [t for t in row["elf"] if not t.startswith("12")]
    result = m.analyze(probe, "12.1")
    assert "12.1" not in result["backend_arches"]
    assert preflight.check_runtime(_snapshot(result))["status"] == "block"
