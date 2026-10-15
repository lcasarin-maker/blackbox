"""Veredicto por reinicio: cada rama con el caso que la activa y el que NO."""

import json
import os
from datetime import datetime
from types import SimpleNamespace

import pytest

from tools import reboot_verdict as rv
from tools.reboot_verdict import disparador, veredicto

pytestmark = pytest.mark.unit

BASE = {"telemetria": {"psi_mem_full_avg10": 0.0}}


def etiqueta(**kw):
    return veredicto({**BASE, **kw})["etiqueta"]


def test_corte_abrupto_es_el_caso_sin_nada_mas_y_declara_lo_que_no_pudo_correr():
    v = veredicto({**BASE})
    assert v["etiqueta"] == "CORTE_ABRUPTO"
    assert (
        "observador_externo" in v["could_not_run"]
    )  # un corte abrupto nunca sale "limpio"


def test_colapso_por_journal_y_por_psi_pero_no_con_psi_cero():
    assert etiqueta(colapso_en_ventana=True) == "COLAPSO_MEMORIA"
    assert etiqueta(telemetria={"psi_mem_full_avg10": 72.3}) == "COLAPSO_MEMORIA"
    assert (
        etiqueta() != "COLAPSO_MEMORIA"
    )  # control negativo: PSI 0.0 como los 4 cortes reales


def test_cierre_ordenado_exige_el_target_y_no_se_confunde_con_corte():
    assert etiqueta(cierre="reboot") == "CIERRE_ORDENADO_REBOOT"
    assert etiqueta(cierre="poweroff") == "CIERRE_ORDENADO_POWEROFF"
    assert etiqueta(cierre=None) != "CIERRE_ORDENADO_REBOOT"


def test_disparador_ausente_se_declara_no_registrado():
    v = veredicto({**BASE, "cierre": "reboot"})
    assert "NO_REGISTRADO" in v["razones"][0]
    v = veredicto(
        {**BASE, "cierre": "reboot", "disparador": "sudo ... COMMAND=/usr/sbin/reboot"}
    )
    assert "NO_REGISTRADO" not in v["razones"][0]


def test_panic_gana_a_colapso_y_a_cierre():
    assert (
        etiqueta(panic=True, colapso_en_ventana=True, cierre="reboot") == "PANIC_KERNEL"
    )
    assert etiqueta(panic=False) != "PANIC_KERNEL"


def test_journal_parado_sin_target_no_se_rotula_cierre():
    assert etiqueta(journal_parado=True) == "INDETERMINADO"


def test_observador_externo_separa_red_de_apagado_interno():
    assert etiqueta(externo={"voltaje_perdido": True}) == "CORTE_DE_RED"
    assert etiqueta(externo={"voltaje_perdido": False}) == "APAGADO_INTERNO"
    v = veredicto({**BASE, "externo": {"voltaje_perdido": True}})
    assert "observador_externo" not in v["could_not_run"]


def test_fuente_ilegible_pasa_a_could_not_run():
    v = veredicto({**BASE, "no_se_pudo_leer": ["journal_boot_-3"]})
    assert "journal_boot_-3" in v["could_not_run"]


def test_watchdog_bootstatus_distinto_de_cero_se_anota():
    assert any(
        "bootstatus=2" in r
        for r in veredicto({**BASE, "bootstatus_siguiente": 2})["razones"]
    )
    assert not any(
        "bootstatus" in r
        for r in veredicto({**BASE, "bootstatus_siguiente": 0})["razones"]
    )


def test_disparador_reconoce_sudo_y_logind_y_devuelve_none_sin_ellos():
    ruido = ["oct 10 13:44:40 h systemd[1]: Stopped target swap.target"]
    assert disparador(ruido) is None
    assert disparador(ruido + ["h sudo[1]: u : COMMAND=/usr/sbin/reboot"]) is not None
    assert (
        disparador(ruido + ["h systemd-logind[9]: Power key pressed short."])
        is not None
    )


def test_disparador_reconoce_las_frases_reales_de_logind_medidas_el_2026_10_10():
    # texto literal del journal del boot 295efc0f, 13:44:38 (el regex original no lo vio)
    real = "2026-10-10T13:44:38-06:00 h systemd-logind[2452]: The system will power off now!"
    assert disparador([real]) is not None
    assert disparador(["h systemd-logind[2452]: System is powering down."]) is not None
    assert (
        disparador(["h systemd-logind[2452]: New session 3 of user lcasarin."]) is None
    )  # no es cierre


