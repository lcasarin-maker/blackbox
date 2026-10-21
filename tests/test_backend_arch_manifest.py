"""Negative controls for the backend kernel/PTX manifest (FEATURE-FORUM-GB10-RUNTIME-COMPAT-01)."""

import copy
import importlib.util
import json
import os
import runpy
import shutil
import site
import stat
import sys
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


# --- token and suffix rules not reached above ---------------------------------------------------

def test_unparseable_arch_token_raises_instead_of_guessing() -> None:
    for bad in ("", "x", "9", "121b", "sm_121"):
        with pytest.raises(ValueError, match="unparseable arch token"):
            m.parse_token(bad)
    assert m.parse_token("121a") == (12, 1, "a")  # control: a valid token does parse


@pytest.mark.parametrize("token,covers", [
    ("120f", True),   # family-specific PTX, same major, minor 0 <= 1
    ("121f", True),   # exact minor
    ("122f", False),  # minor above the target
    ("100f", False),  # other major
])
def test_family_specific_ptx_covers_same_major_only(token: str, covers: bool) -> None:
    assert m.ptx_covers(token, (12, 1)) is covers
    assert (m.backend_verdict([], [token], "12.1")["status"] == "ptx_forward_compat") is covers


def test_plain_ptx_boundary_is_inclusive_of_the_exact_target() -> None:
    assert m.ptx_covers("121", (12, 1)) and m.ptx_covers("120", (12, 1)) and m.ptx_covers("90", (12, 1))
    assert not m.ptx_covers("122", (12, 1)) and not m.ptx_covers("130", (12, 1))


# --- missing core backends when the family is present but incomplete ---------------------------------

def test_vllm_family_without_a_core_lib_lists_it_missing_and_is_incomplete() -> None:
    probe = _probe((["120"], []), (["120"], []), (["121a"], []))
    probe["families"][0]["per_file"].pop(1)  # drop _moe_C
    result = m.analyze(probe, "12.1")
    assert result["missing_core"] == ["vllm:_moe_C_stable_libtorch.abi3.so"]
    assert not result["backend_manifest_complete"] and result["backend_arches"] == []


def test_absent_or_empty_vllm_family_lists_both_core_libs_missing() -> None:
    for vllm_family in ({"family": "vllm_native_extensions", "per_file": []}, None):
        probe = _probe((["120"], []), (["120"], []), (["121a"], []))
        if vllm_family is None:
            probe["families"].pop(0)
        else:
            probe["families"][0] = vllm_family
        result = m.analyze(probe, "12.1")
        assert result["missing_core"] == ["vllm:" + lib for lib in m.CORE_VLLM_LIBS]
        assert not result["backend_manifest_complete"]


def test_torch_family_without_libtorch_cuda_lists_it_missing() -> None:
    probe = _probe((["120"], []), (["120"], []), (["121a"], []))
    probe["families"][1]["per_file"][0]["path"] = "/x/libc10_cuda.so"
    result = m.analyze(probe, "12.1")
    assert result["missing_core"] == ["torch:libtorch_cuda.so"] and "torch:libc10_cuda.so" in result["per_backend"]
    assert not result["backend_manifest_complete"]


# --- the in-container probe, run for real against a tree of tiny fake binaries ------------------------
# The stub cuobjdump's output is the INPUT fixture; every assertion is on what the probe derives from it.

PROBE = Path(m.__file__).parent / "_backend_arch_container_probe.py"
STUB_CUOBJDUMP = r"""#!/bin/bash
[ "$1" = "--version" ] && { echo "cuobjdump stub release 99"; exit 0; }
kind=${1#--list-}; f=$2; b=$(basename "$f")
case "$b" in
  nodev*) echo "cuobjdump info    : File '$f' does not contain device code" >&2; exit 1;;
  broken*) echo "cuobjdump fatal   : boom" >&2; exit 2;;
  big*) [ "$kind" = elf ] && for i in $(seq 1 800); do echo "ELF file $i: big.sm_121.cubin"; done; exit 0;;
esac
[ -f "$STUB_SIDE/$b-$kind" ] && cat "$STUB_SIDE/$b-$kind"
exit 0
"""


