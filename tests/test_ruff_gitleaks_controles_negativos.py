"""Control negativo para los dos gates de terceros que SI pueden bloquear un
commit (ruff, gitleaks) y no tenian ninguno.

La auditoria H1 del 2026-09-28 encontro que SPEC.md afirmaba "cada gate de
este repo que puede bloquear se verifica con control negativo" mientras estos
dos -- ambos de .pre-commit-config.yaml, ambos con stages: [pre-commit] --
no tenian ni uno, a diferencia de bash-sintaxis (ver test_bash_sintaxis.py).

El fixture de gitleaks importa: una clave AWS de ejemplo publica
(AKIAIOSFODNN7EXAMPLE, de la propia documentacion de AWS) NO dispara el
ruleset por defecto de gitleaks 8.30.1 -- medido en vivo antes de escribir
este test. Un bloque PEM si, de forma confiable, sin depender de una regla
especifica de proveedor.
"""
import subprocess


def test_ruff_pasa_sobre_codigo_limpio(tmp_path):
    limpio = tmp_path / "limpio.py"
    limpio.write_text("def f():\n    return 1\n", encoding="utf-8")
    r = subprocess.run(
        ["ruff", "check", "--select", "E9,F821,F632,F811", str(limpio)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout


def test_ruff_FALLA_sobre_un_nombre_no_definido(tmp_path):
    roto = tmp_path / "roto.py"
    roto.write_text("def f():\n    return nombre_no_definido\n", encoding="utf-8")
    r = subprocess.run(
        ["ruff", "check", "--select", "E9,F821,F632,F811", str(roto)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "F821" in r.stdout


def test_gitleaks_pasa_sobre_un_archivo_sin_secretos(tmp_path):
    limpio = tmp_path / "limpio.txt"
    limpio.write_text("nada que ver aqui\n", encoding="utf-8")
    r = subprocess.run(
        ["gitleaks", "detect", "--no-git", "--no-banner", "--source", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr


def test_gitleaks_FALLA_sobre_una_clave_privada_pem(tmp_path):
    # gitleaks:allow -- fixture falsa a proposito, ver docstring del modulo.
    # Partida en dos concatenaciones para que el propio gitleaks de ESTE repo
    # no la lea como un secreto real al escanear este archivo de test.
    cabecera = "-----BEGIN RSA " + "PRIVATE KEY-----"
    pie = "-----END RSA " + "PRIVATE KEY-----"
    (tmp_path / "clave.pem").write_text(
        cabecera + "\n"
        "MIIEpAIBAAKCAQEA1c7+9z5Pad7OejecsaAtl0/CBnEG9EsQIkiN0S4Qmy4mIkxa\n"
        + pie + "\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        ["gitleaks", "detect", "--no-git", "--no-banner", "--source", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
