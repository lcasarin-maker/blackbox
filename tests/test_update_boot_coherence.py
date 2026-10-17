"""Pre-reboot kernel gate (FORUM-00-KERNEL-INITRD-UPDATE-GATE): healthy case, incident negatives,
recovery trial, and the controls proving each verdict can come out the other way."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tools import forum_finding, preflight
from tools import update_boot_coherence as ubc

FINDING = ubc.FINDING
T, P = "7.0.0-1019-nvidia", "6.17.0-1032-nvidia"
B1, B2, B3 = ("11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222",
              "33333333-3333-3333-3333-333333333333")


def _salidas() -> dict[str, tuple[int, str, str]]:
    return {
        "uname": (0, P + "\n", ""),
        "dpkg": (0, "", ""),
        "apt-get": (0, "Reading package lists...\n", ""),
        "stat": (0, f"/boot/vmlinuz-{T} 21675307\n/boot/initrd.img-{T} 86338312\n"
                    f"/boot/vmlinuz-{P} 20896063\n/boot/initrd.img-{P} 84189487\n", ""),
        "mokutil": (0, "SecureBoot enabled\n", ""),
        "signer": (0, "Canonical Ltd. Kernel Module Signing\n", ""),
        "vermagic": (0, f"{T} SMP preempt mod_unload modversions aarch64\n", ""),
    }


def _sano() -> list[dict[str, Any]]:
    salidas = _salidas()
    filas = []
    for argv in ubc.comandos_kernel(T, P):
        rc, out, err = salidas[argv[4] if argv[0] == "modinfo" else argv[0]]
        filas.append({"argv": argv, "rc": rc, "stdout": out, "stderr": err})
    return filas


def _prueba(boots: tuple[str, str, str] = (B1, B2, B3),
            kernels: tuple[str, str, str] = (P, "6.11.0-1016-nvidia", P)) -> dict[str, Any]:
    comandos = []
    for fase, boot, kernel in zip(ubc.TRIAL_PHASES, boots, kernels):
        comandos += [{"argv": ["cat", "/proc/sys/kernel/random/boot_id"], "exit_code": 0, "stdout": boot + "\n",
                      "stderr": "", "phase": fase},
                     {"argv": ["uname", "-r"], "exit_code": 0, "stdout": kernel + "\n", "stderr": "", "phase": fase}]
    return {"id": FINDING, "commands": comandos}


def _evidencia(d: Path, filas: list[dict[str, Any]], prueba: dict[str, Any] | None = None,
               snapshot: dict[str, Any] | None = None) -> Path:
    d.mkdir()
    snap = snapshot if snapshot is not None else ubc.snapshot_kernel(filas, T)
    (d / "commands.json").write_text(json.dumps({"id": FINDING, "commands": [
        {"argv": f["argv"], "exit_code": f["rc"], "stdout": f["stdout"], "stderr": f["stderr"]} for f in filas]}), encoding="utf-8")
    (d / "preflight.json").write_text(json.dumps({"id": FINDING, "target_kernel": T, "snapshot": snap,
                                                  "preflight_result": preflight.check_kernel(snap)}), encoding="utf-8")
    if prueba is not None:
        (d / ubc.TRIAL_FILE).write_text(json.dumps(prueba), encoding="utf-8")
    return d


def test_sano_deriva_un_snapshot_completo_que_pasa() -> None:
    snap = ubc.snapshot_kernel(_sano(), T)
    assert all(v is True for v in snap.values()), snap
    assert preflight.check_kernel(snap) == {"status": "pass", "findings": []}


def test_cada_negativo_de_incidente_bloquea_con_su_etiqueta() -> None:
    negativos = ubc.negativos_kernel(_sano(), T)
    assert len(negativos) == 7
    for nombre, (filas, etiqueta) in negativos.items():
        juicio = preflight.check_kernel(ubc.snapshot_kernel(filas, T))
        assert juicio["status"] == "block" and etiqueta in juicio["findings"], (nombre, juicio)
    assert ubc.evaluar_negativos(_sano(), T) is None


def test_modulo_sin_firma_con_secure_boot_apagado_no_es_falso_positivo() -> None:
    filas = [{**f, "stdout": ""} if f["argv"][-2:] == ["signer", "nvidia"] else f for f in _sano()]
    apagado = [{**f, "stdout": "SecureBoot disabled\n"} if f["argv"][0] == "mokutil" else f for f in filas]
    assert ubc.snapshot_kernel(apagado, T)["module_ready"] is True
    ilegible = [{**f, "rc": 1} if f["argv"][0] == "mokutil" else f for f in filas]
    assert ubc.snapshot_kernel(ilegible, T)["module_ready"] is None  # could_not_run, no verdict


def test_sin_prueba_de_arranque_queda_could_not_run(tmp_path: Path) -> None:
    r = forum_finding.evaluate(FINDING, _evidencia(tmp_path / "e", _sano()))
    assert (r["status"], r["fail"], r["could_not_run"]) == ("unknown", 0, 1), r
    assert "recovery-trial.json" in r["reason"] and "7 incident negatives pass" in r["reason"]


def test_prueba_de_recuperacion_real_cierra(tmp_path: Path) -> None:
    r = forum_finding.evaluate(FINDING, _evidencia(tmp_path / "e", _sano(), _prueba()))
    assert (r["status"], r["fail"], r["could_not_run"]) == ("pass", 0, 0), r


@pytest.mark.parametrize("prueba,estado,motivo", [
    (_prueba(boots=(B1, B1, B3)), "fail", "share a boot_id"),
    (_prueba(kernels=(P, P, P)), "fail", "default kernel"),
    (_prueba(kernels=(P, "6.11.0-1016-nvidia", "6.11.0-1016-nvidia")), "fail", "roll back"),
    ({"id": FINDING, "commands": _prueba()["commands"][:4]}, "unknown", "restaurado"),
    ({"id": "OTRA", "commands": _prueba()["commands"]}, "unknown", "missing"),
])
def test_prueba_de_recuperacion_rota_no_cierra(tmp_path: Path, prueba: dict[str, Any], estado: str,
                                               motivo: str) -> None:
    r = forum_finding.evaluate(FINDING, _evidencia(tmp_path / "e", _sano(), prueba))
    assert r["status"] == estado and motivo in r["reason"], r


def test_control_negativo_un_gate_ciego_da_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: a check_kernel that never blocks must turn the verdict into fail, even with a good trial."""
    evidencia = _evidencia(tmp_path / "e", _sano(), _prueba())
    monkeypatch.setattr(preflight, "check_kernel", lambda _s: {"status": "pass", "findings": []})
    monkeypatch.setitem(preflight.CHECKS, "kernel", preflight.check_kernel)
    r = forum_finding.evaluate(FINDING, evidencia)
    assert (r["status"], r["fail"]) == ("fail", 1), r
    assert "blind to incident negative" in r["reason"]


