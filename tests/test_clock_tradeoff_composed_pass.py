"""Voto de Luis 2026-10-16: el tradeoff pasa sólo si inventario, labels y el A/B compuesto pasan en la misma ventana.

Fixtures sintéticas: la A/B sana es `_scenario()` de test_cobertura_g3_hardware (con su misma costura `_csv_policy`,
porque GB10 no expone el rango -lgc activo); el inventario térmico extiende el `_capture` de los tests semánticos.
Nada sale del host vivo.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from test_clock_tradeoff_observation_semantics import _capture as _thermal_base
from test_cobertura_g3_hardware import _bench, _evidence, _fake_policy, _scenario
from tools import verify_clock_cap_tradeoff as tradeoff
from tools import verify_gpu_clock_cap_ab as gpu

INSIDE_WINDOW = "2026-10-04T00:00:20+00:00"  # _scenario() fecha sus filas desde 2026-10-04T00:00:00, 2 s por fila


@pytest.fixture(autouse=True)
def policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gpu, "_csv_policy", _fake_policy)


def _thermal(*, stamp: str = INSIDE_WINDOW, label: str = "ok", trips: bool = True,
             unavailable: int = 0, zone_c: float = 60.0) -> dict[str, Any]:
    capture = _thermal_base(labels=[{"status": label, "value": "GPU"}], unavailable=unavailable)
    trip = [{"type": {"status": "ok", "value": "critical"},
             "temperature": {"status": "ok", "value": 104.8}}] if trips else []
    capture["thermal_zones"] = [{"name": "thermal_zone0", "type": {"status": "ok", "value": "acpitz"},
                                 "temperature": {"status": "ok", "value": zone_c}, "trip_points": trip}]
    capture["thermal_zone_scan"] = {"count": 1}
    capture["captured_at_utc"] = stamp
    return capture


def _run(tmp_path: Path, thermal: dict[str, Any], ab_rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    thermal_path = tmp_path / "thermal.json"
    thermal_path.write_text(json.dumps(thermal), encoding="utf-8")
    ab_dir = tmp_path / "ab"
    ab_dir.mkdir()
    if ab_rows is not None:
        _evidence(ab_dir, ab_rows)
    return tradeoff.verify(thermal_path, ab_dir)


def test_pass_when_inventory_labels_threshold_and_composed_ab_share_one_window(tmp_path: Path) -> None:
    result = _run(tmp_path, _thermal(), _scenario())
    assert result["status"] == "pass" and result["fail"] == 0 and result["could_not_run"] == 0, result
    assert set(result["checks"].values()) == {"pass"}, result
    assert "throughput=100.000/80.000 tok/s" in result["reason"], result


def test_ab_missing_stays_unknown(tmp_path: Path) -> None:
    result = _run(tmp_path, _thermal(), None)
    assert result["status"] == "unknown" and result["could_not_run"] == 1, result
    assert result["checks"]["matched_clock_runs"] == "unknown" and result["checks"]["rollback"] == "unknown", result


def test_ab_failure_propagates_as_fail(tmp_path: Path) -> None:
    result = _run(tmp_path, _thermal(), _scenario(capped_clock=2200))
    assert result["status"] == "fail" and "exceeded the applied cap" in result["reason"], result
    assert result["checks"]["matched_clock_runs"] == "fail", result


def test_ab_without_rollback_readback_stays_unknown(tmp_path: Path) -> None:
    rows = _scenario()[:-1]  # se quita el readback posterior al rollback 300,2800
    result = _run(tmp_path, _thermal(), rows)
    assert result["status"] == "unknown" and "readbacks" in result["reason"], result
    assert result["checks"]["rollback"] == "unknown", result


def test_window_mismatch_is_fail(tmp_path: Path) -> None:
    result = _run(tmp_path, _thermal(stamp="2026-10-03T17:23:11+00:00"), _scenario())
    assert result["status"] == "fail" and "outside the A/B evidence window" in result["reason"], result
    assert result["checks"]["same_window"] == "fail", result


def test_identity_mismatch_is_fail(tmp_path: Path) -> None:
    thermal = _thermal()
    thermal["host"]["dmi"]["product_name"] = {"status": "ok", "value": "Other product"}
    result = _run(tmp_path, thermal, _scenario())
    assert result["status"] == "fail" and "different OEM/product" in result["reason"], result


def test_thermal_inventory_missing_or_incomplete_is_not_pass(tmp_path: Path) -> None:
    ab_dir = tmp_path / "ab"
    ab_dir.mkdir()
    _evidence(ab_dir, _scenario())
    missing = tradeoff.verify(tmp_path / "absent.json", ab_dir)
    assert missing["status"] == "unknown" and missing["checks"]["thermal_inventory"] == "unknown", missing
    (tmp_path / "x").mkdir()
    incomplete = _run(tmp_path / "x", _thermal(unavailable=1), _scenario())
    assert incomplete["status"] == "unknown" and incomplete["checks"]["thermal_inventory"] == "unknown", incomplete


def test_label_missing_stays_unknown(tmp_path: Path) -> None:
    result = _run(tmp_path, _thermal(label="absent"), _scenario())
    assert result["status"] == "unknown" and "lack labels" in result["reason"], result
    assert result["checks"]["sensor_labels"] == "unknown" and result["checks"]["matched_clock_runs"] == "pass", result


def test_oem_threshold_missing_is_unknown_and_exceeded_is_fail(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    missing = _run(tmp_path / "a", _thermal(trips=False), _scenario())
    assert missing["status"] == "unknown" and "OEM-safe threshold" in missing["reason"], missing
    hot = _run(tmp_path / "b", _thermal(zone_c=105.0), _scenario(capped_bench=_bench(80)))
    assert hot["status"] == "fail" and "trip point" in hot["reason"], hot


def _bridged(*, zone_types: tuple[str | None, ...] = ("acpitz", "acpitz"),
             extra: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Forma de la captura real: hwmon `acpitz` sin temp*_label, puente thermal_hwmon a thermal_zone*/type."""
    capture = _thermal()
    trip = capture["thermal_zones"][0]["trip_points"]
    capture["thermal_zones"] = [
        {"name": f"thermal_zone{i}", "temperature": {"status": "ok", "value": 45.0}, "trip_points": trip,
         "type": {"status": "ok", "value": kind} if kind else {"status": "absent", "error": "type unavailable"}}
        for i, kind in enumerate(zone_types)]
    capture["thermal_zone_scan"] = {"count": len(zone_types)}
    unlabelled = {"status": "absent", "error": "label unavailable"}
    capture["hwmon"] = [
        {"name": "hwmon0", "chip_name": {"status": "ok", "value": "acpitz"},
         "temperature_inputs": [{"path": f"/sys/class/hwmon/hwmon0/temp{i + 1}_input", "label": unlabelled}
                                for i in range(len(zone_types))]},
        {"name": "hwmon1", "chip_name": {"status": "ok", "value": "nvme"},
         "temperature_inputs": [{"path": "/sys/class/hwmon/hwmon1/temp1_input",
                                 "label": {"status": "ok", "value": "Composite"}}]},
        *(extra or [])]
    capture["hwmon_scan"] = {"count": len(capture["hwmon"])}
    return capture