def test_la_fila_lleva_la_palabra_bert_0x14_del_arranque_siguiente_y_nada_si_no_hay():
    con = veredicto(
        {
            **BASE,
            "bert": {
                "palabra_en_0x14": "00000100",
                "section_guid": "3c1e3f4b-1e1a-43df-af28-59820e958e3c",
            },
        }
    )
    assert con["bert_palabra_0x14"] == "00000100" and con["bert_guid"].startswith(
        "3c1e3f4b"
    )
    sin = veredicto({**BASE})
    assert (
        sin["bert_palabra_0x14"] is None and sin["bert_guid"] is None
    )  # control: sin registro no se inventa una palabra


# ------------------------------------------------- forense movido desde Atlas (detect_atom_crash)
# DEBT-CONTRATO-ATLAS-INSTRUMENTOS-EN-BLACKBOX-01: la medicion vive en bb; Atlas solo lee la fila.
SMART_SIN_PERMISO = (
    "smartctl 7.4 2023-08-01 r5530 [aarch64-linux-6.17.0-1031-nvidia] (local build)\n"
    "Copyright (C) 2002-23, Bruce Allen, Christian Franke, www.smartmontools.org\n"
    "\n"
    "Smartctl open device: /dev/nvme0n1 failed: Permission denied\n"
)
SMART_CON_PERMISO = (
    "smartctl 7.4 2023-08-01 r5530 [aarch64-linux] (local build)\n"
    "Copyright (C) 2002-23, Bruce Allen, Christian Franke\n"
    "\n"
    "=== START OF SMART DATA SECTION ===\n"
    "SMART overall-health self-assessment test result: PASSED\n"
    "Temperature:                        41 Celsius\n"
)


def test_patrones_de_diagnostico_no_casan_el_ruido_de_un_boot_normal():
    for linea in (
        "kernel: ACPI: thermal: Thermal Zone [TSOC] (47 C)",
        "kernel: watchdog: NMI not fully supported",
        "kernel: watchdog: Hard watchdog permanently disabled",
        "kernel: simple-framebuffer simple-framebuffer.0: [drm] Registered 1 planes with drm panic",
    ):
        assert not rv.PATRONES_DIAGNOSTICO.search(linea), linea


def test_patrones_de_diagnostico_casan_los_eventos_reales():
    for linea in (
        "kernel: NVRM: Xid (PCI:000f:01:00): 13, Graphics SM Warp Exception",
        "kernel: workqueue: mmput_async_fn hogged CPU for >20000us 11 times",
        "kernel: Out of memory: Killed process 1234 (python3)",
        "kernel: Xid (PCI:0000:01:00): 79, algo",
        "kernel: GPU has fallen off the bus",
    ):
        assert rv.PATRONES_DIAGNOSTICO.search(linea), linea


def test_xids_con_la_forma_real_y_sin_inventar_uno():
    xids = rv.xids_del_boot(
        [
            "kernel: NVRM: Xid (PCI:000f:01:00): 13, Graphics SM Warp Exception",
            "kernel: NVRM: Xid (PCI:000f:01:00): 43, pid=39320, name=python3",
        ]
    )
    assert [(x["xid"], x["pid"]) for x in xids] == [(13, None), (43, 39320)]
    assert rv.xids_del_boot(["kernel: workqueue: hogged CPU for >20000us"]) == []


def test_crash_confirmado_es_journal_corrupto_o_panic_y_nada_mas():
    base = {"inicio_epoch": 1000.0, "fin_epoch": 4600.0}
    assert rv.forense({**base, "journal_danado": "/var/log/journal/x/system.journal"})[
        "crash_confirmado"
    ]
    assert rv.forense({**base, "panic_linea": "Kernel panic - not syncing: hung_task"})[
        "crash_confirmado"
    ]
    # control negativo: sin ninguna de las dos no se confirma, haya o no cierre de PID 1
    assert not rv.forense({**base, "cierre_pid1": False})["crash_confirmado"]
    assert not rv.forense({**base, "cierre_pid1": True})["crash_confirmado"]
    f = rv.forense(base)
    assert f["esquema"] == "bb-reboot/1" and f["duracion_s"] == 3600.0
    assert rv.forense({})["duracion_s"] is None  # sin horas no hay duracion, nunca 0


