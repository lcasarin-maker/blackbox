"""Suspension de `sudo panic` (tools/boton_rojo.py): shims de systemctl y docker en PATH y raiz falsa (BB_ROJO_RAIZ).

Ninguna prueba toca la maquina real: el home, /run/user y /var/lib viven bajo
tmp_path. `restaura` entra por la linea de comandos de verdad (`panic restaura [todo si]`,
tools/panic.py). Controles negativos obligatorios (docs/PANIC.md):
  (i)   una unidad KEEP suspendida hace fallar `keep_intactas` (control: lista mutada);
  (ii)  borrar en vez de renombrar lo detecta `test_renombra_nunca_borra`;
  (iii) el manifiesto se fsyncea antes de la primera accion, y lo persistente va antes que lo vivo;
  (iv)  restaura se niega ante un sha256 distinto y no toca el archivo;
  (v)   la segunda corrida no duplica unidades ni contenedores.
"""

from __future__ import annotations

import getpass
import json
import os
import pwd
import stat
import sys
import textwrap
import time
from pathlib import Path

import pytest

from tools import boton_rojo as br
from tools import panic

pytestmark = pytest.mark.integration

SYSTEMCTL = r'''
import glob, json, os, sys, time
st_path, log = os.environ["SHIM_STATE"], os.environ["SHIM_LOG"]
st = json.load(open(st_path))
a = sys.argv[1:]
man = glob.glob(os.environ["SHIM_MANIFIESTOS"], recursive=True)
with open(log, "a") as fh:
    fh.write(json.dumps({"argv": ["systemctl"] + a, "manifiesto": bool(man), "t": time.time()}) + "\n")
if st.get("cuelga"):
    time.sleep(30)
a = [x for x in a if x not in ("--user", "--no-block", "--") and not x.startswith("--machine=")]
cmd, rest = a[0], a[1:]
u = st["units"]
if cmd == "show":
    names = [x for x in rest if not x.startswith("-") and x not in ("Id", "UnitFileState", "ActiveState")]
    print("\n\n".join(f"Id={n}\nUnitFileState={u.get(n, ['not-found', 'inactive'])[0]}\nActiveState={u.get(n, ['x', 'inactive'])[1]}" for n in names))
elif cmd == "list-units":
    print("\n".join(st.get("scopes", [])))
elif cmd in ("stop", "start", "enable"):
    if any(n in st.get("falla", []) for n in rest):
        sys.stderr.write(f"Failed to {cmd}\n"); sys.exit(5)
    for n in rest:
        e, ac = u.get(n, ["enabled", "inactive"])
        u[n] = [("enabled" if cmd == "enable" else e), ("active" if cmd == "start" else "inactive" if cmd == "stop" else ac)]
json.dump(st, open(st_path, "w"))
'''

DOCKER = r'''
import json, os, sys, time
st_path, log = os.environ["SHIM_DOCKER_STATE"], os.environ["SHIM_LOG"]
a = sys.argv[1:]
with open(log, "a") as fh:
    fh.write(json.dumps({"argv": ["docker"] + a, "t": time.time()}) + "\n")
if a[0] == "stop":
    time.sleep(float(os.environ.get("SHIM_DOCKER_STOP_SLEEP", "0")))
st = json.load(open(st_path))
cs = st["containers"]
por_nombre = {c["Name"].lstrip("/"): c for c in cs}
if a[0] == "ps":
    print("\n".join(c["Id"] for c in cs if c["State"]["Running"] or "-aq" in a))
elif a[0] == "inspect":
    print(json.dumps([c for c in cs if c["Id"] in a[1:]]))
elif a[0] == "update":
    pol = a[1].split("=", 1)[1]
    for n in a[2:]:
        por_nombre[n]["HostConfig"]["RestartPolicy"]["Name"] = pol; print(n)
elif a[0] == "stop":
    for n in a[3:]:
        por_nombre[n]["State"]["Running"] = False; print(n)
elif a[0] == "start":
    por_nombre[a[1]]["State"]["Running"] = True; print(a[1])
json.dump(st, open(st_path, "w"))
'''

