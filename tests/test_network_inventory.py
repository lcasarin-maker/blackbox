from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any

import pytest

from tools import host_diagnostics as hd


class Runner:
    def __init__(self, records: Any = None) -> None:
        self.records = records
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["timeout"] == hd.TIMEOUT_S
        assert kwargs.get("shell", False) is False
        if argv == ["ip", "-j", "link", "show"]:
            output = self.records if isinstance(self.records, str) else json.dumps(self.records)
            return subprocess.CompletedProcess(argv, 0, output, "")
        return subprocess.CompletedProcess(argv, 0, "", "")


def _link(root: Path, logical: str, target: Path) -> None:
    link = root / "sys" / logical
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(os.path.relpath(target, link.parent))


def _network_tree(root: Path) -> tuple[Path, Path, Path]:
    pci = root / "sys/devices/pci0000:00/0000:00:01.0"
    pci.mkdir(parents=True)
    (pci / "vendor").write_text("0x15b3", encoding="ascii")
    (pci / "device").write_text("0x101d", encoding="ascii")
    netdev = root / "sys/class/net/eth0"
    netdev.mkdir(parents=True)
    for key, value in {"mtu": "9000", "carrier": "1", "operstate": "up"}.items():
        (netdev / key).write_text(value, encoding="ascii")
    _link(root, "class/net/eth0/device", pci)
    hca = pci / "infiniband/mlx5_0"
    port = hca / "ports/1"
    for directory in (port / "gids", port / "gid_attrs/types", port / "gid_attrs/ndevs"):
        directory.mkdir(parents=True)
    for path, value in {
        hca / "fw_ver": "28.47.1000", hca / "node_guid": "0011:2233:4455:6677",
        hca / "sys_image_guid": "0011:2233:4455:6688", port / "link_layer": "Ethernet",
        port / "state": "4: ACTIVE", port / "gids/0": "fe80::211:22ff:fe33:4455",
        port / "gid_attrs/types/0": "RoCE v2", port / "gid_attrs/ndevs/0": "eth0",
    }.items():
        path.write_text(value, encoding="ascii")
    _link(root, "bus/pci/devices/0000:00:01.0", pci)
    _link(root, "class/infiniband/mlx5_0", hca)
    (hca / "device").symlink_to(os.path.relpath(pci, hca))
    return pci, netdev, hca


def test_ip_link_inventory_reads_native_json_and_keeps_missing_fields_unknown() -> None:
    runner = Runner([
        {"ifname": "eth0", "ifindex": 2, "mtu": 9000, "operstate": "UP",
         "link_type": "ether"},
        {"ifname": "eth1", "ifindex": 3, "operstate": "DOWN"},
    ])

    result = hd.ip_link_inventory(runner)

    assert runner.calls == [["ip", "-j", "link", "show"]]
    assert result["status"] == "ok"
    assert result["links"]["eth0"]["mtu"] == {"status": "ok", "value": 9000}
    assert result["links"]["eth1"]["status"] == "partial"
    assert result["links"]["eth1"]["mtu"]["status"] == "unknown"
    assert "address" not in result["links"]["eth0"]


@pytest.mark.parametrize("payload,expected", [
    ("not-json", "JSONDecodeError"),
    ("{}", "root is not a list"),
    ([None, {"ifname": "../bad"}, {"ifname": "eth0"}, {"ifname": "eth0"}],
     "duplicate interface name"),
])
def test_ip_link_inventory_rejects_invalid_native_output(payload: Any, expected: str) -> None:
    result = hd.ip_link_inventory(Runner(payload))
    assert result["status"] == "could_not_run"
    assert expected in str(result.get("error", result.get("errors")))


def test_ip_link_inventory_preserves_command_failure() -> None:
    class Denied:
        def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            raise PermissionError("ip denied")

    result = hd.ip_link_inventory(Denied())
    assert result["status"] == "could_not_run"
    assert result["command"] == ["ip", "-j", "link", "show"]


def test_infiniband_inventory_preserves_absent_subsystem(tmp_path: Path) -> None:
    result = hd.infiniband_inventory(tmp_path)
    assert result["status"] == "could_not_run"
    assert result["devices"] == {}


