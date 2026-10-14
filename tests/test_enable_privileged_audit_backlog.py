"""enable-privileged.sh fija el limite de la cola de audit en un archivo que ordena DESPUES de `audit.rules` (DEBT-AUDIT-ANILLO-DESBORDADO-SIN-LIMITE-01).

Medido el 2026-10-13: con `-b 32768` en `10-blackbox-signals.rules`, `auditctl -s` seguia en `backlog_limit 8192`, porque
`rules.d/audit.rules` (de serie, `-b 8192`) ordena despues de `10-` y lo pisa. Estatico: lee el instalador, no toca /etc/audit.
El control negativo corre el mismo chequeo sobre el texto con el `-b` en el archivo `10-` y sobre un nombre que ordena antes.
"""

from __future__ import annotations

import re
from pathlib import Path

INSTALADOR = Path(__file__).resolve().parent.parent / "enable-privileged.sh"
DE_SERIE = "audit.rules"  # rules.d/audit.rules: -b 8192, lo trae el paquete auditd


def _heredoc(texto: str, destino: str) -> str | None:
    m = re.search(r"cat >/etc/audit/rules\.d/" + re.escape(destino) + r" <<'RULES'\n(.*?)\nRULES\n", texto, re.S)
    return m.group(1) if m else None


def limite_gana(texto: str, nombre: str = "zz-blackbox-backlog.rules") -> bool:
    cuerpo = _heredoc(texto, nombre)
    pone_limite = cuerpo is not None and re.search(r"^-b 32768$", cuerpo, re.M) is not None
    ordena_despues = nombre > DE_SERIE
    solo_alli = _heredoc(texto, "10-blackbox-signals.rules") is not None and re.search(r"^-b ", _heredoc(texto, "10-blackbox-signals.rules") or "", re.M) is None
    return bool(pone_limite and ordena_despues and solo_alli)


def test_el_limite_vive_en_un_archivo_que_ordena_despues_del_de_serie() -> None:
    assert limite_gana(INSTALADOR.read_text(encoding="utf-8"))


def test_el_instalador_lo_aplica_en_caliente_y_lo_retira_en_revert() -> None:
    texto = INSTALADOR.read_text(encoding="utf-8")
    assert "auditctl -b 32768" in texto  # efecto inmediato, sin esperar a reiniciar auditd
    # el retiro tiene su PROPIO `if`: no depende de que siga existiendo el archivo 10-
    assert re.search(r"if \[ -f /etc/audit/rules\.d/zz-blackbox-backlog\.rules \]; then\n\s+run rm -f /etc/audit/rules\.d/zz-blackbox-backlog\.rules", texto)


def test_control_negativo_en_el_archivo_10_o_con_un_nombre_que_ordena_antes_falla() -> None:
    texto = INSTALADOR.read_text(encoding="utf-8")
    assert not limite_gana(texto, "10-blackbox-backlog.rules")  # no existe ese heredoc
    assert not limite_gana(texto.replace("zz-blackbox-backlog.rules", "10-blackbox-backlog.rules"), "10-blackbox-backlog.rules")  # ordena antes de audit.rules
    mal = texto.replace("-b 32768\nRULES\n    augenrules", "-b 8192\nRULES\n    augenrules", 1)
    assert not limite_gana(mal)  # con otro valor no cuenta
    con_b_en_10 = texto.replace("## (0) El limite de la cola", "-b 32768\n## (0) El limite de la cola", 1)
    assert not limite_gana(con_b_en_10)  # un -b en el archivo 10- tambien se rechaza


def test_control_negativo_un_rm_anidado_en_el_if_del_archivo_10_no_cuenta() -> None:
    texto = INSTALADOR.read_text(encoding="utf-8")
    anidado = texto.replace(
        "if [ -f /etc/audit/rules.d/zz-blackbox-backlog.rules ]; then\n    run rm -f /etc/audit/rules.d/zz-blackbox-backlog.rules",
        "if [ -f /etc/audit/rules.d/10-blackbox-signals.rules ]; then\n    run rm -f /etc/audit/rules.d/zz-blackbox-backlog.rules",
        1,
    )
    assert anidado != texto
    assert not re.search(r"if \[ -f /etc/audit/rules\.d/zz-blackbox-backlog\.rules \]; then\n\s+run rm -f /etc/audit/rules\.d/zz-blackbox-backlog\.rules", anidado)
