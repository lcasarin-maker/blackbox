import json

from tools import atom_gpu_telemetry as agt


def test_psi_memory_parses_some_full_and_reports_missing_group(tmp_path):
    path = tmp_path / "pressure"
    path.write_text("some avg10=1.25 avg60=0.50 avg300=0.10 total=123\n", encoding="utf-8")
    result = agt.leer_psi_memoria(path)
    assert result["psi_mem_some_avg10"] == 1.25
    assert result["psi_mem_some_total"] == 123
    assert result["psi_mem_full_avg10"] is None
    assert "grupo ausente: full" in result["psi_mem_ausente"]


def test_psi_memory_marks_invalid_values_and_unreadable_file(tmp_path):
    path = tmp_path / "pressure"
    path.write_text("some avg10=nan avg60=101 total=-1\nfull avg10=0\n", encoding="utf-8")
    result = agt.leer_psi_memoria(path)
    assert result["psi_mem_some_avg10"] is None
    assert result["psi_mem_some_avg60"] is None
    assert "some.avg10 inválido" in result["psi_mem_ausente"]
    assert "some.total inválido" in result["psi_mem_ausente"]
    path.write_text("some avg10=inf avg60=2 total=1.5\nfull avg10=1 avg60=2 avg300=3 total=4\n", encoding="utf-8")
    result = agt.leer_psi_memoria(path)
    assert result["psi_mem_some_avg10"] is None
    assert result["psi_mem_some_total"] is None
    assert "some.total inválido" in result["psi_mem_ausente"]
    assert "campo ausente: some.avg300" in result["psi_mem_ausente"]
    missing = agt.leer_psi_memoria(tmp_path / "missing")
    assert "No such file" in missing["psi_mem_ausente"]


def test_muestra_includes_psi_without_changing_sampling_cadence(monkeypatch):
    monkeypatch.setattr(agt, "leer_zonas", lambda: [])
    monkeypatch.setattr(agt, "leer_gpu", lambda: {})
    monkeypatch.setattr(agt, "leer_memoria_sistema", lambda: {})
    monkeypatch.setattr(agt, "leer_psi_memoria", lambda: {"psi_mem_full_avg10": 99.0})
    monkeypatch.setattr(agt, "leer_vllm_metrics", lambda: {})
    monkeypatch.setattr(agt, "vigilar_journal", lambda state: ([], None))
    monkeypatch.setattr(agt, "mitigar", lambda *a, **kw: [])
    events = agt.muestrear({}, {}, escribir=False, actuar=False)
    assert events[0]["psi_mem_full_avg10"] == 99.0
    assert agt.INTERVALO_DEFAULT_S == 5.0


def test_udp_export_precedes_local_jsonl_write(monkeypatch, tmp_path):
    orden = []
    monkeypatch.setattr(agt, "JSONL_PATH", tmp_path / "telemetry.jsonl")
    monkeypatch.setattr(agt, "_boot_id", lambda: "boot-test")
    monkeypatch.setenv("BLACKBOX_UDP_DESTINATION", "127.0.0.1:9000")
    monkeypatch.setattr(agt, "exportar_udp", lambda events, dest: orden.append(
        ("exportar", events[0]["boot_id"], dest)))
    monkeypatch.setattr(agt.os, "fsync", lambda fd: orden.append(("fsync", fd)))
    agt._escribir({"evento": "muestra", "ts": "now"})
    assert orden[0] == ("exportar", "boot-test", "127.0.0.1:9000")
    assert orden[1][0] == "fsync"


def test_udp_payload_is_bounded_and_excludes_identity_and_process_data():
    payload = agt._udp_payload({
        "evento": "muestra", "ts": "now", "psi_mem_full_avg10": 99.0,
        "hostname": "private-host", "pid": 123, "gpu_procs": [{"pid": 456}],
    })
    assert len(payload) <= agt.UDP_DATAGRAM_MAX_BYTES
    data = json.loads(payload)
    assert data["psi_mem_full_avg10"] == 99.0
    assert "hostname" not in data and "pid" not in data and "gpu_procs" not in data


def test_udp_is_opt_in_and_requires_literal_ip(monkeypatch, capsys):
    def should_not_open(*args, **kwargs):
        raise AssertionError("UDP socket unexpectedly opened")

    monkeypatch.setattr(agt.socket, "socket", should_not_open)
    agt.exportar_udp([{"evento": "muestra"}], None)
    agt.exportar_udp([{"evento": "muestra"}], "collector.example:9000")
    assert "exportación UDP falló" in capsys.readouterr().err


def test_udp_export_uses_explicit_destination_and_failure_is_visible(monkeypatch, capsys):
    captured = {}

    class FakeSocket:
        def __init__(self, family, kind):
            captured["family"] = family

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def settimeout(self, timeout):
            captured["timeout"] = timeout

        def sendto(self, payload, address):
            captured["payload"] = payload
            captured["address"] = address

    monkeypatch.setattr(agt.socket, "socket", FakeSocket)
    agt.exportar_udp([{"evento": "muestra", "psi_mem_full_avg10": 99.0}], "127.0.0.1:9000")
    assert captured["address"] == ("127.0.0.1", 9000)
    assert captured["timeout"] == agt.UDP_SEND_TIMEOUT_S
    assert json.loads(captured["payload"])["psi_mem_full_avg10"] == 99.0

    class FailingSocket(FakeSocket):
        def sendto(self, payload, address):
            raise OSError("simulated failure")

    monkeypatch.setattr(agt.socket, "socket", FailingSocket)
    agt.exportar_udp([{"evento": "muestra"}], "127.0.0.1:9000")
    assert "simulated failure" in capsys.readouterr().err


def test_dry_run_never_exports_udp(monkeypatch, capsys):
    monkeypatch.setattr(agt, "rotar_si_hace_falta", lambda: 0)
    monkeypatch.setattr(agt, "leer_umbrales", lambda: {})
    monkeypatch.setattr(agt, "muestrear", lambda *a, **kw: [{"evento": "muestra"}])
    monkeypatch.setattr(agt, "exportar_udp", lambda *a: (_ for _ in ()).throw(
        AssertionError("dry run attempted export")))
    monkeypatch.setenv("BLACKBOX_UDP_DESTINATION", "127.0.0.1:9000")
    monkeypatch.setattr("sys.argv", ["atom_gpu_telemetry", "--dry-run", "--once"])
    assert agt.main() == 0
    capsys.readouterr()
