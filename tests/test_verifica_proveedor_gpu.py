"""GPU/CPU_FALLBACK/INDETERMINADO verdicts, with a CPU_FALLBACK negative control."""

from pathlib import Path

import pytest

from tools import verifica_proveedor_gpu as v

FX = Path(__file__).parent / "fixtures" / "verifica_proveedor_gpu"


def _fx(name: str) -> str:
    return (FX / name).read_text(encoding="utf-8")


def _runner(maps_rc: int, maps: str, apps_rc: int, apps: str) -> v.Runner:
    def run(argv: list[str]) -> tuple[int, str]:
        return (maps_rc, maps) if "sh" in argv else (apps_rc, apps)
    return run


def test_gpu() -> None:
    r = v.check_container("c", runner=_runner(0, _fx("gpu_maps.txt"), 0, "236, 34345\n"))
    assert r["verdict"] == "GPU" and r["processes"][0]["gpu_mib"] == 34345


def test_cpu_fallback_negative_control() -> None:
    r = v.check_container("c", runner=_runner(0, _fx("cpu_fallback_maps.txt"), 0, ""))
    assert r["verdict"] == "CPU_FALLBACK"


def test_libcuda_mapped_but_no_context_is_cpu_fallback() -> None:
    r = v.check_container("c", runner=_runner(0, _fx("gpu_maps.txt"), 0, ""))
    assert r["verdict"] == "CPU_FALLBACK"


@pytest.mark.parametrize("maps_rc,maps,apps_rc,apps", [
    (1, "", 0, ""),                                   # docker exec failed
    (0, _fx("gpu_maps.txt"), 9, ""),                  # nvidia-smi failed
    (0, _fx("gpu_maps.txt"), 0, "garbage\n"),         # malformed csv
    (0, "236|ERR|VLLM::EngineCore\n", 0, "236, 5\n"), # maps unreadable
    (0, "236|0|VLLM::EngineCore\n", 0, "236, 5\n"),   # memory without libcuda
    (0, "1|3|other\n", 0, ""),                        # no engine process
])
def test_indeterminado(maps_rc: int, maps: str, apps_rc: int, apps: str) -> None:
    r = v.check_container("c", runner=_runner(maps_rc, maps, apps_rc, apps))
    assert r["verdict"] == "INDETERMINADO" and r["reasons"]


def test_parse_noise_and_blank_lines() -> None:
    assert v.parse_maps("noise\n5|x|cmd\n") == [{"pid": 5, "libcuda": None, "cmd": "cmd"}]
    assert v.parse_apps("\n1, 2\n") == {1: 2}


def test_docker_runner_missing_binary() -> None:
    rc, out = v._docker_runner(["/nonexistent-binary-xyz"])
    assert rc == 127 and "cannot run" in out


def test_main_exit_codes(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    for verdict, code in (("GPU", 0), ("CPU_FALLBACK", 1), ("INDETERMINADO", 2)):
        monkeypatch.setattr(v, "check_container", lambda c, m, verdict=verdict: {"verdict": verdict})
        assert v.main(["c"]) == code
    assert "INDETERMINADO" in capsys.readouterr().out
