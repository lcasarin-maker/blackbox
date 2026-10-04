from __future__ import annotations

import json
import io
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any, Mapping

from tools.workload_restart_policy import decide
from tools import workload_restart_policy


def test_restart_budget_persists_per_workload_and_expires(tmp_path: Path) -> None:
    state = tmp_path / "restart-budget.json"
    for attempt in range(3):
        result = decide(state, "owned-container-17", now=100 + attempt, limit=3, window_seconds=60)
        assert result["status"] == "allow" and result["data_touched"] is False
    fourth = decide(state, "owned-container-17", now=103, limit=3, window_seconds=60)
    assert fourth["status"] == "blocked" and fourth["allow"] is False
    assert decide(state, "healthy-service", now=103, limit=3, window_seconds=60)["status"] == "allow"
    assert decide(state, "owned-container-17", now=200, limit=3, window_seconds=60)["status"] == "allow"
    persisted = json.loads(state.read_text(encoding="utf-8"))
    assert "owned-container-17" in persisted["workloads"]


def test_restart_budget_refuses_malformed_state_and_identity(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.write_text("{broken", encoding="utf-8")
    assert decide(state, "owned", now=10)["status"] == "could_not_run"
    assert decide(state, "*", now=10)["status"] == "fail"


def test_clock_rollback_preserves_attempt_history(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    assert decide(state, "owned", now=100)["status"] == "allow"
    original = state.read_bytes()
    result = decide(state, "owned", now=90)
    assert result["status"] == "could_not_run"
    assert "clock moved behind" in result["reason"]
    assert state.read_bytes() == original
    invalid = decide(state, "owned", now=True)
    assert invalid["status"] == "fail" and invalid["fail"] == 1 and invalid["could_not_run"] == 0


def test_state_write_error_is_could_not_run_and_cleans_temporary_file(
        tmp_path: Path, monkeypatch) -> None:
    state = tmp_path / "state.json"
    def unavailable(_fd: int) -> None:
        raise OSError("sync failed")

    monkeypatch.setattr(workload_restart_policy.os, "fsync", unavailable)
    result = decide(state, "owned", now=10)
    assert result["status"] == "could_not_run"
    assert "sync failed" in result["reason"]
    assert result["could_not_run"] == 1 and result["unknowns"] == [result["reason"]]
    assert not state.exists()
    assert list(tmp_path.glob(".state.json.*")) == []


def test_restart_policy_cli_persists_and_blocks_only_named_workload(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    state = tmp_path / "budget.json"
    command = [sys.executable, "-m", "tools.workload_restart_policy", "--state", str(state),
               "--workload-id", "owned-model", "--limit", "2", "--window-seconds", "3600"]
    for _ in range(2):
        allowed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        assert allowed.returncode == 0 and json.loads(allowed.stdout)["state_persisted"] is True
    blocked = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    assert blocked.returncode == 1 and json.loads(blocked.stdout)["status"] == "blocked"
    healthy_command = command.copy()
    healthy_command[healthy_command.index("owned-model")] = "healthy-api"
    healthy = subprocess.run(healthy_command,
                             cwd=root, capture_output=True, text=True, check=False)
    assert healthy.returncode == 0 and json.loads(healthy.stdout)["attempts"] == 1


def test_restart_policy_cli_serializes_concurrent_budget_claims(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    state = tmp_path / "budget.json"
    command = [sys.executable, "-m", "tools.workload_restart_policy", "--state", str(state),
               "--workload-id", "one-owned-workload", "--limit", "3", "--window-seconds", "600"]
    processes = [subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True) for _ in range(10)]
    results = [process.communicate(timeout=10) + (process.returncode,) for process in processes]
    assert sum(code == 0 for _stdout, _stderr, code in results) == 3
    assert sum(code == 1 for _stdout, _stderr, code in results) == 7
    assert len(json.loads(state.read_text(encoding="utf-8"))["workloads"]["one-owned-workload"]) == 3


def test_restart_policy_main_emits_allowed_and_denied_verdicts(tmp_path: Path,
                                                               monkeypatch) -> None:
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    state = tmp_path / "state.json"
    args = ["--state", str(state), "--workload-id", "owned", "--limit", "1"]
    assert workload_restart_policy.main(args) == 0
    assert json.loads(output.getvalue())["allow"] is True
    output.seek(0)
    output.truncate(0)
    assert workload_restart_policy.main(args) == 1
    assert json.loads(output.getvalue())["status"] == "blocked"


def test_state_directory_creation_error_is_could_not_run(tmp_path: Path, monkeypatch) -> None:
    state = tmp_path / "unavailable" / "state.json"

    def fail_mkdir(*_args, **_kwargs):
        raise OSError("directory denied")

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)
    report = decide(state, "owned", now=10)
    assert report["status"] == "could_not_run"
    assert report["allow"] is False
    assert report["could_not_run"] == 1
    assert "directory denied" in report["reason"]


def test_state_lock_error_is_could_not_run(tmp_path: Path, monkeypatch) -> None:
    state = tmp_path / "state.json"

    def fail_flock(_fd: int, _operation: int) -> None:
        raise OSError("lock denied")

    monkeypatch.setattr(workload_restart_policy.fcntl, "flock", fail_flock)
    report = decide(state, "owned", now=10)
    assert report["status"] == "could_not_run"
    assert report["allow"] is False
    assert report["could_not_run"] == 1
    assert report["unknowns"] == [report["reason"]]
    assert "lock denied" in report["reason"]
    assert not state.exists()


def test_state_schema_and_per_workload_attempt_records_fail_closed(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"schema": 2, "workloads": {}}), encoding="utf-8")
    bad_schema = decide(state, "owned", now=10)
    assert bad_schema["status"] == "could_not_run"
    assert bad_schema["could_not_run"] == 1
    assert "invalid state schema" in bad_schema["reason"]

    state.write_text(json.dumps({"schema": 1, "workloads": {"owned": [True]}}),
                     encoding="utf-8")
    malformed_attempts = decide(state, "owned", now=10)
    assert malformed_attempts["status"] == "could_not_run"
    assert malformed_attempts["could_not_run"] == 1
    assert malformed_attempts["reason"] == "workload state malformed"
    assert json.loads(state.read_text(encoding="utf-8"))["workloads"]["owned"] == [True]


# This selector is deliberately evidence-gated. Policy unit tests above never stand in
# for a real reboot/recovery cycle. Capture provenance remains caller-supplied.
_MAX_CAPTURE_BYTES = 4 * 1024 * 1024
_MAX_DATA_FILE_BYTES = 8 * 1024 * 1024
_MAX_DATA_FILES = 256


def _unknown(reason: str) -> dict[str, object]:
    return {"status": "unknown", "could_not_run": 1, "fail": 0,
            "reason": reason, "checks": {}}


def _strict_json_bytes(raw: bytes, label: str) -> object:
    from tools.capture_io import strict_json_loads

    if len(raw) > _MAX_CAPTURE_BYTES:
        raise ValueError(f"{label} exceeds bounded capture size")
    return strict_json_loads(raw.decode("utf-8", errors="strict"))