def test_smart_sin_permiso_se_declara_y_legible_se_registra(monkeypatch):
    monkeypatch.setattr(rv, "_correr_con_codigo", lambda *a: (2, SMART_SIN_PERMISO))
    s = rv.salud_de_almacenamiento()
    assert s["smart_no_disponible"] == "permiso denegado, requiere root"
    assert "smart" not in s
    monkeypatch.setattr(rv, "_correr_con_codigo", lambda *a: (0, SMART_CON_PERMISO))
    s = rv.salud_de_almacenamiento()
    assert "smart_no_disponible" not in s and any("PASSED" in ln for ln in s["smart"])
    assert not any(ln.startswith(("smartctl ", "Copyright (")) for ln in s["smart"])
    monkeypatch.setattr(rv, "_correr_con_codigo", lambda *a: (-1, "No such file"))
    assert "no ejecutable" in rv.salud_de_almacenamiento()["smart_no_disponible"]
    monkeypatch.setattr(rv, "_correr_con_codigo", lambda *a: (1, "Use smartctl -h\n"))
    assert "sin datos SMART" in rv.salud_de_almacenamiento()["smart_no_disponible"]


def test_edac_sin_controladores_ausente_y_legible(tmp_path, monkeypatch):
    edac = tmp_path / "mc"
    edac.mkdir()
    monkeypatch.setattr(rv, "EDAC_DIR", edac)
    assert "sin controladores" in rv._edac()["edac_no_disponible"]
    (edac / "mc0").mkdir()
    (edac / "mc0" / "ce_count").write_text("7\n", encoding="utf-8")
    (edac / "mc0" / "ue_count").write_text("0\n", encoding="utf-8")
    assert rv._edac() == {"edac": {"mc0_ce_count": 7, "mc0_ue_count": 0}}
    (edac / "mc0" / "ue_count").write_text("basura\n", encoding="utf-8")
    ilegible = rv._edac()["edac"]["mc0_ue_count"]
    assert ilegible.startswith("ilegible")  # un contador roto no se lee como cero
    monkeypatch.setattr(rv, "EDAC_DIR", tmp_path / "no_existe")
    assert "no existe" in rv._edac()["edac_no_disponible"]


def test_vmcore_solo_el_volcado_escrito_en_el_hueco_del_corte(tmp_path, monkeypatch):
    crash = tmp_path / "crash"
    dentro, viejo = crash / "202610111300", crash / "202609010000"
    for d, t in ((dentro, 5000), (viejo, 100)):
        d.mkdir(parents=True)
        (d / "dump.x").write_text("vmcore", encoding="utf-8")
        os.utime(d, (t, t))
    (crash / "kexec_cmd").write_text("no es volcado", encoding="utf-8")
    monkeypatch.setattr(rv, "CRASH_DIR", crash)
    assert rv.vmcore_en(4000, 6000) == str(dentro)
    # control negativo: el volcado viejo NO se atribuye a un corte posterior (Atlas si lo hacia)
    assert rv.vmcore_en(7000, 9000) is None
    monkeypatch.setattr(rv, "CRASH_DIR", tmp_path / "sin_crash")
    assert rv.vmcore_en(0, None) is None