KEEP_TXT = textwrap.dedent("""\
    # comentario
    bb-aviso-termico
    blackbox-*
    [suspende]
    ai-nemotron*
    kb-nightly*
    own-chats-*
""")

UNIDADES = {
    "bb-aviso-termico.service": ["enabled", "active"],
    "blackbox-sample.timer": ["enabled", "active"],
    "ai-nemotron.service": ["enabled", "active"],
    "kb-nightly.timer": ["enabled", "active"],
    "kb-nightly.service": ["static", "inactive"],
    "nueva-cosa.service": ["disabled", "inactive"],
    "own-chats-sync.service": ["enabled", "active"],
}


def _c(cid, nombre, runtime, pol, corriendo, gpu=False):
    dr = [{"Driver": "nvidia", "Count": -1, "Capabilities": [["gpu"]]}] if gpu else None
    return {"Id": cid, "Name": "/" + nombre, "State": {"Running": corriendo},
            "HostConfig": {"Runtime": runtime, "DeviceRequests": dr, "RestartPolicy": {"Name": pol}}}


CONTENEDORES = [
    _c("a1", "nemotron-server", "nvidia", "no", True),
    _c("b2", "aequitas-vllm", "runc", "unless-stopped", True, gpu=True),
    _c("c3", "aequitas-pg", "runc", "unless-stopped", True),
    _c("d4", "bolt-test", "nvidia", "always", False),
]


class Maquina:
    def __init__(self, tmp: Path, monkeypatch: pytest.MonkeyPatch, contenedores=CONTENEDORES) -> None:
        self.raiz = tmp / "raiz"
        usuario = getpass.getuser()
        pw = pwd.getpwnam(usuario)
        self.home = self.raiz / pw.pw_dir.lstrip("/")
        self.ud = self.home / ".config" / "systemd" / "user"
        self.ud.mkdir(parents=True)
        self.susp = self.home / ".local/share/blackbox/suspensiones"
        self.respaldo = self.raiz / "var/lib/blackbox/rojo"
        self.marca = self.raiz / "var/lib/blackbox/rojo.activo"
        self.manager = self.raiz / f"run/user/{pw.pw_uid}/systemd/private"
        self.manager.parent.mkdir(parents=True)
        self.manager.write_text("")
        otro = tmp / "otro_proyecto"
        otro.mkdir()
        for n in UNIDADES:
            cuerpo = f"[Service]\nExecStart=/bin/true # {n}\n"
            if n == "own-chats-sync.service":
                (otro / n).write_text(cuerpo)
                (self.ud / n).symlink_to(otro / n)
            else:
                (self.ud / n).write_text(cuerpo)
        (self.ud / "atlas-api.service.d").mkdir()
        (self.ud / "foo.service.bak").write_text("viejo")
        (self.ud / "default.target.wants").mkdir()
        self.keep = tmp / "keep.txt"
        self.keep.write_text(KEEP_TXT)
        shims = tmp / "shims"
        shims.mkdir()
        for nombre, cuerpo in (("systemctl", SYSTEMCTL), ("docker", DOCKER)):
            f = shims / nombre
            f.write_text(f"#!{sys.executable}\n{cuerpo}")
            f.chmod(f.stat().st_mode | stat.S_IXUSR)
        self.state = tmp / "state.json"
        self.docker_state = tmp / "docker.json"  # aparte: docker stop corre EN PARALELO con systemctl
        self.docker_state.write_text(json.dumps({"containers": contenedores}))
        self.log = tmp / "log.jsonl"
        self.estado_shim({"units": dict(UNIDADES),
                          "scopes": ["run-u1.scope loaded active running /usr/bin/git push origin master",
                                     "liberation_job_1.scope loaded active running /usr/bin/timeout 2m x",
                                     "app-gnome-foo-1.scope loaded active running Application launched",
                                     "init.scope loaded active running System and Service Manager"]})
        monkeypatch.setenv("BB_ROJO_RAIZ", str(self.raiz))
        monkeypatch.setenv("BB_ROJO_USUARIO", usuario)
        monkeypatch.delenv("BB_ROJO_COMO_ROOT", raising=False)
        monkeypatch.setenv("SHIM_STATE", str(self.state))
        monkeypatch.setenv("SHIM_DOCKER_STATE", str(self.docker_state))
        monkeypatch.setenv("SHIM_LOG", str(self.log))
        monkeypatch.setenv("SHIM_MANIFIESTOS", str(self.susp / "*-boton-rojo*.json"))
        monkeypatch.setenv("PATH", f"{shims}{os.pathsep}{os.environ['PATH']}")

    def estado_shim(self, st: dict | None = None) -> dict:
        if st is not None:
            self.state.write_text(json.dumps(st))
        return json.loads(self.state.read_text())

    def docker_estado(self) -> list[dict]:
        return json.loads(self.docker_state.read_text())["containers"]

    def llamadas(self, prog: str | None = None) -> list[dict]:
        if not self.log.exists():
            return []
        todas = [json.loads(ln) for ln in self.log.read_text().splitlines()]
        return [c for c in todas if prog is None or c["argv"][0] == prog]

    def corre(self, *args: str) -> int:
        if args:
            return panic.main(list(args))
        return br.suspende(self.keep, "prueba")

    def manifiesto(self) -> dict:
        (m,) = br.manifiestos(br.Ctx())
        return json.loads(m.read_text())

    def corriendo(self) -> dict[str, bool]:
        return {c["Name"].lstrip("/"): c["State"]["Running"] for c in self.docker_estado()}

    def politicas(self) -> dict[str, str]:
        return {c["Name"].lstrip("/"): c["HostConfig"]["RestartPolicy"]["Name"]
                for c in self.docker_estado()}


