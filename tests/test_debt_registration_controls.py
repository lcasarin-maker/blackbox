"""Regression controls for defects registered during the debt audit."""

import json
import csv
import copy
from datetime import datetime
import os
import subprocess
import sys
import time
import hashlib
import shutil
import types

from test_bb_usable import _cargar
from test_bb_bash import _arbol_cgroup, _fila_escritorio, _syscall, correr
import test_bb_bash as bash_tests
import test_atom_gpu_telemetry_bb as atom_tests
import test_bb_usable as bb_usable_tests
from pathlib import Path
import re

import pytest

from tools import provider_trace
from tools import cgroup_repro, cuda_integrity
from tools import verify_apt_critical_removals
from tools import host_diagnostics


def test_debt_close_check_verify_apt_critical_removals_01(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parent.parent
    evidence = root / "tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-APT-CRITICAL-REMOVALS-01"
    result = verify_apt_critical_removals.verify(evidence)
    assert result["status"] == "pass", result
    assert result["fail"] == 0
    assert result["could_not_run"] == 0
    assert result["checks"] == {"captured_upgrade": "pass", "captured_critical_removal": "block"}
    assert result["evidence_sha256"] == (evidence / "apt-captures.sha256").read_text(encoding="ascii").strip()
    assert result["closure"] == "open"

    # Missing evidence and a dead command are unknown, not passes.
    missing = verify_apt_critical_removals.verify(tmp_path)
    assert missing["status"] == "unknown" and missing["could_not_run"] == 1
    raw = (evidence / "apt-captures.json").read_bytes()
    captures = json.loads(raw)
    captures["commands"][1]["exit_code"] = 2
    sandbox = tmp_path / "dead-command"
    sandbox.mkdir()
    serialized = json.dumps(captures).encode()
    (sandbox / "apt-captures.json").write_bytes(serialized)
    (sandbox / "apt-captures.sha256").write_text(hashlib.sha256(serialized).hexdigest(), encoding="ascii")
    dead = verify_apt_critical_removals.verify(sandbox)
    assert dead["status"] == "unknown" and dead["could_not_run"] == 1

    # A verifier with its shared classifier neutralized must fail the dangerous capture.
    monkeypatch.setattr(verify_apt_critical_removals, "check_apt",
                        lambda _snapshot: {"status": "pass", "findings": []})
    neutralized = verify_apt_critical_removals.verify(evidence)
    assert neutralized["status"] == "fail" and neutralized["fail"] == 1
    assert neutralized["could_not_run"] == 0


def _capture_could_not_run(value) -> int:
    if isinstance(value, dict):
        return int(value.get("status") == "could_not_run") + sum(
            _capture_could_not_run(child) for child in value.values())
    if isinstance(value, list):
        return sum(_capture_could_not_run(child) for child in value)
    return 0


class _CaptureUnknown(ValueError):
    pass


class _CaptureFailure(ValueError):
    pass


def _runtime_capture_provenance(document, evidence_dir: Path) -> None:
    source_hashes = document["source_hashes"]
    archive = {"bb-runtime-live.py": "runtime-collector-source.txt",
               "host_diagnostics.py": "runtime-host-diagnostics.source.txt",
               "cuda_integrity.py": "runtime-cuda-integrity.source.txt"}
    if not isinstance(source_hashes, list) or len(source_hashes) != len(archive):
        raise _CaptureUnknown("source hashes absent")
    for row in source_hashes:
        if row["status"] != "ok" or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise _CaptureUnknown("source hash malformed")
        source = evidence_dir / archive[Path(row["path"]).name]
        if hashlib.sha256(source.read_bytes()).hexdigest() != row["sha256"]:
            raise _CaptureUnknown(f"archived source hash mismatch: {source.name}")
    collector_hash = next(row["sha256"] for row in source_hashes
                          if Path(row["path"]).name == "bb-runtime-live.py")
    command_note = (evidence_dir / "runtime-collector-command.txt").read_text(encoding="utf-8")
    if (f"Collector SHA-256: {collector_hash}" not in command_note
            or "Command: python3 /tmp/bb-runtime-live.py > tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01/runtime-capture.json" not in command_note):
        raise _CaptureUnknown("collector command/source provenance mismatch")
    cuda_source = (evidence_dir / archive["cuda_integrity.py"]).read_text(encoding="utf-8")
    literals = ("--property=MemoryMax=512M", "--property=CPUQuota=50%",
                "--property=RuntimeMaxSec=60s", "--_bounded-worker", "timeout=75")
    if not all(value in cuda_source for value in literals):
        raise _CaptureUnknown("bounded wrapper source literals absent")
    run = document["cuda_test"]
    if not run["wrapper_verified"] or document["wrapper_source_literals"] != list(literals):
        raise _CaptureUnknown("bounded wrapper record differs from archived source")
    expected_limits = {"MemoryMax": "512M", "CPUQuota": "50%", "RuntimeMaxSec": "60s"}
    if run["wrapper_limits"] != expected_limits:
        raise _CaptureFailure("wrapper limits mismatch")


def _capture_host_identity(phase) -> tuple:
    timestamp = datetime.fromisoformat(phase["timestamp_utc"])
    if timestamp.tzinfo is None:
        raise _CaptureUnknown("capture timestamp lacks timezone")
    host = phase["host"]
    if not all(host[key] for key in ("system", "kernel_release", "architecture")):
        raise _CaptureUnknown("OS/kernel/architecture identity absent")
    for key in ("boot_id", "nvidia_module", "os_release", "dgx_release", "memory"):
        if host[key]["status"] != "ok":
            raise _CaptureUnknown(f"host observation unavailable: {key}")
    if host["memory"]["mem_available_bytes"] < 1024**3:
        raise _CaptureUnknown("host headroom below 1 GiB")
    dgx = host["dgx_release"]["values"]
    if dgx["DGX_NAME"] != "DGX Spark":
        raise _CaptureFailure("wrong OEM subject")
    if not dgx["DGX_SWBUILD_VERSION"] or not dgx["DGX_OTA_VERSION"]:
        raise _CaptureUnknown("DGX release versions absent")
    return (timestamp, host["system"], host["kernel_release"], host["architecture"],
            host["boot_id"]["value"], host["os_release"]["sha256"],
            host["dgx_release"]["sha256"], dgx["DGX_SWBUILD_VERSION"], dgx["DGX_OTA_VERSION"],
            host["nvidia_module"]["value"])


def _capture_container_identity(runtime) -> tuple:
    for key in ("container_runtime_version", "running_container_image_tags"):
        if runtime[key]["status"] != "ok" or runtime[key]["returncode"] != 0:
            raise _CaptureUnknown(f"container read unavailable: {key}")
    images = runtime["running_container_image_ids"]
    if images["status"] != "ok":
        raise _CaptureUnknown("container image IDs unavailable")
    rows = runtime["running_container_image_tags"]["stdout"].splitlines()
    vllm_rows = {fields[0]: fields[1] for row in rows if len(fields := row.split(maxsplit=1)) == 2
                 and "vllm" in fields[1].casefold()}
    records = images["containers"]
    ids = [record["container_id"] for record in records]
    if (not vllm_rows or images["candidate_count"] != len(vllm_rows)
            or len(records) != len(vllm_rows) or len(set(ids)) != len(records)):
        raise _CaptureFailure("container candidate count mismatch")
    for row in records:
        if (row["status"] != "ok" or row["image_ref"] != vllm_rows.get(row["container_id"])
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", row["image_id"])):
            raise _CaptureFailure("container image ID evidence mismatch")
    return runtime["container_runtime_version"]["stdout"], records


def _capture_runtime_identity(phase, document) -> tuple:
    runtime = phase["runtime"]
    for key in ("nvidia_smi_banner", "nvidia_gpu_state"):
        if runtime[key]["status"] != "ok" or runtime[key]["returncode"] != 0:
            raise _CaptureUnknown(f"GPU read unavailable: {key}")
    query = next(csv.reader([runtime["nvidia_gpu_state"]["stdout"]]))
    if len(query) != 5 or not all(value.strip() for value in query):
        raise _CaptureUnknown("GPU state query malformed")
    if "GB10" not in query[0]:
        raise _CaptureFailure("wrong GPU subject")
    driver = query[1].strip()
    if driver != phase["host"]["nvidia_module"]["value"]:
        raise _CaptureFailure("loaded module/driver version mismatch")
    if f"Driver Version: {driver}" not in runtime["nvidia_smi_banner"]["stdout"]:
        raise _CaptureFailure("nvidia-smi banner/query disagree")
    cuda = runtime["cuda_runtime"]
    if cuda["status"] != "ok" or type(cuda["runtime_version"]) is not int or cuda["runtime_version"] <= 0:
        raise _CaptureUnknown("exact CUDA Runtime API version unavailable")
    if (cuda["runtime_version"] // 1000 != cuda["major"]
            or (cuda["runtime_version"] % 1000) // 10 != cuda["minor"]):
        raise _CaptureFailure("CUDA runtime version fields disagree")
    expected = {key: document["cuda_runtime_api_version"].get(key) for key in cuda}
    if cuda != expected:
        raise _CaptureFailure("CUDA Runtime API snapshots disagree")
    return tuple(query[:3]), cuda["runtime_version"], _capture_container_identity(runtime)


def _capture_cuda_outcome(document) -> None:
    run = document["cuda_test"]
    argv = run["argv"]
    if (run["status"] != "pass" or run["returncode"] != 0 or run["stderr"]
            or len(argv) < 6 or Path(argv[1]).name != "cuda_integrity.py"
            or argv[-4:] != ["--workers", "1", "--rounds", "1"]
            or "--_bounded-worker" in argv):
        raise _CaptureFailure("raw CUDA command/exit is not the bounded entry point")
    if len(run["stdout"].splitlines()) != 1:
        raise _CaptureFailure("CUDA output is not one raw JSON result")
    result = json.loads(run["stdout"])
    if result != run["result"]:
        raise _CaptureFailure("stored result differs from raw stdout")
    valid = (result.get("status") == "pass" and result.get("workers") == 1
             and result.get("rounds_per_worker") == 1 and result.get("allocations") == 6
             and result.get("max_aggregate_allocation_bytes") == 4 * 1024 * 1024
             and result.get("full_buffer_readback") is True
             and result.get("release_between_rounds") is True
             and result.get("library") == document["cuda_runtime_api_version"]["library"]
             and type(result.get("seconds")) in (int, float)
             and 0 < result["seconds"] <= 60)
    if not valid:
        raise _CaptureFailure("raw CUDA functional outcome invalid")
    negative = document["negative_control"]
    if (negative["status"] != "pass"
            or "readback mismatch at byte 2" not in negative["status_message"]):
        raise _CaptureFailure("corrupted-byte negative control absent")


def _runtime_capture_verdict(document) -> dict:
    try:
        if document["schema"] != 1 or document["id"] != "DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01":
            raise _CaptureUnknown("capture identity/schema absent")
        phases = [document["before"], document["after"]]
        run = document["cuda_test"]
        unavailable = sum(_capture_could_not_run(phase["runtime"]) + sum(
            _capture_could_not_run(phase["host"][key]) for key in (
                "boot_id", "nvidia_module", "os_release", "dgx_release", "memory"))
                          for phase in phases)
        unavailable += sum(_capture_could_not_run(item) for item in document["source_hashes"])
        unavailable += int(run.get("status") == "could_not_run") + int(not run.get("wrapper_verified"))
        if document["could_not_run"] != unavailable:
            raise _CaptureUnknown("could_not_run total differs from raw leaf statuses")
        if unavailable:
            raise _CaptureUnknown(f"capture has could_not_run={unavailable}")
        evidence_dir = (Path(__file__).resolve().parent.parent
                        / "tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01")
        _runtime_capture_provenance(document, evidence_dir)
        identities = []
        for phase in phases:
            host = _capture_host_identity(phase)
            runtime = _capture_runtime_identity(phase, document)
            identities.append((host, runtime))
        before_host, after_host = identities[0][0], identities[1][0]
        before_runtime, after_runtime = identities[0][1], identities[1][1]
        if after_host[0] <= before_host[0] or (after_host[0] - before_host[0]).total_seconds() > 120:
            raise _CaptureFailure("timestamps do not bracket a short run")
        if before_host[1:] != after_host[1:] or before_runtime != after_runtime:
            raise _CaptureFailure("host/runtime identity changed during the run")
        _capture_cuda_outcome(document)
        return {"status": "pass", "could_not_run": 0, "findings": []}
    except _CaptureUnknown as exc:
        return {"status": "unknown", "could_not_run": 1, "findings": [str(exc)]}
    except _CaptureFailure as exc:
        return {"status": "fail", "could_not_run": 0, "findings": [str(exc)]}
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, json.JSONDecodeError) as exc:
        return {"status": "unknown", "could_not_run": 1,
                "findings": [f"malformed or incomplete raw observation: {type(exc).__name__}: {exc}"]}


def test_delta_forum_runtime_version_capture_01(monkeypatch: pytest.MonkeyPatch) -> None:
    root = Path(__file__).resolve().parent.parent
    evidence = root / "tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01/runtime-capture.json"
    sidecar = Path(str(evidence) + ".sha256")
    raw = evidence.read_bytes()
    expected_sha = sidecar.read_text(encoding="ascii").strip()
    assert hashlib.sha256(raw).hexdigest() == expected_sha, "could_not_run=1: raw capture digest mismatch"
    observed = json.loads(raw)
    assert _runtime_capture_verdict(observed) == {"status": "pass", "could_not_run": 0, "findings": []}

    # Incomplete, unavailable, wrong-subject and corrupted-output controls must not inherit stored PASS.
    for mutate, expected in (
        (lambda item: item.pop("before"), "unknown"),
        (lambda item: item["before"]["runtime"]["cuda_runtime"].update(status="could_not_run"), "unknown"),
        (lambda item: item["before"]["runtime"]["nvidia_gpu_state"].update(
            stdout=item["before"]["runtime"]["nvidia_gpu_state"]["stdout"].replace("GB10", "Other GPU")), "fail"),
        (lambda item: item["cuda_test"]["result"].update(full_buffer_readback=False), "fail"),
        (lambda item: item["after"]["host"]["boot_id"].update(value="different-boot"), "fail"),
        (lambda item: item["before"]["runtime"]["running_container_image_ids"].update(
            containers=[]), "fail"),
    ):
        altered = copy.deepcopy(observed)
        mutate(altered)
        assert _runtime_capture_verdict(altered)["status"] == expected

    status_only = {"schema": 1, "id": observed["id"], "status": "pass", "could_not_run": 0}
    assert _runtime_capture_verdict(status_only)["status"] == "unknown"
    unavailable_capture = copy.deepcopy(observed)
    unavailable_capture["before"]["runtime"]["cuda_runtime"]["status"] = "could_not_run"
    with monkeypatch.context() as neutralized_reader:
        neutralized_reader.setattr(sys.modules[__name__], "_capture_could_not_run", lambda _value: 0)
        assert _runtime_capture_verdict(unavailable_capture)["status"] != "pass"
    assert cuda_integrity.verify_bytes(b"\x07" * 32, b"\x07" * 32) is None

    def negative_detects(verifier) -> bool:
        try:
            verifier(b"abcd", b"abXd")
        except ValueError as exc:
            return "readback mismatch at byte 2" in str(exc)
        return False

    assert negative_detects(cuda_integrity.verify_bytes)
    with monkeypatch.context() as neutralized:
        neutralized.setattr(cuda_integrity, "verify_bytes", lambda *_args: None)
        assert not negative_detects(cuda_integrity.verify_bytes)


def test_apt_critical_verifier_cli_and_evidence_controls(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parent.parent
    source = root / "tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-APT-CRITICAL-REMOVALS-01"
    evidence = tmp_path / "evidence"
    shutil.copytree(source, evidence)
    command = [sys.executable, "-m", "tools.verify_apt_critical_removals", "--evidence", str(evidence)]

    def run(code: int, expected: str) -> None:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=10)
        assert result.returncode == code, result.stdout + result.stderr
        report = json.loads(result.stdout)
        assert report["status"] == expected
        assert report["fail"] == (1 if expected == "fail" else 0)
        assert report["could_not_run"] == (0 if expected != "unknown" else 1)

    run(0, "pass")
    captured = json.loads((evidence / "apt-captures.json").read_text(encoding="utf-8"))

    def save(document: object) -> None:
        raw = json.dumps(document).encode("utf-8")
        (evidence / "apt-captures.json").write_bytes(raw)
        (evidence / "apt-captures.sha256").write_text(hashlib.sha256(raw).hexdigest(), encoding="ascii")

    for mutate, code, status in (
        (lambda obj: obj["commands"].pop(), 2, "unknown"),
        (lambda obj: obj["commands"].append(obj["commands"][0]), 2, "unknown"),
        (lambda obj: obj["commands"][1].update(argv=["apt-get", "remove"]), 2, "unknown"),
        (lambda obj: obj["commands"][1].update(argv="malformed"), 2, "unknown"),
        (lambda obj: obj["commands"][1].update(stderr="warning"), 2, "unknown"),
        (lambda obj: obj["commands"][1].update(exit_code=2), 2, "unknown"),
        (lambda obj: obj["commands"][1].update(stdout="0 upgraded, 0 newly installed, 1 to remove and 0 not upgraded."), 2, "unknown"),
        (lambda obj: obj["commands"][1].update(stdout=obj["commands"][1]["stdout"].replace("nvidia-system-station", "other-package")), 1, "fail"),
        (lambda obj: obj["commands"][1].update(exit_code="0"), 2, "unknown"),
        (lambda obj: obj["commands"][1].update(stdout=17), 2, "unknown"),
        (lambda obj: obj["commands"][1].update(stderr=17), 2, "unknown"),
        (lambda obj: obj["commands"].append("malformed extra record"), 2, "unknown"),
    ):
        altered = json.loads(json.dumps(captured))
        mutate(altered)
        save(altered)
        run(code, status)

    save(captured)
    (evidence / "apt-captures.sha256").write_text("0" * 64, encoding="ascii")
    run(2, "unknown")
    save([])
    run(2, "unknown")
    save(captured)
    (evidence / "apt-captures.json").write_bytes(b"\xff")
    run(2, "unknown")



def test_debt_schema_evidence_index_scope_01(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parent.parent
    manifest = root / "tasks/evidence/DEBT-SCHEMA-EVIDENCE-INDEX-SCOPE-01/migration.json"
    rows = json.loads(manifest.read_text(encoding="utf-8"))["files"]
    assert len(rows) == 4
    for row in rows:
        assert not (root / row["old"]).exists()
        assert hashlib.sha256((root / row["new"]).read_bytes()).hexdigest() == row["sha256"]
    runner = root / ".simplecode/run.py"
    positive = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.ledger_schema", "--root", str(root), "--check"],
        capture_output=True, text=True, timeout=60)
    assert positive.returncode == 0, positive.stdout + positive.stderr
    assert "could_not_run=0" in positive.stdout, positive.stdout
    # A genuine task placed outside governed folders must remain visible to the gate.
    misplaced = tmp_path / "tasks" / "misplaced"
    misplaced.mkdir(parents=True)
    card = root / "tasks/done/DEBT-RUFF-BB-USABLE-01.md"
    (misplaced / card.name).write_bytes(card.read_bytes())
    negative = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.ledger_schema", "--root", str(tmp_path), "--check"],
        capture_output=True, text=True, timeout=60)
    assert negative.returncode != 0, negative.stdout + negative.stderr
    assert card.name in negative.stdout + negative.stderr
    assert "could_not_run=1" in negative.stdout, negative.stdout


def test_bug_coverage_cli_subprocess_01(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parent.parent
    target = root / "tools/inventario.py"
    entrypoint = len(target.read_text(encoding="utf-8").splitlines())
    for patch_children in (True, False):
        config = root / ".coveragerc" if patch_children else tmp_path / "without-patch.ini"
        if not patch_children:
            config.write_text("[run]\n", encoding="utf-8")
        data = tmp_path / ("with-patch" if patch_children else "without-patch")
        report = data.with_suffix(".json")
        # This is an independent measurement, including its deliberately broken control.
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("COVERAGE_", "COV_CORE_"))}
        env.update(COVERAGE_FILE=str(data), COVERAGE_RCFILE=str(config))
        run = subprocess.run(
            [sys.executable, "-m", "coverage", "run", "--source=tools", "-m", "pytest", "-q",
             "tests/test_debt_registration_controls.py::test_debt_no_cover_inventario_146"],
            cwd=root, env=env, capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stdout + run.stderr
        exported = subprocess.run(
            [sys.executable, "-m", "coverage", "json", "-o", str(report)],
            cwd=root, env=env, capture_output=True, text=True, timeout=20)
        assert exported.returncode == 0, exported.stdout + exported.stderr
        measured = json.loads(report.read_text(encoding="utf-8"))["files"]["tools/inventario.py"]
        assert (entrypoint in measured["executed_lines"]) is patch_children, measured


def test_debt_broad_except_cuda_integrity_57() -> None:
    import ctypes

    slots = {7: (ctypes.c_void_p(7), 1, 1)}
    attempts = []

    def failed_free(pointer):
        attempts.append(pointer.value)
        return 8

    with pytest.raises(RuntimeError, match="cudaFree hole returned CUDA error 8") as raised:
        cuda_integrity.release_slots(slots, [7], failed_free, "hole")
    assert slots == {}
    assert attempts == [7]
    assert any("uncertain device state" in note for note in raised.value.__notes__)


def test_debt_broad_except_cuda_integrity_67() -> None:
    import ctypes

    slots = {7: (ctypes.c_void_p(7), 1, 1), 8: (ctypes.c_void_p(8), 1, 1)}
    attempts = []

    def free(pointer):
        attempts.append(pointer.value)
        return 8 if pointer.value == 7 else 0

    assert cuda_integrity.cleanup_slots(slots, free, lambda: 0) == [
        "pointer 7: cudaFree cleanup returned CUDA error 8"]
    assert slots == {}
    assert attempts == [7, 8]


def test_debt_broad_except_cuda_integrity_74() -> None:
    assert cuda_integrity.cleanup_slots({}, lambda _pointer: 0,
                                        lambda: 19) == ["cudaDeviceSynchronize cleanup returned CUDA error 19"]


def test_debt_broad_except_cuda_integrity_127() -> None:
    from test_memory_capture_and_cuda_integrity import FakeCuda

    fake = FakeCuda(fail_memset_after=3, fail_free_on_call=1)
    with pytest.raises(RuntimeError, match="cudaMemset initial allocation returned CUDA error 9") as raised:
        cuda_integrity.run_worker(fake, index=0, rounds=1, worker_bytes=4 * 1024 * 1024)
    assert len(fake.free_attempts) == 3
    assert len(set(fake.free_attempts)) == 3
    assert len(fake.buffers) == 1
    assert any("cleanup failures" in note for note in raised.value.__notes__)

    fake = FakeCuda(fail_free_on_call=1)
    memset_calls = 0
    def cancel_during_fill(pointer, value, size):
        nonlocal memset_calls
        memset_calls += 1
        if memset_calls == 3:
            raise KeyboardInterrupt("cancel CUDA worker")
        return fake.fill(pointer, value, size)
    fake.cudaMemset.function = cancel_during_fill
    with pytest.raises(KeyboardInterrupt, match="cancel CUDA worker") as cancelled:
        cuda_integrity.run_worker(fake, index=0, rounds=1, worker_bytes=4 * 1024 * 1024)
    assert len(fake.free_attempts) == 3
    assert len(set(fake.free_attempts)) == 3
    assert any("cleanup failures" in note for note in cancelled.value.__notes__)


def test_debt_broad_except_cuda_integrity_209(monkeypatch: pytest.MonkeyPatch,
                                              capsys: pytest.CaptureFixture[str]) -> None:
    error = RuntimeError("primary CUDA failure")
    error.add_note("cleanup failed for allocation 123")
    monkeypatch.setattr("sys.argv", ["cuda_integrity.py", "--_bounded-worker"])
    monkeypatch.setattr(cuda_integrity, "run", lambda *_args: (_ for _ in ()).throw(error))
    assert cuda_integrity.main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result == {"status": "fail", "error": "RuntimeError: primary CUDA failure",
                      "notes": ["cleanup failed for allocation 123"]}
    monkeypatch.setattr(cuda_integrity, "run", lambda *_args: (_ for _ in ()).throw(KeyboardInterrupt("cancel")))
    with pytest.raises(KeyboardInterrupt, match="cancel"):
        cuda_integrity.main()
    capsys.readouterr()


def test_debt_broad_except_cgroup_repro_113(monkeypatch: pytest.MonkeyPatch,
                                           capsys: pytest.CaptureFixture[str]) -> None:
    from test_cgroup_repro import cuda_runtime

    runtime, events = cuda_runtime(monkeypatch, memset_result=17, fail_sync=3)
    runtime.cudaFree.callback = lambda ptr: events.append("free") or (0 if ptr is None else 23)
    assert cgroup_repro.cuda_worker("cuda_malloc", 1) == 33
    result = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert result["phase"] == "error"
    assert result["error"] == "RuntimeError: cudaMemset returned CUDA error 17"
    assert any("cudaFree returned CUDA error 23" in note for note in result["notes"])
    assert any("release cudaDeviceSynchronize returned CUDA error 44" in note for note in result["notes"])
    assert events.count("free") == 2  # warmup plus the one allocation cleanup attempt
    assert events.count("sync") == 3  # cleanup sync runs even after cudaFree reports failure

    runtime, events = cuda_runtime(monkeypatch, fail_sync=3)
    runtime.cudaMemset.callback = lambda *_args: (_ for _ in ()).throw(KeyboardInterrupt("cancel allocation"))
    runtime.cudaFree.callback = lambda ptr: events.append("free") or (
        0 if ptr is None else (_ for _ in ()).throw(RuntimeError("free teardown failed")))
    with pytest.raises(KeyboardInterrupt, match="cancel allocation") as cancelled:
        cgroup_repro.cuda_worker("cuda_malloc", 1)
    assert events.count("sync") == 3
    assert any("free teardown failed" in note for note in cancelled.value.__notes__)
    assert any("CUDA error 44" in note for note in cancelled.value.__notes__)


def test_debt_broad_except_cgroup_repro_150(monkeypatch: pytest.MonkeyPatch,
                                           capsys: pytest.CaptureFixture[str]) -> None:
    worker_result, result, events = _observe_torch_primary_cleanup(monkeypatch, capsys)
    cancellation, cancel_events = _observe_torch_cancellation_cleanup(monkeypatch)
    assert worker_result == 30
    assert result["error"] == "RuntimeError: fill failed"
    assert any("sync teardown 3 failed" in note for note in result["notes"])
    assert any("empty_cache teardown failed" in note for note in result["notes"])
    assert any("sync teardown 4 failed" in note for note in result["notes"])
    assert events.count("empty_cache") == 2
    assert cancellation["exception"] == "KeyboardInterrupt"
    assert cancellation["message"] == "cancel fill"
    assert any("cancel teardown sync 3" in note for note in cancellation["notes"])
    assert any("cancel teardown sync 4" in note for note in cancellation["notes"])
    assert cancel_events.count("empty_cache") == 2


def _observe_torch_primary_cleanup(monkeypatch, capsys):
    import sys
    from test_cgroup_repro import fake_torch

    events = []
    torch = fake_torch(events, fail_fill=True)
    sync_calls = 0

    def failing_sync():
        nonlocal sync_calls
        sync_calls += 1
        events.append("sync")
        if sync_calls > 2:
            raise RuntimeError(f"sync teardown {sync_calls} failed")

    empty_cache_calls = 0

    def failing_empty_cache():
        nonlocal empty_cache_calls
        empty_cache_calls += 1
        events.append("empty_cache")
        if empty_cache_calls > 1:
            raise RuntimeError("empty_cache teardown failed")

    torch.cuda.synchronize = failing_sync
    setattr(torch.cuda, "empty_cache", failing_empty_cache)
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setattr(cgroup_repro, "snapshot", lambda _pid: {"pid": 12})
    monkeypatch.setattr(cgroup_repro.time, "sleep", lambda _seconds: None)
    worker_result = cgroup_repro.torch_worker(1)
    result = json.loads(capsys.readouterr().out.splitlines()[-1])
    return worker_result, result, events


def _observe_torch_cancellation_cleanup(monkeypatch):
    import sys
    from test_cgroup_repro import fake_torch

    class CancelTensor:
        def __init__(self, events, cancel):
            self.events = events
            self.cancel = cancel
        def fill_(self, _value):
            self.events.append("fill")
            if self.cancel:
                raise KeyboardInterrupt("cancel fill")

    events = []
    torch = fake_torch(events)
    tensor_count = 0
    original_empty = torch.empty

    def cancel_second_fill(*args, **kwargs):
        nonlocal tensor_count
        tensor_count += 1
        original_empty(*args, **kwargs)
        return CancelTensor(events, tensor_count > 1)

    setattr(torch, "empty", cancel_second_fill)
    sync_calls = 0
    def failing_cancel_sync():
        nonlocal sync_calls
        sync_calls += 1
        events.append("sync")
        if sync_calls > 2:
            raise RuntimeError(f"cancel teardown sync {sync_calls}")

    torch.cuda.synchronize = failing_cancel_sync
    monkeypatch.setitem(sys.modules, "torch", torch)
    with pytest.raises(KeyboardInterrupt, match="cancel fill") as cancelled:
        cgroup_repro.torch_worker(1)
    observation = {"exception": type(cancelled.value).__name__,
                   "message": str(cancelled.value),
                   "notes": cancelled.value.__notes__}
    return observation, events



def _run_without_skips(selection: str) -> int:
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", selection],
        capture_output=True, text=True, cwd=root, timeout=60,
    )
    output = result.stdout + result.stderr
    assert " skipped" not in output, output
    assert "COULD_NOT_RUN" not in output, output
    return result.returncode