def _exe(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _fake(path: Path, elf: tuple[str, ...] = (), ptx: tuple[str, ...] = ()) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x7fELF-fake")
    lines = {"elf": [f"ELF file    {i + 1}: {path.stem}.sm_{a}.cubin" for i, a in enumerate(elf)],
             "ptx": [f"PTX file    {i + 1}: {path.stem}.compute_{a}.ptx" for i, a in enumerate(ptx)]}
    for kind, rows in lines.items():
        if rows:
            # sidecar lives outside site-packages so walk() never sees it; the header line carries no arch
            side = next(p for p in path.parents if p.name == "sp").parent / "side"
            side.mkdir(exist_ok=True)
            (side / f"{path.name}-{kind}").write_text("\n".join(["Fatbin code:", *rows]) + "\n", encoding="utf-8")


def _run_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
               moe_arch: str = "100") -> dict:
    sp, bin_dir = tmp_path / "sp", tmp_path / "bin"
    _exe(bin_dir / "cuobjdump", STUB_CUOBJDUMP)
    _exe(bin_dir / "python3", "#!/bin/sh\necho stub-python\n")
    _exe(sp / "triton/backends/nvidia/bin/ptxas", "#!/bin/sh\necho \"ptxas stub $1\"\n")
    _fake(sp / "vllm/_C_stable_libtorch.abi3.so", elf=("121a",))
    _fake(sp / "vllm/_moe_C_stable_libtorch.abi3.so", elf=(moe_arch,))
    _fake(sp / "vllm/_flashmla_C.abi3.so", elf=("90a", "100"))
    _fake(sp / "vllm/nodev.so")
    _fake(sp / "vllm/broken.so")
    _fake(sp / "vllm/big.so")
    _fake(sp / "torch/lib/libtorch_cuda.so", elf=("80",), ptx=("80",))
    _fake(sp / "torch/lib/libc10_cuda.so", elf=("121",))
    _fake(sp / "torch/lib/libother.so", elf=("50",))  # filtered out by the family regex
    _fake(sp / "nvidia/cu13/lib/libfoo.so.12", elf=("90",))  # versioned soname: second clause of walk
    _fake(sp / "nvidia/cu13/lib/empty.so")
    _fake(sp / "triton/_C/libtriton.so", elf=("80",))
    _fake(sp / "flashinfer_jit_cache/a.so", elf=("100", "120"), ptx=("120",))
    _fake(sp / "flashinfer_jit_cache/b.so", elf=("100",))
    _fake(sp / "flashinfer_cubin/k.cubin", elf=("100",))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("STUB_SIDE", str(tmp_path / "side"))
    spec = importlib.util.spec_from_file_location("probe_under_test", PROBE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "SP", str(sp))
    monkeypatch.setattr(mod, "CUOBJDUMP", str(bin_dir / "cuobjdump"))
    assert mod.main() is None
    return json.loads(capsys.readouterr().out)


def test_probe_derives_every_family_from_the_stub_listing(tmp_path, monkeypatch, capsys) -> None:
    doc = _run_probe(tmp_path, monkeypatch, capsys)
    fams = {f["family"]: f for f in doc["families"]}
    assert doc["site_packages"] == str(tmp_path / "sp")
    assert list(fams) == ["vllm_native_extensions", "torch_cuda_libs", "nvidia_wheel_libs", "triton_native",
                          "flashinfer_jit_cache", "flashinfer_cubin"]
    vllm = fams["vllm_native_extensions"]
    assert vllm["files"] == 6 and vllm["elf"] == ["100", "121", "121a", "90a"] and vllm["ptx"] == []
    assert (vllm["errors"], vllm["no_device_code"]) == (1, 1)  # broken.so rc 2 / nodev.so "no device code"
    states = {Path(r["path"]).name: (r["state"], r["rc_elf"], r["rc_ptx"]) for r in vllm["per_file"]}
    assert states["broken.so"] == ("error", 2, 2) and states["nodev.so"] == ("no_device_code", 1, 1)
    assert states["_C_stable_libtorch.abi3.so"] == ("ok", 0, 0)
    assert sum(vllm["combos"].values()) == 6 and vllm["combos"]["elf=121a;ptx="] == 1
    assert len(vllm["listing_sha256"]) == 64
    torch = fams["torch_cuda_libs"]
    assert sorted(Path(r["path"]).name for r in torch["per_file"]) == ["libc10_cuda.so", "libtorch_cuda.so"]
    assert torch["elf"] == ["121", "80"] and torch["ptx"] == ["80"]
    assert fams["nvidia_wheel_libs"]["files"] == 2 and fams["nvidia_wheel_libs"]["elf"] == ["90"]
    assert fams["triton_native"]["elf"] == ["80"]
    jit = fams["flashinfer_jit_cache"]  # aggregate only: no per_file, unions and combos instead
    assert jit["per_file"] is None and jit["elf"] == ["100", "120"] and jit["ptx"] == ["120"]
    assert jit["combos"] == {"elf=100,120;ptx=120": 1, "elf=100;ptx=": 1}
    assert fams["flashinfer_cubin"]["files"] == 1 and fams["flashinfer_cubin"]["elf"] == ["100"]


