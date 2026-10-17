"""Pre-OTA DRM gate (FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT): healthy case, incident negatives,
recovery trial, and the controls proving each verdict can come out the other way."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tools import forum_finding, preflight
from tools import update_drm_coherence as udc

FINDING = udc.FINDING
B0, B1, B2, B3 = ("00000000-0000-4000-8000-000000000000", "11111111-1111-4111-8111-111111111111",
                  "22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333")
DRM = udc.DRM
DECL = {"id": FINDING, "target_ota": "DGX OS 7.5.0", "requires_kms": True,
        "source": "https://docs.nvidia.com/dgx/dgx-spark/release-notes.html",
        "statement": "texto literal de la declaracion del vendor"}
KMS = "/etc/modprobe.d/nvidia-graphics-drivers-kms.conf:options nvidia_drm modeset=1\n"
OVERRIDE = "/etc/modprobe.d/zz-nvidia-drm-override.conf:options nvidia-drm modeset=0\n"


def _row(argv: list[str], stdout: str, rc: int = 0, stderr: str = "") -> dict[str, Any]:
    return {"argv": argv, "rc": rc, "stdout": stdout, "stderr": stderr}


def _conectores(conector: str, driver: str, estado: str = "connected") -> list[dict[str, Any]]:
    """card0 bound to `driver` (simple-framebuffer or nvidia), card1 always nvidia."""
    card0 = "/sys/bus/platform/drivers/simple-framebuffer" if driver == "simple" else "/sys/bus/pci/drivers/nvidia"
    return [_row(["ls", DRM], f"card0\n{conector}\ncard1\nrenderD128\nversion\n"),
            _row(["grep", "-H", ".", f"{DRM}/{conector}/status"], f"{DRM}/{conector}/status:{estado}\n"),
            _row(["readlink", "-f", f"{DRM}/card0/device/driver", f"{DRM}/card1/device/driver"],
                 f"{card0}\n/sys/bus/pci/drivers/nvidia\n")]


def _config(modprobe: str = KMS, release: str = "7.2.3") -> list[dict[str, Any]]:
    return [_row(["uname", "-r"], "6.17.0-1032-nvidia\n"),
            _row(udc.RELEASE, f'DGX_SWBUILD_VERSION="{release}"\n'),
            _row(udc.PAQUETE, "nvidia-drm-options-modeset0 25.07-1 ii \n"),
            _row(udc.MODPROBE, modprobe),
            _row(udc.CMDLINE, "", rc=1)]


def _sano(modeset: str = "Y", boot_raiz: str = B0) -> list[dict[str, Any]]:
    raiz = (f"== boot_id\n{boot_raiz}\n== /sys/module/nvidia_drm/parameters\n"
            f"nvidia_drm.modeset={modeset}\nnvidia_drm.fbdev=Y\n")
    return [_row(udc.BOOT_ID, B0 + "\n"), *_config(), _row(udc.MODESET_ROOT, raiz),
            _row(udc.SSH_ESCUCHA, "LISTEN 0 4096 0.0.0.0:22 0.0.0.0:*\n"),
            *_conectores("card1-HDMI-A-1", "nvidia")]


def _fase_filas(fase: str, boot: str, conector: str = "card1-HDMI-A-1", driver: str = "nvidia",
                modprobe: str = KMS, ssh: str = "<ip> 50000 <ip> 22\n", estado: str = "connected"
                ) -> list[dict[str, Any]]:
    filas = [_row(udc.BOOT_ID, boot + "\n"), *_config(modprobe), _row(udc.SSH_SESION, ssh, rc=0 if ssh else 1),
             *_conectores(conector, driver, estado)]
    return [{"argv": f["argv"], "exit_code": f["rc"], "stdout": f["stdout"], "stderr": f["stderr"], "phase": fase}
            for f in filas]


def _prueba(boots: tuple[str, str, str] = (B1, B2, B3), **por_fase: dict[str, Any]) -> dict[str, Any]:
    base = {"antes": {"modprobe": KMS + OVERRIDE, "conector": "card0-Unknown-1", "driver": "simple"},
            "objetivo": {"modprobe": KMS}, "rollback": {"modprobe": KMS + OVERRIDE,
                                                         "conector": "card0-Unknown-1", "driver": "simple"}}
    comandos: list[dict[str, Any]] = []
    for fase, boot in zip(udc.TRIAL_PHASES, boots):
        comandos += _fase_filas(fase, boot, **{**base[fase], **por_fase.get(fase, {})})
    return {"id": FINDING, "commands": comandos}


def _evidencia(d: Path, filas: list[dict[str, Any]], prueba: dict[str, Any] | None = None,
               decl: dict[str, Any] | None = DECL, snapshot: dict[str, Any] | None = None) -> Path:
    d.mkdir()
    snap = snapshot if snapshot is not None else udc.snapshot_drm(filas, decl)
    (d / "commands.json").write_text(json.dumps({"id": FINDING, "commands": [
        {"argv": f["argv"], "exit_code": f["rc"], "stdout": f["stdout"], "stderr": f["stderr"]} for f in filas]}),
        encoding="utf-8")
    (d / "preflight.json").write_text(json.dumps({"id": FINDING, "kind": "drm", "snapshot": snap,
                                                  "preflight_result": preflight.check_drm(snap)}), encoding="utf-8")
    if decl is not None:
        (d / udc.DECLARATION_FILE).write_text(json.dumps(decl), encoding="utf-8")
    if prueba is not None:
        (d / udc.TRIAL_FILE).write_text(json.dumps(prueba), encoding="utf-8")
    return d


def test_sano_deriva_un_snapshot_completo_que_pasa() -> None:
    snap = udc.snapshot_drm(_sano(), DECL)
    assert snap == {"effective_modeset": "Y", "target_requires_kms": True, "override_present": False,
                    "recovery_accessible": True}
    assert preflight.check_drm(snap) == {"status": "pass", "findings": []}


def test_cada_negativo_de_incidente_bloquea_por_separado_con_su_etiqueta() -> None:
    negativos = udc.negativos_drm(_sano(), DECL)
    assert len(negativos) == 4
    for nombre, (filas, decl, etiqueta) in negativos.items():
        juicio = preflight.check_drm(udc.snapshot_drm(filas, decl))
        assert juicio["status"] == "block" and etiqueta in juicio["findings"], (nombre, juicio)
    assert udc.evaluar_negativos(_sano(), DECL) is None


def test_el_negativo_del_incidente_aislado_bloquea_solo_por_kms() -> None:
    """Incident 382452: no override in config, KMS off, OTA requires KMS -> only the KMS label."""
    filas, decl, _ = udc.negativos_drm(_sano(), DECL)["OTA exige KMS y modeset efectivo apagado (incidente 382452)"]
    juicio = preflight.check_drm(udc.snapshot_drm(filas, decl))
    assert juicio == {"status": "block", "findings": ["OTA requires KMS but effective modeset is not enabled"]}


def test_lectura_root_de_otro_arranque_no_cuenta() -> None:
    assert udc.snapshot_drm(_sano(boot_raiz=B3), DECL)["effective_modeset"] is None


def test_lectura_de_usuario_denegada_queda_could_not_run() -> None:
    filas = [f for f in _sano() if f["argv"] != udc.MODESET_ROOT]
    filas.append(_row(udc.MODESET_USER, "", rc=1, stderr=f"cat: {udc.MODESET_USER[1]}: Permission denied\n"))
    assert udc.snapshot_drm(filas, DECL)["effective_modeset"] is None


@pytest.mark.parametrize("cambio", [
    {"source": "https://forums.developer.nvidia.com/t/382452"},
    {"source": "http://docs.nvidia.com/x"},
    {"source": "https://nvidia.com.example.org/x"},
    {"requires_kms": "true"},
    {"statement": ""},
    {"id": "OTRA"},
])
def test_declaracion_sin_fuente_de_vendor_no_da_requisito(cambio: dict[str, Any]) -> None:
    assert udc.requiere_kms({**DECL, **cambio}) is None
    assert udc.requiere_kms(DECL) is True


def test_sin_declaracion_ni_prueba_queda_could_not_run(tmp_path: Path) -> None:
    r = forum_finding.evaluate(FINDING, _evidencia(tmp_path / "e", _sano(), decl=None))
    assert (r["status"], r["could_not_run"]) == ("unknown", 1) and "target_requires_kms" in r["reason"], r


def test_sin_prueba_de_recuperacion_queda_could_not_run(tmp_path: Path) -> None:
    r = forum_finding.evaluate(FINDING, _evidencia(tmp_path / "e", _sano()))
    assert (r["status"], r["fail"], r["could_not_run"]) == ("unknown", 0, 1), r
    assert "recovery-trial.json" in r["reason"] and "4 incident negatives pass" in r["reason"]


def test_prueba_de_recuperacion_real_cierra(tmp_path: Path) -> None:
    r = forum_finding.evaluate(FINDING, _evidencia(tmp_path / "e", _sano(), _prueba()))
    assert (r["status"], r["fail"], r["could_not_run"]) == ("pass", 0, 0), r


@pytest.mark.parametrize("prueba,estado,motivo", [
    (_prueba(boots=(B1, B1, B3)), "fail", "share a boot_id"),
    (_prueba(objetivo={"conector": "card0-Unknown-1", "driver": "simple"}), "fail", "incident 382452"),
    (_prueba(antes={"estado": "disconnected"}), "fail",
     "no display connector"),
    (_prueba(objetivo={"modprobe": KMS + OVERRIDE}), "fail", "same configuration"),
    (_prueba(rollback={"modprobe": KMS, "conector": "card0-Unknown-1", "driver": "simple"}), "fail",
     "does not restore"),
    (_prueba(rollback={"ssh": ""}), "unknown", "SSH session"),
    ({"id": FINDING, "commands": [c for c in _prueba()["commands"] if c["phase"] != "rollback"]}, "unknown",
     "rollback"),
    ({"id": "OTRA", "commands": _prueba()["commands"]}, "unknown", "missing"),
])
def test_prueba_de_recuperacion_rota_no_cierra(tmp_path: Path, prueba: dict[str, Any], estado: str,
                                               motivo: str) -> None:
    r = forum_finding.evaluate(FINDING, _evidencia(tmp_path / "e", _sano(), prueba))
    assert r["status"] == estado and motivo in r["reason"], r


def test_control_negativo_gate_que_da_por_satisfecho_el_requisito_kms_da_fail(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: a check_drm that treats target_requires_kms as always satisfied is blind to the incident."""
    evidencia = _evidencia(tmp_path / "e", _sano(), _prueba())
    original = preflight.check_drm

    def ciego(snapshot: dict[str, Any]) -> dict[str, Any]:
        return original({**snapshot, "target_requires_kms": False})

    monkeypatch.setattr(preflight, "check_drm", ciego)
    monkeypatch.setitem(preflight.CHECKS, "drm", ciego)
    r = forum_finding.evaluate(FINDING, evidencia)
    assert (r["status"], r["fail"]) == ("fail", 1), r
    assert "blind to incident negative 'OTA exige KMS" in r["reason"]


