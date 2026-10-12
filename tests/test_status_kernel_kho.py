"""`bb status` y la regresion del kernel 7.0.0-1019 (KHO deja CmaTotal en 0).

FEATURE-BB-PREFLIGHT-KERNEL-KHO-01. Cada caso redirige /proc con BB_PROC_DIR:
el que DEBE avisar y el que NO, mas el ilegible, que debe decir NOT_COLLECTED y
no ARMADO.
"""

import pytest

from test_bb_bash import correr

FILA = "kernel sin la regresion KHO/CMA"
MALO = "Linux version 7.0.0-1019-nvidia (buildd@x) #19 SMP\n"
SANO = "Linux version 6.17.0-1032-nvidia (buildd@x) #32 SMP\n"
CMA_OK = "MemTotal: 1 kB\nCmaTotal:         131072 kB\n"
CMA_0 = "MemTotal: 1 kB\nCmaTotal:              0 kB\n"


@pytest.fixture
def datos(tmp_path):
    d = tmp_path / "blackbox"
    (d / "samples").mkdir(parents=True)
    return d


def _fila(datos, tmp_path, version, cmdline, meminfo):
    p = tmp_path / "proc"
    p.mkdir()
    for nombre, texto in (("version", version), ("cmdline", cmdline), ("meminfo", meminfo)):
        if texto is not None:
            (p / nombre).write_text(texto, encoding="utf-8")
    r = correr(["status"], datos, {"BB_PROC_DIR": str(p)})
    lineas = r.stdout.splitlines()
    i = next(i for i, l in enumerate(lineas) if FILA in l)
    return lineas[i] + " " + lineas[i + 1], r.stdout


def test_kernel_malo_SIN_kho_off_dice_KERNEL_CONOCIDO_MALO(datos, tmp_path):
    fila, _ = _fila(datos, tmp_path, MALO, "BOOT_IMAGE=/vmlinuz root=/dev/x\n", CMA_0)
    assert "FALTA" in fila and "KERNEL_CONOCIDO_MALO" in fila and "AUSENTE" in fila, fila


def test_kernel_malo_CON_kho_off_y_CMA_sano_esta_ARMADO(datos, tmp_path):
    fila, _ = _fila(datos, tmp_path, MALO, "root=/dev/x kho=off quiet\n", CMA_OK)
    assert "ARMADO" in fila, fila


def test_kernel_malo_CON_kho_off_pero_CMA_en_0_sigue_MALO(datos, tmp_path):
    """El post #44 del hilo: el caso que persiste con kho=off."""
    fila, _ = _fila(datos, tmp_path, MALO, "root=/dev/x kho=off\n", CMA_0)
    assert "KERNEL_CONOCIDO_MALO" in fila and "CmaTotal=0" in fila, fila


def test_control_negativo_kernel_sano_6_17_no_avisa(datos, tmp_path):
    fila, _ = _fila(datos, tmp_path, SANO, "root=/dev/x\n", CMA_0)
    assert "ARMADO" in fila and "KERNEL_CONOCIDO_MALO" not in fila, fila


def test_control_negativo_kho_off_como_subcadena_no_cuenta(datos, tmp_path):
    fila, _ = _fila(datos, tmp_path, MALO, "root=/dev/x kho=offline\n", CMA_OK)
    assert "KERNEL_CONOCIDO_MALO" in fila, fila


@pytest.mark.parametrize("version,cmdline,meminfo", [
    (None, "root=/dev/x\n", CMA_OK),            # /proc/version ilegible
    (MALO, None, CMA_OK),                       # cmdline ilegible en el kernel malo
    (MALO, "kho=off\n", "MemTotal: 1 kB\n"),    # sin CmaTotal en el kernel malo
])
def test_control_negativo_lo_ilegible_es_NOT_COLLECTED_y_no_ARMADO(datos, tmp_path, version, cmdline, meminfo):
    fila, salida = _fila(datos, tmp_path, version, cmdline, meminfo)
    assert "CIEGO" in fila and "NOT_COLLECTED" in fila and "ARMADO" not in fila, fila
    assert "could_not_run: 0" not in salida, salida