@pytest.fixture
def maq(tmp_path, monkeypatch):
    return Maquina(tmp_path, monkeypatch)


def keep_intactas(ud: Path, keep_txt: Path) -> None:
    """Toda unidad KEEP sigue en su nombre; ninguna `.suspendido-*` es KEEP."""
    keep, _ = br.lee_listas(keep_txt)
    for f in ud.iterdir():
        if ".suspendido-" in f.name:
            assert not br.casa(f.name.split(".suspendido-")[0], keep), f"unidad KEEP suspendida: {f.name}"
    for n in UNIDADES:
        if br.casa(n, keep):
            assert (ud / n).exists(), f"unidad KEEP desaparecio: {n}"


# (i) ----------------------------------------------------------------------


def test_keep_nunca_se_suspende(maq):
    assert maq.corre() == 0
    keep_intactas(maq.ud, maq.keep)
    assert (maq.ud / "bb-aviso-termico.service").is_file()
    assert (maq.ud / "blackbox-sample.timer").is_file()


def test_control_negativo_keep_mutada_si_falla(maq):
    """Control de (i): se suspende con una lista SIN bb-aviso-termico y se juzga con la real."""
    real = maq.keep.read_text()
    maq.keep.write_text(real.replace("bb-aviso-termico\n", ""))
    assert maq.corre() == 0
    maq.keep.write_text(real)
    with pytest.raises(AssertionError, match="unidad KEEP"):
        keep_intactas(maq.ud, maq.keep)


def test_keep_real_cubre_la_lista_del_brief():
    keep, suspende = br.lee_listas(br.KEEP)
    for n in ("bb-muestreo-corte", "bb-aviso-termico", "bb-aviso-gpu-reset", "bb-guardia-proceso",
              "bb-portero", "bb-vigilante-memavail", "bb-vigilante-termico", "bb-reboot-verdict",
              "bb-modulo-nvidia-registro", "bb-arranque-forense", "bb-reloj-arranque",
              "atom-gpu-telemetry", "atom-crash-detector", "blackbox-sample", "blackbox-drift",
              "ai-gpu-telemetry"):
        assert br.casa(n + ".service", keep), n
    for n in ("ai-nemotron.service", "ai-nemotron-vigilante.timer", "ai-ollama.service",
              "atlas-api.service", "bb-canario-motor.timer", "bb-dmem-tope.timer"):
        assert not br.casa(n, keep) and br.casa(n, suspende), n


