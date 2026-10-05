from __future__ import annotations

import json
import ctypes as C
import os
from pathlib import Path
import runpy
import subprocess
import sys
import types
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


def test_gpu_runtime_capture_uses_bounded_readonly_queries_and_preserves_failures(
        monkeypatch: pytest.MonkeyPatch) -> None:
    container_id = "a" * 64
    image_id = "sha256:" + "b" * 64

    class RuntimeRunner(FakeRunner):
        def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            self.calls.append((argv, kwargs))
            if argv[:2] == ["docker", "ps"]:
                return subprocess.CompletedProcess(argv, 0, f"{container_id} vllm:test\n", "")
            if argv[:2] == ["docker", "inspect"]:
                return subprocess.CompletedProcess(argv, 0, image_id + "\n", "")
            return subprocess.CompletedProcess(argv, 0, "observed-version-or-gpu-state\n", "")

    good = RuntimeRunner()
    monkeypatch.setattr(hd, "cuda_runtime_version_capture", lambda: {
        "status": "ok", "library": "libcudart.so.13", "runtime_version": 13000,
        "major": 13, "minor": 0})
    runtime = hd.gpu_runtime_capture(good)
    assert set(runtime) == {"nvidia_smi_banner", "nvidia_gpu_state", "container_runtime_version",
                            "running_container_image_tags", "running_container_image_ids",
                            "cuda_runtime"}
    assert runtime["running_container_image_ids"]["status"] == "ok"
    assert runtime["running_container_image_ids"]["containers"] == [{
        "status": "ok", "container_id": container_id, "image_ref": "vllm:test",
        "image_id": image_id}]
    assert [call[0] for call in good.calls] == [
        ["docker", "ps", "--no-trunc", "--format", "{{.ID}} {{.Image}}"],
        ["docker", "inspect", "--format", "{{.Image}}", container_id],
        ["nvidia-smi"],
        ["nvidia-smi", "--query-gpu=name,driver_version,pci.bus_id,utilization.gpu,power.draw",
         "--format=csv,noheader"],
        ["docker", "version", "--format", "{{.Server.Version}}"],
    ]
    assert all(call[1]["timeout"] == hd.TIMEOUT_S and call[1]["stdin"] == subprocess.DEVNULL
               and call[1].get("shell", False) is False for call in good.calls)

    monkeypatch.setattr(hd, "cuda_runtime_version_capture", lambda: {
        "status": "could_not_run", "error": "libcudart unavailable"})
    unavailable = FakeRunner(PermissionError("query unavailable"))
    failed = hd.gpu_runtime_capture(unavailable)
    assert failed["running_container_image_ids"]["status"] == "partial"
    assert all(failed[key]["status"] == "could_not_run" for key in (
        "nvidia_smi_banner", "nvidia_gpu_state", "cuda_runtime",
        "container_runtime_version", "running_container_image_tags"))
    assert hd.could_not_run_count(failed) == 5


def test_container_image_id_capture_bounds_inspects_and_marks_incomplete() -> None:
    ids = [f"{number:x}" * 64 for number in range(1, 6)]

    class InspectRunner:
        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            self.calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "sha256:" + "b" * 64 + "\n", "")

    runner = InspectRunner()
    result = hd.running_container_image_ids(
        {"status": "ok", "stdout": "".join(f"{item} vllm:test{i}\n" for i, item in enumerate(ids))},
        runner)
    assert result["status"] == "partial"
    assert len(runner.calls) == hd.MAX_CONTAINER_IMAGE_INSPECTIONS
    assert result["containers"][-1] == {
        "status": "could_not_run", "reason": "inspection limit exceeded",
        "container_count": 5, "uninspected_container_count": 1}
    assert hd.could_not_run_count(result) == 1


@pytest.mark.parametrize("inspection", [
    subprocess.CompletedProcess([], 0, "not-an-image-id\n", ""),
    PermissionError("docker inspect denied"),
])
def test_container_image_id_invalid_or_denied_inspection_is_unknown(inspection: Any) -> None:
    container_id = "a" * 64

    class InspectRunner:
        def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            assert argv == ["docker", "inspect", "--format", "{{.Image}}", container_id]
            if isinstance(inspection, Exception):
                raise inspection
            return inspection

    result = hd.running_container_image_ids(
        {"status": "ok", "stdout": f"{container_id} vllm:test\n"}, InspectRunner())
    assert result["status"] == "partial"
    assert result["containers"] == [{
        "status": "could_not_run", "container_id": container_id,
        "image_ref": "vllm:test",
        "inspect_status": "could_not_run" if isinstance(inspection, Exception) else "ok",
    }]
    assert hd.could_not_run_count(result) == 1


