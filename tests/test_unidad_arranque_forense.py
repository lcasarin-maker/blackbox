"""La unidad de usuario que dispara `bb-root-run arranque-forense` en cada arranque (FEATURE-LECTOR-PSTORE-BERT-ROOT-01)."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
UNIDAD = RAIZ / "systemd/bb-arranque-forense.service"
SUDOERS = RAIZ / "adopted/pendiente-de-despliegue/etc_sudoers.d_bb-root-run"


def test_la_unidad_llama_solo_al_ejecutor_sellado_con_un_nombre_del_manifiesto():
    ln = [x for x in UNIDAD.read_text(encoding="utf-8").splitlines() if x.startswith("ExecStart=")]
    assert ln == ["ExecStart=/usr/bin/sudo -n /usr/local/sbin/bb-root-run arranque-forense"]
    manifiesto = (RAIZ / "adopted/root-scripts/manifest.src.json").read_text(encoding="utf-8")
    assert '"arranque-forense"' in manifiesto


def test_control_negativo_la_regla_de_sudo_deja_pasar_ese_nombre_y_rechaza_los_demas():
    import re
    patron = re.search(r"bb-root-run (\^.*\$)", SUDOERS.read_text(encoding="utf-8"))
    assert patron is not None
    assert re.fullmatch(patron.group(1), "arranque-forense")
    assert not re.fullmatch(patron.group(1), "../arranque-forense") and not re.fullmatch(patron.group(1), "a b")