# (ii) ---------------------------------------------------------------------


def test_renombra_nunca_borra(maq):
    antes = {f.name: (br.sha256(f), br.modo(f), f.lstat().st_uid) for f in maq.ud.iterdir()
             if f.name.endswith(br.SUFIJOS)}
    assert maq.corre() == 0
    fecha = maq.manifiesto()["fecha"]
    for nombre, (h, md, uid) in antes.items():
        vivo, susp = maq.ud / nombre, maq.ud / f"{nombre}.suspendido-{fecha}"
        assert os.path.lexists(vivo) or os.path.lexists(susp), f"{nombre} BORRADA"
        if os.path.lexists(susp):
            assert (br.sha256(susp), br.modo(susp), susp.lstat().st_uid) == (h, md, uid)
    assert (maq.ud / f"own-chats-sync.service.suspendido-{fecha}").is_symlink()
    assert (maq.ud / "foo.service.bak").exists() and (maq.ud / "atlas-api.service.d").is_dir()


# (iii) --------------------------------------------------------------------


def test_manifiesto_fsync_antes_y_lo_persistente_antes_que_lo_vivo(maq, monkeypatch):
    eventos: list[str] = []
    fsync_real, rename_real = os.fsync, os.rename
    corre_real, lanza_real = br.Ejecutor.corre, br.Ejecutor.lanza

    def fsync(fd):
        eventos.append("fsync")
        fsync_real(fd)

    def rename(a, b):
        hay = any(maq.susp.glob("*-boton-rojo*.json"))
        eventos.append("rename" if hay else "rename SIN MANIFIESTO")
        rename_real(a, b)

    def corre(self, cmd, timeout):
        eventos.append(" ".join(cmd))
        return corre_real(self, cmd, timeout)

    def lanza(cmd):
        eventos.append(" ".join(cmd))
        return lanza_real(cmd)

    monkeypatch.setattr(br.os, "fsync", fsync)
    monkeypatch.setattr(br.os, "rename", rename)
    monkeypatch.setattr(br.Ejecutor, "corre", corre)
    monkeypatch.setattr(br.Ejecutor, "lanza", staticmethod(lanza))
    assert maq.corre() == 0

    def primero(pred):
        return next(i for i, e in enumerate(eventos) if pred(e))

    assert "rename SIN MANIFIESTO" not in eventos
    i_rename = primero(lambda e: e == "rename")
    i_update = primero(lambda e: e.startswith("docker update"))
    i_stop = primero(lambda e: e.startswith("systemctl") and " stop " in e)
    i_dstop = primero(lambda e: e.startswith("docker stop"))
    assert "fsync" in eventos[:i_rename]
    assert i_rename < i_update < min(i_stop, i_dstop)
    stops = [c for c in maq.llamadas("systemctl") if "stop" in c["argv"]]
    assert stops and all(c["manifiesto"] for c in stops)
    assert maq.marca.is_file()


def test_el_reporte_nombra_sin_clasificar_contenedores_y_scopes(maq, capsys):
    assert maq.corre() == 0
    out = capsys.readouterr().out
    assert "nueva-cosa.service" in out and "SIN CLASIFICAR" in out
    assert "aequitas-vllm" in out and "nemotron-server" in out and "aequitas-pg" not in out
    assert "run-u1.scope: /usr/bin/git push origin master" in out
    assert "liberation_job_1.scope: /usr/bin/timeout 2m x" in out
    assert "app-gnome-foo-1" not in out and "init.scope" not in out
    assert "SIGUEN CORRIENDO (scopes transitorios; no se matan): 2" in out