def test_infiniband_inventory_preserves_inaccessible_root_listing(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "sys/class/infiniband"
    path.mkdir(parents=True)
    original = hd.read_names

    def denied(directory: Path) -> dict[str, Any]:
        if directory == path:
            return {"status": "could_not_run", "error": "PermissionError: denied"}
        return original(directory)

    monkeypatch.setattr(hd, "read_names", denied)
    result = hd.infiniband_inventory(tmp_path)
    assert result == {"status": "could_not_run", "error": "PermissionError: denied",
                      "devices": {}}


@pytest.mark.parametrize("escape", ["root", "hca", "ports", "port", "gids"])
def test_infiniband_inventory_rejects_sysfs_directory_escape(
        tmp_path: Path, escape: str) -> None:
    class_dir = tmp_path / "sys/class"
    class_dir.mkdir(parents=True)
    if escape == "root":
        (class_dir / "infiniband").symlink_to("/etc")
    else:
        root = class_dir / "infiniband"
        root.mkdir()
        if escape == "hca":
            (root / "mlx5_0").symlink_to("/etc")
        else:
            hca = tmp_path / "sys/devices/pci0000:00/infiniband/mlx5_0"
            hca.mkdir(parents=True)
            (root / "mlx5_0").symlink_to(os.path.relpath(hca, root))
            if escape == "ports":
                (hca / "ports").symlink_to("/etc")
            elif escape == "port":
                (hca / "ports").mkdir()
                (hca / "ports/1").symlink_to("/etc")
            else:
                (hca / "ports/1").mkdir(parents=True)
                (hca / "ports/1/gids").symlink_to("/etc")

    result = hd.infiniband_inventory(tmp_path)

    assert result["status"] == "could_not_run"
    assert result["devices"].get("mlx5_0", {}).get("status", "could_not_run") == \
        "could_not_run"


def test_infiniband_inventory_correlates_gid_netdev_pci_and_firmware(tmp_path: Path) -> None:
    _pci, _netdev, _hca = _network_tree(tmp_path)

    result = hd.infiniband_inventory(tmp_path)

    device = result["devices"]["mlx5_0"]
    assert result["status"] == "ok"
    assert device["firmware_version"] == {"status": "ok", "value": "28.47.1000"}
    assert device["pci"]["pci_address"] == "0000:00:01.0"
    gid = device["ports"]["1"]["gids"]["0"]
    assert gid["gid"]["value"] == "fe80::211:22ff:fe33:4455"
    assert gid["type"]["value"] == "RoCE v2"
    assert gid["netdev"]["value"] == "eth0"
    assert gid["pci_binding"]["pci_vendor"] == "0x15b3"


def test_infiniband_inventory_reports_missing_port_and_gid_records(tmp_path: Path) -> None:
    hca = tmp_path / "sys/devices/pci0000:00/0000:00:02.0/infiniband/mlx5_1"
    (hca / "ports/not-a-port").mkdir(parents=True)
    bad_gid = hca / "ports/1/gids/not-a-gid"
    bad_gid.parent.mkdir(parents=True)
    bad_gid.write_text("invalid", encoding="ascii")
    _link(tmp_path, "class/infiniband/mlx5_1", hca)

    result = hd.infiniband_inventory(tmp_path)

    assert result["status"] == "could_not_run"
    assert result["devices"]["mlx5_1"]["ports"]["not-a-port"]["status"] == "could_not_run"
    assert result["devices"]["mlx5_1"]["ports"]["1"]["gids"]["not-a-gid"]["status"] == \
        "could_not_run"


def test_infiniband_inventory_marks_missing_ports_and_gid_tables(tmp_path: Path) -> None:
    no_ports = tmp_path / "sys/devices/pci0000:00/0000:00:03.0/infiniband/mlx5_2"
    no_ports.mkdir(parents=True)
    _link(tmp_path, "class/infiniband/mlx5_2", no_ports)
    no_gids = tmp_path / "sys/devices/pci0000:00/0000:00:04.0/infiniband/mlx5_3/ports/1"
    no_gids.mkdir(parents=True)
    _link(tmp_path, "class/infiniband/mlx5_3", no_gids.parent.parent)
    no_netdev = tmp_path / "sys/devices/pci0000:00/0000:00:05.0/infiniband/mlx5_4/ports/1"
    for directory in (no_netdev / "gids", no_netdev / "gid_attrs/types"):
        directory.mkdir(parents=True)
    for name, value in {"gids/0": "fe80::1", "gid_attrs/types/0": "RoCE v2"}.items():
        (no_netdev / name).write_text(value, encoding="ascii")
    _link(tmp_path, "class/infiniband/mlx5_4", no_netdev.parent.parent)

    result = hd.infiniband_inventory(tmp_path)

    assert result["devices"]["mlx5_2"]["status"] == "could_not_run"
    assert result["devices"]["mlx5_2"]["firmware_version"]["status"] == "unknown"
    assert result["devices"]["mlx5_3"]["ports"]["1"]["status"] == "could_not_run"
    assert result["devices"]["mlx5_4"]["ports"]["1"]["gids"]["0"]["status"] == \
        "could_not_run"


def test_network_inventory_joins_link_sysfs_pci_rdma_and_firmware(tmp_path: Path) -> None:
    _network_tree(tmp_path)
    runner = Runner([{"ifname": "eth0", "ifindex": 2, "mtu": 9000, "operstate": "UP",
                      "link_type": "ether"}])

    result = hd.network_inventory(tmp_path, runner)

    assert runner.calls == [["ip", "-j", "link", "show"]]
    assert result["status"] == "ok"
    assert result["physical_attachment"] == "UNKNOWN"
    assert result["transport_validation"] == "not_run"
    assert result["interfaces"]["eth0"]["mtu_sysfs"]["value"] == "9000"
    assert result["interfaces"]["eth0"]["pci_binding"]["pci_vendor"] == "0x15b3"
    assert result["interfaces"]["eth0"]["firmware_version"]["status"] == "unknown"
    assert result["infiniband"]["devices"]["mlx5_0"]["ports"]["1"]["gids"][
        "0"]["netdev"]["value"] == "eth0"


def test_network_inventory_marks_missing_link_and_rdma_telemetry(tmp_path: Path) -> None:
    result = hd.network_inventory(tmp_path, Runner([]))
    assert result["status"] == "could_not_run"
    assert result["physical_attachment"] == "UNKNOWN"
    assert result["infiniband"]["status"] == "could_not_run"


def test_network_inventory_marks_sysfs_interface_missing_from_ip_json(tmp_path: Path) -> None:
    _network_tree(tmp_path)
    result = hd.network_inventory(tmp_path, Runner([]))
    assert result["status"] == "could_not_run"
    assert result["interfaces_missing_from_ip"] == ["eth0"]
    assert result["interfaces"]["eth0"]["ip_link"]["status"] == "unknown"


def test_network_inventory_propagates_inaccessible_sysfs_fields(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _network_tree(tmp_path)
    original = hd.capture_io.read_regular_bytes

    def denied(path: Path, max_bytes: int) -> bytes:
        if path.name == "mtu":
            raise PermissionError("mtu denied")
        return original(path, max_bytes)

    monkeypatch.setattr(hd.capture_io, "read_regular_bytes", denied)
    result = hd.network_inventory(tmp_path, Runner([
        {"ifname": "eth0", "ifindex": 2, "mtu": 9000, "operstate": "UP",
         "link_type": "ether"}]))

    assert result["status"] == "could_not_run"
    assert result["interfaces"]["eth0"]["status"] == "could_not_run"
    assert result["interfaces"]["eth0"]["mtu_sysfs"]["status"] == "could_not_run"


def test_infiniband_inventory_propagates_unreadable_firmware(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _network_tree(tmp_path)
    original = hd.capture_io.read_regular_bytes

    def denied(path: Path, max_bytes: int) -> bytes:
        if path.name == "fw_ver":
            raise PermissionError("firmware denied")
        return original(path, max_bytes)

    monkeypatch.setattr(hd.capture_io, "read_regular_bytes", denied)
    result = hd.infiniband_inventory(tmp_path)

    assert result["status"] == "could_not_run"
    assert result["devices"]["mlx5_0"]["status"] == "could_not_run"
    assert result["devices"]["mlx5_0"]["firmware_version"]["status"] == "could_not_run"
