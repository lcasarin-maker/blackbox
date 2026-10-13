from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from tools import gpumem_historial as h

T0 = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
BOOT = "boot-a"


def inf(*hojas: tuple[str, float], total: float | None = None) -> dict[str, Any]:
    return {"estado": "OK", "cobrado_total_gib": sum(g for _, g in hojas) if total is None else total, "hojas": [{"quien": q, "ruta": q, "gib": g} for q, g in hojas]}


SIN = {"estado": "SIN_REGION", "motivo": "dmem.capacity vacio"}


def primera(informe: dict[str, Any], ahora: datetime = T0, boot: str = BOOT) -> dict[str, Any]:
    fila = h.decide_fila(None, informe, ahora, boot)
    assert fila is not None
    return fila


def test_sin_previa_escribe() -> None:
    f = primera(inf(("a", 10.0)))
    assert f["estado"] == "OK" and f["hojas"] == [{"quien": "a", "gib": 10.0}] and f["pico_por_quien"] == {"a": 10.0}
    assert "termino" not in f


def test_sin_cambio_y_menos_de_10_min_no_escribe() -> None:
    previa = primera(inf(("a", 10.0)))
    assert h.decide_fila(previa, inf(("a", 10.1)), T0 + timedelta(minutes=9), BOOT) is None
    # control negativo: el mismo caso con 10 min exactos SI escribe
    assert h.decide_fila(previa, inf(("a", 10.1)), T0 + timedelta(minutes=10), BOOT) is not None


def test_cambio_de_025_gib_escribe_y_menos_no() -> None:
    previa = primera(inf(("a", 10.0), ("b", 5.0)))
    assert h.decide_fila(previa, inf(("a", 10.0), ("b", 5.24)), T0 + timedelta(minutes=1), BOOT) is None
    f = h.decide_fila(previa, inf(("a", 10.0), ("b", 5.25)), T0 + timedelta(minutes=1), BOOT)
    assert f is not None and f["pico_por_quien"] == {"a": 10.0, "b": 5.25}


def test_cambio_del_total_escribe() -> None:
    previa = primera(inf(("a", 10.0), total=10.0))
    f = h.decide_fila(previa, inf(("a", 10.0), total=10.5), T0 + timedelta(minutes=1), BOOT)
    assert f is not None


def test_hoja_nueva_escribe() -> None:
    previa = primera(inf(("a", 10.0)))
    f = h.decide_fila(previa, inf(("a", 10.0), ("b", 0.01), total=10.0), T0 + timedelta(minutes=1), BOOT)
    assert f is not None and len(f["hojas"]) == 2


def test_pico_por_boot_id() -> None:
    f1 = primera(inf(("a", 20.0)))
    f2 = h.decide_fila(f1, inf(("a", 5.0)), T0 + timedelta(minutes=1), BOOT)
    assert f2 is not None and f2["pico_por_quien"] == {"a": 20.0}
    otro = h.decide_fila(f2, inf(("a", 3.0)), T0 + timedelta(minutes=2), "boot-b")
    assert otro is not None and otro["pico_por_quien"] == {"a": 3.0}


def test_hoja_que_desaparece_genera_termino() -> None:
    f1 = primera(inf(("a", 20.0), ("b", 4.0)))
    f2 = h.decide_fila(f1, inf(("a", 20.0)), T0 + timedelta(minutes=1), BOOT)
    assert f2 is not None
    assert f2["termino"] == [{"quien": "b", "ultimo_gib": 4.0, "pico_gib": 4.0, "motivo": "desconocido"}]


def test_sin_region_registra_sin_cifras_y_limita_a_una_cada_10_min() -> None:
    f1 = primera(SIN)
    assert f1["estado"] == "SIN_REGION" and "cobrado_total_gib" not in f1 and "hojas" not in f1
    assert h.decide_fila(f1, SIN, T0 + timedelta(minutes=9), BOOT) is None
    assert h.decide_fila(f1, SIN, T0 + timedelta(minutes=10), BOOT) is not None


def test_sin_region_explica_el_fin() -> None:
    f1 = primera(inf(("a", 7.0)))
    f2 = h.decide_fila(f1, SIN, T0 + timedelta(minutes=1), BOOT)
    assert f2 is not None and f2["termino"][0]["motivo"] == "SIN_REGION" and f2["termino"][0]["ultimo_gib"] == 7.0


def test_cambio_de_estado_escribe() -> None:
    previa = primera(SIN)
    assert h.decide_fila(previa, inf(("a", 1.0)), T0 + timedelta(minutes=1), BOOT) is not None


def test_previa_con_ts_ilegible_escribe() -> None:
    previa = {**primera(inf(("a", 1.0))), "ts": "basura"}
    assert h.decide_fila(previa, inf(("a", 1.0)), T0 + timedelta(minutes=1), BOOT) is not None


def test_paso_off_no_escribe(tmp_path: Path) -> None:
    ruta = tmp_path / "h.jsonl"
    assert h.paso("off", ruta, toma=lambda r: inf(("a", 1.0)), ahora=T0, boot_id=BOOT) is None
    assert not ruta.exists()


def test_paso_actuar_es_unsupported(tmp_path: Path) -> None:
    ruta = tmp_path / "h.jsonl"
    r = h.paso("actuar", ruta, toma=lambda r: inf(("a", 1.0)), ahora=T0, boot_id=BOOT)
    assert r is not None and r["estado"] == "UNSUPPORTED" and not ruta.exists()


def test_paso_observar_escribe_y_no_duplica(tmp_path: Path) -> None:
    ruta = tmp_path / "sub" / "h.jsonl"
    kw: dict[str, Any] = {"ruta": ruta, "toma": lambda r: inf(("a", 1.0)), "boot_id": BOOT}
    assert h.paso("observar", ahora=T0, **kw) is not None
    assert h.paso("observar", ahora=T0 + timedelta(minutes=1), **kw) is None
    assert len(ruta.read_text(encoding="utf-8").splitlines()) == 1


def test_paso_lee_boot_id_del_sistema(tmp_path: Path) -> None:
    f = h.paso("observar", tmp_path / "h.jsonl", toma=lambda r: inf(("a", 1.0)), ahora=T0)
    assert f is not None and f["boot_id"] == h.BOOT_ID.read_text(encoding="utf-8").strip()


def test_resumen_y_filas_ilegibles(tmp_path: Path) -> None:
    ruta = tmp_path / "h.jsonl"
    assert h.resumen(ruta) == {"filas": 0, "picos_por_quien": {}, "ultimo_estado": None}
    f = primera(inf(("a", 2.0)))
    ruta.write_text("basura\n[1]\n" + json.dumps(f) + "\n", encoding="utf-8")
    assert h.resumen(ruta) == {"filas": 1, "picos_por_quien": {"a": 2.0}, "ultimo_estado": "OK"}


def test_ruta_por_defecto(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    assert h.ruta_por_defecto() == tmp_path / "gpumem_historial.jsonl"


def test_main_resumen_y_paso(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    assert h.main([]) == 0
    assert json.loads(capsys.readouterr().out)["filas"] == 0
    (tmp_path / "interruptores.json").write_text(json.dumps({"modos": {h.NOMBRE: "observar"}}), encoding="utf-8")
    monkeypatch.setattr(h.gpumem, "informe", lambda raiz, docker=None: SIN)
    monkeypatch.setattr(h, "paso", lambda modo, **k: h.decide_fila(None, SIN, T0, BOOT) if modo == "observar" else None)
    assert h.main(["--paso"]) == 0
    assert json.loads(capsys.readouterr().out)["estado"] == "SIN_REGION"
