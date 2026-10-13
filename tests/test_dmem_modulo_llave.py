"""dmem_modulo.sh: la comprobacion de llave enrolada debe sobrevivir a que mokutil --test-key salga 1."""

from __future__ import annotations

import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "tools" / "dmem_modulo.sh"


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
