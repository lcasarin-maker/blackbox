from __future__ import annotations

import json
from pathlib import Path
import runpy
import subprocess
import sys
from typing import Any

import pytest

from tools import host_diagnostics as hd

# Classified helper, distinct from Path.read_text.
read_host_value = hd.read_text


class FakeRunner:
    def __init__(self, result: subprocess.CompletedProcess[str] | Exception | None = None):
        self.result = result or subprocess.CompletedProcess([], 0, "ok\n", "")
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append((argv, kwargs))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_read_text_success_and_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "state"
    source.write_text(" active \n", encoding="utf-8")
    assert read_host_value(source) == {"status": "ok", "value": "active"}
    assert read_host_value(tmp_path / "missing")["status"] == "could_not_run"

    def denied(*args: Any, **kwargs: Any) -> str:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "read_text", denied)
    assert read_host_value(source)["error"].startswith("PermissionError:")

    def failed(*args: Any, **kwargs: Any) -> str:
        raise OSError("io fault")

    monkeypatch.setattr(Path, "read_text", failed)
    assert read_host_value(source)["error"] == "OSError: io fault"


def test_read_names_success_and_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "names"
    source.mkdir()
    (source / "b").touch()
    (source / "a").touch()
    assert hd.read_names(source) == {"status": "ok", "value": ["a", "b"]}
    assert hd.read_names(tmp_path / "missing")["status"] == "could_not_run"

    def denied(self: Path) -> Any:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "iterdir", denied)
    assert hd.read_names(source)["error"].startswith("PermissionError:")

    def failed(self: Path) -> Any:
        raise OSError("io fault")

    monkeypatch.setattr(Path, "iterdir", failed)
    assert hd.read_names(source)["error"] == "OSError: io fault"


@pytest.mark.parametrize("error", [FileNotFoundError("missing"), PermissionError("denied"),
                                    subprocess.TimeoutExpired(["x"], 4), OSError("io")])
def test_command_failure_is_preserved(error: Exception) -> None:
    result = hd.run_readonly(["safe-query"], FakeRunner(error))
    assert result["status"] == "could_not_run"
    assert result["command"] == ["safe-query"]


def test_command_rc_output_caps_and_safe_invocation() -> None:
    runner = FakeRunner(subprocess.CompletedProcess([], 0, "x" * 20_000, "y" * 20_000))
    result = hd.run_readonly(["nmcli", "device", "status"], runner)
    assert result["status"] == "ok"
    assert len(result["stdout"]) == hd.MAX_OUTPUT_CHARS
    assert result["stdout_truncated"] is True
    assert result["stderr_truncated"] is True
    assert runner.calls[0][1].get("shell", False) is False
    assert runner.calls[0][1]["stdin"] == subprocess.DEVNULL
    assert runner.calls[0][1]["timeout"] == hd.TIMEOUT_S

    failed = hd.run_readonly(["systemctl", "is-active", "gdm.service"],
                             FakeRunner(subprocess.CompletedProcess([], 3, "inactive\n", "")), (3, 4))
    assert failed["status"] == "observed"
    assert failed["returncode"] == 3


def test_gpu_runtime_capture_uses_bounded_readonly_queries_and_preserves_failures() -> None:
    good = FakeRunner(subprocess.CompletedProcess([], 0, "observed-version-or-gpu-state\n", ""))
    runtime = hd.gpu_runtime_capture(good)
    assert set(runtime) == {"nvidia_smi_banner", "nvidia_gpu_state", "container_runtime_version",
                            "running_container_image_tags"}
    assert all(item["status"] == "ok" for item in runtime.values())
    assert [call[0] for call in good.calls] == [
        ["nvidia-smi"],
        ["nvidia-smi", "--query-gpu=name,driver_version,pci.bus_id,utilization.gpu,power.draw",
         "--format=csv,noheader"],
        ["docker", "version", "--format", "{{.Server.Version}}"],
        ["docker", "ps", "--no-trunc", "--format", "{{.ID}} {{.Image}}"],
    ]
    assert all(call[1]["timeout"] == hd.TIMEOUT_S and call[1]["stdin"] == subprocess.DEVNULL
               and call[1].get("shell", False) is False for call in good.calls)

    unavailable = FakeRunner(PermissionError("query unavailable"))
    failed = hd.gpu_runtime_capture(unavailable)
    assert all(item["status"] == "could_not_run" for item in failed.values())
    assert hd.could_not_run_count(failed) == 4