def _journal_falso(respuestas):
    def _journal(*args):
        for clave, (rc, salida) in respuestas.items():
            if all(x in args for x in clave):
                return SimpleNamespace(returncode=rc, stdout=salida, stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    return _journal


BOOTS = [
    {
        "index": -1,
        "boot_id": "a" * 32,
        "first_entry": 1_000_000_000,
        "last_entry": 4_600_000_000,
    },
    {
        "index": 0,
        "boot_id": "b" * 32,
        "first_entry": 4_700_000_000,
        "last_entry": 4_800_000_000,
    },
]


def _recoge(monkeypatch, tmp_path, respuestas):
    monkeypatch.setattr(rv, "TELEMETRIA", tmp_path / "no_hay.jsonl")
    monkeypatch.setattr(rv, "CRASH_DIR", tmp_path / "sin_crash")
    monkeypatch.setattr(rv, "WATCHDOG_BOOTSTATUS", tmp_path / "bootstatus")
    monkeypatch.setattr(rv, "_journal", _journal_falso(respuestas))
    return rv.recoge(BOOTS, 0)


def test_recoge_lee_journal_corrupto_del_siguiente_y_lineas_del_caido(
    monkeypatch, tmp_path
):
    ev = _recoge(
        monkeypatch,
        tmp_path,
        {
            ("systemd-journald.service",): (
                0,
                "File /var/log/journal/x/system.journal corrupted or uncleanly shut "
                "down, renaming and replacing.",
            ),
            ("-k", "-1"): (
                0,
                "k: NVRM: Xid (PCI:000f:01:00): 43, pid=7, name=p\nk: normal\n",
            ),
        },
    )
    f = rv.forense(ev)
    assert f["journal_danado"] == "/var/log/journal/x/system.journal"
    assert f["crash_confirmado"] and f["cierre_pid1"] is False
    assert f["xids"][0]["xid"] == 43 and len(f["lineas_diagnostico"]) == 1


def test_recoge_control_negativo_cierre_limpio_no_confirma_crash(monkeypatch, tmp_path):
    ev = _recoge(
        monkeypatch, tmp_path, {("_PID=1",): (0, "Reached target x\nShutting down.\n")}
    )
    f = rv.forense(ev)
    assert f["cierre_pid1"] is True and not f["crash_confirmado"]
    assert f["journal_danado"] is None


def test_recoge_journal_ilegible_va_a_could_not_run_no_a_limpio(monkeypatch, tmp_path):
    ev = _recoge(
        monkeypatch,
        tmp_path,
        {("_PID=1",): (1, ""), ("systemd-journald.service",): (1, "")},
    )
    assert ev["cierre_pid1"] is None  # no leido: ni True ni False
    assert "journal_pid1_boot_-1" in ev["no_se_pudo_leer"]
    assert "journal_journald_boot_0" in ev["no_se_pudo_leer"]


def test_main_escribe_fila_con_esquema_y_forense(monkeypatch, tmp_path):
    monkeypatch.setattr(rv, "SALIDA", tmp_path / "reboots.jsonl")
    monkeypatch.setattr(rv, "TELEMETRIA", tmp_path / "no_hay.jsonl")
    monkeypatch.setattr(rv, "CRASH_DIR", tmp_path / "sin_crash")
    monkeypatch.setattr(rv, "WATCHDOG_BOOTSTATUS", tmp_path / "bootstatus")
    monkeypatch.setattr(rv, "_correr_con_codigo", lambda *a: (2, SMART_SIN_PERMISO))
    monkeypatch.setattr(rv, "_publica_hallazgos", lambda filas: None)
    monkeypatch.setattr(
        rv, "_journal", _journal_falso({("--list-boots",): (0, json.dumps(BOOTS))})
    )
    assert rv.main(["--ultimos", "1", "--escribe"]) == 0
    fila = json.loads((tmp_path / "reboots.jsonl").read_text(encoding="utf-8"))
    assert fila["esquema"] == "bb-reboot/1" and fila["boot_id_siguiente"] == "b" * 32
    assert (
        fila["almacenamiento"]["smart_no_disponible"]
        == "permiso denegado, requiere root"
    )
    assert fila["crash_confirmado"] is False and fila["cierre_pid1"] is False


def test_evidencia_externa_une_el_medidor_con_el_veredicto(tmp_path):
    import json as _j
    from tools import reboot_verdict as rv

    ruta = tmp_path / "e.jsonl"
    assert rv._evidencia_externa(1000, 255, ruta) == (None, None)  # sin medidor: sigue CORTE_ABRUPTO por falta de observador
    filas = [{"epoch": 999, "ok": True, "voltaje_v": 120, "potencia_w": 40}, {"epoch": 1001, "ok": True, "voltaje_v": 120, "potencia_w": 0.2}, {"epoch": 1002, "ok": True, "voltaje_v": 120, "potencia_w": 0.2}]
    ruta.write_text("\n".join(_j.dumps(f) for f in filas) + "\n", encoding="utf-8")
    ext, nc = rv._evidencia_externa(1000, 255, ruta)
    assert nc is None and ext is not None and ext["voltaje_perdido"] is False
    assert etiqueta(externo=ext) == "APAGADO_INTERNO"  # el mismo dato produce el veredicto
    ruta.write_text(_j.dumps({"epoch": 1001, "ok": False}) + "\n", encoding="utf-8")
    ext2, nc2 = rv._evidencia_externa(1000, 255, ruta)
    assert ext2 is None and nc2 is not None and "no concluyente" in nc2  # un enchufe mudo se declara, no se adivina


def test_anade_evidencia_externa_modifica_el_ev_solo_si_hay_algo_que_decir(tmp_path):
    import json as _j
    from tools import reboot_verdict as rv

    ruta = tmp_path / "e.jsonl"
    ev = {"hueco_s": 255, "no_se_pudo_leer": []}
    rv._anade_evidencia_externa(ev, 1000, ruta)
    assert "externo" not in ev and ev["no_se_pudo_leer"] == []
    ruta.write_text(_j.dumps({"epoch": 1001, "ok": False}) + "\n", encoding="utf-8")
    rv._anade_evidencia_externa(ev, 1000, ruta)
    assert "externo" not in ev and "medidor_externo" in ev["no_se_pudo_leer"][0]
    ruta.write_text(_j.dumps({"epoch": 1001, "ok": True, "voltaje_v": 3, "potencia_w": 0}) + "\n", encoding="utf-8")
    rv._anade_evidencia_externa(ev, 1000, ruta)
    assert ev["externo"]["voltaje_perdido"] is True


# ------------------------------------------------- ramas sin cubrir: ejecutables reales en PATH, bert, telemetria, main
def _ejecutable(directorio, nombre, cuerpo):
    ruta = directorio / nombre
    ruta.write_text("#!/bin/sh\n" + cuerpo + "\n", encoding="utf-8")
    ruta.chmod(0o755)
    return ruta


def _solo_path(monkeypatch, directorio):
    monkeypatch.setenv("PATH", f"{directorio}:/usr/bin:/bin")


def test_externo_sin_conclusion_deja_el_corte_abrupto_sin_atribuir_causa():
    v = veredicto({**BASE, "externo": {"voltaje_perdido": None}})
    assert v["etiqueta"] == "CORTE_ABRUPTO"
    assert not any("medidor externo" in r for r in v["razones"])  # no inventa ni red ni apagado interno
    assert "observador_externo" not in v["could_not_run"]  # hay un observador: solo que no concluye


def test_cierre_por_logind_dice_que_quien_lo_pidio_no_consta():
    v = veredicto({**BASE, "cierre": "reboot", "disparador": "h systemd-logind[9]: The system will reboot now!"})
    assert v["etiqueta"] == "CIERRE_ORDENADO_REBOOT"
    assert "orden ejecutada por logind" in v["razones"][0] and "QUIEN la pidio no consta" in v["razones"][0]
    sudo = veredicto({**BASE, "cierre": "reboot", "disparador": "h sudo[1]: u : COMMAND=/usr/sbin/reboot"})
    assert sudo["razones"][0].startswith("pedido por sudo")  # control: con COMMAND= es la otra rama


def test_correr_con_codigo_devuelve_codigo_y_salida_de_un_ejecutable_real(tmp_path, monkeypatch):
    _ejecutable(tmp_path, "smartctl", "echo salida-stdout; echo salida-stderr >&2; exit 3")
    _solo_path(monkeypatch, tmp_path)
    codigo, salida = rv._correr_con_codigo("smartctl", "-H")
    assert codigo == 3 and "salida-stdout" in salida and "salida-stderr" in salida


def test_correr_con_codigo_menos_uno_si_el_ejecutable_no_existe_o_se_cuelga(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))  # vacio
    codigo, mensaje = rv._correr_con_codigo("smartctl-que-no-existe")
    assert codigo == -1 and "smartctl-que-no-existe" in mensaje

    def cuelga(*_a, **_k):
        raise rv.subprocess.TimeoutExpired("smartctl", 60)

    monkeypatch.setattr(rv.subprocess, "run", cuelga)
    codigo, mensaje = rv._correr_con_codigo("smartctl")
    assert codigo == -1 and "timed out after 60" in mensaje