def test_probe_records_commands_truncates_long_stdout_and_hides_env(tmp_path, monkeypatch, capsys) -> None:
    doc = _run_probe(tmp_path, monkeypatch, capsys)
    cmds = doc["commands"]
    assert not any(c["argv"] == ["env"] for c in cmds)  # keep=False
    version = next(c for c in cmds if c["argv"][1:] == ["--version"] and c["argv"][0].endswith("/bin/cuobjdump"))
    assert version["exit_code"] == 0 and version["stdout"] == "cuobjdump stub release 99\n"
    pyrow = next(c for c in cmds if c["argv"][0] == "python3")
    assert pyrow["stdout"] == "stub-python\n"
    ptxas = [c for c in cmds if c["argv"][0].endswith("triton/backends/nvidia/bin/ptxas")]
    assert [c["stdout"] for c in ptxas] == ["ptxas stub --version\n", "ptxas stub --help\n"]
    big = next(c for c in cmds if c["argv"][:2] == [str(tmp_path / "bin/cuobjdump"), "--list-elf"]
               and c["argv"][2].endswith("big.so"))
    full = "".join(f"ELF file {i}: big.sm_121.cubin\n" for i in range(1, 801))
    assert len(big["stdout"]) == 20000 and big["stdout"] == full[:20000]
    assert big["stdout_truncated"]["total_bytes"] == len(full)
    import hashlib
    assert big["stdout_truncated"]["sha256"] == hashlib.sha256(full.encode()).hexdigest()
    assert all("stdout_truncated" not in c for c in cmds if c is not big)  # control: short outputs stay verbatim


def test_probe_command_that_cannot_start_is_recorded_as_exit_minus_one(tmp_path, monkeypatch, capsys) -> None:
    doc = _run_probe(tmp_path, monkeypatch, capsys)
    # /usr/local/cuda/bin/{nvcc,ptxas} are hard-coded; whichever way this host resolves them, the row exists
    # and is either a real run (exit 0 or nonzero) or the OSError branch (exit -1 with the exception named).
    for path in ("/usr/local/cuda/bin/nvcc", "/usr/local/cuda/bin/ptxas"):
        rows = [c for c in doc["commands"] if c["argv"][0] == path]
        assert rows
        if not os.path.exists(path):
            assert rows[0]["exit_code"] == -1 and rows[0]["stderr"].startswith("FileNotFoundError")


