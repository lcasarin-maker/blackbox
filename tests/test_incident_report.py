"""Reporte por incidente: vocabulario NOT_COLLECTED/UNSUPPORTED/COLLECTION_FAILED, ceros con intervalo,
y las funciones puras que arman la tabla de seis timestamps."""

import json
import re
from typing import Any

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


def test_leer_distingue_ausente_de_ilegible_y_de_contenido(tmp_path):
    (tmp_path / "ok").write_text("580.178\n", encoding="utf-8")
    assert ir._leer(str(tmp_path / "ok")) == "580.178"
    assert ir._leer(str(tmp_path / "no_existe")) == ir.UNSUPPORTED
    assert (
        ir._leer(str(tmp_path)) == ir.COLLECTION_FAILED
    )  # un directorio no se lee: no es "vacio"


def test_iso_sin_epoch_es_not_collected_y_con_epoch_trae_offset_y_utc():
    assert ir.iso(None) == ir.NOT_COLLECTED
    s = ir.iso(1791742398)
    assert "Z)" in s and ("+" in s or "-" in s[10:])


def test_decodifica_throttle_nombra_bits_y_no_confunde_cero_con_ilegible():
    assert ir.decodifica_throttle("0x0000000000000000") == "ninguno"
    assert ir.decodifica_throttle("0x20") == "SW_THERMAL_SLOWDOWN"
    assert ir.decodifica_throttle("0x48") == "HW_SLOWDOWN+HW_THERMAL_SLOWDOWN"
    assert (
        ir.decodifica_throttle("basura") == ir.COLLECTION_FAILED
    )  # control negativo: no es "ninguno"
    assert ir.decodifica_throttle(None) == ir.COLLECTION_FAILED


def test_throttle_del_boot_cuenta_por_razon_y_mide_distancia_al_final():
    ms = [fila(0), fila(60, throttle="0x20"), fila(120), fila(600)]
    t = ir.throttle_del_boot(ms)
    assert t["muestras_por_razon"] == {"ninguno": 3, "SW_THERMAL_SLOWDOWN": 1}
    assert t["muestras_con_throttle_termico_hw"] == 0
    assert (
        t[
            "minutos_entre_la_ultima_muestra_con_cada_razon_termica_y_la_ultima_muestra_del_boot"
        ]["SW_THERMAL_SLOWDOWN"]
        == 9.0
    )
    assert ir.throttle_del_boot([])["estado"] == ir.NOT_COLLECTED


def test_residencia_termica_mide_calor_sostenido_y_la_racha():
    def zonas(t):
        return [{"temp_c": t}]

    ms = [fila(i * 5, zonas=zonas(95.0)) for i in range(12)] + [
        fila(100, zonas=zonas(60.0))
    ]
    r = ir.residencia_termica(ms)
    assert r["racha_maxima_sobre_90C_min"] == 1.0  # 12 muestras * 5 s
    assert r["minutos_sobre_94.8C"] == 1.0
    frio = ir.residencia_termica([fila(i * 5, zonas=zonas(50.0)) for i in range(12)])
    assert (
        frio["racha_maxima_sobre_90C_min"] == 0.0
    )  # control negativo: un boot frio no tiene racha


def test_ventana_previa_solo_mira_los_ultimos_minutos():
    ms = [
        fila(0, gpu_temp_c=40.0),
        fila(1000, gpu_temp_c=80.0),
        fila(1060, gpu_temp_c=84.0),
    ]
    w = ir.ventana_previa(ms, minutos=5)
    assert w["gpu_temp_c"] == {
        "min": 80.0,
        "max": 84.0,
    }  # el 40.0 de hace 17 min queda fuera
    assert ir.ventana_previa([])["estado"] == ir.NOT_COLLECTED


def test_seis_timestamps_marca_nvrm_fuera_de_ventana_como_no_relevante():
    ms = [fila(0), fila(4000, vllm_num_requests_running=3.0)]
    nvrm = {
        "NV_ERR_NO_MEMORY": {
            "cuenta": 19,
            "primera": "2026-10-10T17:49:53-06:00",
            "ultima": "2026-10-11T11:00:00+00:00",
        }
    }
    t = ir.seis_timestamps({"bootstatus_siguiente": 0}, ms, nvrm, 1791746000.0)
    assert len(t) == 6
    assert "NO relevante" in t[0]["ts"]
    cerca = {
        "NV_ERR_NO_MEMORY": {
            "cuenta": 2,
            "primera": "x",
            "ultima": "2026-10-11T19:05:00+00:00",
        }
    }
    assert (
        "(RELEVANTE" in ir.seis_timestamps({}, ms, cerca, None)[0]["ts"]
    )  # control: dentro de ventana
    sin_tele = ir.seis_timestamps({}, [], cerca, None)[0]["ts"]
    # un desconocido no se lee como negativo: sin telemetria no hay juicio de relevancia
    assert "NO relevante" not in sin_tele
    assert ir.NOT_COLLECTED in sin_tele