def test_cuda_runtime_version_capture_reads_exact_api_version_and_preserves_unknown(
        monkeypatch: pytest.MonkeyPatch) -> None:
    class VersionFunction:
        argtypes: Any = None
        restype: Any = None

        def __call__(self, pointer: Any) -> int:
            C.cast(pointer, C.POINTER(C.c_int))[0] = 13000
            return 0

    library = types.SimpleNamespace(cudaRuntimeGetVersion=VersionFunction())
    monkeypatch.setattr("tools.host_diagnostics.ctypes.util.find_library", lambda _name: "libcudart.so.13")
    monkeypatch.setattr(hd.C, "CDLL", lambda _name: library)
    assert hd.cuda_runtime_version_capture() == {
        "status": "ok", "library": "libcudart.so.13", "runtime_version": 13000,
        "major": 13, "minor": 0}

    monkeypatch.setattr("tools.host_diagnostics.ctypes.util.find_library", lambda _name: None)
    assert hd.cuda_runtime_version_capture() == {
        "status": "could_not_run", "error": "libcudart unavailable"}


@pytest.mark.parametrize("library,error", [
    (OSError("bad shared object"), "OSError: bad shared object"),
    (types.SimpleNamespace(), "AttributeError: 'types.SimpleNamespace' object has no attribute 'cudaRuntimeGetVersion'"),
])
def test_cuda_runtime_library_or_symbol_failure_is_unknown(
        monkeypatch: pytest.MonkeyPatch, library: Any, error: str) -> None:
    monkeypatch.setattr("tools.host_diagnostics.ctypes.util.find_library", lambda _name: "libcudart.so.13")

    def load(_name: str) -> Any:
        if isinstance(library, Exception):
            raise library
        return library

    monkeypatch.setattr(hd.C, "CDLL", load)
    assert hd.cuda_runtime_version_capture() == {
        "status": "could_not_run", "library": "libcudart.so.13", "error": error}


@pytest.mark.parametrize(("returncode", "version"), [(35, 13000), (0, 0)])
def test_cuda_runtime_api_failure_or_zero_version_is_unknown(
        monkeypatch: pytest.MonkeyPatch, returncode: int, version: int) -> None:
    class VersionFunction:
        def __call__(self, pointer: Any) -> int:
            C.cast(pointer, C.POINTER(C.c_int))[0] = version
            return returncode

    function = VersionFunction()
    monkeypatch.setattr("tools.host_diagnostics.ctypes.util.find_library", lambda _name: "libcudart.so.13")
    monkeypatch.setattr(hd.C, "CDLL", lambda _name: types.SimpleNamespace(cudaRuntimeGetVersion=function))
    result = hd.cuda_runtime_version_capture()
    assert result == {"status": "could_not_run", "library": "libcudart.so.13",
                      "returncode": returncode, "runtime_version": version}


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