def _load_capture(root: Path, references: object, name: str) -> dict[str, Any]:
    from tools.capture_io import read_regular_bytes
    import re

    if not isinstance(references, dict):
        raise ValueError("capture references are malformed")
    reference = references.get(name)
    if not isinstance(reference, dict):
        raise FileNotFoundError(f"capture reference missing: {name}")
    relative = reference.get("path")
    expected_hash = reference.get("sha256")
    if (not isinstance(relative, str) or not relative or Path(relative).is_absolute()
            or ".." in Path(relative).parts or not isinstance(expected_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None):
        raise ValueError(f"capture reference malformed: {name}")
    raw = read_regular_bytes(root / relative, _MAX_CAPTURE_BYTES)
    if len(raw) > _MAX_CAPTURE_BYTES:
        raise ValueError(f"capture exceeds bounded size: {name}")
    import hashlib
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError(f"capture digest mismatch: {name}")
    value = _strict_json_bytes(raw, name)
    if not isinstance(value, dict):
        raise ValueError(f"capture record must be an object: {name}")
    if (type(value.get("schema")) is not int or value.get("schema") != 1
            or type(value.get("returncode")) is not int
            or not isinstance(value.get("argv"), list)
            or not value["argv"] or any(not isinstance(item, str) for item in value["argv"])
            or not isinstance(value.get("stdout"), str)
            or not isinstance(value.get("stderr"), str)
            or not isinstance(value.get("boot_id"), str)
            or not isinstance(value.get("started_at"), str)
            or not isinstance(value.get("finished_at"), str)):
        raise ValueError(f"raw command receipt malformed: {name}")
    from datetime import datetime
    import uuid
    try:
        timestamp = datetime.fromisoformat(value["started_at"].replace("Z", "+00:00"))
        finished = datetime.fromisoformat(value["finished_at"].replace("Z", "+00:00"))
        uuid.UUID(value["boot_id"])
    except ValueError as exc:
        raise ValueError(f"capture timestamp or boot ID malformed: {name}") from exc
    if (timestamp.tzinfo is None or timestamp.utcoffset() is None
            or finished.tzinfo is None or finished.utcoffset() is None
            or finished < timestamp):
        raise ValueError(f"capture timestamp ordering or timezone invalid: {name}")
    return value


def _replay_decision_captures(initial_state: object,
                              decisions: list[tuple[str, dict[str, Any]]],
                              expected_state_path: str | None = None
                              ) -> tuple[bool, list[tuple[str, dict[str, Any], dict[str, Any]]], object]:
    """Replay raw CLI receipts through the production policy on a temporary copy."""
    from datetime import datetime
    import tempfile
    from tools.workload_restart_policy import decide

    if (not isinstance(initial_state, dict) or type(initial_state.get("schema")) is not int
            or initial_state.get("schema") != 1
            or not isinstance(initial_state.get("workloads"), dict)):
        raise ValueError("restart budget initial state malformed")
    with tempfile.TemporaryDirectory(prefix="restart-budget-replay-") as temporary:
        path = Path(temporary) / "state.json"
        path.write_text(json.dumps(initial_state), encoding="utf-8")
        observed: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        ordered = sorted(decisions, key=lambda item: datetime.fromisoformat(
            str(item[1]["started_at"]).replace("Z", "+00:00")))
        state_path_arguments: set[str] = set()
        for name, record in ordered:
            argv = record["argv"]
            state_arg, workload_id, actual, expected = _replay_one_decision(path, name, record, argv)
            state_path_arguments.add(state_arg)
            observed.append((workload_id, actual, record))
        if len(state_path_arguments) != 1:
            raise ValueError("restart policy switched persistent state paths")
        if expected_state_path is not None and state_path_arguments != {expected_state_path}:
            raise ValueError("restart policy did not use the captured persistent state path")
        final_state = json.loads(path.read_text(encoding="utf-8"))
        return True, observed, final_state


def _replay_one_decision(path: Path, name: str, record: dict[str, Any],
                         argv: object) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    from datetime import datetime
    import re
    from tools.capture_io import strict_json_loads

    if (not isinstance(argv, list) or len(argv) != 11 or not Path(argv[0]).is_absolute()
            or re.fullmatch(r"python(?:3(?:\.\d+)?)?", Path(argv[0]).name) is None
            or argv[1:3] != ["-m", "tools.workload_restart_policy"]
            or set(argv[3::2]) != {"--state", "--workload-id", "--limit", "--window-seconds"}
            or record["returncode"] not in {0, 1, 2}):
        raise ValueError(f"policy decision did not invoke the production CLI: {name}")

    def option(flag: str) -> str:
        if argv.count(flag) != 1:
            raise ValueError(f"policy decision must contain exactly one {flag}: {name}")
        index = argv.index(flag)
        if index + 1 >= len(argv):
            raise ValueError(f"policy decision has empty {flag}: {name}")
        return argv[index + 1]

    try:
        state_path = option("--state")
        workload_id = option("--workload-id")
        limit = int(option("--limit"))
        window = int(option("--window-seconds"))
        moment = int(datetime.fromisoformat(str(record["started_at"]).replace("Z", "+00:00")).timestamp())
        actual = strict_json_loads(str(record["stdout"]))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"policy decision input/output malformed: {name}") from exc
    if not isinstance(actual, dict):
        raise ValueError(f"policy decision output is not an object: {name}")
    expected = decide(path, workload_id, now=moment, limit=limit, window_seconds=window)
    code = {"allow": 0, "blocked": 1}.get(str(expected["status"]), 2)
    fields = ("status", "workload_id", "attempts", "limit", "window_seconds")
    if record["returncode"] != code or any(actual.get(key) != expected.get(key) for key in fields):
        raise ValueError(f"observed policy decision disagrees with replay: {name}")
    return state_path, workload_id, actual, expected


def _inspect_record(receipt: Mapping[str, object], label: str) -> dict[str, Any]:
    import re
    from tools.capture_io import strict_json_loads

    try:
        parsed = strict_json_loads(str(receipt["stdout"]))
    except (KeyError, json.JSONDecodeError) as exc:
        raise ValueError(f"docker inspect output malformed: {label}") from exc
    if not isinstance(parsed, list) or len(parsed) != 1 or not isinstance(parsed[0], dict):
        raise ValueError(f"docker inspect must return exactly one container: {label}")
    row = parsed[0]
    container_id = row.get("Id")
    config = row.get("Config")
    host = row.get("HostConfig")
    state = row.get("State")
    restart = host.get("RestartPolicy") if isinstance(host, dict) else None
    image = config.get("Image") if isinstance(config, dict) else None
    network = row.get("NetworkSettings")
    ports = network.get("Ports") if isinstance(network, dict) else None
    host_ports: set[int] = set()
    published_ports: dict[str, set[int]] = {}
    if isinstance(ports, dict):
        for container_port, bindings in ports.items():
            if not isinstance(bindings, list):
                continue
            for binding in bindings:
                if isinstance(binding, dict) and isinstance(binding.get("HostPort"), str):
                    if binding["HostPort"].isdigit():
                        host_port = int(binding["HostPort"])
                        host_ports.add(host_port)
                        published_ports.setdefault(container_port, set()).add(host_port)
    if (not isinstance(container_id, str) or re.fullmatch(r"[0-9a-f]{64}", container_id) is None
            or not isinstance(config, dict) or not isinstance(host, dict)
            or not isinstance(image, str) or re.search(r"@sha256:[0-9a-f]{64}$", image) is None
            or not isinstance(restart, dict) or not isinstance(restart.get("Name"), str)
            or type(restart.get("MaximumRetryCount")) is not int
            or restart["MaximumRetryCount"] < 0 or not isinstance(state, dict)
            or not isinstance(state.get("Status"), str)
            or type(state.get("Running")) is not bool
            or type(state.get("Pid")) is not int
            or (state["Running"] and state["Pid"] <= 0)
            or (not state["Running"] and state["Pid"] < 0)
            or type(state.get("RestartCount")) is not int or state["RestartCount"] < 0):
        raise ValueError(f"docker inspect identity or restart policy malformed: {label}")
    return {"id": container_id, "image": image,
            "restart_policy": restart, "state": state, "host_ports": host_ports,
            "published_ports": published_ports}


