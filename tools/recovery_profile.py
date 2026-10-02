"""Read recovery state without opening watchdog devices or changing policy."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


STATE_PATHS = (
    'proc/sys/kernel/panic', 'proc/sys/kernel/panic_on_rcu_stall',
    'sys/module/kernel/parameters/crash_kexec_post_notifiers', 'proc/cmdline',
    'proc/sys/kernel/random/boot_id', 'proc/sys/kernel/osrelease',
    'proc/modules', 'sys/kernel/kexec_crash_loaded',
)


def read(path: Path) -> dict:
    """A missing or denied interface is an unread observation, never zero."""
    try:
        return {'status': 'read', 'value': path.read_text(encoding="utf-8").strip()}
    except (OSError, UnicodeError) as exc:
        return {'status': 'could_not_run', 'error': str(exc)}


def entries(path: Path) -> tuple[list[Path], str | None]:
    try:
        return sorted(path.iterdir()), None
    except OSError as exc:
        return [], str(exc)


def pstore(path: Path) -> dict:
    """Keep fingerprints and independent signatures, rather than raw secrets."""
    files, error = entries(path)
    records = []
    for file in files:
        observation = read(file)
        if observation['status'] == 'read':
            content = observation.pop('value')
            observation['normalized_text_sha256'] = hashlib.sha256(content.encode()).hexdigest()
            observation['signals'] = [name for name in
                ('FPAC', 'PSCI', 'NMI', 'SBSA', 'DOE', 'RCU') if name in content]
        records.append({'file': file.name, **observation})
    return {'status': 'could_not_run' if error else 'read',
            'error': error, 'records': records, 'record_count': len(records)}


def capture(root: Path = Path('/')) -> dict:
    state = {name: read(root / name) for name in STATE_PATHS}
    devices, error = entries(root / 'sys/class/watchdog')
    watchdog = {device.name: {name: read(device / name) for name in
        ('identity', 'state', 'status', 'timeout', 'nowayout', 'bootstatus')}
        for device in devices}
    persistent = pstore(root / 'sys/fs/pstore')
    unread = sum(row['status'] == 'could_not_run' for row in state.values())
    unread += sum(row['status'] == 'could_not_run'
                  for device in watchdog.values() for row in device.values())
    unread += int(error is not None) + int(persistent['status'] == 'could_not_run')
    unread += sum(row['status'] == 'could_not_run' for row in persistent['records'])
    return {'status': 'partial' if unread else 'complete', 'could_not_run': unread,
            'state': state, 'watchdog': watchdog, 'watchdog_error': error,
            'watchdog_device_count': len(devices), 'pstore': persistent,
            'limitations': ['sysfs state does not identify the device owner PID',
                            'empty pstore does not prove capture or recovery works',
                            'configured panic does not prove natural stall recovery']}


def main() -> int:
    result = capture()
    print(json.dumps(result, indent=2))
    return 2 if result["could_not_run"] else 0


if __name__ == '__main__':
    raise SystemExit(main())