def test_debt_skip_test_calibra_techo_slice_164():
    assert _run_without_skips(
        "tests/test_calibra_techo_slice.py::test_una_muestra_ILEGIBLE_no_se_traga_en_silencio"
    ) == 0


def test_debt_skip_test_calibra_techo_slice_263():
    assert _run_without_skips(
        "tests/test_calibra_techo_slice.py::test_un_directorio_SIN_PERMISO_se_registra_y_no_pasa_por_vacio"
    ) == 0


def test_debt_skip_test_calibra_techo_slice_315():
    assert _run_without_skips(
        "tests/test_calibra_techo_slice.py::test_el_informe_NOMBRA_los_ficheros_ilegibles"
    ) == 0


def test_debt_skip_test_control_racha_118():
    assert _run_without_skips(
        "tests/test_control_racha.py::test_el_gate_sale_0_sobre_el_corpus_real"
    ) == 0


def test_debt_skip_test_control_racha_130():
    assert _run_without_skips(
        "tests/test_control_racha.py::test_control_negativo_el_gate_SI_sale_1_con_el_corte_bajado"
    ) == 0


def test_debt_skip_test_demonio_al_dia_52():
    assert _run_without_skips("tests/test_demonio_al_dia.py") == 0


def test_debt_skip_test_pii_scan_systemd_167():
    assert _run_without_skips("tests/test_pii_scan_systemd.py") == 0