def test_unlabelled_inputs_identified_by_thermal_zone_type_pass(tmp_path: Path) -> None:
    """Voto de Luis 2026-10-20: sin temp*_label, la zona se identifica por thermal_zone*/type."""
    result = _run(tmp_path, _bridged(), _scenario())
    assert result["checks"]["sensor_labels"] == "pass", result
    assert result["status"] == "pass", result


def test_zone_without_label_nor_type_is_not_pass(tmp_path: Path) -> None:
    """Control negativo: una zona sin label ni type rompe el puente y deja sensor_labels en unknown."""
    result = _run(tmp_path, _bridged(zone_types=("acpitz", None)), _scenario())
    assert result["checks"]["sensor_labels"] == "unknown", result
    assert result["status"] == "unknown" and "hwmon0/temp1_input" in result["reason"], result
    assert "hwmon0/temp2_input" in result["reason"], result


def _wifi(*, name: dict[str, Any] | None = None, inputs: int = 1, hwmon: str = "hwmon2") -> dict[str, Any]:
    """La forma de mt7925_phy0 en la captura real: hwmon sin label y sin thermal_zone de su type."""
    device: dict[str, Any] = {"name": hwmon, "temperature_inputs": [
        {"path": f"/sys/class/hwmon/{hwmon}/temp{i + 1}_input",
         "label": {"status": "absent", "error": "label unavailable"}} for i in range(inputs)]}
    if name is not None:
        device["chip_name"] = name
    return device


WIFI_NAME = {"status": "ok", "value": "mt7925_phy0"}


def test_single_input_device_identified_by_unique_chip_name_pass(tmp_path: Path) -> None:
    """Voto de Luis 2026-10-20 (segunda boleta): name del hwmon unico + una sola temp*_input = identificado."""
    result = _run(tmp_path, _bridged(extra=[_wifi(name=WIFI_NAME)]), _scenario())
    assert result["checks"]["sensor_labels"] == "pass", result
    assert result["status"] == "pass", result


@pytest.mark.parametrize("case", ["no_chip_name", "chip_name_absent", "chip_name_blank", "chip_name_repeated",
                                  "two_inputs"])
def test_chip_name_rule_restrictions_keep_unknown(tmp_path: Path, case: str) -> None:
    """Controles negativos de la regla del chip_name: cada restriccion rota deja la entrada sin identificar."""
    extra = {
        "no_chip_name": [_wifi()],
        "chip_name_absent": [_wifi(name={"status": "absent", "error": "name unavailable"})],
        "chip_name_blank": [_wifi(name={"status": "ok", "value": "  "})],
        "chip_name_repeated": [_wifi(name=WIFI_NAME), _wifi(name=WIFI_NAME, hwmon="hwmon3")],
        "two_inputs": [_wifi(name=WIFI_NAME, inputs=2)],
    }[case]
    result = _run(tmp_path, _bridged(extra=extra), _scenario())
    assert result["checks"]["sensor_labels"] == "unknown", result
    assert result["status"] == "unknown" and "hwmon2/temp1_input" in result["reason"], result
    assert "hwmon0/" not in result["reason"], result


def test_bridge_count_mismatch_or_ambiguous_name_is_not_pass(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    short = _bridged()
    short["thermal_zones"] = short["thermal_zones"][:1]
    short["thermal_zone_scan"] = {"count": 1}
    assert _run(tmp_path / "a", short, _scenario())["checks"]["sensor_labels"] == "unknown"
    twin = {"name": "hwmon2", "chip_name": {"status": "ok", "value": "acpitz"},
            "temperature_inputs": [{"path": "/sys/class/hwmon/hwmon2/temp1_input",
                                    "label": {"status": "ok", "value": "x"}}]}
    assert _run(tmp_path / "b", _bridged(extra=[twin]), _scenario())["checks"]["sensor_labels"] == "unknown"