def _docker_inspect_command(receipt: Mapping[str, object], container_id: str, label: str) -> bool:
    argv = receipt.get("argv")
    return (receipt.get("returncode") == 0 and isinstance(argv, list) and len(argv) >= 3
            and Path(argv[0]).name == "docker" and argv[1] == "inspect"
            and container_id in argv[2:])


def _unit_directives(receipt: Mapping[str, object], unit: str, label: str) -> dict[str, list[str]]:
    argv = receipt.get("argv")
    if (receipt.get("returncode") != 0 or not isinstance(argv, list) or len(argv) != 3
            or Path(argv[0]).name != "systemctl" or argv[1:] != ["cat", unit]):
        raise ValueError(f"systemctl cat command does not own unit capture: {label}")
    sections: dict[str, list[str]] = {}
    section = ""
    for raw_line in str(receipt.get("stdout", "")).splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            sections.setdefault(section, [])
        elif section:
            sections[section].append(line)
    if "Service" not in sections:
        raise ValueError(f"captured unit has no [Service] section: {label}")
    return sections


def _unit_has_policy_start(directives: dict[str, list[str]], workload_id: str,
                           state_path: str) -> bool:
    exec_starts = [line.split("=", 1)[1] for line in directives.get("Service", [])
                   if line.startswith("ExecStart=")]
    if len(exec_starts) != 1:
        return False
    try:
        argv = shlex.split(exec_starts[0])
    except ValueError:
        return False
    return (len(argv) == 11 and Path(argv[0]).name == "python3"
            and argv[1:3] == ["-m", "tools.workload_restart_policy"]
            and argv[3::2] == ["--state", "--workload-id", "--limit", "--window-seconds"]
            and argv[4] == state_path and argv[6] == workload_id
            and argv[8].isdigit() and int(argv[8]) > 0
            and argv[10].isdigit() and int(argv[10]) > 0)


def _ssh_options(argv: list[str], label: str) -> tuple[dict[str, str], int]:
    options: dict[str, str] = {}
    index = 1
    while index < len(argv) and argv[index].startswith("-"):
        flag = argv[index]
        if flag in {"-o", "-p", "-i", "-F"}:
            if index + 1 >= len(argv):
                raise ValueError(f"SSH option lacks value: {label}")
            value = argv[index + 1]
            if flag == "-o":
                key, separator, setting = value.partition("=")
                if not separator or key in options:
                    raise ValueError(f"SSH option malformed or duplicated: {label}")
                options[key] = setting
            else:
                options[flag] = value
            index += 2
        elif flag in {"-V", "-G", "-v", "-q", "-T", "-N"}:
            raise ValueError(f"SSH invocation is a probe, not remote command: {label}")
        else:
            raise ValueError(f"SSH option unsupported for ownership proof: {label}")
    return options, index


def _ssh_command(receipt: Mapping[str, object], expected: list[str], label: str) -> tuple[str, list[str]]:
    argv = receipt.get("argv")
    if (receipt.get("returncode") != 0 or not isinstance(argv, list) or not argv
            or Path(argv[0]).name != "ssh"):
        raise ValueError(f"SSH command is not a successful ssh invocation: {label}")
    options, index = _ssh_options(argv, label)
    if index >= len(argv):
        raise ValueError(f"SSH target missing: {label}")
    target = argv[index]
    host = target.rsplit("@", 1)[-1].strip("[]").lower()
    if (host in {"localhost", "127.0.0.1", "::1"} or not host or "." not in host
            or options.get("StrictHostKeyChecking", "").lower() != "yes"
            or not options.get("UserKnownHostsFile")):
        raise ValueError(f"SSH target or host-key pin is not a remote management target: {label}")
    remote = argv[index + 1:]
    if remote != expected:
        raise ValueError(f"SSH remote command differs from expected command: {label}")
    return target, remote


def _curl_response(receipt: Mapping[str, object], host_ports: set[int], expected_model: str) -> bool:
    argv = receipt.get("argv")
    if (receipt.get("returncode") != 0 or not isinstance(argv, list) or not argv
            or Path(argv[0]).name != "curl"):
        return False
    if any(argv.count(flag) != 1 for flag in
           ("--fail-with-body", "--max-time", "--config", "--data-binary", "--write-out")):
        return False
    if argv[argv.index("--write-out") + 1] != "\\n%{http_code}":
        return False
    try:
        timeout = float(argv[argv.index("--max-time") + 1])
        config_path = Path(argv[argv.index("--config") + 1])
        url = next(item for item in reversed(argv) if item.startswith("http://") or item.startswith("https://"))
    except (ValueError, IndexError, StopIteration):
        return False
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    if (timeout <= 0 or timeout > 30 or not config_path.is_absolute()
            or parsed_url.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed_url.path != "/v1/chat/completions" or parsed_url.port not in host_ports):
        return False
    if argv.count("--data-binary") != 1:
        return False
    try:
        request_body = json.loads(argv[argv.index("--data-binary") + 1])
    except (ValueError, IndexError, json.JSONDecodeError):
        return False
    if (not isinstance(request_body, dict) or request_body.get("model") != expected_model
            or not isinstance(request_body.get("messages"), list) or not request_body["messages"]):
        return False
    try:
        body_text, status_text = str(receipt["stdout"]).rsplit("\n", 1)
        body = json.loads(body_text)
    except (KeyError, ValueError, json.JSONDecodeError):
        return False
    choices = body.get("choices") if isinstance(body, dict) else None
    return (status_text == "200" and isinstance(choices, list) and bool(choices)
            and body.get("model") == expected_model
            and isinstance(choices[0], dict) and isinstance(choices[0].get("message"), dict)
            and isinstance(choices[0]["message"].get("content"), str)
            and bool(choices[0]["message"]["content"].strip()))


def _telemetry_absent(receipt: Mapping[str, object], host_ports: set[int]) -> bool:
    argv = receipt.get("argv")
    if (not isinstance(argv, list) or not argv or Path(argv[0]).name != "curl"
            or receipt.get("returncode") == 0 or str(receipt.get("stdout", "")).strip()
            or argv.count("--max-time") != 1):
        return False
    try:
        timeout = float(argv[argv.index("--max-time") + 1])
        url = next(value for value in reversed(argv) if value.startswith(("http://", "https://")))
    except (ValueError, IndexError, StopIteration):
        return False
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return (0 < timeout <= 15 and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            and parsed.path == "/metrics" and parsed.port in host_ports)


def _tree_snapshot(folder: Path) -> dict[str, tuple[str, int]]:
    import hashlib
    import os
    import stat
    from tools.capture_io import read_regular_bytes

    if not folder.is_dir() or folder.is_symlink():
        raise FileNotFoundError(f"data snapshot unavailable: {folder.name}")
    entries: dict[str, tuple[str, int]] = {}
    for parent, directories, filenames in os.walk(folder, followlinks=False):
        if any((Path(parent) / directory).is_symlink() for directory in directories):
            raise ValueError("data snapshot contains symlink directory")
        for filename in filenames:
            path = Path(parent) / filename
            relative = path.relative_to(folder).as_posix()
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode):
                raise ValueError(f"data snapshot contains non-regular file: {relative}")
            if len(entries) >= _MAX_DATA_FILES:
                raise ValueError("data snapshot exceeds file-count limit")
            raw = read_regular_bytes(path, _MAX_DATA_FILE_BYTES)
            if len(raw) > _MAX_DATA_FILE_BYTES:
                raise ValueError(f"data snapshot file exceeds bounded size: {relative}")
            entries[relative] = (hashlib.sha256(raw).hexdigest(), stat.S_IMODE(mode))
    return entries


def _same_tree(root: Path, left_name: str, right_name: str) -> tuple[bool, str]:
    snapshots = [_tree_snapshot(root / name) for name in (left_name, right_name)]
    if not snapshots[0]:
        raise ValueError("data snapshot is empty")
    return (snapshots[0] == snapshots[1], "data file paths, bytes, or modes differ")


