"""Pruebas de cobertura del lector JSONL y su CLI de blackbox scan."""

from __future__ import annotations

import datetime as dt
import json
import runpy
import sys
from pathlib import Path

import pytest

from tools import scan_samples as scan


def _ts(epoch: float) -> str:
    return dt.datetime.fromtimestamp(epoch, dt.timezone.utc).isoformat()


def _fila(epoch: float, boot: str = "A", **extra) -> dict:
    return {"ts": _ts(epoch), "boot_id": boot, **extra}


def test_epoch_and_counter_parser_inputs():
    assert scan._epoch(None) is None
    assert scan._epoch("not-a-date") is None
    assert scan._epoch("2026-09-29T12:00:00") is not None
    assert scan._epoch("2026-09-29T12:00:00+00:00") is not None
    assert scan._pares(None, 3) == {}
    assert scan._pares("cpu0:1", 3) == {}
    assert scan._pares("cpu0:x:2", 3) == {}
    assert scan._pares("cpu0:1:2", 3) == {"cpu0": (1, 2)}


def test_prepare_reports_read_json_timestamp_and_empty_failures(tmp_path):
    missing = tmp_path / "missing.jsonl"
    bad = tmp_path / "bad.jsonl"
    bad.write_text("\n{broken}\n[]\n{}\n", encoding="utf-8")
    filas, razones = scan.preparar([missing, bad], 10, 20)
    assert filas == []
    assert any("no se pudo leer" in r for r in razones)
    assert any("línea(s) JSONL inválidas" in r for r in razones)
    assert any("timestamp ISO válido" in r for r in razones)
    assert any("ninguna muestra JSON válida" in r for r in razones)

    invalid_encoding = tmp_path / "invalid-encoding.jsonl"
    invalid_encoding.write_bytes(b"\xff")
    _, razones = scan.preparar([invalid_encoding], 10, 20)
    assert any("no se pudo leer" in r for r in razones)


def test_prepare_filters_orders_validates_and_separates_boot_counters(tmp_path):
    path = tmp_path / "samples.jsonl"
    filas = [
        _fila(10.5, "old", mem_free_kb=10, zombies=0, apps=[], psi={"io_some": 0},
              gateway="OK", gw_salud="1,2,3,4,5,6,7", py_bg=[], top_rss=[],
              cpu_jiffies="cpu0:1:2", red="eth0:10:20"),
        _fila(11, "new", mem_free_kb=11, zombies=1, apps=[], psi={"mem_full": 0},
              gateway="OK", gw_salud="1,2,3,4,5,6,7", py_bg=[], top_rss=[],
              cpu_jiffies="cpu0:10:20", red="eth0:100:200"),
        _fila(12, "new", mem_free_kb=12, zombies=0, apps=[], psi={"cpu_some": 0},
              gateway="OK", gw_salud="1,2,3,4,5,6,7", py_bg=[], top_rss=[],
              cpu_jiffies="cpu0:20:40", red="eth0:200:400"),
        _fila(30, "new", mem_free_kb=13),
    ]
    path.write_text("\n".join(json.dumps(f) for f in filas), encoding="utf-8")
    datos, razones = scan.preparar([path], 10, 20)
    assert [d["ts"] for d in datos] == [filas[0]["ts"], filas[1]["ts"], filas[2]["ts"]]
    assert "cpu_jiffies" not in datos[0]
    assert datos[1]["cpu_jiffies"] == "cpu0:10:20"
    assert datos[2]["cpu_jiffies"] == "cpu0:20:40"
    assert not any("ninguna muestra trae dato" in r for r in razones)
    assert not any("faltan dos muestras" in r for r in razones)


@pytest.mark.parametrize(
    ("rows", "reason"),
    [
        ([{"ts": _ts(1), "cpu_jiffies": "cpu0:1:2", "red": "eth0:1:2"}],
         "boot_id"),
        ([ {"ts": _ts(1), "cpu_jiffies": "cpu0:1:2", "red": "eth0:1:2"},
           {"ts": _ts(2), "cpu_jiffies": "cpu0:2:4", "red": "eth0:2:4"} ],
         "boot_id"),
        ([ _fila(1, cpu_jiffies="cpu0:10:20", red="eth0:100:200"),
           _fila(1, cpu_jiffies="cpu0:20:40", red="eth0:200:400") ],
         "timestamps duplicados"),
        ([ _fila(1, cpu_jiffies="cpu0:20:40", red="eth0:200:400"),
           _fila(2, cpu_jiffies="cpu0:10:20", red="eth0:100:200") ],
         "retrocedió"),
        ([ _fila(1, cpu_jiffies="bad", red="bad"),
           _fila(2, cpu_jiffies="bad", red="bad") ],
         "faltan dos muestras"),
    ],
)
def test_prepare_reports_counter_uncertainty(tmp_path, rows, reason):
    path = tmp_path / "counter.jsonl"
    path.write_text("\n".join(json.dumps(f) for f in rows), encoding="utf-8")
    _, razones = scan.preparar([path], 0, 3)
    assert any(reason in r for r in razones)