def test_suspende_completo(maq):
    assert maq.corre() == 0
    m = maq.manifiesto()
    assert m["esquema"] == "bb-suspension/1" and m["estado"] == "completo"
    assert {u["unidad"] for u in m["unidades"]} == {
        "ai-nemotron.service", "kb-nightly.timer", "kb-nightly.service",
        "nueva-cosa.service", "own-chats-sync.service"}
    u = next(u for u in m["unidades"] if u["unidad"] == "ai-nemotron.service")
    modo_real = oct((maq.ud / f"ai-nemotron.service.suspendido-{m['fecha']}").stat().st_mode & 0o7777)
    assert (u["enabled"], u["active"], u["modo"], u["detenida"]) == ("enabled", "active", modo_real, True)
    assert len(u["sha256"]) == 64
    assert next(u for u in m["unidades"] if u["unidad"] == "nueva-cosa.service")["sin_clasificar"]
    assert {c["nombre"]: c["restart_policy"] for c in m["contenedores"]} == {
        "nemotron-server": "no", "aequitas-vllm": "unless-stopped", "bolt-test": "always"}
    assert maq.corriendo() == {"nemotron-server": False, "aequitas-vllm": False,
                               "aequitas-pg": True, "bolt-test": False}  # la base de datos sigue
    assert maq.politicas() == {"nemotron-server": "no", "aequitas-vllm": "no",
                               "aequitas-pg": "unless-stopped", "bolt-test": "no"}
    assert maq.estado_shim()["units"]["bb-aviso-termico.service"][1] == "active"
    assert ["systemctl", "--user", "daemon-reload"] in [c["argv"] for c in maq.llamadas()]
    assert m["fecha"] in maq.marca.read_text()


def test_como_root_va_por_machine(maq, monkeypatch):
    monkeypatch.setenv("BB_ROJO_COMO_ROOT", "1")
    assert maq.corre() == 0
    u = getpass.getuser()
    llamadas = maq.llamadas("systemctl")
    assert llamadas and all(c["argv"][1:3] == [f"--machine={u}@.host", "--user"] for c in llamadas)


def test_manager_abajo_omite_stop_sin_fallar(maq, capsys):
    """Ciclo de reboot: aun no hay sesion. Renombres y docker si; systemctl ni se llama."""
    maq.manager.unlink()
    assert maq.corre() == 0
    out = capsys.readouterr().out
    assert "manager de usuario" in out and "OMITIDOS" in out
    assert maq.llamadas("systemctl") == []
    assert not (maq.ud / "ai-nemotron.service").exists()
    assert maq.manifiesto()["estado"] == "completo"
    assert maq.politicas()["aequitas-vllm"] == "no"


def test_manifiesto_cae_a_var_lib_si_el_home_no_deja(maq, capsys):
    maq.susp.parent.mkdir(parents=True)
    maq.susp.parent.chmod(0o500)
    try:
        assert maq.corre() == 0
    finally:
        maq.susp.parent.chmod(0o700)
    out = capsys.readouterr().out
    assert f"el manifiesto va a {maq.respaldo}" in out
    (m,) = maq.respaldo.glob("*-boton-rojo.json")
    assert json.loads(m.read_text())["estado"] == "completo"
    assert not (maq.ud / "ai-nemotron.service").exists()


def test_stop_fallido_es_could_not_run_y_renombra_igual(maq, capsys):
    st = maq.estado_shim()
    st["falla"] = ["kb-nightly.timer"]
    maq.estado_shim(st)
    assert maq.corre() == 1
    assert "systemctl stop (5 unidades)" in capsys.readouterr().out
    assert not (maq.ud / "kb-nightly.timer").exists()


def test_systemd_mudo_no_bloquea_los_renombres(maq, monkeypatch):
    monkeypatch.setattr(br, "T_SYSTEMCTL", 1)
    monkeypatch.setattr(br, "T_RELOAD", 1)
    st = maq.estado_shim()
    st["cuelga"] = True
    maq.estado_shim(st)
    assert maq.corre() == 1
    assert not (maq.ud / "ai-nemotron.service").exists()
    assert len(maq.llamadas("systemctl")) == 1  # tras el primer timeout no se insiste