def _load_restart_bundle(root: Path) -> tuple[dict[str, object], dict[str, dict[str, Any]], list[str]]:
    from tools.capture_io import read_regular_bytes

    raw = read_regular_bytes(root / "manifest.json", _MAX_CAPTURE_BYTES)
    manifest = _strict_json_bytes(raw, "manifest.json")
    if (not isinstance(manifest, dict) or type(manifest.get("schema")) is not int
            or manifest.get("schema") != 1):
        raise ValueError("manifest schema missing or unsupported")
    names = ("inspect_before", "inspect_during", "inspect_after", "unit_before",
             "unit_during", "unit_after", "boot_before", "boot_after", "docker_events",
             "journal", "state_before", "state_after", "management_before", "management_after",
             "healthy_control", "unrelated_boot_before", "unrelated_boot_after",
             "unrelated_reboot_trigger", "telemetry_absent", "service_probe_after")
    captures = {name: _load_capture(root, manifest.get("captures"), name) for name in names}
    decisions = manifest.get("decision_captures")
    if not isinstance(decisions, list) or len(decisions) < 4:
        raise FileNotFoundError("real policy decision receipts are incomplete")
    for name in decisions:
        if not isinstance(name, str) or name in captures:
            raise ValueError("policy decision capture names malformed")
        captures[name] = _load_capture(root, manifest.get("captures"), name)
    return manifest, captures, decisions


def _identity_and_boot_checks(manifest: dict[str, object], captures: dict[str, dict[str, Any]],
                              checks: dict[str, bool]) -> dict[str, Any]:
    from datetime import datetime
    import uuid

    inspected = {name: _inspect_record(captures[name], name)
                 for name in ("inspect_before", "inspect_during", "inspect_after")}
    subject = inspected["inspect_before"]
    workload_id = str(subject["id"])
    state_path = manifest.get("state_path")
    if not isinstance(state_path, str) or not Path(state_path).is_absolute():
        raise FileNotFoundError("manifest lacks absolute persistent restart-state path")
    for name in ("inspect_before", "inspect_during", "inspect_after"):
        if not _docker_inspect_command(captures[name], workload_id, name):
            raise ValueError(f"raw docker inspect command does not name the captured workload: {name}")
    checks["same_immutable_container"] = all(
        inspected[name]["id"] == workload_id and inspected[name]["image"] == subject["image"]
        for name in ("inspect_during", "inspect_after"))
    checks["policy_rollback"] = inspected["inspect_before"]["restart_policy"] == inspected["inspect_after"]["restart_policy"]
    unit_name = manifest.get("unit_name")
    if not isinstance(unit_name, str) or not unit_name.endswith(".service"):
        raise FileNotFoundError("manifest lacks exact systemd unit identity")
    units = {name: _unit_directives(captures[name], unit_name, name)
             for name in ("unit_before", "unit_during", "unit_after")}
    checks["actual_start_gate"] = _unit_has_policy_start(units["unit_during"], workload_id, state_path)
    checks["unit_rollback"] = units["unit_before"] == units["unit_after"] != units["unit_during"]
    boots = {name: str(captures[name]["stdout"]).strip() for name in
             ("boot_before", "boot_after", "unrelated_boot_before", "unrelated_boot_after")}
    for name, boot_id in boots.items():
        receipt = captures[name]
        argv = receipt["argv"]
        if (receipt["returncode"] != 0 or len(argv) != 2 or Path(argv[0]).name != "cat"
                or argv[1] != "/proc/sys/kernel/random/boot_id"):
            raise ValueError(f"boot ID is not captured by native cat command: {name}")
        try:
            uuid.UUID(boot_id)
        except ValueError as exc:
            raise ValueError(f"boot ID malformed: {name}") from exc
    checks["boot_changed"] = (boots["boot_before"] != boots["boot_after"]
        and captures["boot_before"]["boot_id"] == boots["boot_before"]
        and captures["boot_after"]["boot_id"] == boots["boot_after"])
    checks["unrelated_reboot_observed"] = boots["unrelated_boot_before"] != boots["unrelated_boot_after"]
    trigger = captures["unrelated_reboot_trigger"]
    target, _ = _ssh_command(trigger, ["systemctl", "reboot"], "unrelated reboot")
    checks["unrelated_reboot_triggered"] = (
        trigger["boot_id"] == boots["unrelated_boot_before"]
        and captures["unrelated_boot_before"]["boot_id"] == boots["unrelated_boot_before"]
        and captures["unrelated_boot_after"]["boot_id"] == boots["unrelated_boot_after"])
    trigger_time = int(datetime.fromisoformat(str(trigger["started_at"]).replace("Z", "+00:00")).timestamp())
    window = tuple(int(datetime.fromisoformat(str(captures[name]["started_at"]).replace("Z", "+00:00")).timestamp())
                   for name in ("unrelated_boot_before", "unrelated_boot_after"))
    checks["trigger_between_boot_probes"] = window[0] <= trigger_time <= window[1]
    return {"inspected": inspected, "workload_id": workload_id, "state_path": state_path,
            "boots": boots, "trigger": trigger, "trigger_target": target,
            "trigger_time": trigger_time}


def _docker_event_checks(captures: dict[str, dict[str, Any]], context: dict[str, Any],
                         checks: dict[str, bool]) -> tuple[list[Any], list[dict[str, Any]], int]:
    from tools.capture_io import strict_json_loads
    from datetime import datetime

    workload_id = str(context["workload_id"])
    event_argv = captures["docker_events"]["argv"]
    if (not isinstance(event_argv, list) or len(event_argv) < 5
            or Path(event_argv[0]).name != "docker" or event_argv[1] != "events"
            or event_argv.count("--filter") != 1
            or event_argv[event_argv.index("--filter") + 1] != f"container={workload_id}"
            or event_argv.count("--format") != 1
            or event_argv[event_argv.index("--format") + 1] not in {"{{json .}}", "json"}):
        raise ValueError("docker event stream is not owned by docker events")
    parsed_events = [strict_json_loads(line) for line in str(captures["docker_events"]["stdout"]).splitlines() if line]
    if any(not isinstance(event, dict) for event in parsed_events):
        raise ValueError("docker event stream contains non-object")
    events = [event for event in parsed_events if isinstance(event, dict)]
    matching = [event for event in events if event.get("Type") == "container"
                and isinstance(event.get("Actor"), dict) and event["Actor"].get("ID") == workload_id]
    actions = [event.get("Action", event.get("status")) for event in matching]
    for event in matching:
        if type(event.get("time")) is not int or event["time"] < 0:
            raise ValueError("docker event has invalid time")
    if event_argv.count("--since") != 1 or event_argv.count("--until") != 1:
        raise ValueError("docker event command lacks an explicit bounded time window")
    try:
        lower = int(event_argv[event_argv.index("--since") + 1])
        upper = int(event_argv[event_argv.index("--until") + 1])
    except (ValueError, IndexError) as exc:
        raise ValueError("docker event window must use captured epoch seconds") from exc
    capture_start = int(datetime.fromisoformat(
        str(captures["docker_events"]["started_at"]).replace("Z", "+00:00")).timestamp())
    capture_end = int(datetime.fromisoformat(
        str(captures["docker_events"]["finished_at"]).replace("Z", "+00:00")).timestamp())
    if lower >= upper or lower > capture_start or upper < capture_end:
        raise ValueError("docker event time window does not cover command capture interval")
    if any(not lower <= event["time"] <= upper for event in matching):
        raise ValueError("docker event falls outside its declared capture window")
    starts = sum(action in {"start", "restart"} for action in actions)
    checks["bounded_subject_events"] = starts > 0 and all(
        event.get("Actor", {}).get("ID") == workload_id for event in matching)
    context["starts"] = starts
    return actions, matching, starts