def test_seis_timestamps_declara_el_cero_con_su_intervalo_y_el_receptor_ausente():
    ms = [fila(0), fila(60, psi_mem_full_avg10=0.0)]
    t = ir.seis_timestamps(
        {},
        ms,
        {
            "NV_ERR_NO_MEMORY": {
                "cuenta": 0,
                "primera": "0 en el journal del boot -1 (-k --grep NVRM:)",
                "ultima": None,
            }
        },
        None,
    )
    assert t[1]["ts"].startswith("0 de ") and "min previos" in t[1]["ts"]
    assert ir.NOT_COLLECTED in t[3]["fuente"]  # sin receptor externo se dice
    assert t[5]["ts"] == ir.NOT_COLLECTED  # sin boot siguiente no se inventa hora


def test_exposicion_cuenta_minutos_de_carga_no_solo_uptime():
    ms = [
        fila(
            i * 5,
            gpu_util_pct=95.0 if i < 6 else 2.0,
            vllm_num_requests_running=1.0 if i < 3 else 0.0,
        )
        for i in range(12)
    ]
    e = ir.exposicion(ms)
    assert e["minutos_gpu_util_80_o_mas"] == 0.5
    assert e["minutos_con_vllm_peticiones"] == 0.2


def test_nodo_anonimo_no_contiene_hostname_ni_machine_id(monkeypatch):
    monkeypatch.setattr(ir, "_leer", lambda ruta: "abcdef0123456789")
    n = ir.nodo_anonimo()
    assert n.startswith("node-") and "abcdef" not in n
    monkeypatch.setattr(ir, "_leer", lambda ruta: ir.UNSUPPORTED)
    assert (
        ir.nodo_anonimo() == ir.COLLECTION_FAILED
    )  # sin machine-id no se inventa un nodo


def test_el_cmdline_del_boot_sale_sin_el_uuid_del_disco(monkeypatch):
    class R:
        returncode = 0
        stdout = "Kernel command line: BOOT_IMAGE=/boot/vmlinuz root=UUID=14775751-e6a7-4614-8ee1-e3aedc5d7ada ro quiet\n"

    monkeypatch.setattr(ir.rv, "_journal", lambda *a: R())
    c = ir.config_del_boot(-1)["cmdline_del_boot"]
    assert "UUID=REDACTED" in c and "14775751" not in c
    assert "ro quiet" in c  # control: se redacta el UUID, no el resto


BERT_REAL = """ACPI: BERT 0x0000000087065D98 000030 (v01 MTKID  MTKTABLE 00000001 CREA 00000001)
BERT: Error records from previous boot:
[Hardware Error]: event severity: corrected
[Hardware Error]:   section type: unknown, 3c1e3f4b-1e1a-43df-af28-59820e958e3c
[Hardware Error]:   section length: 0x3e
[Hardware Error]:   00000000: 000d0000 544d0000 0044494b 00000000  ......MTKID.....
[Hardware Error]:   00000010: 00000000 00000100 00000022 56190000  ........"......V
BERT: Total records found: 1
pcieport 0000:00:00.0: PME: Signaling with IRQ 276
"""


def test_bert_registro_extrae_guid_y_palabra_0x14_del_volcado_literal(monkeypatch):
    class R:
        returncode = 0
        stdout = BERT_REAL

    monkeypatch.setattr(ir.rv, "_journal", lambda *a: R())
    b = ir.bert_registro(0)
    assert b["section_guid"] == "3c1e3f4b-1e1a-43df-af28-59820e958e3c"
    assert b["palabra_en_0x14"] == "00000100" and b["creador_tabla_acpi"] == "MTKID"
    assert b["severidad"] == "corrected" and b["section_length"] == "0x3e"
    assert (
        b["misma_clase_que_cita_el_personal_de_nvidia"] is True
    )  # el GUID que cita el personal de NVIDIA


