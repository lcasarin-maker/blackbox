from __future__ import annotations

import json
import os
from pathlib import Path
import pytest
import shutil
import subprocess
import sys
from types import SimpleNamespace
from tools import nvme_readonly


def _snapshot(*, mount_ro: bool = False, signals: dict | None = None,
              inventory: dict | None = None) -> dict:
    return {"checks": {"storage": {
        "root_mounts": {"status": "ok", "value": [{"target": "/", "options": "ro" if mount_ro else "rw",
                                                             "read_only": mount_ro}]},
        "nvme_inventory": inventory or {"status": "ok", "stdout": "[{\"DevicePath\":\"/dev/nvme0n1\",\"SerialNumber\":\"fixture-serial\"}]"},
    }, "kernel_signals": signals or {"status": "ok", "stdout": "healthy boot"}}}


def test_nvme_report_distinguishes_media_error_readonly_unknown_and_healthy() -> None:
    healthy = nvme_readonly.classify(_snapshot())
    assert healthy["status"] == "pass" and healthy["could_not_run"] == 0
    assert healthy["writes_performed"] is False
    assert "physical device health remains unproven" in healthy["claim"]
    media = nvme_readonly.classify(_snapshot(signals={"status": "ok", "stdout": "nvme nvme0: I/O error"}))
    assert media["status"] == "fail" and media["fail"] == 1
    readonly = nvme_readonly.classify(_snapshot(mount_ro=True))
    assert readonly["status"] == "fail" and "read-only root mount" in readonly["findings"]
    unavailable = nvme_readonly.classify(_snapshot(inventory={"status": "could_not_run"}))
    assert unavailable["status"] == "could_not_run" and unavailable["could_not_run"] == 1
    malformed = nvme_readonly.classify(_snapshot(inventory={"status": "ok", "stdout": "not-json"}))
    assert malformed["status"] == "could_not_run" and malformed["could_not_run"] == 1
    unidentifiable = nvme_readonly.classify(_snapshot(inventory={
        "status": "ok", "stdout": "[{\"DevicePath\":\"/dev/nvme0n1\"}]"}))
    assert unidentifiable["status"] == "could_not_run"
    empty_inventory = nvme_readonly.classify(_snapshot(inventory={"status": "ok", "stdout": "[]"}))
    assert empty_inventory["status"] == "could_not_run"
    unrelated_io = nvme_readonly.classify(_snapshot(signals={
        "status": "ok", "stdout": "usb 1-1: I/O error"}))
    assert unrelated_io["status"] == "pass"
    unrelated_io_other_line = nvme_readonly.classify(_snapshot(signals={
        "status": "ok", "stdout": "nvme nvme0: controller ready\nusb 1-1: I/O error"}))
    assert unrelated_io_other_line["status"] == "pass"
    empty_mounts = _snapshot()
    empty_mounts["checks"]["storage"]["root_mounts"]["value"] = []
    assert nvme_readonly.classify(empty_mounts)["status"] == "could_not_run"
    missing_root = _snapshot()
    missing_root["checks"]["storage"]["root_mounts"]["value"] = [
        {"target": "/models", "options": "rw", "read_only": False}]
    assert nvme_readonly.classify(missing_root)["status"] == "could_not_run"
    duplicate_root = _snapshot()
    duplicate_root["checks"]["storage"]["root_mounts"]["value"].append(
        {"target": "/", "options": "rw", "read_only": False})
    assert nvme_readonly.classify(duplicate_root)["status"] == "could_not_run"


def test_export_requires_separate_filesystem_and_never_overwrites(tmp_path: Path) -> None:
    source = tmp_path / "identified-copy.img"
    source.write_bytes(b"immutable test copy")
    same_filesystem = nvme_readonly.export_copy(source, tmp_path / "backup")
    assert same_filesystem["status"] == "could_not_run"
    assert (same_filesystem["fail"], same_filesystem["could_not_run"]) == (0, 1)
    assert source.read_bytes() == b"immutable test copy"

    shm = Path("/dev/shm")
    if not shm.is_dir() or os.stat(source).st_dev == os.stat(shm).st_dev:
        return
    destination = shm / f"nvme-readonly-test-{os.getpid()}"
    destination.mkdir(mode=0o700)
    try:
        root = Path(__file__).resolve().parents[1]
        command = [sys.executable, "-m", "tools.nvme_readonly", "--export-source", str(source),
                   "--destination-dir", str(destination)]
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        assert completed.returncode == 0
        copied = json.loads(completed.stdout)
        assert copied["status"] == "pass" and copied["source_written"] is False
        assert (copied["fail"], copied["could_not_run"]) == (0, 0)
        target = Path(copied["destination"])
        assert target.read_bytes() == source.read_bytes()
        duplicate = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        assert duplicate.returncode == 2 and json.loads(duplicate.stdout)["status"] == "could_not_run"
    finally:
        shutil.rmtree(destination)


def test_nvme_cli_reads_snapshot_and_exports_identified_copy(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps(_snapshot()), encoding="utf-8")
    command = [sys.executable, "-m", "tools.nvme_readonly", "--snapshot", str(snapshot)]
    report = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    assert report.returncode == 0
    assert json.loads(report.stdout)["status"] == "pass"

    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    unavailable = subprocess.run([*command[:4], str(bad)], cwd=root,
                                 capture_output=True, text=True, check=False)
    assert unavailable.returncode == 2
    assert json.loads(unavailable.stdout)["could_not_run"] == 1