@pytest.mark.parametrize("args", [["seco"], ["estado"], ["--seco"], ["restaura", "si"], ["restaura", "todo", "no"]])
def test_la_interfaz_publica_solo_tiene_panic_y_restaura(maq, capsys, args):
    """`seco` y `estado` salieron de la interfaz (YAGNI): ahora son uso equivocado y no tocan nada."""
    antes = sorted(f.name for f in maq.ud.iterdir())
    assert maq.corre(*args) == 2
    assert "uso: sudo panic" in capsys.readouterr().out
    assert sorted(f.name for f in maq.ud.iterdir()) == antes and maq.llamadas() == []


# (v) ----------------------------------------------------------------------


def test_segunda_corrida_no_duplica(maq, capsys):
    assert maq.corre() == 0
    m1 = maq.manifiesto()
    assert maq.corre() == 0
    m2 = maq.manifiesto()
    assert len(m2["unidades"]) == len(m1["unidades"]) == len({u["unidad"] for u in m2["unidades"]})
    assert len(m2["contenedores"]) == len(m1["contenedores"])
    assert [c["tipo"] for c in m2["corridas"]] == ["primera corrida", "segunda corrida"]
    assert m2["corridas"][1]["nuevas"] == []
    assert m2["creado"] == m1["creado"]  # no se piso
    assert "UNIDADES suspendidas: 0" in capsys.readouterr().out.split("[segunda corrida]")[1]


def test_continua_un_manifiesto_a_medias(maq, monkeypatch):
    """Corte tras renombrar la primera unidad: la siguiente corrida termina las demas."""
    rename_real = os.rename
    n = {"i": 0}

    def rename(a, b):
        n["i"] += 1
        if n["i"] == 2:
            raise KeyboardInterrupt("corte")
        rename_real(a, b)

    monkeypatch.setattr(br.os, "rename", rename)
    with pytest.raises(KeyboardInterrupt):
        maq.corre()
    assert maq.manifiesto()["estado"] == "en_curso"
    monkeypatch.setattr(br.os, "rename", rename_real)
    assert maq.corre() == 0
    m = maq.manifiesto()
    assert m["estado"] == "completo" and all(u["hecho"] for u in m["unidades"])
    assert [c["tipo"] for c in m["corridas"]] == ["primera corrida", "continuacion"]


# (iv) ---------------------------------------------------------------------


def test_restaura_se_niega_ante_sha256_distinto(maq, capsys):
    assert maq.corre() == 0
    fecha = maq.manifiesto()["fecha"]
    alterada = maq.ud / f"kb-nightly.timer.suspendido-{fecha}"
    alterada.write_text("[Timer]\nOnCalendar=minutely\n")
    assert maq.corre("restaura") == 1
    out = capsys.readouterr().out
    assert "kb-nightly.timer: NO se toca -- sha256 distinto" in out
    assert alterada.exists() and not (maq.ud / "kb-nightly.timer").exists()
    assert (maq.ud / "kb-nightly.service").exists()  # las verificables si vuelven
    assert maq.manifiesto()["estado"] == "restaurado_parcial"
    assert maq.marca.exists()  # sigue pulsado


