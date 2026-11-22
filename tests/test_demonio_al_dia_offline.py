"""Contrato CLI offline del verificador de mtime de demonios."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "tools" / "demonio_al_dia.sh"


def _bwrap_base(bwrap: str, pid_dir: str = "/proc/123") -> list[str]:
    return [bwrap, "--clearenv", "--unshare-all", "--die-with-parent",
            "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
            "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib64", "/lib64",
            "--dev", "/dev", "--tmpfs", "/proc", "--dir", pid_dir,
            "--tmpfs", "/run", "--tmpfs", "/tmp"]


@pytest.fixture(scope="module")
def bwrap() -> str:
    executable = shutil.which("bwrap")
    if not executable:
        pytest.skip("COULD_NOT_RUN: falta bwrap; trigger=restaurar aislamiento sintético")
    probe = subprocess.run(
        _bwrap_base(executable) + ["--chdir", "/tmp", "--setenv", "PATH", "/usr/bin:/bin",
                                   "/usr/bin/true"],
        capture_output=True, text=True, check=False, timeout=10)
    if probe.returncode:
        pytest.skip(f"COULD_NOT_RUN: bwrap aislado rc={probe.returncode}: {probe.stderr.strip()}")
    return executable


def _ejecuta(bwrap: str, tmp_path: Path, fix_stat: str, **overrides: str) -> subprocess.CompletedProcess[str]:
    fixture = tmp_path / "fixture"
    bin_dir = fixture / "bin"
    bin_dir.mkdir(parents=True)
    salida = tmp_path / "salida"
    salida.mkdir()
    (fixture / "code.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    systemctl = bin_dir / "systemctl"
    systemctl.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" >>\"$CALL_LOG\"\n"
        "[ \"${FIX_SYSTEMCTL:-ok}\" = denied ] && exit 1\n"
        "[ \"${1:-}\" = --user ] || exit 91\n"
        "[ \"${2:-}\" = show ] || exit 91\n"
        "[ \"${FIX_PID:-123}\" = 123 ] && pid=123 || pid=\"$FIX_PID\"\n"
        "printf 'ActiveState=active\\nSubState=running\\nMainPID=%s\\nExecMainStartTimestamp=%s\\n' "
        "\"$pid\" \"${FIX_TS:-2025-01-02 00:00:00 UTC}\"\n",
        encoding="utf-8")
    systemctl.chmod(0o755)
    stat = bin_dir / "stat"
    stat.write_text(
        "#!/bin/sh\n"
        "case \"$FIX_STAT\" in\n"
        " updated) printf '1\\n' ;;\n"
        " stale) printf '1800000000\\n' ;;\n"
        " same) printf '1735776000\\n' ;;\n"
        " unavailable) exit 1 ;;\n"
        " empty) : ;;\n"
        " nonnumeric) printf 'not-an-integer\\n' ;;\n"
        " overflow) printf '999999999999999999999999999999\\n' ;;\n"
        "esac\n",
        encoding="utf-8")
    stat.chmod(0o755)
    date = bin_dir / "date"
    date.write_text(
        "#!/bin/sh\n"
        "case \"${FIX_DATE:-normal}\" in\n"
        " failed_with_output) printf '1735776000\\n'; exit 1 ;;\n"
        " overflow) printf '999999999999999999999999999999\\n' ;;\n"
        " *) exec /usr/bin/date \"$@\" ;;\n"
        "esac\n",
        encoding="utf-8")
    date.chmod(0o755)
    calls = salida / "systemctl.calls"
    args = _bwrap_base(bwrap)
    args += ["--dir", "/workspace", "--ro-bind", str(RAIZ), "/workspace",
             "--dir", "/fixture", "--ro-bind", str(fixture), "/fixture",
             "--dir", "/output", "--bind", str(salida), "/output",
             "--chdir", "/workspace", "--setenv", "PATH", "/fixture/bin:/usr/bin:/bin",
             "--setenv", "HOME", "/tmp", "--setenv", "BLACKBOX_DATA", "/tmp/blackbox",
             "--setenv", "TMPDIR", "/tmp", "--setenv", "CALL_LOG", "/output/systemctl.calls",
             "--setenv", "FIX_STAT", fix_stat]
    for key, value in overrides.items():
        args += ["--setenv", key, value]
    args += ["/usr/bin/env", "bash", "/workspace/tools/demonio_al_dia.sh",
             "--user", "fixture.service", "/fixture/code.sh"]
    result = subprocess.run(args, capture_output=True, text=True, check=False, timeout=10)
    if calls.exists():
        assert "restart" not in calls.read_text(encoding="utf-8")
    return result


@pytest.mark.parametrize(("fix_stat", "overrides", "expected", "texto"), [
    ("updated", {}, 0, "despues de la ultima modificacion"),
    ("stale", {}, 1, "codigo VIEJO"),
    ("same", {}, 2, "coinciden dentro de la resolucion"),
    ("unavailable", {}, 2, "mtime"),
    ("empty", {}, 2, "mtime"),
    ("nonnumeric", {}, 2, "mtime"),
    ("overflow", {}, 2, "COULD_NOT_RUN"),
    ("updated", {"FIX_DATE": "failed_with_output"}, 2, "COULD_NOT_RUN"),
    ("updated", {"FIX_DATE": "overflow"}, 2, "COULD_NOT_RUN"),
    ("updated", {"FIX_SYSTEMCTL": "denied"}, 2, "COULD_NOT_RUN"),
    ("updated", {"FIX_PID": "999"}, 2, "COULD_NOT_RUN"),
    ("updated", {"FIX_TS": "fecha inválida"}, 2, "COULD_NOT_RUN"),
])
def test_cli_en_bwrap_sintetico_da_veredicto_correcto(
    bwrap: str, tmp_path: Path, fix_stat: str, overrides: dict[str, str],
    expected: int, texto: str,
) -> None:
    result = _ejecuta(bwrap, tmp_path, fix_stat, **overrides)
    assert result.returncode == expected, result.stdout + result.stderr
    assert texto in result.stdout + result.stderr
    if expected == 2:
        assert "COULD_NOT_RUN" in result.stderr
