"""Control negativo para el gate `bash-sintaxis` (.pre-commit-config.yaml).

La auditoria H1 del 2026-09-28 encontro que SPEC.md afirmaba "cada gate se
verifica con control negativo" mientras este gate -- envuelto en gate_runner
como los demas, pero cuyo comando real es un `bash -n` desnudo -- no tenia
ninguno registrado. Esto prueba lo unico que un control negativo tiene que
probar: que el mismo comando puede dar los dos veredictos, no solo el que ya
esperabamos.
"""
import subprocess


def test_bash_n_pasa_sobre_un_script_real_del_repo():
    r = subprocess.run(["bash", "-n", "bin/bb"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_bash_n_FALLA_sobre_sintaxis_rota(tmp_path):
    roto = tmp_path / "roto.sh"
    roto.write_text("if [ 1 -eq 1 ]; then\n  echo sin cerrar\n", encoding="utf-8")
    r = subprocess.run(["bash", "-n", str(roto)], capture_output=True, text=True)
    assert r.returncode != 0, "bash -n debia rechazar un if sin cerrar"
    assert r.stderr.strip(), "bash -n debia explicar el rechazo, aunque sea en el idioma del sistema"