def test_prepare_missing_fields_and_thermal_validation(tmp_path):
    path = tmp_path / "thermal.jsonl"
    good = {"evento": "muestra", "gpu_temp_c": 50, "sm_clk_mhz": 900,
            "gpu_util_pct": 0, "throttle": "0x0", "gpu_procs": [],
            "vllm_num_requests_running": 0}
    path.write_text(json.dumps(_fila(15, **good)), encoding="utf-8")
    datos, razones = scan.preparar([path], 10, 20, "termica")
    assert len(datos) == 1 and razones == []

    path.write_text(json.dumps(_fila(15)), encoding="utf-8")
    _, razones = scan.preparar([path], 10, 20, "termica")
    assert len(razones) == 7
    assert all("falta dato utilizable" in r for r in razones)


def test_associate_cpu_work_handles_correlations_and_bad_sources(tmp_path):
    cpu_path = tmp_path / "cpu.jsonl"
    cpu_path.write_text(
        "{bad}\n[]\n" + json.dumps(_fila(95, cpu_top=[{"pid": 7, "cpu_s": 1}])) + "\n"
        + json.dumps({"ts": _ts(96), "cpu_top": []}) + "\n",
        encoding="utf-8",
    )
    gpu = {"ts": _ts(100), "boot_id": "A", "gpu_util_pct": 0,
           "vllm_num_requests_running": 1,
           "gpu_procs": [{"pid": "7"}]}
    follow = {"ts": _ts(105), "boot_id": "A", "gpu_util_pct": 0,
              "vllm_num_requests_running": 1}
    thermal = [gpu, follow]
    razones = scan.asociar_cpu_gpu(thermal, [cpu_path], 0, 200)
    assert any("JSONL inválidas" in r for r in razones)
    assert gpu["scan_cpu_work_pids"] == ["7"]
    assert follow["scan_cpu_work_pids"] == ["7"]

    unmatched = {**gpu, "gpu_procs": [{"pid": "8"}]}
    expired = {"ts": _ts(131), "boot_id": "A", "gpu_util_pct": 0,
               "vllm_num_requests_running": 1}
    scan.asociar_cpu_gpu([unmatched], [cpu_path], 0, 200)
    scan.asociar_cpu_gpu([gpu, expired], [cpu_path], 0, 200)
    assert unmatched["scan_cpu_work_pids"] == []
    assert expired["scan_cpu_work_pids"] == []

    stale = {**gpu, "ts": _ts(130), "gpu_procs": [{"pid": "7"}]}
    empty = {**gpu, "ts": _ts(131), "gpu_procs": []}
    missing_boot = {**gpu, "ts": _ts(132), "boot_id": None}
    no_process = {**gpu, "ts": _ts(133), "gpu_procs": None}
    reasons = scan.asociar_cpu_gpu([stale, empty, missing_boot, no_process],
                                   [cpu_path], 0, 200)
    assert any("sin atribución" in r for r in reasons)
    assert stale["scan_cpu_work_pids"] == ["7"]
    assert empty["scan_cpu_work_pids"] == []

    missing = tmp_path / "absent.jsonl"
    corrupt = tmp_path / "corrupt.jsonl"
    corrupt.write_bytes(b"\xff")
    reasons = scan.asociar_cpu_gpu([gpu], [missing, corrupt], 0, 200)
    assert len(reasons) == 3


def test_cli_writes_filtered_output_and_rejects_reversed_window(tmp_path, monkeypatch):
    source = tmp_path / "source.jsonl"
    output = tmp_path / "filtered.jsonl"
    status = tmp_path / "status.json"
    source.write_text(json.dumps(_fila(15, mem_free_kb=10)) + "\n",
                      encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["scan_samples", "--since", "10",
        "--until", "20", "--output", str(output), "--status", str(status),
        str(source)])
    assert scan.main() == 0
    assert json.loads(output.read_text(encoding="utf-8"))["ts"] == _ts(15)
    assert json.loads(status.read_text(encoding="utf-8"))["in_window"] == 1

    monkeypatch.setattr(sys, "argv", ["scan_samples", "--since", "20",
        "--until", "10", "--output", str(output), "--status", str(status),
        str(source)])
    with pytest.raises(SystemExit):
        scan.main()

    thermal = tmp_path / "thermal.jsonl"
    cpu = tmp_path / "cpu.jsonl"
    thermal.write_text(json.dumps(_fila(15, "A", evento="muestra",
        gpu_temp_c=50, sm_clk_mhz=900, gpu_util_pct=0, throttle="0x0",
        gpu_procs=[{"pid": "9"}], vllm_num_requests_running=1)),
        encoding="utf-8")
    cpu.write_text(json.dumps(_fila(14, "A", cpu_top=[{"pid": 9, "cpu_s": 1}])),
                   encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["scan_samples", "--kind", "termica",
        "--since", "10", "--until", "20", "--output", str(output),
        "--status", str(status), "--cpu-input", str(cpu), str(thermal)])
    assert scan.main() == 0
    assert json.loads(output.read_text(encoding="utf-8"))["scan_cpu_work_pids"] == ["9"]

    monkeypatch.setattr(sys, "argv", ["scan_samples", "--since", "10",
        "--until", "20", "--output", str(output), "--status", str(status),
        str(source)])
    with pytest.raises(SystemExit) as salida:
        runpy.run_path(str(Path(scan.__file__)), run_name="__main__")
    assert salida.value.code == 0