def test_sysfs_hardware_capture_reads_physical_bindings_without_commands(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proc = tmp_path / "proc/sys/kernel/random"
    proc.mkdir(parents=True)
    (proc / "boot_id").write_text("boot-test\n", encoding="utf-8")
    (tmp_path / "proc/sys/kernel/osrelease").write_text("6.1-test\n", encoding="utf-8")

    pci = tmp_path / "sys/devices/pci0000:00/0000:01:00.0"
    pci.mkdir(parents=True)
    (pci / "vendor").write_text("0x10de\n", encoding="ascii")
    (pci / "device").write_text("0x2342\n", encoding="ascii")
    (pci / "class").write_text("0x030000\n", encoding="ascii")
    driver = tmp_path / "sys/bus/pci/drivers/nvidia"
    driver.mkdir(parents=True)
    module = tmp_path / "sys/module/nvidia"
    module.mkdir(parents=True)
    (module / "version").write_text("580-test\n", encoding="ascii")
    (pci / "driver").symlink_to(driver, target_is_directory=True)
    pci_links = tmp_path / "sys/bus/pci/devices"
    pci_links.mkdir(parents=True)
    (pci_links / pci.name).symlink_to(pci, target_is_directory=True)

    net = pci / "net/eth0"
    net.mkdir(parents=True)
    (net / "mtu").write_text("9000\n", encoding="ascii")
    (net / "carrier").write_text("1\n", encoding="ascii")
    (net / "operstate").write_text("up\n", encoding="ascii")
    (net / "device").symlink_to(pci, target_is_directory=True)
    net_class = tmp_path / "sys/class/net"
    net_class.mkdir(parents=True)
    (net_class / "eth0").symlink_to(net, target_is_directory=True)
    (tmp_path / "sys/class/infiniband").mkdir(parents=True)

    def forbidden_command(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("sysfs-only collector invoked a command")

    monkeypatch.setattr(hd, "run_readonly", forbidden_command)
    report = hd.sysfs_hardware_capture(tmp_path)
    assert report["status"] == "observed"
    assert report["could_not_run"] == 0
    assert report["safety"]["commands_executed"] is False
    observed_net = report["observations"]["network"]["eth0"]
    assert observed_net["mtu"] == {"status": "ok", "value": "9000"}
    assert observed_net["pci_binding"]["pci_address"] == pci.name
    observed_pci = report["observations"]["pci_devices"]["devices"][pci.name]
    assert observed_pci["vendor"] == {"status": "ok", "value": "0x10de"}
    assert observed_pci["class"]["value"] == "0x030000"


def test_sysfs_hardware_capture_marks_unreadable_paths_and_pci_truncation(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "proc/sys/kernel/random").mkdir(parents=True)
    (tmp_path / "proc/sys/kernel/osrelease").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "proc/sys/kernel/osrelease").write_text("6.1-test\n", encoding="utf-8")
    (tmp_path / "proc/sys/kernel/random/boot_id").write_text("boot-test\n", encoding="utf-8")
    (tmp_path / "sys/class/net").mkdir(parents=True)
    (tmp_path / "sys/class/infiniband").mkdir(parents=True)
    pci = tmp_path / "sys/bus/pci/devices"
    pci.mkdir(parents=True)
    (pci / "0000:01:00.0").mkdir()
    (pci / "0000:02:00.0").mkdir()
    monkeypatch.setattr(hd, "MAX_PCI_DEVICE_INSPECTIONS", 1)

    report = hd.sysfs_hardware_capture(tmp_path)
    assert report["status"] == "partial"
    assert report["could_not_run"] > 0
    inventory = report["observations"]["pci_devices"]
    assert inventory["truncated"] is True
    assert inventory["inspected_count"] == 1


def test_pci_directory_scan_is_bounded_and_total_count_stays_unknown(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    devices = tmp_path / "sys/bus/pci/devices"
    devices.mkdir(parents=True)
    for index in range(4):
        (devices / f"0000:00:0{index}.0").mkdir()
    monkeypatch.setattr(hd, "MAX_PCI_DEVICE_INSPECTIONS", 2)
    original_scandir = os.scandir
    consumed = 0

    class CountedEntries:
        def __init__(self, entries: Any):
            self.entries = entries

        def __enter__(self) -> CountedEntries:
            return self

        def __exit__(self, *_args: Any) -> None:
            self.entries.close()

        def __iter__(self) -> Any:
            nonlocal consumed
            for entry in self.entries:
                consumed += 1
                yield entry

    def counted_scandir(path: Path) -> Any:
        return CountedEntries(original_scandir(path))

    monkeypatch.setattr(hd.os, "scandir", counted_scandir)
    inventory = hd._pci_device_inventory(tmp_path)
    assert consumed == 3
    assert inventory["status"] == "could_not_run"
    assert inventory["truncated"] is True
    assert inventory["device_count"] is None
    assert inventory["observed_entry_count"] == 2
    assert inventory["inspected_count"] == 2


def test_pci_directory_scan_errors_are_could_not_run(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "sys/bus/pci/devices").mkdir(parents=True)

    def denied(_path: Path) -> Any:
        raise PermissionError("PCI directory denied")

    monkeypatch.setattr(hd.os, "scandir", denied)
    inventory = hd._pci_device_inventory(tmp_path)
    assert inventory["status"] == "could_not_run"
    assert inventory["devices"] == {}
    assert "PermissionError" in inventory["error"]


def test_sysfs_text_rejects_oversize_and_interface_inventory_truncates(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kernel = tmp_path / "proc/sys/kernel/osrelease"
    kernel.parent.mkdir(parents=True)
    kernel.write_bytes(b"x" * (hd.MAX_SYSFS_TEXT_BYTES + 1))
    assert hd._sysfs_text(tmp_path, kernel)["truncated"] is True

    net = tmp_path / "sys/class/net"
    net.mkdir(parents=True)
    for index in range(3):
        (net / f"eth{index}").mkdir()
    monkeypatch.setattr(hd, "MAX_NETWORK_INTERFACE_INSPECTIONS", 2)
    interfaces = hd._interfaces(tmp_path)
    assert interfaces["status"] == "could_not_run"
    assert interfaces["truncated"] is True
    assert interfaces["inspected_count"] == 2


def test_sysfs_fifo_read_returns_could_not_run_without_blocking(tmp_path: Path) -> None:
    fifo = tmp_path / "proc/sys/kernel/osrelease"
    fifo.parent.mkdir(parents=True)
    os.mkfifo(fifo)
    result = subprocess.run(
        [sys.executable, "-c",
         "from pathlib import Path; from tools import host_diagnostics as h; "
         f"print(h._sysfs_text(Path({str(tmp_path)!r}), "
         "Path('proc/sys/kernel/osrelease')))"],
        capture_output=True, text=True, timeout=2, check=False,
    )
    assert result.returncode == 0
    assert "could_not_run" in result.stdout


def test_sysfs_confined_resolved_ancestor_remains_bounded(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "sys/kernel").mkdir(parents=True)
    (root / "sys/kernel/release").write_text("6.1\n", encoding="utf-8")
    (root / "sys/alias").symlink_to(root / "sys/kernel", target_is_directory=True)
    assert hd._sysfs_text(root, root / "sys/alias/release") == {
        "status": "ok", "value": "6.1"}
    outside = tmp_path / "outside"
    outside.write_text("escape", encoding="utf-8")
    (root / "sys/kernel/escape").symlink_to(outside)
    assert hd._sysfs_text(root, root / "sys/kernel/escape")["status"] == "could_not_run"
    (root / "sys/escape-dir").symlink_to(outside.parent, target_is_directory=True)
    assert hd._sysfs_text(root, root / "sys/escape-dir/outside")["status"] == "could_not_run"


def test_sysfs_interface_scandir_error_is_reported(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    net = tmp_path / "sys/class/net"
    net.mkdir(parents=True)

    def denied(_path: Path) -> Any:
        raise PermissionError("net directory denied")

    monkeypatch.setattr(hd.os, "scandir", denied)
    result = hd._interfaces(tmp_path)
    assert result["status"] == "could_not_run"
    assert "PermissionError" in result["error"]


def test_optional_sysfs_disappearance_after_resolution_stays_unknown(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    serial = tmp_path / "sys/devices/usb1/1-1/serial"
    serial.parent.mkdir(parents=True)
    serial.write_text("unit-01", encoding="ascii")

    def raced(_path: Path) -> dict[str, str]:
        return {"status": "could_not_run", "error": "FileNotFoundError: raced"}

    monkeypatch.setattr(hd, "_bounded_sysfs_text", raced)
    assert hd._device_attributes(tmp_path, serial.parent, ("serial",))["serial"] == {
        "status": "unknown", "reason": "sysfs attribute absent"}
    assert hd._sysfs_text(tmp_path, serial, optional=True) == {
        "status": "unknown", "reason": "sysfs attribute absent"}


def test_optional_text_distinguishes_success_and_raced_absence(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    value = tmp_path / "optional"
    value.write_text("present", encoding="utf-8")
    assert hd.read_optional_text(value) == {"status": "ok", "value": "present"}

    def raced(_path: Path) -> dict[str, str]:
        return {"status": "could_not_run", "error": "FileNotFoundError: raced"}

    monkeypatch.setattr(hd, "read_text", raced)
    assert hd.read_optional_text(value) == {
        "status": "unknown", "reason": "sysfs attribute absent"}


def test_pci_binding_reports_escaping_driver_and_module_targets(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-links"
    outside.mkdir()
    pci = tmp_path / "sys/devices/0000:00:01.0"
    pci.mkdir(parents=True)
    (pci / "vendor").write_text("0x10ec", encoding="ascii")
    (pci / "device").write_text("0x8127", encoding="ascii")
    interface = tmp_path / "sys/class/net/eth0"
    interface.mkdir(parents=True)
    (interface / "device").symlink_to(os.path.relpath(pci, interface))
    drivers = tmp_path / "sys/bus/pci/drivers"
    drivers.mkdir(parents=True)
    (pci / "driver").symlink_to(outside, target_is_directory=True)
    assert hd.pci_binding(tmp_path, "eth0")["status"] == "could_not_run"

    driver = drivers / "test-driver"
    driver.mkdir()
    (pci / "driver").unlink()
    (pci / "driver").symlink_to(os.path.relpath(driver, pci), target_is_directory=True)
    (driver / "module").symlink_to(outside, target_is_directory=True)
    result = hd.pci_binding(tmp_path, "eth0")
    assert result["status"] == "could_not_run"
    assert "outside" in result["error"].lower()


def test_pci_inventory_reports_unavailable_list_invalid_name_and_driver_escape(
        tmp_path: Path) -> None:
    assert hd._pci_device_inventory(tmp_path)["status"] == "could_not_run"
    devices = tmp_path / "sys/bus/pci/devices"
    devices.mkdir(parents=True)
    (devices / "not-a-pci-address").mkdir()
    inventory = hd._pci_device_inventory(tmp_path)
    assert inventory["errors"] == {"not-a-pci-address": "invalid PCI address"}

    pci = tmp_path / "sys/devices/0000:00:01.0"
    pci.mkdir(parents=True)
    for name, value in {"vendor": "0x10ec", "device": "0x8127", "class": "0x020000"}.items():
        (pci / name).write_text(value, encoding="ascii")
    (devices / "0000:00:01.0").symlink_to(pci, target_is_directory=True)
    outside = tmp_path.parent / f"{tmp_path.name}-outside-pci-driver"
    outside.mkdir()
    (pci / "driver").symlink_to(outside, target_is_directory=True)
    inventory = hd._pci_device_inventory(tmp_path)
    assert inventory["devices"]["0000:00:01.0"]["driver"]["status"] == "could_not_run"


def test_sysfs_cli_report_and_incompatible_backup_flags(tmp_path: Path,
                                                       capsys: pytest.CaptureFixture[str]) -> None:
    result = hd.main(["--sysfs-only", "--root", str(tmp_path)])
    assert result == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "partial"

    with pytest.raises(SystemExit, match="2"):
        hd.main(["--sysfs-only", "--backup-source", "disk"])
    assert "cannot be combined" in capsys.readouterr().err


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
    (pci_device / "driver").symlink_to(os.path.relpath(drivers, pci_device))
    (drivers / "module").symlink_to(os.path.relpath(sysfs / "module/r8127", drivers))
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
    r8169 = sysfs / "bus/pci/drivers/r8169"
    r8169.mkdir(parents=True)
    (pci_device / "driver").symlink_to(os.path.relpath(r8169, pci_device))
    assert hd.pci_binding(tmp_path, "enp1s0")["driver"] == "r8169"

    virtual = tmp_path / "sys/class/net/docker0"
    virtual.mkdir(parents=True)
    assert hd.pci_binding(tmp_path, "docker0")["status"] == "not_pci"
    assert hd.pci_binding(tmp_path, "../bad")["status"] == "could_not_run"

    (pci_device / "vendor").unlink()
    os.mkfifo(pci_device / "vendor")
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
    (interface_dir / "device").symlink_to(os.path.relpath(pci_device, interface_dir))
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
    example_driver = tmp_path / "sys/bus/pci/drivers/example"
    example_driver.mkdir(parents=True)
    (pci_device / "driver").symlink_to(os.path.relpath(example_driver, pci_device))

    def failed_module_link(path: Path) -> Path:
        if path.name == "module":
            raise OSError("module link unavailable")
        return original(path)

    monkeypatch.setattr(Path, "readlink", failed_module_link)
    assert hd.pci_binding(tmp_path, "eth0")["error"] == "OSError: module link unavailable"


def test_pci_sysfs_readers_reject_symlinks_that_escape_fixture_root(
        tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-device"
    outside.mkdir()
    (outside / "vendor").write_text("secret-vendor", encoding="ascii")
    (outside / "device").write_text("secret-device", encoding="ascii")
    interface = tmp_path / "sys/class/net/eth0"
    interface.mkdir(parents=True)
    (interface / "device").symlink_to(outside, target_is_directory=True)
    binding = hd.pci_binding(tmp_path, "eth0")
    assert binding["status"] == "could_not_run"
    assert "outside" in binding["error"].lower()

    internal = tmp_path / "sys/devices/0000:02:00.0"
    internal.mkdir(parents=True)
    (internal / "vendor").symlink_to(outside / "vendor")
    (internal / "device").write_text("0x1234", encoding="ascii")
    (interface / "device").unlink()
    (interface / "device").symlink_to(internal, target_is_directory=True)
    attribute_binding = hd.pci_binding(tmp_path, "eth0")
    assert attribute_binding["status"] == "could_not_run"
    assert "outside" in str(attribute_binding["error"]).lower()

    devices = tmp_path / "sys/bus/pci/devices"
    devices.mkdir(parents=True)
    (devices / "0000:01:00.0").symlink_to(outside, target_is_directory=True)
    inventory = hd._pci_device_inventory(tmp_path)
    assert inventory["status"] == "could_not_run"
    assert inventory["devices"]["0000:01:00.0"]["status"] == "could_not_run"


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
    assert result["checks"]["gpu_runtime"]["running_container_image_ids"]["status"] == "partial"
    assert result["could_not_run"] > 0
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