def _event_and_journal_checks(captures: dict[str, dict[str, Any]], context: dict[str, Any],
                              checks: dict[str, bool], observations: dict[str, object]
                              ) -> tuple[list[Any], list[dict[str, Any]], int]:
    actions, matching, starts = _docker_event_checks(captures, context, checks)
    _journal_observations(captures, context, observations)
    return actions, matching, starts


def _journal_observations(captures: dict[str, dict[str, Any]], context: dict[str, Any],
                          observations: dict[str, object]) -> None:
    from tools.capture_io import strict_json_loads

    workload_id = str(context["workload_id"])
    parsed_journal = [strict_json_loads(line) for line in str(captures["journal"]["stdout"]).splitlines() if line]
    if any(not isinstance(row, dict) for row in parsed_journal):
        raise ValueError("journal stream contains non-object")
    journal = [row for row in parsed_journal if isinstance(row, dict)]
    boots = context["boots"]
    if any(type(row.get("__REALTIME_TIMESTAMP")) is not str
           or not row["__REALTIME_TIMESTAMP"].isdigit() for row in journal):
        raise ValueError("journal record lacks native realtime timestamp")
    boots = context["boots"]
    _validate_journal_scope(journal, captures, boots)
    workload_oom = [row for row in journal if "oom" in str(row.get("MESSAGE", "")).lower()
        and any(workload_id[:12] in str(row.get(key, ""))
                for key in ("_SYSTEMD_CGROUP", "CONTAINER_ID", "CONTAINER_ID_FULL"))]
    observations["workload_oom_correlated"] = bool(workload_oom)
    unrelated = [row for row in journal if row.get("_BOOT_ID") == boots["unrelated_boot_after"]
                 and "oom" not in str(row.get("MESSAGE", "")).lower()]
    if not unrelated:
        raise FileNotFoundError("journal lacks sample correlated to unrelated reboot boot")


def _validate_journal_scope(journal: list[dict[str, Any]], captures: dict[str, dict[str, Any]],
                            boots: dict[str, str]) -> None:
    from datetime import datetime

    boot_ids = {row.get("_BOOT_ID") for row in journal if isinstance(row.get("_BOOT_ID"), str)}
    if not set(boots.values()).issubset(boot_ids):
        raise FileNotFoundError("journal lacks rows for all captured boot IDs")
    journal_argv = captures["journal"]["argv"]
    boot_range = next((item.partition("=")[2] for item in journal_argv
                       if item.startswith("--boot=")), "")
    if (not journal_argv or Path(journal_argv[0]).name != "journalctl"
            or journal_argv.count("--output=json") != 1 or not boot_range.startswith("-")):
        raise ValueError("journal records are not owned by bounded journalctl JSON query")
    range_parts = boot_range.removeprefix("-").split("..", maxsplit=1)
    if (len(range_parts) != 2 or not range_parts[0].isdigit()
            or int(range_parts[0]) < len(set(boots.values())) - 1 or range_parts[1] != "0"):
        raise ValueError("journal boot range does not cover the observed reboot sequence")
    row_times: dict[str, list[int]] = {}
    for row in journal:
        boot = row.get("_BOOT_ID")
        if isinstance(boot, str):
            row_times.setdefault(boot, []).append(int(row["__REALTIME_TIMESTAMP"]))
    start_id = boots["boot_before"]
    next_id = boots["boot_after"]
    unrelated_id = boots["unrelated_boot_after"]
    def boot_boundary(name: str) -> int:
        return int(datetime.fromisoformat(
            str(captures[name]["started_at"]).replace("Z", "+00:00")).timestamp() * 1_000_000)
    if (max(row_times[start_id]) >= boot_boundary("boot_after")
            or min(row_times[next_id]) < boot_boundary("boot_after")
            or max(row_times[next_id]) >= boot_boundary("unrelated_boot_after")
            or min(row_times[unrelated_id]) < boot_boundary("unrelated_boot_after")):
        raise ValueError("journal realtime records contradict captured boot chronology")


def _budget_checks(root: Path, manifest: dict[str, object], captures: dict[str, dict[str, Any]],
                   context: dict[str, Any], checks: dict[str, bool]
                   ) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    from tools.capture_io import strict_json_loads

    workload_id = str(context["workload_id"])
    state_path = str(context["state_path"])
    before = strict_json_loads(str(captures["state_before"]["stdout"]))
    after = strict_json_loads(str(captures["state_after"]["stdout"]))
    for name in ("state_before", "state_after"):
        receipt = captures[name]
        argv = receipt["argv"]
        if (receipt["returncode"] != 0 or len(argv) != 2
                or Path(argv[0]).name != "cat" or argv[1] != state_path):
            raise ValueError(f"restart state capture is not cat of declared state path: {name}")
    if (not isinstance(before, dict) or not isinstance(after, dict)
            or type(before.get("schema")) is not int or before.get("schema") != 1
            or type(after.get("schema")) is not int or after.get("schema") != 1
            or not isinstance(before.get("workloads"), dict)
            or not isinstance(after.get("workloads"), dict)):
        raise ValueError("restart budget state schema malformed")
    before_attempts = before["workloads"].get(workload_id, [])
    after_attempts = after["workloads"].get(workload_id, [])
    if (not isinstance(before_attempts, list) or not isinstance(after_attempts, list)
            or any(type(value) is not int or value < 0 for value in before_attempts + after_attempts)):
        raise ValueError("restart budget attempt history malformed")
    checks["budget_persisted_across_boot"] = len(after_attempts) >= len(before_attempts) and bool(after_attempts)
    decisions = manifest.get("decision_captures")
    if not isinstance(decisions, list) or any(not isinstance(name, str) for name in decisions):
        raise ValueError("decision capture names malformed")
    rows = [(name, captures[name]) for name in decisions]
    _, evaluated, final_state = _replay_decision_captures(
        before, rows, expected_state_path=state_path)
    checks["policy_state_matches_replay"] = (after == final_state
        and captures["state_before"]["boot_id"] == context["boots"]["boot_before"]
        and captures["state_after"]["boot_id"] == context["boots"]["boot_after"])
    own = [entry for entry in evaluated if entry[0] == workload_id]
    healthy = [entry for entry in evaluated if entry[0] != workload_id]
    allowed = [entry for entry in own if entry[1].get("status") == "allow" and entry[2]["returncode"] == 0]
    blocked = [entry for entry in own if entry[1].get("status") == "blocked" and entry[2]["returncode"] == 1]
    limits: list[int] = []
    for entry in own:
        limit_value = entry[1].get("limit")
        if type(limit_value) is not int or limit_value < 1:
            raise ValueError("policy replay limit is absent or malformed")
        limits.append(limit_value)
    if not limits:
        raise ValueError("policy replay limit is absent or malformed")
    checks["restart_budget_blocks"] = (len(set(limits)) == 1 and len(allowed) >= limits[0]
        and bool(blocked) and allowed[0][2]["boot_id"] == context["boots"]["boot_before"]
        and any(entry[2]["boot_id"] == context["boots"]["boot_after"] for entry in blocked)
        and int(context["starts"]) <= limits[0])
    healthy_subject = _inspect_record(captures["healthy_control"], "healthy_control")
    healthy_id = str(healthy_subject["id"])
    if not _docker_inspect_command(captures["healthy_control"], healthy_id, "healthy_control"):
        raise ValueError("healthy control is not an owned docker inspect capture")
    healthy_rows = [entry for entry in healthy if entry[0] == healthy_id]
    checks["healthy_control_allowed"] = (healthy_id != workload_id and bool(healthy_rows)
        and any(entry[1].get("status") == "allow" and entry[2]["returncode"] == 0 for entry in healthy_rows))
    checks["healthy_control_running"] = healthy_subject["state"].get("Status") == "running"
    return evaluated


