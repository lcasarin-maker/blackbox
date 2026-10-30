"""Evaluate the A/B of pinning the inference host to the A725 cores.

Closes FEATURE-FORUM-CPU-PIN-ECORES-AB-01. The verifier never produces the
experiment; it judges a caller-supplied capture and answers only `pass`, `fail`
or `unknown`. Missing or incomplete evidence is `unknown` (exit 2), never `pass`.
A contradiction inside the evidence is `fail` (exit 1). Origin of the capture is
not authenticated.

Evidence: `<dir>/ab.json`, one strict JSON object (no duplicate keys, no NaN):

  id        "FEATURE-FORUM-CPU-PIN-ECORES-AB-01"
  plan      predeclared before the runs:
              a725_cpus "0-4,10-14"   x925_cpus "5-9,15-19"   all_cpus "0-19"
              min_arm_seconds  int >= 1800   (a 5 min run does not saturate the heat)
              min_repeats      int >= 2
              min_cooling_c    number > 0    (drop of the hottest zone that counts as cooling)
              max_repeat_spread_c number > 0 (allowed spread of one arm's repeats)
              min_gpu_util_pct number > 0    (the GPU must be under load)
  topology  {"<cpuset>": "<midr_el1>"} for a725_cpus and x925_cpus, read from the
            host; A725 = 0x410fd871, X925 = 0x410fd851.
  runs      list; each run:
              arm        "unpinned" | "pin_a725" | "pin_x925"   (pin_x925 = negative control)
              repeat     int >= 1, distinct inside the arm
              cpuset     "0-19" for unpinned, the plan cpuset for the pinned arms
              taskset_readback  `taskset -p` readback; must equal cpuset (pinned arms)
              duration_seconds  number >= plan.min_arm_seconds
              clock_cap_mhz     int; the same in every run
              workload   {model_sha256, image_digest, input_sha256, concurrency, max_new_tokens};
                         the same in every run
              zones_c    exactly 7 acpitz zones, {"acpitz0": {"peak_c": n, "mean_c": n}, ...},
                         same names in every run
              clock_mhz  {"mean": n, "min": n}  effective graphics clock
              decode_tok_s, prefill_tok_s, power_w_mean  numbers > 0
              gpu_util_mean_pct  number in [min_gpu_util_pct, 100]
              clocks_event_reasons  hex string, e.g. "0x0000000000000000"
  rollback  {"command": "taskset -a -p -c 0-19 <pid>", "exit": 0,
             "readback_exit": 0, "readback_cpuset": "0-19"}

Verdict rules: every arm needs >= plan.min_repeats runs; repeats of one arm must
agree within plan.max_repeat_spread_c on the hottest-zone peak; the control
(pin_x925) cooling the hottest zone by >= plan.min_cooling_c against unpinned is
`fail` (the instrument does not discriminate). A pin_a725 that does not cool is a
valid null result and passes with effect "null".
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from tools.capture_io import read_regular_bytes, strict_json_loads

ROOT = Path(__file__).resolve().parents[1]
FINDING = "FEATURE-FORUM-CPU-PIN-ECORES-AB-01"
CAPTURE_LIMIT = 4_000_000
ARMS = ("unpinned", "pin_a725", "pin_x925")
ZONE_COUNT = 7
MIDR = {"a725": "0x410fd871", "x925": "0x410fd851"}
WORKLOAD_KEYS = ("model_sha256", "image_digest", "input_sha256", "concurrency", "max_new_tokens")
RUN_NUMBERS = ("duration_seconds", "decode_tok_s", "prefill_tok_s", "power_w_mean", "gpu_util_mean_pct")
MIN_ARM_SECONDS_FLOOR = 1800
REASONS = re.compile(r"0x[0-9a-fA-F]{1,16}")
CPUSET = re.compile(r"\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*")


class _Unknown(Exception):
    """Evidence is absent or incomplete."""


class _Fail(Exception):
    """Evidence contradicts itself or the rules."""


def _result(status: str, reason: str, files: list[str], **extra: Any) -> dict[str, Any]:
    return {"status": status, "reason": reason, "files": files,
            "fail": int(status == "fail"), "could_not_run": int(status == "unknown"), **extra}


def _num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _pos(value: Any) -> bool:
    return _num(value) and value > 0


def _cpus(text: str) -> frozenset[int]:
    out: set[int] = set()
    for part in text.split(","):
        low, _, high = part.partition("-")
        out.update(range(int(low), int(high or low) + 1))
    return frozenset(out)


def _same_cpus(left: Any, right: Any) -> bool:
    return (isinstance(left, str) and isinstance(right, str)
            and CPUSET.fullmatch(left) is not None and CPUSET.fullmatch(right) is not None
            and _cpus(left) == _cpus(right))


def _load(path: Path) -> dict[str, Any]:
    try:
        raw = read_regular_bytes(path, CAPTURE_LIMIT)
        if len(raw) > CAPTURE_LIMIT:
            raise _Unknown(f"{path.name} exceeds {CAPTURE_LIMIT} bytes")
        value = strict_json_loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        raise _Unknown(f"ab.json missing or unreadable: {type(error).__name__}") from error
    if not isinstance(value, dict) or value.get("id") != FINDING:
        raise _Unknown("ab.json is not an object carrying this finding id")
    return value


def _plan(data: dict[str, Any]) -> dict[str, Any]:
    plan = data.get("plan")
    if not isinstance(plan, dict):
        raise _Unknown("predeclared plan absent")
    for key in ("a725_cpus", "x925_cpus", "all_cpus"):
        if not isinstance(plan.get(key), str) or CPUSET.fullmatch(plan[key]) is None:
            raise _Unknown(f"plan.{key} absent or malformed")
    a725, x925, whole = (_cpus(plan[key]) for key in ("a725_cpus", "x925_cpus", "all_cpus"))
    if a725 & x925 or not a725 or not x925 or not (a725 | x925) <= whole:
        raise _Fail("plan cpusets overlap or fall outside all_cpus")
    if not (_num(plan.get("min_arm_seconds")) and plan["min_arm_seconds"] >= MIN_ARM_SECONDS_FLOOR):
        raise _Unknown(f"plan.min_arm_seconds absent or below {MIN_ARM_SECONDS_FLOOR}")
    if type(plan.get("min_repeats")) is not int or plan["min_repeats"] < 2:
        raise _Unknown("plan.min_repeats absent or below 2")
    for key in ("min_cooling_c", "max_repeat_spread_c", "min_gpu_util_pct"):
        if not _pos(plan.get(key)):
            raise _Unknown(f"plan.{key} absent or not positive")
    return plan


def _topology(data: dict[str, Any], plan: dict[str, Any]) -> None:
    topology = data.get("topology")
    if not isinstance(topology, dict):
        raise _Unknown("topology (midr_el1 per cpuset) absent")
    for name, key in (("a725", "a725_cpus"), ("x925", "x925_cpus")):
        if plan[key] not in topology:
            raise _Unknown(f"topology lacks midr_el1 for {plan[key]}")
        if topology[plan[key]] != MIDR[name]:
            raise _Fail(f"cpus {plan[key]} are {topology[plan[key]]!r}, not {name} {MIDR[name]}")


def _zones(run: dict[str, Any], where: str) -> dict[str, float]:
    zones = run.get("zones_c")
    if not isinstance(zones, dict) or len(zones) != ZONE_COUNT:
        raise _Unknown(f"{where}: exactly {ZONE_COUNT} acpitz zones are required")
    for name, entry in zones.items():
        if not (isinstance(entry, dict) and _pos(entry.get("peak_c")) and _pos(entry.get("mean_c"))
                and entry["mean_c"] <= entry["peak_c"]):
            raise _Unknown(f"{where}: zone {name} lacks a valid peak_c/mean_c")
    return {name: float(entry["peak_c"]) for name, entry in zones.items()}


def _run(run: Any, plan: dict[str, Any], index: int) -> dict[str, Any]:
    where = f"runs[{index}]"
    if not isinstance(run, dict) or run.get("arm") not in ARMS:
        raise _Unknown(f"{where}: arm must be one of {ARMS}")
    where = f"runs[{index}] {run['arm']}"
    if type(run.get("repeat")) is not int or run["repeat"] < 1:
        raise _Unknown(f"{where}: repeat must be an integer >= 1")
    if any(not _pos(run.get(key)) for key in RUN_NUMBERS):
        raise _Unknown(f"{where}: duration, decode, prefill, power or gpu utilization missing")
    if run["duration_seconds"] < plan["min_arm_seconds"]:
        raise _Unknown(f"{where}: duration {run['duration_seconds']}s is below {plan['min_arm_seconds']}s")
    if run["gpu_util_mean_pct"] < plan["min_gpu_util_pct"] or run["gpu_util_mean_pct"] > 100:
        raise _Unknown(f"{where}: GPU was not under the declared load")
    clock = run.get("clock_mhz")
    if not (isinstance(clock, dict) and _pos(clock.get("mean")) and _pos(clock.get("min"))
            and clock["min"] <= clock["mean"]):
        raise _Unknown(f"{where}: effective clock_mhz mean/min missing")
    if type(run.get("clock_cap_mhz")) is not int or run["clock_cap_mhz"] <= 0:
        raise _Unknown(f"{where}: clock_cap_mhz missing")
    if not isinstance(run.get("clocks_event_reasons"), str) or not REASONS.fullmatch(run["clocks_event_reasons"]):
        raise _Unknown(f"{where}: clocks_event_reasons missing")
    workload = run.get("workload")
    if not isinstance(workload, dict) or any(key not in workload for key in WORKLOAD_KEYS):
        raise _Unknown(f"{where}: workload tuple incomplete")
    expected = {"unpinned": plan["all_cpus"], "pin_a725": plan["a725_cpus"], "pin_x925": plan["x925_cpus"]}[run["arm"]]
    if not _same_cpus(run.get("cpuset"), expected):
        raise _Fail(f"{where}: cpuset {run.get('cpuset')!r} is not the arm's {expected!r}")
    if run["arm"] != "unpinned" and not _same_cpus(run.get("taskset_readback"), expected):
        raise _Fail(f"{where}: taskset readback {run.get('taskset_readback')!r} differs from {expected!r}")
    return {"arm": run["arm"], "repeat": run["repeat"], "zones": _zones(run, where),
            "cap": run["clock_cap_mhz"], "workload": tuple(workload[key] for key in WORKLOAD_KEYS),
            "decode": float(run["decode_tok_s"]), "prefill": float(run["prefill_tok_s"]),
            "clock_mean": float(clock["mean"])}


def _rollback(data: dict[str, Any], plan: dict[str, Any]) -> None:
    rollback = data.get("rollback")
    if not isinstance(rollback, dict):
        raise _Unknown("rollback record absent")
    if not isinstance(rollback.get("command"), str) or "taskset" not in rollback["command"]:
        raise _Unknown("rollback command absent")
    if rollback.get("exit") != 0 or rollback.get("readback_exit") != 0 or type(rollback.get("exit")) is not int:
        raise _Unknown("rollback or its readback did not run successfully")
    if not _same_cpus(rollback.get("readback_cpuset"), plan["all_cpus"]):
        raise _Fail(f"rollback readback {rollback.get('readback_cpuset')!r} is not {plan['all_cpus']!r}")


def _arms(data: dict[str, Any], plan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        raise _Unknown("no runs")
    parsed = [_run(run, plan, index) for index, run in enumerate(runs)]
    by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    for item in parsed:
        by_arm[item["arm"]].append(item)
    for arm, items in by_arm.items():
        if not items:
            raise _Unknown(f"arm {arm} has no runs" + (" (negative control)" if arm == "pin_x925" else ""))
        if len({item["repeat"] for item in items}) != len(items):
            raise _Fail(f"arm {arm} repeats {[item['repeat'] for item in items]} are not distinct")
        if len(items) < plan["min_repeats"]:
            raise _Unknown(f"arm {arm} has {len(items)} run(s); {plan['min_repeats']} repeats required")
    first = parsed[0]
    if any(item["cap"] != first["cap"] for item in parsed):
        raise _Fail("clock cap differs between runs")
    if any(item["workload"] != first["workload"] for item in parsed):
        raise _Fail("workload tuple differs between runs")
    if any(set(item["zones"]) != set(first["zones"]) for item in parsed):
        raise _Fail("zone names differ between runs")
    return by_arm


def _hot(items: list[dict[str, Any]]) -> list[float]:
    return [max(item["zones"].values()) for item in items]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _judge(data: dict[str, Any], files: list[str]) -> dict[str, Any]:
    plan = _plan(data)
    _topology(data, plan)
    by_arm = _arms(data, plan)
    _rollback(data, plan)
    for arm, items in by_arm.items():
        peaks = _hot(items)
        if max(peaks) - min(peaks) > plan["max_repeat_spread_c"]:
            raise _Unknown(f"arm {arm} repeats disagree by {max(peaks) - min(peaks):.2f} C "
                           f"(> {plan['max_repeat_spread_c']}); the comparison is noise")
    base = _mean(_hot(by_arm["unpinned"]))
    drop = {arm: base - _mean(_hot(by_arm[arm])) for arm in ("pin_a725", "pin_x925")}
    if drop["pin_x925"] >= plan["min_cooling_c"]:
        raise _Fail(f"negative control cooled {drop['pin_x925']:.2f} C (>= {plan['min_cooling_c']}); "
                    "the instrument does not discriminate")
    effect = "cooling" if drop["pin_a725"] >= plan["min_cooling_c"] else "null"
    zones = sorted(by_arm["unpinned"][0]["zones"])
    per_zone = {zone: round(_mean([i["zones"][zone] for i in by_arm["unpinned"]])
                            - _mean([i["zones"][zone] for i in by_arm["pin_a725"]]), 3) for zone in zones}
    summary = {arm: {"hottest_peak_c": round(_mean(_hot(items)), 3),
                     "decode_tok_s": round(_mean([i["decode"] for i in items]), 3),
                     "prefill_tok_s": round(_mean([i["prefill"] for i in items]), 3),
                     "clock_mhz_mean": round(_mean([i["clock_mean"] for i in items]), 3)}
               for arm, items in by_arm.items()}
    return _result("pass", f"effect={effect}; pin_a725 hottest-zone drop {drop['pin_a725']:.2f} C, "
                   f"control drop {drop['pin_x925']:.2f} C; origin remains unauthenticated", files,
                   effect=effect, drop_c=drop, per_zone_drop_a725_c=per_zone, arms=summary)


def verify(evidence: str | Path | None = None) -> dict[str, Any]:
    """Return the verdict for the evidence directory (default: the finding's own)."""
    directory = Path(evidence) if evidence is not None else ROOT / "tasks/evidence" / FINDING
    path = directory / "ab.json"
    files = [str(path)]
    try:
        return _judge(_load(path), files)
    except _Unknown as error:
        return _result("unknown", str(error), files)
    except _Fail as error:
        return _result("fail", str(error), files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=None, help="directory containing ab.json")
    result = verify(parser.parse_args(argv).evidence)
    print(json.dumps(result, sort_keys=True))
    if result["status"] == "pass" and result["fail"] == 0 and result["could_not_run"] == 0:
        return 0
    if result["status"] == "fail" and result["fail"] > 0 and result["could_not_run"] == 0:
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