def test_journal_real_pasa_los_argumentos_a_journalctl_con_no_pager(tmp_path, monkeypatch):
    _ejecutable(tmp_path, "journalctl", 'printf "%s\\n" "$@"')
    _solo_path(monkeypatch, tmp_path)
    r = rv._journal("-b", "-1", "-k")
    assert r.returncode == 0 and r.stdout.splitlines() == ["--no-pager", "-b", "-1", "-k"]


def test_ultima_telemetria_toma_la_ultima_muestra_del_boot_y_acepta_id_con_o_sin_guiones(tmp_path, monkeypatch):
    plano = "0123456789abcdef0123456789abcdef"
    guiones = "01234567-89ab-cdef-0123-456789abcdef"
    otro = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    t = tmp_path / "t.jsonl"
    filas = [
        {"evento": "muestra", "boot_id": guiones, "n": 1},
        {"evento": "muestra", "boot_id": otro, "n": 9},
        {"evento": "arranque", "boot_id": guiones, "n": 5},  # no es una muestra
        {"evento": "muestra", "boot_id": guiones, "n": 2},
    ]
    t.write_text("\n".join(json.dumps(f) for f in filas) + "\n", encoding="utf-8")
    monkeypatch.setattr(rv, "TELEMETRIA", t)
    ultima_plano = rv._ultima_telemetria(plano)
    assert ultima_plano is not None
    assert ultima_plano["n"] == 2  # el id plano se convierte a la forma con guiones
    ultima_guiones = rv._ultima_telemetria(guiones)
    assert ultima_guiones is not None
    assert ultima_guiones["n"] == 2
    assert rv._ultima_telemetria("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa") is None  # control negativo: boot sin muestras
    monkeypatch.setattr(rv, "TELEMETRIA", tmp_path / "ausente.jsonl")
    assert rv._ultima_telemetria(plano) is None


