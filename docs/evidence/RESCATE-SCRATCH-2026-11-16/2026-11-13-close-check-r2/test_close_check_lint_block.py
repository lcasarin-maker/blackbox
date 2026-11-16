"""Aceptacion de la ficha canonica: sigue roja, el reporte vigente no es bloqueo."""
from test_close_check_report_measurement import fixture,policy


def test_aceptacion_bloqueo_pendiente_en_cierre_sin_codigo(tmp_path):
    repo=tmp_path/'r';base,head=fixture(repo)
    r=policy(repo,'--base',base,'--head',head)
    assert r.returncode==1,('criterio pendiente: bloqueo votado tras adjudicar falsos positivos',r.returncode,r.stdout,r.stderr)


def test_aceptacion_clasificador_no_rechaza_ejecucion_real():
    from simple_policy.close_check_lint import classify
    assert classify('shellcheck bin/bb')[0] == 'ejecuta'
    assert classify("python3 - <<'PY'\nfrom product import run\nrun()\nPY")[0] == 'ejecuta'


def test_aceptacion_no_confunde_echo_con_ejecucion():
    from simple_policy.close_check_lint import classify
    assert classify('echo pytest')[0] == 'no_ejecuta'