def test_snapshot_registrado_que_contradice_las_filas_da_fail(tmp_path: Path) -> None:
    filas = [{**f, "rc": 100, "stderr": "E: Unmet dependencies.\n"} if f["argv"][0] == "apt-get" else f
             for f in _sano()]
    mentira = {**ubc.snapshot_kernel(filas, T), "apt_check": True}
    r = forum_finding.evaluate(FINDING, _evidencia(tmp_path / "e", filas, _prueba(), snapshot=mentira))
    assert r["status"] == "fail" and "derived from raw rows" in r["reason"], r


def test_estado_roto_real_bloquea_antes_de_mirar_la_prueba(tmp_path: Path) -> None:
    filas = [{**f, "stdout": f["stdout"].replace(f"initrd.img-{T} 86338312", f"initrd.img-{T} 0")}
             if f["argv"][0] == "stat" else f for f in _sano()]
    r = forum_finding.evaluate(FINDING, _evidencia(tmp_path / "e", filas, _prueba()))
    assert r["status"] == "fail" and "target initrd missing or empty" in r["reason"], r


def test_captura_registra_could_not_run_y_no_escribe_el_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ubc.socket, "gethostname", lambda: "maquina-x")

    def correr(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        if argv[0] == "mokutil":
            raise FileNotFoundError("mokutil")
        return subprocess.CompletedProcess(argv, 0, "signer maquina-x key\n", "")

    filas = ubc.capturar([["modinfo"], ["mokutil", "--sb-state"]], correr, fase="antes")
    assert filas[0]["stdout"] == "signer <host> key\n" and filas[0]["phase"] == "antes"
    assert filas[1]["exit_code"] == 127 and filas[1]["stderr"].startswith("could_not_run")