def test_disparador_boot_consulta_logind_y_sudo_y_prefiere_la_ultima_linea_que_nombra_la_orden(tmp_path, monkeypatch):
    _ejecutable(tmp_path, "journalctl", 'case "$5" in\n'
                '  systemd-logind) echo "h systemd-logind[9]: The system will reboot now!";;\n'
                '  sudo) [ -n "$SUDO_LINEA" ] && echo "$SUDO_LINEA";;\nesac')
    _solo_path(monkeypatch, tmp_path)
    monkeypatch.delenv("SUDO_LINEA", raising=False)
    solo_logind = rv._disparador_boot(-1)
    assert solo_logind is not None
    assert "systemd-logind" in solo_logind  # solo logind habla
    monkeypatch.setenv("SUDO_LINEA", "h sudo[1]: u : COMMAND=/usr/sbin/reboot")
    con_sudo = rv._disparador_boot(-1)
    assert con_sudo is not None
    assert "COMMAND=/usr/sbin/reboot" in con_sudo  # sudo es la ultima en el orden de consulta
    _ejecutable(tmp_path, "journalctl", "exit 0")
    assert rv._disparador_boot(-1) is None  # control negativo: ninguna linea nombra la orden


BERT_BLOQUE = [
    "ACPI: BERT 0x000000008 000030 (v01 NVIDIA MTKID   00000001)",
    "BERT: Error records from previous boot:",
    "[Hardware Error]: event severity: fatal",
    "[Hardware Error]:  Error 0, type: fatal",
    "[Hardware Error]:   section type: unknown, 3c1e3f4b-1e1a-43df-af28-59820e958e3c",
    "[Hardware Error]:   section length: 0x40",
    "[Hardware Error]:   00000000: aaaaaaaa bbbbbbbb cccccccc dddddddd",
    "[Hardware Error]:   00000010: 11111111 22222222 33333333 44444444",
    "BERT: Total records found: 1",
    "[Hardware Error]:   00000010: 99999999 88888888",  # ruido posterior al bloque: no debe entrar
]


def test_bert_registro_lee_cada_campo_del_bloque_y_la_palabra_en_0x14(monkeypatch):
    monkeypatch.setattr(rv, "_journal", _journal_falso({("-k", "cat"): (0, "\n".join(BERT_BLOQUE))}))
    r = rv.bert_registro(0)
    assert r["severidad"] == "fatal" and r["section_length"] == "0x40"
    assert r["section_guid"] == rv.GUID_MTKID and r["misma_clase_que_cita_el_personal_de_nvidia"] is True
    assert r["creador_tabla_acpi"] == "MTKID" and r["palabra_en_0x14"] == "22222222"
    assert r["volcado_hex"] == {"00000000": "aaaaaaaa bbbbbbbb cccccccc dddddddd",
                                "00000010": "11111111 22222222 33333333 44444444"}


