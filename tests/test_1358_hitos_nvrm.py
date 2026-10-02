from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from tools import hitos_incidente as hi
from tools.hitos_incidente import analyze

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "hitos_incidente.py"
WATCHER = ROOT / "adopted/system-config/usr_local_bin_nvrm-watch.sh"


def journal(message: str, stamp: str = "1789999200000000", boot: str = "boot-a", **extra):
    unit = extra.pop("unit", None)
    row = {"MESSAGE": message, "__REALTIME_TIMESTAMP": stamp, "_BOOT_ID": boot, **extra}
    if unit:
        row["_SYSTEMD_UNIT"] = unit
    return row


def test_firma_allocator_detecta_1359_y_1361_sin_depender_de_numero_de_linea():
    rows = [
        journal("NVRM: Check failed: Out of memory [NV_ERR_NO_MEMORY] at mem_desc.c:1359"),
        journal("NVRM: Check failed: Out of memory [NV_ERR_NO_MEMORY] ... mem_desc.c:1361"),
        journal("NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY] _memdescAllocInternal"),
    ]
    hits = analyze(rows, []) ["nvrm"]
    assert len(hits) == 3
    assert all(hit["allocator_signature"] for hit in hits)
    assert all(hit["boot_id"] == "boot-a" for hit in hits)


def test_error_nvrm_sin_wedge_se_registra_como_hito_independiente():
    result = analyze([journal("NVRM: Check failed: Out of memory [NV_ERR_NO_MEMORY]")], [])
    assert len(result["nvrm"]) == 1
    assert result["nvrm"][0]["allocator_signature"] is False
    assert result["psi_observations"] == []


def test_wedge_psi_sin_nvrm_no_inventa_evento_de_allocator():
    rows = [journal("bb-usable: COLAPSO PSI mem_full=99.0", unit="bb-usable.service")]
    samples = [{"ts": "2026-09-24T14:00:00-06:00", "boot_id": "boot-b",
                "psi": {"mem_full": 99.0}}]
    result = analyze(rows, samples)
    assert result["nvrm"] == []
    assert result["psi_observations"][0]["timestamp"] == "2026-09-24T14:00:00-06:00"
    assert result["psi_observations"][0]["boot_id"] == "boot-b"
    assert "no fija el inicio físico" in result["psi_observations"][0]["note"]


def test_hitos_servicio_watchdog_y_boot_separados_con_zona_y_boot():
    rows = [
        journal("[bb-usable] -- NO se acaricia el watchdog --", unit="bb-usable.service"),
        journal("Unit config FailureAction=reboot-immediate", unit="bb-usable.service"),
        journal("Main process exited, code=killed, status=6/ABRT", unit="bb-usable.service"),
        journal("Watchdog timeout (limit 6min)!", unit="bb-usable.service"),
        journal("Started bb-usable.service - recovered", unit="bb-usable.service"),
        journal("Linux version 6.17.0", stamp="1790002800000000", boot="boot-c"),
    ]
    result = analyze(rows, [])
    assert len(result["service_loss"]) == 1
    assert len(result["watchdog"]) == 1
    assert len(result["service_recovery"]) == 1
    assert result["service_loss"][0]["unit"] == "bb-usable.service"
    assert len(result["watchdog"]) == 1
    next_boot = next(event for event in result["boot"] if event["boot_id"] == "boot-c")
    assert next_boot["timestamp"].endswith("+00:00")


def test_journal_real_reconstruye_hitos_separados_y_boot_siguiente():
    path = ROOT / "tasks/evidence/SWARM-LUNA-1358-2026-10-02/journal-watchdog.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    result = analyze(rows, [])
    psi_time = datetime.fromisoformat(result["psi_signal"][0]["timestamp"])
    watchdog_time = datetime.fromisoformat(result["watchdog"][0]["timestamp"])
    restart_time = datetime.fromisoformat(result["service_recovery"][0]["timestamp"])
    mexico = timezone(timedelta(hours=-6))
    assert psi_time.astimezone(mexico).strftime("%H:%M:%S") == "14:04:04"
    assert watchdog_time.astimezone(mexico).strftime("%H:%M:%S") == "14:09:34"
    assert restart_time.astimezone(mexico).strftime("%H:%M:%S") == "14:11:52"
    assert result["psi_signal"][0]["boot_id"] == "3b3cfe2872fb44548bbada7979e251bd"
    assert result["service_recovery"][0]["boot_id"] == "1764ed418a9b438aa138ab74a5e97f77"
    assert "inicio exacto" in result["boot"][0]["note"]


