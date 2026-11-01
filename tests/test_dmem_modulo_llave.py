"""dmem_modulo.sh: llave enrolada y firmas, guardia con tope por nvidia-smi, retroceso por kernel y unidad generada.

La comprobacion de llave enrolada debe sobrevivir a que mokutil --test-key salga 1; la guardia no puede colgarse con
un nvidia-smi colgado (y el control de mutacion lo demuestra: sin `timeout`, la corrida no termina); `retrocede
--kernel X` solo toca updates/ de X. Todo sobre una raiz falsa (BB_DMEM_MODROOT, BB_DMEM_ESTADO, BB_DMEM_SIN_RAIZ).
"""

from __future__ import annotations

import configparser
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "tools" / "dmem_modulo.sh"
MARCA = RAIZ / "adopted" / "system-units" / "etapa-marca.sh"
MODS = ["nvidia", "nvidia-modeset", "nvidia-uvm", "nvidia-drm", "nvidia-peermem"]


def _corre(tmp_path: Path, salida: str, rc: int) -> subprocess.CompletedProcess[str]:
    fake = tmp_path / "bin"
    fake.mkdir()
    mok = fake / "mokutil"
    mok.write_text(f"#!/bin/sh\necho '{salida}'\nexit {rc}\n", encoding="utf-8")
    mok.chmod(0o755)
    llave = tmp_path / "MOK.der"
    llave.write_bytes(b"x")
    # solo la funcion: se extrae del script para no exigir root ni tocar /lib/modules
    cuerpo = "\n".join(
        ln for ln in SCRIPT.read_text(encoding="utf-8").splitlines() if ln.startswith("llave_enrolada()")
    )
    prog = f"set -euo pipefail\nLLAVE_PUB={llave}\n{cuerpo}\nllave_enrolada\n"
    return subprocess.run(
        ["bash", "-c", prog],
        env={"PATH": f"{fake}:/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )


def test_enrolada_con_mokutil_saliendo_1(tmp_path: Path) -> None:
    assert _corre(tmp_path, "/x/MOK.der is already enrolled", 1).returncode == 0


def test_no_enrolada_es_rechazada(tmp_path: Path) -> None:
    assert _corre(tmp_path, "/x/MOK.der is not enrolled", 1).returncode != 0


def _codigo_sin_comentarios(texto: str) -> str:
    return "\n".join(ln.split(" #")[0] for ln in texto.splitlines() if not ln.lstrip().startswith("#"))


def _viola_regla_de_recarga(texto: str) -> list[str]:
    """Con Docker en cgroup systemd, recargar systemd quita la GPU a contenedores en marcha (hilo 352743)."""
    malas = []
    for ln in _codigo_sin_comentarios(texto).splitlines():
        if "daemon-reload" in ln:
            malas.append(ln.strip())
        if ("systemctl enable" in ln or "systemctl disable" in ln) and "--no-reload" not in ln:
            malas.append(ln.strip())
    return malas


def test_el_script_no_recarga_systemd() -> None:
    assert _viola_regla_de_recarga(SCRIPT.read_text(encoding="utf-8")) == []


def test_el_detector_de_recarga_ve_la_version_anterior() -> None:
    anterior = "systemctl daemon-reload && systemctl enable bb-dmem-guardia.service\nsystemctl disable bb-dmem-guardia.service\n"
    assert len(_viola_regla_de_recarga(anterior)) == 3


# --- raiz falsa: /lib/modules, estado, depmod, nvidia-smi, modinfo y openssl de mentira ----------------------------

def _ejecutable(ruta: Path, texto: str) -> Path:
    ruta.write_text(texto, encoding="utf-8")
    ruta.chmod(0o755)
    return ruta


class Caja:
    def __init__(self, tmp: Path) -> None:
        self.tmp, self.mods, self.estado, self.bin = tmp, tmp / "lib-modules", tmp / "estado", tmp / "bin"
        for d in (self.mods, self.estado, self.bin, tmp / "blackbox"):
            d.mkdir(mode=0o755)
            d.chmod(0o755)
        self.depmod_log = tmp / "depmod.log"
        _ejecutable(self.bin / "depmod", f'#!/bin/sh\necho "$*" >> {self.depmod_log}\n')
        self.env = {"PATH": f"{self.bin}:/usr/bin:/bin", "BB_DMEM_SIN_RAIZ": "1", "BB_DMEM_MODROOT": str(self.mods),
                    "BB_DMEM_ESTADO": str(self.estado), "BB_DMEM_DEPMOD": str(self.bin / "depmod"),
                    "BB_DMEM_ETAPA_MARCA": str(MARCA), "BB_DMEM_NVSMI_TIMEOUT": "1", "BB_DMEM_GUARDIA_PLAZO": "1",
                    "BB_ETAPA_DIR": str(tmp / "blackbox" / "arranque"), "BB_ETAPA_KMSG": str(tmp / "kmsg")}

    def instalado(self, kernel: str) -> list[Path]:
        """Los 5 .ko en updates/ de `kernel` y sus lineas en instalados.txt, como los deja `instala`."""
        up = self.mods / kernel / "updates"
        up.mkdir(parents=True)
        kos = []
        with (self.estado / "instalados.txt").open("a", encoding="utf-8") as f:
            for m in MODS:
                ko = up / f"{m}.ko"
                ko.write_bytes(f"{kernel}/{m}".encode())
                f.write(f"{hashlib.sha256(ko.read_bytes()).hexdigest()}  {ko}\n")
                kos.append(ko)
        return kos

    def nvidia_smi(self, cuerpo: str) -> None:
        _ejecutable(self.bin / "nvidia-smi", "#!/bin/sh\n" + cuerpo + "\n")

    def etapas(self) -> list[str]:
        f = self.tmp / "blackbox" / "arranque" / "etapas.jsonl"
        return [json.loads(x)["etapa"] for x in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []

    def depmod(self) -> list[str]:
        return self.depmod_log.read_text(encoding="utf-8").splitlines() if self.depmod_log.exists() else []


def _corre_con_tope(argv: list[str], env: dict[str, str], tope: float) -> subprocess.CompletedProcess[str] | None:
    """None si no termino en `tope` s. Mata el GRUPO: un nvidia-smi colgado retendria la tuberia y `run` no volveria."""
    p = subprocess.Popen(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=tope)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        return None
    return subprocess.CompletedProcess(argv, p.returncode, out, "")


def _dmem(caja: Caja, *args: str, script: Path = SCRIPT, tope: float = 60) -> subprocess.CompletedProcess[str]:
    r = _corre_con_tope(["bash", str(script), *args], caja.env, tope)
    assert r is not None, f"dmem_modulo.sh {' '.join(args)} no termino en {tope} s"
    return r


@pytest.fixture
def caja(tmp_path: Path) -> Caja:
    return Caja(tmp_path)


KERNEL = os.uname().release


def test_guardia_con_nvidia_smi_colgado_sale_por_timeout_y_retrocede(caja: Caja):
    kos = caja.instalado(KERNEL)
    caja.nvidia_smi("exec sleep 300")
    t0 = time.monotonic()
    r = _dmem(caja, "guardia", tope=30)
    assert r.returncode == 0, r.stdout
    assert time.monotonic() - t0 < 20
    assert "la GPU NO respondio en 1 s (cada nvidia-smi con tope de 1 s): retrocedo" in r.stdout
    assert not any(k.exists() for k in kos) and (caja.estado / "retrocedido").exists()
    assert caja.depmod() == [f"-a {KERNEL}"] and caja.etapas() == ["guardia-dmem-retrocede"]


def test_control_de_mutacion_sin_timeout_la_guardia_se_cuelga(caja: Caja, tmp_path: Path):
    texto = SCRIPT.read_text(encoding="utf-8")
    assert texto.count('timeout "$NVSMI_TIMEOUT" nvidia-smi') == 1
    mutado = tmp_path / "dmem_modulo_sin_timeout.sh"
    mutado.write_text(texto.replace('timeout "$NVSMI_TIMEOUT" nvidia-smi', "nvidia-smi"), encoding="utf-8")
    caja.instalado(KERNEL)
    caja.nvidia_smi("exec sleep 300")
    assert _corre_con_tope(["bash", str(mutado), "guardia"], caja.env, 8) is None
    assert (caja.mods / KERNEL / "updates" / "nvidia.ko").exists()  # colgada: nunca llego a retroceder


def test_guardia_con_gpu_listada_se_queda_y_lo_marca(caja: Caja):
    kos = caja.instalado(KERNEL)
    caja.nvidia_smi('echo "GPU 0: NVIDIA GB10 (UUID: GPU-x)"')
    r = _dmem(caja, "guardia")
    assert r.returncode == 0 and "el modulo parcheado se queda" in r.stdout
    assert all(k.exists() for k in kos) and caja.depmod() == [] and caja.etapas() == ["guardia-dmem-gpu-ok"]


def test_control_negativo_rc_0_sin_gpu_listada_no_cuenta_como_lista(caja: Caja):
    kos = caja.instalado(KERNEL)
    caja.nvidia_smi('echo "No devices were found"')
    assert _dmem(caja, "guardia", tope=30).returncode == 0
    assert not any(k.exists() for k in kos) and caja.etapas() == ["guardia-dmem-retrocede"]


def test_guardia_sin_la_marca_instalada_lo_dice_y_decide_igual(caja: Caja):
    caja.instalado(KERNEL)
    caja.nvidia_smi('echo "GPU 0: x"')
    caja.env["BB_DMEM_ETAPA_MARCA"] = str(caja.tmp / "no-instalada")
    r = _dmem(caja, "guardia")
    assert r.returncode == 0 and "la decision guardia-dmem-gpu-ok no queda como etapa" in r.stdout


def test_retrocede_kernel_x_solo_toca_updates_de_x(caja: Caja):
    x = caja.instalado("7.0.0-1019-nvidia")
    y = caja.instalado("6.17.0-1032-nvidia")
    r = _dmem(caja, "retrocede", "--kernel", "7.0.0-1019-nvidia")
    assert r.returncode == 0, r.stdout
    assert not any(k.exists() for k in x) and not (caja.mods / "7.0.0-1019-nvidia" / "updates").exists()
    assert all(k.exists() for k in y) and caja.depmod() == ["-a 7.0.0-1019-nvidia"]
    queda = (caja.estado / "instalados.txt").read_text(encoding="utf-8")
    assert sorted(ln.split()[1] for ln in queda.splitlines()) == sorted(str(k) for k in y)
    assert "quedan 5 archivos de OTRO kernel" in r.stdout
    r = _dmem(caja, "retrocede", "--kernel", "6.17.0-1032-nvidia")
    assert r.returncode == 0 and not (caja.estado / "instalados.txt").exists() and not any(k.exists() for k in y)
    assert caja.depmod() == ["-a 7.0.0-1019-nvidia", "-a 6.17.0-1032-nvidia"]


def test_retrocede_sin_kernel_es_el_que_corre(caja: Caja):
    otro = caja.instalado("0.0.0-otro")
    propio = caja.instalado(KERNEL)
    assert _dmem(caja, "retrocede").returncode == 0
    assert not any(k.exists() for k in propio) and all(k.exists() for k in otro) and caja.depmod() == [f"-a {KERNEL}"]


def test_retrocede_kernel_sin_updates_sale_limpio_sin_tocar_nada(caja: Caja):
    caja.instalado("6.17.0-1032-nvidia")
    (caja.mods / "7.0.0-1019-nvidia").mkdir()
    antes = (caja.estado / "instalados.txt").read_bytes()
    r = _dmem(caja, "retrocede", "--kernel", "7.0.0-1019-nvidia")
    assert r.returncode == 0 and "no tiene updates/" in r.stdout
    assert (caja.estado / "instalados.txt").read_bytes() == antes and caja.depmod() == []


def test_retrocede_kernel_con_un_archivo_alterado_no_lo_borra_y_falla(caja: Caja):
    x = caja.instalado("7.0.0-1019-nvidia")
    y = caja.instalado("6.17.0-1032-nvidia")
    x[0].write_bytes(b"alterado")
    r = _dmem(caja, "retrocede", "--kernel", "7.0.0-1019-nvidia")
    assert r.returncode == 1 and "retroceso INCOMPLETO" in r.stdout and "depmod -a 7.0.0-1019-nvidia" in r.stdout
    assert x[0].exists() and not any(k.exists() for k in x[1:]) and all(k.exists() for k in y)
    queda = [ln.split()[1] for ln in (caja.estado / "instalados.txt").read_text(encoding="utf-8").splitlines()]
    assert sorted(queda) == sorted(str(k) for k in [x[0], *y])


@pytest.mark.parametrize("args,mensaje", [(["--kernel", "../../etc"], "version de kernel invalida"),
                                          (["--kernel"], "uso: retrocede"), (["7.0"], "uso: retrocede")])
def test_retrocede_rechaza_un_kernel_mal_dado(caja: Caja, args: list[str], mensaje: str):
    caja.instalado(KERNEL)
    r = _dmem(caja, "retrocede", *args)
    assert r.returncode == 1 and mensaje in r.stdout and caja.depmod() == []


def test_estado_kernel_muestra_updates_de_ese_kernel(caja: Caja):
    x = caja.instalado("7.0.0-1019-nvidia")
    r = _dmem(caja, "estado", "--kernel", "7.0.0-1019-nvidia")
    assert r.returncode == 0 and "elegido: 7.0.0-1019-nvidia" in r.stdout
    assert hashlib.sha256(x[0].read_bytes()).hexdigest() in r.stdout
    r = _dmem(caja, "estado", "--kernel", "6.17.0-1032-nvidia")
    assert r.returncode == 0 and "6.17.0-1032-nvidia no tiene updates/" in r.stdout


# --- instala: cada .ko firmado CON la llave enrolada ------------------------------------------------------------

def _firmados(caja: Caja, sig: dict[str, str | None], serie_llave: str | None = "0A1B2C3D") -> None:
    """firmados/<m>.ko con su sig_key (None = sin firma); openssl de mentira da la serie de la llave."""
    d = caja.estado / "firmados"
    d.mkdir()
    for m in MODS:
        (d / f"{m}.ko").write_bytes(m.encode())
        if sig.get(m, "0a:1b:2c:3d") is not None:
            (d / f"{m}.ko.sig").write_text(str(sig.get(m, "0a:1b:2c:3d")) + "\n", encoding="utf-8")
    _ejecutable(caja.bin / "modinfo", '#!/bin/sh\n[ "$1 $2" = "-F sig_key" ] || exit 1\ncat "$3.sig" 2>/dev/null\n')
    salida = f'echo "serial={serie_llave}"' if serie_llave is not None else "exit 1"
    _ejecutable(caja.bin / "openssl", f"#!/bin/sh\n{salida}\n")
    caja.env["BB_DMEM_LLAVE_PUB"] = str(caja.tmp / "MOK.der")


def test_instala_con_los_cinco_firmados_por_la_llave(caja: Caja):
    _firmados(caja, {"nvidia": "00:0A:1B:2C:3D"})  # cero inicial y minusculas: la misma serie
    r = _dmem(caja, "instala")
    assert r.returncode == 0, r.stdout
    assert "los 5 modulos estan firmados con" in r.stdout and "(serie A1B2C3D)" in r.stdout
    assert sorted(p.name for p in (caja.mods / KERNEL / "updates").iterdir()) == sorted(f"{m}.ko" for m in MODS)
    assert len((caja.estado / "instalados.txt").read_text(encoding="utf-8").splitlines()) == 5
    assert caja.depmod() == [f"-a {KERNEL}"]


@pytest.mark.parametrize("sig,serie,mensaje", [
    ({"nvidia-uvm": "FF:EE"}, "0A1B2C3D", "ATENCION: nvidia-uvm.ko esta firmado con la llave de serie FFEE"),
    ({"nvidia-drm": None}, "0A1B2C3D", "nvidia-drm.ko NO esta firmado"),
    ({}, None, "no pude leer la serie"),
])
def test_control_negativo_instala_se_niega_si_la_firma_no_es_de_la_llave(caja: Caja, sig: dict[str, str | None],
                                                                          serie: str | None, mensaje: str):
    _firmados(caja, sig, serie)
    r = _dmem(caja, "instala")
    assert r.returncode == 1 and mensaje in r.stdout and "no firmo la llave enrolada" in r.stdout
    assert not (caja.mods / KERNEL / "updates").exists() and not (caja.estado / "instalados.txt").exists()


# --- la unidad que genera instala -------------------------------------------------------------------------------

def _unidad_generada() -> str:
    m = re.search(r'cat >"\$nueva" <<UNIT\n(.*?)\nUNIT\n', SCRIPT.read_text(encoding="utf-8"), re.S)
    assert m is not None
    return m.group(1).replace('$(readlink -f "${BASH_SOURCE[0]}")', str(SCRIPT))


def test_la_unidad_de_la_guardia_tiene_tope_y_no_espera_a_multi_user(tmp_path: Path):
    c = configparser.ConfigParser(interpolation=None)
    c.optionxform = str  # pyright: ignore[reportAttributeAccessIssue]  # systemd distingue mayusculas
    c.read_string(_unidad_generada())
    assert c["Service"]["TimeoutStartSec"] == "300" and c["Unit"]["DefaultDependencies"] == "no"
    assert c["Install"]["WantedBy"] == "basic.target" and "multi-user" not in _unidad_generada()
    assert c["Service"]["ExecStart"] == f"/bin/bash {SCRIPT} guardia"
    # 300 s cubren el plazo, el ultimo nvidia-smi, la pausa y el retroceso
    texto = SCRIPT.read_text(encoding="utf-8")
    assert "GUARDIA_PLAZO=${BB_DMEM_GUARDIA_PLAZO:-120}" in texto and "NVSMI_TIMEOUT=${BB_DMEM_NVSMI_TIMEOUT:-10}" in texto


@pytest.mark.skipif(shutil.which("systemd-analyze") is None, reason="systemd-analyze no disponible")
def test_la_unidad_de_la_guardia_pasa_systemd_analyze_verify(tmp_path: Path):
    u = tmp_path / "bb-dmem-guardia.service"
    u.write_text(_unidad_generada() + "\n", encoding="utf-8")
    r = subprocess.run(["systemd-analyze", "verify", str(u)], capture_output=True, text=True, timeout=60, check=False)
    assert r.stdout + r.stderr == ""
    u.write_text(_unidad_generada().replace("TimeoutStartSec", "TimeoutStarSec") + "\n", encoding="utf-8")
    r = subprocess.run(["systemd-analyze", "verify", str(u)], capture_output=True, text=True, timeout=60, check=False)
    assert "Unknown key name 'TimeoutStarSec'" in r.stdout + r.stderr  # control negativo: el criterio puede fallar