def test_mount_summary_ro_rw_and_malformed(tmp_path: Path) -> None:
    mountinfo = tmp_path / "proc/self/mountinfo"
    mountinfo.parent.mkdir(parents=True)
    mountinfo.write_text(
        "29 20 0:25 / / rw,relatime - ext4 /dev/root rw\n"
        "30 20 0:26 / /boot ro,relatime - vfat /dev/boot ro\n"
        "31 20 0:27 / /mnt/archive\\040disk rw,relatime - ext4 /dev/sdb rw\n"
        "broken\n", encoding="utf-8")
    result = hd.mount_summary(tmp_path)
    assert result == {"status": "ok", "value": [
        {"target": "/", "options": "rw,relatime", "read_only": False},
        {"target": "/boot", "options": "ro,relatime", "read_only": True},
    ]}
    assert hd.mount_summary(tmp_path / "absent")["status"] == "could_not_run"
    no_mounts = tmp_path / "empty/proc/self"
    no_mounts.mkdir(parents=True)
    (no_mounts / "mountinfo").write_text("broken\n", encoding="utf-8")
    assert hd.mount_summary(tmp_path / "empty")["status"] == "could_not_run"


def test_interfaces_filter_invalid_names(tmp_path: Path) -> None:
    net = tmp_path / "sys/class/net"
    net.mkdir(parents=True)
    for name in ("lo", "eth0", "enP7s7", "bad name", "x" * 16):
        (net / name).mkdir()
    inventory = hd._interfaces(tmp_path)
    assert inventory == {"status": "ok", "interfaces": ["enP7s7", "eth0"],
                         "ethernet": [], "excluded": {
                             "enP7s7": "no sysfs device link (virtual or non-device interface)",
                             "eth0": "no sysfs device link (virtual or non-device interface)"},
                         "errors": {}}
    assert hd._interfaces(tmp_path / "missing")["status"] == "could_not_run"


def test_module_state_distinguishes_loaded_builtin_absent_and_missing(tmp_path: Path) -> None:
    release = tmp_path / "proc/sys/kernel"
    release.mkdir(parents=True)
    (release / "osrelease").write_text("6.1-test\n", encoding="utf-8")
    modules = tmp_path / "lib/modules/6.1-test"
    modules.mkdir(parents=True)
    (modules / "modules.builtin").write_text("kernel/drivers/hid/hid-generic.ko\n",
                                             encoding="utf-8")
    loaded = tmp_path / "sys/module/usbhid"
    loaded.mkdir(parents=True)
    assert hd.module_state(tmp_path, "usbhid") == {
        "status": "loaded", "loaded": True, "built_in": False}
    assert hd.module_state(tmp_path, "hid-generic")["status"] == "built_in"
    assert hd.module_state(tmp_path, "hid_generic")["status"] == "absent"
    assert hd.module_state(tmp_path, "../bad")["status"] == "could_not_run"
    assert hd.module_state(tmp_path / "missing", "usbhid")["status"] == "could_not_run"

    no_release = tmp_path / "no-release"
    (no_release / "sys/module/usbhid").mkdir(parents=True)
    unknown_release = hd.module_state(no_release, "usbhid")
    assert unknown_release["status"] == "loaded"
    assert unknown_release["built_in_status"] == "could_not_run"

    (modules / "modules.builtin").unlink()
    unknown = hd.module_state(tmp_path, "usbhid")
    assert unknown["status"] == "loaded"
    assert unknown["built_in"] is None
    assert unknown["built_in_status"] == "could_not_run"
    assert hd.module_state(tmp_path, "usb_serial")["status"] == "could_not_run"


def test_module_path_permission_failure_is_not_absence(monkeypatch: pytest.MonkeyPatch,
                                                       tmp_path: Path) -> None:
    def denied(self: Path) -> Any:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "stat", denied)
    state, error = hd._module_loaded(tmp_path / "sys/module/usbhid")
    assert state is None
    assert error == "PermissionError: denied"


