"""Caducidad de las slices de prueba de oomd (voto de Luis, 2026-11-18: versionarlas con caducidad de 30 dias).

Una suspension o una excepcion sin fecha se vuelve permanente en silencio (contrato de suspension). Aqui la fecha la
vigila la suite: el 2026-12-18 este test se pone rojo y obliga a elegir entre retirar las slices o renovarlas con ficha.
`vencidas` es pura (recibe el dia) para que el caso rojo se pueda correr hoy, y no solo cuando llegue la fecha.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CADUCA = date(2026, 12, 18)
SLICES = ("bbtest-oomd.slice", "bbtest-oomd-neg.slice")


def vencidas(hoy: date, repo: Path = REPO) -> list[str]:
    return [s for s in SLICES if (repo / "adopted" / "systemd-user" / s).exists() and hoy > CADUCA]


def test_las_slices_de_prueba_no_estan_vencidas() -> None:
    assert not vencidas(date.today()), (
        f"caducaron el {CADUCA}: retirar adopted/systemd-user/bbtest-oomd*.slice y las de ~/.config/systemd/user "
        "(DEBT-SLICES-OOMD-DE-PRUEBA-CADUCAN-2026-12-18-01), o renovar con ficha y mover CADUCA y las filas de SPEC.md")


def test_control_negativo_pasada_la_fecha_las_dos_estan_vencidas() -> None:
    assert vencidas(date(2026, 12, 19)) == list(SLICES)


def test_control_negativo_el_dia_de_la_fecha_aun_no_vencen() -> None:
    assert vencidas(CADUCA) == []


def test_control_negativo_retiradas_no_hay_nada_que_vencer(tmp_path: Path) -> None:
    assert vencidas(date(2027, 1, 1), tmp_path) == []


def test_la_fecha_del_test_es_la_de_las_filas_de_spec() -> None:
    """Renovar solo el test sin tocar SPEC.md (o al reves) deja la caducidad mintiendo."""
    filas = [l for l in (REPO / "SPEC.md").read_text(encoding="utf-8").splitlines() if "bbtest-oomd" in l]
    assert len(filas) == 2 and all(CADUCA.isoformat() in l for l in filas), filas
