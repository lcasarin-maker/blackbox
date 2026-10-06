"""Cierre de DEBT-COBERTURA-PISO-REBAJADO-01: el piso vuelve a 100 % solo al cerrar las fichas xfail."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_piso_de_cobertura_vuelve_a_100():
    assert (ROOT / ".coverage_watermark").read_text(encoding="utf-8").strip() == "100.00"
