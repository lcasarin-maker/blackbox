"""Native kernel/pstore/netconsole observations; never imply delivery or recovery."""
from pathlib import Path
import runpy

from tools import kernel_capture as capture


def _write(root: Path, relative: str, value: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8")


def _base(root: Path) -> None:
    for relative in capture.KERNEL_PATHS.values():
        _write(root, relative, "6.12.0-test\n")
    archive = root / "sys/fs/pstore"
    archive.mkdir(parents=True)
    _write(root, "proc/cmdline", "quiet netconsole=6665@192.0.2.1/eth0,6666@192.0.2.2/aa:bb:cc:dd:ee:ff secret=kernel-arg")


def test_observes_static_and_dynamic_configuration_without_endpoint_values(monkeypatch, tmp_path):
    _base(tmp_path)
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "loaded", "loaded": True})
    _write(tmp_path, "sys/module/netconsole/parameters/netconsole", "6665@192.0.2.1/eth0,6666@192.0.2.2/aa:bb:cc:dd:ee:ff")
    target = "sys/kernel/config/netconsole/target0/"
    for name, value in {
        "enabled": "1", "extended": "1", "release": "6.12", "dev_name": "eth0",
        "local_port": "6665", "remote_port": "6666", "local_ip": "192.0.2.1",
        "remote_ip": "192.0.2.2", "local_mac": "00:11:22:33:44:55",
        "remote_mac": "aa:bb:cc:dd:ee:ff", "transmit_errors": "0",
    }.items():
        _write(tmp_path, target + name, value)
    result = capture.capture(tmp_path)
    assert result["status"] == "observed"
    assert result["could_not_run"] == 0
    assert result["netconsole"]["module"]["status"] == "loaded"
    assert result["netconsole"]["boot_parameter_present"] is True
    assert result["netconsole"]["static_parameter"]["configured"] is True
    assert result["netconsole"]["targets"][0]["enabled"]["value"] == "1"
    assert result["netconsole"]["receiver_receipt"] == "not observed"
    serialized = str(result)
    for secret in ("192.0.2.1", "192.0.2.2", "aa:bb:cc:dd:ee:ff", "secret=kernel-arg"):
        assert secret not in serialized


def test_absent_module_and_empty_pstore_are_observations_not_proof(monkeypatch, tmp_path):
    _base(tmp_path)
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "absent", "loaded": False})
    result = capture.capture(tmp_path)
    assert result["status"] == "observed"
    assert result["could_not_run"] == 0
    assert result["pstore"]["record_count"] == 0
    assert result["netconsole"]["static_parameter"]["status"] == "not_applicable"
    assert any("does not prove" in item for item in result["limitations"])
    assert result["netconsole"]["receiver_receipt"] == "not observed"


def test_denied_dynamic_attribute_counts_could_not_run(monkeypatch, tmp_path):
    _base(tmp_path)
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "loaded", "loaded": True})
    target = tmp_path / "sys/kernel/config/netconsole/target0"
    for name in capture.NETCONSOLE_ATTRIBUTES:
        _write(tmp_path, f"sys/kernel/config/netconsole/target0/{name}", "0")
    original = Path.read_text

    def denied(path: Path, *args, **kwargs):
        if path == target / "remote_ip":
            raise PermissionError("denied")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied)
    result = capture.capture(tmp_path)
    assert result["status"] == "partial"
    assert result["could_not_run"] >= 1
    row = result["netconsole"]["targets"][0]
    assert row["status"] == "could_not_run"
    assert row["attribute_status"]["remote_ip"] == "could_not_run"


def test_denied_module_state_is_partial(monkeypatch, tmp_path):
    _base(tmp_path)
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "could_not_run", "error": "denied"})
    result = capture.capture(tmp_path)
    assert result["status"] == "partial"
    assert result["could_not_run"] == 1
    assert result["netconsole"]["dynamic_targets_status"]["status"] == "not_applicable"


def test_missing_kernel_and_pstore_interfaces_count_as_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "absent"})
    result = capture.capture(tmp_path)
    assert result["status"] == "partial"
    assert result["could_not_run"] >= len(capture.KERNEL_PATHS)
    assert result["boot_parameter_netconsole"]["present"] is None


def test_target_with_no_readable_attributes_is_unknown(monkeypatch, tmp_path):
    _base(tmp_path)
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "loaded"})
    (tmp_path / "sys/kernel/config/netconsole/target0").mkdir(parents=True)
    result = capture.capture(tmp_path)
    assert result["netconsole"]["targets"][0]["status"] == "unknown"
    assert result["netconsole"]["targets"][0]["readable_attribute_count"] == 0


