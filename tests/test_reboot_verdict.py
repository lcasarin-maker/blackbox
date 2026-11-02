"""Veredicto por reinicio: cada rama con el caso que la activa y el que NO."""

import json
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import reboot_verdict as rv
from tools import ultimo_aliento
from tools.reboot_verdict import disparador, veredicto

pytestmark = pytest.mark.unit

BASE = {"telemetria": {"psi_mem_full_avg10": 0.0}}


@pytest.fixture(autouse=True)
def _sin_fuentes_de_la_maquina(tmp_path, monkeypatch):
    """Ningun test lee /var/lib/blackbox ni el $BLACKBOX_DATA real: cada fuente apunta a un tmp vacio."""
    monkeypatch.setattr(rv, "PSTORE_DIR", tmp_path / "sin_pstore")
    monkeypatch.setattr(rv, "ETAPAS", tmp_path / "sin_etapas.jsonl")
    monkeypatch.setattr(rv, "ANILLO", tmp_path / "sin_anillo.bin")
    monkeypatch.setattr(rv, "EXTERNO", tmp_path / "sin_externo")


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
        disparador(["h systemd-logind[2452]: New session 3 of user u."]) is None
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


# ------------------------------------------------- forense movido desde el detector de un consumidor externo
# Una ficha reubicada al consumidor de conocimiento: la medicion vive en bb; el consumidor externo solo lee la fila.
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
    # control negativo: el volcado viejo NO se atribuye a un corte posterior (el consumidor externo si lo hacia)
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