def test_muestras_ordena_instantes_con_zonas_distintas_y_solo_llama_recuperacion_tras_fallo():
    rows = [
        {"ts": "2026-09-24T14:30:00-06:00", "boot_id": "boot-a",
         "psi": {"mem_full": 90}, "servicio_ssh": {"estado": "OK"}},
        {"ts": "2026-09-24T20:15:00+00:00", "boot_id": "boot-a",
         "psi": {"mem_full": 91}, "servicio_ssh": {"estado": "TIMEOUT", "motivo": "banner ausente"}},
        {"ts": "2026-09-24T20:16:00+00:00", "boot_id": "boot-a",
         "psi": {"mem_full": 10}, "servicio_ssh": {"estado": "OK"}},
        {"ts": "2026-09-24T20:17:00+00:00", "boot_id": "boot-b",
         "psi": {"mem_full": 0}, "servicio_ssh": {"estado": "OK"}},
    ]
    result = analyze([], rows)
    obs = result["service_observations"]
    assert [event["service_state"] for event in obs] == ["TIMEOUT", "OK", "OK", "OK"]
    assert result["service_loss"][0]["reason"] == "banner ausente"
    assert len(result["service_recovery"]) == 1
    assert result["service_recovery"][0]["boot_id"] == "boot-a"
    assert [event["mem_full"] for event in result["psi_observations"]] == [91.0, 10.0, 0.0, 90.0]


