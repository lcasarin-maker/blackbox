"""Cobertura de tools/incident_report.py (DEBT-COBERTURA-PISO-REBAJADO-01): caminos de fallo, ramas de
journal y el CLI. Cada prueba ejecuta el codigo real y afirma lo que sale (valores, archivos, codigos)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools import incident_report as ir

pytestmark = pytest.mark.unit


def fila(seg, **kw):
    h, resto = divmod(seg, 3600)
    base = {
        "ts": f"2026-10-11T{18 + h:02d}:{resto // 60:02d}:{resto % 60:02d}+00:00",
        "evento": "muestra",
        "throttle": "0x0000000000000000",
    }
    return {**base, **kw}


class _J:
    """Respuesta de journalctl (frontera externa: el binario no corre en CI)."""

    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def _bin_falso(dir_, nombre, salida, rc=0):
    dir_.mkdir(exist_ok=True)
    p = dir_ / nombre
    p.write_text(f"#!/bin/sh\nprintf '%s' '{salida}'\nexit {rc}\n", encoding="utf-8")
    p.chmod(0o755)
    return dir_


def test_cmd_devuelve_la_salida_y_marca_fallo_de_binario_ausente_codigo_y_timeout(monkeypatch, tmp_path):
    d = _bin_falso(tmp_path / "bin", "mi-herramienta", "hola mundo")
    monkeypatch.setenv("PATH", str(d))
    assert ir._cmd("mi-herramienta") == "hola mundo"
    assert ir._cmd("no-existe-xyz") == ir.COLLECTION_FAILED  # OSError
    d2 = _bin_falso(tmp_path / "bin2", "falla", "x", rc=3)
    monkeypatch.setenv("PATH", str(d2))
    assert ir._cmd("falla") == ir.COLLECTION_FAILED  # rc != 0 no es salida

    def _timeout(*a, **k):
        raise subprocess.TimeoutExpired("x", 30)

    monkeypatch.setattr(ir.subprocess, "run", _timeout)
    assert ir._cmd("falla") == ir.COLLECTION_FAILED


def test_epoch_de_parsea_iso_y_un_texto_invalido_es_none():
    assert ir.epoch_de("2026-10-11T18:00:00+00:00") == 1791741600.0
    assert ir.epoch_de("no-es-fecha") is None
    assert ir.epoch_de(None) is None


def test_swap_suma_la_columna_de_tamano_y_un_archivo_roto_es_collection_failed(monkeypatch):
    orig = Path.read_text
    contenido = {"v": "Filename Type Size Used Priority\n/a file 100 0 -2\n/b file 23 0 -3\n"}

    def fake(self, *a, **k):
        if str(self) == "/proc/swaps":
            return contenido["v"]
        return orig(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", fake)
    assert ir._swap() == "123"
    contenido["v"] = "cabecera\n/a file mucho 0 -2\n"
    assert ir._swap() == ir.COLLECTION_FAILED


def test_plataforma_lee_dgx_release_modulo_y_secure_boot(monkeypatch, tmp_path):
    ko = tmp_path / "nvidia.ko"
    ko.write_bytes(b"x" * 321)
    d = tmp_path / "bin"
    _bin_falso(d, "modinfo", str(ko))
    _bin_falso(d, "nvidia-smi", "GB10, 580.1, 97.1")
    _bin_falso(d, "uname", "6.17.0")
    monkeypatch.setenv("PATH", str(d))
    monkeypatch.setattr(
        ir,
        "_leer",
        lambda ruta: 'DGX_PLATFORM="DGX Spark"\nRUIDO=1\nDGX_SWBUILD_VERSION="7.2"'
        if ruta == "/etc/dgx-release"
        else "dato",
    )
    sb: dict[str, bytes | None] = {"v": b"\x06\x00\x00\x00\x01"}
    orig = Path.read_bytes

    def fake(self):
        if "SecureBoot" in str(self):
            if sb["v"] is None:
                raise PermissionError("efivars")
            return sb["v"]
        return orig(self)

    monkeypatch.setattr(Path, "read_bytes", fake)
    p = ir.plataforma()
    assert p["dgx"] == {"DGX_PLATFORM": "DGX Spark", "DGX_SWBUILD_VERSION": "7.2"}
    assert p["modulo_nvidia"]["bytes"] == "321" and p["gpu_driver_vbios"] == "GB10, 580.1, 97.1"
    assert p["kernel"] == "6.17.0" and p["secure_boot"] == "enabled"
    sb["v"] = b"\x06\x00\x00\x00\x00"
    assert ir.plataforma()["secure_boot"] == "disabled"
    sb["v"] = b""  # IndexError: no se lee como disabled
    assert ir.plataforma()["secure_boot"] == ir.COLLECTION_FAILED
    sb["v"] = None
    assert ir.plataforma()["secure_boot"] == ir.COLLECTION_FAILED
    ko.unlink()  # modinfo apunta a un archivo que ya no esta
    assert ir.plataforma()["modulo_nvidia"]["bytes"] == ir.COLLECTION_FAILED


def test_config_vigente_arma_sysctl_watchdog_y_swap(monkeypatch, tmp_path):
    d = tmp_path / "bin"
    _bin_falso(d, "sysctl", "7")
    _bin_falso(d, "systemctl", "1min")
    monkeypatch.setenv("PATH", str(d))
    monkeypatch.setattr(ir, "_leer", lambda ruta: "wd:" + ruta.rsplit("/", 1)[-1])
    monkeypatch.setattr(ir, "_swap", lambda: "42")
    c = ir.config_vigente()
    assert c["sysctl_panic"] == {
        "kernel.panic": "7",
        "kernel.hung_task_panic": "7",
        "kernel.softlockup_panic": "7",
    }
    assert c["watchdog_hw"]["timeout_s"] == "wd:timeout" and c["swap_kib"] == "42"
    assert c["watchdog_systemd"] == "1min"


def test_residencia_termica_y_exposicion_sin_muestras_son_not_collected():
    assert ir.residencia_termica([]) == {"estado": ir.NOT_COLLECTED}
    assert ir.exposicion([]) == {"estado": ir.NOT_COLLECTED}


def test_residencia_ventana_salta_la_fila_truncada_y_cuenta_las_validas(tmp_path):
    ruta = tmp_path / "t.jsonl"
    ruta.write_text(
        '{"ts": "2026-10-11T18:00:05+00:00", "evento": "muestra", "gpu_temp_c": 71, "zonas": [{"temp_c": 91.0}]}\n'
        '{"ts": "2026-10-11T18:00:10+00:00", "evento": "mues\n'  # truncada por la muerte subita
        '{"ts": "2026-10-11T18:00:15+00:00", "evento": "muestra", "gpu_temp_c": 75, "zonas": [{"temp_c": 80.0}]}\n',
        encoding="utf-8",
    )
    r = ir.residencia_ventana(1791741600.0, 1791741700.0, ruta)
    assert r["estado"] == "ok" and r["muestras"] == 2 and r["gpu_temp_max_c"] == 75
    assert r["residencia"]["pico_zona_c"] == 91.0


def test_muestras_bb_un_jsonl_ilegible_es_collection_failed_no_cero(tmp_path):
    (tmp_path / "malo.jsonl").mkdir()  # abrir un directorio como archivo -> OSError
    filas, estado = ir.muestras_bb_del_boot("0123456789abcdef0123456789abcdef", tmp_path)
    assert filas == [] and estado == ir.COLLECTION_FAILED


def test_gw_rechaza_contadores_no_numericos_y_acepta_los_numericos():
    assert ir._gw({"gw_salud": "a,b,c,d,e,f,g"}) is None
    assert ir._gw({"gw_salud": "1,0,0.5,0,10,20,0"}) == {"run": 1.0, "kv": 0.5, "gen": 10.0, "prompt": 20.0}


def test_progreso_ignora_el_par_con_mismo_timestamp_y_mide_el_siguiente():
    def f(ts, g, p):
        return {
            "ts": ts,
            "vllm_generation_tokens_total": g,
            "vllm_prompt_tokens_total": p,
            "vllm_num_requests_running": 1,
            "vllm_kv_cache_usage_perc": 0.1,
        }

    t = [
        f("2026-10-11T18:00:00+00:00", 0, 0),
        f("2026-10-11T18:00:00+00:00", 5, 5),
        f("2026-10-11T18:00:10+00:00", 100, 5),
    ]
    r = ir.progreso_del_engine(t, [])
    assert r["estado"] == "ok"
    assert r["generacion_tok_s"]["ultimo"] == 9.5  # (100-5)/10: el par dt=0 no aporta ni divide por cero


def test_fase_con_metrics_sin_par_de_contadores_y_sin_avance():
    ev: dict = {}
    assert ir._fase_con_metrics({"run": 0}, {"estado": "x"}, ev).startswith("inactivo")
    assert ir._fase_con_metrics({"run": 3}, {"estado": "x"}, ev).startswith(ir.NOT_COLLECTED)
    assert ev["progreso"] == "x"
    prog = {
        "estado": "ok",
        "generacion_tok_s": {"ultimo": 0},
        "prompt_tok_s": {"ultimo": 0},
        "peticiones_en_curso_ultimo_par": 2,
        "pares_consecutivos_al_final_con_peticiones_y_0_tok_s": 0,
    }
    assert ir._fase_con_metrics({"run": 2}, prog, {}).startswith("indeterminada")
    prog["prompt_tok_s"]["ultimo"] = 5
    assert ir._fase_con_metrics({"run": 2}, prog, {}).startswith("prefill")


def test_carga_de_atlas_salta_la_linea_truncada_del_boot(tmp_path):
    marca = "01234567-89ab-cdef-0123-456789abcdef"
    ruta = tmp_path / "cola.jsonl"
    ruta.write_text(
        f'{{"event": "job_start", "boot_id": "{marca}", "job_file": "a.md"}}\n'
        f'{{"event": "job_start", "boot_id": "{marca}", "job_fi\n',
        encoding="utf-8",
    )
    r = ir.carga_de_atlas(marca.replace("-", ""), ruta)
    assert r["estado"] == "ok" and r["jobs_iniciados_en_el_boot"] == 1
    assert [j["job_file"] for j in r["jobs_en_ejecucion_al_cortar"]] == ["a.md"]


def test_lineas_nvrm_cuenta_no_memory_y_xid_y_declara_el_cero_con_su_alcance(monkeypatch):
    sal = (
        "2026-10-11T18:00:01+00:00 h kernel: NVRM: Xid (PCI:000f:01:00): 79, GPU fell\n"
        "2026-10-11T18:00:02+00:00 h kernel: NVRM: NV_ERR_NO_MEMORY a\n"
        "2026-10-11T18:00:09+00:00 h kernel: NVRM: NV_ERR_NO_MEMORY b\n"
        "2026-10-11T18:00:10+00:00 h kernel: otra cosa\n"
        "2026-10-11T18:00:11+00:00 h kernel: NVRM: Xid (PCI:000f:01:00): 79, again\n"
    )
    monkeypatch.setattr(ir.rv, "_journal", lambda *a: _J(0, sal))
    r = ir.lineas_nvrm(-1)
    assert r["lineas_NVRM_total"] == 4 and r["xid_por_codigo_en_journal"] == {"79": 2}
    assert r["NV_ERR_NO_MEMORY"] == {
        "cuenta": 2,
        "primera": "2026-10-11T18:00:02+00:00",
        "ultima": "2026-10-11T18:00:09+00:00",
    }
    monkeypatch.setattr(ir.rv, "_journal", lambda *a: _J(1, ""))
    r0 = ir.lineas_nvrm(-1)
    assert r0["NV_ERR_NO_MEMORY"]["cuenta"] == 0 and r0["NV_ERR_NO_MEMORY"]["primera"].startswith("0 en el journal")
    assert r0["xid_por_codigo_en_journal"].startswith("0 en el journal")
    monkeypatch.setattr(ir.rv, "_journal", lambda *a: _J(2, ""))
    assert ir.lineas_nvrm(-1) == {"estado": ir.COLLECTION_FAILED}


def test_silencio_del_kernel_mide_segundos_entre_ultima_linea_y_ultima_muestra(monkeypatch):
    ms = [fila(0), fila(60)]
    assert ir.silencio_del_kernel(-1, []) == {"estado": ir.NOT_COLLECTED}
    monkeypatch.setattr(ir.rv, "_journal", lambda *a: _J(0, "2026-10-11T18:00:30+00:00 host kernel: x\n"))
    r = ir.silencio_del_kernel(-1, ms)
    assert r["segundos_de_silencio_del_kernel_antes_de_la_ultima_muestra"] == 30.0
    monkeypatch.setattr(ir.rv, "_journal", lambda *a: _J(1, ""))
    assert ir.silencio_del_kernel(-1, ms) == {"estado": ir.COLLECTION_FAILED}


def test_estado_mitigaciones_compara_el_cap_declarado_con_el_maximo_bajo_carga(monkeypatch):
    cfg = {"watchdog_hw": {"estado": "active", "timeout_s": "30"}, "uvm_global_oversubscription": "1"}
    cap_boot = {"clock_cap_confirmado_por_driver": "208-2411 MHz"}
    monkeypatch.setattr(ir, "_cmd", lambda *a: "active")
    monkeypatch.setattr(
        ir,
        "_leer",
        lambda ruta: "ExecStart=nvidia-smi -lgc 208,2400"
        if ruta.endswith("atom-clock-lock.service")
        else ir.UNSUPPORTED,
    )
    carga = [fila(0, gpu_util_pct=95, sm_clk_mhz=2000), fila(5, gpu_util_pct=10, sm_clk_mhz=2999)]
    d1 = ir.estado_mitigaciones(carga, cfg, cap_boot)[0]
    assert d1["cap_declarado_mhz"] == 2400 and d1["maximo_sm_medido_bajo_carga_en_el_boot"] == 2000
    assert d1["el_cap_acota"].startswith("NO: ") and "400 MHz" in d1["el_cap_acota"]
    d1b = ir.estado_mitigaciones([fila(0, gpu_util_pct=95, sm_clk_mhz=2380)], cfg, cap_boot)[0]
    assert d1b["el_cap_acota"] == "si"
    sin = ir.estado_mitigaciones([fila(0)], cfg, cap_boot)
    assert sin[0]["el_cap_acota"] == ir.NOT_COLLECTED  # sin muestras bajo carga no se infiere
    assert sin[2]["estado"] == "active, timeout 30 s" and sin[-1]["estado"] == ir.NOT_COLLECTED
    assert sin[0]["id"] == "github:D1"


def test_adjunto_presente_da_ruta_tamano_y_declara_el_stat_que_falla(tmp_path):
    (tmp_path / "bb-1.kernel.log").write_text("abcd", encoding="utf-8")
    assert ir._adjunto_presente(tmp_path, "bb-1", "kernel.log") == f"{tmp_path}/bb-1.kernel.log (4 bytes)"
    assert ir._adjunto_presente(tmp_path, "bb-2", "kernel.log") is None
    assert ir._adjunto_presente(tmp_path, None, "kernel.log") is None
    assert ir._adjunto_presente(tmp_path, "x" * 5000, "log") == ir.COLLECTION_FAILED  # ENAMETOOLONG


BOOTS = [
    {
        "index": -1,
        "boot_id": "aaaaaaaabbbbccccddddeeeeeeeeeeee",
        "first_entry": 1_791_740_000_000_000,
        "last_entry": 1_791_741_600_000_000,
    },
    {
        "index": 0,
        "boot_id": "11111111222233334444555555555555",
        "first_entry": 1_791_741_900_000_000,
        "last_entry": 1_791_742_000_000_000,
    },
]


def _entorno_reporte(monkeypatch, tmp_path, journal=None):
    """Un journal falso con dos boots (el segundo es el vivo) y todo archivo de estado en tmp_path."""

    def jf(*a):
        if a[0] == "--list-boots":
            return _J(0, json.dumps(BOOTS))
        return _J(1, "")

    monkeypatch.setattr(ir.rv, "_journal", journal or jf)
    monkeypatch.setattr(ir.rv, "TELEMETRIA", tmp_path / "tele.jsonl")
    monkeypatch.setattr(ir, "MUESTRAS_BB", tmp_path / "bb")
    monkeypatch.setattr(ir, "ATLAS_COLA", tmp_path / "cola.jsonl")
    monkeypatch.setattr(ir, "SALIDA", tmp_path / "salida")
    monkeypatch.setattr(ir, "plataforma", lambda: {"secure_boot": "disabled", "serie_y_uuid": "REDACTED"})
    monkeypatch.setattr(
        ir,
        "config_vigente",
        lambda: {"watchdog_hw": {"estado": "x", "timeout_s": "1"}, "uvm_global_oversubscription": "0"},
    )


def test_reporte_arma_el_incidente_del_ultimo_boot_terminado_y_anota_al_operador(monkeypatch, tmp_path):
    _entorno_reporte(monkeypatch, tmp_path)
    rep = ir.reporte(None, anotaciones={"boton": "si", "led": "apagado"})
    assert rep["formato"] == "bb-incident/1"
    assert rep["resumen"]["boot_id"].startswith("aaaaaaaa")
    assert rep["resumen"]["incident_id"].endswith("-aaaaaaaa")
    op = rep["resumen"]["observacion_fisica_del_operador"]
    assert op["quedo_apagado_hasta_pulsar_boton"] == "si" and op["led_de_encendido"] == "apagado"
    assert op["ventiladores"] == ir.NOT_COLLECTED
    assert rep["carga_de_atlas"]["estado"].startswith(ir.NOT_COLLECTED)  # Atlas no publica: se declara
    assert len(rep["seis_timestamps"]) == 6
    assert ir.reporte(-1)["resumen"]["boot_id"] == rep["resumen"]["boot_id"]


def test_reporte_aborta_con_could_not_run_si_journalctl_falla_o_el_boot_no_esta_terminado(monkeypatch, tmp_path):
    _entorno_reporte(monkeypatch, tmp_path)
    with pytest.raises(SystemExit, match=r"el boot 0 no esta entre los terminados \(vivo = 0\)"):
        ir.reporte(0)
    with pytest.raises(SystemExit, match="el boot 7 no esta entre"):
        ir.reporte(7)
    monkeypatch.setattr(ir.rv, "_journal", lambda *a: _J(1, "", "sin permisos"))
    with pytest.raises(SystemExit, match="COULD_NOT_RUN: journalctl --list-boots fallo: sin permisos"):
        ir.reporte()


def test_main_ventana_imprime_lineas_de_scan_y_sale_con_2_si_no_hay_telemetria(monkeypatch, tmp_path, capsys):
    _entorno_reporte(monkeypatch, tmp_path)
    assert ir.main(["--ventana", "1791741600", "1791741700"]) == 2  # sin archivo de telemetria
    assert "NOT_COLLECTED" in capsys.readouterr().out
    (tmp_path / "tele.jsonl").write_text(
        '{"ts": "2026-10-11T18:00:05+00:00", "evento": "muestra", "gpu_temp_c": 71, '
        '"zonas": [{"temp_c": 91.0}], "throttle": "0x20"}\n',
        encoding="utf-8",
    )
    assert ir.main(["--ventana", "1791741600", "1791741700"]) == 0
    assert "racha maxima >90C" in capsys.readouterr().out


def test_main_json_guarda_escribe_md_json_y_log_del_kernel_con_el_hostname_anonimo(monkeypatch, tmp_path, capsys):
    def jf(*a):
        if a[0] == "--list-boots":
            return _J(0, json.dumps(BOOTS))
        if "-e" in a:
            return _J(0, "linea de MIHOST kernel\n")
        return _J(1, "")

    _entorno_reporte(monkeypatch, tmp_path, journal=jf)
    monkeypatch.setattr(ir, "nodo_anonimo", lambda: "node-xyz")
    monkeypatch.setattr(ir, "_cmd", lambda *a: "MIHOST" if a == ("hostname",) else ir.COLLECTION_FAILED)
    assert ir.main(["--json", "--guarda", "--estado", "colgado", "--ac", "si"]) == 0
    cap = capsys.readouterr()
    rep = json.loads(cap.out)
    base = tmp_path / "salida" / rep["resumen"]["incident_id"]
    assert rep["resumen"]["observacion_fisica_del_operador"]["estado"] == "colgado"
    guardado = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
    assert guardado["resumen"]["boot_id"] == rep["resumen"]["boot_id"]
    assert base.with_suffix(".md").read_text(encoding="utf-8").startswith("# Incidente ")
    log = (tmp_path / "salida" / f"{base.name}.kernel-ultimas-300.log").read_text(encoding="utf-8")
    assert "node-xyz" in log and "MIHOST" not in log
    assert "escrito" in cap.err


def test_main_sin_guarda_imprime_markdown_y_no_escribe_nada(monkeypatch, tmp_path, capsys):
    _entorno_reporte(monkeypatch, tmp_path)
    assert ir.main([]) == 0
    assert capsys.readouterr().out.startswith("# Incidente ")
    assert not (tmp_path / "salida").exists()


def test_telemetria_del_boot_filtra_por_boot_y_salta_la_fila_truncada(monkeypatch, tmp_path):
    marca = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    (tmp_path / "tele.jsonl").write_text(
        json.dumps({"boot_id": marca, "n": 1}) + "\n"
        + json.dumps({"boot_id": "otro-boot", "n": 2}) + "\n"
        + '{"boot_id": "' + marca + '", "n\n'  # truncada por la muerte subita
        + json.dumps({"boot_id": marca, "n": 4}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ir.rv, "TELEMETRIA", tmp_path / "tele.jsonl")
    assert [f["n"] for f in ir.telemetria_del_boot("aaaaaaaabbbbccccddddeeeeeeeeeeee")] == [1, 4]
    monkeypatch.setattr(ir.rv, "TELEMETRIA", tmp_path / "no-existe.jsonl")
    assert ir.telemetria_del_boot("aaaaaaaabbbbccccddddeeeeeeeeeeee") == []


def test_ejecutado_como_script_sale_con_el_codigo_de_main(tmp_path):
    r = subprocess.run(
        [sys.executable, "-m", "tools.incident_report", "--ventana", "0", "1"],
        capture_output=True,
        text=True,
        cwd=Path(ir.__file__).resolve().parents[1],
        env={**os.environ, "BLACKBOX_DATA": str(tmp_path)},
    )
    assert r.returncode == 2 and "NOT_COLLECTED" in r.stdout
