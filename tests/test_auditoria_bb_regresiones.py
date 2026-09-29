"""Cierres reproducibles para la auditoría adversarial de blackbox."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import signal
import sys
import datetime as dt
import subprocess
from pathlib import Path

import pytest

from tools import atom_gpu_telemetry as agt
from tools import scan_samples


def _cargar_guardia():
    ruta = Path(__file__).resolve().parents[1] / "bin/bb-guardia-proceso"
    loader = importlib.machinery.SourceFileLoader("bb_guardia_auditoria", str(ruta))
    spec = importlib.util.spec_from_loader("bb_guardia_auditoria", loader)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    try:
        loader.exec_module(modulo)
    finally:
        sys.modules.pop(spec.name, None)
    return modulo


def _cargar_watchdog():
    ruta = Path(__file__).resolve().parents[1] / "bin/bb-usable"
    loader = importlib.machinery.SourceFileLoader("bb_usable_auditoria", str(ruta))
    spec = importlib.util.spec_from_loader("bb_usable_auditoria", loader)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    try:
        loader.exec_module(modulo)
    finally:
        sys.modules.pop(spec.name, None)
    return modulo


def _bb_scan(tmp_path, filas, ventana="1 minute ago", termica_filas=None):
    repo = Path(__file__).resolve().parents[1]
    datos_dir = tmp_path / "bb-data"
    samples_dir = datos_dir / "samples"
    samples_dir.mkdir(parents=True)
    with (samples_dir / "sample.jsonl").open("w", encoding="utf-8") as fh:
        for fila in filas:
            fh.write(fila if isinstance(fila, str) else json.dumps(fila))
            fh.write("\n")
    ahora = dt.datetime.now(dt.timezone.utc)
    termica = tmp_path / "thermal.jsonl"
    default_termica = {
        "ts": ahora.isoformat(), "evento": "muestra", "gpu_temp_c": 50,
        "sm_clk_mhz": 1000, "gpu_util_pct": 0, "throttle": "0x0",
        "gpu_procs": [], "vllm_num_requests_running": 0, "boot_id": "boot-test",
    }
    termica.write_text("".join(json.dumps(d) + "\n" for d in
                                      (termica_filas or [default_termica])),
                       encoding="utf-8")
    mockbin = tmp_path / "mockbin"
    mockbin.mkdir()
    journal = mockbin / "journalctl"
    journal.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    journal.chmod(0o755)
    env = dict(os.environ)
    env.update({"BLACKBOX_DATA": str(datos_dir),
                "ATOM_TELEMETRY_JSONL": str(termica),
                "PATH": str(mockbin) + os.pathsep + env["PATH"]})
    return subprocess.run([str(repo / "bin/bb"), "scan", ventana],
                          capture_output=True, text=True, env=env, timeout=25)


@pytest.mark.parametrize("una_vez", [False, True])
def test_termica_dry_run_sin_senales(una_vez, monkeypatch, capsys):
    """El modo de observación imprime la alarma sin pausar procesos."""
    senales = []
    monkeypatch.setattr(agt.sys, "argv", ["agt", "--dry-run"] +
                        (["--once"] if una_vez else []))
    monkeypatch.setattr(agt, "leer_umbrales", lambda: {})
    monkeypatch.setattr(agt, "leer_zonas", lambda: [])
    monkeypatch.setattr(agt, "leer_gpu", lambda: {})
    monkeypatch.setattr(agt, "leer_memoria_sistema", lambda: {})
    monkeypatch.setattr(agt, "leer_vllm_metrics", lambda: {})
    monkeypatch.setattr(agt, "leer_procesos_gpu", lambda: {"gpu_procs": []})
    monkeypatch.setattr(agt, "vigilar_journal", lambda _estado: ([], None))
    monkeypatch.setattr(agt, "_alarmas", lambda *_args, **_kwargs: [
        {"evento": "temp_critica", "zona": "thermal_zone0",
         "carga_gpu": "con_carga"}])
    monkeypatch.setattr(agt, "pids_mitigables", lambda: [987654321])
    monkeypatch.setattr(agt.os, "kill", lambda pid, sig: senales.append((pid, sig)))

    if una_vez:
        assert agt.main() == 0
    else:
        monkeypatch.setattr(agt.time, "sleep", lambda _s: (_ for _ in ()).throw(
            KeyboardInterrupt))
        assert agt.main() == 0

    salida = capsys.readouterr().out
    assert '"evento": "temp_critica"' in salida
    assert senales == []


def test_guardia_replay_no_actua(monkeypatch, tmp_path):
    """Al arrancar, historia acumulada queda fuera de la escalada."""
    monkeypatch.delenv("BB_GUARDIA_DRY_RUN", raising=False)
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    g = _cargar_guardia()
    g.DATA = tmp_path
    g.ESTADO = tmp_path / "estado.json"
    g.EVIDENCIA = tmp_path / "evidencia.jsonl"
    g.SAMPLES_DIR = tmp_path / "samples"
    g.SAMPLES_DIR.mkdir()
    hoy = "2026-09-29"
    archivo = g.SAMPLES_DIR / f"{hoy}.jsonl"
    fila = {"ts": "2000-01-01T00:00:00+00:00", "boot_id": "old-boot",
            "top_rss": [{"pid": 987654321, "comm": "python3",
                         "rss_kb": 30 * 1024 * 1024,
                         "starttime_ticks": 123}]}
    archivo.write_text((json.dumps(fila) + "\n") * 4, encoding="utf-8")
    monkeypatch.setattr(g.time, "strftime", lambda _fmt: hoy)
    monkeypatch.setattr(g.time, "sleep", lambda _s: (_ for _ in ()).throw(
        KeyboardInterrupt))
    senales = []
    monkeypatch.setattr(g.os, "kill", lambda pid, sig: senales.append((pid, sig)))

    with pytest.raises(KeyboardInterrupt):
        g.main()

    assert senales == []
    assert not g.EVIDENCIA.exists()

    boot = tmp_path / "boot_id"
    boot.write_text("boot-current\n", encoding="ascii")
    monkeypatch.setattr(g, "BOOT_ID_PATH", boot)
    monkeypatch.setattr(g, "_starttime_ticks", lambda _pid: 123)
    fresca = {"ts": "2026-09-29T00:00:00+00:00", "boot_id": "boot-current",
              "top_rss": [{"pid": 42, "starttime_ticks": 123}]}
    instante = 1790640000
    assert g._muestra_fresca(fresca, ahora=instante)
    fresca["top_rss"][0]["starttime_ticks"] = 124
    assert not g._muestra_fresca(fresca, ahora=instante)


def test_guardia_archivo_tardio(monkeypatch, tmp_path):
    """Reintenta archivos tardíos y sigue rotación, truncado y reemplazo."""
    monkeypatch.setenv("BB_GUARDIA_DRY_RUN", "1")
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    g = _cargar_guardia()
    g.DATA = tmp_path
    g.ESTADO = tmp_path / "estado.json"
    g.EVIDENCIA = tmp_path / "evidencia.jsonl"
    g.SAMPLES_DIR = tmp_path / "samples"
    g.SAMPLES_DIR.mkdir()
    fecha = ["2026-09-29"]
    monkeypatch.setattr(g.time, "strftime", lambda _fmt: fecha[0])
    monkeypatch.setattr(g, "_muestra_fresca", lambda _muestra: True)
    procesadas = []

    def procesar(top0, estado):
        procesadas.append(top0["id"])
        return estado

    monkeypatch.setattr(g, "procesar_muestra", procesar)
    monkeypatch.setattr(g, "_escribir_estado", lambda _estado: None)
    ruta1 = g.SAMPLES_DIR / "2026-09-29.jsonl"
    ruta2 = g.SAMPLES_DIR / "2026-09-30.jsonl"

    def linea(id_):
        return json.dumps({"top_rss": [{"id": id_}]}) + "\n"

    paso = [0]

    def dormir(_segundos):
        paso[0] += 1
        n = paso[0]
        if n == 1:
            ruta1.write_text(linea("historia-inicial"), encoding="utf-8")
        elif n == 2:
            with ruta1.open("a", encoding="utf-8") as fh:
                fh.write(linea("A"))
        elif n == 3:
            fecha[0] = "2026-09-30"
            ruta2.write_text(linea("historia-dia-nuevo"), encoding="utf-8")
        elif n == 4:
            with ruta2.open("a", encoding="utf-8") as fh:
                fh.write(linea("B"))
        elif n == 5:
            ruta2.write_text(linea("C"), encoding="utf-8")
        elif n == 6:
            reemplazo = g.SAMPLES_DIR / "reemplazo.jsonl"
            reemplazo.write_text(linea("historia-reemplazo"), encoding="utf-8")
            reemplazo.replace(ruta2)
        elif n == 7:
            with ruta2.open("a", encoding="utf-8") as fh:
                fh.write(linea("D"))
        else:
            raise KeyboardInterrupt

    monkeypatch.setattr(g.time, "sleep", dormir)
    with pytest.raises(KeyboardInterrupt):
        g.main()

    assert procesadas == ["A", "B", "C", "D"]


def test_watchdog_colapso_psi_ilegible(monkeypatch):
    """PSI perdido no devuelve el latido tras declarar colapso."""
    bbu = _cargar_watchdog()
    eventos = []
    psi = iter([99.0, 99.0, None])
    monkeypatch.setattr(bbu, "notify", eventos.append)
    monkeypatch.setattr(bbu, "probe", lambda: 0.01)
    monkeypatch.setattr(bbu, "psi_memory_full_avg10", lambda: next(psi))
    monkeypatch.setattr(bbu, "latencia_x_ms", lambda: None)
    monkeypatch.setattr(bbu, "PROBE_INTERVAL", 0)
    monkeypatch.setattr(bbu, "PSI_ACT_SONDAS", 2)
    def sleep_tercero(_s):
        sleep_tercero.llamadas += 1
        if sleep_tercero.llamadas == 4:
            raise KeyboardInterrupt
    sleep_tercero.llamadas = 0

    monkeypatch.setattr(bbu.time, "sleep", sleep_tercero)
    with pytest.raises(KeyboardInterrupt):
        bbu.main()

    assert eventos.count("WATCHDOG=1") == 2, eventos


def test_termica_recupera_pausas(monkeypatch, tmp_path):
    """Recupera solo procesos con identidad propia y resuelve señal interrumpida."""
    proc = tmp_path / "proc"
    pid_dir = proc / "4321"
    pid_dir.mkdir(parents=True)
    stat_path = pid_dir / "stat"
    boot_path = tmp_path / "boot_id"
    boot_path.write_text("boot-A\n", encoding="ascii")
    monkeypatch.setattr(agt, "PROC_DIR", proc)
    monkeypatch.setattr(agt, "BOOT_ID_PATH", boot_path)
    monkeypatch.setattr(agt, "MITIGACION_STATE_PATH", tmp_path / "mitigacion.json")

    def escribir_stat(inicio, estado="S"):
        campos = [estado, *(["0"] * 18), str(inicio)]
        stat_path.write_text(f"4321 (build_incremental) {' '.join(campos)}\n",
                             encoding="ascii")

    escribir_stat(777)
    llamadas = []

    def senal(_pid, sig):
        llamadas.append(sig)
        escribir_stat(777, "T" if sig == agt.signal.SIGSTOP else "S")

    estado = {"mitigados": set(), "identidades": {}, "intentos": {},
              "en_alarma": {"thermal_zone0"}, "inicio": {}}
    persistir = agt._guardar_estado_mitigacion
    agt.mitigar([{"evento": "temp_critica", "carga_gpu": "con_carga"}],
                estado, listar_pids=lambda: [4321], enviar_senal=senal,
                persistir_estado=persistir)
    escribir_stat(778)
    reutilizado = agt._cargar_estado_mitigacion(enviar_senal=senal)
    assert reutilizado["mitigados"] == set()
    assert llamadas == [agt.signal.SIGSTOP]
    escribir_stat(777, "T")
    persistir(estado)
    recuperado = agt._cargar_estado_mitigacion(enviar_senal=senal)
    assert recuperado["mitigados"] == {4321}
    recuperado["en_alarma"].clear()
    eventos = agt.mitigar([], recuperado, enviar_senal=senal,
                          persistir_estado=persistir)
    assert llamadas == [agt.signal.SIGSTOP, agt.signal.SIGCONT]
    assert eventos[0]["evento"] == "mitigacion_reanuda"

    # Una muerte entre SIGSTOP y el guardado de confirmación deja una intención
    # durable; al recuperar, solo se continúa si PID y starttime aún coinciden.
    llamadas.clear()
    escribir_stat(888)
    def caer_despues_de_parar(_pid, sig):
        llamadas.append(sig)
        escribir_stat(888, "T")
        raise SystemExit("simulated service crash")

    nuevo = {"mitigados": set(), "identidades": {}, "intentos": {},
             "en_alarma": {"thermal_zone0"}, "inicio": {}}
    with pytest.raises(SystemExit):
        agt.mitigar([{"evento": "temp_critica", "carga_gpu": "con_carga"}],
                    nuevo, listar_pids=lambda: [4321],
                    enviar_senal=caer_despues_de_parar,
                    persistir_estado=persistir)
    recuperado = agt._cargar_estado_mitigacion(enviar_senal=senal)
    assert llamadas == [agt.signal.SIGSTOP, agt.signal.SIGCONT]
    assert recuperado["mitigados"] == set()


def test_scan_respeta_ventana(tmp_path):
    """El lector compartido excluye muestras anteriores y futuras y ordena."""
    archivo = tmp_path / "samples.jsonl"
    archivo.write_text("\n".join([
        json.dumps({"ts": "2000-01-01T00:00:00+00:00", "valor": "vieja"}),
        json.dumps({"ts": "2026-09-29T10:01:00+00:00", "valor": "B"}),
        json.dumps({"ts": "2030-01-01T00:00:00+00:00", "valor": "futura"}),
        json.dumps({"ts": "2026-09-29T10:00:00+00:00", "valor": "A"}),
    ]) + "\n", encoding="utf-8")
    datos, razones = scan_samples.preparar(
        [archivo], 1790676000, 1790676120)

    assert [d["valor"] for d in datos] == ["A", "B"]
    assert any("boot_id" in r for r in razones)
    assert any("cpu_jiffies" in r for r in razones)
    assert any("red:" in r for r in razones)

    ahora = dt.datetime.now(dt.timezone.utc)
    def muestra(ts):
        return {"ts": ts, "boot_id": "boot-window", "mem_free_kb": 1000,
                "zombies": 0, "apps": [], "psi": {"mem_full": 0},
                "gateway": "OK", "gw_salud": "0,0,0,0,0,0,0",
                "py_bg": [], "top_rss": [], "cpu_jiffies": "cpu0:1:2",
                "red": "eth0:10:20"}
    scan = _bb_scan(tmp_path / "cli", [
        muestra("2000-01-01T00:00:00+00:00"),
        muestra((ahora-dt.timedelta(seconds=30)).isoformat()),
        muestra(ahora.isoformat()),
        muestra("2030-01-01T00:00:00+00:00"),
    ])
    assert scan.returncode == 0, scan.stderr[-1000:]
    assert "muestras en ventana:         2" in scan.stdout


def test_scan_cnr_analisis_fallido(tmp_path):
    """JSON corrupto y registros sin campos no se esconden como análisis sano."""
    archivo = tmp_path / "samples.jsonl"
    archivo.write_text("no-json\n" + json.dumps({
        "ts": "2026-09-29T10:00:00+00:00"}) + "\n", encoding="utf-8")
    datos, razones = scan_samples.preparar(
        [archivo], 1790675940, 1790676060)

    assert len(datos) == 1
    assert any("JSONL inválidas" in r for r in razones)
    assert any("cpu_jiffies" in r for r in razones)
    assert any("red:" in r for r in razones)
    salida, estado = tmp_path / "ventana.jsonl", tmp_path / "status.json"
    assert scan_samples.main([
        "--since", "1790675940", "--until", "1790676060",
        "--output", str(salida), "--status", str(estado), str(archivo),
    ]) == 0
    resultado = json.loads(estado.read_text(encoding="utf-8"))
    assert resultado["could_not_run"] > 0
    assert len(salida.read_text(encoding="utf-8").splitlines()) == 1

    ahora = dt.datetime.now(dt.timezone.utc)
    row = {"ts": ahora.isoformat(), "boot_id": "boot-test",
           "mem_free_kb": 1000, "zombies": 0, "apps": [],
           "psi": {"mem_full": 0}, "gateway": "OK",
           "gw_salud": "0,0,0,0,0,0,0", "py_bg": [], "top_rss": [],
           "cpu_jiffies": "cpu0:100:200", "red": "eth0:1000:2000"}
    scan = _bb_scan(tmp_path, [row, "corrupt-json",
                               {**row, "ts": "2000-01-01T00:00:00+00:00"},
                               {**row, "ts": "2030-01-01T00:00:00+00:00"}])
    assert scan.returncode == 0, scan.stderr[-1000:]
    assert "muestras en ventana:         1" in scan.stdout
    assert "JSONL inválidas" in scan.stdout
    assert "NO esta limpio" in scan.stdout


def test_scan_no_cruza_contadores_entre_boots(tmp_path):
    archivo = tmp_path / "boots.jsonl"
    filas = [
        {"ts": "2026-09-29T10:00:00+00:00", "boot_id": "A",
         "cpu_jiffies": "cpu0:100:200", "red": "eth0:1000:2000"},
        {"ts": "2026-09-29T10:01:00+00:00", "boot_id": "B",
         "cpu_jiffies": "cpu0:10:20", "red": "eth0:100:200"},
        {"ts": "2026-09-29T10:02:00+00:00", "boot_id": "B",
         "cpu_jiffies": "cpu0:20:40", "red": "eth0:200:400"},
    ]
    archivo.write_text("\n".join(json.dumps(f) for f in filas), encoding="utf-8")
    datos, _ = scan_samples.preparar([archivo], 1790675940, 1790676240)

    assert "cpu_jiffies" not in datos[0]
    assert datos[1]["cpu_jiffies"] == filas[1]["cpu_jiffies"]


def test_scan_gpu_vacia_invalida(tmp_path):
    """Vacío invalida caché; idle no implica fallback, CPU sí da evidencia."""
    ahora = dt.datetime.now(dt.timezone.utc)

    def evento(segundos, **campos):
        base = {"ts": (ahora-dt.timedelta(seconds=segundos)).isoformat(),
                "boot_id": "boot-gpu", "evento": "muestra", "gpu_temp_c": 50,
                "sm_clk_mhz": 1000, "gpu_util_pct": 0, "throttle": "0x0",
                "vllm_num_requests_running": 1}
        return {**base, **campos}

    fantasma = {"pid": "4321", "nombre": "already-exited", "mem_mib": 100}
    sin_dato = [
        evento(50, gpu_procs=[fantasma]),
        evento(45, gpu_procs=[]),
        evento(40),
    ]
    idle_proc = {"pid": "5432", "nombre": "idle-worker", "mem_mib": 50}
    sin_trabajo = [evento(30, gpu_procs=[idle_proc], vllm_num_requests_running=0),
                   evento(25, vllm_num_requests_running=0),
                   evento(20, vllm_num_requests_running=0)]
    sin_cpu = [evento(15, gpu_procs=[{"pid": "7777", "nombre": "unknown-worker",
                                      "mem_mib": 80}],
                      vllm_num_requests_running=2)]
    cpu = {"ts": (ahora-dt.timedelta(seconds=60)).isoformat(),
           "boot_id": "boot-gpu", "cpu_top": [{"pid": 4321, "cpu_s": 2.0}]}
    filas = [{"ts": cpu["ts"], "boot_id": cpu["boot_id"],
              "cpu_top": cpu["cpu_top"]}]
    observado = _bb_scan(tmp_path / "observacion", filas,
                         "5 minutes ago", sin_dato + sin_trabajo + sin_cpu)
    assert observado.returncode == 0, observado.stderr[-1000:]
    assert "AVISO: 1 caso(s) de 0%" not in observado.stdout
    assert "muestras GPU ociosas con cero solicitudes: 3" in observado.stdout
    assert "atribución CPU temporal y por PID" in observado.stdout

    activa = [evento(30, gpu_procs=[{"pid": "4321", "nombre": "worker",
                                     "mem_mib": 100}],
                     vllm_num_requests_running=2),
              evento(25, vllm_num_requests_running=2),
              evento(20, vllm_num_requests_running=2)]
    confirmada = _bb_scan(tmp_path / "confirmada", filas,
                          "5 minutes ago", activa)
    assert confirmada.returncode == 0, confirmada.stderr[-1000:]
    assert "AVISO: 1 caso(s) de 0%" in confirmada.stdout
    assert "worker (100MiB)" in confirmada.stdout
