"""bb scan debe leer el kernel de TODOS los boots de la ventana, no solo el actual.

`journalctl -k` implica `-b`: una ventana que cruza un reinicio ignoraba en
silencio los Xid, OOM y registros BERT de los boots anteriores. Medido el
2026-10-10 sobre la misma ventana: `-k` contaba 0 registros BERT y
`_TRANSPORT=kernel` contaba 3. El journalctl falso de aqui solo contesta al
selector que cruza boots, como el real: si bb vuelve a `-k`, estas pruebas caen.
"""
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

BERT = """2026-10-05T00:31:50-06:00 h kernel: BERT: Error records from previous boot:
2026-10-05T00:31:50-06:00 h kernel: [Hardware Error]:   00000010: 00000000 00000010 00000022 56190000
2026-10-06T16:50:26-06:00 h kernel: BERT: Error records from previous boot:
2026-10-06T16:50:26-06:00 h kernel: [Hardware Error]:   00000010: 00000000 00000100 00000022 56190000
2026-10-07T16:55:42-06:00 h kernel: audit: audit_backlog=8193 > audit_backlog_limit=8192
2026-10-07T16:55:42-06:00 h kernel: audit: audit_lost=2662 audit_rate_limit=0 audit_backlog_limit=8192
"""


def _scan(tmp_path, kernel_texto):
    mock = tmp_path / "mockbin"
    mock.mkdir()
    (tmp_path / "kernel.txt").write_text(kernel_texto, encoding="utf-8")
    j = mock / "journalctl"
    j.write_text('#!/bin/sh\ncase "$*" in *_TRANSPORT=kernel*) cat "%s/kernel.txt" ;; esac\nexit 0\n' % tmp_path,
                 encoding="utf-8")
    j.chmod(0o755)
    d = tmp_path / "datos"
    (d / "samples").mkdir(parents=True)
    env = {**os.environ, "BLACKBOX_DATA": str(d), "PATH": f"{mock}{os.pathsep}{os.environ['PATH']}"}
    return subprocess.run([str(RAIZ / "bin/bb"), "scan", "2026-10-04 23:00"],
                          capture_output=True, text=True, env=env, timeout=120).stdout


def test_scan_cuenta_los_registros_bert_de_boots_anteriores(tmp_path):
    s = _scan(tmp_path, BERT)
    assert "registros BERT del firmware (corte sin apagado): 2" in s
    assert "palabra@0x14=00000100" in s and "palabra@0x14=00000010" in s


def test_scan_informa_el_audit_perdido(tmp_path):
    assert "eventos de audit perdidos (anillo desbordado): 2662" in _scan(tmp_path, BERT)


def test_control_negativo_sin_registros_bert_dice_cero_y_no_inventa(tmp_path):
    s = _scan(tmp_path, "2026-10-05T00:00:00-06:00 h kernel: todo normal\n")
    assert "registros BERT del firmware (corte sin apagado): 0" in s
    assert "palabra@0x14" not in s
