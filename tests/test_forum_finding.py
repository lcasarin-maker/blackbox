"""tools/forum_finding.py: cada rama de rechazo del evaluador de preflights del foro, sobre evidencia real en tmp_path.

Cada camino de rechazo lleva su control: la misma evidencia sin la corrupcion produce el veredicto contrario.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools import forum_finding as ff
from tools import preflight, provider_trace

ROOT = Path(__file__).resolve().parents[1]
GSP = "FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01"
FALLBACK = "FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01"
APT = "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01"
SANO = {"pci_present": True, "cuda_status": 0, "gsp_timeout": False, "evidence_id": "host-query-test"}
CMD_OK = {"cmd": "nvidia-smi -L", "exit": 0, "stdout": "GPU 0: GB10", "stderr": ""}


def _escribe(ruta: Path, valor: Any) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(valor if isinstance(valor, str) else json.dumps(valor), encoding="utf-8")
    return ruta


def _gsp(tmp_path: Path, snapshot: Any = SANO, comandos: Any = (CMD_OK,), resultado: Any = None, ident: str = GSP) -> Path:
    """Directorio de evidencia gsp coherente: el resultado grabado es el que recalcula preflight.CHECKS."""
    if resultado is None:
        resultado = preflight.CHECKS["gsp"](snapshot) if isinstance(snapshot, dict) else {"status": "pass", "findings": []}
    _escribe(tmp_path / "preflight.json", {"id": ident, "snapshot": snapshot, "preflight_result": resultado})
    if comandos is not None:
        _escribe(tmp_path / "commands.json", {"id": GSP, "commands": list(comandos) if not isinstance(comandos, str) else comandos})
    return tmp_path


# --- _read_json -----------------------------------------------------------------------------------------------


def test_read_json_acepta_un_objeto_y_rechaza_lo_demas(tmp_path: Path) -> None:
    assert ff._read_json(_escribe(tmp_path / "ok.json", {"a": 1})) == {"a": 1}
    assert ff._read_json(_escribe(tmp_path / "lista.json", [1])) is None  # no es un objeto
    assert ff._read_json(_escribe(tmp_path / "roto.json", "{no")) is None
    assert ff._read_json(tmp_path / "ausente.json") is None


def test_read_json_rechaza_un_archivo_mas_grande_que_el_tope(tmp_path: Path) -> None:
    justo = tmp_path / "justo.json"
    justo.write_bytes(b'{"a": 1}' + b" " * (ff.MAX_CAPTURE_BYTES - len(b'{"a": 1}')))
    assert justo.stat().st_size == ff.MAX_CAPTURE_BYTES and ff._read_json(justo) == {"a": 1}
    grande = tmp_path / "grande.json"
    grande.write_bytes(b'{"a": 1}' + b" " * (ff.MAX_CAPTURE_BYTES - len(b'{"a": 1}') + 1))
    assert grande.stat().st_size == ff.MAX_CAPTURE_BYTES + 1 and ff._read_json(grande) is None


# --- _raw_commands --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("documento,motivo", [
    ("{no", "missing, malformed, or belongs to another finding"),
    ({"id": "OTRO", "commands": []}, "missing, malformed, or belongs to another finding"),
    ({"id": GSP, "commands": "no es lista"}, "missing, malformed, or belongs to another finding"),
    ({"id": GSP, "commands": ["texto"]}, "raw command row is malformed"),
    ({"id": GSP, "commands": [{"argv": ["x"], "exit_code": True, "stdout": ""}]}, "lacks literal argv or exit code"),
    ({"id": GSP, "commands": [{"argv": 7, "exit_code": 0, "stdout": ""}]}, "lacks literal argv or exit code"),
    ({"id": GSP, "commands": [{"argv": ["x"], "exit_code": 0, "stdout": 5}]}, "raw command output is malformed"),
    ({"id": GSP, "commands": [{"argv": ["x"], "exit_code": 0, "stdout": "", "stderr": None}]}, "raw command output is malformed"),
])
def test_raw_commands_rechaza_cada_forma_mal_hecha_con_su_motivo(tmp_path: Path, documento: Any, motivo: str) -> None:
    filas, error = ff._raw_commands(_escribe(tmp_path / "c.json", documento), GSP)
    assert filas is None and error is not None and motivo in error


def test_raw_commands_acepta_los_dos_formatos_de_captura(tmp_path: Path) -> None:
    documento = {"id": GSP, "commands": [{"argv": ["a", "b"], "exit_code": 0, "stdout": "x", "stderr": "e"},
                                         {"cmd": "c d", "exit": 3, "stdout": "y"}]}
    filas, error = ff._raw_commands(_escribe(tmp_path / "c.json", documento), GSP)
    assert error is None
    assert filas == [{"argv": ["a", "b"], "rc": 0, "stdout": "x", "stderr": "e"},
                     {"argv": "c d", "rc": 3, "stdout": "y", "stderr": ""}]


# --- evaluate: ids y evidencia de un preflight ------------------------------------------------------------------


def test_evaluate_rechaza_un_id_no_soportado_sin_leer_nada(tmp_path: Path) -> None:
    r = ff.evaluate("NO-EXISTE", tmp_path)
    assert (r["status"], r["fail"], r["could_not_run"], r["files"]) == ("fail", 1, 0, [])
    assert r["reason"] == "unsupported forum finding ID"


def test_evaluate_sin_evidencia_usa_el_directorio_del_repo(tmp_path: Path) -> None:
    r = ff.evaluate(GSP)  # sin `evidence`: tasks/evidence/<id> del repo
    assert r["status"] == "unknown" and r["files"] == [str(ROOT / "tasks/evidence" / GSP / "preflight.json"),
                                                       str(ROOT / "tasks/evidence" / GSP / "commands.json")]


def test_gsp_sano_con_comandos_legibles_queda_abierto_y_los_rechazos_son_distintos(tmp_path: Path) -> None:
    abierto = ff.evaluate(GSP, _gsp(tmp_path / "ok"))
    assert abierto["status"] == "unknown" and abierto["could_not_run"] == 1
    assert "incident negative and recovery/rollback controls are missing" in abierto["reason"]


def test_gsp_sin_preflight_o_con_otro_id_es_unknown(tmp_path: Path) -> None:
    sin = tmp_path / "sin"
    sin.mkdir()
    r = ff.evaluate(GSP, sin)
    assert r["status"] == "unknown" and "preflight snapshot absent, malformed, or mismatched" in r["reason"]
    otro = ff.evaluate(GSP, _gsp(tmp_path / "otro", ident="OTRO-ID"))
    assert otro["status"] == "unknown" and "mismatched" in otro["reason"]


def test_gsp_con_snapshot_que_no_es_un_objeto_es_fail(tmp_path: Path) -> None:
    r = ff.evaluate(GSP, _gsp(tmp_path, snapshot=["no", "objeto"]))
    assert (r["status"], r["fail"], r["reason"]) == ("fail", 1, "snapshot is not an object")


def test_gsp_con_comandos_ausentes_o_mal_formados_es_unknown_con_el_motivo_del_lector(tmp_path: Path) -> None:
    ausentes = ff.evaluate(GSP, _gsp(tmp_path / "a", comandos=None))
    assert ausentes["status"] == "unknown" and "raw command capture is missing" in ausentes["reason"]
    mal = ff.evaluate(GSP, _gsp(tmp_path / "b", comandos=["texto"]))
    assert mal["status"] == "unknown" and mal["reason"] == "raw command row is malformed"


def test_gsp_con_timeout_de_gsp_registrado_y_recalculado_es_fail_con_el_hallazgo(tmp_path: Path) -> None:
    malo = dict(SANO, gsp_timeout=True)
    r = ff.evaluate(GSP, _gsp(tmp_path, snapshot=malo))
    assert (r["status"], r["fail"], r["could_not_run"]) == ("fail", 1, 0)
    assert r["reason"] == "GSP timeout observed"
    # control negativo: el resultado grabado que miente (dice pass) es fail por otra razon, la de la discrepancia
    mentira = ff.evaluate(GSP, _gsp(tmp_path / "m", snapshot=malo, resultado={"status": "pass", "findings": []}))
    assert mentira["status"] == "fail" and "differs from re-evaluation" in mentira["reason"]


def test_gsp_con_snapshot_incompleto_es_unknown_con_las_observaciones_que_faltan(tmp_path: Path) -> None:
    r = ff.evaluate(GSP, _gsp(tmp_path, snapshot={"pci_present": True}))
    assert r["status"] == "unknown" and "missing observation: cuda_status" in r["reason"]


@pytest.mark.parametrize("campo", ["stdout", "stderr"])
def test_gsp_con_una_sonda_inaccesible_no_se_deja_pasar_por_sana(tmp_path: Path, campo: str) -> None:
    denegada = dict(CMD_OK, **{campo: "cat: /sys/x: Permission denied"})
    r = ff.evaluate(GSP, _gsp(tmp_path, comandos=[denegada]))
    assert r["status"] == "unknown" and r["reason"] == "one or more required raw probes were inaccessible"
    # control negativo: la misma evidencia con el comando sano llega al veredicto abierto de siempre
    assert "inaccessible" not in ff.evaluate(GSP, _gsp(tmp_path / "ok"))["reason"]


def test_gsp_con_could_not_run_en_la_captura_tambien_cuenta_como_sonda_inaccesible(tmp_path: Path) -> None:
    r = ff.evaluate(GSP, _gsp(tmp_path, comandos=[dict(CMD_OK, stdout="could_not_run: smi")]))
    assert r["reason"] == "one or more required raw probes were inaccessible"


# --- findings sin evaluador propio -----------------------------------------------------------------------------


def test_apt_evaluado_directamente_es_unknown_con_los_controles_que_faltan_no_un_keyerror(tmp_path: Path) -> None:
    """Defecto real hallado: APT esta en SUPPORTED pero no en PREFLIGHTS ni MISSING_CONTROLS; evaluate() lanzaba KeyError."""
    (tmp_path / "captura.json").write_text("{}", encoding="utf-8")
    r = ff.evaluate(APT, tmp_path)
    assert r["status"] == "unknown" and r["could_not_run"] == 1 and r["fail"] == 0
    assert "finding-specific closure evidence still missing" in r["reason"]
    assert r["files"] == [str(tmp_path / "captura.json")]  # lista lo que si hay en el directorio
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    assert ff.evaluate(APT, vacio)["files"] == []  # control: directorio sin archivos
    assert ff.evaluate(APT, tmp_path / "no-existe")["files"] == []  # control: directorio inexistente


def test_todo_id_soportado_sin_evaluador_propio_tiene_sus_controles_declarados() -> None:
    from tools.forum_hardware_subjects import IDS as RAW

    propios = set(ff.PREFLIGHTS) | RAW | {FALLBACK, "FORUM-02-PSTORE-KERNEL-REGRESSION"}
    assert (ff.SUPPORTED - propios) <= set(ff.MISSING_CONTROLS)


# --- proveedor (fallback) --------------------------------------------------------------------------------------


def _salida(nombre: str) -> str:
    return json.dumps(provider_trace.analyze_file(ROOT / "tests/fixtures/provider_trace" / f"{nombre}.jsonl"))


def _fila(nombre: str, stdout: str | None = None) -> dict[str, Any]:
    return {"cmd": f"python3 tools/provider_trace.py tests/fixtures/provider_trace/{nombre}.jsonl",
            "stdout": _salida(nombre) if stdout is None else stdout}


def _proveedor(tmp_path: Path, **cambios: Any) -> Path:
    documento = {"id": FALLBACK, "input_kind": "synthetic JSONL fixtures; no workload was generated",
                 "commands": [_fila("gpu-healthy"), _fila("cpu-only"), _fila("gpu-to-cpu-respawn")]}
    documento.update(cambios)
    _escribe(tmp_path / "provider-trace-run.json", documento)
    return tmp_path


def test_proveedor_con_los_tres_controles_recalculados_queda_abierto(tmp_path: Path) -> None:
    r = ff.evaluate(FALLBACK, _proveedor(tmp_path))
    assert r["status"] == "unknown" and "fixture controls recompute correctly" in r["reason"]


def test_proveedor_sin_registro_o_con_otro_id_es_unknown(tmp_path: Path) -> None:
    sin = tmp_path / "sin"
    sin.mkdir()
    r = ff.evaluate(FALLBACK, sin)
    assert r["status"] == "unknown" and r["reason"] == "provider trace run record unavailable or mismatched"
    otro = ff.evaluate(FALLBACK, _proveedor(tmp_path / "otro", id="OTRO"))
    assert otro["status"] == "unknown" and "unavailable or mismatched" in otro["reason"]


def test_proveedor_que_miente_sobre_el_origen_de_su_entrada_es_fail(tmp_path: Path) -> None:
    r = ff.evaluate(FALLBACK, _proveedor(tmp_path, input_kind="live production workload"))
    assert (r["status"], r["reason"]) == ("fail", "provider record misstates its fixture input provenance")


def test_proveedor_con_comandos_que_no_son_lista_es_fail(tmp_path: Path) -> None:
    r = ff.evaluate(FALLBACK, _proveedor(tmp_path, commands={"cmd": "x"}))
    assert (r["status"], r["reason"]) == ("fail", "provider trace commands are malformed")


@pytest.mark.parametrize("fila", ["texto", {"stdout": "{}"}, {"cmd": 7, "stdout": "{}"}])
def test_proveedor_con_una_fila_mal_formada_es_fail(tmp_path: Path, fila: Any) -> None:
    r = ff.evaluate(FALLBACK, _proveedor(tmp_path, commands=[fila]))
    assert (r["status"], r["reason"]) == ("fail", "provider trace command row malformed")


def test_proveedor_ignora_filas_que_no_apuntan_a_un_fixture(tmp_path: Path) -> None:
    filas = [{"cmd": "echo nada", "stdout": ""}, _fila("gpu-healthy"), _fila("cpu-only"), _fila("gpu-to-cpu-respawn")]
    assert ff.evaluate(FALLBACK, _proveedor(tmp_path, commands=filas))["status"] == "unknown"


@pytest.mark.parametrize("stdout", ["esto no es json", "", "[1, 2", 5, None])
def test_proveedor_con_salida_grabada_que_no_es_json_es_fail(tmp_path: Path, stdout: Any) -> None:
    primera = {"cmd": _fila("gpu-healthy")["cmd"], "stdout": stdout}
    filas = [primera, _fila("cpu-only"), _fila("gpu-to-cpu-respawn")]
    r = ff.evaluate(FALLBACK, _proveedor(tmp_path, commands=filas))
    assert r["status"] == "fail" and r["reason"] == "provider fixture gpu-healthy output is not valid JSON"


def test_proveedor_sin_el_control_sano_o_sin_el_negativo_es_fail_con_su_motivo(tmp_path: Path) -> None:
    sin_sano = ff.evaluate(FALLBACK, _proveedor(tmp_path / "a", commands=[_fila("cpu-only"), _fila("gpu-to-cpu-respawn")]))
    assert (sin_sano["status"], sin_sano["reason"]) == ("fail", "healthy-GPU and CPU-request fixture controls do not pass")
    sin_cpu = ff.evaluate(FALLBACK, _proveedor(tmp_path / "b", commands=[_fila("gpu-healthy"), _fila("gpu-to-cpu-respawn")]))
    assert sin_cpu["reason"] == "healthy-GPU and CPU-request fixture controls do not pass"
    sin_negativo = ff.evaluate(FALLBACK, _proveedor(tmp_path / "c", commands=[_fila("gpu-healthy"), _fila("cpu-only")]))
    assert (sin_negativo["status"], sin_negativo["reason"]) == ("fail", "post-respawn GPU-to-CPU negative control is not detected")


# --- traza real del proveedor --------------------------------------------------------------------------------------


def _evento(**kw: Any) -> str:
    return json.dumps(kw)


TRAZA_SANA = [
    _evento(event="request", request_id="r1", requested_provider="gpu"),
    _evento(event="worker", request_id="r1", worker_id="w1", pid=10),
    _evento(event="provider", request_id="r1", worker_id="w1", provider="CUDAExecutionProvider"),
    _evento(event="latency", request_id="r1", worker_id="w1", milliseconds=12),
]


def _traza(tmp_path: Path, lineas: list[str]) -> Path:
    (tmp_path).mkdir(parents=True, exist_ok=True)
    (tmp_path / "provider-trace.jsonl").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return tmp_path


def test_traza_real_consistente_se_recalcula_pero_no_cierra(tmp_path: Path) -> None:
    r = ff.evaluate(FALLBACK, _traza(tmp_path, TRAZA_SANA))
    assert r["status"] == "unknown" and "real request trace recomputed" in r["reason"]
    assert r["files"] == [str(tmp_path / "provider-trace.jsonl")]


def test_traza_real_con_una_linea_rota_es_incompleta_y_dice_cual(tmp_path: Path) -> None:
    r = ff.evaluate(FALLBACK, _traza(tmp_path, [*TRAZA_SANA, "{truncada"]))
    assert r["status"] == "unknown" and r["reason"].startswith("real per-request trace is incomplete: ")
    assert "line 5: malformed or truncated JSON" in r["reason"]


def test_traza_real_sin_ninguna_peticion_no_produce_una_secuencia_interpretable(tmp_path: Path) -> None:
    r = ff.evaluate(FALLBACK, _traza(tmp_path, [""]))
    assert r["reason"] == "real provider trace did not produce an interpretable request sequence"


def test_traza_real_con_peticion_servida_por_cpu_es_un_bloqueo_con_hallazgo_y_sigue_abierta(tmp_path: Path) -> None:
    lineas = [TRAZA_SANA[0], TRAZA_SANA[1], _evento(event="provider", request_id="r1", worker_id="w1", provider="cpu"), TRAZA_SANA[3]]
    r = ff.evaluate(FALLBACK, _traza(tmp_path, lineas))
    assert r["status"] == "unknown" and "real request trace recomputed" in r["reason"]


def test_traza_real_con_bloqueo_sin_hallazgos_por_peticion_no_se_da_por_buena(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # ponytail: analyze_file no puede devolver block sin findings (block se construye a partir de ellos); el guardia es defensivo y
    # solo se alcanza sustituyendo el colaborador, no la funcion bajo prueba. Techo: un cambio de contrato de provider_trace.
    monkeypatch.setattr(provider_trace, "analyze_file", lambda _p: {"status": "block", "findings": [], "unknowns": [], "could_not_run_count": 0})
    r = ff.evaluate(FALLBACK, _traza(tmp_path, TRAZA_SANA))
    assert r["status"] == "unknown" and r["reason"] == "real provider trace reports a block without request-level findings"
    monkeypatch.setattr(provider_trace, "analyze_file", lambda _p: {"status": "block", "findings": ["x"], "unknowns": [], "could_not_run_count": 0})
    assert "real request trace recomputed" in ff.evaluate(FALLBACK, tmp_path)["reason"]  # control: con hallazgos si se acepta