def test_pci_binding_reports_bound_unbound_non_pci_and_unreadable(tmp_path: Path,
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    sysfs = tmp_path / "sys"
    interface_dir = sysfs / "class/net/enp1s0"
    interface_dir.mkdir(parents=True)
    pci_device = sysfs / "devices/pci0000:00/0000:00:01.0"
    pci_device.mkdir(parents=True)
    (pci_device / "vendor").write_text("0x10ec\n", encoding="ascii")
    (pci_device / "device").write_text("0x8127\n", encoding="ascii")
    drivers = sysfs / "bus/pci/drivers/r8127"
    drivers.mkdir(parents=True)
    (pci_device / "driver").symlink_to("/sys/bus/pci/drivers/r8127")
    (drivers / "module").symlink_to("/sys/module/r8127")
    module = sysfs / "module/r8127"
    module.mkdir(parents=True)
    (module / "version").write_text("11.014.00-NAPI\n", encoding="ascii")
    (interface_dir / "device").symlink_to("../../../devices/pci0000:00/0000:00:01.0")
    bound = hd.pci_binding(tmp_path, "enp1s0")
    assert bound == {"status": "bound", "pci_vendor": "0x10ec", "pci_device": "0x8127",
                     "pci_address": "0000:00:01.0",
                     "driver": "r8127", "module": "r8127",
                     "module_version": {"status": "ok", "value": "11.014.00-NAPI"},
                     "module_version_status": "ok"}

    (pci_device / "driver").unlink()
    assert hd.pci_binding(tmp_path, "enp1s0")["status"] == "unbound"
    (pci_device / "driver").symlink_to("/sys/bus/pci/drivers/r8169")
    assert hd.pci_binding(tmp_path, "enp1s0")["driver"] == "r8169"

    virtual = tmp_path / "sys/class/net/docker0"
    virtual.mkdir(parents=True)
    assert hd.pci_binding(tmp_path, "docker0")["status"] == "not_pci"
    assert hd.pci_binding(tmp_path, "../bad")["status"] == "could_not_run"

    def denied(*args: Any, **kwargs: Any) -> str:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "read_text", denied)
    assert hd.pci_binding(tmp_path, "enp1s0")["status"] == "could_not_run"


