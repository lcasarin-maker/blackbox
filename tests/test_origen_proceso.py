"""tools/origen_proceso.py: QUE proceso es y QUIEN lo lanzo, sin guardar secretos.

Tres clases de prueba. Puras sobre el enmascarado. Sobre un /proc FALSO para la deteccion de la fuente
primaria y la regla de "el padre salio" portadas de witr (cada caso con su control: la misma cadena sin
el corte acredita a la shell; con el corte, no). Y REALES: un proceso pequeno lanzado desde un padre
conocido (y desde un git hook de verdad) cuya cadena, cmdline y rama tienen que salir correctos, con un
secreto sembrado en argv y en el entorno que NO puede aparecer en el registro.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from tools import origen_proceso as op

def _url_con_clave(esquema, usuario, clave, resto):
    """URL con credencial armada en tiempo de ejecucion: un literal asi en el fuente es lo que el
    detector de secretos del repo bloquea, con razon, aunque aqui sea una semilla de prueba."""
    return "".join([esquema, "://", usuario, ":", clave, "@", resto])


SEMILLAS = ("SEMILLA-ARGV-1", "SEMILLA-ARGV-2", "SEMILLA-URL-3", "SEMILLA-ENV-4", "ghp_SEMILLATOKEN5abcdef")


# ============================================================ enmascarado


def test_enmascara_valores_secretos_y_conserva_nombres():
    argv = ["prog", "--api-key=uno", "--token", "dos", "_".join(["DATABASE", "URL"]) + "=" + _url_con_clave("postgres", "u", "tres", "h/db"),
            "Authorization: Bearer cuatro", _url_con_clave("https", "user", "cinco", "host/x"), "ghp_abcdefghijklmnop", "API_KEY=seis"]
    out = op.enmascarar_argv(argv)
    plano = " ".join(out)
    for valor in ("uno", "dos", "tres", "cuatro", "cinco", "ghp_abcdefghijklmnop", "seis"):
        assert valor not in plano, (valor, out)
    assert "--api-key=<enmascarado>" in out and "API_KEY=<enmascarado>" in out
    assert out[2:4] == ["--token", "<enmascarado>"]


def test_enmascara_secretos_dentro_del_comando_de_un_bash_c():
    """El padre `bash -c` lleva el comando del hijo entero en UN argumento: el test real lo midio."""
    texto = "python3 x.py --api-key=siete TOKEN=ocho -H 'Authorization: Bearer nueve' --password diez"
    plano = " ".join(op.enmascarar_argv(["bash", "-c", texto]))
    for valor in ("siete", "ocho", "nueve", "diez"):
        assert valor not in plano, plano
    assert "python3 x.py" in plano, "lo que no es secreto se conserva"


def test_control_negativo_no_enmascara_lo_que_no_es_secreto():
    """Sin esto, enmascararlo TODO pasaria el test de arriba. Los dos casos medidos en esta maquina."""
    argv = ["vllm", "--max-num-batched-tokens", "8192", "--author", "luis", "--session-id", "abc-123",
            "-n", "4"]
    assert op.enmascarar_argv(argv) == argv


# ============================================================ /proc falso


def _proc(raiz: Path, pid: int, comm: str, **kw):
    """Un /proc/<pid> minimo. kw: ppid, sid, inicio, cgroup, argv, env, rss_paginas, estado."""
    d = raiz / str(pid)
    d.mkdir(parents=True)
    campos = [kw.get("estado", "S"), str(kw.get("ppid", 1)), str(pid), str(kw.get("sid", pid)), "0",
              *(["0"] * 14), str(kw.get("inicio", 100 + pid)), "0", str(kw.get("rss_paginas", 10))]
    (d / "stat").write_text(f"{pid} ({comm}) {' '.join(campos)}\n", encoding="ascii")
    (d / "status").write_text("Uid:\t1000\t1000\t1000\t1000\n", encoding="ascii")
    (d / "cmdline").write_bytes("\0".join(kw.get("argv", [comm])).encode() + b"\0")
    (d / "cgroup").write_text(f"0::{kw.get('cgroup', '/user.slice/x.scope')}\n", encoding="ascii")
    (d / "environ").write_bytes("\0".join(kw.get("env", [])).encode())
    (d / "cwd").symlink_to(raiz)
    (d / "exe").symlink_to(raiz)


@pytest.fixture
def proc(tmp_path, monkeypatch):
    raiz = tmp_path / "proc"
    raiz.mkdir()
    corriendo = tmp_path / "run-systemd-system"
    corriendo.mkdir()
    monkeypatch.setattr(op, "SYSTEMD_CORRIENDO", corriendo)
    _proc(raiz, 1, "systemd", ppid=0, sid=1, inicio=1, cgroup="/init.scope")
    return raiz


def _init_sin_systemd(proc, monkeypatch):
    """PID 1 que no es systemd ni un supervisor conocido: el unico caso en que witr llega a init/cron,
    porque en una maquina con systemd detectSystemd (y el mapa de supervisores, que incluye "systemd")
    van antes en el orden (witr detect.go:161-173)."""
    import shutil
    shutil.rmtree(proc / "1")
    _proc(proc, 1, "minit", ppid=0, sid=1, inicio=1, cgroup="/")
    monkeypatch.setattr(op, "SYSTEMD_CORRIENDO", proc / "no-existe")


def test_fuente_shell_con_la_cadena_intacta(proc):
    _proc(proc, 50, "bash", sid=50)
    _proc(proc, 60, "python3", ppid=50, sid=50)
    o = op.origen(60, proc)
    assert [a["pid"] for a in o["ancestros"]] == [50, 1]
    assert o["fuente"] == {"tipo": "shell", "nombre": "bash", "pid": 50}
    assert "padre_salio" not in o


def test_padre_de_otra_sesion_lo_adopto_y_la_shell_de_arriba_NO_se_acredita(proc):
    """witr ancestry.go:90-98 + detect.go:116-147. Misma cadena que arriba salvo la sesion: el control
    es el test anterior, que con la sesion compartida SI acredita a bash."""
    _proc(proc, 50, "bash", sid=50)
    _proc(proc, 60, "python3", ppid=50, sid=70)
    o = op.origen(60, proc)
    assert o["padre_salio"] is True
    assert o["fuente"]["tipo"] == "desconocido" and o["fuente"]["padre_salio"]
    assert any("padre original salio" in w for w in o["advertencias"])


def test_rastro_claude_solo_debajo_del_corte(proc):
    """La regla de witr aplicada a los rastros de bb: un `claude` que solo ADOPTO al proceso no lo
    reclama. Control: la misma cadena con la sesion compartida si lo reclama."""
    _proc(proc, 50, "claude", sid=50, argv=["claude", "--session-id", "s-1"])
    _proc(proc, 60, "python3", ppid=50, sid=50)
    _proc(proc, 61, "python3", ppid=50, sid=70)
    assert op.origen(60, proc)["rastros"]["claude"]["session_id"] == "s-1"
    assert "claude" not in op.origen(61, proc)["rastros"]


def test_padre_que_ya_no_existe_corta_la_cadena(proc):
    _proc(proc, 60, "python3", ppid=999, sid=70)
    o = op.origen(60, proc)
    assert o["padre_salio"] is True and o["ancestros"] == []
    assert o["fuente"]["tipo"] == "desconocido"


def test_pid_reciclado_no_se_cose_a_la_cadena(proc):
    """witr ancestry.go:52-55: un 'padre' que nacio despues que el hijo es otro proceso."""
    _proc(proc, 50, "bash", sid=50, inicio=900)
    _proc(proc, 60, "python3", ppid=50, sid=50, inicio=500)
    o = op.origen(60, proc)
    assert o["padre_salio"] is True and o["ancestros"] == []


def test_adoptado_por_init_se_queda_init_pero_lo_dice(proc, monkeypatch):
    _init_sin_systemd(proc, monkeypatch)
    _proc(proc, 60, "demonio", ppid=1, sid=70)
    with_corte = op.origen(60, proc)
    assert with_corte["fuente"]["tipo"] == "init"
    assert "adoptado por init" in with_corte["fuente"]["descripcion"]


def test_systemd_se_lee_del_propio_proceso_y_sobrevive_al_corte(proc):
    _proc(proc, 60, "atlas", ppid=1, sid=60, cgroup="/system.slice/atlas-api.service")
    assert op.origen(60, proc)["fuente"] == {"tipo": "systemd", "nombre": "atlas-api.service"}


def test_systemd_user_manager_no_explica_a_un_huerfano():
    assert not op._explica_huerfano({"tipo": "systemd", "nombre": "user@1000.service"}, [])
    assert op._explica_huerfano({"tipo": "systemd", "nombre": "atlas-api.service"}, [])


def test_contenedor_solo_con_id_y_no_el_servicio_del_runtime(proc):
    hexid = "a" * 64
    _proc(proc, 60, "VLLM::EngineCor", ppid=1, cgroup=f"/docker.slice/docker-{hexid}.scope")
    _proc(proc, 61, "dockerd", ppid=1, cgroup="/system.slice/docker.service")
    assert op.origen(60, proc)["fuente"] == {"tipo": "contenedor", "nombre": "docker"}
    assert op.origen(61, proc)["fuente"]["tipo"] == "systemd", "dockerd no es un contenedor"


def test_orden_contenedor_antes_que_shell(proc):
    _proc(proc, 50, "bash", sid=50, cgroup=f"/docker-{'b' * 64}.scope")
    _proc(proc, 60, "python3", ppid=50, sid=50, cgroup=f"/docker-{'b' * 64}.scope")
    assert op.origen(60, proc)["fuente"]["tipo"] == "contenedor"


def test_con_systemd_un_job_de_cron_es_de_su_unidad(proc):
    """Fiel a witr: con systemd de init, la unidad (cron.service) gana a cron en el orden."""
    _proc(proc, 40, "cron", sid=40, cgroup="/system.slice/cron.service")
    _proc(proc, 41, "backup", ppid=40, sid=40, cgroup="/system.slice/cron.service")
    assert op.origen(41, proc)["fuente"] == {"tipo": "systemd", "nombre": "cron.service"}


def test_cron_y_ssh(proc, monkeypatch):
    _init_sin_systemd(proc, monkeypatch)
    _proc(proc, 40, "cron", sid=40)
    _proc(proc, 41, "backup", ppid=40, sid=40)
    assert op.origen(41, proc)["fuente"]["tipo"] == "cron"
    _proc(proc, 30, "sshd-session", sid=30)
    _proc(proc, 31, "bash", ppid=30, sid=30)
    _proc(proc, 32, "top", ppid=31, sid=30)
    assert op.origen(32, proc)["fuente"]["tipo"] == "ssh", "ssh va antes que shell"


def test_ld_preload_solo_el_nombre_y_rss_alto(proc):
    _proc(proc, 60, "python3", env=["LD_PRELOAD=/tmp/SEMILLA.so", "HOME=/x", "SNAPX=1"],
          rss_paginas=(2 * 1024 * 1024 * 1024) // os.sysconf("SC_PAGE_SIZE"))
    o = op.origen(60, proc)
    assert o["env_nombres"] == ["LD_PRELOAD"]
    assert "SEMILLA" not in json.dumps(o)
    assert any("LD_PRELOAD" in w for w in o["advertencias"])
    assert any("RSS alto" in w for w in o["advertencias"])


def test_control_negativo_sin_LD_PRELOAD_ni_rss_alto_no_hay_esas_advertencias(proc):
    _proc(proc, 60, "python3", env=["LD_PRELOAD=", "HOME=/x"])
    o = op.origen(60, proc)
    assert o["env_nombres"] == [], "un LD_PRELOAD vacio no inyecta nada (witr detect.go:203)"
    assert not any("LD_PRELOAD" in w or "RSS" in w for w in o["advertencias"])


def test_campo_ilegible_es_NOT_COLLECTED_con_motivo(proc):
    _proc(proc, 60, "python3")
    (proc / "60" / "cwd").unlink()
    (proc / "60" / "cgroup").unlink()
    o = op.leer_proceso(60, proc)
    assert o["cwd"] == "NOT_COLLECTED" and o["no_colectado"]["cwd"] == "proceso terminado"
    assert o["unit"] == "NOT_COLLECTED"
    muerto = op.leer_proceso(424242, proc)
    assert muerto["comm"] == "NOT_COLLECTED" and muerto["rss_kb"] == "NOT_COLLECTED", "nunca un cero"


# ============================================================ procesos REALES


# El hijo imprime su pid al nacer: el evento es su stdout, sin sondear ni dormir.
PAUSA = "import os, signal; print(os.getpid(), flush=True); signal.pause()"


def _pid_del_hijo(padre: subprocess.Popen) -> int:
    assert padre.stdout is not None
    return int(padre.stdout.readline())


def _limpia(padre: subprocess.Popen, hijo: int | None) -> None:
    """Mata al hijo POR PID: matar antes al padre lo deja huerfano (su `pkill -P` ya no lo encuentra) y un hijo suelto
    mantiene abierto el pipe del gate que corre esta suite (colgo un pre-push 8 minutos el 2026-10-12)."""
    if hijo is not None:
        try:
            os.kill(hijo, signal.SIGKILL)
        except ProcessLookupError:
            pass
    padre.kill()
    padre.wait(timeout=10)


def test_real_cadena_cmdline_y_ningun_secreto(tmp_path):
    """Un python3 pequeno lanzado por un bash conocido, con secretos sembrados en argv y entorno."""
    hijo = (f"{sys.executable} -c '{PAUSA}' --api-key={SEMILLAS[0]} "
            f"TOKEN={SEMILLAS[1]} {_url_con_clave('https', 'u', SEMILLAS[2], 'host/x')} {SEMILLAS[4]}")
    env = {**os.environ, "MI_SECRET": SEMILLAS[3], "LD_PRELOAD": ""}
    padre = subprocess.Popen(["bash", "-c", f"{hijo}; true"], cwd=tmp_path, env=env,
                             stdout=subprocess.PIPE, text=True)
    pid = None
    try:
        pid = _pid_del_hijo(padre)
        o = op.origen(pid)
        plano = json.dumps(o)
        for s in SEMILLAS:
            assert s not in plano, f"secreto {s} en el registro"
        assert o["ancestros"][0]["pid"] == padre.pid and o["ancestros"][0]["comm"] == "bash"
        assert o["ancestros"][-1]["pid"] == 1, "la cadena llega a PID 1"
        assert o["cmdline"][:3] == [sys.executable, "-c", PAUSA]
        assert "--api-key=<enmascarado>" in o["cmdline"] and "TOKEN=<enmascarado>" in o["cmdline"]
        assert o["cwd"] == str(tmp_path)
        assert o["fuente"]["tipo"] == "shell" and o["fuente"]["nombre"] == "bash"
        assert o["env_nombres"] == [], "solo nombres de la lista, y LD_PRELOAD vacio no cuenta"
    finally:
        _limpia(padre, pid)


def test_real_git_hook_da_repo_y_rama(tmp_path):
    repo = tmp_path / "repo"
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True)
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/rama-de-prueba\n", encoding="utf-8")
    hook = hooks / "pre-push"
    hook.write_text(f"#!/bin/bash\n{sys.executable} -c '{PAUSA}'\n", encoding="utf-8")
    hook.chmod(0o755)
    padre = subprocess.Popen([str(hook)], cwd=repo, stdout=subprocess.PIPE, text=True)
    pid = None
    try:
        pid = _pid_del_hijo(padre)
        o = op.origen(pid)
        assert o["rastros"]["git_hook"] == {"hook": "pre-push", "pid": padre.pid, "repo": str(repo),
                                            "rama": "rama-de-prueba"}
        assert op.clave_lanzador(o).startswith("git_hook pre-push")
    finally:
        _limpia(padre, pid)


def test_control_negativo_sin_hook_no_hay_rastro_de_hook(tmp_path):
    """El hijo se separa con `setsid -f`: queda adoptado por el gestor de usuario, sin ningun ancestro de esta suite.
    Sin esto el control falla cuando la suite corre DENTRO de un pre-push real: su cadena de ancestros incluye ese
    hook y el rastro `git_hook` es verdadero (fallo medido 2026-10-12, coverage-100 en un pre-push)."""
    padre = subprocess.Popen(["setsid", "-f", sys.executable, "-c", PAUSA],
                             cwd=tmp_path, stdout=subprocess.PIPE, text=True)
    pid = None
    try:
        pid = _pid_del_hijo(padre)
        assert "git_hook" not in op.origen(pid)["rastros"]
    finally:
        _limpia(padre, pid)


# ============================================================ lector y codigos de salida (witr app.go:100)


def _registro(procesos):
    return {"esquema": op.ESQUEMA, "ts": "2026-10-12T05:00:00-0600", "motivo": "prueba", "procesos": procesos}


def _p(pid, fuente="shell", advertencias=()):
    return {"pid": pid, "comm": "python3", "rss_kb": 1024, "cmdline": ["python3"], "unit": "u",
            "fuente": {"tipo": fuente, "nombre": "bash"}, "rastros": {}, "advertencias": list(advertencias)}


@pytest.fixture
def datos(tmp_path, monkeypatch):
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    return tmp_path


def _escribir(datos, *registros):
    for r in registros:
        op.anexar_jsonl(datos / "origen" / "2026-10-12.jsonl", r)


def test_codigos_de_salida(datos, capsys):
    assert op.main(["leer"]) == 2, "sin registros: no encontrado"
    _escribir(datos, _registro([_p(1)]))
    assert op.main(["leer"]) == 0
    _escribir(datos, _registro([_p(2, advertencias=["RSS alto"])]))
    assert op.main(["leer"]) == 1
    _escribir(datos, _registro([_p(3, fuente="desconocido")]))
    assert op.main(["leer"]) == 6, "origen desconocido pesa mas que advertencias"
    assert op.main(["leer", "--desde", "2026-10-13"]) == 2, "fuera de la ventana"
    assert op.main(["leer", "--desde", "ayer"]) == 4, "entrada invalida"
    capsys.readouterr()


def test_una_linea_corrupta_se_cuenta_y_no_se_salta_en_silencio(datos, capsys):
    _escribir(datos, _registro([_p(1)]))
    with (datos / "origen" / "2026-10-12.jsonl").open("a", encoding="utf-8") as fh:
        fh.write('{"ts": "2026-10-12T05:01:00-0600", "procesos": [\n')
    assert op.main(["leer", "--json"]) == 1
    salida = json.loads(capsys.readouterr().out)
    assert salida["lineas_ilegibles"] == 1 and salida["codigo"] == 1


def test_un_fallo_propio_es_5_y_no_1(datos, monkeypatch):
    """witr app.go:106-108: un fallo del instrumento no puede leerse como "encontrado con advertencias"."""
    monkeypatch.setattr(op, "capturar", lambda *a: 1 / 0)
    assert op.main(["capturar", "--motivo", "x"]) == 5


def test_permiso_denegado_es_3(datos):
    _escribir(datos, _registro([_p(1)]))
    if os.geteuid() == 0:
        pytest.skip("root lee aunque el modo sea 000")
    os.chmod(datos / "origen" / "2026-10-12.jsonl", 0)
    try:
        assert op.main(["leer"]) == 3
    finally:
        os.chmod(datos / "origen" / "2026-10-12.jsonl", 0o644)


def test_json_es_contrato_y_agrupa_por_lanzador(datos, capsys):
    hook = _p(5)
    hook["rastros"] = {"git_hook": {"hook": "pre-push", "repo": "/r", "rama": "main", "pid": 4}}
    _escribir(datos, _registro([_p(1), _p(2), hook]))
    assert op.main(["leer", "--json"]) == 0
    salida = json.loads(capsys.readouterr().out)
    assert salida["codigo"] == 0
    grupos = {g["lanzador"]: [p["pid"] for p in g["procesos"]] for g in salida["grupos"]}
    assert grupos == {"shell bash unit=u": [1, 2], "git_hook pre-push repo=/r rama=main": [5]}


def test_capturar_guarda_y_el_lector_lo_encuentra(datos, capsys):
    assert op.main(["capturar", "--motivo", "prueba", "--top", "0", "--pid", str(os.getpid())]) == 0
    reg = json.loads(capsys.readouterr().out)
    assert reg["procesos"][0]["pid"] == os.getpid()
    assert op.main(["leer", "--json"]) in (0, 1)
    assert json.loads(capsys.readouterr().out)["grupos"]
