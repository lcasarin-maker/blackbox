"""El portero clasifica por la FORMA del comando. Las tandas `soffice --headless` de otros proyectos quedan sin clase.

Cierre de DEBT-PORTERO-NO-CLASIFICA-TANDAS-DE-LIBREOFFICE-DE-OTROS-PROYECTOS-01. Mientras la ficha siga abierta
`tests/conftest.py` marca el test xfail (tests/known_failures.json).
"""
from __future__ import annotations

from tools import portero


def test_una_conversion_de_libreoffice_headless_tiene_clase():
    argv = ["/usr/lib/libreoffice/program/soffice.bin", "-env:UserInstallation=file:///tmp/perfil", "--headless",
            "--convert-to", "pdf", "--outdir", "/tmp/salida", "/tmp/entrada.docx"]
    assert portero.clasifica(argv) is not None


def test_control_negativo_un_proceso_cualquiera_no_tiene_clase():
    """El instrumento puede decir 'sin clase': un editor o un shell no son trabajo pesado por forma."""
    assert portero.clasifica(["/usr/bin/bash", "-lc", "echo hola"]) is None
