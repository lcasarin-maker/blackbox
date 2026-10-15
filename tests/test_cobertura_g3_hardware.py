"""DEBT-COBERTURA-PISO-REBAJADO-01, grupo 3: lineas sin cubrir de los verificadores de hardware.

Todo ejecuta el codigo real sobre capturas pequenas en tmp_path. `_csv_policy` es en produccion un stub que
devuelve None (nvidia-smi no expone el rango -lgc activo en GB10); los tests de la ruta de exito lo sustituyen
por un lector que interpreta filas `readback` -- la unica costura sustituida, todo lo demas es el codigo real.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tools import hardware_evidence as he
from tools import verify_forum_finding as vff
from tools import verify_gpu_clock_cap_ab as gpu

QUERY = ("nvidia-smi --query-gpu=clocks.current.graphics,power.draw,temperature.gpu,utilization.gpu,"
         "clocks_throttle_reasons.active --format=csv")
PLAN = {"stock_policy": [300, 2800], "capped_policy": [300, 2100],
        "soak_seconds": 5, "max_sample_gap_seconds": 60}


def _row(cmd: str, out: str = "", *, exit_code: int = 0, sec: int = 0, stderr: str = "") -> dict[str, Any]:
    stamp = datetime(2026, 10, 4, tzinfo=UTC) + timedelta(seconds=sec)
    return {"cmd": cmd, "stdout": out, "stderr": stderr, "exit": exit_code, "captured_at": stamp.isoformat()}


def _bench(tps: float = 100, **changes: Any) -> str:
    metrics: dict[str, Any] = {
        "duration_seconds": 30, "tokens_per_second": tps, "completed_requests": 10, "failed_requests": 0,
        "p50_latency_ms": 40, "p99_latency_ms": 70, "model_sha256": "m", "image_digest": "i",
        "input_sha256": "x", "concurrency": 2, "max_new_tokens": 128,
    }
    metrics.update(changes)
    return json.dumps(metrics)


def _fake_policy(row: dict[str, Any]) -> tuple[int, int] | None:
    if row["cmd"] != "readback" or row["exit"] != 0:
        return None
    lo, hi = row["stdout"].split(",")
    return int(lo), int(hi)


def _identity() -> list[dict[str, Any]]:
    return [
        _row("dmidecode -t system", "Manufacturer: OEM\nProduct Name: GB10\nBIOS Version: 1.0"),
        _row("uname -r", "6.17.0"),
        _row("cat /etc/os-release", "PRETTY_NAME=Test"),
        _row("modinfo nvidia", "version: 580.178.04"),
        _row("nvidia-smi --query-gpu=name,driver_version --format=csv", "GB10, 580.178.04"),
        _row("fwupdmgr get-devices", "├─System Firmware:\n│     Current version: 1.0"),
        _row("nvidia-smi -q -d SUPPORTED_CLOCKS", "Graphics : 2100 MHz\nGraphics : 2800 MHz"),
        _row("cat clock-cap-plan.json", json.dumps(PLAN)),
        _row("cat /sys/fs/pstore/console-ramoops", "empty"),
        _row("journalctl -k", "kernel output"),
    ]


def _scenario(**o: Any) -> list[dict[str, Any]]:
    """Opciones: with_initial, supported, base_runs, base_samples, capped_tps, capped_clock, capped_bench, base_bench, loadunload."""
    with_initial, supported = o.get("with_initial", True), o.get("supported")
    base_runs, base_samples = o.get("base_runs", 2), o.get("base_samples", 2)
    capped_tps, capped_clock = o.get("capped_tps", 80), o.get("capped_clock", 2000)
    capped_bench, base_bench, loadunload = o.get("capped_bench"), o.get("base_bench"), o.get("loadunload", True)
    rows = _identity()
    if supported is not None:
        rows[6] = _row("nvidia-smi -q -d SUPPORTED_CLOCKS", supported)
    if with_initial:
        rows.append(_row("readback", "300,2800"))
    for i in range(base_runs):
        rows.append(_row("llm-benchmark --json", base_bench or _bench(100)))
    for _ in range(base_samples):
        rows.append(_row(QUERY, "1800, 240, 65, 70, 0"))
    rows.append(_row(QUERY, "300, 20, 40, 1, 0"))  # periodo idle
    rows.append(_row("nvidia-smi -lgc 300,2100"))
    rows.append(_row("readback", "300,2100"))
    for _ in range(2):
        rows.append(_row("llm-benchmark --json", capped_bench or _bench(capped_tps)))
    for _ in range(2):
        rows.append(_row(QUERY, f"{capped_clock}, 200, 60, 70, 0"))
    if loadunload:
        rows.append(_row("model load", "loaded"))
        rows.append(_row("model unload", "unloaded"))
    rows.append(_row("nvidia-smi -lgc 300,2800"))
    rows.append(_row("readback", "300,2800"))
    for i, row in enumerate(rows):  # tiempo estrictamente creciente, 2 s por fila
        stamp = datetime(2026, 10, 4, tzinfo=UTC) + timedelta(seconds=2 * i)
        row["captured_at"] = stamp.isoformat()
    return rows


def _evidence(tmp_path: Path, rows: list[dict[str, Any]]) -> Path:
    (tmp_path / "commands.json").write_text(
        json.dumps({"id": gpu.FINDING, "experiment_plan": PLAN, "commands": rows}), encoding="utf-8")
    return tmp_path


@pytest.fixture()
def policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gpu, "_csv_policy", _fake_policy)


# ---------------------------------------------------------------- ruta completa del evaluador

def test_gpu_pasa_con_ab_completo_y_reporta_el_promedio_recomputado(tmp_path: Path, policy: None) -> None:
    result = gpu.verify(_evidence(tmp_path, _scenario()))
    assert result["status"] == "pass" and result["fail"] == 0 and result["could_not_run"] == 0, result
    assert "throughput=100.000/80.000 tok/s" in result["reason"]
    assert "declared soak=5s" in result["reason"]


def test_gpu_main_devuelve_0_en_pass_y_1_en_fallo_de_driver(tmp_path: Path, policy: None,
                                                            capsys: pytest.CaptureFixture[str]) -> None:
    ok = tmp_path / "ok"
    ok.mkdir()
    assert gpu.main(["--evidence", str(_evidence(ok, _scenario()))]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "pass"

    bad = tmp_path / "bad"
    bad.mkdir()
    fault = [_row("nvidia-smi -q", "", exit_code=9, stderr="GPU has fallen off the bus")]
    assert gpu.main(["--evidence", str(_evidence(bad, fault))]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "fail"

    empty = tmp_path / "empty"
    empty.mkdir()
    assert gpu.main(["--evidence", str(empty)]) == 2


def test_gpu_orden_de_politicas_roto_es_fail(tmp_path: Path, policy: None) -> None:
    result = gpu.verify(_evidence(tmp_path, _scenario(with_initial=False)))
    assert result["status"] == "fail" and "stock/cap/rollback order" in result["reason"], result


def test_gpu_cap_fuera_de_los_relojes_soportados_es_fail(tmp_path: Path, policy: None) -> None:
    result = gpu.verify(_evidence(tmp_path, _scenario(supported="Graphics : 2800 MHz")))
    assert result["status"] == "fail" and "absent from nvidia-smi supported" in result["reason"], result


def test_gpu_baseline_con_workload_fallido_propaga_el_error(tmp_path: Path, policy: None) -> None:
    result = gpu.verify(_evidence(tmp_path, _scenario(base_bench=_bench(100, failed_requests=3))))
    assert result["status"] == "fail" and result["reason"].startswith("baseline workload recorded failed"), result


def test_gpu_capped_con_reloj_sobre_el_tope_propaga_el_error(tmp_path: Path, policy: None) -> None:
    result = gpu.verify(_evidence(tmp_path, _scenario(capped_clock=2200)))
    assert result["status"] == "fail" and "exceeded the applied cap" in result["reason"], result


def test_gpu_tuplas_distintas_entre_baseline_y_capped_son_fail(tmp_path: Path, policy: None) -> None:
    result = gpu.verify(_evidence(tmp_path, _scenario(capped_bench=_bench(80, image_digest="otra"))))
    assert result["status"] == "fail" and "tuples differ" in result["reason"], result


def test_gpu_sin_carga_y_descarga_no_pasa_por_las_compuertas_de_soporte(tmp_path: Path, policy: None) -> None:
    result = gpu.verify(_evidence(tmp_path, _scenario(loadunload=False)))
    assert result["status"] == "unknown" and "load and unload" in result["reason"], result


def test_gpu_baseline_con_una_sola_muestra_de_telemetria_es_unknown(tmp_path: Path, policy: None) -> None:
    rows = _scenario(base_samples=0)
    rows = [r for r in rows if r["cmd"] != QUERY or r["stdout"].startswith("300")] # deja solo la muestra idle
    for i, row in enumerate(rows):
        row["captured_at"] = (datetime(2026, 10, 4, tzinfo=UTC) + timedelta(seconds=2 * i)).isoformat()
    result = gpu.verify(_evidence(tmp_path, rows))
    assert result["status"] == "unknown" and "baseline power/temperature" in result["reason"], result


# ---------------------------------------------------------------- compuertas de soporte

def test_support_gates_cada_faltante_da_su_razon(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    base = [
        _row("cat /sys/fs/pstore/x", "e", sec=0), _row("journalctl -k", "k", sec=1),
        _row(QUERY, "1500, 80, 45, 2, 0", sec=2), _row("nvidia-smi -lgc 300,2100", sec=3),
        _row("model load", "l", sec=4), _row("model unload", "u", sec=5), _row("nvidia-smi -lgc 300,2800", sec=20),
    ]
    assert gpu._support_gates(base, 3, 6, {"soak_seconds": 10}, path) is None
    no_journal = [r for r in base if r["cmd"] != "journalctl -k"]
    gate = gpu._support_gates(no_journal, 2, 5, {"soak_seconds": 10}, path)
    assert gate is not None and gate["reason"] == "kernel journal output is missing"
    busy = [dict(r, stdout="1500, 80, 45, 90, 0") if r["cmd"] == QUERY else r for r in base]
    gate = gpu._support_gates(busy, 3, 6, {"soak_seconds": 10}, path)
    assert gate is not None and "idle/control" in gate["reason"]


# ---------------------------------------------------------------- _consume_measurement

def _consume(row: dict[str, Any], tmp_path: Path, phase: str = "baseline") -> tuple[dict[str, Any] | None, list[Any]]:
    runs: list[Any] = []
    err = gpu._consume_measurement({"row": row, "phase": phase, "plan": PLAN, "path": tmp_path / "c.json",
                                    "runs": runs, "samples": []})
    return err, runs


def test_consume_sin_timestamp_es_unknown(tmp_path: Path) -> None:
    err, _ = _consume({"cmd": "x", "stdout": "", "exit": 0}, tmp_path)
    assert err is not None and err["status"] == "unknown" and "timestamp unavailable" in err["reason"]


def test_consume_workload_que_solo_menciona_benchmark_no_es_runner(tmp_path: Path) -> None:
    err, runs = _consume(_row("echo benchmark"), tmp_path)
    assert err is not None and err["status"] == "unknown" and "native benchmark" in err["reason"] and runs == []


def test_consume_salida_de_benchmark_incompleta_es_unknown(tmp_path: Path) -> None:
    err, runs = _consume(_row("llm-benchmark", '{"tokens_per_second": 1}'), tmp_path)
    assert err is not None and "lacks complete raw identity" in err["reason"] and runs == []


def test_consume_requests_fallidos_son_fail_y_el_exitoso_se_acumula(tmp_path: Path) -> None:
    err, runs = _consume(_row("llm-benchmark", _bench(failed_requests=2)), tmp_path)
    assert err is not None and err["status"] == "fail" and runs == []
    err, runs = _consume(_row("llm-benchmark", _bench(55)), tmp_path)
    assert err is None and [r["tokens_per_second"] for r in runs] == [55.0]


def test_consume_comando_que_no_es_workload_se_ignora(tmp_path: Path) -> None:
    err, runs = _consume(_row("uname -r", "6.17"), tmp_path)
    assert err is None and runs == []


# ---------------------------------------------------------------- _plan

def test_plan_cada_defecto_da_su_estado(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    plan_row = [_row("cat clock-cap-plan.json", json.dumps(PLAN))]
    bad_pair = {**PLAN, "stock_policy": [300]}
    parsed, err = gpu._plan({"experiment_plan": bad_pair}, plan_row, path)
    assert parsed is None and err is not None and "positive stock and capped" in err["reason"]
    parsed, err = gpu._plan({"experiment_plan": {**PLAN, "soak_seconds": 0}}, plan_row, path)
    assert err is not None and "soak duration" in err["reason"]
    parsed, err = gpu._plan({"experiment_plan": PLAN}, [], path)
    assert err is not None and "plan-file capture is missing" in err["reason"]
    parsed, err = gpu._plan({"experiment_plan": PLAN}, [_row("cat clock-cap-plan.json", "{not json")], path)
    assert err is not None and err["status"] == "fail" and "malformed JSON" in err["reason"]


# ---------------------------------------------------------------- lectura y esquema de la captura

def test_json_mayor_que_el_limite_se_rechaza(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "commands.json"
    path.write_text(json.dumps({"id": gpu.FINDING, "pad": "x" * 200}), encoding="utf-8")
    assert gpu._json(path) is not None
    monkeypatch.setattr(gpu, "CAPTURE_LIMIT", 50)
    assert gpu._json(path) is None


def test_capture_rechaza_timestamps_invalidos_ingenuos_o_no_crecientes(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"

    def write(stamps: list[str]) -> None:
        rows = [{"cmd": "uname -r", "exit": 0, "stdout": "k", "captured_at": s} for s in stamps]
        path.write_text(json.dumps({"id": gpu.FINDING, "commands": rows}), encoding="utf-8")

    write(["2026-10-04T00:00:01+00:00", "2026-10-04T00:00:02+00:00"])
    assert gpu._capture(path) is not None
    write(["no-es-fecha"])
    assert gpu._capture(path) is None
    write(["2026-10-04T00:00:01"])  # sin zona horaria
    assert gpu._capture(path) is None
    write(["2026-10-04T00:00:02+00:00", "2026-10-04T00:00:02+00:00"])  # no estrictamente creciente
    assert gpu._capture(path) is None


def test_timestamp_devuelve_none_si_falta_o_es_invalido() -> None:
    assert gpu._timestamp({"captured_at": "2026-10-04T00:00:00Z"}) == datetime(2026, 10, 4, tzinfo=UTC)
    assert gpu._timestamp({}) is None
    assert gpu._timestamp({"captured_at": "ayer"}) is None


# ---------------------------------------------------------------- argv, telemetria, benchmark

def test_command_args_quita_sudo_doas_y_sus_opciones_y_tolera_comillas_rotas() -> None:
    assert gpu._command_args({"cmd": "sudo -n -E nvidia-smi -q"}) == ["nvidia-smi", "-q"]
    assert gpu._command_args({"cmd": "sudo -u root nvidia-smi -q"}) == ["nvidia-smi", "-q"]
    assert gpu._command_args({"cmd": "doas -- uname -r"}) == ["uname", "-r"]
    assert gpu._command_args({"cmd": "echo 'sin cerrar"}) == []
    assert gpu._command_args({}) == []


def test_telemetry_con_campo_no_numerico_es_none() -> None:
    assert gpu._telemetry(_row(QUERY, "alto, 240, 65, 70, 0")) is None
    assert gpu._telemetry(_row(QUERY, "1800, 240, 65, 70, 0")) is not None


def test_benchmark_rechaza_campos_no_numericos_y_digests_vacios() -> None:
    assert gpu._benchmark(_row("b", _bench(70))) is not None
    assert gpu._benchmark(_row("b", _bench(duration_seconds="30"))) is None
    assert gpu._benchmark(_row("b", _bench(model_sha256="  "))) is None
    assert gpu._benchmark(_row("b", _bench(max_new_tokens=0))) is None


# ---------------------------------------------------------------- driver_version y firmware

def _drv(query: str, out: str) -> str | None:
    return gpu._driver_version(_row(f"nvidia-smi --query-gpu={query} --format=csv", out))


def test_driver_version_en_sus_formas_de_salida() -> None:
    assert _drv("name,driver_version", "GB10, 580.1") == "580.1"
    assert _drv("name,driver_version", "name, driver_version\nGB10, 580.1") == "580.1"  # con cabecera
    assert _drv("driver_version", "driver_version, 580.1") == "580.1"  # nombre de columna pegado a la fila
    assert _drv("name,driver_version", "name, driver_version, GB10, 580.1") is None  # el desfase solo se corrige con 1 columna
    assert _drv("name,driver_version", "GB10") is None  # columnas que no cuadran
    assert _drv("name,memory", "GB10, 1") is None  # driver_version no se pidio
    assert _drv("name,driver_version", "") is None  # sin registros
    assert gpu._driver_version(_row("nvidia-smi -q", "x")) is None  # sin --query-gpu
    assert _drv("name,driver_version", "x" * 200_000) is None  # csv rechaza el campo gigante


def test_firmware_version_exige_bloque_de_system_firmware_con_version_actual() -> None:
    ok = "├─Otro:\n│  Current version: 9\n├─System Firmware:\n│  Device ID: 1\n│  Current version: 1.0\n└─Fin:"
    assert gpu._system_firmware_version(ok) is True
    assert gpu._system_firmware_version("├─System Firmware:\n│  Device ID: 1\n└─Fin:\n│ Current version: 1.0") is False
    assert gpu._system_firmware_version("sin bloques") is False


# ---------------------------------------------------------------- hardware_evidence

def _manifest(directory: Path, finding: str, captures: Any) -> Path:
    path = directory / "capture.json"
    path.write_text(json.dumps({"finding_id": finding, "captures": captures}), encoding="utf-8")
    return path


def test_inspect_bundle_directorio_ausente_y_sin_manifiesto(tmp_path: Path) -> None:
    gone = he.inspect_bundle("F", tmp_path / "nada", {"a"})
    assert gone["status"] == "unknown" and "missing evidence directory" in gone["reason"]
    (tmp_path / "suelto.txt").write_text("x", encoding="utf-8")
    nomanifest = he.inspect_bundle("F", tmp_path, {"a"})
    assert nomanifest["status"] == "unknown" and nomanifest["files"] == [str(tmp_path / "suelto.txt")]


def test_inspect_bundle_manifiesto_sin_capturas_es_unknown(tmp_path: Path) -> None:
    _manifest(tmp_path, "F", [])
    result = he.inspect_bundle("F", tmp_path, {"a"})
    assert result["status"] == "unknown" and result["reason"] == "raw captures are absent"


def test_inspect_bundle_fila_sin_ruta_y_ruta_que_escapa_son_fail(tmp_path: Path) -> None:
    _manifest(tmp_path, "F", [{"sha256": "x"}])
    assert he.inspect_bundle("F", tmp_path, {"a"})["reason"] == "capture row lacks a relative path"
    _manifest(tmp_path, "F", [{"path": "../fuera.txt", "sha256": "x"}])
    escaped = he.inspect_bundle("F", tmp_path, {"a"})
    assert escaped["status"] == "fail" and "escapes evidence directory" in escaped["reason"]


def test_inspect_bundle_captura_cruda_ausente_es_unknown_y_con_hash_malo_es_fail(tmp_path: Path) -> None:
    _manifest(tmp_path, "F", [{"path": "raw.txt", "sha256": "0" * 64}])
    missing = he.inspect_bundle("F", tmp_path, {"a"})
    assert missing["status"] == "unknown" and "raw capture unavailable: raw.txt" in missing["reason"]
    (tmp_path / "raw.txt").write_text("contenido", encoding="utf-8")
    mismatch = he.inspect_bundle("F", tmp_path, {"a"})
    assert mismatch["status"] == "fail" and "hash mismatch" in mismatch["reason"]


def test_inspect_bundle_integro_sin_requisitos_queda_en_unknown_por_adjudicar(tmp_path: Path) -> None:
    raw = b"contenido"
    (tmp_path / "raw.txt").write_bytes(raw)
    _manifest(tmp_path, "F", [{"path": "raw.txt", "sha256": hashlib.sha256(raw).hexdigest()}])
    result = he.inspect_bundle("F", tmp_path, set())
    assert result["status"] == "unknown" and "require adjudication" in result["reason"]
    assert result["files"] == [str(tmp_path / "capture.json"), str(tmp_path / "raw.txt")]
    # control: con un requisito que ninguna captura satisface, el mismo bundle nombra lo no probado
    pending = he.inspect_bundle("F", tmp_path, {"gpu_identity"})
    assert "unproven required observations: gpu_identity" in pending["reason"]


def test_manifiesto_mayor_que_el_limite_es_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _manifest(tmp_path, "F", [{"path": "a", "sha256": "x"}])
    monkeypatch.setattr(he, "MAX_CAPTURE_BYTES", 16)
    result = he.inspect_bundle("F", tmp_path, {"a"})
    assert result["status"] == "fail" and "exceeds the 8 MiB input bound" in result["reason"]


@pytest.mark.parametrize("finding", ["FEATURE-FORUM-GPU-CLOCK-CAP-AB-01", "FEATURE-FORUM-WIFI-ISOLATION-01",
                                     "FEATURE-USB-HID-POSTUPDATE-CHECK"])
def test_verify_enruta_a_cada_verificador_de_dominio_y_apunta_a_su_commands_json(tmp_path: Path, finding: str) -> None:
    result = he.verify(finding, tmp_path)
    assert result["status"] == "unknown" and result["could_not_run"] == 1
    assert result["files"] == [str(tmp_path / "commands.json")]


def test_verify_id_desconocido_cae_al_inventario_generico(tmp_path: Path) -> None:
    result = he.verify("NO-EXISTE-ESTE-ID", tmp_path)
    assert result["status"] == "unknown" and "capture.json" in result["reason"]


# ---------------------------------------------------------------- verify_forum_finding

def test_verify_forum_finding_id_no_soportado_es_fail() -> None:
    result = vff.verify_forum_finding("NO-EXISTE-ESTE-ID")
    assert result["status"] == "fail" and result["reason"] == "unsupported forum finding ID" and result["fail"] == 1


def test_verify_forum_finding_apt_pasa_la_decision_del_entorno(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BB_APT_APPROVED_DECISION_SHA256", "ab" * 32)
    result = vff.verify_forum_finding("DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01", tmp_path)
    assert result["status"] == "unknown" and result["files"] == [str(tmp_path / "commands.json")]


def test_verify_forum_finding_main_como_script_devuelve_1_en_fail() -> None:
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run([sys.executable, "-m", "tools.verify_forum_finding", "--id", "NO-EXISTE-ESTE-ID"],
                          cwd=root, capture_output=True, text=True, check=False)
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["reason"] == "unsupported forum finding ID"
