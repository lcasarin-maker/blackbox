"""Veredicto por reinicio: cada rama con el caso que la activa y el que NO."""

import pytest

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
