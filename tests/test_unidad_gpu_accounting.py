"""La unidad pendiente que reaplica `nvidia-smi -am 1` en cada arranque (DEBT-GPU-ACCOUNTING-MODE-APAGADO-01)."""

from pathlib import Path

UNIDAD = Path(__file__).resolve().parent.parent / "adopted/system-config/etc_systemd_system_bb-gpu-accounting.service"
RELOJ = Path(__file__).resolve().parent.parent / "adopted/system-config/etc_systemd_system_atom-clock-lock.service"


def _claves(texto: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for ln in texto.splitlines():
        if "=" in ln and not ln.startswith("["):
            k, v = ln.split("=", 1)
            out.setdefault(k, []).append(v)
    return out


def test_la_unidad_enciende_el_accounting_tras_persistenced_y_sobrevive_al_arranque():
    c = _claves(UNIDAD.read_text(encoding="utf-8"))
    assert c["ExecStart"] == ["/usr/bin/nvidia-smi -am 1"]
    assert c["Type"] == ["oneshot"] and c["WantedBy"] == ["multi-user.target"]
    assert c["After"] == ["nvidia-persistenced.service"]


def test_control_negativo_la_unidad_no_apaga_el_accounting_ni_toca_el_clock():
    """Misma comprobacion contra la unidad hermana de clock: sus argumentos son otros, asi que el test distingue."""
    c = _claves(RELOJ.read_text(encoding="utf-8"))
    assert c["ExecStart"] != _claves(UNIDAD.read_text(encoding="utf-8"))["ExecStart"]
    assert "-am 0" not in UNIDAD.read_text(encoding="utf-8") and "-lgc" not in UNIDAD.read_text(encoding="utf-8")