def _access_and_service_checks(manifest: dict[str, object], captures: dict[str, dict[str, Any]],
                               context: dict[str, Any], checks: dict[str, bool]) -> None:
    inspected = context["inspected"]
    management_targets = []
    for name in ("management_before", "management_after"):
        target, _ = _ssh_command(captures[name], ["bash", "-lc",
            "test -f /run/blackbox-management-ready && printf BB_MANAGEMENT_READY"], name)
        management_targets.append(target)
        checks[name] = str(captures[name]["stdout"]).strip() == "BB_MANAGEMENT_READY"
    checks["management_probes_match"] = (management_targets[0] == management_targets[1]
        == context["trigger_target"])
    checks["telemetry_absence_control"] = _telemetry_absent(
        captures["telemetry_absent"], inspected["inspect_after"]["host_ports"])
    model = manifest.get("model_id")
    port = manifest.get("api_container_port")
    if not isinstance(model, str) or not model or type(port) is not int or not 1 <= port <= 65535:
        raise FileNotFoundError("manifest lacks model identity or measured application container port")
    host_ports = inspected["inspect_after"]["published_ports"].get(f"{port}/tcp", set())
    checks["service_recovered"] = _curl_response(captures["service_probe_after"], host_ports, model)


def _evaluate_restart_recovery_bundle(root: Path) -> dict[str, object]:
    """Evaluate raw cycle captures; provenance remains caller supplied."""
    try:
        manifest, captures, _ = _load_restart_bundle(root)
    except FileNotFoundError as exc:
        return _unknown(str(exc))
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
        return {"status": "fail", "could_not_run": 0, "fail": 1,
                "reason": f"invalid evidence bundle: {type(exc).__name__}: {exc}", "checks": {}}

    checks: dict[str, bool] = {}
    observations: dict[str, object] = {}
    try:
        context = _identity_and_boot_checks(manifest, captures, checks)
        context["inspected"] = {name: _inspect_record(captures[name], name)
                                for name in ("inspect_before", "inspect_during", "inspect_after")}
        actions, matching, starts = _event_and_journal_checks(captures, context, checks, observations)
        context["starts"] = starts
        _budget_checks(root, manifest, captures, context, checks)
        _access_and_service_checks(manifest, captures, context, checks)
        trigger_time = int(context["trigger_time"])
        checks["no_subject_autostart_after_unrelated_reboot"] = not any(
            action in {"start", "restart"} and event["time"] >= trigger_time
            for action, event in zip(actions, matching, strict=True))
        decisions = manifest.get("decision_captures", [])
        if not isinstance(decisions, list) or any(not isinstance(name, str) for name in decisions):
            raise ValueError("decision capture names malformed")
        checks["all_required_commands_succeeded"] = all(
            capture["returncode"] == 0 for name, capture in captures.items()
            if name not in {"telemetry_absent", *decisions})
        checks["data_preserved"] = _same_tree(root, "data-before", "data-after")[0]
    except FileNotFoundError as exc:
        return _unknown(str(exc))
    except (KeyError, OSError, UnicodeError, ValueError, TypeError,
            json.JSONDecodeError, RecursionError) as exc:
        return {"status": "fail", "could_not_run": 0, "fail": 1,
                "reason": f"evidence contradicts or malforms required predicate: {type(exc).__name__}: {exc}",
                "checks": checks}
    if checks and all(checks.values()):
        return {"status": "pass", "could_not_run": 0, "fail": 0,
                "reason": "all captured predicates match", "checks": checks,
                "observations": observations,
                "provenance": "caller-supplied receipts; source authenticity unverified"}
    return {"status": "fail", "could_not_run": 0, "fail": 1,
            "reason": "one or more required predicates were measured false",
            "checks": checks, "observations": observations,
            "provenance": "caller-supplied receipts; source authenticity unverified"}


def _store_cycle_capture(root: Path, refs: dict[str, object], name: str, *details: object,
                         returncode: int = 0, stderr: str = "") -> None:
    from datetime import datetime, timezone
    import hashlib

    if (len(details) != 4 or not isinstance(details[0], list)
            or any(not isinstance(item, str) for item in details[0])
            or not isinstance(details[1], str) or not isinstance(details[2], str)
            or type(details[3]) is not int):
        raise ValueError("cycle capture builder arguments malformed")
    argv, stdout, boot_id, timestamp = details
    if (not isinstance(argv, list) or any(not isinstance(item, str) for item in argv)
            or not isinstance(stdout, str) or not isinstance(boot_id, str)
            or type(timestamp) is not int):
        raise ValueError("cycle capture builder arguments malformed")
    def instant(value: int) -> str:
        return datetime.fromtimestamp(value, timezone.utc).isoformat()

    record = {"schema": 1, "argv": argv, "returncode": returncode, "stdout": stdout,
              "stderr": stderr, "boot_id": boot_id, "started_at": instant(timestamp),
              "finished_at": instant(timestamp + 1)}
    raw = json.dumps(record, separators=(",", ":")).encode()
    relative = f"captures/{name}.json"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    refs[name] = {"path": relative, "sha256": hashlib.sha256(raw).hexdigest()}


def _docker_inspect_stdout(container_id: str, running: bool, pid: int,
                           host_port: int | None = None) -> str:
    ports = {"8000/tcp": ([{"HostIp": "127.0.0.1", "HostPort": str(host_port)}]
                           if host_port is not None else None)}
    row = {"Id": container_id, "Config": {"Image": "example/model@sha256:" + "c" * 64},
           "HostConfig": {"RestartPolicy": {"Name": "no", "MaximumRetryCount": 0}},
           "NetworkSettings": {"Ports": ports},
           "State": {"Status": "running" if running else "exited", "Running": running,
                     "Pid": pid, "RestartCount": 0}}
    return json.dumps([row])


def _ssh_receipt(command: list[str]) -> list[str]:
    return ["/usr/bin/ssh", "-o", "StrictHostKeyChecking=yes", "-o",
            "UserKnownHostsFile=/etc/ssh/known_hosts", "operator@recovery.example", *command]


