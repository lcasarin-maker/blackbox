"""Controls positive, negative, unknown, and CLI paths for preflight checks."""

import json
from pathlib import Path
import runpy

import pytest

from tools import preflight


def test_apt_classifies_simulated_removals() -> None:
    assert preflight.check_apt({})["status"] == "unknown"
    assert preflight.check_apt({"plan": "0 upgraded, 0 newly installed, 0 to remove, 0 not upgraded.", "critical_packages": [], "exit_code": 0, "stderr": ""})["status"] == "unknown"
    assert preflight.check_apt({"plan": "The following packages will be REMOVED:\n1 upgraded, 0 newly installed, 1 to remove and 0 not upgraded.\nRemv core [1]", "critical_packages": ["core"], "exit_code": 0, "stderr": ""})["status"] == "block"
    assert preflight.check_apt({"plan": "0 upgraded, 0 newly installed, 0 to remove, 0 not upgraded.", "critical_packages": ["core"], "exit_code": 0, "stderr": ""})["status"] == "pass"
    assert preflight.check_apt({"plan": "0 upgraded, 0 newly installed, 0 to remove, 0 not upgraded.", "critical_packages": [None], "exit_code": 0, "stderr": ""})["status"] == "unknown"
    assert preflight.check_apt({"plan": "0 upgraded, 0 newly installed, 0 to remove, 0 not upgraded.", "critical_packages": ["core"]})["status"] == "unknown"
    assert preflight.check_apt({"plan": "Remv core [1]", "critical_packages": ["core"], "exit_code": 0, "stderr": ""})["status"] == "unknown"
    assert preflight.check_apt({"plan": "0 upgraded, 0 newly installed, 0 to remove, 0 not upgraded.", "critical_packages": ["core"], "exit_code": 1, "stderr": ""})["status"] == "unknown"
    assert preflight.check_apt({"plan": "0 upgraded, 0 newly installed, 0 to remove, 0 not upgraded.", "critical_packages": ["core"], "exit_code": 0, "stderr": "error"})["status"] == "unknown"
    assert preflight.check_apt({"plan": "1 upgraded, 0 newly installed, 2 to remove and 0 not upgraded.\nRemv core [1]", "critical_packages": ["core"], "exit_code": 0, "stderr": ""})["status"] == "unknown"
    nvidia_firmware = "nvidia-firmware-580-580.173.02"
    actual_simulation = f"The following packages will be REMOVED:\n  {nvidia_firmware}\n0 upgraded, 0 newly installed, 1 to remove and 15 not upgraded.\nRemv {nvidia_firmware} [580.173.02-0ubuntu0.24.04.1]\n"
    assert preflight.check_apt({"plan": actual_simulation, "critical_packages": ["nvidia-firmware-580-580.178.04:arm64"], "exit_code": 0, "stderr": ""})["status"] == "pass"
    actual_critical = actual_simulation.replace(nvidia_firmware, "nvidia-system-station")
    assert preflight.check_apt({"plan": actual_critical, "critical_packages": ["nvidia-system-station:arm64"], "exit_code": 0, "stderr": ""})["status"] == "block"


def test_runtime_compatibility_negative_controls() -> None:
    good = {
        "host_arch": "aarch64", "image_arch": "arm64", "image_digest": "sha256:" + "a" * 64,
        "driver_version": "580.178.04", "image_driver_constraint": "cuda>=13.0 brand=...",
        "gpu_arch": "12.1", "backend_arches": ["12.0", "12.1"],
        "driver_compatibility": "pass", "backend_manifest_complete": True,
    }
    assert preflight.check_runtime({})["status"] == "unknown"
    assert preflight.check_runtime(good)["status"] == "pass"
    for key, value in (("host_arch", "x86_64"), ("image_arch", "amd64"), ("image_digest", "latest"),
                       ("driver_compatibility", "block")):
        sample = dict(good, **{key: value})
        assert preflight.check_runtime(sample)["status"] == "block", key
    assert preflight.check_runtime(dict(good, backend_manifest_complete=False, backend_arches=["12.0"]))["status"] == "unknown"
    assert preflight.check_runtime(dict(good, backend_arches=["12.0"]))["status"] == "block"
    assert preflight.check_runtime(dict(good, driver_compatibility="unknown"))["status"] == "unknown"
    assert preflight.check_runtime(dict(good, driver_compatibility="unsupported"))["status"] == "unknown"
    assert preflight.check_runtime(dict(good, host_arch=3))["status"] == "unknown"
    assert preflight.check_runtime(dict(good, image_arch=" "))["status"] == "unknown"
    assert preflight.check_runtime(dict(good, backend_arches="12.1"))["status"] == "unknown"
    assert preflight.check_runtime(dict(good, backend_manifest_complete="false"))["status"] == "unknown"