def test_bert_registro_con_bloque_pobre_declara_not_collected_en_vez_de_inventar(monkeypatch):
    pobre = ["BERT: Error records from previous boot:", "[Hardware Error]: algo sin los campos esperados"]
    monkeypatch.setattr(rv, "_journal", _journal_falso({("-k", "cat"): (0, "\n".join(pobre))}))  # sin 'Total records found'
    r = rv.bert_registro(0)
    assert (r["severidad"], r["section_guid"], r["section_length"]) == ("NOT_COLLECTED",) * 3
    assert r["creador_tabla_acpi"] == "NOT_COLLECTED" and r["palabra_en_0x14"] == "NOT_COLLECTED"
    assert r["volcado_hex"] == {} and r["misma_clase_que_cita_el_personal_de_nvidia"] is False
    # otra clase de registro: el guid se informa tal cual y no se confunde con la que cita el personal de NVIDIA
    otra = [x.replace(rv.GUID_MTKID, "00000000-0000-0000-0000-000000000000") for x in BERT_BLOQUE]
    monkeypatch.setattr(rv, "_journal", _journal_falso({("-k", "cat"): (0, "\n".join(otra))}))
    assert rv.bert_registro(0)["misma_clase_que_cita_el_personal_de_nvidia"] is False


def test_bert_registro_con_journal_que_falla_es_collection_failed(monkeypatch):
    monkeypatch.setattr(rv, "_journal", _journal_falso({("-k", "cat"): (1, "")}))
    assert rv.bert_registro(0) == {"estado": "COLLECTION_FAILED"}
    monkeypatch.setattr(rv, "_journal", _journal_falso({("-k", "cat"): (0, "kernel: sin BERT")}))
    assert "0 registros BERT" in rv.bert_registro(0)["estado"]  # control: rc 0 sin bloque es otra cosa


def test_recoge_journales_ilegibles_del_caido_van_a_could_not_run(monkeypatch, tmp_path):
    ev = _recoge(monkeypatch, tmp_path, {("500",): (1, ""), ("-k", "-1"): (1, "")})
    assert "journal_boot_-1" in ev["no_se_pudo_leer"] and "journal_kernel_boot_-1" in ev["no_se_pudo_leer"]
    ok = _recoge(monkeypatch, tmp_path, {})
    assert "journal_boot_-1" not in ok["no_se_pudo_leer"] and "journal_kernel_boot_-1" not in ok["no_se_pudo_leer"]


def test_recoge_detecta_el_cierre_el_disparador_y_el_colapso_dentro_de_la_ventana_final(monkeypatch, tmp_path):
    fin = datetime.fromisoformat("2026-10-11T13:00:00-06:00").timestamp()
    boots = [dict(BOOTS[0], last_entry=int(fin * 1e6)), dict(BOOTS[1], first_entry=int((fin + 100) * 1e6))]
    monkeypatch.setattr(rv, "TELEMETRIA", tmp_path / "no_hay.jsonl")
    monkeypatch.setattr(rv, "CRASH_DIR", tmp_path / "sin_crash")
    monkeypatch.setattr(rv, "WATCHDOG_BOOTSTATUS", tmp_path / "bootstatus")
    reciente = "2026-10-11T12:50:00-06:00 h bb-usable[1]: [bb-usable] COLAPSO psi"
    viejo = "2026-10-11T11:00:00-06:00 h bb-usable[1]: [bb-usable] COLAPSO psi"
    cierre = "2026-10-11T12:59:59-06:00 h systemd[1]: Reached target reboot.target - System Reboot."
    orden = "h sudo[1]: u : COMMAND=/usr/sbin/reboot"
    monkeypatch.setattr(rv, "_journal", _journal_falso({("-t", "sudo"): (0, orden), ("500",): (0, f"{reciente}\n{cierre}\n")}))
    ev = rv.recoge(boots, 0)
    assert ev["cierre"] == "reboot" and ev["colapso_en_ventana"] is True and ev["disparador"] == orden
    # control negativo: un COLAPSO de hace 2 h no cuenta, y sin target de cierre no se consulta el disparador
    monkeypatch.setattr(rv, "_journal", _journal_falso({("500",): (0, f"{viejo}\n")}))
    ev = rv.recoge(boots, 0)
    assert ev["cierre"] is None and ev["colapso_en_ventana"] is False and ev["disparador"] is None
    # una linea con COLAPSO sin fecha legible no se toma por colapso reciente
    monkeypatch.setattr(rv, "_journal", _journal_falso({("500",): (0, "sin fecha [bb-usable] COLAPSO\n")}))
    assert rv.recoge(boots, 0)["colapso_en_ventana"] is False