def _build_synthetic_restart_cycle(root: Path, state_path: Path) -> None:
    import uuid

    root.mkdir(parents=True, exist_ok=True)
    boot0, boot1, boot2 = (str(uuid.UUID(int=value)) for value in (1, 2, 3))
    start = 1_700_000_000
    workload = "a" * 64
    healthy = "b" * 64
    before_state = {"schema": 1, "workloads": {}}
    state_path.write_text(json.dumps(before_state), encoding="utf-8")
    refs: dict[str, object] = {}
    manifest: dict[str, object] = {"schema": 1, "captures": refs,
        "unit_name": "bb-workload.service", "state_path": str(state_path),
        "model_id": "model-v1", "api_container_port": 8000,
        "decision_captures": ["decision_allow_1", "decision_allow_2",
                               "decision_healthy", "decision_blocked"]}
    for name, running, pid, port, boot, second in (
        ("inspect_before", True, 101, 8080, boot0, 105),
        ("inspect_during", False, 0, 8080, boot0, 180),
        ("inspect_after", True, 202, 8080, boot1, 250),
        ("healthy_control", True, 303, 8181, boot1, 260)):
        target = healthy if name == "healthy_control" else workload
        _store_cycle_capture(root, refs, name, ["/usr/bin/docker", "inspect", target],
            _docker_inspect_stdout(target, running, pid, port), boot, start + second)
    base_unit = "[Unit]\\nDescription=owned workload\\n[Service]\\nExecStart=/usr/bin/docker start " + workload
    managed_unit = ("[Unit]\\nDescription=owned workload\\n[Service]\\nExecStart=/usr/bin/python3 -m "
                    "tools.workload_restart_policy --state " + str(state_path) + " --workload-id "
                    + workload + " --limit 2 --window-seconds 3600")
    for name, text, stamp, boot in (("unit_before", base_unit, 100, boot0),
                                     ("unit_during", managed_unit, 110, boot0),
                                     ("unit_after", base_unit, 240, boot1)):
        _store_cycle_capture(root, refs, name, ["/usr/bin/systemctl", "cat", "bb-workload.service"],
                             text.replace("\\n", "\n"), boot, start + stamp)
    for name, boot, stamp in (("boot_before", boot0, 100), ("boot_after", boot1, 200),
                              ("unrelated_boot_before", boot1, 300),
                              ("unrelated_boot_after", boot2, 400)):
        _store_cycle_capture(root, refs, name, ["/usr/bin/cat", "/proc/sys/kernel/random/boot_id"],
                             boot + "\n", boot, start + stamp)
    _store_cycle_capture(root, refs, "unrelated_reboot_trigger",
        _ssh_receipt(["systemctl", "reboot"]), "", boot1, start + 301)
    event_rows = []
    for stamp in (start + 111, start + 112):
        event_rows.append({"Type": "container", "Action": "start", "time": stamp,
                           "Actor": {"ID": workload}})
    _store_cycle_capture(root, refs, "docker_events",
        ["/usr/bin/docker", "events", "--since", str(start + 100), "--until", str(start + 500),
         "--filter", f"container={workload}",
         "--format", "{{json .}}"], "\n".join(json.dumps(row) for row in event_rows), boot0, start + 105)
    journal = []
    for boot, stamp, message in ((boot0, start + 110, "initial kernel ready"),
                                 (boot1, start + 201, "main reboot complete"),
                                 (boot1, start + 300, "before unrelated reboot"),
                                 (boot2, start + 401, "unrelated boot ready")):
        journal.append({"_BOOT_ID": boot, "__REALTIME_TIMESTAMP": str(stamp * 1_000_000),
                        "MESSAGE": message})
    _store_cycle_capture(root, refs, "journal", ["/usr/bin/journalctl", "--boot=-2..0", "--output=json"],
                         "\n".join(json.dumps(row) for row in journal), boot2, start + 402)
    _store_cycle_capture(root, refs, "state_before", ["/usr/bin/cat", str(state_path)],
                         json.dumps(before_state), boot0, start + 102)
    decision_specs = (("decision_allow_1", workload, start + 110, boot0),
                      ("decision_allow_2", workload, start + 111, boot0),
                      ("decision_healthy", healthy, start + 112, boot0),
                      ("decision_blocked", workload, start + 210, boot1))
    for name, identity, timestamp, boot in decision_specs:
        _key, record = _policy_receipt(identity, timestamp, boot, state_path, limit=2)
        record["finished_at"] = record["started_at"]
        record["started_at"] = __import__("datetime").datetime.fromtimestamp(
            timestamp, __import__("datetime").timezone.utc).isoformat()
        _store_cycle_capture(root, refs, name, record["argv"], record["stdout"], boot, timestamp,
                             returncode=record["returncode"], stderr=str(record["stderr"]))
    _store_cycle_capture(root, refs, "state_after", ["/usr/bin/cat", str(state_path)],
                         state_path.read_text(encoding="utf-8"), boot1, start + 220)
    ready_argv = _ssh_receipt(["bash", "-lc",
        "test -f /run/blackbox-management-ready && printf BB_MANAGEMENT_READY"])
    _store_cycle_capture(root, refs, "management_before", ready_argv,
                         "BB_MANAGEMENT_READY\n", boot1, start + 270)
    _store_cycle_capture(root, refs, "management_after", ready_argv,
                         "BB_MANAGEMENT_READY\n", boot2, start + 410)
    _store_cycle_capture(root, refs, "telemetry_absent",
        ["/usr/bin/curl", "--max-time", "5", "http://127.0.0.1:8080/metrics"],
        "", boot1, start + 280, returncode=7, stderr="connection refused")
    app_argv = ["/usr/bin/curl", "--fail-with-body", "--max-time", "15", "--config",
        "/run/secrets/inference.curl", "--data-binary",
        '{"model":"model-v1","messages":[{"role":"user","content":"ping"}]}',
        "--write-out", "\\n%{http_code}", "http://127.0.0.1:8080/v1/chat/completions"]
    _store_cycle_capture(root, refs, "service_probe_after", app_argv,
        '{"model":"model-v1","choices":[{"message":{"content":"pong"}}]}\n200', boot1, start + 275)
    (root / "data-before").mkdir(parents=True)
    (root / "data-after").mkdir(parents=True)
    (root / "data-before" / "sentinel.bin").write_bytes(b"preserved operator data")
    (root / "data-after" / "sentinel.bin").write_bytes(b"preserved operator data")
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_complete_synthetic_restart_cycle_passes_then_mutated_probe_fails(tmp_path: Path) -> None:
    import hashlib

    root = tmp_path / "cycle"
    state_path = tmp_path / "external-state.json"
    _build_synthetic_restart_cycle(root, state_path)
    baseline = _evaluate_restart_recovery_bundle(root)
    assert baseline["status"] == "pass", baseline
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert isinstance(manifest, dict) and isinstance(manifest.get("captures"), dict)
    reference = manifest["captures"]["service_probe_after"]
    assert isinstance(reference, dict) and isinstance(reference.get("path"), str)
    probe_path = root / reference["path"]
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    probe["argv"][-1] = "http://127.0.0.1:8080/v1/models"
    mutated = json.dumps(probe, separators=(",", ":")).encode()
    probe_path.write_bytes(mutated)
    reference["sha256"] = hashlib.sha256(mutated).hexdigest()
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    rejected = _evaluate_restart_recovery_bundle(root)
    assert rejected["status"] == "fail", rejected
    checks = rejected.get("checks")
    assert isinstance(checks, dict) and checks.get("service_recovered") is False


def test_restart_recovery_close_check_uses_real_cycle_evidence() -> None:
    """Original close_check gate: missing physical recovery evidence stays UNKNOWN/CNR."""
    import pytest

    root = Path(__file__).resolve().parents[1] / "tasks/evidence/FORUM-00-DOCKER-OOM-RESTART-LOOP/restart-cycle"
    result = _evaluate_restart_recovery_bundle(root)
    if result["status"] != "pass":
        pytest.fail(f"{str(result['status']).upper()}/CNR: {result['reason']}; checks={result['checks']}")


def test_restart_reader_recomputes_container_identity_and_restart_policy() -> None:
    record = {"stdout": json.dumps([{"Id": "a" * 64,
              "Config": {"Image": "example/model@sha256:" + "b" * 64},
              "HostConfig": {"RestartPolicy": {"Name": "no", "MaximumRetryCount": 0}},
              "State": {"Status": "running", "Running": True, "Pid": 43, "RestartCount": 0}}])}
    parsed = _inspect_record(record, "unit fixture")
    assert parsed["id"] == "a" * 64
    assert parsed["image"].endswith("b" * 64)
    assert parsed["restart_policy"] == {"Name": "no", "MaximumRetryCount": 0}


def test_restart_reader_rejects_unpinned_image_or_wrong_identity() -> None:
    import pytest

    record = {"stdout": json.dumps([{"Id": "a" * 64,
              "Config": {"Image": "example/model:latest"},
              "HostConfig": {"RestartPolicy": {"Name": "always", "MaximumRetryCount": 0}},
              "State": {"Status": "running", "Running": True, "Pid": 43, "RestartCount": 0}}])}
    with pytest.raises(ValueError, match="identity or restart policy"):
        _inspect_record(record, "tampered fixture")