def test_nvme_main_reports_fail_and_refuses_incomplete_export(tmp_path: Path,
                                                               capsys: pytest.CaptureFixture[str]) -> None:
    snapshot = tmp_path / "bad-media.json"
    snapshot.write_text(json.dumps(_snapshot(signals={"status": "ok", "stdout": "nvme nvme0: I/O error"})),
                        encoding="utf-8")
    assert nvme_readonly.main(["--snapshot", str(snapshot)]) == 1
    assert json.loads(capsys.readouterr().out)["fail"] == 1
    with pytest.raises(SystemExit) as error:
        nvme_readonly.main(["--export-source", str(snapshot)])
    assert error.value.code == 2


def test_copy_removes_partial_destination_when_source_changes(tmp_path: Path,
                                                               monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source-copy"
    source.write_bytes(b"source contents")
    target = tmp_path / "recovery-copy"
    real_fstat = os.fstat
    calls = 0

    def changing_fstat(fd: int):
        nonlocal calls
        calls += 1
        current = real_fstat(fd)
        if calls == 1:
            return current
        return SimpleNamespace(st_dev=current.st_dev, st_ino=current.st_ino,
                               st_size=current.st_size, st_mtime_ns=current.st_mtime_ns + 1,
                               st_ctime_ns=current.st_ctime_ns)

    monkeypatch.setattr(nvme_readonly.os, "fstat", changing_fstat)
    with pytest.raises(OSError, match="source changed during copy"):
        nvme_readonly._copy_file(source, target, source.stat())
    assert source.read_bytes() == b"source contents"
    assert not target.exists()


def test_copy_refuses_destination_without_capacity(tmp_path: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source-copy"
    source.write_bytes(b"data")
    destination = tmp_path / "separate"
    real_stat = Path.stat

    def destination_on_other_device(path: Path, *args, **kwargs):
        result = real_stat(path, *args, **kwargs)
        if path == destination:
            return SimpleNamespace(st_dev=result.st_dev + 1)
        return result

    monkeypatch.setattr(Path, "stat", destination_on_other_device)
    monkeypatch.setattr(nvme_readonly.shutil, "disk_usage",
                        lambda _path: SimpleNamespace(free=0))
    result = nvme_readonly.export_copy(source, destination)
    assert result["status"] == "could_not_run"
    assert "insufficient destination space" in result["error"]
    assert source.read_bytes() == b"data"


def test_copy_detects_path_replaced_with_same_bytes_and_timestamp(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source-copy"
    source.write_bytes(b"same bytes")
    expected = source.stat()
    original = tmp_path / "original-inode"
    real_fstat = os.fstat
    calls = 0

    def replace_path(fd: int):
        nonlocal calls
        calls += 1
        current = real_fstat(fd)
        if calls == 2:
            source.rename(original)
            source.write_bytes(b"same bytes")
            os.utime(source, ns=(expected.st_atime_ns, expected.st_mtime_ns))
        return current

    monkeypatch.setattr(nvme_readonly.os, "fstat", replace_path)
    target = tmp_path / "recovery-copy"
    with pytest.raises(OSError, match="source path changed during copy"):
        nvme_readonly._copy_file(source, target, expected)
    assert source.read_bytes() == original.read_bytes() == b"same bytes"
    assert not target.exists()


@pytest.mark.parametrize("record", [None, "not a record", []])
def test_capture_text_rejects_non_mapping_records(record: object) -> None:
    assert nvme_readonly._capture_text(record) == (None, "capture record malformed")


@pytest.mark.parametrize("record", [
    {"status": "error", "stdout": "ignored"},
    {"status": "ok", "stdout": None},
])
def test_capture_text_rejects_unavailable_status_or_output(record: dict) -> None:
    assert nvme_readonly._capture_text(record) == (None, "query status or output unavailable")


@pytest.mark.parametrize("document", ["", "42", "{\"Devices\":\"not-a-list\"}"])
def test_nvme_inventory_distinguishes_empty_from_malformed(document: str) -> None:
    observed = nvme_readonly._has_inventory_device(document)
    assert observed is (False if document == "" else None)


def test_kernel_signal_query_unavailable_stays_unknown() -> None:
    report = nvme_readonly.classify(_snapshot(signals={"status": "could_not_run"}))
    assert report["status"] == "could_not_run"
    assert report["could_not_run"] >= 1
    assert "kernel signal query query unavailable" in report["unknowns"]


def test_classify_reports_missing_checks_as_could_not_run() -> None:
    report = nvme_readonly.classify({"snapshot": "without checks"})
    assert report == {
        "status": "could_not_run", "fail": 0, "could_not_run": 1,
        "findings": ["snapshot checks missing"],
    }


def test_copy_rejects_source_changed_between_inventory_and_open(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source-copy"
    source.write_bytes(b"identified bytes")
    expected = source.stat()
    target = tmp_path / "recovery-copy"
    real_open = os.open

    def replace_before_open(path, flags, *args, **kwargs):
        if Path(path) == source:
            source.write_bytes(b"replacement bytes")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(nvme_readonly.os, "open", replace_before_open)
    with pytest.raises(OSError, match="source identity changed before copy"):
        nvme_readonly._copy_file(source, target, expected)
    assert source.read_bytes() == b"replacement bytes"
    assert not target.exists()


def test_copy_detects_destination_digest_mismatch_and_removes_copy(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source-copy"
    source.write_bytes(b"original bytes")
    target = tmp_path / "recovery-copy"
    monkeypatch.setattr(nvme_readonly, "_hash_file", lambda _path: "wrong-digest")
    with pytest.raises(OSError, match="destination copy digest mismatch"):
        nvme_readonly._copy_file(source, target, source.stat())
    assert source.read_bytes() == b"original bytes"
    assert not target.exists()


def test_export_refuses_symlink_source_without_touching_target(tmp_path: Path) -> None:
    original = tmp_path / "original"
    original.write_bytes(b"keep original")
    link = tmp_path / "suspect-link"
    link.symlink_to(original)
    result = nvme_readonly.export_copy(link, tmp_path / "elsewhere")
    assert result["status"] == "could_not_run"
    assert "regular file" in result["error"]
    assert original.read_bytes() == b"keep original"


def _read_nvme_capture(path: Path) -> dict:
    from datetime import datetime
    import uuid
    from tools.capture_io import read_regular_bytes, strict_json_loads

    raw = read_regular_bytes(path, 4 * 1024 * 1024)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError(f"capture exceeds size limit: {path.name}")
    value = strict_json_loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"capture must be an object: {path.name}")
    command = value.get("command")
    if (not isinstance(command, list) or not command
            or any(not isinstance(token, str) or not token for token in command)
            or type(value.get("returncode")) is not int
            or not isinstance(value.get("stdout"), str)
            or not isinstance(value.get("stderr"), str)):
        raise ValueError(f"raw command receipt is malformed: {path.name}")
    try:
        started = datetime.fromisoformat(value["started_at"].replace("Z", "+00:00"))
        finished = datetime.fromisoformat(value["finished_at"].replace("Z", "+00:00"))
        uuid.UUID(value["boot_id"])
    except (KeyError, AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"capture time or boot ID is malformed: {path.name}") from exc
    if (started.tzinfo is None or started.utcoffset() is None
            or finished.tzinfo is None or finished.utcoffset() is None
            or finished < started):
        raise ValueError(f"capture time ordering is invalid: {path.name}")
    return value


class _NVMeCaptureUnavailable(Exception):
    pass


def _nvme_stdout_json(capture: dict, label: str) -> object:
    from tools.capture_io import strict_json_loads

    if capture["returncode"] != 0:
        raise _NVMeCaptureUnavailable(f"raw {label} command returned {capture['returncode']}")
    return strict_json_loads(capture["stdout"])


def _index_copy_lab_cases(cases: object) -> dict[str, dict]:
    observed: dict[str, dict] = {}
    if not isinstance(cases, list):
        raise ValueError("copy lab cases are malformed")
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("case"), str):
            raise ValueError("copy lab case row is malformed")
        command = case.get("command")
        if (not isinstance(command, list) or len(command) < 3
                or command[0] != "python3" or command[1:3] != ["-m", "tools.nvme_readonly"]
                or type(case.get("exit_code")) is not int
                or not isinstance(case.get("stdout"), str)
                or not isinstance(case.get("stderr"), str)
                or case["case"] in observed):
            raise ValueError("copy lab command or case identity is invalid")
        observed[case["case"]] = case
    return observed


def _copy_command_paths(case: dict) -> tuple[str, str]:
    command = case["command"]
    values = []
    for flag in ("--export-source", "--destination-dir"):
        indexes = [index for index, item in enumerate(command) if item == flag]
        if len(indexes) != 1 or indexes[0] + 1 >= len(command):
            raise ValueError(f"copy lab command must specify one {flag}")
        values.append(command[indexes[0] + 1])
    if any(not Path(value).is_absolute() or ".." in Path(value).parts for value in values):
        raise ValueError("copy lab command contains unsafe paths")
    return values[0], values[1]


def _validate_copy_lab_outputs(lab: dict, observed: dict[str, dict]) -> None:
    import re
    from tools.capture_io import strict_json_loads

    expected_names = {"export-to-separate-filesystem", "overwrite-refused",
                      "same-filesystem-refused", "restore-copy-to-original-filesystem"}
    if not expected_names.issubset(observed):
        raise FileNotFoundError("copy lab lacks copy, refusal, or return-path records")
    if (type(lab.get("bytes")) is not int or lab["bytes"] <= 0
            or not isinstance(lab.get("source_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", lab["source_sha256"]) is None
            or lab.get("restored_sha256") != lab.get("source_sha256")
            or any(type(lab.get(key)) is not int for key in
                   ("pass", "negative_controls_observed", "unexpected_fail", "unexpected_could_not_run"))):
        raise ValueError("copy lab byte, digest, or restoration metadata contradicts")
    for name in ("export-to-separate-filesystem", "restore-copy-to-original-filesystem"):
        if observed[name]["exit_code"] != 0:
            raise ValueError(f"copy lab positive case returned nonzero: {name}")
    for name in ("overwrite-refused", "same-filesystem-refused"):
        if observed[name]["exit_code"] != 2:
            raise ValueError(f"copy lab refusal case returned unexpected code: {name}")
    outputs = {name: strict_json_loads(observed[name]["stdout"]) for name in expected_names}
    copy_out = outputs["export-to-separate-filesystem"]
    restore_out = outputs["restore-copy-to-original-filesystem"]
    refused = [outputs["overwrite-refused"], outputs["same-filesystem-refused"]]
    copy_source, copy_dir = _copy_command_paths(observed["export-to-separate-filesystem"])
    restore_source, restore_dir = _copy_command_paths(observed["restore-copy-to-original-filesystem"])
    overwrite_source, overwrite_dir = _copy_command_paths(observed["overwrite-refused"])
    samefs_source, samefs_dir = _copy_command_paths(observed["same-filesystem-refused"])
    if (not isinstance(copy_out, dict) or not isinstance(restore_out, dict)
            or any(not isinstance(item, dict) for item in refused)
            or copy_out.get("status") != "pass" or restore_out.get("status") != "pass"
            or copy_out.get("source_written") is not False or restore_out.get("source_written") is not False
            or any(item.get("status") != "could_not_run" or item.get("source_written") is not False
                   for item in refused)
            or any(output.get("sha256") != lab["source_sha256"]
                   or type(output.get("bytes")) is not int or output["bytes"] != lab["bytes"]
                   or type(output.get("source_device")) is not int
                   or type(output.get("destination_device")) is not int
                   or output["source_device"] < 0 or output["destination_device"] < 0
                   for output in (copy_out, restore_out))
            or copy_out.get("source") != copy_source
            or not isinstance(copy_out.get("destination"), str)
            or Path(copy_out["destination"]).parent != Path(copy_dir)
            or restore_source != copy_out.get("destination")
            or restore_out.get("source") != restore_source
            or not isinstance(restore_out.get("destination"), str)
            or Path(restore_out["destination"]).parent != Path(restore_dir)
            or (overwrite_source, overwrite_dir) != (copy_source, copy_dir)
            or samefs_source != copy_source or samefs_dir == copy_dir
            or copy_out.get("source_device") == copy_out.get("destination_device")
            or restore_out.get("source_device") == restore_out.get("destination_device")
            or lab.get("pass") != 2 or lab.get("negative_controls_observed") != 2
            or lab.get("unexpected_fail") != 0 or lab.get("unexpected_could_not_run") != 0
            or lab.get("fail") != 0 or lab.get("could_not_run") != 2):
        raise ValueError("copy lab outputs contradict hashes, refusals, or separate-device behavior")


def _validate_copy_lab(evidence: Path) -> None:
    from tools.capture_io import read_regular_bytes, strict_json_loads

    raw = read_regular_bytes(evidence / "export-copy-lab/run.json", 1024 * 1024)
    if len(raw) > 1024 * 1024:
        raise ValueError("copy lab receipt exceeds size limit")
    lab = strict_json_loads(raw.decode("utf-8"))
    if not isinstance(lab, dict):
        raise ValueError("copy lab receipt is not an object")
    _validate_copy_lab_outputs(lab, _index_copy_lab_cases(lab.get("cases")))


def _validate_nvme_identity(identity: dict, smart: dict) -> dict:
    import re

    rows = _nvme_stdout_json(identity, "device identity")
    command = smart["command"]
    if (identity["command"] != ["nvme", "list", "--output-format=json"]
            or not isinstance(rows, dict) or not isinstance(rows.get("Devices"), list)
            or len(command) != 4 or command[:3] != ["nvme", "smart-log", "--output-format=json"]
            or re.fullmatch(r"/dev/nvme\d+n\d+", command[3]) is None):
        raise ValueError("device or SMART command does not identify an exact NVMe namespace")
    device_path = command[3]
    devices = [row for row in rows["Devices"]
               if isinstance(row, dict) and row.get("DevicePath") == device_path]
    if not devices:
        raise _NVMeCaptureUnavailable("captured NVMe namespace is absent from current inventory")
    if len(devices) != 1:
        raise ValueError("inventory does not uniquely bind the SMART target")
    subject = devices[0]
    for name in ("SerialNumber", "Firmware", "ModelNumber"):
        if not isinstance(subject.get(name), str) or not subject[name].strip():
            raise ValueError(f"NVMe inventory lacks {name}")
    if identity["boot_id"] != smart["boot_id"]:
        raise ValueError("device identity and SMART receipts cross boot IDs")
    smart_values = _validate_smart_metrics(smart)
    from datetime import datetime
    if datetime.fromisoformat(identity["finished_at"].replace("Z", "+00:00")) > datetime.fromisoformat(
            smart["started_at"].replace("Z", "+00:00")):
        raise ValueError("identity capture did not precede SMART query")
    return {"path": device_path, "subject": subject, "serial": subject["SerialNumber"],
            "boot_id": identity["boot_id"], "smart": smart_values}


def _validate_smart_metrics(smart: dict) -> dict:
    smart_values = _nvme_stdout_json(smart, "SMART health")
    if not isinstance(smart_values, dict):
        raise ValueError("SMART output is not an object")
    for metric in ("critical_warning", "media_errors", "num_err_log_entries"):
        if metric not in smart_values:
            raise _NVMeCaptureUnavailable(f"SMART response lacks {metric}")
        if type(smart_values[metric]) is not int or smart_values[metric] < 0:
            raise ValueError(f"SMART metric is missing or invalid: {metric}")
    return smart_values


def _validate_nvme_journal(journal: dict, subject: dict) -> bool:
    import re
    from datetime import datetime

    boot_id = subject["boot_id"]
    if journal["command"] != ["journalctl", "--boot", boot_id, "--dmesg", "--output=json", "--no-pager"]:
        raise ValueError("journal command does not bind the observed boot")
    controller = re.match(r"/dev/(nvme\d+)n\d+", subject["path"])
    assert controller is not None
    has_device_error = False
    rows = journal["stdout"].splitlines()
    if not rows:
        raise _NVMeCaptureUnavailable("kernel journal has no raw records")
    for line in rows:
        row = _nvme_stdout_json({**journal, "stdout": line}, "kernel journal line")
        if not isinstance(row, dict):
            raise ValueError("kernel journal row is malformed")
        stamp = row.get("__REALTIME_TIMESTAMP")
        message = row.get("MESSAGE")
        if (row.get("_BOOT_ID") != boot_id or not isinstance(stamp, str)
                or not stamp.isdigit() or not isinstance(message, str)):
            raise ValueError("kernel journal row lacks device-time binding")
        finish = int(datetime.fromisoformat(journal["finished_at"].replace("Z", "+00:00")).timestamp()
                     * 1_000_000)
        if int(stamp) > finish:
            raise ValueError("journal event occurs after its capture finished")
        has_device_error |= controller.group(1) in message and nvme_readonly.IO_RE.search(message) is not None
    return has_device_error


def _validate_nvme_mounts(mounts: dict, subject: dict) -> tuple[str, bool]:
    from datetime import datetime
    from tools.capture_io import strict_json_loads

    before, after = mounts.get("before"), mounts.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("mount transition lacks before/after raw captures")
    states: list[tuple[str, set[str], datetime, datetime]] = []
    for capture in (before, after):
        if (capture.get("command") != ["findmnt", "--json", "--target", "/"]
                or type(capture.get("returncode")) is not int
                or capture.get("boot_id") != subject["boot_id"]
                or not isinstance(capture.get("stdout"), str)):
            raise ValueError("mount state is not a successful same-boot findmnt query")
        if capture["returncode"] != 0:
            raise _NVMeCaptureUnavailable(f"findmnt query returned {capture['returncode']}")
        try:
            started = datetime.fromisoformat(capture["started_at"].replace("Z", "+00:00"))
            finished = datetime.fromisoformat(capture["finished_at"].replace("Z", "+00:00"))
        except (KeyError, AttributeError, TypeError, ValueError) as exc:
            raise ValueError("mount receipt timestamps are malformed") from exc
        if (started.tzinfo is None or finished.tzinfo is None or finished < started):
            raise ValueError("mount receipt timestamps are unordered")
        parsed = strict_json_loads(capture["stdout"])
        filesystems = parsed.get("filesystems") if isinstance(parsed, dict) else None
        if not isinstance(filesystems, list) or len(filesystems) != 1 or not isinstance(filesystems[0], dict):
            raise ValueError("findmnt did not return exactly one root mount")
        source, options = filesystems[0].get("source"), filesystems[0].get("options")
        if not isinstance(source, str) or not isinstance(options, str):
            raise ValueError("findmnt lacks source or mount options")
        states.append((source, set(options.split(",")), started, finished))
    device = subject["path"]
    bound = states[0][0] == states[1][0] and (
        states[0][0] == device or states[0][0].startswith(device + "p"))
    if states[0][3] >= states[1][2]:
        raise ValueError("mount observations are not strictly ordered")
    ro_transition = bound and "ro" not in states[0][1] and "ro" in states[1][1]
    return states[0][0], ro_transition


def _recovery_option(command: list[str], flag: str) -> str:
    positions = [index for index, token in enumerate(command) if token == flag]
    if len(positions) != 1 or positions[0] + 1 >= len(command):
        raise ValueError(f"recovery command must contain one {flag} value")
    value = command[positions[0] + 1]
    if not Path(value).is_absolute() or ".." in Path(value).parts:
        raise ValueError(f"recovery command has unsafe {flag} path")
    return value


def _validate_backup_mount(recovery: dict, backup_source: str, subject: dict,
                           root_source: str, backup_started: object) -> None:
    from datetime import datetime
    from tools.capture_io import strict_json_loads

    source_mount = recovery.get("source_mount")
    if (not isinstance(source_mount, dict)
            or source_mount.get("command") != ["findmnt", "--json", "--target", backup_source]
            or type(source_mount.get("returncode")) is not int or source_mount.get("returncode") != 0
            or source_mount.get("boot_id") != subject["boot_id"]
            or not isinstance(source_mount.get("stderr"), str)
            or not isinstance(source_mount.get("stdout"), str)
            or not isinstance(source_mount.get("started_at"), str)
            or not isinstance(source_mount.get("finished_at"), str)):
        raise ValueError("backup source lacks a same-boot mount binding")
    try:
        source_finished = datetime.fromisoformat(source_mount["finished_at"].replace("Z", "+00:00"))
        source_started = datetime.fromisoformat(source_mount["started_at"].replace("Z", "+00:00"))
        action_started = datetime.fromisoformat(str(backup_started).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("source mount or backup timestamps are malformed") from exc
    if (source_started.tzinfo is None or source_finished.tzinfo is None
            or action_started.tzinfo is None or source_finished < source_started
            or source_finished > action_started):
        raise ValueError("backup source mount observation does not precede the backup action")
    source_doc = strict_json_loads(source_mount["stdout"])
    filesystems = source_doc.get("filesystems") if isinstance(source_doc, dict) else None
    if (not isinstance(filesystems, list) or len(filesystems) != 1
            or not isinstance(filesystems[0], dict) or filesystems[0].get("source") != root_source):
        raise ValueError("backup source filesystem differs from the identified NVMe root mount")


def _validate_oem_return(incident: Path, recovery: dict, subject: dict) -> None:
    import hashlib
    import re
    from tools.capture_io import read_regular_bytes, strict_json_loads

    oem = recovery.get("oem_return")
    if not isinstance(oem, dict):
        raise FileNotFoundError("OEM return artifact reference is absent")
    artifact, digest, case_id = oem.get("artifact"), oem.get("sha256"), oem.get("case_id")
    if (not isinstance(artifact, str) or Path(artifact).is_absolute() or ".." in Path(artifact).parts
            or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or not isinstance(case_id, str) or not case_id.strip()):
        raise ValueError("OEM return reference is malformed")
    raw = read_regular_bytes(incident / artifact, 1024 * 1024)
    if len(raw) > 1024 * 1024 or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("OEM artifact bytes do not match their digest")
    text = raw.decode("utf-8")
    values = (subject["serial"], subject["subject"]["ModelNumber"],
              subject["subject"]["Firmware"], case_id)
    if any(value not in text for value in values):
        raise ValueError("OEM artifact is not bound to the device identity and case")
    if not any(word in text.lower() for word in ("rma", "return", "repair", "replacement")):
        raise ValueError("OEM artifact does not state a return or repair route")


def _validate_backup_rollback(incident: Path, recovery: dict, subject: dict, root_source: str) -> None:
    from datetime import datetime
    import re
    from tools.capture_io import strict_json_loads

    backup_receipt = _read_nvme_capture(incident / "backup.json")
    rollback_receipt = _read_nvme_capture(incident / "rollback.json")
    for capture in (backup_receipt, rollback_receipt):
        command = capture["command"]
        if (len(command) < 3 or command[0] != sys.executable
                or command[1:3] != ["-m", "tools.nvme_readonly"]):
            raise ValueError("backup/rollback command has wrong interpreter or module")
        if capture["boot_id"] != subject["boot_id"]:
            raise ValueError("backup/rollback receipt crosses the incident boot")
    backup_finished = datetime.fromisoformat(backup_receipt["finished_at"].replace("Z", "+00:00"))
    rollback_started = datetime.fromisoformat(rollback_receipt["started_at"].replace("Z", "+00:00"))
    if backup_finished.tzinfo is None or rollback_started.tzinfo is None or rollback_started <= backup_finished:
        raise ValueError("rollback action does not follow completion of the backup")
    backup_out = _nvme_stdout_json(backup_receipt, "backup")
    rollback_out = _nvme_stdout_json(rollback_receipt, "rollback")
    if not isinstance(backup_out, dict) or not isinstance(rollback_out, dict):
        raise ValueError("backup/rollback output is not JSON object")
    backup_source = _recovery_option(backup_receipt["command"], "--export-source")
    backup_dir = _recovery_option(backup_receipt["command"], "--destination-dir")
    rollback_source = _recovery_option(rollback_receipt["command"], "--export-source")
    rollback_dir = _recovery_option(rollback_receipt["command"], "--destination-dir")
    backup_meta, rollback_meta = recovery.get("backup"), recovery.get("rollback")
    if (not isinstance(backup_meta, dict) or not isinstance(rollback_meta, dict)
            or backup_meta.get("sha256") != backup_out.get("sha256")
            or rollback_meta.get("sha256") != rollback_out.get("sha256")
            or not isinstance(backup_out.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", backup_out["sha256"]) is None):
        raise ValueError("backup/rollback output digest does not match the recorded bytes")
    if (backup_out.get("status") != "pass" or backup_out.get("source_written") is not False
            or backup_out.get("source") != backup_source
            or not isinstance(backup_out.get("destination"), str)
            or Path(backup_out["destination"]).parent != Path(backup_dir)
            or backup_out.get("source_device") == backup_out.get("destination_device")
            or rollback_out.get("status") != "pass" or rollback_out.get("source_written") is not False
            or rollback_source != backup_out.get("destination")
            or rollback_out.get("source") != rollback_source
            or not isinstance(rollback_out.get("destination"), str)
            or Path(rollback_out["destination"]).parent != Path(rollback_dir)
            or rollback_out.get("sha256") != backup_out.get("sha256")
            or rollback_out.get("destination_device") != backup_out.get("source_device")):
        raise ValueError("raw copy outputs do not prove separated backup and byte-identical return")
    _validate_backup_mount(recovery, backup_source, subject, root_source,
                           backup_receipt["started_at"])
    _validate_oem_return(incident, recovery, subject)


def _assert_nvme_incident_bundle(incident: Path) -> None:
    from tools.capture_io import read_regular_bytes, strict_json_loads

    required = ("device-identity.json", "smart-health.json", "kernel-journal.json",
                "mount-transitions.json", "recovery-and-rollback.json", "backup.json", "rollback.json")
    missing = [name for name in required if not (incident / name).is_file()]
    if missing:
        raise FileNotFoundError(", ".join(missing))
    mount_raw = read_regular_bytes(incident / "mount-transitions.json", 4 * 1024 * 1024)
    recovery_raw = read_regular_bytes(incident / "recovery-and-rollback.json", 4 * 1024 * 1024)
    if len(mount_raw) > 4 * 1024 * 1024 or len(recovery_raw) > 4 * 1024 * 1024:
        raise ValueError("mount/recovery capture exceeds size limit")
    mounts = strict_json_loads(mount_raw.decode("utf-8"))
    recovery = strict_json_loads(recovery_raw.decode("utf-8"))
    if not isinstance(mounts, dict) or not isinstance(recovery, dict):
        raise ValueError("mount/recovery capture must be an object")
    identity = _read_nvme_capture(incident / "device-identity.json")
    smart = _read_nvme_capture(incident / "smart-health.json")
    journal = _read_nvme_capture(incident / "kernel-journal.json")
    subject = _validate_nvme_identity(identity, smart)
    kernel_error = _validate_nvme_journal(journal, subject)
    root_source, mount_ro = _validate_nvme_mounts(mounts, subject)
    if root_source != subject["path"] and not root_source.startswith(subject["path"] + "p"):
        raise _NVMeCaptureUnavailable("root mount source is not mapped directly to the captured NVMe namespace")
    media_error = subject["smart"]["critical_warning"] > 0 or subject["smart"]["media_errors"] > 0
    if not (media_error or kernel_error or mount_ro):
        raise FileNotFoundError("raw captures show no SMART fault, device-matched kernel I/O error, "
                                "or root remount read-only")
    _validate_backup_rollback(incident, recovery, subject, root_source)


def test_nvme_real_incident_close_check_requires_raw_device_and_recovery_evidence() -> None:
    """Recompute device, fault, copy, rollback, and OEM routing evidence from raw captures."""
    import json

    repository = Path(__file__).resolve().parents[1]
    evidence_arg = os.environ.get("BLACKBOX_NVME_EVIDENCE_DIR")
    evidence = Path(evidence_arg) if evidence_arg else repository / "tasks/evidence/FEATURE-FORUM-NVME-READONLY-01"
    try:
        _validate_copy_lab(evidence)
        _assert_nvme_incident_bundle(evidence / "incident")
    except FileNotFoundError as exc:
        pytest.fail(f"UNKNOWN/CNR: required raw physical evidence is unavailable: {exc}")
    except _NVMeCaptureUnavailable as exc:
        pytest.fail(f"UNKNOWN/CNR: NVMe query or incident signal is unavailable: {exc}")
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError,
            RecursionError) as exc:
        pytest.fail(f"FAIL: raw NVMe evidence contradicts or malforms a required predicate: {exc}")


def _synthetic_nvme_incident_bundle(root: Path) -> None:
    """Create parser-unit input only; this fixture never feeds the real-evidence selector."""
    import datetime
    import hashlib

    incident = root / "incident"
    incident.mkdir(parents=True)
    boot_id = "00000000-0000-0000-0000-000000000001"
    device = "/dev/nvme0n1"
    serial, model, firmware = "SERIAL-UNIT", "MODEL-UNIT", "FW-UNIT"
    base = datetime.datetime(2026, 10, 4, tzinfo=datetime.timezone.utc)
    def stamp(seconds: int) -> str:
        return (base + datetime.timedelta(seconds=seconds)).isoformat()
    def receipt(command: list[str], stdout: str, start: int, end: int) -> dict:
        return {"command": command, "returncode": 0, "stdout": stdout, "stderr": "",
                "boot_id": boot_id, "started_at": stamp(start), "finished_at": stamp(end)}
    def save(path: Path, value: object) -> None:
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    identity_stdout = json.dumps({"Devices": [{"DevicePath": device, "SerialNumber": serial,
        "ModelNumber": model, "Firmware": firmware}]})
    smart_stdout = json.dumps({"critical_warning": 1, "media_errors": 0, "num_err_log_entries": 1})
    save(incident / "device-identity.json", receipt(["nvme", "list", "--output-format=json"],
                                                       identity_stdout, 1, 2))
    save(incident / "smart-health.json", receipt(["nvme", "smart-log", "--output-format=json", device],
                                                    smart_stdout, 3, 4))
    event_us = int((base + datetime.timedelta(seconds=5)).timestamp() * 1_000_000)
    journal_line = json.dumps({"_BOOT_ID": boot_id, "__REALTIME_TIMESTAMP": str(event_us),
                               "MESSAGE": "nvme0: I/O error"})
    save(incident / "kernel-journal.json", receipt(
        ["journalctl", "--boot", boot_id, "--dmesg", "--output=json", "--no-pager"],
        journal_line, 6, 7))
    mounts = {}
    for name, options, start in (("before", "rw", 8), ("after", "ro", 10)):
        mounts[name] = receipt(["findmnt", "--json", "--target", "/"],
            json.dumps({"filesystems": [{"source": device, "target": "/", "options": options}]}),
            start, start + 1)
    save(incident / "mount-transitions.json", mounts)

    sha = hashlib.sha256(b"preserved-bytes").hexdigest()
    source = "/mnt/fixture.bin"
    backup_dir, backup_copy = "/backup", "/backup/fixture.bin.1.recovery-copy"
    backup_command = [sys.executable, "-m", "tools.nvme_readonly", "--export-source", source,
                      "--destination-dir", backup_dir]
    rollback_command = [sys.executable, "-m", "tools.nvme_readonly", "--export-source", backup_copy,
                        "--destination-dir", "/restore"]
    backup_output = {"status": "pass", "source_written": False, "source": source,
        "destination": backup_copy, "source_device": 1, "destination_device": 2,
        "bytes": 16, "sha256": sha}
    rollback_output = {"status": "pass", "source_written": False, "source": backup_copy,
        "destination": "/restore/fixture.bin.1.recovery-copy", "source_device": 2,
        "destination_device": 1, "bytes": 16, "sha256": sha}
    save(incident / "backup.json", receipt(backup_command, json.dumps(backup_output), 12, 13))
    save(incident / "rollback.json", receipt(rollback_command, json.dumps(rollback_output), 14, 15))
    source_mount = receipt(["findmnt", "--json", "--target", source],
        json.dumps({"filesystems": [{"source": device, "target": "/mnt", "options": "rw"}]}),
        11, 11)
    oem_text = f"OEM CASE-UNIT {serial} {model} {firmware}: RMA return route approved"
    artifact = "oem-return.txt"
    (incident / artifact).write_text(oem_text, encoding="utf-8")
    recovery = {"backup": {"sha256": sha}, "rollback": {"sha256": sha},
                "source_mount": source_mount,
                "oem_return": {"artifact": artifact,
                    "sha256": hashlib.sha256(oem_text.encode()).hexdigest(), "case_id": "CASE-UNIT"}}
    save(incident / "recovery-and-rollback.json", recovery)


def test_nvme_incident_reader_accepts_complete_unit_fixture_only(tmp_path: Path) -> None:
    """Prove the parser accepts a complete fixture without treating it as host evidence."""
    import hashlib

    _synthetic_nvme_incident_bundle(tmp_path)
    digest = hashlib.sha256(b"copy-fixture").hexdigest()
    lab_dir = tmp_path / "export-copy-lab"
    lab_dir.mkdir()
    def case(name: str, code: int, output: dict, source: str, destination: str) -> dict:
        command = ["python3", "-m", "tools.nvme_readonly", "--export-source", source,
                   "--destination-dir", destination]
        return {"case": name, "command": command,
                "exit_code": code, "stdout": json.dumps(output), "stderr": ""}
    good = {"status": "pass", "source_written": False, "sha256": digest, "bytes": 12,
            "source_device": 1, "destination_device": 2}
    refused = {"status": "could_not_run", "source_written": False, "could_not_run": 1}
    first_copy = "/backup/file.bin.1.recovery-copy"
    restored_copy = "/restore/file.bin.1.recovery-copy.2.recovery-copy"
    copy_output = {**good, "source": "/mnt/file.bin", "destination": first_copy}
    restore_output = {**good, "source": first_copy, "destination": restored_copy,
                      "source_device": 2, "destination_device": 1}
    lab = {"scope": "controlled copy; no device recovery, NVMe health or OEM compatibility conclusion",
           "bytes": 12, "source_sha256": digest, "restored_sha256": digest,
           "source_metadata_unchanged": True, "pass": 2, "negative_controls_observed": 2,
           "unexpected_fail": 0, "unexpected_could_not_run": 0, "fail": 0, "could_not_run": 2,
           "cases": [case("export-to-separate-filesystem", 0, copy_output, "/mnt/file.bin", "/backup"),
                     case("restore-copy-to-original-filesystem", 0, restore_output, first_copy, "/restore"),
                     case("overwrite-refused", 2, refused, "/mnt/file.bin", "/backup"),
                     case("same-filesystem-refused", 2, refused, "/mnt/file.bin", "/mnt") ]}
    (lab_dir / "run.json").write_text(json.dumps(lab), encoding="utf-8")
    assert _validate_copy_lab(tmp_path) is None
    assert _assert_nvme_incident_bundle(tmp_path / "incident") is None


def test_nvme_incident_reader_rejects_empty_capture_placeholders(tmp_path: Path) -> None:
    incident = tmp_path / "incident"
    incident.mkdir()
    for name in ("device-identity.json", "smart-health.json", "kernel-journal.json",
                 "mount-transitions.json", "recovery-and-rollback.json", "backup.json", "rollback.json"):
        (incident / name).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="raw command receipt is malformed"):
        _assert_nvme_incident_bundle(incident)


def test_nvme_incident_reader_rejects_boolean_smart_counters(tmp_path: Path) -> None:
    _synthetic_nvme_incident_bundle(tmp_path)
    smart_path = tmp_path / "incident/smart-health.json"
    capture = json.loads(smart_path.read_text(encoding="utf-8"))
    output = json.loads(capture["stdout"])
    output["critical_warning"] = True
    capture["stdout"] = json.dumps(output)
    smart_path.write_text(json.dumps(capture), encoding="utf-8")
    with pytest.raises(ValueError, match="SMART metric is missing or invalid"):
        _assert_nvme_incident_bundle(tmp_path / "incident")


def test_nvme_incident_reader_rejects_rollback_digest_mismatch(tmp_path: Path) -> None:
    _synthetic_nvme_incident_bundle(tmp_path)
    rollback_path = tmp_path / "incident/rollback.json"
    receipt = json.loads(rollback_path.read_text(encoding="utf-8"))
    output = json.loads(receipt["stdout"])
    output["sha256"] = "0" * 64
    receipt["stdout"] = json.dumps(output)
    rollback_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="rollback output digest"):
        _assert_nvme_incident_bundle(tmp_path / "incident")


def test_nvme_incident_reader_rejects_oem_artifact_for_another_device(tmp_path: Path) -> None:
    import hashlib

    _synthetic_nvme_incident_bundle(tmp_path)
    incident = tmp_path / "incident"
    artifact = incident / "oem-return.txt"
    text = artifact.read_text(encoding="utf-8").replace("SERIAL-UNIT", "OTHER-SERIAL")
    artifact.write_text(text, encoding="utf-8")
    recovery_path = incident / "recovery-and-rollback.json"
    recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
    recovery["oem_return"]["sha256"] = hashlib.sha256(text.encode()).hexdigest()
    recovery_path.write_text(json.dumps(recovery), encoding="utf-8")
    with pytest.raises(ValueError, match="not bound to the device identity"):
        _assert_nvme_incident_bundle(incident)


@pytest.mark.parametrize("raw", ['{"checks":{},"checks":{}}', '{"value":NaN}'])
def test_snapshot_cli_rejects_ambiguous_json(tmp_path: Path, capsys, raw: str) -> None:
    snapshot = tmp_path / "capture.json"
    snapshot.write_text(raw, encoding="utf-8")
    assert nvme_readonly.main(["--snapshot", str(snapshot)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["could_not_run"] == 1 and report["writes_performed"] is False


def test_snapshot_cli_rejects_fifo_and_oversize(tmp_path: Path, capsys, monkeypatch) -> None:
    snapshot = tmp_path / "capture.json"
    os.mkfifo(snapshot)
    assert nvme_readonly.main(["--snapshot", str(snapshot)]) == 2
    capsys.readouterr()
    snapshot.unlink()
    monkeypatch.setattr(nvme_readonly, "MAX_SNAPSHOT_BYTES", 128)
    snapshot.write_bytes(b"x" * 129)
    assert nvme_readonly.main(["--snapshot", str(snapshot)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["could_not_run"] == 1 and "bounded" in report["error"]
