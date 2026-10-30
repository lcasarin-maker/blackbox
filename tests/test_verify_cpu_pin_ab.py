"""verify_cpu_pin_ab: a complete synthetic A/B passes; every mutation must change the verdict."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

from tools import verify_cpu_pin_ab as ab

ROOT = Path(__file__).resolve().parents[1]
A725, X925, ALL = "0-4,10-14", "5-9,15-19", "0-19"
WORKLOAD = {"model_sha256": "m" * 64, "image_digest": "sha256:" + "i" * 64,
            "input_sha256": "x" * 64, "concurrency": 4, "max_new_tokens": 256}


def _run(arm: str, repeat: int, hottest: float, cpuset: str, readback: str | None) -> dict[str, Any]:
    zones = {f"acpitz{n}": {"peak_c": hottest - n, "mean_c": hottest - n - 2.0} for n in range(7)}
    run: dict[str, Any] = {
        "arm": arm, "repeat": repeat, "cpuset": cpuset, "duration_seconds": 1900,
        "clock_cap_mhz": 2100, "workload": dict(WORKLOAD), "zones_c": zones,
        "clock_mhz": {"mean": 1900.0, "min": 1400.0}, "decode_tok_s": 107.0,
        "prefill_tok_s": 2400.0, "power_w_mean": 55.0, "gpu_util_mean_pct": 80.0,
        "clocks_event_reasons": "0x0000000000000000",
    }
    if readback is not None:
        run["taskset_readback"] = readback
    return run


def _evidence() -> dict[str, Any]:
    runs = []
    for repeat, delta in ((1, 0.0), (2, 0.5)):
        runs.append(_run("unpinned", repeat, 94.0 + delta, ALL, None))
        runs.append(_run("pin_a725", repeat, 72.0 + delta, A725, A725))
        runs.append(_run("pin_x925", repeat, 93.5 + delta, X925, X925))
    return {
        "id": ab.FINDING,
        "plan": {"a725_cpus": A725, "x925_cpus": X925, "all_cpus": ALL, "min_arm_seconds": 1800,
                 "min_repeats": 2, "min_cooling_c": 3.0, "max_repeat_spread_c": 2.0,
                 "min_gpu_util_pct": 30.0},
        "topology": {A725: "0x410fd871", X925: "0x410fd851"},
        "runs": runs,
        "rollback": {"command": "taskset -a -p -c 0-19 1245358", "exit": 0,
                     "readback_exit": 0, "readback_cpuset": ALL},
    }


def _write(directory: Path, data: Any) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "ab.json").write_text(json.dumps(data), encoding="utf-8")
    return directory


def _drop_arm(arm: str) -> Callable[[dict[str, Any]], None]:
    return lambda d: d.__setitem__("runs", [r for r in d["runs"] if r["arm"] != arm])


def _control_cools(d: dict[str, Any]) -> None:
    for run in d["runs"]:
        if run["arm"] == "pin_x925":
            run["zones_c"] = {k: {"peak_c": v["peak_c"] - 20.0, "mean_c": v["mean_c"] - 20.0}
                              for k, v in run["zones_c"].items()}


def _one_repeat(d: dict[str, Any]) -> None:
    d["runs"] = [r for r in d["runs"] if r["repeat"] == 1]


def _drop_zone(d: dict[str, Any]) -> None:
    del d["runs"][1]["zones_c"]["acpitz6"]


def _set(path: tuple[Any, ...], value: Any) -> Callable[[dict[str, Any]], None]:
    def apply(d: dict[str, Any]) -> None:
        node: Any = d
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
    return apply


def _pop_key(key: str) -> Callable[[dict[str, Any]], None]:
    return lambda d: d.pop(key)


def _no_null_effect(d: dict[str, Any]) -> None:
    for run in d["runs"]:
        if run["arm"] == "pin_a725":
            run["zones_c"] = copy.deepcopy(d["runs"][0]["zones_c"])


# name, mutation, expected status, expected exit code
CASES: list[tuple[str, Callable[[dict[str, Any]], None], str, int]] = [
    ("missing_x925_arm", _drop_arm("pin_x925"), "unknown", 2),
    ("missing_unpinned_arm", _drop_arm("unpinned"), "unknown", 2),
    ("missing_a725_arm", _drop_arm("pin_a725"), "unknown", 2),
    ("missing_zone", _drop_zone, "unknown", 2),
    ("missing_rollback", _pop_key("rollback"), "unknown", 2),
    ("rollback_failed", _set(("rollback", "exit"), 1), "unknown", 2),
    ("rollback_readback_wrong", _set(("rollback", "readback_cpuset"), A725), "fail", 1),
    ("control_also_cools", _control_cools, "fail", 1),
    ("single_repeat", _one_repeat, "unknown", 2),
    ("short_run", _set(("runs", 0, "duration_seconds"), 300), "unknown", 2),
    ("gpu_idle", _set(("runs", 0, "gpu_util_mean_pct"), 1.0), "unknown", 2),
    ("different_cap", _set(("runs", 1, "clock_cap_mhz"), 1400), "fail", 1),
    ("different_workload", _set(("runs", 2, "workload", "concurrency"), 8), "fail", 1),
    ("pin_readback_differs", _set(("runs", 1, "taskset_readback"), ALL), "fail", 1),
    ("wrong_cpuset_for_arm", _set(("runs", 1, "cpuset"), X925), "fail", 1),
    ("a725_cpus_are_not_a725", _set(("topology", A725), "0x410fd851"), "fail", 1),
    ("no_topology", _pop_key("topology"), "unknown", 2),
    ("no_plan", _pop_key("plan"), "unknown", 2),
    ("plan_one_repeat", _set(("plan", "min_repeats"), 1), "unknown", 2),
    ("noisy_repeats", _set(("runs", 3, "zones_c", "acpitz0", "peak_c"), 99.0), "unknown", 2),
    ("no_event_reasons", _set(("runs", 0, "clocks_event_reasons"), ""), "unknown", 2),
    ("nan_power", _set(("runs", 0, "power_w_mean"), "nan"), "unknown", 2),
    ("wrong_finding_id", _set(("id",), "OTHER"), "unknown", 2),
]


def test_complete_evidence_passes(tmp_path: Path) -> None:
    result = ab.verify(_write(tmp_path, _evidence()))
    assert result["status"] == "pass" and result["fail"] == 0 and result["could_not_run"] == 0
    assert result["effect"] == "cooling" and set(result["per_zone_drop_a725_c"]) == {f"acpitz{n}" for n in range(7)}
    assert ab.main(["--evidence", str(tmp_path)]) == 0


def test_null_result_is_valid_and_passes(tmp_path: Path) -> None:
    data = _evidence()
    _no_null_effect(data)
    result = ab.verify(_write(tmp_path, data))
    assert result["status"] == "pass" and result["effect"] == "null"


@pytest.mark.parametrize(("name", "mutate", "status", "code"), CASES, ids=[c[0] for c in CASES])
def test_each_mutation_changes_the_verdict(
    tmp_path: Path, name: str, mutate: Callable[[dict[str, Any]], None], status: str, code: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = _evidence()
    mutate(data)
    result = ab.verify(_write(tmp_path / name, data))
    assert result["status"] == status, result["reason"]
    assert result["status"] != "pass"
    assert ab.main(["--evidence", str(tmp_path / name)]) == code
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == status


def test_empty_directory_is_could_not_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    result = ab.verify(tmp_path)
    assert result["status"] == "unknown" and result["could_not_run"] == 1 and result["fail"] == 0
    assert ab.main(["--evidence", str(tmp_path)]) == 2
    assert json.loads(capsys.readouterr().out)["could_not_run"] == 1


def test_nonexistent_directory_and_malformed_json(tmp_path: Path) -> None:
    assert ab.verify(tmp_path / "absent")["status"] == "unknown"
    (tmp_path / "ab.json").write_text("{not json", encoding="utf-8")
    assert ab.verify(tmp_path)["status"] == "unknown"
    (tmp_path / "ab.json").write_text('{"id": "x", "id": "y"}', encoding="utf-8")
    assert ab.verify(tmp_path)["status"] == "unknown"


def test_close_check_command_exits_2_without_evidence(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    done = subprocess.run([sys.executable, "-m", "tools.verify_cpu_pin_ab", "--evidence", str(tmp_path)],
                          cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    assert done.returncode == 2 and json.loads(done.stdout)["could_not_run"] == 1
