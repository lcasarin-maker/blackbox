"""Exercise Wi-Fi trace semantics that determine whether an A/B trial counts."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from tools import verify_wifi_isolation as wifi


def _row(command: str, output: str, *, exit_code: int = 0,
         captured_at: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "cmd": command,
        "exit": exit_code,
        "stdout": output,
        "stderr": "",
    }
    if captured_at is not None:
        row["captured_at"] = captured_at
    return row


def test_native_link_details_and_interface_are_read_from_the_same_iw_command() -> None:
    link = _row(
        "sudo iw dev wlp2s0 link",
        "Connected to aa:bb:cc:dd:ee:ff\nSSID: lab-net\nfreq: 5180\n",
    )
    assert wifi._wifi_connected(link)
    assert wifi._link_details(link) == ("AA:BB:CC:DD:EE:FF", "lab-net", 5180)
    assert wifi._iw_interface(link) == "wlp2s0"
    assert wifi._adapter_interface(_row("ethtool -i wlp2s0", "driver: mt7925e")) == "wlp2s0"
    assert wifi._adapter_interface(_row("ethtool -i", "")) is None
    assert wifi._iw_interface(_row("iw dev bad/name link", "")) is None


def test_association_requires_the_expected_ssid_bssid_and_requested_band() -> None:
    row = _row("iw dev wlan0 link",
               "Connected to AA:BB:CC:DD:EE:FF\nSSID: office\nfreq: 5180\n")
    assert wifi._association_matches([row], 0, "802-11-wireless.bssid",
                                     "aa:bb:cc:dd:ee:ff", "office")
    assert wifi._association_matches([row], 0, "802-11-wireless.band", "a", "office")
    assert not wifi._association_matches([row], 0, "802-11-wireless.band", "bg", "office")
    assert not wifi._association_matches([row], 0, "802-11-wireless.bssid",
                                         "00:00:00:00:00:00", "office")
    assert not wifi._association_matches([row], 0, "802-11-wireless.bssid",
                                         "aa:bb:cc:dd:ee:ff", "guest")
    assert not wifi._association_matches([_row("iw dev wlan0 link", "Disconnected")],
                                         0, "802-11-wireless.band", "a", "office")


def test_ping_is_not_management_ssh_and_loopback_must_show_a_reply() -> None:
    ping = _row("ping -c 1 127.0.0.1", "1 packets transmitted, 1 received")
    silent_ping = _row("ping -c 1 localhost", "", exit_code=0)
    local_ssh = _row("ssh localhost true", "ok")
    remote_ping = _row("ping management", "ok")
    remote_ssh = _row("ssh operator@management true", "ok")
    assert wifi._is_loopback_probe(ping) and wifi._loopback_probe(ping)
    assert wifi._is_loopback_probe(silent_ping) and not wifi._loopback_probe(silent_ping)
    assert wifi._is_loopback_probe(local_ssh) and wifi._loopback_probe(local_ssh)
    assert not wifi._management_probe(remote_ping)
    assert wifi._management_probe(remote_ssh)


def test_route_is_bound_to_observed_wireless_interface() -> None:
    route = _row("ip route show default", "default via 192.0.2.1 dev wlp2s0 proto dhcp")
    assert wifi._default_route(route)
    assert wifi._default_route(route, "wlp2s0")
    assert not wifi._default_route(route, "wlan0")
    assert not wifi._default_route(_row("ip route", "192.0.2.0/24 dev wlp2s0"))


def test_capture_timestamps_must_be_timezone_aware_and_monotonic() -> None:
    start = datetime(2026, 10, 4, tzinfo=UTC)
    ordered = [
        _row("true", "", captured_at=start.isoformat()),
        _row("true", "", captured_at=(start + timedelta(seconds=1)).isoformat()),
    ]
    assert wifi._valid_timestamps(ordered)
    assert not wifi._valid_timestamps([ordered[1], ordered[0]])
    assert not wifi._valid_timestamps([_row("true", "", captured_at="2026-10-04T00:00:00")])
    assert not wifi._valid_timestamps([_row("true", "", captured_at="invalid")])
    assert not wifi._valid_timestamps([_row("true", ""), ordered[0]])


def _trial_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    origin = datetime(2026, 10, 4, tzinfo=UTC)

    def add(command: str, output: str, *, at: int | None = None) -> None:
        stamp = (origin + timedelta(seconds=at)).isoformat() if at is not None else None
        rows.append(_row(command, output, captured_at=stamp))

    snapshot = (
        "802-11-wireless.ssid: lab-net\n"
        "802-11-wireless.bssid: AA:AA:AA:AA:AA:AA\n"
        "802-11-wireless.band: a\n"
        "802-11-wireless.autoconnect-retries: 3\n"
    )
    add("nmcli connection show lab", snapshot)
    trial_values = {
        "802-11-wireless.bssid": "BB:BB:BB:BB:BB:BB",
        "802-11-wireless.band": "bg",
        "802-11-wireless.autoconnect-retries": "0",
    }
    originals = {
        "802-11-wireless.bssid": "AA:AA:AA:AA:AA:AA",
        "802-11-wireless.band": "a",
        "802-11-wireless.autoconnect-retries": "3",
    }
    clock = 0
    for prop, value in trial_values.items():
        add(f"nmcli connection modify lab {prop} {value}", "")
        add("nmcli connection up lab --timeout 20", "activated", at=clock)
        if prop.endswith("band"):
            frequency = 2412
        else:
            frequency = 5180
        bssid = value if prop.endswith("bssid") else "AA:AA:AA:AA:AA:AA"
        add("iw dev wlp2s0 link",
            f"Connected to {bssid}\nSSID: lab-net\nfreq: {frequency}\n")
        add("ip route show default", "default via 192.0.2.1 dev wlp2s0")
        add("ssh operator@management true", "reachable", at=clock + 30)
        clock += 60
        add(f"nmcli connection modify lab {prop} {originals[prop]}", "")
    add("nmcli connection show lab", snapshot)
    return rows


def test_trials_require_reassociation_route_remote_recovery_and_readback() -> None:
    rows = _trial_rows()
    result = wifi._verify_trials(rows, Path("commands.json"))
    assert result["status"] == "pass", result

    route_index = next(i for i, row in enumerate(rows) if row["cmd"] == "ip route show default")
    rows[route_index]["stdout"] = "default via 192.0.2.1 dev eth0"
    result = wifi._verify_trials(rows, Path("commands.json"))
    assert result["status"] == "fail" and "did not associate" in result["reason"], result

    rows = _trial_rows()
    final_snapshot_index = max(i for i, row in enumerate(rows)
                               if row["cmd"] == "nmcli connection show lab")
    rows[final_snapshot_index]["stdout"] = rows[0]["stdout"].replace("band: a", "band: bg")
    result = wifi._verify_trials(rows, Path("commands.json"))
    assert result["status"] == "unknown" and "rollback" in result["reason"], result


def test_incident_needs_raw_split_path_and_matching_observed_software_tuple(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    rows = [
        _row("journalctl -u NetworkManager", "wpa_supplicant: WRONG_KEY\nno-secrets"),
        _row("ping -c 1 127.0.0.1", "1 packets transmitted, 1 received"),
        _row("ssh operator@management true", "connection refused", exit_code=255),
        _row("dmidecode -t system", "Manufacturer: ASUS\nProduct Name: GX10\nBIOS Version: B.1"),
        _row("uname -r", "6.17.0-gb10"),
        _row("modinfo mt7925e", "version: 1.2"),
        _row("nmcli --version", "nmcli tool, version 1.48"),
        _row("cat /etc/os-release", 'PRETTY_NAME="NVIDIA DGX OS 7.5"'),
        _row("wpa_supplicant -v", "wpa_supplicant v2.10"),
        _row("ethtool -i wlan0", "driver: mt7925e\nfirmware-version: 2026.01"),
        _row("iw dev wlan0 link", "Connected to AA:BB:CC:DD:EE:FF\nSSID: lab\nfreq: 5180"),
    ]
    data: dict[str, Any] = {"vendor_sources": []}
    result = wifi._check_incident(data, rows, path)
    assert result is not None and result["status"] == "unknown"

    identity = wifi._observed_identity(rows)
    assert identity is not None and len(identity) == 9
    text = "OEM compatibility reference " + " | ".join(identity) + " applies to this adapter tuple."
    data["vendor_sources"] = [{"url": "https://www.asus.com/support/example", "text": text,
                                "sha256": hashlib.sha256(text.encode()).hexdigest()}]
    assert wifi._source_applies(data, rows)
    assert wifi._check_incident(data, rows, path) is None

    changed = list(identity)
    changed[4] = "other-kernel"
    unsupported = "OEM compatibility reference " + " | ".join(changed) + " applies to this adapter tuple."
    data["vendor_sources"] = [{"url": "https://www.asus.com/support/example", "text": unsupported,
                                "sha256": hashlib.sha256(unsupported.encode()).hexdigest()}]
    assert not wifi._source_applies(data, rows)


def test_incident_distinguishes_failed_local_host_from_wifi_path_failure(tmp_path: Path) -> None:
    rows = [
        _row("journalctl -u NetworkManager", "WRONG_KEY no-secrets wpa_supplicant"),
        _row("ping -c 1 127.0.0.1", "", exit_code=1),
        _row("ssh operator@management true", "connection refused", exit_code=255),
    ]
    result = wifi._check_incident({}, rows, tmp_path / "commands.json")
    assert result is not None and result["status"] == "fail" and "host failure" in result["reason"]


def test_trial_requires_baseline_all_candidate_mutations_and_bounded_remote_return() -> None:
    rows = _trial_rows()
    rows[:] = [row for row in rows if row["cmd"] != "nmcli connection show lab"]
    result = wifi._verify_trials(rows, Path("commands.json"))
    assert result["status"] == "unknown" and "initial SSID" in result["reason"]

    rows = _trial_rows()
    rows[:] = [row for row in rows if "connection modify" not in row["cmd"]]
    result = wifi._verify_trials(rows, Path("commands.json"))
    assert result["status"] == "unknown" and "candidate changes" in result["reason"]

    rows = _trial_rows()
    link = next(row for row in rows if row["cmd"] == "iw dev wlp2s0 link")
    link["stdout"] = link["stdout"].replace("SSID: lab-net", "SSID: guest")
    result = wifi._verify_trials(rows, Path("commands.json"))
    assert result["status"] == "fail" and "within 60 seconds" in result["reason"]

    rows = _trial_rows()
    remote = next(row for row in rows if row["cmd"].startswith("ssh operator@management"))
    remote["captured_at"] = (datetime(2026, 10, 4, tzinfo=UTC) + timedelta(seconds=61)).isoformat()
    result = wifi._verify_trials(rows, Path("commands.json"))
    assert result["status"] == "fail" and "within 60 seconds" in result["reason"]