def test_snapshot_registrado_que_contradice_las_filas_da_fail(tmp_path: Path) -> None:
    filas = _sano()
    mentira = {**udc.snapshot_drm(filas, DECL), "target_requires_kms": False}
    r = forum_finding.evaluate(FINDING, _evidencia(tmp_path / "e", filas, _prueba(), snapshot=mentira))
    assert r["status"] == "fail" and "derived from raw rows" in r["reason"], r


def test_estado_del_incidente_real_bloquea_antes_de_mirar_la_prueba(tmp_path: Path) -> None:
    filas = [{**f, "stdout": KMS + OVERRIDE} if f["argv"] == udc.MODPROBE else f for f in _sano(modeset="N")]
    r = forum_finding.evaluate(FINDING, _evidencia(tmp_path / "e", filas, _prueba()))
    assert r["status"] == "fail" and "OTA requires KMS but effective modeset is not enabled" in r["reason"], r


def test_inventario_de_conectores_desde_un_sysfs_sustituto(tmp_path: Path) -> None:
    for nombre in ("card0", "card0-Unknown-1", "card1"):
        (tmp_path / nombre).mkdir()
    (tmp_path / "card0-Unknown-1" / "status").write_text("connected\n", encoding="utf-8")
    comandos = udc.comandos_conectores(str(tmp_path))
    assert comandos[0] == ["ls", str(tmp_path)]
    assert comandos[1] == ["grep", "-H", ".", f"{tmp_path}/card0-Unknown-1/status"]
    assert comandos[2] == ["readlink", "-f", f"{tmp_path}/card0/device/driver", f"{tmp_path}/card1/device/driver"]
    assert udc.comandos_conectores(str(tmp_path / "vacio")) == [["ls", str(tmp_path / "vacio")]]


def test_fase_de_prueba_registra_ssh_sin_ips_y_could_not_run() -> None:
    def correr(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        if argv == udc.SSH_SESION:
            return subprocess.CompletedProcess(argv, 0, "10.0.0.7 50000 10.0.0.9 22\n", "")
        if argv[0] == "dpkg-query":
            raise FileNotFoundError("dpkg-query")
        return subprocess.CompletedProcess(argv, 0, "", "")

    filas = udc.capturar_fase("antes", correr, drm="/nonexistent-drm")
    ssh = next(f for f in filas if f["argv"] == udc.SSH_SESION)
    assert ssh["stdout"] == "<ip> 50000 <ip> 22\n" and ssh["phase"] == "antes"
    dpkg = next(f for f in filas if f["argv"][0] == "dpkg-query")
    assert dpkg["exit_code"] == 127 and dpkg["stderr"].startswith("could_not_run")


def test_comandos_del_gate_solo_usan_sudo_con_root_read() -> None:
    assert all(c[0] != "sudo" for c in udc.comandos_drm())
    assert udc.MODESET_ROOT in udc.comandos_drm(root_read=True)
    assert udc.MODESET_USER not in udc.comandos_drm(root_read=True)