def test_debt_skip_test_pii_scan_systemd_86():
    assert _run_without_skips("tests/test_pii_scan_systemd.py") == 0


def _simplecode_runner(tmp_path: Path) -> Path:
    """Copy the pinned ignored kit into a disposable subject repo for organ tests."""
    source = Path(__file__).resolve().parent.parent / ".simplecode"
    target = tmp_path / ".simplecode"
    target.mkdir()
    for name in ("run.py", "runtime.zip", "kit.lock"):
        (target / name).write_bytes((source / name).read_bytes())
    return target / "run.py"


def test_debt_exception_backlog_md_freeze_01() -> None:
    """Simplecode retired the organ; BB retains neither its subject nor exemption."""
    from zipfile import ZipFile

    repo = Path(__file__).resolve().parent.parent
    with ZipFile(repo / ".simplecode" / "runtime.zip") as runtime:
        assert "simplecode/verification/backlog_md_freeze.py" not in runtime.namelist()
    config = (repo / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "backlog_md_freeze" not in config
    exemptions = json.loads((repo / ".simplecode" / "organ_inapplicable.json").read_text(encoding="utf-8"))
    assert "backlog_md_freeze" not in exemptions["entries"]
    assert not (repo / "BACKLOG.md").exists()
    assert not (repo / ".simplecode" / "backlog_md_frozen.json").exists()


def test_debt_exception_lockfile_parity_01(tmp_path: Path) -> None:
    runner = _simplecode_runner(tmp_path)
    repo = Path(__file__).resolve().parent.parent
    current = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.lockfile_parity", "--root", str(repo)],
        capture_output=True, text=True, check=False,
    )
    assert current.returncode == 0, current.stdout + current.stderr
    assert "NO APLICA: no hay requirements-lock.txt" in current.stdout

    root = tmp_path / "subject"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\ndependencies = ["synthetic-pkg==1.0"]\n', encoding="utf-8")
    (root / "requirements-lock.txt").write_text("synthetic-pkg==2.0\n", encoding="utf-8")
    negative = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.lockfile_parity", "--root", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert negative.returncode == 1, negative.stdout + negative.stderr
    assert "DIVERGE synthetic-pkg" in negative.stdout


