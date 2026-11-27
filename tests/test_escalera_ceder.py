"""Pruebas de escalera ceder -> congelar -> detener verificada por caida de memory.current."""
from __future__ import annotations

import json
from pathlib import Path

from tools import portero

REPO = Path(__file__).resolve().parents[1]


def escalar_alivio(
    unidad: str,
    memory_current_antes: int,
    memory_current_despues_ceder: int,
    caida_minima: int,
    protegidas: set[str],
    congelar_fn,
    detener_fn,
) -> str:
    """Escala ceder -> congelar -> detener solo si memory.current no cayo; nunca detiene protegidas."""
    if memory_current_antes - memory_current_despues_ceder >= caida_minima:
        return "cedio"
    congelar_fn(unidad)
    if unidad in protegidas:
        return "congelada_protegida"
    detener_fn(unidad)
    return "detenida"


def test_escala_solo_si_memory_current_no_cayo() -> None:
    acciones: list[str] = []
    res = escalar_alivio(
        "trabajo.scope", 500_000, 490_000, 100_000, set(),
        lambda u: acciones.append(f"congelar:{u}"),
        lambda u: acciones.append(f"detener:{u}"),
    )
    assert res == "detenida"
    assert acciones == ["congelar:trabajo.scope", "detener:trabajo.scope"]


def test_control_negativo_unidad_que_cede_no_se_congela_ni_detiene() -> None:
    acciones: list[str] = []
    res = escalar_alivio(
        "trabajo.scope", 500_000, 300_000, 100_000, set(),
        lambda u: acciones.append(f"congelar:{u}"),
        lambda u: acciones.append(f"detener:{u}"),
    )
    assert res == "cedio"
    assert acciones == []


def test_unidad_protegida_nunca_se_detiene() -> None:
    data = json.loads((REPO / "data/procesos_protegidos.json").read_text(encoding="utf-8"))
    protegidas = {x["patron"] for x in data.get("unidades", [])} | {x["nombre"] for x in data.get("comm", [])}
    assert protegidas
    assert hasattr(portero, "decide")
    acciones: list[str] = []
    muestra = next(iter(protegidas))
    res = escalar_alivio(
        muestra, 500_000, 495_000, 100_000, protegidas,
        lambda u: acciones.append(f"congelar:{u}"),
        lambda u: acciones.append(f"detener:{u}"),
    )
    assert res == "congelada_protegida"
    assert acciones == [f"congelar:{muestra}"]
