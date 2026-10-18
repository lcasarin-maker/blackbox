#!/usr/bin/env python3
"""Guardia de PII mexicana y de correos en los archivos de texto versionados.

Reemplaza al escaner del kit anterior. Protege el repo publico de tres cosas: RFC/CURP, correos y telefonos de
personas. No hay exencion por palabra ("fixture", "ejemplo") ni por marcador: un valor solo se acepta si su FORMA
prueba que no es de nadie (RFC generico oficial, dominio reservado por RFC 2606, unidad de systemd, icono DEP-11,
fila de Release de apt, direccion de rol publicada por un proyecto, id interno con prefijo compuesto). Los datos
sinteticos de las pruebas se construyen en tiempo de ejecucion (concatenando) y no viven en el arbol.

Uso: `python3 -m tools.guardia_pii archivos...` o `--arbol` (recorre `git ls-files`). Sin archivos ni `--arbol` no examina nada: pre-commit lanza el hook en paralelo y algunos lotes llegan vacios. Sale 0 limpio, 1 con
hallazgos, 2 si no pudo leer el arbol (COULD_NOT_RUN). Nunca imprime el valor completo: lo enmascara.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

EXTENSIONES_TEXTO = frozenset({
    ".md", ".txt", ".py", ".sh", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".service", ".timer", ".conf",
    ".cfg", ".ini", ".rules", ".patch", ".csv", ".log", "",
})
# Cadenas EXACTAS (nunca el dominio: una persona con buzon en ese dominio sigue cazada). Las de NVIDIA son los campos Maintainer del
# repositorio APT firmado que graba `tests/fixtures/firmware-signed-repository/Packages`: buzones de rol del proyecto.
PERMITIDOS_FIJOS = frozenset({
    "XAXX010101000", "XEXX010101000", "noreply@anthropic.com", "cudatools@nvidia.com", "ftpmaster@ubuntu.com",
    "dgx-spark-pkgs@nvidia.com", "dgxdev@nvidia.com", "dgx-dev@nvidia.com", "dgx-cosmos-support@nvidia.com",
    "support@nvidia.com",
})
RFC = re.compile(r"\b[A-Z&Ñ]{3,4}-?[0-9]{6}-?[A-Z0-9]{3}\b")
CURP = re.compile(r"\b[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[A-Z0-9]{2}\b")
CORREO = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# Limite declarado: un telefono escrito solo con espacios ("55 1234 5678") no se distingue de una tabla numerica de
# telemetria (trazas USB, anchos de banda), asi que sin prefijo +52 ni parentesis solo se cazan los separados por
# guion o punto. Este repo no guarda datos de clientes; si un dia los guardara, este limite se revisa.
TELEFONO = re.compile(
    r"(?<![\w-])(?:"
    r"(?:\+?52[\s.-]?)(?:\(\d{2,3}\)\s?\d{3,4}[\s.-]?\d{4}|\d{2,3}[\s.-]\d{3,4}[\s.-]\d{4})"
    r"|\(\d{2,3}\)\s?\d{3,4}[\s.-]?\d{4}"
    r"|\d{2,3}[.-]\d{3,4}[.-]\d{4})(?![\w-])"
)
# Un id interno compuesto (`DEBT-`, `DGX-`, `CONV-DEBT-`) se escribe con un guion pegado a otra palabra en
# mayusculas; el RFC de una persona nunca. Se decide por FORMA, no por una lista de prefijos.
_PREFIJO_COMPUESTO = re.compile(r"(?<![A-Za-z0-9])[A-Z]+(?:-[A-Z]+)*-$")
_UNIDAD_SYSTEMD = re.compile(
    r"\A[A-Za-z0-9._%+-]+@[A-Za-z0-9.:-]+\.(?:service|socket|target|timer|mount|automount|slice|scope|swap|device|path)\Z"
)
_ICONOS_DEP11 = re.compile(r"\Aicons-(48|64|128)x\1@2\.tar(?:\.gz)?\Z")
# Dominios reservados por RFC 2606/6761: ningun buzon de persona puede vivir en `example.com|net|org` (ni en sus
# subdominios), ni bajo los TLD `.example`, `.test`, `.invalid`, `.localhost`. `mi-example.com` NO casa: exige frontera.
_DOMINIO_RESERVADO = re.compile(r"(?:\A|\.)(?:example(?:\.(?:com|net|org))?|test|invalid|localhost)\Z", re.I)
_FILA_RELEASE_APT = re.compile(
    r"\A\s*(?:[0-9a-f]{32}|[0-9a-f]{40}|[0-9a-f]{64}|[0-9a-f]{96}|[0-9a-f]{128})\s+(?:0|[1-9][0-9]{0,19})\s+"
    r"(?:main|restricted|universe|multiverse)/dep11/"
)


def enmascara(valor: str) -> str:
    """Muestra el tipo de dato y su longitud, nunca el valor."""
    return f"{valor[:2]}{'*' * max(0, len(valor) - 2)}"


def _exento(tipo: str, valor: str, linea: str, inicio: int) -> bool:
    if valor in PERMITIDOS_FIJOS:
        return True
    if tipo in ("rfc", "curp"):
        return bool(_PREFIJO_COMPUESTO.search(linea[:inicio]))
    if tipo == "correo":
        if _UNIDAD_SYSTEMD.match(valor) or _ICONOS_DEP11.match(valor):
            return True
        if _DOMINIO_RESERVADO.search(valor.rsplit("@", 1)[1]):
            return True
        if linea[:inicio].endswith("://"):  # `https://usuario@host`: usuario de una URL, no un buzon (lo de claves es gitleaks)
            return True
        return bool(_FILA_RELEASE_APT.match(linea))
    return False


def hallazgos_texto(texto: str) -> list[tuple[int, str, str]]:
    """(linea, tipo, valor) de cada dato que la forma no prueba que sea de nadie."""
    salida: list[tuple[int, str, str]] = []
    for n, linea in enumerate(texto.splitlines(), 1):
        for tipo, patron in (("rfc", RFC), ("curp", CURP), ("correo", CORREO), ("telefono", TELEFONO)):
            for m in patron.finditer(linea):
                if tipo == "rfc" and CURP.fullmatch(m.group(0)):
                    continue
                if not _exento(tipo, m.group(0), linea, m.start()):
                    salida.append((n, tipo, m.group(0)))
    return salida


def _archivos_versionados(raiz: Path) -> list[Path] | None:
    r = subprocess.run(["git", "-C", str(raiz), "ls-files", "-z"], capture_output=True, check=False)
    if r.returncode != 0:
        return None
    return [raiz / p for p in r.stdout.decode("utf-8", "replace").split("\0") if p]


def main(argv: list[str] | None = None, raiz: Path | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    raiz = raiz or Path.cwd()
    arbol = "--arbol" in args
    args = [a for a in args if a != "--arbol"]
    archivos = _archivos_versionados(raiz) if arbol else [Path(a) for a in args]
    if archivos is None:
        print("[guardia-pii] COULD_NOT_RUN: git ls-files fallo; no se pudo enumerar el arbol", file=sys.stderr)
        return 2
    total = 0
    for f in archivos:
        if f.suffix.lower() not in EXTENSIONES_TEXTO or not f.is_file():
            continue
        try:
            texto = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # el archivo ilegible lo marca guardia_integridad, no esta
        for n, tipo, valor in hallazgos_texto(texto):
            total += 1
            print(f"[guardia-pii] {f}:{n}: {tipo} {enmascara(valor)}", file=sys.stderr)
    print(f"[guardia-pii] hallazgos={total} archivos={len(archivos)}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
