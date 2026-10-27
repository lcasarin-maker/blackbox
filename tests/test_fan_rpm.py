"""FEATURE-FAN-RPM-LEER-ACPI-FAN-DONDE-EXISTA-01: RPM from hwmon acpi_fan, NOT_COLLECTED when absent.

Every test carries its negative control on the same fixture: the opposite verdict
is produced by changing only the fact under test, so a reader that always
answered one way would fail here.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import thermal_coverage


def _hwmon(root: Path, index: int, name: str, fans: dict[int, str] | None = None) -> Path:
    device = root / "sys/class/hwmon" / f"hwmon{index}"
    device.mkdir(parents=True)
    (device / "name").write_text(f"{name}\n", encoding="utf-8")
    for fan, value in (fans or {}).items():
        (device / f"fan{fan}_input").write_text(f"{value}\n", encoding="utf-8")
    return device


def _this_atom(root: Path) -> None:
    """The hwmon names measured on this ATOM on 2026-10-26: no acpi_fan."""
    _hwmon(root, 0, "acpitz")
    _hwmon(root, 1, "nvme")
    _hwmon(root, 2, "mt7925_phy0")


def test_acpi_fan_reports_rpm_per_fan(tmp_path: Path) -> None:
    _this_atom(tmp_path)
    _hwmon(tmp_path, 3, "acpi_fan", {1: "2030"})
    _hwmon(tmp_path, 4, "acpi_fan", {1: "2075"})
    result = thermal_coverage.acpi_fan(tmp_path, str(tmp_path / "forense"))
    assert result["status"] == "observed" and result["could_not_run"] == 0
    assert [(v["hwmon"], v["canal"], v["rpm"], v["estado"]) for v in result["ventiladores"]] == [
        ("hwmon3", "fan1", 2030, "girando"), ("hwmon4", "fan1", 2075, "girando")]

    # Negative control: same fan files under a hwmon that is NOT acpi_fan are not read.
    other = tmp_path / "other"
    _hwmon(other, 3, "nct6775", {1: "2030"})
    control = thermal_coverage.acpi_fan(other, str(other / "forense"))
    assert control["status"] == "NOT_COLLECTED" and control["ventiladores"] == []


def test_acpi_fan_absent_is_not_collected_never_zero(tmp_path: Path) -> None:
    _this_atom(tmp_path)
    result = thermal_coverage.acpi_fan(tmp_path, str(tmp_path / "forense"))
    assert result["status"] == "NOT_COLLECTED"
    assert result["motivo"] == "NOT_COLLECTED: sin hwmon acpi_fan"
    assert result["ventiladores"] == [] and result["could_not_run"] == 1
    assert 0 not in [v["rpm"] for v in result["ventiladores"]]

    # Negative control: adding one acpi_fan hwmon to the same tree flips it to a reading.
    _hwmon(tmp_path, 3, "acpi_fan", {1: "2030"})
    control = thermal_coverage.acpi_fan(tmp_path, str(tmp_path / "forense"))
    assert control["status"] == "observed" and control["ventiladores"][0]["rpm"] == 2030


def test_acpi_fan_zero_is_stopped_not_missing(tmp_path: Path) -> None:
    _hwmon(tmp_path, 0, "acpi_fan", {1: "0"})
    result = thermal_coverage.acpi_fan(tmp_path, str(tmp_path / "forense"))
    fan = result["ventiladores"][0]
    assert fan["rpm"] == 0 and fan["rpm"] is not None
    assert fan["estado"] == "detenido"
    assert result["status"] == "observed" and result["could_not_run"] == 0

    # Negative control: a nonzero value on the same channel is not labelled stopped.
    (tmp_path / "sys/class/hwmon/hwmon0/fan1_input").write_text("1\n", encoding="utf-8")
    control = thermal_coverage.acpi_fan(tmp_path, str(tmp_path / "forense"))
    assert control["ventiladores"][0]["estado"] == "girando"


@pytest.mark.parametrize("make_unreadable", ["directory", "malformed"])
def test_acpi_fan_unreadable_input_is_not_collected_with_reason(tmp_path: Path, make_unreadable: str) -> None:
    device = _hwmon(tmp_path, 0, "acpi_fan", {2: "2075"})
    if make_unreadable == "directory":
        (device / "fan1_input").mkdir()  # read fails with IsADirectoryError
    else:
        (device / "fan1_input").write_text("garbage\n", encoding="utf-8")
    result = thermal_coverage.acpi_fan(tmp_path, str(tmp_path / "forense"))
    fan1, fan2 = result["ventiladores"]
    assert fan1["canal"] == "fan1" and fan1["rpm"] is None
    assert fan1["estado"].startswith("NOT_COLLECTED: ") and len(fan1["estado"]) > len("NOT_COLLECTED: ")
    assert fan2["rpm"] == 2075  # one bad channel does not hide the readable one
    assert result["status"] == "partial" and result["could_not_run"] == 1

    # Negative control: a readable value in the same channel is a reading, not NOT_COLLECTED.
    if make_unreadable == "directory":
        (device / "fan1_input").rmdir()
    (device / "fan1_input").write_text("2030\n", encoding="utf-8")
    control = thermal_coverage.acpi_fan(tmp_path, str(tmp_path / "forense"))
    assert control["ventiladores"][0]["rpm"] == 2030 and control["status"] == "observed"


def test_acpi_fan_carries_oem_and_firmware_identity(tmp_path: Path) -> None:
    dmi = tmp_path / "sys/class/dmi/id"
    dmi.mkdir(parents=True)
    (dmi / "sys_vendor").write_text("NVIDIA\n", encoding="utf-8")
    forense = tmp_path / "forense"
    forense.mkdir()
    (forense / "dmidecode-t45.txt").write_text(
        "\tFirmware Component Name: EC Firmware\n\tFirmware Version: 3.5.11\n", encoding="utf-8")
    (forense / "dmidecode-bios.txt").write_text("\tVersion: 5.36_0ACUM08\n", encoding="utf-8")
    _hwmon(tmp_path, 0, "acpi_fan", {1: "2030"})
    result = thermal_coverage.acpi_fan(tmp_path, str(forense))
    assert result["identidad"]["sys_vendor"] == {"status": "ok", "value": "NVIDIA"}
    assert "EC Firmware=3.5.11" in result["identidad"]["firmware"]
    assert "BIOS=5.36_0ACUM08" in result["identidad"]["firmware"]

    # Negative control: without the forensic files the firmware is NOT_COLLECTED, not empty.
    control = thermal_coverage.acpi_fan(tmp_path, str(tmp_path / "absent"))
    assert control["identidad"]["firmware"] == "NOT_COLLECTED"
    assert control["identidad"]["product_name"]["status"] == "could_not_run"


def test_acpi_fan_cli_exit_code_tracks_could_not_run(tmp_path: Path, monkeypatch, capsys) -> None:
    _this_atom(tmp_path)
    argv = ["thermal_coverage", "--acpi-fan", "--root", str(tmp_path), "--forense-dir", str(tmp_path / "f")]
    monkeypatch.setattr("sys.argv", argv)
    assert thermal_coverage.main() == 2
    assert json.loads(capsys.readouterr().out)["motivo"] == "NOT_COLLECTED: sin hwmon acpi_fan"

    # Negative control: with a readable acpi_fan the same command exits 0.
    _hwmon(tmp_path, 3, "acpi_fan", {1: "0"})
    assert thermal_coverage.main() == 0
    assert json.loads(capsys.readouterr().out)["ventiladores"][0]["estado"] == "detenido"