def test_debt_exception_red_team_corpus_01(tmp_path: Path) -> None:
    runner = _simplecode_runner(tmp_path)
    repo = Path(__file__).resolve().parent.parent
    current = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.red_team_corpus", "--root", str(repo), "--gate"],
        capture_output=True, text=True, check=False,
    )
    assert current.returncode == 0, current.stdout + current.stderr
    assert "generados hoy: 91" in current.stdout
    assert "casos registrados: 0" in current.stdout

    root = tmp_path / "subject"
    (root / "tasks").mkdir(parents=True)
    (root / "tasks" / "red_team_corpus.json").write_text(
        '{"casos":{"synthetic/removed":{"first_seen":"2026-10-02"}}}\n', encoding="utf-8")
    negative = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.red_team_corpus", "--root", str(root), "--gate"],
        capture_output=True, text=True, check=False,
    )
    assert negative.returncode == 1, negative.stdout + negative.stderr
    assert "FAIL: 1 caso(s) adversarial(es)" in negative.stderr


def _fake_observation_clock(monkeypatch: pytest.MonkeyPatch, *, advances: bool) -> list[float]:
    elapsed = [0.0]
    monkeypatch.setattr(cgroup_repro, "snapshot", lambda _pid: {"monotonic_ns": int(elapsed[0] * 1_000_000_000)})
    monkeypatch.setattr(cgroup_repro.time, "sleep", lambda seconds: elapsed.__setitem__(0, elapsed[0] + (seconds if advances else 0.0)))
    return elapsed