def test_pci_binding_preserves_readlink_errors(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    interface_dir = tmp_path / "sys/class/net/eth0"
    interface_dir.mkdir(parents=True)

    def failed_link(_path: Path) -> Path:
        raise OSError("link unavailable")

    monkeypatch.setattr(Path, "readlink", failed_link)
    assert hd.pci_binding(tmp_path, "eth0") == {
        "status": "could_not_run", "error": "OSError: link unavailable"}


def test_pci_binding_preserves_driver_and_module_link_errors(tmp_path: Path,
                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    interface_dir = tmp_path / "sys/class/net/eth0"
    pci_device = tmp_path / "sys/devices/0000:00:01.0"
    pci_device.mkdir(parents=True)
    (interface_dir).mkdir(parents=True)
    (interface_dir / "device").symlink_to("../../../devices/0000:00:01.0")
    (pci_device / "vendor").write_text("0x10ec", encoding="ascii")
    (pci_device / "device").write_text("0x8127", encoding="ascii")
    original = Path.readlink

    def failed_driver_link(path: Path) -> Path:
        if path.name == "driver":
            raise OSError("driver link unavailable")
        return original(path)

    monkeypatch.setattr(Path, "readlink", failed_driver_link)
    assert hd.pci_binding(tmp_path, "eth0")["error"] == "OSError: driver link unavailable"
    monkeypatch.setattr(Path, "readlink", original)
    (pci_device / "driver").symlink_to("/sys/bus/pci/drivers/example")

    def failed_module_link(path: Path) -> Path:
        if path.name == "module":
            raise OSError("module link unavailable")
        return original(path)

    monkeypatch.setattr(Path, "readlink", failed_module_link)
    assert hd.pci_binding(tmp_path, "eth0")["error"] == "OSError: module link unavailable"


def test_module_state_preserves_sysfs_stat_error(tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    def failed_stat(_path: Path) -> Any:
        raise OSError("sysfs stat unavailable")

    monkeypatch.setattr(Path, "stat", failed_stat)
    assert hd.module_state(tmp_path, "usbhid") == {
        "status": "could_not_run", "error": "OSError: sysfs stat unavailable"}


def test_capture_uses_fixed_read_only_queries_and_reports_signals(tmp_path: Path) -> None:
    net = tmp_path / "sys/class/net"
    net.mkdir(parents=True)
    interface = net / "eth0"
    interface.mkdir()
    device = tmp_path / "sys/devices/0000:00:01.0"
    device.mkdir(parents=True)
    (interface / "device").symlink_to("../../../devices/0000:00:01.0")
    (device / "vendor").write_text("0x1234", encoding="ascii")
    (device / "device").write_text("0xabcd", encoding="ascii")
    runner = FakeRunner()
    result = hd.capture(tmp_path, runner)
    assert result["schema"] == 1
    assert result["status"] == "partial"
    assert result["safety"] == {"mode": "read_only", "shell": False,
                                "services_changed": False, "network_changed": False,
                                "modules_changed": False, "block_device_written": False}
    assert result["checks"]["network"]["eee"]["eth0"]["status"] == "ok"
    assert result["checks"]["gpu_runtime"]["nvidia_smi_banner"]["status"] == "ok"
    assert result["checks"]["gpu_runtime"]["running_container_image_tags"]["status"] == "ok"
    commands = [call[0] for call in runner.calls]
    assert ["ethtool", "--show-eee", "eth0"] in commands
    assert ["nvme", "list", "--output-format=json"] in commands
    assert all("--set-eee" not in argv and "rescue.target" not in argv for argv in commands)
    assert result["checks"]["usb"]["usbhid_module"]["status"] == "could_not_run"


def test_interface_inventory_limits_eee_to_physical_wired_devices(tmp_path: Path) -> None:
    net = tmp_path / "sys/class/net"
    net.mkdir(parents=True)
    for name in ("enp1s0", "wlan0", "docker0", "usb0"):
        (net / name).mkdir()
    devices = tmp_path / "sys/devices"
    devices.mkdir()
    for name in ("enp1s0", "wlan0", "usb0"):
        (devices / name).mkdir()
        (net / name / "device").symlink_to(f"../../../devices/{name}")
    (net / "wlan0" / "wireless").mkdir()
    inventory = hd._interfaces(tmp_path)
    assert inventory["ethernet"] == ["enp1s0", "usb0"]
    assert inventory["excluded"] == {
        "docker0": "no sysfs device link (virtual or non-device interface)",
        "wlan0": "wireless interface"}


def test_interface_inventory_retains_sysfs_link_failure(tmp_path: Path,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    net = tmp_path / "sys/class/net"
    (net / "eth0").mkdir(parents=True)
    original = hd._link_name

    def failed_device_link(path: Path) -> tuple[str | None, str | None]:
        if path.name == "device":
            return None, "PermissionError: denied"
        return original(path)

    monkeypatch.setattr(hd, "_link_name", failed_device_link)
    assert hd._interfaces(tmp_path) == {
        "status": "could_not_run", "interfaces": ["eth0"], "ethernet": [],
        "excluded": {}, "errors": {"eth0": "PermissionError: denied"}}


def test_main_emits_partial_json_with_nonzero_exit(capsys: pytest.CaptureFixture[str],
                                                  tmp_path: Path) -> None:
    assert hd.main(["--root", str(tmp_path)]) == 2
    record = json.loads(capsys.readouterr().out)
    assert record["safety"]["mode"] == "read_only"
    assert record["report_status"] == "partial"
    assert record["could_not_run"] > 0


def test_module_entrypoint_exits_zero(monkeypatch: pytest.MonkeyPatch,
                                     capsys: pytest.CaptureFixture[str],
                                     tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "argv", [str(Path(hd.__file__)), "--root", str(tmp_path)])
    monkeypatch.setattr(subprocess, "run", FakeRunner())
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(Path(hd.__file__)), run_name="__main__")
    assert result.value.code == 2
    record = json.loads(capsys.readouterr().out)
    assert record["schema"] == 1
    assert record["could_not_run"] > 0


def test_could_not_run_count_detects_nested_negative_control() -> None:
    assert hd.could_not_run_count({"check": {"status": "ok"}}) == 0
    assert hd.could_not_run_count({"check": {"status": "could_not_run"},
                                   "list": [{"status": "could_not_run"}]}) == 2


def test_contact_emails_redacted_without_altering_systemd_units(monkeypatch):
    contact = "<support@contact.invalid>"
    unit = "modprobe@nvidia.service"
    def verify():
        runner = FakeRunner(subprocess.CompletedProcess([], 3,
            f"Realtek team {contact}\n{unit} active", f"contact {contact}"))
        result = hd.run_readonly(["journalctl", "--boot"], runner)
        assert result["stdout"] == f"Realtek team <redacted-contact>\n{unit} active"
        assert result["stderr"] == "contact <redacted-contact>"
        assert result["contact_emails_redacted"] == 2
        assert result["returncode"] == 3 and result["status"] == "could_not_run"
        assert result["stdout_truncated"] is False
    verify()
    monkeypatch.setattr(hd, "CONTACT_EMAIL_RE", hd.re.compile(r"(?!)"))
    with pytest.raises(AssertionError):
        verify()
    root = Path(__file__).resolve().parent.parent
    checked = subprocess.run(
        [sys.executable, str(root / ".simplecode/run.py"),
         "simplecode.verification.pii_scan", "--root", str(root)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "hallazgos=0 could_not_run=0" in checked.stdout


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_contact_redaction_precedes_output_truncation(stream, monkeypatch):
    raw = "abcd<support@contact.invalid>"
    monkeypatch.setattr(hd, "MAX_OUTPUT_CHARS", len(raw) - 1)
    values = {"stdout": "", "stderr": "", stream: raw}
    result = hd.run_readonly(["journalctl"], FakeRunner(
        subprocess.CompletedProcess([], 0, **values)))
    assert result[stream] == "abcd<redacted-contact>"
    assert result[f"{stream}_truncated"] is False
    assert result["contact_emails_redacted"] == 1
