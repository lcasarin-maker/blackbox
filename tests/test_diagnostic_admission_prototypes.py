"""Behavior checks for memory unknown handling and thermal channel coverage."""
import json
from pathlib import Path
import runpy
from typing import cast

from tools import recipe_memory, thermal_coverage


def test_recipe_memory_unknown_when_kv_is_unmeasured() -> None:
    result = recipe_memory.assess(
        {"weights": 100, "kv_cache": None, "staging": 0, "graphs": 0,
         "draft": 0, "buffers": 0}, 10_000, 100)
    assert result == {"status": "unknown", "missing_fields": ["kv_cache"]}


def test_recipe_memory_zero_is_measured_and_budget_is_discriminating() -> None:
    measured = cast(dict[str, int | None], {name: 0 for name in recipe_memory.COMPONENTS})
    assert recipe_memory.assess(measured, 0, 0) == {
        "status": "comparison_only", "comparison": "within_declared_budget",
        "required_bytes": 0, "available_bytes": 0, "headroom_bytes": 0}
    measured["weights"] = 1
    assert recipe_memory.assess(measured, 0, 0)["comparison"] == "exceeds_available"
    assert recipe_memory.assess(measured, -1, 0)["status"] == "invalid"
    assert recipe_memory.assess(measured, 0, -1)["invalid_fields"] == ["reserve"]


def test_recipe_collection_preserves_raw_host_capture_and_digest(monkeypatch, tmp_path: Path) -> None:
    raw = {"host_reserve_context": {"memavailable": {"status": "absent", "value": None}}}
    monkeypatch.setattr(recipe_memory, "capture", lambda _root: raw)
    result = recipe_memory.collect({name: None for name in recipe_memory.COMPONENTS}, None, tmp_path)
    assert result["assessment"]["status"] == "unknown"
    assert result["host_memavailable"] == {"status": "absent", "value": None}
    assert result["raw_host_capture"] == raw
    assert result["component_provenance"] == "caller_supplied_unverified"
    assert len(result["record_sha256"]) == 64