def _phase_times(output: str) -> dict[str, int]:
    return {event["phase"]: event["monotonic_ns"] for event in map(json.loads, output.splitlines())}


def test_debt_sunset_cgroup_repro_107(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """CUDA path retains allocation for the observation window, using mocked CUDA calls."""
    class Call:
        argtypes = None
        restype = None
        def __call__(self, *args):
            if args and hasattr(args[0], "_obj"):
                args[0]._obj.value = 1234
            return 0
    class Runtime:
        cudaMalloc = Call()
        cudaMallocManaged = Call()
        cudaMemset = Call()
        cudaFree = Call()
        cudaDeviceSynchronize = Call()
    monkeypatch.setattr(cgroup_repro.ctypes.util, "find_library", lambda _name: "libcudart-test")
    monkeypatch.setattr(cgroup_repro.ctypes, "CDLL", lambda _name: Runtime())
    elapsed = _fake_observation_clock(monkeypatch, advances=True)
    assert cgroup_repro.cuda_worker("cuda_malloc", 1) == 0
    held = _phase_times(capsys.readouterr().out)
    assert held["after_release"] - held["held"] >= 2_000_000_000
    assert elapsed[0] == 2

    _fake_observation_clock(monkeypatch, advances=False)
    assert cgroup_repro.cuda_worker("cuda_malloc", 1) == 0
    neutralized = _phase_times(capsys.readouterr().out)
    assert neutralized["after_release"] - neutralized["held"] < 2_000_000_000


def test_debt_sunset_cgroup_repro_149(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """PyTorch allocation path retains its live tensor for the bounded window; CUDA is mocked."""
    class Tensor:
        def fill_(self, _value):
            return self
    class Cuda:
        def is_available(self): return True
        def init(self): pass
        def synchronize(self): pass
        def empty_cache(self): pass
    fake_torch = types.SimpleNamespace(cuda=Cuda(), empty=lambda *_a, **_k: Tensor(), float16=object(), __version__="test")
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    elapsed = _fake_observation_clock(monkeypatch, advances=True)
    assert cgroup_repro.torch_worker(1) == 0
    held = _phase_times(capsys.readouterr().out)
    assert held["after_release"] - held["held"] >= 2_000_000_000
    assert elapsed[0] == 2

    _fake_observation_clock(monkeypatch, advances=False)
    assert cgroup_repro.torch_worker(1) == 0
    neutralized = _phase_times(capsys.readouterr().out)
    assert neutralized["after_release"] - neutralized["held"] < 2_000_000_000


def test_debt_sunset_cgroup_repro_167(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """CPU allocation worker exposes held and released phases across the same window."""
    elapsed = _fake_observation_clock(monkeypatch, advances=True)
    assert cgroup_repro.memory_worker("cpu_touch", 1) == 0
    held = _phase_times(capsys.readouterr().out)
    assert held["after_release"] - held["held"] >= 2_000_000_000
    assert elapsed[0] == 2

    _fake_observation_clock(monkeypatch, advances=False)
    assert cgroup_repro.memory_worker("cpu_touch", 1) == 0
    neutralized = _phase_times(capsys.readouterr().out)
    assert neutralized["after_release"] - neutralized["held"] < 2_000_000_000


def test_debt_sunset_atom_gpu_telemetry_1671(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from tools import atom_gpu_telemetry as telemetry

    calls: list[float] = []
    samples = [0]
    elapsed = [0.0]
    observed: list[float] = []
    monkeypatch.setattr(telemetry.time, "monotonic", lambda: elapsed[0])
    def one_sample_then_stop(*_args, **_kwargs):
        if samples[0]:
            observed.append(elapsed[0])
            assert observed[-1] - observed[-2] == 0.25
            raise KeyboardInterrupt
        observed.append(elapsed[0])
        samples[0] += 1
        return []
    monkeypatch.setattr(telemetry, "leer_umbrales", lambda: {})
    monkeypatch.setattr(telemetry, "muestrear", one_sample_then_stop)
    def advance(seconds: float) -> None:
        calls.append(seconds)
        elapsed[0] += seconds
    monkeypatch.setattr(telemetry.time, "sleep", advance)
    monkeypatch.setattr(sys, "argv", ["atom_gpu_telemetry", "--dry-run", "--interval-seconds", "0.25"])
    assert telemetry.main() == 0
    capsys.readouterr()
    assert calls == [0.25]
    assert samples[0] == 1

    calls.clear()
    elapsed[0] = 0.0
    samples[0] = 0
    observed.clear()
    with monkeypatch.context() as neutralized:
        neutralized.setattr(telemetry.time, "sleep", lambda _seconds: None)
        with pytest.raises(AssertionError):
            telemetry.main()


def test_debt_sunset_test_bb_bash_1550(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[float] = []
    now = [0.0]
    monkeypatch.setattr(bash_tests.subprocess, "run", lambda *_a, **_k: types.SimpleNamespace(stdout=""))
    monkeypatch.setattr(bash_tests.time, "time", lambda: now[0])
    def yielding_sleep(seconds: float) -> None:
        calls.append(seconds)
        now[0] += seconds
    monkeypatch.setattr(bash_tests.time, "sleep", yielding_sleep)
    with pytest.raises(AssertionError, match="ningun proceso"):
        bash_tests._esperar_proceso("synthetic-absent", timeout=0.1)
    assert calls == [0.05, 0.05]


def test_debt_sunset_test_bb_bash_1602(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[float] = []
    counter = [0]
    killpg_calls = []
    wait_calls = []
    class Result:
        def __init__(self, stdout): self.stdout = stdout
    def pgrep_until_absent(*_args, **_kwargs):
        counter[0] += 1
        return Result("4242\n") if counter[0] < 3 else Result("")
    monkeypatch.setattr(bash_tests.subprocess, "run", pgrep_until_absent)
    monkeypatch.setattr(bash_tests.time, "sleep", lambda seconds: calls.append(seconds))
    monkeypatch.setattr(bash_tests.os, "killpg",
                        lambda pid, sig: killpg_calls.append((pid, sig)))
    class Parent:
        pid = 4242
        def wait(self, **kwargs): wait_calls.append(kwargs)
    remaining = bash_tests._matar_electron_falso(
        Parent(), ["synthetic-renderer"], timeout=1)
    assert remaining == [""]
    assert counter[0] == 3
    assert killpg_calls == [(4242, bash_tests.signal.SIGKILL)]
    assert wait_calls == [{"timeout": 1}]
    assert calls == [0.05, 0.05]


def _fresh_bb_data(tmp_path: Path, name: str) -> Path:
    data = tmp_path / name
    (data / "samples").mkdir(parents=True)
    return data


def test_debt_sunset_test_bb_bash_322(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bash_tests.test_swap_mide_el_RITMO_no_solo_el_nivel(_fresh_bb_data(tmp_path, "positive"), tmp_path)
    source = bash_tests.BB.read_text(encoding="utf-8")
    without_rate = source.replace('v=(a-b)/d', 'v=(a-b)')
    assert without_rate != source
    mutant = tmp_path / "bb-without-rate-normalization"
    mutant.write_text(without_rate, encoding="utf-8")
    mutant.chmod(0o755)
    mutant_tmp = tmp_path / "rate-mutant-inputs"
    mutant_tmp.mkdir()
    with monkeypatch.context() as sourcecopy:
        sourcecopy.setattr(bash_tests, "BB", mutant)
        with pytest.raises(AssertionError):
            bash_tests.test_swap_mide_el_RITMO_no_solo_el_nivel(
                _fresh_bb_data(tmp_path, "rate-mutant"), mutant_tmp)


def test_debt_sunset_test_bb_bash_339(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = _fresh_bb_data(tmp_path, "negative")
    bash_tests.test_control_negativo_sin_trafico_de_swap_el_ritmo_es_cero(data, tmp_path)
    assert bash_tests.muestras(data)[-1]["swap"]["in_pag_s"] == 0.0


def test_debt_sunset_test_bb_bash_352(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bash_tests.test_un_contador_que_RETROCEDE_no_produce_un_ritmo_negativo(
        _fresh_bb_data(tmp_path, "negative-counter"), tmp_path)
    original = bash_tests.BB.read_text(encoding="utf-8")
    vulnerable = original.replace('printf "%.1f", (v>0?v:0)', 'printf "%.1f", v')
    assert vulnerable != original
    mutant = tmp_path / "bb-without-swap-clamp"
    mutant.write_text(vulnerable, encoding="utf-8")
    mutant.chmod(0o755)
    mutant_data = _fresh_bb_data(tmp_path, "mutant-counter")
    mutant_tmp = tmp_path / "mutant-inputs"
    mutant_tmp.mkdir()
    (tmp_path / "date-count").unlink(missing_ok=True)
    with monkeypatch.context() as sourcecopy:
        sourcecopy.setattr(bash_tests, "BB", mutant)
        with pytest.raises(AssertionError) as mutant_failure:
            bash_tests.test_un_contador_que_RETROCEDE_no_produce_un_ritmo_negativo(mutant_data, mutant_tmp)
    assert "-899988.0" in str(mutant_failure.value)


def test_debt_sunset_test_bb_bash_766(tmp_path: Path) -> None:
    data = _fresh_bb_data(tmp_path, "cpu-positive")
    bash_tests.test_cpu_top_NOMBRA_a_quien_quema_cpu(data)
    assert "cpu_top" in bash_tests.muestras(data)[-1]


def test_debt_sunset_test_bb_bash_802(tmp_path: Path) -> None:
    data = _fresh_bb_data(tmp_path, "cpu-negative")
    bash_tests.test_control_negativo_un_proceso_dormido_no_sale_como_que_quema(data)
    assert "cpu_top" in bash_tests.muestras(data)[-1]



def test_debt_coverage_targets_bin_usable_01(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parent.parent
    executable = root / "bin" / "bb-usable"
    env = os.environ.copy()
    env["COVERAGE_FILE"] = str(tmp_path / ".coverage")
    loaded = bb_usable_tests._cargar()
    loaded_path = loaded.__dict__.get("__file__")
    assert isinstance(loaded_path, str)
    assert executable.suffix == "" and Path(loaded_path).resolve() == executable

    measured = subprocess.run(
        ["coverage", "run", "--branch", "--source=bin", "-m", "pytest", "-q",
         "tests/test_bb_usable.py"],
        capture_output=True, text=True, cwd=root, env=env, timeout=120, check=False,
    )
    assert measured.returncode == 0, measured.stdout + measured.stderr
    assert " passed" in measured.stdout, measured.stdout + measured.stderr
    assert "skipped" not in measured.stdout and "could_not_run" not in measured.stdout
    report = subprocess.run(
        ["coverage", "report"], capture_output=True, text=True, cwd=root, env=env,
        timeout=30, check=False,
    )
    assert report.returncode == 0, report.stdout + report.stderr
    row = next((line for line in report.stdout.splitlines()
                if line.split()[:1] == ["bin/bb-usable"]), "")
    assert row and int(row.split()[1]) > 0, report.stdout

    original = executable.read_text(encoding="utf-8")
    mutated = original.replace(
        'return float(field.split("=", 1)[1])', "return -1.0", 1)
    assert mutated != original
    mutant = tmp_path / "bb-usable-mutant"
    mutant.write_text(mutated, encoding="utf-8")
    run_dir = tmp_path / "mutated-test"
    run_dir.mkdir()
    monkeypatch.setattr(bb_usable_tests, "RUTA", mutant)
    with pytest.raises(AssertionError):
        bb_usable_tests.test_lee_el_full_avg10(
            bb_usable_tests._cargar(), run_dir, monkeypatch)


def test_debt_no_cover_test_atom_gpu_telemetry_bb_85(monkeypatch):
    subject = atom_tests.agt
    atom_tests.test_vllm_con_status_distinto_de_200_lo_DECLARA(monkeypatch)

    def reads_non_200_body(url, timeout_s=subject.VLLM_METRICS_TIMEOUT_S):
        req = subject.urllib.request.Request(
            url, headers={"User-Agent": "Atlas-Telemetry/1.0"})
        with subject.urllib.request.urlopen(req, timeout=timeout_s) as response:
            response.read()

    monkeypatch.setattr(subject, "leer_vllm_metrics", reads_non_200_body)
    with pytest.raises(AttributeError, match="read"):
        atom_tests.test_vllm_con_status_distinto_de_200_lo_DECLARA(monkeypatch)


def test_bug_provider_trace_latency_overflow_01(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture = Path(__file__).parent / "fixtures" / "provider_trace" / "gpu-healthy.jsonl"
    records = [json.loads(line) for line in fixture.read_text(encoding="utf-8").splitlines()]
    for latency in (10**400, -10**400, True, -1, float("inf"), float("nan")):
        trace = [dict(record, milliseconds=latency) if record["event"] == "latency" else record for record in records]
        path = tmp_path / "trace.jsonl"
        path.write_text("\n".join(json.dumps(record) for record in trace), encoding="utf-8")
        assert provider_trace.main([str(path)]) == 2
        result = json.loads(capsys.readouterr().out)
        assert result["status"] == "unknown"
        assert result["could_not_run_count"] == 0
        assert any("invalid latency" in item for item in result["unknowns"])
    for latency in (0, 1, 1.5):
        trace = [json.dumps(dict(record, milliseconds=latency) if record["event"] == "latency" else record) for record in records]
        assert provider_trace.analyze_lines(trace)["status"] == "pass"
    fallback = fixture.with_name("gpu-to-cpu-respawn.jsonl")
    assert provider_trace.analyze_file(fallback)["status"] == "block"


def test_debt_noqa_bb_usable_249(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    executable = Path(__file__).resolve().parent.parent / "bin" / "bb-usable"
    lint = subprocess.run(["python3", "-m", "ruff", "check", "--select", "E731", "--ignore-noqa", str(executable)],
                          capture_output=True, text=True, check=False)
    assert lint.returncode == 0, lint.stdout + lint.stderr
    module = bb_usable_tests._cargar()
    monkeypatch.setattr(module, "notify", lambda message: None)
    monkeypatch.setattr(module, "probe", lambda: 0.001)

    def stop(_seconds: float) -> None:
        raise RuntimeError("stop before sampling")

    monkeypatch.setattr(module.time, "sleep", stop)
    with pytest.raises(RuntimeError, match="stop before sampling"):
        module.main()
    assert "[bb-usable] sonda sana de referencia:" in capsys.readouterr().err


def test_debt_shellcheck_bb_2(tmp_path: Path) -> None:
    datos = tmp_path / "blackbox"
    executable = Path(__file__).resolve().parent.parent / "bin" / "bb"
    source = executable.read_text(encoding="utf-8").replace("# shellcheck disable=SC2319\n", "")
    candidate = tmp_path / "status.sh"
    candidate.write_text(source, encoding="utf-8")
    lint = subprocess.run(["shellcheck", "--include=SC2319", str(candidate)], capture_output=True, text=True, check=False)
    assert lint.returncode == 0, lint.stdout + lint.stderr
    for low, expected in ((2 * 1024**3, "ARMADO"), (0, "FALTA")):
        result = correr(["status"], datos, _arbol_cgroup(tmp_path, low=low))
        assert expected in _fila_escritorio(result)


def test_debt_shellcheck_bb_2286(tmp_path: Path) -> None:
    datos = tmp_path / "blackbox"
    for low, expected in ((2 * 1024**3, "ARMADO"), (0, "FALTA")):
        result = correr(["status"], datos, _arbol_cgroup(tmp_path / "cgroups with spaces", low=low))
        assert expected in _fila_escritorio(result), result.stdout + result.stderr


def _run_script(path: Path, argv: list[str], expected: int) -> tuple[str, str]:
    root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, str(path), *argv], cwd=root, env=env,
        text=True, capture_output=True, timeout=10, check=False)
    assert result.returncode == expected, result.stdout + result.stderr
    return result.stdout, result.stderr


def _assert_no_cover_entrypoint(script: str, tmp_path: Path) -> None:
    import re

    source = Path(__file__).resolve().parent.parent / "tools" / script
    if script == "check_harvest_accepted.py":
        accepted = tmp_path / "accepted.md"
        accepted.write_text(
            '---\nid: HARVEST-TEST\naccepted: {by: maintainer, date: "2026-10-02", trigger: reopen-on-regression}\n---\n',
            encoding="utf-8")
        out, _ = _run_script(source, [str(accepted)], 0)
        assert "accepted completo" in out
        out, err = _run_script(source, [], 2)
        assert "uso:" in err
    elif script == "control_racha.py":
        samples = tmp_path / "samples"
        samples.mkdir()
        (samples / "valid.jsonl").write_text(
            '{"ts":"2026-09-15T03:00:00-0600","psi":{"mem_full":0}}\n',
            encoding="utf-8")
        out, _ = _run_script(source, ["--muestras", str(samples)], 0)
        assert "corpus 1 muestras" in out
        _, err = _run_script(source, ["--codex-invalid-argument"], 2)
        assert "unrecognized arguments" in err
    else:
        out, _ = _run_script(source, ["--help"], 0)
        assert "usage:" in out.lower()
        _, err = _run_script(source, ["--codex-invalid-argument"], 2)
        assert "unrecognized arguments" in err

    # A flipped launcher exit is the mutation this regression must catch.
    original = source.read_text(encoding="utf-8")
    if script == "check_harvest_accepted.py":
        mutated = original.replace("    main()\n", "    sys.exit(0)\n")
    else:
        mutated, count = re.subn(
            r"(?m)^if __name__ == [\"']__main__[\"']:\s*(?:#.*)?\n\s*(?:sys\.exit|raise SystemExit)\(main\(\)\)",
            'if __name__ == "__main__":\n    sys.exit(0)', original, count=1)
        assert count == 1
    mutant = tmp_path / script
    mutant.write_text(mutated, encoding="utf-8")
    if script == "check_harvest_accepted.py":
        mutant_argv = []
    else:
        mutant_argv = ["--codex-invalid-argument"]
    with pytest.raises(AssertionError):
        _run_script(mutant, mutant_argv, 2)


def test_debt_no_cover_atom_gpu_telemetry_1676(tmp_path):
    _assert_no_cover_entrypoint("atom_gpu_telemetry.py", tmp_path)


def test_debt_no_cover_calibra_latencia_x_333(tmp_path):
    _assert_no_cover_entrypoint("calibra_latencia_x.py", tmp_path)


def test_debt_no_cover_calibra_psi_322(tmp_path):
    _assert_no_cover_entrypoint("calibra_psi.py", tmp_path)


def test_debt_no_cover_calibra_techo_slice_226(tmp_path):
    _assert_no_cover_entrypoint("calibra_techo_slice.py", tmp_path)


def test_debt_no_cover_check_harvest_accepted_157(tmp_path):
    _assert_no_cover_entrypoint("check_harvest_accepted.py", tmp_path)


def test_debt_no_cover_control_racha_160(tmp_path):
    _assert_no_cover_entrypoint("control_racha.py", tmp_path)


def test_debt_no_cover_inventario_146(tmp_path):
    _assert_no_cover_entrypoint("inventario.py", tmp_path)


def test_debt_no_cover_mutacion_alcanza_66(tmp_path):
    _assert_no_cover_entrypoint("mutacion_alcanza.py", tmp_path)


def test_debt_no_cover_nombra_victimas_271(tmp_path):
    _assert_no_cover_entrypoint("nombra_victimas.py", tmp_path)


def test_debt_no_cover_presupuesto_memoria_497(tmp_path):
    _assert_no_cover_entrypoint("presupuesto_memoria.py", tmp_path)


def test_debt_shellcheck_bb_subject_01(tmp_path: Path) -> None:
    data = tmp_path / "data"
    audit = tmp_path / "audit with spaces"
    audit.mkdir()
    now = int(time.time())
    (audit / "audit.log.1").write_text(_syscall(now - 300, 9101, pid=1111, comm='"old"'), encoding="utf-8")
    (audit / "audit.log").write_text(_syscall(now - 10, 9102, pid=2222, comm='"new"'), encoding="utf-8")
    result = correr(["sigterm", "10 minutes ago"], data, {"BLACKBOX_AUDIT_DIR": str(audit)})
    assert "old[1111]" in result.stdout, result.stdout + result.stderr
    assert "new[2222]" in result.stdout, result.stdout + result.stderr
    assert "el registro cubre:" in result.stdout
    for path in audit.iterdir():
        path.write_text(_syscall(now - 10, 9103, pid=3333, key="unrelated"), encoding="utf-8")
    negative = correr(["sigterm", "10 minutes ago"], data, {"BLACKBOX_AUDIT_DIR": str(audit)})
    assert "0 senales registradas" in negative.stdout
    assert "3333" not in negative.stdout


def test_debt_research_collector_bb_forum_fetch_01(tmp_path: Path) -> None:
    """Close check: maintained fetcher passes offline positive and negative controls."""
    from test_bb_forum_collectors import test_fetch_valid_incomplete_error_retry_timeout_and_io

    assert test_fetch_valid_incomplete_error_retry_timeout_and_io(tmp_path) is None


def test_debt_research_collector_bb_forum_inventory_01(tmp_path: Path) -> None:
    """Close check: inventory pagination and duplicate-page controls pass offline."""
    from test_bb_forum_collectors import test_inventory_pages_deduplicates_and_rejects_repeated_page

    assert test_inventory_pages_deduplicates_and_rejects_repeated_page(tmp_path) is None