def test_external_symlinked_target_is_rejected(monkeypatch, tmp_path):
    _base(tmp_path)
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "loaded"})
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "sys/kernel/config/netconsole").mkdir(parents=True)
    (tmp_path / "sys/kernel/config/netconsole/target0").symlink_to(outside, target_is_directory=True)
    result = capture.capture(tmp_path)
    assert result["status"] == "partial"
    assert result["netconsole"]["targets"][0]["status"] == "could_not_run"


def test_external_symlinked_pstore_is_rejected(monkeypatch, tmp_path):
    _base(tmp_path)
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "absent"})
    outside = tmp_path.parent / f"{tmp_path.name}-archive"
    outside.mkdir()
    (tmp_path / "sys/fs/pstore").rmdir()
    (tmp_path / "sys/fs/pstore").symlink_to(outside, target_is_directory=True)
    result = capture.capture(tmp_path)
    assert result["status"] == "partial"
    assert result["pstore"]["status"] == "could_not_run"


def test_external_symlinked_pstore_record_is_rejected(monkeypatch, tmp_path):
    _base(tmp_path)
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "absent"})
    outside = tmp_path.parent / f"{tmp_path.name}-record"
    outside.write_text("private RCU detail", encoding="utf-8")
    (tmp_path / "sys/fs/pstore/record").symlink_to(outside)
    result = capture.capture(tmp_path)
    assert result["status"] == "partial"
    assert result["pstore"]["records"][0]["status"] == "could_not_run"
    assert "private RCU detail" not in str(result)


def test_pstore_content_is_hashed_and_private_text_not_serialized(monkeypatch, tmp_path):
    _base(tmp_path)
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "absent"})
    _write(tmp_path, "sys/fs/pstore/dmesg-efi-0", "RCU private log body")
    result = capture.capture(tmp_path)
    row = result["pstore"]["records"][0]
    assert row["signals"] == ["RCU"]
    assert len(row["normalized_text_sha256"]) == 64
    assert "RCU private log body" not in str(result)


def test_denied_pstore_file_read_counts_could_not_run(monkeypatch, tmp_path):
    _base(tmp_path)
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "absent"})
    file = tmp_path / "sys/fs/pstore/record"
    file.write_text("record", encoding="utf-8")
    original = Path.read_text

    def denied(path: Path, *args, **kwargs):
        if path == file:
            raise PermissionError("denied")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied)
    result = capture.capture(tmp_path)
    assert result["status"] == "partial"
    assert result["could_not_run"] == 1
    assert result["pstore"]["records"][0]["status"] == "could_not_run"


def test_denied_config_listing_counts_could_not_run(monkeypatch, tmp_path):
    _base(tmp_path)
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "loaded"})
    config = tmp_path / "sys/kernel/config/netconsole"
    config.mkdir(parents=True)
    original = Path.iterdir

    def denied(path: Path):
        if path == config:
            raise PermissionError("denied")
        return original(path)

    monkeypatch.setattr(Path, "iterdir", denied)
    result = capture.capture(tmp_path)
    assert result["status"] == "partial"
    assert result["netconsole"]["dynamic_targets_status"]["status"] == "could_not_run"


def test_non_directory_config_entry_is_skipped(monkeypatch, tmp_path):
    _base(tmp_path)
    monkeypatch.setattr(capture, "module_state", lambda *_: {"status": "loaded"})
    _write(tmp_path, "sys/kernel/config/netconsole/not-a-target", "data")
    result = capture.capture(tmp_path)
    assert result["netconsole"]["targets"] == []


def test_main_returns_partial_exit_and_prints_zero_or_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(capture, "capture", lambda: {"could_not_run": 0})
    assert capture.main() == 0
    assert '"could_not_run": 0' in capsys.readouterr().out
    monkeypatch.setattr(capture, "capture", lambda: {"could_not_run": 1})
    assert capture.main() == 2
    assert '"could_not_run": 1' in capsys.readouterr().out


def test_module_entrypoint_exits_with_capture_status():
    try:
        runpy.run_path(str(Path(capture.__file__)), run_name="__main__")
    except SystemExit as exc:
        assert exc.code in (0, 2)
    else:
        raise AssertionError("module entry point must exit")
