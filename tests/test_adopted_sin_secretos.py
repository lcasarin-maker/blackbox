"""Nada de lo adoptado lleva un secreto ni una IP de LAN sin redactar.

Adoptar es copiar de la maquina a un repo PUBLICO (FEATURE-OWNEAR-EN-BB-LO-QUE-
ACTUA-SOBRE-LA-MAQUINA-01). Un `.env`, un token o una `DATABASE_URL` copiados
por arrastre quedarian publicados; esta guarda recorre `adopted/` entero y
falla si aparece uno. Los dos ultimos tests son su control negativo: siembran
cada forma de secreto y exigen que la guarda la cace.
"""

from __future__ import annotations

import re
from pathlib import Path

ADOPTED = Path(__file__).resolve().parent.parent / "adopted"

# Un valor de verdad: al menos 4 caracteres que no sean comilla, espacio ni `<`
# (las plantillas del fabricante traen `#FTP_PASSWORD=""` y `SSH_KEY="<path>"`).
_VALOR = r"""\s*[=:]\s*["']?[^"'\s<]{4,}"""
SECRETO = re.compile(
    r"(?i)\b[A-Z0-9_]*(?:API_?KEY|SECRET|TOKEN|PASSWORD|PASSWD)[A-Z0-9_]*" + _VALOR
    + r"|DATABASE_URL"
    + r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    + r"|\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@"
    + r"|\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,})"
)
IP_LAN = re.compile(
    r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
)


def hallazgos(nombre: str, texto: str) -> list[str]:
    fuera = [f"{nombre}: un .env no se adopta"] if re.search(r"(^|[._/])env$|^\.env", nombre) else []
    fuera += [f"{nombre}: secreto {m.group(0)[:12]!r}..." for m in SECRETO.finditer(texto)]
    fuera += [f"{nombre}: IP de LAN sin redactar" for _ in IP_LAN.finditer(texto)]
    return fuera


def test_lo_adoptado_no_lleva_secretos_ni_ip_de_lan():
    fuera: list[str] = []
    archivos = [f for f in sorted(ADOPTED.rglob("*")) if f.is_file()]
    assert archivos, "adopted/ vacio: la guarda no tendria sujeto"
    for f in archivos:
        fuera += hallazgos(f.relative_to(ADOPTED).as_posix(), f.read_text(encoding="utf-8", errors="ignore"))
    assert fuera == []


def test_control_negativo_cada_secreto_sembrado_se_caza():
    # Partidos con `+` a proposito: el detector de secretos del kit lee la
    # fuente, y un literal entero aqui seria un hallazgo suyo, no un sembrado.
    sembrados = [
        "_".join(["OPENAI", "API", "KEY"]) + "=" + "ab12" * 3,
        "_".join(["JWT", "SECRET"]) + '="' + "s3cr" * 3 + '"',
        "_".join(["MONGO", "PASSWORD"]) + ": " + "hunt" * 2,
        "DATABASE_" + "URL=postgres://h/db",
        "-----BEGIN OPENSSH " + "PRIVATE KEY-----",
        "mongodb://usuario:" + "clave@127.0.0.1/db",
        "sk-" + "a" * 24,
        "echo x > /dev/udp/192.168.7.20/6666",
    ]
    for s in sembrados:
        assert hallazgos("x.conf", s), f"la guarda dejo pasar {s!r}"
    assert hallazgos("librechat/.env", "")
    assert hallazgos("x_.env", "")


def test_control_negativo_lo_limpio_no_da_falsos_positivos():
    limpios = ['#FTP_PASSWORD=""', '#SSH_KEY="<path>"', "host 127.0.0.1",
               "echo x > /dev/udp/<REDACTADO-IP-LAN>/6666", "token de prosa sin asignacion"]
    for s in limpios:
        assert hallazgos("x.conf", s) == [], s