def test_bert_ausente_se_declara_con_su_alcance_y_el_fallo_no_se_lee_como_ausente(
    monkeypatch,
):
    class Sin:
        returncode = 0
        stdout = "pcieport 0000:00:00.0: PME: Signaling\n"

    class Roto:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(ir.rv, "_journal", lambda *a: Sin())
    assert (
        "0 registros BERT en el journal del kernel del boot 3"
        in ir.bert_registro(3)["estado"]
    )
    monkeypatch.setattr(ir.rv, "_journal", lambda *a: Roto())
    assert (
        ir.bert_registro(3)["estado"] == ir.COLLECTION_FAILED
    )  # control: error de lectura != ausencia


def test_el_markdown_incluye_toda_clave_del_reporte_y_no_puede_omitir_una_nueva():
    rep = {
        "formato": "bb-incident/1",
        "resumen": {"incident_id": "x", "nodo_anonimizado": "node-0", "veredicto": "V"},
        "seis_timestamps": [],
        "seccion_futura_que_nadie_registro": {"dato": 1},
        "throttle_del_boot": {"a": 2},
    }
    texto = ir.md(rep)
    assert "Seccion futura que nadie registro" in texto and "Throttle del boot" in texto
    assert (
        "Formato" not in texto.split("## ", 1)[1]
    )  # control: las claves de cabecera no se duplican como seccion


def test_adjuntos_marcan_fieldiag_bloqueado_con_secure_boot_y_la_ruta_apunta_a_atlas():
    s = ir.adjuntos_y_ruta({"oem": "GIGABYTE", "secure_boot": "enabled"})
    fieldiag = next(a for a in s["adjuntos_en_orden"] if "fieldiag" in a["que"])
    assert (
        "bloqueado" in fieldiag["estado"]
        and "Secure Boot enabled" in fieldiag["estado"]
    )
    libre = ir.adjuntos_y_ruta({"oem": "GIGABYTE", "secure_boot": "disabled"})
    assert (
        "bloqueado"
        not in next(a for a in libre["adjuntos_en_orden"] if "fieldiag" in a["que"])[
            "estado"
        ]
    )  # control
    ruta = s["ruta_de_soporte"]
    assert ruta["oem"] == "GIGABYTE" and all(
        d.startswith(ir.ATLAS_RAIZ) for d in ruta["donde_leerla"]
    )
    assert (
        "dicho_por_personal_de_nvidia_en_foros" not in ruta
    )  # bb no guarda conocimiento: lo consulta en Atlas


def test_el_journal_del_kernel_para_adjuntar_no_lleva_el_hostname(monkeypatch):
    class R:
        returncode = 0
        stdout = "2026-10-11T12:13:14-06:00 mihost kernel: NVRM: algo\n2026-10-11T12:13:15-06:00 mihost kernel: otra\n"

    monkeypatch.setattr(ir.rv, "_journal", lambda *a: R())
    monkeypatch.setattr(ir, "_cmd", lambda *a: "mihost")
    t = ir.journal_kernel_anonimo(-1, "node-abc")
    assert "mihost" not in t and t.count("node-abc") == 2
    assert "NVRM: algo" in t  # control: se sustituye el host, no el contenido


def test_si_el_journal_no_se_puede_leer_el_adjunto_lo_dice_y_no_sale_vacio(monkeypatch):
    class Roto:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(ir.rv, "_journal", lambda *a: Roto())
    assert ir.journal_kernel_anonimo(-1, "node-abc").startswith(ir.COLLECTION_FAILED)


# ------------------------------------------------------------------ firmas (instrumento de bb)
def _firmas():
    import json

    return json.loads(ir.FIRMAS.read_text(encoding="utf-8"))["firmas"]


def test_todas_las_firmas_compilan_tienen_clase_valida_e_ids_unicos():
    import re

    f = _firmas()
    assert len({x["id"] for x in f}) == len(f)
    assert {x["clase"] for x in f} <= {"incidente", "ruido_conocido", "ambiguo"}
    for x in f:
        re.compile(x["regex"])
        assert x["atlas"]  # cada firma apunta a donde Atlas la documenta


def test_las_firmas_reconocen_lineas_literales_y_no_se_confunden():
    import re

    por = {x["id"]: x["regex"] for x in _firmas()}
    nomem = "NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY] (0x00000051) returned from _memdescAllocInternal(pMemDesc) @ mem_desc.c:1359"
    assert re.search(por["nvrm_nomem"], nomem)
    assert not re.search(por["nvrm_nomem_1361"], nomem)  # control: 1359 no es 1361
    assert re.search(
        por["xid_43"], "NVRM: Xid (PCI:000f:01:00): 43, pid=1617149, name=python3"
    )
    assert not re.search(
        por["xid_43"], "NVRM: Xid (PCI:000f:01:00): 13, Graphics SM Warp Exception"
    )
    assert re.search(
        por["mlx5_27w"],
        "mlx5_core 0000:01:00.0: mlx5_pcie_event:299: Detected insufficient power on the PCIe slot (27W).",
    )
    assert re.search(
        por["watchdog_no_paro"], "watchdog: watchdog0: watchdog did not stop!"
    )
    assert re.search(
        por["tecla_de_encendido"], "systemd-logind[2452]: Power key pressed short."
    )
    assert not re.search(por["oom_global"], "NVRM: algo sin relacion")