def test_recipe_cli_writes_unknown_capture_and_returns_incomplete(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "host"
    (root / "proc").mkdir(parents=True)
    (root / "proc/meminfo").write_text("MemAvailable: 0 kB\n", encoding="utf-8")
    output = tmp_path / "recipe.json"
    monkeypatch.setattr("sys.argv", ["recipe_memory", "--root", str(root), "--output", str(output)])
    assert recipe_memory.main() == 2
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["assessment"]["status"] == "unknown"
    assert record["host_memavailable"]["status"] == "ok"
    assert record["host_memavailable"]["kib"] == 0


def test_recipe_cli_emits_json_and_entrypoint_preserves_incomplete_exit(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    root = tmp_path / "host"
    (root / "proc").mkdir(parents=True)
    (root / "proc/meminfo").write_text("MemAvailable: 20 kB\n", encoding="utf-8")
    args = ["recipe_memory", "--root", str(root), *[
        flag for name in recipe_memory.COMPONENTS for flag in (f"--{name.replace('_', '-')}-bytes", "0")
    ], "--reserve-bytes", "0"]
    monkeypatch.setattr("sys.argv", args)
    try:
        runpy.run_path(str(Path(recipe_memory.__file__)), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("CLI entrypoint did not exit")
    emitted = json.loads(capsys.readouterr().out)
    assert emitted["assessment"]["comparison"] == "within_declared_budget"


def test_thermal_coverage_lists_channels_without_safety_verdict(tmp_path: Path) -> None:
    zone = tmp_path / "sys/class/thermal/thermal_zone0"
    zone.mkdir(parents=True)
    (zone / "type").write_text("acpitz\n", encoding="utf-8")
    (zone / "temp").write_text("92500\n", encoding="utf-8")
    (zone / "trip_point_0_type").write_text("critical\n", encoding="utf-8")
    (zone / "trip_point_0_temp").write_text("104800\n", encoding="utf-8")
    hwmon = tmp_path / "sys/class/hwmon/hwmon0"
    hwmon.mkdir(parents=True)
    (hwmon / "name").write_text("cpu_thermal\n", encoding="utf-8")
    (hwmon / "temp1_input").write_text("90000\n", encoding="utf-8")
    (hwmon / "temp1_label").write_text("CPU\n", encoding="utf-8")
    (hwmon / "fan1_input").write_text("2400\n", encoding="utf-8")
    result = thermal_coverage.capture(tmp_path)
    assert result["status"] == "observed" and result["could_not_run"] == 0
    assert result["thermal_zones"][0]["temperature"]["value"] == 92.5
    assert result["thermal_zones"][0]["trip_points"][0]["temperature"]["value"] == 104.8
    assert result["hwmon"][0]["temperature_inputs"][0]["label"]["value"] == "CPU"
    assert result["hwmon"][0]["fan_inputs"][0]["value"] == 2400
    assert result["assessment"] == "coverage_only; no thermal safety conclusion"


def test_thermal_coverage_missing_sensor_is_unknown(tmp_path: Path) -> None:
    (tmp_path / "sys/class/thermal").mkdir(parents=True)
    (tmp_path / "sys/class/hwmon").mkdir(parents=True)
    result = thermal_coverage.capture(tmp_path)
    assert result["no_sensor_detected"] is True
    assert result["thermal_zone_scan"]["status"] == "no_thermal_zones"
    assert result["could_not_run"] > 0
    assert result["status"] == "partial"


def test_thermal_cli_writes_raw_capture_and_returns_partial(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "sys/class/thermal").mkdir(parents=True)
    (tmp_path / "sys/class/hwmon").mkdir(parents=True)
    output = tmp_path / "thermal.json"
    monkeypatch.setattr("sys.argv", ["thermal_coverage", "--root", str(tmp_path), "--output", str(output)])
    assert thermal_coverage.main() == 2
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["no_sensor_detected"] is True
    assert record["could_not_run"] > 0


def test_thermal_cli_emits_capture_json(monkeypatch, tmp_path: Path, capsys) -> None:
    (tmp_path / "sys/class/thermal").mkdir(parents=True)
    (tmp_path / "sys/class/hwmon").mkdir(parents=True)
    monkeypatch.setattr("sys.argv", ["thermal_coverage", "--root", str(tmp_path)])
    assert thermal_coverage.main() == 2
    assert json.loads(capsys.readouterr().out)["thermal_zone_scan"]["status"] == "no_thermal_zones"


def test_thermal_cli_entrypoint_preserves_incomplete_exit(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "sys/class/thermal").mkdir(parents=True)
    (tmp_path / "sys/class/hwmon").mkdir(parents=True)
    monkeypatch.setattr("sys.argv", ["thermal_coverage", "--root", str(tmp_path)])
    try:
        runpy.run_path(str(Path(thermal_coverage.__file__)), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("CLI entrypoint did not exit")


def test_thermal_coverage_malformed_channel_is_counted(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "sys/class/hwmon").mkdir(parents=True)
    zone = tmp_path / "sys/class/thermal/thermal_zone1"
    zone.mkdir(parents=True)
    (zone / "temp").write_text("unknown", encoding="utf-8")
    monkeypatch.setattr(thermal_coverage, "read_text", lambda path: (
        {"status": "ok", "value": "acpitz"} if path.name == "type" else
        {"status": "ok", "value": "unknown"} if path.name == "temp" else
        {"status": "absent", "error": "missing"}))
    result = thermal_coverage.capture(tmp_path)
    assert result["thermal_zones"][0]["temperature"]["status"] == "malformed"
    assert result["could_not_run"] == 1
    assert result["status"] == "partial"


def test_thermal_coverage_counts_unreadable_temperature(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "sys/class/hwmon").mkdir(parents=True)
    zone = tmp_path / "sys/class/thermal/thermal_zone0"
    zone.mkdir(parents=True)
    (zone / "type").write_text("cpu\n", encoding="utf-8")
    (zone / "temp").write_text("70000\n", encoding="utf-8")
    original = thermal_coverage.read_text

    def denied(path: Path):
        if path.name == "temp":
            return {"status": "could_not_run", "error": "fixture denied"}
        return original(path)

    monkeypatch.setattr(thermal_coverage, "read_text", denied)
    result = thermal_coverage.capture(tmp_path)
    assert result["thermal_zones"][0]["temperature"]["status"] == "could_not_run"
    assert result["could_not_run"] == 1


def test_thermal_coverage_counts_trip_point_enumeration_failure(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "sys/class/hwmon").mkdir(parents=True)
    zone = tmp_path / "sys/class/thermal/thermal_zone0"
    zone.mkdir(parents=True)
    (zone / "type").write_text("cpu\n", encoding="utf-8")
    (zone / "temp").write_text("70000\n", encoding="utf-8")
    original = thermal_coverage.read_names

    def denied(path: Path):
        if path == zone:
            return {"status": "could_not_run", "error": "fixture denied"}
        return original(path)

    monkeypatch.setattr(thermal_coverage, "read_names", denied)
    result = thermal_coverage.capture(tmp_path)
    assert result["thermal_zones"][0]["trip_point_scan"]["status"] == "could_not_run"
    assert result["could_not_run"] == 1


def test_thermal_coverage_counts_unreadable_trip_point_type(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "sys/class/hwmon").mkdir(parents=True)
    zone = tmp_path / "sys/class/thermal/thermal_zone0"
    zone.mkdir(parents=True)
    (zone / "type").write_text("cpu\n", encoding="utf-8")
    (zone / "temp").write_text("70000\n", encoding="utf-8")
    (zone / "trip_point_0_type").write_text("critical\n", encoding="utf-8")
    (zone / "trip_point_0_temp").write_text("95000\n", encoding="utf-8")
    original = thermal_coverage.read_text

    def unreadable(path: Path):
        if path.name == "trip_point_0_type":
            return {"status": "could_not_run", "error": "fixture denied"}
        return original(path)

    monkeypatch.setattr(thermal_coverage, "read_text", unreadable)
    result = thermal_coverage.capture(tmp_path)
    assert result["thermal_zones"][0]["trip_points"][0]["type"]["status"] == "could_not_run"
    assert result["could_not_run"] == 1


def test_thermal_coverage_reports_enumeration_error_separately(monkeypatch, tmp_path: Path) -> None:
    original = thermal_coverage.read_names

    def denied(path: Path):
        if path == tmp_path / "sys/class/thermal":
            return {"status": "could_not_run", "error": "fixture denied"}
        return original(path)

    monkeypatch.setattr(thermal_coverage, "read_names", denied)
    (tmp_path / "sys/class/hwmon").mkdir(parents=True)
    result = thermal_coverage.capture(tmp_path)
    assert result["thermal_zone_scan"] == {
        "status": "could_not_run", "error": "fixture denied", "count": 0}
    assert result["could_not_run"] > 0


def test_thermal_coverage_counts_hwmon_enumeration_error(monkeypatch, tmp_path: Path) -> None:
    thermal = tmp_path / "sys/class/thermal/thermal_zone0"
    thermal.mkdir(parents=True)
    (thermal / "type").write_text("cpu\n", encoding="utf-8")
    (thermal / "temp").write_text("70000\n", encoding="utf-8")
    original = thermal_coverage.read_names

    def denied(path: Path):
        if path == tmp_path / "sys/class/hwmon":
            return {"status": "could_not_run", "error": "fixture denied"}
        return original(path)

    monkeypatch.setattr(thermal_coverage, "read_names", denied)
    result = thermal_coverage.capture(tmp_path)
    assert result["hwmon_scan"] == {
        "status": "could_not_run", "error": "fixture denied", "count": 0}
    assert result["could_not_run"] > 0