def test_probe_through_analyze_flags_the_backend_without_12_1_and_the_control_clears_it(
        tmp_path, monkeypatch, capsys) -> None:
    bad = m.analyze(_run_probe(tmp_path / "bad", monkeypatch, capsys, moe_arch="100"), "12.1")
    assert bad["per_backend"]["vllm:_moe_C_stable_libtorch.abi3.so"]["status"] == "NOT_COVERED"
    assert "vllm:_flashmla_C.abi3.so" in bad["flagged_not_covered"] and "vllm:broken.so" in bad["per_backend"]
    assert bad["per_backend"]["vllm:broken.so"]["rcs_ok"] is False
    assert bad["backend_manifest_complete"] and "12.1" not in bad["backend_arches"]
    good = m.analyze(_run_probe(tmp_path / "good", monkeypatch, capsys, moe_arch="120"), "12.1")
    assert good["per_backend"]["vllm:_moe_C_stable_libtorch.abi3.so"]["status"] == "native"
    assert "12.1" in good["backend_arches"]  # libtorch_cuda: sm_80 + PTX 80 is forward compat, still covered
    assert good["per_backend"]["torch:libtorch_cuda.so"]["status"] == "ptx_forward_compat"


def test_probe_run_as_script_exits_cleanly_on_an_empty_site_packages(tmp_path, monkeypatch, capsys) -> None:
    empty = tmp_path / "empty-sp"
    empty.mkdir()
    _exe(tmp_path / "bin/python3", "#!/bin/sh\necho stub-python\n")
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(site, "getsitepackages", lambda: [str(empty)])
    with pytest.raises(SystemExit) as salida:
        runpy.run_path(str(PROBE), run_name="__main__")
    assert salida.value.code is None
    doc = json.loads(capsys.readouterr().out)
    assert doc["site_packages"] == str(empty) and all(f["files"] == 0 for f in doc["families"])
    # no files -> nothing for analyze to call a core backend
    assert not m.analyze(doc, "12.1")["backend_manifest_complete"]


# --- capture / build_evidence / main ---------------------------------------------------------------

STUB_DOCKER = r"""#!/bin/bash
cat > "$STUB_STDIN"
printf '%s\n' "$@" > "$STUB_ARGV"
printf '{"stub": true}\n\xff'
echo "warn" >&2
exit "${STUB_RC:-0}"
"""


def _docker_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rc: int) -> tuple[Path, Path]:
    _exe(tmp_path / "bin/docker", STUB_DOCKER)
    stdin, argv = tmp_path / "stdin.bin", tmp_path / "argv.txt"
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("STUB_STDIN", str(stdin))
    monkeypatch.setenv("STUB_ARGV", str(argv))
    monkeypatch.setenv("STUB_RC", str(rc))
    return stdin, argv


@pytest.mark.parametrize("rc", [0, 3])
def test_capture_pipes_the_probe_to_a_no_gpu_no_network_container_and_records_what_came_back(
        tmp_path, monkeypatch, rc: int) -> None:
    stdin, argv = _docker_stub(tmp_path, monkeypatch, rc)
    out = tmp_path / "cap.json"
    assert m.capture(out, container="bb-test") == rc
    record = json.loads(out.read_text(encoding="utf-8"))
    assert stdin.read_bytes() == PROBE.read_bytes()  # the probe source is exactly what the container got on stdin
    seen = argv.read_text(encoding="utf-8").splitlines()
    assert record["argv"] == ["docker", *seen] and record["exit_code"] == rc
    assert seen[:2] == ["run", "--rm"] and "--network" in seen and seen[seen.index("--network") + 1] == "none"
    assert seen[seen.index("--name") + 1] == "bb-test" and seen[-2:] == [m.IMAGE, "-"]
    assert "NVIDIA_VISIBLE_DEVICES=void" in seen
    assert record["stdout"] == '{"stub": true}\n\ufffd' and record["stderr"] == "warn\n"  # undecodable byte replaced


def _evidence_copy(tmp_path: Path) -> Path:
    ev = tmp_path / "ev"
    ev.mkdir()
    for name in ("preflight.json", "commands.json"):
        shutil.copy(EVIDENCE / name, ev / name)
    return ev


def _capture_file(tmp_path: Path, exit_code: int = 0, argv_tail: str = "") -> Path:
    cmds = json.loads((EVIDENCE / "commands.json").read_text(encoding="utf-8"))["commands"]
    row = next(c for c in cmds if isinstance(c.get("argv"), list) and "--entrypoint" in c["argv"])
    path = tmp_path / "capture.json"
    path.write_text(json.dumps({"argv": row["argv"] + ([argv_tail] if argv_tail else []), "exit_code": exit_code,
                                "stdout": row["stdout"], "stderr": row.get("stderr", "")}), encoding="utf-8")
    return path