def test_coincidencias_separan_incidentes_de_ruido_y_distinguen_fallo_de_cero(
    monkeypatch,
):
    class R:
        def __init__(self, rc, out):
            self.returncode, self.stdout = rc, out

    monkeypatch.setattr(ir.rv, "_journal", lambda *a: R(0, "linea\nlinea\n"))
    c = ir.coincidencias_firmas(-1)
    assert {x["id"] for x in c["incidente"]} >= {"nvrm_nomem", "xid_43"}
    assert {x["id"] for x in c["ruido_conocido_contado_aparte"]} >= {
        "mlx5_27w"
    }  # el ruido NO va con los incidentes
    assert next(x for x in c["incidente"] if x["id"] == "nvrm_nomem")["lineas"] == 2
    monkeypatch.setattr(ir.rv, "_journal", lambda *a: R(1, ""))
    assert str(ir.coincidencias_firmas(-1)["incidente"][0]["lineas"]).startswith(
        "0 en el journal"
    )  # rc 1 = sin coincidencias
    monkeypatch.setattr(ir.rv, "_journal", lambda *a: R(2, ""))
    assert (
        ir.coincidencias_firmas(-1)["incidente"][0]["lineas"] == ir.COLLECTION_FAILED
    )  # error != cero


def test_si_el_archivo_de_firmas_falta_se_declara_y_no_se_inventa(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(ir, "FIRMAS", tmp_path / "no_existe.json")
    assert ir.coincidencias_firmas(-1)["estado"] == ir.COLLECTION_FAILED


def test_los_punteros_a_atlas_existen_si_atlas_esta_y_la_comprobacion_puede_fallar():
    """Relacion de informacion, no de codigo: bb solo LEE la ruta del documento en Atlas. Sin Atlas, se omite."""
    import re
    from pathlib import Path

    raiz = Path.home() / "projects/Atlas" / ir.ATLAS_RAIZ
    if not raiz.is_dir():
        import pytest

        pytest.skip("Atlas no esta en esta maquina")
    for x in _firmas():
        doc = x["atlas"].split("#")[0].split(" (")[0]
        if (
            "/" in doc
        ):  # `carpeta/prefijo`: debe existir al menos un archivo con ese prefijo
            carpeta, prefijo = doc.split("/", 1)
            assert list((raiz / carpeta).glob(prefijo + "*")), (x["id"], doc)
        else:
            assert (raiz / doc).exists(), (x["id"], doc)
        if "#" in x["atlas"]:
            ident = x["atlas"].split("#")[1]
            assert re.search(
                rf"^### {re.escape(ident)} ", (raiz / doc).read_text(encoding="utf-8"), re.M
            ), (x["id"], ident)
    # control negativo: un puntero roto debe fallar
    assert not re.search(
        r"^### github:S999 ", (raiz / "catalogo_destilado.md").read_text(encoding="utf-8"), re.M
    )


# ------------------------------------------------------------- calor sostenido para `bb scan`
def _escribe_telemetria(ruta, filas):
    import json

    ruta.write_text("".join(json.dumps(f) + "\n" for f in filas), encoding="utf-8")


def _muestra(ts, z, evento="muestra", **kw):
    return {
        "ts": ts,
        "evento": evento,
        "gpu_temp_c": 80.0,
        "zonas": [{"zona": "thermal_zone0", "temp_c": z}],
        "throttle": "0x0000000000000000",
        **kw,
    }


def test_residencia_ventana_solo_cuenta_las_muestras_dentro_de_la_ventana(tmp_path):
    from datetime import datetime, timezone

    f = tmp_path / "t.jsonl"
    filas = [
        _muestra(f"2026-10-11T18:{m:02d}:00.000000+00:00", 96.0) for m in range(0, 10)
    ]  # 10 muestras calientes
    filas += [
        _muestra("2026-10-11T17:00:00.000000+00:00", 96.0)
    ]  # fuera: una hora antes
    filas += [
        {
            "ts": "2026-10-11T18:05:00.000000+00:00",
            "evento": "temp_critica",
            "zona": "z",
        }
    ]  # no es muestra
    _escribe_telemetria(f, filas)
    a = datetime(2026, 10, 11, 18, 0, 0, tzinfo=timezone.utc).timestamp()
    b = datetime(2026, 10, 11, 18, 9, 59, tzinfo=timezone.utc).timestamp()
    r = ir.residencia_ventana(a, b, f)
    assert (
        r["estado"] == "ok" and r["muestras"] == 10
    )  # ni la de hace una hora ni el evento
    assert r["residencia"]["minutos_sobre_94.8C"] == round(10 * 5 / 60, 1)


def test_residencia_ventana_distingue_ventana_vacia_de_archivo_ausente_y_no_inventa_ceros(
    tmp_path,
):
    f = tmp_path / "t.jsonl"
    _escribe_telemetria(f, [_muestra("2026-10-11T18:00:00.000000+00:00", 96.0)])
    vacia = ir.residencia_ventana(0.0, 1.0, f)
    assert vacia["estado"].startswith(
        "0 muestras de telemetria entre"
    )  # el cero lleva su intervalo
    assert (
        ir.residencia_ventana(0.0, 1.0, tmp_path / "no_existe.jsonl")["estado"]
        == ir.NOT_COLLECTED
    )
    assert (
        "calor sostenido:" in ir.lineas_scan(vacia)[0]
        and ">85C" not in ir.lineas_scan(vacia)[0]
    )


def test_lineas_scan_imprime_la_racha_el_pico_y_el_throttle_decodificado(tmp_path):
    from datetime import datetime, timezone

    f = tmp_path / "t.jsonl"
    filas = [
        _muestra(
            f"2026-10-11T18:00:{s:02d}.000000+00:00",
            96.0,
            throttle="0x0000000000000020",
        )
        for s in range(0, 40, 5)
    ]
    _escribe_telemetria(f, filas)
    a = datetime(2026, 10, 11, 18, 0, 0, tzinfo=timezone.utc).timestamp()
    texto = "\n".join(ir.lineas_scan(ir.residencia_ventana(a, a + 60, f)))
    assert "SW_THERMAL_SLOWDOWN=8" in texto and "pico de zona 96.0 C" in texto
    assert "racha maxima >90C:" in texto


# --- FEATURE-INCIDENTE-CAMPOS-NO-COLECTADOS-01: fase de carga, progreso del engine, primera respuesta, adjuntos
# Todos los nombres llevan `fase_de_carga` porque ese es el filtro del close_check de la ficha.
def bbm(min_, gw="", mib=None, ts_base=0):
    """Muestra de `bb sample`: `gw` es el gw_salud 'run,wait,kv,preempt,gen,prompt,err' ('' = /metrics caido)."""
    m: dict[str, Any] = {
        "ts": f"2026-10-11T18:{min_ + ts_base:02d}:00+00:00",
        "boot_id": "b",
        "gw_salud": gw,
    }
    if mib is not None:
        m["gpu"] = [{"pid": 1, "mib": mib}]
    return m


def gws(run, gen, prompt, kv=0.16):
    return f"{run:g},0,{kv:.3f},0,{gen:g},{prompt:g},0"


def test_fase_de_carga_progreso_calcula_tok_s_de_los_contadores_y_un_reinicio_no_da_negativos():
    bb = [
        bbm(0, gws(4, 1000, 5000)),
        bbm(1, gws(4, 7000, 65000)),  # +6000 gen, +60000 prompt en 60 s
        bbm(2, gws(4, 100, 90)),  # el contador BAJA: el engine se reinicio
        bbm(3, gws(4, 700, 690)),
    ]
    p = ir.progreso_del_engine([], bb)
    assert p["estado"] == "ok" and p["generacion_tok_s"]["max"] == 100.0
    assert p["prompt_tok_s"]["max"] == 1000.0
    assert p["reinicios_del_contador"] == 1
    assert p["generacion_tok_s"]["min"] >= 0  # control: ningun par negativo


def test_fase_de_carga_progreso_detecta_la_firma_s11_y_no_la_confunde_con_decode():
    detenido = [bbm(i, gws(8, 500, 900, kv=0.04)) for i in range(5)]  # 8 peticiones, 0 tok/s
    p = ir.progreso_del_engine([], detenido)
    assert p["firma_S11_motor_detenido"].startswith("SI: 4 pares")
    vivo = [bbm(i, gws(8, 500 + 600 * i, 900)) for i in range(5)]  # control negativo: genera
    assert ir.progreso_del_engine([], vivo)["firma_S11_motor_detenido"].startswith("NO")
    ocioso = [bbm(i, gws(0, 500, 900)) for i in range(5)]  # control: sin peticiones no es S11
    assert ir.progreso_del_engine([], ocioso)["firma_S11_motor_detenido"].startswith("NO")


def test_fase_de_carga_progreso_sin_contadores_es_not_collected_y_no_cero():
    assert ir.progreso_del_engine([], [])["estado"].startswith(ir.NOT_COLLECTED)
    caido = [bbm(i, "") for i in range(5)]
    assert ir.progreso_del_engine([], caido)["estado"].startswith(ir.NOT_COLLECTED)
    solo_uno = [bbm(0, gws(1, 10, 10))]
    assert "0 pares medibles" in ir.progreso_del_engine([], solo_uno)["estado"]
    # telemetria vieja (sin contadores de tokens): se cae a bb sample, no se lee como 0 tok/s
    vieja = [fila(i * 5, vllm_num_requests_running=3.0) for i in range(4)]
    p = ir.progreso_del_engine(vieja, [bbm(0, gws(3, 0, 0)), bbm(1, gws(3, 60, 60))])
    assert p["fuente"].startswith("bb sample") and p["generacion_tok_s"]["ultimo"] == 1.0


def test_fase_de_carga_progreso_prefiere_la_telemetria_de_5_s_cuando_trae_tokens():
    tele = [
        fila(
            i * 5,
            vllm_num_requests_running=2.0,
            vllm_kv_cache_usage_perc=0.1,
            vllm_generation_tokens_total=1000.0 + 50 * i,
            vllm_prompt_tokens_total=0.0,
        )
        for i in range(4)
    ]
    p = ir.progreso_del_engine(tele, [bbm(0, gws(1, 0, 0))])
    assert p["fuente"].startswith("atom_gpu_telemetry")
    assert p["generacion_tok_s"]["ultimo"] == 10.0  # 50 tokens en 5 s


def test_fase_de_carga_distingue_carga_descarga_decode_prefill_inactivo_y_motor_detenido():
    def fase(bb):
        return ir.fase_de_carga(bb, "vacio", ir.progreso_del_engine([], bb))["fase"]

    assert fase([bbm(i, "", mib=3000 + 4000 * i) for i in range(5)]).startswith(
        "carga de modelo"
    )
    assert fase([bbm(i, "", mib=30000 - 4000 * i) for i in range(5)]).startswith(
        "descarga de modelo"
    )
    assert fase(
        [bbm(i, gws(4, 100 + 600 * i, 100 + 600 * i), mib=30000) for i in range(5)]
    ).startswith("decode")
    assert fase(
        [bbm(i, gws(4, 100, 100 + 600 * i), mib=30000) for i in range(5)]
    ).startswith("prefill")
    assert fase([bbm(i, gws(0, 100, 100), mib=30000) for i in range(5)]).startswith(
        "inactivo"
    )
    assert fase([bbm(i, gws(8, 100, 100), mib=30000) for i in range(5)]).startswith(
        "motor detenido"
    )


def test_fase_de_carga_un_boot_sin_carga_no_sale_con_fase_de_carga_ni_de_decode():
    # control negativo de la ficha: sin carga la fase NO es carga de modelo
    sin_carga = ir.fase_de_carga(
        [bbm(i, "", mib=0) for i in range(5)], "vacio", ir.progreso_del_engine([], [])
    )["fase"]
    assert sin_carga.startswith("sin carga") and "carga de modelo" not in sin_carga
    estable = ir.fase_de_carga(
        [bbm(i, "", mib=20000) for i in range(5)],
        "vacio",
        ir.progreso_del_engine([], []),
    )["fase"]
    assert estable.startswith(
        "indeterminada"
    )  # sin /metrics y memoria quieta: no se inventa una fase
    sin_gpu = ir.fase_de_carga([bbm(i, "") for i in range(5)], "vacio", {})["fase"]
    assert sin_gpu.startswith(ir.NOT_COLLECTED)
    assert ir.fase_de_carga([], "VACIO-DE-LA-FUENTE", {})["fase"] == "VACIO-DE-LA-FUENTE"


def test_fase_de_carga_training_y_nccl_se_declaran_unsupported_no_se_infieren():
    r = ir.fase_de_carga([bbm(0, gws(1, 1, 1))], "vacio", {})
    assert set(r["fases_no_distinguibles"]) == {"training", "NCCL setup"}
    assert all(v.startswith(ir.UNSUPPORTED) for v in r["fases_no_distinguibles"].values())


def test_fase_de_carga_muestras_bb_filtra_por_boot_y_distingue_ausente_de_cero(tmp_path):
    assert ir.muestras_bb_del_boot("aabbccdd" * 4, tmp_path / "no_existe")[1].startswith(
        ir.NOT_COLLECTED
    )
    marca = "aabbccdd-aabb-ccdd-aabb-ccddaabbccdd"
    (tmp_path / "2026-10-11.jsonl").write_text(
        json.dumps({"ts": "x", "boot_id": marca})
        + "\n"
        + json.dumps({"ts": "y", "boot_id": "otro"})
        + "\n"
        + '{"ts": "truncada", "boot_id": "'
        + marca
        + '"',
        encoding="utf-8",
    )
    filas, _ = ir.muestras_bb_del_boot("aabbccdd" * 4, tmp_path)
    assert [m["ts"] for m in filas] == ["x"]  # ni el otro boot ni la fila truncada
    vacias, motivo = ir.muestras_bb_del_boot("11" * 16, tmp_path)
    assert vacias == [] and motivo.startswith("0 muestras")  # el cero lleva su alcance


def test_fase_de_carga_primera_respuesta_de_aplicacion_no_cuenta_el_boot_sin_metrics():
    sin = [
        fila(i * 5, vllm_num_requests_running=None, vllm_ausente="no alcanzable")
        for i in range(3)
    ]
    r = ir.primera_respuesta_de_aplicacion(sin, [])
    assert r["ts"].startswith("0 respuestas en 3 muestras")  # cero observado, con su alcance
    con = sin + [fila(15, vllm_num_requests_running=1.0)]
    r = ir.primera_respuesta_de_aplicacion(con, [])
    assert (
        r["segundos_desde_la_primera_muestra_del_boot"] == 15.0
        and r["incertidumbre"] == "+-5 s"
    )
    assert ir.primera_respuesta_de_aplicacion([], [])["ts"] == ir.NOT_COLLECTED
    r = ir.primera_respuesta_de_aplicacion([], [bbm(0, ""), bbm(2, gws(1, 1, 1))])
    assert (
        r["segundos_desde_la_primera_muestra_del_boot"] == 120.0
        and "bb sample" in r["fuente"]
    )


def test_fase_de_carga_seis_timestamps_lleva_la_primera_respuesta_y_sin_ella_lo_dice():
    ms = [fila(0), fila(60)]
    pr = {"ts": "2026-10-11T19:28:40+00:00", "fuente": "F", "incertidumbre": "+-5 s"}
    fila6 = ir.seis_timestamps({}, ms, {}, 1791742398, pr)[5]
    assert "primera respuesta de aplicacion: 2026-10-11T19:28:40" in fila6["ts"]
    sin = ir.seis_timestamps({}, ms, {}, 1791742398, None)[5]
    assert "no se midio" in sin["incertidumbre"] and "primera respuesta" not in sin["ts"]
    nc = {"ts": ir.NOT_COLLECTED, "fuente": "x", "incertidumbre": ir.NOT_COLLECTED}
    assert "primera respuesta" not in ir.seis_timestamps({}, ms, {}, 1791742398, nc)[5]["ts"]


def test_fase_de_carga_adjuntos_reconoce_el_archivo_presente_y_si_falta_dice_por_que(
    tmp_path,
):
    plat = {"oem": "GIGABYTE", "secure_boot": "enabled"}
    vacio = ir.adjuntos_y_ruta(plat, "bb-X", tmp_path, uid=1000)["adjuntos_en_orden"]
    assert vacio[0]["estado"].startswith(ir.NOT_COLLECTED)
    assert "root: no (uid 1000)" in vacio[0]["estado"]
    assert "boot actual, no el del incidente" in vacio[0]["estado"]
    assert "bloqueado: Secure Boot enabled" in vacio[1]["estado"]
    (tmp_path / "bb-X.nvidia-bug-report.log.gz").write_bytes(b"x" * 7)
    (tmp_path / "bb-X.fieldiag-summary.json").write_text("{}", encoding="utf-8")
    puesto = ir.adjuntos_y_ruta(plat, "bb-X", tmp_path, uid=1000)["adjuntos_en_orden"]
    assert puesto[0]["estado"].startswith("presente:") and "(7 bytes)" in puesto[0]["estado"]
    assert puesto[1]["estado"].startswith("presente:")
    otro = ir.adjuntos_y_ruta(plat, "bb-OTRO", tmp_path, uid=1000)["adjuntos_en_orden"]
    assert otro[0]["estado"].startswith(ir.NOT_COLLECTED)  # control: adjunto de otro incidente
    como_root = ir.adjuntos_y_ruta(plat, "bb-X", tmp_path / "v", uid=0)
    assert "root: si" in como_root["adjuntos_en_orden"][0]["estado"]


# --- FEATURE-INCIDENTE-CARGA-DE-ATLAS-01
BOOT = "54b7161869da4fc99f7becb9571f529d"
BOOT_G = "54b71618-69da-4fc9-9f7b-ecb9571f529d"


def _atlas_log(tmp_path, lineas):
    f = tmp_path / "liberation_watchdog.jsonl"
    f.write_text("\n".join(json.dumps(x) for x in lineas) + "\n", encoding="utf-8")
    return f


def _start(jf, boot=BOOT_G, ts="2026-10-11T11:35:08"):
    return {
        "ts": ts,
        "event": "job_start",
        "job_file": jf,
        "name": jf[:-5],
        "boot_id": boot,
        "memory_max_gb": 12,
        "timeout_minutes": 180,
        "command": "echo",
    }


def _done(jf):
    return {"ts": "2026-10-11T11:40:00", "event": "job_done", "job_file": jf, "exit_code": 0}


def test_carga_de_atlas_lista_solo_los_jobs_del_boot_sin_job_done(tmp_path):
    f = _atlas_log(
        tmp_path,
        [
            _start("a.json"),
            _done("a.json"),  # terminado: no corria al cortar
            _start("b.json"),  # abierto: corria al cortar
            _start("c.json", boot="00000000-0000-0000-0000-000000000000"),  # otro boot
            {
                "ts": "t",
                "event": "job_orphaned",
                "job_file": "b.json",
                "boot_id_al_arrancar": BOOT_G,
            },
        ],
    )
    r = ir.carga_de_atlas(BOOT, f)
    assert (
        r["estado"] == "ok"
        and r["jobs_iniciados_en_el_boot"] == 2
        and r["jobs_terminados_en_el_boot"] == 1
    )
    [job] = r["jobs_en_ejecucion_al_cortar"]
    assert job["job_file"] == "b.json" and job["atlas_lo_registro_huerfano"] is True
    assert job["memory_max_gb"] == 12 and "command" not in job  # el comando no se copia


def test_carga_de_atlas_un_reintento_cuenta_por_su_ultimo_job_start(tmp_path):
    f = _atlas_log(tmp_path, [_start("a.json"), _done("a.json"), _start("a.json")])
    r = ir.carga_de_atlas(BOOT, f)
    assert [j["job_file"] for j in r["jobs_en_ejecucion_al_cortar"]] == ["a.json"]
    cerrado = ir.carga_de_atlas(
        BOOT, _atlas_log(tmp_path, [_start("a.json"), _done("a.json")])
    )
    # control: cuando todo cerro, el cero se dice con su alcance y no sale una lista vacia muda
    assert cerrado["jobs_en_ejecucion_al_cortar"].startswith("0 jobs sin job_done de 1")


def test_carga_de_atlas_sin_jobs_del_boot_dice_el_alcance_y_sin_archivo_es_not_collected(
    tmp_path,
):
    r = ir.carga_de_atlas(BOOT, _atlas_log(tmp_path, [_start("c.json", boot="otro")]))
    assert r["estado"].startswith(f"0 job_start con boot_id {BOOT_G} en 1 lineas")
    assert "jobs_en_ejecucion_al_cortar" not in r  # un cero no se rellena con una lista
    assert ir.carga_de_atlas(BOOT, tmp_path / "no_existe.jsonl")["estado"].startswith(
        ir.NOT_COLLECTED
    )


def test_carga_de_atlas_archivo_ilegible_es_collection_failed_no_ausente(tmp_path):
    f = tmp_path / "liberation_watchdog.jsonl"
    f.write_bytes(b"\xff\xfe\x00 no es utf-8\n" + b'{"event": "job_start"}\n')
    assert ir.carga_de_atlas(BOOT, f)["estado"] == ir.COLLECTION_FAILED


def test_carga_de_atlas_es_solo_lectura_y_sin_import_de_codigo_de_atlas():
    from pathlib import Path

    fuente = Path(ir.__file__).read_text(encoding="utf-8")
    assert not re.search(r"^\s*(from|import)\s+atlas", fuente, re.M | re.I)


def test_carga_de_atlas_el_markdown_la_imprime_como_seccion():
    rep = {
        "formato": "bb-incident/1",
        "resumen": {"incident_id": "i", "nodo_anonimizado": "n", "veredicto": "v"},
        "seis_timestamps": [],
        "carga_de_atlas": {"estado": ir.NOT_COLLECTED},
    }
    assert "Carga de atlas" in ir.md(rep)
