"""tools/motor_caidas.py: causas de las caidas del motor de inferencia local.

Cada prueba positiva lleva su control negativo: un lector que cuenta cero caidas
tambien sale en un journal sano, asi que se prueba que cuenta una caida real Y
que no inventa una donde no la hay.
"""
import pytest

from tools import motor_caidas as mc

FATAL = ("2026-10-10T05:17:01-06:00 h python3[1]: (EngineCore pid=235) ERROR 10-10 11:17:01 "
         "[core.py:1351] EngineCore encountered a fatal error.")
CUDA = ("2026-10-10T05:17:01-06:00 h python3[1]: (EngineCore pid=235) ERROR 10-10 11:17:01 "
        "[core.py:1351] torch.AcceleratorError: CUDA error: an illegal memory access was encountered")
XID13 = "2026-10-10T05:17:01-06:00 h kernel: NVRM: Xid (PCI:000f:01:00): 13, Graphics SM Warp Exception"
XID43 = "2026-10-10T05:17:02-06:00 h kernel: NVRM: Xid (PCI:000f:01:00): 43, pid=1, name=python3"


def test_una_caida_nombra_su_clase_y_sus_xid(tmp_path):
    r = mc.informe([FATAL, CUDA], [XID13, XID13, XID43], [], tmp_path)
    assert "caidas fatales del EngineCore:   1" in r
    assert "illegal memory access" in r
    assert "Xid13x2" in r and "Xid43x1" in r


def test_control_negativo_journal_sano_no_inventa_caidas(tmp_path):
    r = mc.informe(["2026-10-10T05:17:01-06:00 h python3[1]: INFO todo bien"], [], [], tmp_path)
    assert "caidas fatales del EngineCore:   0" in r
    assert "AVISO" not in r


def test_la_misma_caida_repetida_en_dos_lineas_cuenta_una():
    assert len(mc.caidas([FATAL, FATAL, CUDA])) == 1


def test_caida_sin_xid_cercano_se_dice():
    lejano = XID13.replace("05:17:01", "03:00:00")
    r = mc.informe([FATAL, CUDA], [lejano], [], mc.Path("/nonexistent"))
    assert "SIN Xid" in r and "caidas sin Xid cercano:          1" in r


def test_control_negativo_un_xid_cercano_no_cuenta_como_sin_xid(tmp_path):
    assert "caidas sin Xid cercano:          0" in mc.informe([FATAL, CUDA], [XID13], [], tmp_path)


def test_cuelgue_es_una_linea_REINICIA_del_vigilante(tmp_path):
    bit = ["[2026-10-10 04:21:06] REINICIA ai-nemotron.service",
           "[2026-10-10 04:12:49] chat sin respuesta (http=000) fallo 1 de 3"]
    assert "cuelgues (chat mudo, reiniciado): 1" in mc.informe([], [], bit, tmp_path)


def test_volcado_real_cuenta_y_el_de_prueba_no(tmp_path):
    (tmp_path / "prueba_abc_1_2").write_bytes(b"x")
    assert mc.volcados(tmp_path) == []
    (tmp_path / "vllm_h_9_1").write_bytes(b"x")
    assert [v.name for v in mc.volcados(tmp_path)] == ["vllm_h_9_1"]


def test_caidas_sin_un_solo_volcado_avisan(tmp_path):
    assert "AVISO" in mc.informe([FATAL, CUDA], [], [], tmp_path)


def test_sin_cuda_gdb_el_volcado_dice_que_no_pudo_leerse(tmp_path):
    f = tmp_path / "vllm_h_9_1"; f.write_bytes(b"x")
    assert mc.kernel_del_volcado(f, None) == "cuda-gdb no disponible"


def test_cuda_gdb_que_falla_es_COULD_NOT_RUN_no_un_kernel_inventado(tmp_path):
    f = tmp_path / "vllm_h_9_1"; f.write_bytes(b"x")
    r = mc.kernel_del_volcado(f, "/bin/false")
    assert r.startswith("COULD_NOT_RUN")


# --- atascos: peticiones corriendo y ni un token avanza ---------------------


def _m(minuto, run, gen, pro, boot="b1"):
    return ('{"ts": "2026-10-09T10:%02d:00-0600", "boot_id": "%s", "gw_salud": "%s,0,0.1,0,%s,%s,0"}'
            % (minuto, boot, run, gen, pro))


def test_atasco_peticiones_corriendo_sin_avanzar_tokens_es_un_episodio():
    filas = [_m(0, 30, 100, 500), _m(1, 30, 100, 500), _m(2, 30, 100, 500), _m(3, 30, 100, 500)]
    eps = mc.atascos(filas)
    assert len(eps) == 1 and eps[0][2] == 4


def test_control_negativo_motor_que_avanza_no_es_atasco():
    assert mc.atascos([_m(i, 30, 100 + i * 50, 500 + i * 90) for i in range(8)]) == []


def test_control_negativo_motor_ocioso_run_cero_no_es_atasco():
    assert mc.atascos([_m(i, 0, 100, 500) for i in range(8)]) == []


def test_control_negativo_prefill_que_avanza_aunque_no_genere_no_es_atasco():
    assert mc.atascos([_m(i, 30, 100, 500 + i * 900) for i in range(8)]) == []


def test_control_negativo_dos_muestras_iguales_no_alcanzan_el_minimo():
    assert mc.atascos([_m(0, 30, 100, 500), _m(1, 30, 100, 500), _m(2, 30, 200, 900)]) == []


def test_un_cambio_de_boot_corta_el_episodio():
    filas = [_m(0, 30, 100, 500), _m(1, 30, 100, 500), _m(2, 30, 100, 500, boot="b2"), _m(3, 30, 100, 500, boot="b2")]
    assert mc.atascos(filas) == []