def test_gsp_distinguishes_pci_from_usable_gpu() -> None:
    assert preflight.check_gsp({})["status"] == "unknown"
    good = {"pci_present": True, "cuda_status": 0, "gsp_timeout": False, "evidence_id": "incident"}
    assert preflight.check_gsp(good)["status"] == "pass"
    assert preflight.check_gsp(dict(good, pci_present=False))["status"] == "block"
    assert preflight.check_gsp(dict(good, cuda_status=999))["status"] == "block"
    assert preflight.check_gsp(dict(good, gsp_timeout=True))["status"] == "block"
    assert preflight.check_gsp(dict(good, pci_present="yes"))["status"] == "unknown"
    assert preflight.check_gsp(dict(good, evidence_id=""))["status"] == "unknown"


def test_fallback_detects_silent_cpu_provider() -> None:
    assert preflight.check_fallback({})["status"] == "unknown"
    good = {"requests": 2, "requested_provider": "gpu", "observed_provider": "gpu",
            "worker_restarted": False, "evidence_id": "trace"}
    assert preflight.check_fallback(good)["status"] == "pass"
    assert preflight.check_fallback(dict(good, requests=0))["status"] == "unknown"
    assert preflight.check_fallback(dict(good, requests=-1))["status"] == "block"
    assert preflight.check_fallback(dict(good, observed_provider="cpu"))["status"] == "block"
    assert preflight.check_fallback(dict(good, requests="2"))["status"] == "unknown"
    assert preflight.check_fallback(dict(good, worker_restarted="false"))["status"] == "unknown"


def test_drm_gate_detects_override_and_recovery_failures() -> None:
    assert preflight.check_drm({})["status"] == "unknown"
    good = {"effective_modeset": "Y", "target_requires_kms": True, "override_present": True,
            "recovery_accessible": True}
    assert preflight.check_drm(good)["status"] == "pass"
    assert preflight.check_drm(dict(good, effective_modeset="N"))["status"] == "block"
    assert preflight.check_drm(dict(good, target_requires_kms=False, override_present=False,
                                   effective_modeset="N"))["status"] == "pass"
    assert preflight.check_drm(dict(good, recovery_accessible=False))["status"] == "block"
    assert preflight.check_drm(dict(good, effective_modeset="enabled"))["status"] == "unknown"
    assert preflight.check_drm(dict(good, target_requires_kms="true"))["status"] == "unknown"


def test_kernel_gate_checks_every_boot_condition() -> None:
    assert preflight.check_kernel({})["status"] == "unknown"
    good = {"dpkg_clean": True, "apt_check": True, "vmlinuz_present": True, "initrd_present": True,
            "module_ready": True, "previous_kernel_bootable": True}
    assert preflight.check_kernel(good)["status"] == "pass"
    for key in good:
        assert preflight.check_kernel(dict(good, **{key: False}))["status"] == "block", key
    assert preflight.check_kernel(dict(good, dpkg_clean="yes"))["status"] == "unknown"


@pytest.mark.parametrize("content,status,code", [
    ('{"plan":"0 upgraded, 0 newly installed, 0 to remove, 0 not upgraded.","critical_packages":["core"],"exit_code":0,"stderr":""}', "pass", 0),
    ('{"plan":"The following packages will be REMOVED:\\nRemv core [1]\\n0 upgraded, 0 newly installed, 1 to remove and 0 not upgraded.","critical_packages":["core"],"exit_code":0,"stderr":""}', "block", 2),
    ('[]', "unknown", 2),
    ('{', "unknown", 2),
])
def test_cli_classifies_json(tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str,
                             status: str, code: int) -> None:
    source = tmp_path / "snapshot.json"
    source.write_text(content, encoding="utf-8")
    assert preflight.main(["apt", str(source)]) == code
    assert json.loads(capsys.readouterr().out)["status"] == status


def test_cli_accepts_evidence_envelope(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "evidence.json"
    source.write_text('{"snapshot":{"plan":"0 upgraded, 0 newly installed, 0 to remove, 0 not upgraded.","critical_packages":["core"],"exit_code":0,"stderr":""}}', encoding="utf-8")
    assert preflight.main(["apt", str(source)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "pass"
    source.write_text('{"snapshot":[]}', encoding="utf-8")
    assert preflight.main(["apt", str(source)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "unknown"


def test_cli_reports_unreadable_snapshot(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert preflight.main(["kernel", str(tmp_path / "missing.json")]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "unknown"


def test_module_entrypoint_executes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "snapshot.json"
    source.write_text('{"plan":"0 upgraded, 0 newly installed, 0 to remove, 0 not upgraded.","critical_packages":["core"],"exit_code":0,"stderr":""}', encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["tools.preflight", "apt", str(source)])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(Path(preflight.__file__)), run_name="__main__")
    assert exit_info.value.code == 0