def test_restart_data_reader_hashes_actual_bytes_and_modes(tmp_path: Path) -> None:
    before = tmp_path / "data-before"; after = tmp_path / "data-after"
    before.mkdir(); after.mkdir()
    (before / "sentinel.bin").write_bytes(b"operator data")
    (after / "sentinel.bin").write_bytes(b"operator data")
    assert _same_tree(tmp_path, "data-before", "data-after")[0]
    (after / "sentinel.bin").write_bytes(b"changed")
    assert not _same_tree(tmp_path, "data-before", "data-after")[0]


def _policy_receipt(workload_id: str, timestamp: int, boot_id: str,
                    state: Path, limit: int = 2) -> tuple[str, dict[str, Any]]:
    import datetime
    argv = [sys.executable, "-m", "tools.workload_restart_policy", "--state", str(state),
            "--workload-id", workload_id, "--limit", str(limit), "--window-seconds", "3600"]
    outcome = workload_restart_policy.decide(state, workload_id, now=timestamp,
                                             limit=limit, window_seconds=3600)
    return (f"decision_{timestamp}", {"schema": 1, "argv": argv,
            "returncode": {"allow": 0, "blocked": 1}[outcome["status"]],
            "stdout": json.dumps(outcome), "stderr": "", "boot_id": boot_id,
            "started_at": datetime.datetime.fromtimestamp(
                timestamp, datetime.timezone.utc).isoformat()})


def test_restart_decision_replay_matches_real_policy_across_boot_ids(tmp_path: Path) -> None:
    before = {"schema": 1, "workloads": {}}
    state = tmp_path / "subject-state.json"
    state.write_text(json.dumps(before), encoding="utf-8")
    workload_id = "a" * 64
    first = _policy_receipt(workload_id, 1000, "00000000-0000-0000-0000-000000000001", state)
    second = _policy_receipt(workload_id, 1001, "00000000-0000-0000-0000-000000000001", state)
    blocked = _policy_receipt(workload_id, 1002, "00000000-0000-0000-0000-000000000002", state)
    ok, rows, final_state = _replay_decision_captures(before, [blocked, second, first])
    assert ok and len(rows) == 3
    assert rows[-1][1]["status"] == "blocked"
    assert final_state == json.loads(state.read_text(encoding="utf-8"))


def test_restart_decision_replay_rejects_forged_block_status(tmp_path: Path) -> None:
    import pytest

    before = {"schema": 1, "workloads": {}}
    state = tmp_path / "subject-state.json"
    state.write_text(json.dumps(before), encoding="utf-8")
    receipt = _policy_receipt("a" * 64, 1000,
        "00000000-0000-0000-0000-000000000001", state)
    forged = dict(receipt[1])
    forged["stdout"] = json.dumps({"status": "blocked", "workload_id": "a" * 64,
        "attempts": 1, "limit": 2, "window_seconds": 60})
    with pytest.raises(ValueError, match="disagrees with replay"):
        _replay_decision_captures(before, [(receipt[0], forged)])


def test_restart_decision_replay_rejects_echo_that_mimics_policy(tmp_path: Path) -> None:
    import pytest

    before = {"schema": 1, "workloads": {}}
    state = tmp_path / "state.json"
    state.write_text(json.dumps(before), encoding="utf-8")
    name, record = _policy_receipt("a" * 64, 1000,
        "00000000-0000-0000-0000-000000000001", state)
    forged = dict(record)
    forged["argv"] = ["/bin/echo", *record["argv"][1:]]
    with pytest.raises(ValueError, match="production CLI"):
        _replay_decision_captures(before, [(name, forged)])


def test_restart_docker_and_unit_readers_bind_executable_target_and_directives() -> None:
    import pytest

    container_id = "a" * 64
    assert _docker_inspect_command({"argv": ["/usr/bin/docker", "inspect", container_id],
                                    "returncode": 0}, container_id, "good")
    assert not _docker_inspect_command({"argv": ["/tmp/notdocker", "images", "--filter",
                                                   "label=inspect", container_id],
                                        "returncode": 0}, container_id, "forged")
    captured = {"argv": ["/usr/bin/systemctl", "cat", "workload.service"],
                "returncode": 0,
                "stdout": "# ExecStart=comment only\n[Unit]\nDescription=x\n[Service]\nExecStart=/usr/bin/python3 -m tools.workload_restart_policy --workload-id " + container_id}
    parsed = _unit_directives(captured, "workload.service", "valid")
    assert any(container_id in value for value in parsed["Service"])
    good_start = {"Service": ["ExecStart=/usr/bin/python3 -m tools.workload_restart_policy --state /var/lib/bb/state.json --workload-id "
                              + container_id + " --limit 2 --window-seconds 600"]}
    assert _unit_has_policy_start(good_start, container_id, "/var/lib/bb/state.json")
    duplicate_start = {"Service": good_start["Service"] + ["ExecStart=/usr/bin/echo " + container_id]}
    assert not _unit_has_policy_start(duplicate_start, container_id, "/var/lib/bb/state.json")
    forged: dict[str, object] = dict(captured, stdout="[Unit]\n# [Service] ExecStart=foo " + container_id)
    with pytest.raises(ValueError, match="no \\[Service\\]"):
        _unit_directives(forged, "workload.service", "comment")
    forged["argv"] = ["/bin/echo", "systemctl", "cat", "workload.service"]
    with pytest.raises(ValueError, match="does not own"):
        _unit_directives(forged, "workload.service", "echo")


def test_restart_management_ssh_requires_pinned_remote_target_and_exact_command() -> None:
    import pytest

    record = {"returncode": 0,
              "argv": ["/usr/bin/ssh", "-o", "StrictHostKeyChecking=yes", "-o",
                       "UserKnownHostsFile=/etc/ssh/known_hosts", "operator@recovery.example",
                       "bash", "-lc", "test -f /run/blackbox-management-ready && printf BB_MANAGEMENT_READY"]}
    target, command = _ssh_command(record, ["bash", "-lc",
        "test -f /run/blackbox-management-ready && printf BB_MANAGEMENT_READY"], "valid")
    assert target == "operator@recovery.example" and command[0] == "bash"
    for argv in (
        ["/usr/bin/printf", "systemctl", "reboot"],
        ["/usr/bin/ssh", "-V"],
        ["/usr/bin/ssh", "operator@localhost", "systemctl", "reboot"],
        ["/usr/bin/ssh", "-o", "StrictHostKeyChecking=yes", "operator@recovery.example",
         "systemctl", "reboot"],
    ):
        with pytest.raises(ValueError):
            _ssh_command(dict(record, argv=argv), ["systemctl", "reboot"], "forged")


def test_restart_application_probe_binds_request_route_and_container_port() -> None:
    record = {"argv": ["/usr/bin/curl", "--fail-with-body", "--max-time", "15",
                       "--config", "/run/secrets/inference.curl", "--data-binary",
                       '{"model":"model-v1","messages":[{"role":"user","content":"ping"}]}',
                       "--write-out", "\\n%{http_code}", "http://127.0.0.1:8080/v1/chat/completions"],
              "returncode": 0,
              "stdout": '{"model":"model-v1","choices":[{"message":{"content":"pong"}}]}\n200'}
    assert _curl_response(record, {8080}, "model-v1")
    assert not _curl_response(record, {8081}, "model-v1")
    assert not _curl_response(record, {8080}, "different-model")
    wrong_status_command = dict(record)
    wrong_status_command["argv"] = list(record["argv"])
    wrong_status_command["argv"][wrong_status_command["argv"].index("--write-out") + 1] = "200"
    assert not _curl_response(wrong_status_command, {8080}, "model-v1")
    body_only = dict(record, argv=["/usr/bin/echo", "fake"], stdout=record["stdout"])
    assert not _curl_response(body_only, {8080}, "model-v1")