def test_muestra_ilegible_se_salta_sin_romper():
    filas = ["{no es json", _m(0, 30, 100, 500), _m(1, 30, 100, 500), _m(2, 30, 100, 500)]
    assert len(mc.atascos(filas)) == 1


def test_el_informe_nombra_los_atascos(tmp_path):
    filas = [_m(i, 30, 100, 500) for i in range(5)]
    assert "atascos (peticiones corriendo, 0 tokens): 1" in mc.informe([], [], [], tmp_path, muestras=filas)


def test_un_atasco_que_termina_porque_los_tokens_avanzan_se_cierra_con_su_inicio_y_fin():
    filas = [_m(i, 30, 100, 500) for i in range(4)] + [_m(4, 30, 150, 900), _m(5, 30, 200, 1300)]
    eps = mc.atascos(filas)
    assert len(eps) == 1
    ini, fin, n = eps[0]
    assert (ini.minute, fin.minute, n) == (0, 3, 4)
    # control negativo: un episodio mas corto que `minimo` no se reporta al cerrarse
    assert mc.atascos([_m(0, 30, 100, 500), _m(1, 30, 100, 500), _m(2, 30, 150, 900)]) == []


def test_cuda_gdb_inexistente_o_colgado_es_COULD_NOT_RUN_con_su_causa(tmp_path, monkeypatch):
    f = tmp_path / "vllm_h_9_1"
    f.write_bytes(b"x")
    assert mc.kernel_del_volcado(f, str(tmp_path / "no-existe" / "cuda-gdb")) == "COULD_NOT_RUN: FileNotFoundError"

    def colgado(*_a, **_k):
        raise mc.subprocess.TimeoutExpired("cuda-gdb", 90)

    monkeypatch.setattr(mc.subprocess, "run", colgado)
    assert mc.kernel_del_volcado(f, "cuda-gdb") == "COULD_NOT_RUN: TimeoutExpired"


def _cuda_gdb_falso(tmp_path, salida):
    script = tmp_path / "cuda-gdb"
    script.write_text(f"#!/bin/sh\necho '{salida}'\n", encoding="utf-8")
    script.chmod(0o755)
    return str(script)


def test_sin_dispositivos_nvidia_el_informe_omite_los_volcados_restantes(tmp_path):
    dumps = tmp_path / "dumps"
    dumps.mkdir()
    for nombre in ("vllm_a", "vllm_b", "vllm_c"):
        (dumps / nombre).write_bytes(b"x")
    sin_gpu = mc.informe([], [], [], dumps, cuda_gdb=_cuda_gdb_falso(tmp_path, "assertion m_num_devices > 0 failed"))
    assert "vllm_a: assertion m_num_devices > 0 failed" in sin_gpu
    assert "vllm_b:" not in sin_gpu and "vllm_c:" not in sin_gpu
    assert "análisis restantes omitidos: cuda-gdb no detecta dispositivos NVIDIA" in sin_gpu
    # control negativo: con una salida cualquiera se analizan los tres y no hay omision
    normal = mc.informe([], [], [], dumps, cuda_gdb=_cuda_gdb_falso(tmp_path, "kernel foo en el dispositivo 0"))
    assert all(f"vllm_{x}: kernel foo en el dispositivo 0" in normal for x in "abc")
    assert "omitidos" not in normal


def test_leer_devuelve_las_lineas_o_vacio_si_el_archivo_no_existe(tmp_path):
    f = tmp_path / "j.log"
    f.write_text("a\nb\n", encoding="utf-8")
    assert mc._leer(str(f)) == ["a", "b"]
    assert mc._leer(str(tmp_path / "ausente.log")) == []


def test_main_lee_los_archivos_e_imprime_el_informe(tmp_path, capsys):
    (tmp_path / "unidad.log").write_text(FATAL + "\n" + CUDA + "\n", encoding="utf-8")
    (tmp_path / "kernel.log").write_text(XID13 + "\n", encoding="utf-8")
    (tmp_path / "bitacora.log").write_text("[2026-10-10 04:21:06] REINICIA ai-nemotron.service\n", encoding="utf-8")
    muestras = tmp_path / "muestras.jsonl"
    muestras.write_text("\n".join(_m(i, 30, 100, 500) for i in range(4)) + "\n", encoding="utf-8")
    dumps = tmp_path / "dumps"
    dumps.mkdir()
    base = ["--unidad", str(tmp_path / "unidad.log"), "--kernel", str(tmp_path / "kernel.log"),
            "--bitacora", str(tmp_path / "bitacora.log"), "--volcados", str(dumps)]
    assert mc.main(base + ["--muestras", str(muestras)]) == 0
    out = capsys.readouterr().out
    assert "caidas fatales del EngineCore:   1" in out and "Xid13x1" in out
    assert "cuelgues (chat mudo, reiniciado): 1" in out
    assert "atascos (peticiones corriendo, 0 tokens): 1" in out
    assert "AVISO" in out  # hubo caida y ningun volcado
    # control negativo: sin --muestras no hay atascos que contar
    assert mc.main(base) == 0
    assert "atascos (peticiones corriendo, 0 tokens): 0" in capsys.readouterr().out


def test_script_entrypoint_sale_con_cero_tras_imprimir_el_informe(tmp_path, monkeypatch, capsys):
    import runpy

    vacio = tmp_path / "vacio.log"
    vacio.write_text("", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["motor_caidas.py", "--unidad", str(vacio), "--kernel", str(vacio),
                                     "--bitacora", str(vacio), "--volcados", str(tmp_path / "nodumps")])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(mc.__file__, run_name="__main__")
    assert exc.value.code == 0
    assert "caidas fatales del EngineCore:   0" in capsys.readouterr().out