def test_ya_escritos_lee_los_boot_id_del_archivo_y_ignora_lineas_en_blanco(tmp_path, monkeypatch):
    salida = tmp_path / "reboots.jsonl"
    monkeypatch.setattr(rv, "SALIDA", salida)
    assert rv._ya_escritos() == set()
    salida.write_text(json.dumps({"boot_id": "x1"}) + "\n\n" + json.dumps({"boot_id": "x2"}) + "\n", encoding="utf-8")
    assert rv._ya_escritos() == {"x1", "x2"}


def _main_aislado(monkeypatch, tmp_path, boots=BOOTS):
    monkeypatch.setattr(rv, "SALIDA", tmp_path / "reboots.jsonl")
    monkeypatch.setattr(rv, "TELEMETRIA", tmp_path / "no_hay.jsonl")
    monkeypatch.setattr(rv, "CRASH_DIR", tmp_path / "sin_crash")
    monkeypatch.setattr(rv, "WATCHDOG_BOOTSTATUS", tmp_path / "bootstatus")
    monkeypatch.setattr(rv, "_correr_con_codigo", lambda *a: (2, SMART_SIN_PERMISO))
    monkeypatch.setattr(rv, "_journal", _journal_falso({("--list-boots",): (0, json.dumps(boots))}))


def test_main_no_repite_un_boot_ya_escrito_y_sin_escribe_no_toca_el_archivo(monkeypatch, tmp_path, capsys):
    _main_aislado(monkeypatch, tmp_path)
    monkeypatch.setattr(rv, "_publica_hallazgos", lambda filas: None)
    assert rv.main(["--ultimos", "1", "--escribe"]) == 0
    assert rv.main(["--ultimos", "1", "--escribe"]) == 0  # el boot a*32 ya esta escrito
    assert len((tmp_path / "reboots.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    assert "# 0 boots" in capsys.readouterr().err
    (tmp_path / "reboots.jsonl").unlink()
    assert rv.main(["--ultimos", "1"]) == 0  # control negativo: sin --escribe no escribe pero si imprime la fila
    assert not (tmp_path / "reboots.jsonl").exists()


def test_main_con_journalctl_que_falla_sale_con_2_y_lo_dice(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(rv, "_journal", lambda *a: SimpleNamespace(returncode=1, stdout="", stderr="no hay journal\n"))
    assert rv.main(["--ultimos", "1"]) == 2
    assert "COULD_NOT_RUN: journalctl --list-boots fallo: no hay journal" in capsys.readouterr().err


def test_publica_hallazgos_publica_es_idempotente_y_declara_lo_que_no_pudo(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    ev = {"boot_id": "c" * 32, "fin_epoch": 4600.0, "hueco_s": 100, "inicio_epoch": 1000.0}
    fila = {"boot_idx": -1, "boot_id": "c" * 32, **veredicto({**BASE, **ev}), **rv.forense({**BASE, **ev}),
            "_generado": "2026-10-11T13:00:00-06:00"}
    rv._publica_hallazgos([fila])
    assert "# hallazgo publicado:" in capsys.readouterr().err
    publicados = list((tmp_path / "hallazgos").glob("*.md"))
    assert len(publicados) == 1 and "CORTE_ABRUPTO" in publicados[0].read_text(encoding="utf-8")
    rv._publica_hallazgos([fila])
    assert "# hallazgo ya_publicado:" in capsys.readouterr().err  # mismo texto: no duplica
    publicados[0].write_text(publicados[0].read_text(encoding="utf-8") + "\nedicion ajena\n", encoding="utf-8")
    rv._publica_hallazgos([fila])  # otro contenido bajo el mismo id: se rechaza y se dice, sin tumbar el registro
    assert f"COULD_NOT_PUBLISH {'c' * 8}" in capsys.readouterr().err
    assert len(list((tmp_path / "hallazgos").glob("*.md"))) == 1


def test_script_entrypoint_sale_con_el_codigo_de_main(monkeypatch, tmp_path):
    import runpy

    _ejecutable(tmp_path, "journalctl", "echo sin-journal >&2; exit 1")
    _solo_path(monkeypatch, tmp_path)
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["reboot_verdict.py", "--ultimos", "1"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(rv.__file__, run_name="__main__")
    assert exc.value.code == 2
