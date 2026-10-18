"""Controles de `tools/guardia_pii.py`. Los datos sinteticos se arman aqui; el arbol no los contiene."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools import guardia_pii as gp

ROOT = Path(__file__).resolve().parents[1]
# valores con la FORMA de un dato personal, armados en ejecucion para que ningun archivo versionado los lleve
RFC_PERSONA = "GARC" + "800101" + "AB2"
CURP_PERSONA = "GARC" + "800101" + "HDFRRL" + "09"
CORREO_PERSONA = "nombre.apellido" + "@" + "empresa.com.mx"
TELEFONO_PERSONA = "55" + "-" + "1234" + "-" + "5678"


@pytest.mark.parametrize("texto,tipo", [
    (f"cliente {RFC_PERSONA} pago", "rfc"),
    (f"curp {CURP_PERSONA}", "curp"),
    (f"escribir a {CORREO_PERSONA} hoy", "correo"),
    (f"llamar al {TELEFONO_PERSONA}", "telefono"),
    ("persona" + "@" + "nvidia.com", "correo"),  # el dominio de NVIDIA no exime a una persona
    ("persona" + "@" + "mi-example.com", "correo"),  # `mi-example.com` no es un dominio reservado
    ("+52 55 " + "1234 5678", "telefono"),
    ("(55) " + "1234-5678", "telefono"),
])
def test_el_dato_personal_se_detecta(texto: str, tipo: str):
    assert tipo in {t for _, t, _ in gp.hallazgos_texto(texto)}


@pytest.mark.parametrize("texto", [
    "RFC generico XAXX" + "010101000 oficial",
    "etiqueta cudatools" + "@" + "nvidia.com del Release firmado",
    "user" + "@" + "1000.service y getty" + "@" + "tty1.service",
    "icons-64x64" + "@" + "2.tar.gz",
    "alguien" + "@" + "example.com en la documentacion",
    "nombre" + "@" + "empresa.example.com y soporte" + "@" + "contacto.invalid y op" + "@" + "recovery.example",
    "https://usuario" + "@" + "repo.nvidia.com/ubuntu",
    "Maintainer: dgxdev" + "@" + "nvidia.com",
    "ffff 10.100000 S Co:1:002:0 s 21 01 0100 0000 0000 0",   # traza USB
    "BW average[MB/sec] 1024 10 1000 1000",                   # ancho de banda
    "ver DEBT-" + "ABCD" + "010101" + "XY9 del backlog",
    "numero de pid 12345 y puerto 8000 y 4096 bytes",
    "version 580.178.04 del driver, kernel 6.17.0-1032",
])
def test_lo_legitimo_no_se_marca(texto: str):
    assert gp.hallazgos_texto(texto) == []


def test_el_valor_nunca_se_imprime_completo(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    f = tmp_path / "nota.md"
    f.write_text(f"contacto {CORREO_PERSONA}\n", encoding="utf-8")
    assert gp.main([str(f)]) == 1
    salida = capsys.readouterr().err
    assert CORREO_PERSONA not in salida and "correo" in salida


def test_sin_archivos_ni_arbol_no_examina_nada(capsys: pytest.CaptureFixture[str]):
    assert gp.main([]) == 0
    assert "archivos=0" in capsys.readouterr().out


def test_un_archivo_limpio_sale_0(tmp_path: Path):
    f = tmp_path / "limpio.md"
    f.write_text("solo texto tecnico, nada personal\n", encoding="utf-8")
    assert gp.main([str(f)]) == 0


def test_fuera_de_un_repo_git_es_could_not_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert gp.main(["--arbol"], raiz=tmp_path) == 2
    assert "COULD_NOT_RUN" in capsys.readouterr().err


def test_las_unidades_de_systemd_de_este_repo_no_traen_pii():
    """Sustituye al escaner del kit sobre `systemd/`: las unidades con instancia (`x@1000.service`) no son correos."""
    archivos = [str(p) for p in sorted((ROOT / "systemd").rglob("*")) if p.is_file()]
    assert archivos, "no hay unidades que examinar"
    assert gp.main(archivos) == 0


def test_el_arbol_versionado_de_este_repo_no_trae_pii():
    r = subprocess.run(["python3", "-m", "tools.guardia_pii", "--arbol"], cwd=ROOT, capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr[-1500:]