def test_build_evidence_folds_the_capture_into_preflight_and_replaces_its_own_command_row(tmp_path) -> None:
    ev = _evidence_copy(tmp_path)
    result = m.build_evidence(_capture_file(tmp_path), ev)
    doc = json.loads((ev / "preflight.json").read_text(encoding="utf-8"))
    direct = m.analyze(_recorded_probe(), "12.1")
    assert result == {"status": doc["preflight_result"]["status"], "flagged": direct["flagged_not_covered"],
                      "backend_arches": direct["backend_arches"]}
    assert doc["snapshot"]["backend_arches"] == direct["backend_arches"]
    assert doc["backend_manifest"]["flagged_not_covered"] == direct["flagged_not_covered"]
    assert doc["backend_manifest"]["image"] == m.IMAGE
    assert doc["preflight_result"] == preflight.CHECKS["runtime"](doc["snapshot"])
    assert any("Flagged" in u and ", ".join(direct["flagged_not_covered"]) in u for u in doc["unverified"])
    cmds = json.loads((ev / "commands.json").read_text(encoding="utf-8"))["commands"]
    same = [c for c in cmds if c["cmd"].startswith("docker run --rm -i --name bb-archprobe")]
    assert len(same) == 1 and same[0]["exit"] == 0  # replaced, not duplicated
    # control: a capture with a different argv is appended next to the first, not swapped for it
    m.build_evidence(_capture_file(tmp_path, argv_tail="extra"), ev)
    again = json.loads((ev / "commands.json").read_text(encoding="utf-8"))["commands"]
    assert len([c for c in again if c["cmd"].startswith("docker run --rm -i --name bb-archprobe")]) == 2


def test_build_evidence_with_a_failed_container_records_could_not_run_and_changes_nothing_else(tmp_path) -> None:
    ev = _evidence_copy(tmp_path)
    commands_before = (ev / "commands.json").read_bytes()
    before = json.loads((ev / "preflight.json").read_text(encoding="utf-8"))
    assert m.build_evidence(_capture_file(tmp_path, exit_code=7), ev) == {"status": "could_not_run"}
    doc = json.loads((ev / "preflight.json").read_text(encoding="utf-8"))
    assert doc["could_not_run"] == ["backend_arch_probe: container exited 7"] and doc["could_not_run_count"] == 1
    assert doc["snapshot"] == before["snapshot"] and (ev / "commands.json").read_bytes() == commands_before


def test_main_analyze_prints_the_verdict_and_a_failed_capture_exits_2(tmp_path, capsys) -> None:
    assert m.main(["analyze", "--capture", str(_capture_file(tmp_path))]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["gpu_cc"] == "12.1" and "vllm:_flashmla_C.abi3.so" in printed["flagged_not_covered"]
    assert m.main(["analyze", "--capture", str(_capture_file(tmp_path)), "--gpu-cc", "9.0"]) == 0
    assert json.loads(capsys.readouterr().out)["gpu_cc"] == "9.0"
    assert m.main(["analyze", "--capture", str(_capture_file(tmp_path, exit_code=5))]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "could_not_run"


def test_main_build_evidence_and_capture_dispatch(tmp_path, monkeypatch, capsys) -> None:
    ev = _evidence_copy(tmp_path)
    assert m.main(["build-evidence", "--capture", str(_capture_file(tmp_path)), "--evidence", str(ev)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] in ("pass", "block", "unknown")
    _docker_stub(tmp_path, monkeypatch, 4)
    assert m.main(["capture", "--out", str(tmp_path / "c.json")]) == 4
    assert json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))["exit_code"] == 4


def test_module_run_as_script_exits_with_the_main_code(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["m", "analyze", "--capture", str(_capture_file(tmp_path, exit_code=9))])
    monkeypatch.delitem(sys.modules, "tools.backend_arch_manifest")
    with pytest.raises(SystemExit) as salida:
        runpy.run_module("tools.backend_arch_manifest", run_name="__main__")
    assert salida.value.code == 2