def test_cli_sobre_journal_real_emite_hitos_y_conserva_utc(tmp_path):
    journal_path = ROOT / "tasks/evidence/SWARM-LUNA-1358-2026-10-02/journal-watchdog.jsonl"
    samples_path = tmp_path / "samples.jsonl"
    samples_path.write_text(
        '{"ts":"2026-09-24T14:04:04-06:00","boot_id":"3b3cfe2872fb44548bbada7979e251bd",'
        '"psi":{"mem_full":98.0},"servicio_ssh":{"estado":"OK"}}\n',
        encoding="utf-8")
    result = subprocess.run([sys.executable, str(CLI), "--journal", str(journal_path),
                             "--samples", str(samples_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["psi_signal"][0]["timestamp"].startswith("2026-09-24T20:04:04")
    assert payload["watchdog"][0]["timestamp"].startswith("2026-09-24T20:09:34")
    assert payload["service_recovery"][0]["timestamp"].startswith("2026-09-24T20:11:52")
    assert payload["could_not_run"] == []


@pytest.mark.parametrize("stamp", [None, "bad", ["1789999200000000"], "9" * 1000])
def test_journal_sin_timestamp_valido_marca_incertidumbre(stamp):
    row = {"MESSAGE": "NVRM: Out of memory"}
    if stamp is not None:
        row["__REALTIME_TIMESTAMP"] = stamp
    result = analyze([row], [])
    assert result["nvrm"][0]["timestamp"] is None
    assert result["nvrm"][0]["timestamp_status"].startswith("could_not_run:")


def test_cli_fuente_ausente_y_json_malformado_salen_como_could_not_run(tmp_path):
    malformed = tmp_path / "journal.jsonl"
    malformed.write_text('{"MESSAGE":"ok","__REALTIME_TIMESTAMP":"1789999200000000",'
                          '"_BOOT_ID":"boot-a"}\n{broken}\n', encoding="utf-8")
    samples = tmp_path / "samples.jsonl"
    samples.write_text('{"ts":"2026-09-24T14:00:00-06:00","boot_id":"boot-a",'
                       '"psi":{"mem_full":99},"servicio_ssh":{"estado":"OK"}}\n',
                       encoding="utf-8")
    result = subprocess.run([sys.executable, str(CLI), "--journal", str(malformed),
                             "--samples", str(tmp_path / "missing.jsonl")],
                            capture_output=True, text=True)
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert len(payload["could_not_run"]) == 2
    assert any("JSON inválido" in item for item in payload["could_not_run"])
    assert any("falta" in item for item in payload["could_not_run"])


def test_watcher_registra_firma_sin_ejecutar_accion_nvrm(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fixture = tmp_path / "journal.txt"
    calls = tmp_path / "logger.txt"
    logfile = tmp_path / "watch.log"
    script = tmp_path / "watcher.sh"
    source = WATCHER.read_text(encoding="utf-8").replace(
        "/var/log/nvrm-watch.log", str(logfile))
    script.write_text(source, encoding="utf-8")
    script.chmod(0o755)
    (bindir / "journalctl").write_text(
        "#!/bin/sh\ncat \"$JOURNAL_FIXTURE\"\n", encoding="utf-8")
    (bindir / "logger").write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$LOGGER_CALLS\"\n", encoding="utf-8")
    (bindir / "date").write_text("#!/bin/sh\necho 2026-10-02T12:00:00-06:00\n", encoding="utf-8")
    for command in bindir.iterdir():
        command.chmod(0o755)

    for signature in ("mem_desc.c:1359", "mem_desc.c:1361"):
        fixture.write_text(
            f"kernel: NVRM: Check failed: [NV_ERR_NO_MEMORY] {signature}\n", encoding="utf-8")
        env = dict(os.environ, PATH=f"{bindir}:{os.defpath}", JOURNAL_FIXTURE=str(fixture),
                   LOGGER_CALLS=str(calls))
        subprocess.run(["/bin/bash", str(script)], env=env, check=True,
                       capture_output=True, text=True)
    assert calls.read_text(encoding="utf-8").count("evidence only") == 2
    assert "precursor" not in calls.read_text(encoding="utf-8").lower()
    assert logfile.read_text(encoding="utf-8").count("NVRM allocation error observed") == 2


def test_watcher_no_registra_hito_si_journal_no_tiene_nvrm_oom(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fixture = tmp_path / "journal.txt"
    fixture.write_text("kernel: NVRM: Xid 79\n", encoding="utf-8")
    logfile = tmp_path / "watch.log"
    script = tmp_path / "watcher.sh"
    script.write_text(WATCHER.read_text(encoding="utf-8").replace(
        "/var/log/nvrm-watch.log", str(logfile)), encoding="utf-8")
    script.chmod(0o755)
    (bindir / "journalctl").write_text("#!/bin/sh\ncat \"$JOURNAL_FIXTURE\"\n", encoding="utf-8")
    (bindir / "logger").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (bindir / "date").write_text("#!/bin/sh\necho 2026-10-02T12:00:00-06:00\n", encoding="utf-8")
    for command in bindir.iterdir():
        command.chmod(0o755)
    env = dict(os.environ, PATH=f"{bindir}:{os.defpath}", JOURNAL_FIXTURE=str(fixture))
    subprocess.run(["/bin/bash", str(script)], env=env, check=True,
                   capture_output=True, text=True)
    assert not logfile.exists()


def test_systemd_watchdog_target_is_unit_not_pid1_scope():
    result = analyze([journal("Watchdog timeout (limit 6min)!",
                             _SYSTEMD_UNIT="init.scope", UNIT="bb-usable.service")], [])
    assert result["watchdog"][0]["unit"] == "bb-usable.service"


def test_malformed_boot_identity_is_unknown_instead_of_crashing(tmp_path):
    journal_path = tmp_path / "journal.jsonl"
    sample_path = tmp_path / "sample.jsonl"
    bad_journal_row = journal("NVRM: NV_ERR_NO_MEMORY")
    bad_journal_row["_BOOT_ID"] = ["bad"]
    journal_path.write_text(json.dumps(bad_journal_row) + "\n", encoding="utf-8")
    sample_path.write_text(json.dumps({"ts": "2026-10-02T12:00:00-06:00",
                                      "boot_id": ["bad"], "psi": {"mem_full": 0.0},
                                      "servicio_ssh": {"estado": "OK"}}) + "\n", encoding="utf-8")
    result = subprocess.run([sys.executable, str(CLI), "--journal", str(journal_path),
                             "--samples", str(sample_path)], capture_output=True, text=True)
    assert result.returncode == 2, result.stderr
    payload = json.loads(result.stdout)
    assert payload["nvrm"][0]["boot_id"] is None
    assert len(payload["could_not_run"]) == 2


@pytest.mark.parametrize("raw", [None, 42, "bad", "2026-10-02T12:00:00"])
def test_sample_timestamp_must_be_iso_con_zona(raw):
    assert hi._sample_time({"ts": raw}) is None


def test_journal_time_parsea_microsegundos_utc():
    assert hi._journal_time({"__REALTIME_TIMESTAMP": "1790002800000000"}) == \
        "2026-09-21T15:00:00.000000+00:00"


def test_read_jsonl_salta_lineas_invalidas_y_conserva_registros_validos(tmp_path):
    path = tmp_path / "mixed.jsonl"
    path.write_text('{"a":1}\n\n{broken}\n[]\n{"b":2}\n', encoding="utf-8")
    reasons = []
    assert hi._read_jsonl(path, "fixture", reasons) == [{"a": 1}, {"b": 2}]
    assert any("JSON inválido" in reason for reason in reasons)
    assert any("no es un objeto" in reason for reason in reasons)


def test_read_jsonl_missing_empty_bad_utf8_and_io_errors(tmp_path, monkeypatch):
    missing = []
    assert hi._read_jsonl(tmp_path / "missing", "missing", missing) == []
    assert "falta" in missing[0]
    empty = tmp_path / "empty.jsonl"
    empty.touch()
    missing = []
    assert hi._read_jsonl(empty, "empty", missing) == []
    assert any("sin registros" in reason for reason in missing)
    bad_utf8 = tmp_path / "bad-utf8.jsonl"
    bad_utf8.write_bytes(b"\xff")
    missing = []
    assert hi._read_jsonl(bad_utf8, "utf8", missing) == []
    assert any("no se pudo leer" in reason for reason in missing)
    io_path = tmp_path / "io.jsonl"
    io_path.write_text("{}\n", encoding="utf-8")
    original_open = Path.open

    def failing_open(path, *args, **kwargs):
        if path == io_path:
            raise PermissionError("denied fixture")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    missing = []
    assert hi._read_jsonl(io_path, "io", missing) == []
    assert any("denied fixture" in reason for reason in missing)


def test_psi_invalid_missing_and_root_export_are_reported():
    result = analyze([], [
        {"ts": "2026-10-02T12:00:00-06:00", "boot_id": "b1", "psi_mem_full_avg10": 3},
        {"ts": "2026-10-02T12:00:01-06:00", "boot_id": "b1", "psi": {"mem_full": "bad"}},
        {"ts": "2026-10-02T12:00:02-06:00", "boot_id": "b1"},
    ])
    assert result["psi_observations"][0]["mem_full"] == 3.0
    assert sum("psi memory full inválido" in reason for reason in result["could_not_run"]) == 1
    assert not any("no hay ninguna observación válida" in reason for reason in result["could_not_run"])


def test_psi_sin_ninguna_observacion_valida_es_could_not_run():
    result = analyze([], [{"ts": "2026-10-02T12:00:00-06:00", "boot_id": "b1"}])
    assert any("no hay ninguna observación válida" in reason for reason in result["could_not_run"])


def test_sonda_ssh_ausente_o_desactivada_es_could_not_run():
    for row in ({"ts": "2026-10-02T12:00:00-06:00", "boot_id": "b1",
                 "psi": {"mem_full": 0}},
                {"ts": "2026-10-02T12:00:00-06:00", "boot_id": "b1",
                 "psi": {"mem_full": 0}, "servicio_ssh": {"estado": "DESACTIVADO"}}):
        result = analyze([], [row])
        assert any("sonda" in reason or "DESACTIVADO" in reason
                   for reason in result["could_not_run"])


def test_main_valido_imprime_resultado_y_devuelve_cero(tmp_path, capsys):
    journal_path = tmp_path / "journal.jsonl"
    sample_path = tmp_path / "sample.jsonl"
    journal_path.write_text(json.dumps(journal("Started bb-usable.service", unit="bb-usable.service")) + "\n",
                            encoding="utf-8")
    sample_path.write_text(json.dumps({"ts": "2026-10-02T12:00:00-06:00", "boot_id": "b1",
                                      "psi": {"mem_full": 0},
                                      "servicio_ssh": {"estado": "OK"}}) + "\n",
                           encoding="utf-8")
    assert hi.main(["--journal", str(journal_path), "--samples", str(sample_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["could_not_run"] == []


def test_script_guard_main_termina_con_codigo_dos_si_falta_fuente(tmp_path, monkeypatch):
    journal_path = tmp_path / "missing.jsonl"
    sample_path = tmp_path / "samples.jsonl"
    sample_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [str(CLI), "--journal", str(journal_path),
                                       "--samples", str(sample_path)])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(CLI), run_name="__main__")
    assert exc.value.code == 2
