"""Cobertura de tools/calibra_calor.py (FEATURE-CALIBRAR-CALOR-SOSTENIDO-01).

Los tests que importan son los de control negativo: un corpus SIN cortes tiene que dar cero aciertos con
cualquier configuracion, y un corpus con UN corte sintetico caliente tiene que detectarlo. Si el calculo
diera aciertos sin cortes, o no viera el corte, la tabla real no mediria nada.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools import atom_gpu_telemetry as agt
from tools import calibra_calor as cc

pytestmark = pytest.mark.unit

T0 = datetime(2026, 10, 12, 0, 0, tzinfo=timezone.utc)
ZONAS = ("thermal_zone0", "thermal_zone1")
UMBRALES = {z: 94.8 for z in ZONAS}


def _muestra(boot: str, i: int, temp: float, pw: float = 10.0) -> dict:
    return {"ts": (T0 + timedelta(seconds=5 * i)).isoformat(), "evento": "muestra", "boot_id": boot,
            "gpu_power_w": pw, "zonas": [{"zona": "thermal_zone0", "type": "acpitz", "temp_c": temp},
                                         {"zona": "thermal_zone1", "type": "acpitz", "temp_c": temp - 20}]}


def _corpus(tmp_path: Path, boots: dict[str, tuple[str, list[float]]]) -> tuple[Path, Path]:
    """boots: boot_id -> (etiqueta, temperaturas de zona0 cada 5 s). Escribe telemetria y veredictos."""
    tele, ver = tmp_path / "tele.jsonl", tmp_path / "reboots.jsonl"
    lineas, filas, i = [], [], 0
    for bid, (etiqueta, temps) in boots.items():
        lineas.append(json.dumps({"ts": (T0 + timedelta(seconds=5 * i)).isoformat(), "evento": "arranque"}))
        for t in temps:
            lineas.append(json.dumps(_muestra(bid, i, t)))
            i += 1
        filas.append(json.dumps({"boot_id": bid.replace("-", ""), "etiqueta": etiqueta}))
    tele.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    ver.write_text("\n".join(filas) + "\n", encoding="utf-8")
    return tele, ver


def _calibra(tele: Path, ver: Path) -> dict:
    av: list[str] = []
    return cc.calibra(cc.leer_telemetria(tele, av), cc.leer_veredictos([ver], av), UMBRALES)


FRIO = [60.0] * 400
CALIENTE_AL_FINAL = [60.0] * 300 + [93.0] * 120  # 10 min en banda (>= 89.8) justo antes de morir


def test_control_negativo_corpus_sin_cortes_da_cero_aciertos(tmp_path):
    tele, ver = _corpus(tmp_path, {"aaaa-1": ("CIERRE_ORDENADO_REBOOT", FRIO),
                                   "bbbb-2": ("CIERRE_ORDENADO_POWEROFF", FRIO)})
    r = _calibra(tele, ver)
    assert r["configs"], "sin configuraciones no hay control"
    assert all(c["aciertos"] == [] and c["no_detectados"] == [] for c in r["configs"])
    assert all(c["falsos_positivos"] == [] and len(c["sanos_limpios"]) == 2 for c in r["configs"])
    assert all(c["tasa_acierto_ic95"] is None for c in r["configs"])


def test_control_negativo_corte_sintetico_caliente_se_detecta(tmp_path):
    tele, ver = _corpus(tmp_path, {"cccc-3": ("CORTE_ABRUPTO", CALIENTE_AL_FINAL),
                                   "dddd-4": ("CIERRE_ORDENADO_REBOOT", FRIO)})
    r = _calibra(tele, ver)
    vigente = next(c for c in r["configs"] if c["actual"])
    assert vigente["aciertos"] == ["cccc3"]
    assert vigente["no_detectados"] == [] and vigente["falsos_positivos"] == []
    fila = next(f for f in r["boots"] if f["boot_id"] == "cccc3")
    ev = fila["detector"]["5/0.8"]
    assert ev["dispara_al_final"] and 0 < ev["anticipo_min"] <= 10
    # con la banda a umbral-2 C (92.8) las lecturas de 93.0 tambien entran; con banda 1 C (93.8) no: no detectado
    sin_banda = cc.calibra(cc.leer_telemetria(tele, []), cc.leer_veredictos([ver], []), UMBRALES, (1.0,), (0.8,))
    assert sin_banda["configs"][0]["no_detectados"] == ["cccc3"]


def test_corte_frio_es_no_detectado_y_sano_caliente_es_falso_positivo(tmp_path):
    tele, ver = _corpus(tmp_path, {"eeee-5": ("CORTE_ABRUPTO", FRIO),
                                   "ffff-6": ("CIERRE_ORDENADO_REBOOT", CALIENTE_AL_FINAL),
                                   "gggg-7": ("COLAPSO_MEMORIA", CALIENTE_AL_FINAL),
                                   "hhhh-8": ("INDETERMINADO", FRIO)})
    r = _calibra(tele, ver)
    vigente = next(c for c in r["configs"] if c["actual"])
    assert vigente["no_detectados"] == ["eeee5"]
    assert vigente["falsos_positivos"] == ["ffff6"]
    assert vigente["tasa_fp_ic95"] == cc.wilson(1, 1)
    assert "gggg7" not in vigente["aciertos"] + vigente["falsos_positivos"]  # colapso: ni acierto ni fp
    assert r["could_not_run"] == ["hhhh8: sin veredicto de reboot_verdict (vivo o fuera de rango)"]


def _detector_vivo(temps: list[float]) -> list[int]:
    """Indices donde `_alarmas_sostenidas` (produccion) emite temp_sostenida."""
    estado: dict = {}
    umb = {z: {"umbral_c": 94.8, "trip_c": 104.8} for z in ZONAS}
    out = []
    for i, t in enumerate(temps):
        zonas = [{"zona": "thermal_zone0", "type": "acpitz", "temp_c": t}]
        if any(e["evento"] == "temp_sostenida" for e in agt._alarmas_sostenidas(zonas, umb, estado)):
            out.append(i)
    return out


def test_detector_reproduce_a_produccion_con_las_constantes_vigentes():
    rng = random.Random(7)
    temps = [rng.choice((85.0, 88.0, 90.0, 92.0, 95.0)) if (i // 150) % 2 else rng.uniform(88.5, 96.0)
             for i in range(1500)]
    ms = [cc.Muestra(float(i * 5), {"thermal_zone0": t}, None) for i, t in enumerate(temps)]
    eps = cc.detector(ms, UMBRALES, agt.SOSTENIDA_BANDA_C, agt.SOSTENIDA_FRACCION)
    esperado = _detector_vivo(temps)
    assert len(esperado) >= 2, "la secuencia tiene que abrir y cerrar episodios para que la comparacion valga"
    assert [int(e.inicio // 5) for e in eps] == esperado
    # control negativo: otra banda NO reproduce a produccion
    otra = cc.detector(ms, UMBRALES, 2.0, agt.SOSTENIDA_FRACCION)
    assert [int(e.inicio // 5) for e in otra] != esperado


def test_reinicio_del_servicio_vacia_la_ventana_y_cierra_el_episodio():
    ms = [cc.Muestra(float(i * 5), {"thermal_zone0": 93.0, "sin_umbral": 99.0}, None) for i in range(130)]
    sin = cc.detector(ms, UMBRALES, 5.0, 0.8)
    assert len(sin) == 1 and sin[0].fin is None
    ms[100].reinicio = True
    con = cc.detector(ms, UMBRALES, 5.0, 0.8)
    assert len(con) == 1 and con[0].fin == 500.0  # 30 muestras tras reiniciar: ventana incompleta, no re-dispara


def test_minutos_sobre_y_techo_de_hueco():
    ms = [cc.Muestra(0.0, {"z": 95.0}, None), cc.Muestra(60.0, {"z": 95.0}, None), cc.Muestra(65.0, {"z": 80.0}, None),
          cc.Muestra(70.0, {}, None)]
    assert cc.minutos_sobre(ms, 94.8) == pytest.approx((30 + 5) / 60)  # el hueco de 60 s cuenta solo DT_MAX_S
    assert cc.minutos_sobre(ms, 94.8, desde=10.0) == pytest.approx(5 / 60)
    assert cc._dts([]) == []
    assert cc._dts([cc.Muestra(0.0, {}, None)]) == [0.0]


def test_wilson_y_clase():
    assert cc.wilson(0, 0) is None
    lo, hi = cc.wilson(5, 6) or (0.0, 0.0)
    assert 0.4 < lo < 0.5 and 0.95 < hi <= 1.0
    assert cc.wilson(0, 8) == (0.0, 0.32)
    assert [cc.clase(e) for e in (None, "CORTE_DE_RED", "PANIC_KERNEL", "CIERRE_ORDENADO_HALT", "COLAPSO_MEMORIA",
                                  "INDETERMINADO")] == ["sin_etiqueta", "corte", "corte", "sano", "colapso",
                                                        "sin_etiqueta"]


def test_lecturas_ilegibles_se_anotan(tmp_path):
    tele = tmp_path / "t.jsonl"
    tele.write_text("no json\n" + json.dumps(_muestra("x-1", 0, 50.0)) + "\n"
                    + json.dumps({"evento": "temp_sostenida", "ts": T0.isoformat(), "boot_id": "x-1", "zona": "z"})
                    + "\n", encoding="utf-8")
    av: list[str] = []
    boots = cc.leer_telemetria(tele, av)
    assert av == ["1 lineas de telemetria no son JSON"] and len(boots["x1"].muestras) == 1
    assert boots["x1"].vivos == [(T0.timestamp(), "z")]
    v1, v2 = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    v1.write_text('{"boot_id": "x1", "etiqueta": "CORTE_ABRUPTO"}\n\n{"roto": 1}\n', encoding="utf-8")
    v2.write_text('{"boot_id": "x-1", "etiqueta": "CIERRE_ORDENADO_REBOOT"}\n', encoding="utf-8")
    av = []
    assert cc.leer_veredictos([v1, v2, tmp_path / "no.jsonl"], av) == {"x1": "CIERRE_ORDENADO_REBOOT"}
    assert av[0].startswith("a.jsonl:3 ilegible") and av[1].startswith("veredictos no existe")


def test_recomienda_desempata_hacia_la_vigente():
    assert cc.recomienda([]) is None
    base = {"aciertos": ["a"], "falsos_positivos": []}
    lejos = {**base, "banda_c": 8.0, "fraccion": 0.6}
    cerca = {**base, "banda_c": agt.SOSTENIDA_BANDA_C, "fraccion": agt.SOSTENIDA_FRACCION}
    assert cc.recomienda([lejos, cerca]) is cerca
    mejor = {"aciertos": ["a", "b"], "falsos_positivos": [], "banda_c": 8.0, "fraccion": 0.6}
    assert cc.recomienda([cerca, mejor]) is mejor


def test_contraste_vivo_y_su_control():
    temps = [93.0] * 100
    b = cc.Boot("b", [cc.Muestra(float(i * 5), {"thermal_zone0": t}, None) for i, t in enumerate(temps)],
                vivos=[(59 * 5 + 2.0, "thermal_zone0")])
    vacio = cc.Boot("v", [], vivos=[(0.0, "thermal_zone0")])
    assert cc.contraste_vivo({"b": b, "v": vacio}, UMBRALES) == (1, 1)
    assert cc.contraste_vivo({"b": b}, UMBRALES, banda_c=1.0) == (0, 1)


def test_main_informe_json_y_could_not_run(tmp_path, capsys, monkeypatch):
    tele, ver = _corpus(tmp_path, {"cccc-3": ("CORTE_ABRUPTO", CALIENTE_AL_FINAL),
                                   "dddd-4": ("CIERRE_ORDENADO_REBOOT", FRIO)})
    assert cc.main(["--telemetria", str(tele), "--veredictos", str(ver), "--umbral", "94.8"]) == 0
    out = capsys.readouterr().out
    assert "<- vigente" in out and "could_not_run: 0" in out and "recomendacion" in out
    assert "reproduce 0 de 0" in out
    monkeypatch.setattr(agt, "leer_umbrales", lambda: {z: {"umbral_c": 94.8, "trip_c": 104.8} for z in ZONAS})
    assert cc.main(["--telemetria", str(tele), "--veredictos", str(ver), "--json", "--bandas", "5",
                    "--fracciones", "0.8"]) == 0
    r = json.loads(capsys.readouterr().out)
    assert len(r["configs"]) == 1 and r["configs"][0]["aciertos"] == ["cccc3"]
    monkeypatch.setattr(agt, "leer_umbrales", lambda: {})
    assert cc.main(["--telemetria", str(tele)]) == 2
    assert cc.main(["--telemetria", str(tmp_path / "no.jsonl")]) == 2
    err = capsys.readouterr().err
    assert "sin umbral" in err and "no existe la telemetria" in err
    monkeypatch.setattr(agt, "DATA_DIR", tmp_path / "vacio")
    assert cc.main(["--telemetria", str(tele), "--umbral", "94.8"]) == 0
    assert "veredictos no existe" in capsys.readouterr().out