def test_main_con_list_boots_vacio_sale_con_2_y_lo_dice_en_vez_de_un_traceback(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(rv, "_journal", lambda *a: SimpleNamespace(returncode=0, stdout="", stderr=""))
    assert rv.main(["--ultimos", "1"]) == 2
    assert "COULD_NOT_RUN: journalctl --list-boots no devolvio JSON" in capsys.readouterr().err


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


# ------------------------------------------------- fuentes fuera del journal (2026-11-01): fixtures en tests/fixtures/reboot_verdict
FX = Path(__file__).parent / "fixtures" / "reboot_verdict"
T0, FIN = 1791900000.0, 1791903600.0  # inicio y ultima entrada del boot que muere (los de las fixtures)
SIG = FIN + 120  # primera entrada del boot siguiente
A_ID, G_ID, B_ID = "a" * 32, "9" * 32, "b" * 32
BOOTS_FX = [
    {"index": -1, "boot_id": A_ID, "first_entry": int(T0 * 1e6), "last_entry": int(FIN * 1e6)},
    {"index": 0, "boot_id": B_ID, "first_entry": int(SIG * 1e6), "last_entry": int((SIG + 100) * 1e6)},
]
COLA_MUDA = {("500",): (0, "2026-10-13T08:59:59-06:00 h kernel: linea normal\n")}  # journal con lineas y sin cierre


def _dashed(bid):
    return f"{bid[:8]}-{bid[8:12]}-{bid[12:16]}-{bid[16:20]}-{bid[20:]}"


def _crash(tmp_path, nombre, mtime, archivos):
    d = tmp_path / "crash" / nombre
    d.mkdir(parents=True)
    for a, contenido in archivos.items():
        (d / a).write_text(contenido, encoding="utf-8")
    os.utime(d, (mtime, mtime))
    return d


def _fx(monkeypatch, tmp_path, externo=None, etapas=True, anillo=False, journal=COLA_MUDA):
    monkeypatch.setattr(rv, "TELEMETRIA", tmp_path / "no_hay.jsonl")
    monkeypatch.setattr(rv, "CRASH_DIR", tmp_path / "crash")
    monkeypatch.setattr(rv, "WATCHDOG_BOOTSTATUS", tmp_path / "bootstatus")
    monkeypatch.setattr(rv, "_journal", _journal_falso(journal))
    if externo:
        monkeypatch.setattr(rv, "EXTERNO", FX / externo)
    if etapas:
        monkeypatch.setattr(rv, "ETAPAS", FX / "etapas.jsonl")
    if anillo:
        monkeypatch.setattr(rv, "ANILLO", _anillo_real(tmp_path))


def _anillo_real(tmp_path):
    """Un anillo de verdad, escrito con `ultimo_aliento.Anillo`: 65 s del boot A subiendo hasta 95 C, cada
    250 ms, hasta FIN + 2.25; el arranque B a 40 C, con UNA muestra de B fechada dentro de la ventana de A
    (reloj sin NTP) que el filtro por `boot` no debe atribuirle."""
    ruta = tmp_path / "anillo.bin"
    a = ultimo_aliento.Anillo(str(ruta), tamano=4096 + 1024 * 400)
    a.abrir()
    pasos = 261  # FIN + 2.25 - 65 ... FIN + 2.25
    for k in range(pasos):
        t = FIN + 2.25 - 0.25 * (pasos - 1 - k)
        a.escribir({"ts": t, "boot": A_ID, "tipo": "muestra", "temp_c": {"0": round(70.0 + 25.0 * k / (pasos - 1), 2)}})
    a.escribir({"ts": FIN - 10, "boot": B_ID, "tipo": "muestra", "temp_c": {"0": 40.0}})
    for k in range(8):
        a.escribir({"ts": SIG + 30 + 0.25 * k, "boot": B_ID, "tipo": "muestra", "temp_c": {"0": 40.0}})
    a.cerrar()
    return ruta


def _fila(ev):
    return {**veredicto(ev), **rv.forense(ev)}


def test_kdump_se_detecta_con_solo_dmesg_y_trae_su_linea_de_panico(tmp_path, monkeypatch):
    monkeypatch.setattr(rv, "CRASH_DIR", tmp_path / "crash")
    d = _crash(tmp_path, "202610131500", FIN + 20, {"dmesg.202610131500": (FX / "kdump_dmesg.txt").read_text(encoding="utf-8")})
    k = rv.kdump_en(FIN, SIG)
    assert k is not None and k["directorio"] == str(d) and k["vmcore"] is False
    assert k["linea_panico"] == "[ 3601.130000] Kernel panic - not syncing: Oops: Fatal exception"
    assert k["fuente_panico"] == f"{d / 'dmesg.202610131500'}:6"
    # el punto ciego: con KDUMP_SKIP_VMCORE=1 no hay dump.*, y el lector viejo decia "ninguno"
    assert rv.vmcore_en(FIN, SIG) is None


def test_kdump_ilegible_se_declara_y_no_se_lee_como_sin_panic(tmp_path, monkeypatch):
    monkeypatch.setattr(rv, "CRASH_DIR", tmp_path / "crash")
    d = _crash(tmp_path, "202610131500", FIN + 20, {"dmesg.202610131500": "x"})
    real_open = Path.open

    def sin_permiso(self, *a, **k):
        if self.name.startswith("dmesg."):
            raise PermissionError(13, "Permission denied")
        return real_open(self, *a, **k)

    monkeypatch.setattr(Path, "open", sin_permiso)  # los tests corren como root: el permiso se simula
    k = rv.kdump_en(FIN, SIG)
    assert k is not None
    assert k["linea_panico"] is None and "Permission denied" in k["ilegibles"][0]
    v = veredicto({**BASE, "kdump": k})
    assert v["causa"] == "PANICO_KDUMP" and any("no se pudo leer" in r for r in v["razones"])
    assert not any("no trae" in r for r in v["razones"])  # control: ilegible no es "sin linea de panic"
    monkeypatch.setattr(rv.os, "access", lambda *a: False)  # directorio que ni se puede listar
    k = rv.kdump_en(FIN, SIG)
    assert k is not None
    assert k["directorio"] == str(d) and k["archivos"] == [] and "sin permiso" in k["ilegibles"][0]


def test_kdump_fuera_de_la_ventana_no_se_atribuye(tmp_path, monkeypatch):
    monkeypatch.setattr(rv, "CRASH_DIR", tmp_path / "crash")
    texto = (FX / "kdump_dmesg.txt").read_text(encoding="utf-8")
    _crash(tmp_path, "202610130500", T0 - 500, {"dmesg.202610130500": texto})  # de un corte anterior
    _crash(tmp_path, "202610131600", SIG + 60, {"dmesg.202610131600": texto})  # escrito ya en el boot siguiente
    _crash(tmp_path, "202610131510", FIN + 30, {"kexec_cmd": "no es volcado"})  # en la ventana, sin dmesg ni dump
    assert rv.kdump_en(FIN, SIG) is None


def test_recoge_con_kdump_de_solo_dmesg_da_PANICO_KDUMP_con_la_fuente_citada(tmp_path, monkeypatch):
    _fx(monkeypatch, tmp_path)
    d = _crash(tmp_path, "202610131500", FIN + 20, {"dmesg.202610131500": (FX / "kdump_dmesg.txt").read_text(encoding="utf-8")})
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["etiqueta"] == "CORTE_ABRUPTO"  # la etiqueta sigue diciendo lo que dice el journal
    assert f["causa"] == "PANICO_KDUMP" and f["causa_fuente"] == f"{d / 'dmesg.202610131500'}:6"
    assert f["kdump"]["vmcore"] is False and f["vmcore"] is None
    assert any("kdump guardo el dmesg del panic" in r for r in f["razones"])
    assert not any(r.startswith("causa INDETERMINADA") for r in f["razones"])


def test_con_todas_las_fuentes_vacias_sale_INDETERMINADO(tmp_path, monkeypatch):
    _fx(monkeypatch, tmp_path, etapas=False, journal={})
    ev = rv.recoge(BOOTS_FX, 0)
    f = _fila(ev)
    assert (f["etiqueta"], f["causa"], f["causa_fuente"]) == ("INDETERMINADO", "INDETERMINADO", None)
    assert "observador_externo" in f["could_not_run"]
    assert any("etapas_arranque" in x for x in f["could_not_run"]) and any("pstore_arranque" in x for x in f["could_not_run"])
    assert f["kdump"] is None and f["pstore"] is None and f["etapas"] is None and f["netconsole"] is None
    # control: el mismo boot con lineas en el journal y sin cierre si es CORTE_ABRUPTO (el silencio se leyo)
    _fx(monkeypatch, tmp_path, etapas=False)
    assert _fila(rv.recoge(BOOTS_FX, 0))["etiqueta"] == "CORTE_ABRUPTO"


def test_sin_datos_de_ping_ni_de_enchufe_no_se_concluye_corte_de_energia(tmp_path, monkeypatch):
    _fx(monkeypatch, tmp_path)  # EXTERNO apunta a un directorio vacio
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["causa"] == "INDETERMINADO" and "observador_externo" in f["could_not_run"]
    # solo el enchufe, sin ping: que el enchufe enmudezca puede ser su Wi-Fi, no la pared
    ext = tmp_path / "solo_enchufe"
    ext.mkdir()
    (ext / "energia.jsonl").write_text((FX / "externo_corte" / "energia.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(rv, "EXTERNO", ext)
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["causa"] != "CORTE_DE_ENERGIA" and f["causa"] == "INDETERMINADO"
    assert f["tiempos_externos"]["ping"]["ultima_respuesta"] is None
    # la regla pura tampoco concluye con el enchufe solo, aunque el recolector le pasara su caida
    solo = {"ping": {"ultima_respuesta": None, "primera_falla": None}, "enchufe": {"ultima_ok": FIN, "primera_falla": FIN + 1}}
    assert rv._causa_por_tiempos(solo) is None
    # un ping que respondio por ultima vez en el boot ANTERIOR no da cobertura a este
    (ext / "ping.jsonl").write_text(
        "\n".join(json.dumps({"epoch": T0 - 100 + k, "ok": k == 0}) for k in range(5)) + "\n", encoding="utf-8"
    )
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["tiempos_externos"]["ping"]["ultima_respuesta"] is None and f["hora_muerte"]["fuente"] == "journal"


def test_corte_de_energia_si_el_enchufe_cae_antes_que_el_tcp(tmp_path, monkeypatch):
    _fx(monkeypatch, tmp_path, externo="externo_corte")
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["causa"] == "CORTE_DE_ENERGIA"
    assert f"{FX / 'externo_corte' / 'energia.jsonl'}:9" in f["causa_fuente"] and "ping.jsonl" in f["causa_fuente"]
    t = f["tiempos_externos"]
    assert t["ping"]["ultima_respuesta"] == FIN + 2 and t["ping"]["primera_falla"] == FIN + 3
    assert t["enchufe"]["primera_falla"] == pytest.approx(FIN + 2.6) and t["latido"]["en_el_hueco"] > 0
    assert "observador_externo" not in f["could_not_run"]


def test_enchufe_mudo_desde_mucho_antes_no_prueba_un_corte_de_energia(tmp_path, monkeypatch):
    ext = tmp_path / "ext"
    ext.mkdir()
    (ext / "ping.jsonl").write_text((FX / "externo_corte" / "ping.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    filas = [{"epoch": FIN - 600 + k, "ok": True, "voltaje_v": 121.0, "potencia_w": 148.0} for k in range(5)]
    filas += [{"epoch": FIN - 590 + k, "ok": False} for k in range(620)]  # el Wi-Fi del enchufe cayo 10 min antes
    (ext / "energia.jsonl").write_text("\n".join(json.dumps(x) for x in filas) + "\n", encoding="utf-8")
    _fx(monkeypatch, tmp_path)
    monkeypatch.setattr(rv, "EXTERNO", ext)
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["tiempos_externos"]["enchufe"]["primera_falla"] <= FIN + 3  # cae "a tiempo" de la falla del TCP...
    assert f["causa"] != "CORTE_DE_ENERGIA"  # ...pero ya estaba mudo: su ultima lectura buena es de 10 min antes


def test_cuelgue_si_el_tcp_cae_y_el_enchufe_sigue_con_consumo(tmp_path, monkeypatch):
    _fx(monkeypatch, tmp_path, externo="externo_cuelgue")
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["causa"] == "CUELGUE" and "ping.jsonl" in f["causa_fuente"] and "energia.jsonl" in f["causa_fuente"]
    assert all(r["potencia_w"] >= 20 for r in f["tiempos_externos"]["enchufe"]["tras_caida_tcp"])
    # control: si despues de caer el TCP el enchufe mide 10 W (ni encendida ni apagada) no hay cuelgue que afirmar
    ext = tmp_path / "ext"
    ext.mkdir()
    (ext / "ping.jsonl").write_text((FX / "externo_cuelgue" / "ping.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    bajo = (FX / "externo_cuelgue" / "energia.jsonl").read_text(encoding="utf-8").replace('"potencia_w": 95.0', '"potencia_w": 10.0')
    (ext / "energia.jsonl").write_text(bajo, encoding="utf-8")
    monkeypatch.setattr(rv, "EXTERNO", ext)
    assert _fila(rv.recoge(BOOTS_FX, 0))["causa"] == "INDETERMINADO"


def test_pstore_del_arranque_siguiente_da_PANICO_PSTORE_y_un_registro_repetido_no(tmp_path, monkeypatch):
    _fx(monkeypatch, tmp_path)
    ps = tmp_path / "pstore"
    ps.mkdir()
    (ps / "arranque.jsonl").write_text((FX / "arranque.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    nuevo = ps / f"{_dashed(B_ID)}-dmesg-ramoops-0"
    nuevo.write_text((FX / "pstore_dmesg.txt").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(rv, "PSTORE_DIR", ps)
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["causa"] == "PANICO_PSTORE" and f["causa_fuente"] == f"{nuevo}:3"
    assert f["pstore"]["fila_arranque_siguiente"]["pstore_archivos"] == 1
    assert f["pstore"]["fila_arranque_propia"]["linea_jsonl"] == 1
    # control: la misma copia ya existia, mas vieja, en el arranque anterior: es un registro que nadie borro
    viejo = ps / f"{_dashed(A_ID)}-dmesg-ramoops-0"
    viejo.write_bytes(nuevo.read_bytes())
    os.utime(viejo, (T0 + 20, T0 + 20))
    os.utime(nuevo, (SIG + 20, SIG + 20))
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["causa"] != "PANICO_PSTORE" and f["pstore"]["repetidos"] == [nuevo.name]
    # control: un registro de pstore sin linea de panic no inventa un panic
    nuevo.write_text((FX / "pstore_dmesg_sin_panic.txt").read_text(encoding="utf-8"), encoding="utf-8")
    assert _fila(rv.recoge(BOOTS_FX, 0))["pstore"]["linea_panico"] is None


def test_netconsole_atribuye_el_panic_de_la_ventana_y_no_el_del_boot_anterior(tmp_path, monkeypatch):
    _fx(monkeypatch, tmp_path, externo="externo_netconsole")
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["causa"] == "PANICO_NETCONSOLE"
    assert f["causa_fuente"] == f"{FX / 'externo_netconsole' / 'testigo' / 'netconsole.jsonl'}:4"  # no la linea 1 (otro boot)
    assert f["netconsole"]["lineas_en_ventana"] == 3


def test_etapas_dicen_hasta_donde_llego_y_solo_un_arranque_trunco_es_fallo():
    # las ramas (gpu-lista corre junto a basic) no cuentan para la etapa maxima: el arranque se quedo en basic
    vistas = {"local-fs": (100.0, 4, "e:1"), "basic": (102.0, 6, "e:2"), "gpu-lista": (101.0, 5, "e:3")}
    r = rv.resumen_etapas(vistas)
    assert (r["maxima"], r["faltante"], r["ultima_epoch"]) == ("basic", "multi-user", 102.0)
    assert r["ramas"] == {"network-online": None, "gpu-lista": 5} and r["fuente"] == "e:2"
    ev = {**BASE, "etapas": r, "fin_epoch": 160.0}
    v = veredicto(ev)
    assert v["causa"] == "FALLO_DE_ARRANQUE_EN_BASIC" and v["etiqueta"] == "CORTE_ABRUPTO"
    assert v["causa_fuente"].startswith("e:2") and any("nunca a 'multi-user'" in x for x in v["razones"])
    # control: vivio una hora despues de su ultima etapa: el que fallo fue el escritor, no el arranque
    assert veredicto({**ev, "fin_epoch": 102.0 + 3600})["causa"] == "INDETERMINADO"
    # control: sin gdm (arranque sin pantalla) y sin red, pero llego a graphical: completo
    completo = {e: (100.0 + n, n, f"e:{n}") for n, e in enumerate(rv.ETAPAS_ORDEN) if e not in ("gdm", "sesion-usuario")}
    rc = rv.resumen_etapas(completo)
    assert rc["faltante"] is None and rc["saltadas"] == ["gdm"] and rc["ramas"]["network-online"] is None
    assert veredicto({**BASE, "etapas": rc, "fin_epoch": 110.0})["causa"] == "INDETERMINADO"
    # sesion-<uid> entra a la cadena por etapas_arranque.canonica; la de GDM (uid < 1000) no es de una persona
    assert rv.resumen_etapas({"sesion-1000": (1.0, 1, "e:1")})["alcanzadas"] == ["sesion-usuario"]
    assert rv.resumen_etapas({"sesion-120": (1.0, 1, "e:1")})["alcanzadas"] == []
    # control: solo etapas que no conoce no son un fallo en local-fs
    assert veredicto({**BASE, "etapas": rv.resumen_etapas({"tpm": (1.0, 1, "e:1")}), "fin_epoch": 2.0})["causa"] == "INDETERMINADO"


def test_etapas_leen_la_rotacion_y_toleran_realtime_null(tmp_path, monkeypatch):
    """El esquema real de etapa-marca.sh: `.1` es la generacion vieja, y `realtime: null` es una etapa sin hora."""
    e = tmp_path / "etapas.jsonl"
    (tmp_path / "etapas.jsonl.1").write_text(
        json.dumps({"boot_id": _dashed(A_ID), "etapa": "local-fs", "monotonic": 3.91, "realtime": T0 + 4.1}) + "\n", encoding="utf-8"
    )
    e.write_text(
        json.dumps({"boot_id": _dashed(A_ID), "etapa": "basic", "monotonic": None, "realtime": None}) + "\n"
        + json.dumps({"boot_id": _dashed(A_ID), "etapa": "multi-user", "monotonic": "9", "realtime": T0 + 9}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(rv, "ETAPAS", e)
    todas = rv.etapas_de()
    assert todas is not None
    vistas = todas[A_ID]
    assert set(vistas) == {"local-fs", "basic"}  # multi-user trae monotonic de texto: se descarta como en etapas_arranque
    assert vistas["local-fs"] == (T0 + 4.1, 3.91, f"{e}.1:1") and vistas["basic"] == (None, None, f"{e}:1")
    r = rv.resumen_etapas(vistas)
    assert r["maxima"] == "basic" and r["ultima_epoch"] == T0 + 4.1 and r["fuente"] == f"{e}:1"


def test_arranque_fantasma_con_etapas_y_sin_journal_aparece_como_fila(monkeypatch, tmp_path, capsys):
    _main_aislado(monkeypatch, tmp_path, boots=BOOTS_FX)
    monkeypatch.setattr(rv, "_publica_hallazgos", lambda filas: None)
    monkeypatch.setattr(rv, "ETAPAS", FX / "etapas.jsonl")
    assert rv.main(["--ultimos", "1", "--escribe"]) == 0
    filas = [json.loads(x) for x in (tmp_path / "reboots.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [f["boot_id"] for f in filas] == [A_ID, G_ID]
    a, g = filas
    assert a["boot_id_siguiente"] == G_ID and g["boot_id_siguiente"] == B_ID
    assert a["arranque_fantasma"] is False and a["etapas"]["maxima"] == "sesion-usuario"
    assert g["arranque_fantasma"] is True and g["boot_idx"] is None and g["esquema"] == "bb-reboot/1"
    assert g["etapas"]["maxima"] == "basic" and g["causa"] == "FALLO_DE_ARRANQUE_EN_BASIC"
    assert g["etiqueta"] == "INDETERMINADO" and "etapas.jsonl" in g["causa_fuente"]
    assert a["hueco_s"] == 60  # la ventana de A acaba donde empieza G, no en B
    assert any("arranque fantasma 99999999 se interpone" in r for r in a["razones"])  # su BERT es de G
    # control negativo: sin etapas no hay fantasma que inventar
    (tmp_path / "reboots.jsonl").unlink()
    monkeypatch.setattr(rv, "ETAPAS", tmp_path / "sin_etapas.jsonl")
    assert rv.main(["--ultimos", "1", "--escribe"]) == 0
    assert [json.loads(x)["boot_id"] for x in (tmp_path / "reboots.jsonl").read_text(encoding="utf-8").splitlines()] == [A_ID]


def test_arranque_fantasma_solo_dentro_del_tramo_del_journal():
    etapas = {"1" * 32: {"local-fs": (T0 - 9000, 4, "e:1")}, G_ID: {"local-fs": (FIN + 60, 4, "e:2")}, A_ID: {"basic": (T0 + 6, 6, "e:3")}}
    assert [g["boot_id"] for g in rv.arranques_fantasma(BOOTS_FX, etapas)] == [G_ID]  # el viejo es journal rotado


def test_anillo_da_la_hora_de_muerte_al_segundo_y_la_curva_termica_previa(tmp_path, monkeypatch):
    _fx(monkeypatch, tmp_path, externo="externo_corte", anillo=True)
    f = _fila(rv.recoge(BOOTS_FX, 0))
    h = f["hora_muerte"]
    assert h["fuente"] == "anillo" and h["ultima_senal_epoch"] == FIN + 2.25
    assert h["cota_superior_fuente"] == "ping" and h["cota_superior_epoch"] == FIN + 3
    assert h["incertidumbre_s"] <= 1.0 and h["periodo_anillo_s"] == 0.25
    curva = f["curva_termica_previa"]
    assert 55 <= len(curva) <= 61 and curva[-1]["termica"] == {"0": 95.0}
    assert curva[0]["termica"]["0"] < curva[-1]["termica"]["0"]  # la curva sube
    assert all(FIN + 2.25 - 60 - 1 <= p["epoch"] <= FIN + 2.25 for p in curva)
    # las muestras del arranque siguiente (40 C), incluida la fechada dentro de la ventana, no son del muerto
    assert f["ultimo_aliento"]["temp_c"] == {"0": 95.0} and f["ultimo_aliento"]["boot"] == A_ID
    assert all(p["termica"]["0"] > 40.0 for p in curva)
    # control: sin anillo, la hora la da el ping y se declara la fuente que falto
    _fx(monkeypatch, tmp_path, externo="externo_corte")
    monkeypatch.setattr(rv, "ANILLO", tmp_path / "sin_anillo.bin")
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["hora_muerte"]["fuente"] == "ping" and f["curva_termica_previa"] is None
    assert any("anillo_ultimo_aliento" in x for x in f["could_not_run"])


def test_testigo_que_calla_con_la_atom_se_dice_y_no_concluye(tmp_path, monkeypatch):
    ext = tmp_path / "ext"
    ext.mkdir()
    (ext / "testigo").mkdir()
    (ext / "testigo" / "latido.jsonl").write_text(
        "\n".join(json.dumps({"epoch": FIN - 30 + 5 * k, "evento": "latido"}) for k in range(7)) + "\n", encoding="utf-8"
    )
    _fx(monkeypatch, tmp_path)
    monkeypatch.setattr(rv, "EXTERNO", ext)
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["causa"] == "INDETERMINADO" and f["tiempos_externos"]["latido"]["en_el_hueco"] == 0
    assert any("el testigo externo callo junto con la ATOM" in r for r in f["razones"])


def test_bootstatus_de_un_arranque_que_no_es_el_vivo_sale_de_su_journal(tmp_path, monkeypatch):
    tres = [BOOTS_FX[0], dict(BOOTS_FX[1], index=-1, boot_id="c" * 32), dict(BOOTS_FX[1], index=0, first_entry=int((SIG + 500) * 1e6))]
    tres[0] = dict(tres[0], index=-2)
    wdt = "sbsa-gwdt sbsa-gwdt.0: System reset by WDT."
    _fx(monkeypatch, tmp_path, journal={**COLA_MUDA, ("-k", "cat"): (0, f"k: algo\n{wdt}\n")})
    f = _fila(rv.recoge(tres, 0))
    assert f["watchdog_bootstatus_siguiente"] == 32 and wdt in f["watchdog_bootstatus_fuente"]
    assert any("bootstatus=32" in r for r in f["razones"])
    probe = "sbsa-gwdt sbsa-gwdt.0: Initialized with 10s timeout @ 1000000000 Hz, action=0."
    _fx(monkeypatch, tmp_path, journal={**COLA_MUDA, ("-k", "cat"): (0, probe + "\n")})
    f = _fila(rv.recoge(tres, 0))
    assert f["watchdog_bootstatus_siguiente"] == 0 and "watchdog_bootstatus" not in f["could_not_run"]
    # control: sin linea del driver no se supone 0
    _fx(monkeypatch, tmp_path)
    f = _fila(rv.recoge(tres, 0))
    assert f["watchdog_bootstatus_siguiente"] is None and "watchdog_bootstatus" in f["could_not_run"]


CAMPOS_BB_REBOOT_1 = {
    "boot_idx", "boot_id", "boot_id_siguiente", "etiqueta", "razones", "bert_siguiente", "bert_palabra_0x14",
    "bert_guid", "hueco_s", "could_not_run", "esquema", "hora_inicio", "hora_fin_registrada", "duracion_s",
    "journal_danado", "panic_linea", "cierre_pid1", "crash_confirmado", "lineas_diagnostico", "xids", "vmcore",
    "almacenamiento",
}
CAMPOS_NUEVOS = {
    "causa", "causa_fuente", "watchdog_bootstatus_siguiente", "watchdog_bootstatus_fuente", "arranque_fantasma",
    "kdump", "pstore", "etapas", "netconsole", "tiempos_externos", "ultimo_aliento", "curva_termica_previa", "hora_muerte",
}


def test_la_fila_conserva_cada_campo_de_bb_reboot_1_y_solo_anade(monkeypatch, tmp_path):
    _main_aislado(monkeypatch, tmp_path)
    monkeypatch.setattr(rv, "_publica_hallazgos", lambda filas: None)
    assert rv.main(["--ultimos", "1", "--escribe"]) == 0
    fila = json.loads((tmp_path / "reboots.jsonl").read_text(encoding="utf-8"))
    assert set(fila) == CAMPOS_BB_REBOOT_1 | CAMPOS_NUEVOS and fila["esquema"] == "bb-reboot/1"


def test_series_del_testigo_con_rotaciones_b64_y_parada(tmp_path, monkeypatch):
    """Los nombres y campos reales de bb_testigo en `externo/testigo/`: rotaciones .N, netconsole en `b64` cuando el
    datagrama no era UTF-8, y `evento: parada` (testigo detenido) que no cuenta como latido."""
    import base64

    ext = tmp_path / "ext"
    t = ext / "testigo"
    t.mkdir(parents=True)
    panic = "Kernel panic - not syncing: Fatal exception \xff".encode("latin-1")
    (t / "netconsole.jsonl.1").write_text(json.dumps({"epoch": FIN - 5, "texto": "linea vieja"}) + "\n", encoding="utf-8")
    (t / "netconsole.jsonl").write_text(json.dumps({"epoch": FIN + 1, "b64": base64.b64encode(panic).decode()}) + "\n", encoding="utf-8")
    (t / "latido.jsonl").write_text(
        json.dumps({"epoch": FIN - 10, "evento": "latido"}) + "\n" + json.dumps({"epoch": FIN + 20, "evento": "parada"}) + "\n",
        encoding="utf-8",
    )
    _fx(monkeypatch, tmp_path)
    monkeypatch.setattr(rv, "EXTERNO", ext)
    assert [p.name for p in rv._serie("netconsole", en_la_atom=False)] == ["netconsole.jsonl.1", "netconsole.jsonl"]
    f = _fila(rv.recoge(BOOTS_FX, 0))
    assert f["causa"] == "PANICO_NETCONSOLE" and f["causa_fuente"] == f"{t / 'netconsole.jsonl'}:1"
    assert f["netconsole"]["lineas_en_ventana"] == 2
    lat = f["tiempos_externos"]["latido"]
    assert lat["en_el_hueco"] == 0 and lat["paradas_en_el_hueco"] == 1 and lat["ultimo_hasta_la_muerte"] == FIN - 10
    assert any("lo detuvieron" in r for r in f["razones"])