def test_restaura_sin_todo_no_arranca_el_motor(maq, capsys):
    assert maq.corre() == 0
    assert maq.corre("restaura") == 0
    out = capsys.readouterr().out
    st = maq.estado_shim()
    assert (maq.ud / "ai-nemotron.service").is_file()  # el archivo vuelve
    assert st["units"]["ai-nemotron.service"][1] == "inactive"  # pero no arranca
    assert st["units"]["kb-nightly.timer"][1] == "active"
    assert st["units"]["nueva-cosa.service"][1] == "inactive"  # estaba inactiva: sigue asi
    assert maq.corriendo()["aequitas-vllm"] is False and maq.politicas()["aequitas-vllm"] == "no"
    assert "sudo panic restaura todo si" in out
    assert maq.corre("restaura", "todo") == 0  # `todo` sin `si` tampoco arranca
    assert maq.estado_shim()["units"]["ai-nemotron.service"][1] == "inactive"
    assert maq.corre("restaura", "todo", "si") == 0
    assert maq.estado_shim()["units"]["ai-nemotron.service"][1] == "active"
    assert maq.corriendo() == {"nemotron-server": True, "aequitas-vllm": True,
                               "aequitas-pg": True, "bolt-test": False}  # bolt-test estaba parado
    assert maq.politicas() == {"nemotron-server": "no", "aequitas-vllm": "unless-stopped",
                               "aequitas-pg": "unless-stopped", "bolt-test": "always"}
    assert maq.manifiesto()["estado"] == "restaurado" and not maq.marca.exists()


def test_restaura_con_manager_abajo_deja_el_arranque_pendiente(maq):
    assert maq.corre() == 0
    maq.manager.unlink()
    assert maq.corre("restaura") == 1
    assert (maq.ud / "kb-nightly.timer").is_file()
    assert maq.manifiesto()["estado"] == "restaurado_parcial"
    maq.manager.write_text("")
    assert maq.corre("restaura", "todo", "si") == 0
    assert maq.estado_shim()["units"]["kb-nightly.timer"][1] == "active"


def test_restaura_redondo_devuelve_los_archivos_identicos(maq):
    antes = {f.name: (br.sha256(f), os.path.islink(f), br.modo(f)) for f in maq.ud.iterdir()}
    assert maq.corre() == 0
    assert maq.corre("restaura", "todo", "si") == 0
    assert {f.name: (br.sha256(f), os.path.islink(f), br.modo(f)) for f in maq.ud.iterdir()} == antes


def test_tras_restaurar_otra_pulsacion_abre_manifiesto_nuevo(maq):
    assert maq.corre() == 0
    assert maq.corre("restaura", "todo", "si") == 0
    assert maq.corre() == 0
    nombres = [p.name for p in br.manifiestos(br.Ctx())]
    assert len(nombres) == 2 and nombres[1].endswith("-boton-rojo-2.json")


def test_sin_lista_keep_no_toca_nada(maq):
    maq.keep.unlink()
    assert maq.corre() == 2
    assert (maq.ud / "ai-nemotron.service").exists() and maq.llamadas() == []


# tiempos ------------------------------------------------------------------


def test_tiempo_sin_contenedores_menos_de_5s(tmp_path, monkeypatch, capsys):
    maq = Maquina(tmp_path, monkeypatch, contenedores=[])
    t0 = time.monotonic()
    assert maq.corre() == 0
    dur = time.monotonic() - t0
    with capsys.disabled():
        print(f"\n[tiempo] sin contenedores: {dur:.2f} s")
    assert dur < 5


def test_tiempo_con_contenedores_y_docker_stop_lento_menos_de_20s(maq, monkeypatch, capsys):
    """docker stop tarda el -t 5 entero (peor caso del shim): sigue bajo 20 s."""
    monkeypatch.setenv("SHIM_DOCKER_STOP_SLEEP", str(br.DOCKER_STOP_T))
    t0 = time.monotonic()
    assert maq.corre() == 0
    dur = time.monotonic() - t0
    with capsys.disabled():
        print(f"\n[tiempo] con contenedores, docker stop {br.DOCKER_STOP_T} s: {dur:.2f} s")
    assert dur < 20
    # en paralelo: systemctl stop no espera a docker stop
    stop_sys = next(c["t"] for c in maq.llamadas("systemctl") if "stop" in c["argv"])
    stop_doc = next(c["t"] for c in maq.llamadas("docker") if c["argv"][1] == "stop")
    assert stop_sys - stop_doc < br.DOCKER_STOP_T
