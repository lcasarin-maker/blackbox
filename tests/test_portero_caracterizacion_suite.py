"""Caracterizacion de la clase `suite` del portero: lo que decide y registra, congelado ANTES de anadir otra clase.

DEBT-PORTERO-NO-CLASIFICA-TANDAS-DE-LIBREOFFICE-DE-OTROS-PROYECTOS-01 anade una clase nueva (en `observar`). La
clase `suite` tiene que seguir igual byte a byte: `tests/fixtures/portero_suite_caracterizacion.json` se grabo con
`tools/portero.py` SIN modificar (commit 6ed1d1d0) corriendo `escenarios()`; este test lo compara campo a campo.
Regrabar el fixture (`python3 -m tests.test_portero_caracterizacion_suite`) solo si un cambio de `suite` es
deliberado y votado; nunca para que pase.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from tools import portero as po

G = po.GIB_KB
APP = "/user.slice/user-1000.slice/user@1000.service/app.slice"
CLAUDE = APP + "/app-com.anthropic.Claude-1.scope"
FIXTURE = Path(__file__).parent / "fixtures" / "portero_suite_caracterizacion.json"


def _estado(psi: float | None = 0.0, freno: str | None = "", tope: int | None = 42 * G, uso: int | None = 30 * G,
            consumo: int = 0) -> po.Estado:
    return po.Estado(psi, freno, tope, uso, (), consumo)


def _arbol(raiz: int, edad: float, rss: int = 10 * G, cgroup: str = CLAUDE, **kw: Any) -> po.Arbol:
    return po.Arbol(raiz=raiz, clase="suite", rss_kb=rss, procesos=5, edad_s=edad, cgroup=cgroup, **kw)


def _corriendo() -> po.Arbol:
    return _arbol(1, 600, unidad="bb-portero-suite-1.scope")


ESCENARIOS: dict[str, tuple[list[po.Arbol] | None, po.Estado]] = {
    "admite_uno": ([_arbol(1, 60)], _estado()),
    "cola_dos_congela_al_nuevo": ([_arbol(1, 30), _arbol(2, 60)], _estado()),
    "cola_tres": ([_arbol(1, 10), _arbol(2, 90), _arbol(3, 50)], _estado()),
    "turno_ocupado_congela_al_nuevo": ([_corriendo(), _arbol(2, 60)], _estado()),
    "al_liberarse_descongela_al_mas_antiguo": ([
        _arbol(2, 60, unidad="bb-portero-suite-2.scope", congelado=True),
        _arbol(3, 120, unidad="bb-portero-suite-3.scope", congelado=True)], _estado()),
    "index_lock_no_se_congela": ([_corriendo(), _arbol(2, 60, ancestros=(
        "/bin/sh .git/hooks/pre-commit", "git commit -m x", "bash"))], _estado()),
    "pre_push_si_se_congela": ([_corriendo(), _arbol(2, 60, ancestros=(
        "pre-commit run --hook-stage pre-push", "git push origin master"))], _estado()),
    "fuera_de_app_slice": ([_arbol(1, 60, cgroup="/system.slice/x.service"),
                            _arbol(2, 60, cgroup="/user.slice/user-1000.slice/session-2.scope")], _estado()),
    "ligero_no_se_toca": ([_arbol(1, 60, rss=po.UMBRAL_RSS_SUITE_KB - 1)], _estado()),
    "psi_alto": ([_arbol(1, 60)], _estado(psi=50.0)),
    "freno_termico": ([_arbol(1, 60)], _estado(freno="estado termico 'sostenida'")),
    "holgura_baja": ([_arbol(1, 60)], _estado(uso=42 * G - po.HOLGURA_MIN_KB + 1)),
    "presupuesto_por_tope_propio": ([_arbol(1, 60)], _estado(consumo=23 * G)),
    "excluido_atlas": ([_arbol(1, 60, cgroup=APP + "/liberation_job.scope")], _estado()),
    "sin_medir": ([_arbol(1, 60)], _estado(psi=None)),
    "proc_ilegible": (None, _estado()),
}


def _sin_volatiles(fila: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in fila.items() if k != "ts"}


def escenarios(tmp: Path) -> dict[str, Any]:
    """Lo que el portero decide en cada escenario y lo que `aplica` registra en `observar`, `off` y `actuar`.

    En `actuar` los arboles no se pasan: cada accion con efecto queda como `arbol no observado` (rc=1) sin llamar a
    systemd ni escribir cgroup.freeze; `llamadas` registra lo que se habria ejecutado (debe quedar vacio)."""
    out: dict[str, Any] = {}
    for nombre, (arboles, estado) in ESCENARIOS.items():
        acciones = po.decide(arboles, estado)
        registro: dict[str, Any] = {}
        for modo in ("observar", "off", "actuar"):
            log = tmp / nombre / f"{modo}.jsonl"
            llamadas: list[list[str]] = []
            fx = po.Efectos(log=log, cola=tmp / "cola", ejecutar=lambda a, ll=llamadas: (ll.append(a), (0, ""))[1],
                            cg_raiz=tmp / "cg", proc=tmp / "proc", modo=modo)
            po.aplica(acciones, [] if modo == "actuar" else (arboles or []), estado, fx, {})
            filas = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
            registro[modo] = {"filas": [_sin_volatiles(f) for f in filas], "llamadas": llamadas}
        out[nombre] = {"decide": [asdict(a) for a in acciones], "aplica": registro}
    return out


@pytest.mark.unit
def test_la_clase_suite_decide_y_registra_igual_que_antes_de_la_clase_nueva(tmp_path: Path):
    esperado = json.loads(FIXTURE.read_text(encoding="utf-8"))
    obtenido = json.loads(json.dumps(escenarios(tmp_path)))
    assert sorted(obtenido) == sorted(esperado)
    for nombre in esperado:
        assert obtenido[nombre] == esperado[nombre], nombre


@pytest.mark.unit
def test_control_negativo_la_caracterizacion_detecta_un_cambio_de_suite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """El instrumento puede salir rojo: con un turno mas en `suite` el escenario de la cola cambia."""
    esperado = json.loads(FIXTURE.read_text(encoding="utf-8"))
    monkeypatch.setitem(po.CLASES, "suite", po.Clase(20 * G, 18 * G, 1230, 2, po.UMBRAL_RSS_SUITE_KB))
    obtenido = json.loads(json.dumps(escenarios(tmp_path)))
    assert obtenido["cola_dos_congela_al_nuevo"] != esperado["cola_dos_congela_al_nuevo"]


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        FIXTURE.write_text(json.dumps(escenarios(Path(d)), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"grabado {FIXTURE}")
