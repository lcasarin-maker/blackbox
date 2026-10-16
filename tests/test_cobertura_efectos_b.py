"""Cobertura de efectos (parte B): accion_termica, aviso_termico y origen_proceso.

Archivos reales en `tmp_path`, ejecutables de shell minimos en un PATH propio (systemctl y notify-send
de prueba: nunca los del sistema) y un /proc falso. Los `while True` no se ejecutan: el sleep de la
iteracion lanza una excepcion que corta el bucle (solo en el hilo principal).
"""

from __future__ import annotations

import json
import runpy
import sys
import threading
import warnings
from datetime import datetime, timezone
from pathlib import Path
from time import sleep as _dormir_real
from typing import Any

import pytest

from tools import accion_termica as at
from tools import aviso_termico as av
from tools import origen_proceso as op


class _Fin(Exception):
    """Corta un `while True` desde el sleep de su iteracion."""


def _corta_en(monkeypatch: pytest.MonkeyPatch, modulo: Any, iteraciones: int) -> list[float]:
    pausas: list[float] = []

    def pausa(segundos: float) -> None:
        if threading.current_thread() is not threading.main_thread():
            _dormir_real(segundos)  # blocking-sleep: los hilos que no son el principal (muestreador de GPU) conservan su pausa real; el principal levanta _Fin -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01  # sunset-reviewed: 4.2 -- re-revisado 2026-10-16 contra 4.1 (`git log -L36,36:tests/test_cobertura_efectos_b.py 4d6d1771..HEAD`: 0 commits, la linea no cambio desde el release 4.1.0; la razon sigue valiendo); re-revisado 2026-10-15 contra 4.0 (`git log -L` c4977a8b..HEAD sobre la linea +-6: 0 commits, linea identica a la revision 4.0 c4977a8b; sigue en la rama de hilos no principales del sleep sustituto _corta_en); re-revisado 2026-10-15 contra 3.9 (`git log -L`: ultimo cambio de la linea anterior a la revision 3.9, 9aec733f); re-revisado 2026-10-13 contra 3.5: `git blame` de la linea 36 (7280a6a4) es anterior al bump 3.5.0 (b99560e8), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.4: `git blame` de la linea 36 (095c3a35) es anterior al bump 3.4.1 (eb89c383), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.3: `git blame` de la linea 36 (b008b6ee) es anterior al bump 3.3.0 (3512a16a), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.2: `git blame` de la linea 36 (804713d5) es anterior al bump 3.2.0 (e8e5aa8d), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.1: `git blame` de la linea 36 (93850773) es anterior al bump 3.1.0 (7a5bd48b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 3.0: `git blame` de la linea 36 (4df311d3) es anterior al bump 2.9.1 (ab63e2b), la linea no cambio desde su revision anterior; la razon sigue valiendo: revisado 2026-10-12: doble de prueba de `time.sleep`, acotado por el segundo parametro de cada prueba ; re-revisado 2026-10-13 contra 3.1: la linea no cambio desde 20256295 (git blame de esta linea)
            return
        pausas.append(segundos)
        if len(pausas) >= iteraciones:
            raise _Fin()

    monkeypatch.setattr(modulo.time, "sleep", pausa)
    return pausas


def _bin(directorio: Path, nombre: str, cuerpo: str) -> Path:
    directorio.mkdir(parents=True, exist_ok=True)
    f = directorio / nombre
    f.write_text("#!/bin/sh\n" + cuerpo + "\n", encoding="utf-8")
    f.chmod(0o755)
    return f


def _solo_path(monkeypatch: pytest.MonkeyPatch, directorio: Path) -> None:
    directorio.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PATH", str(directorio))


# ============================================================ accion_termica


def test_accion_systemctl_de_prueba_devuelve_codigo_y_salida(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _bin(tmp_path / "bin", "systemctl", 'echo "$@"\necho "falla" >&2\nexit "$FAKE_RC"')
    _solo_path(monkeypatch, tmp_path / "bin")
    monkeypatch.setenv("FAKE_RC", "3")
    assert at._systemctl(["is-active", "a.scope"]) == (3, "--user is-active a.scope\nfalla")
    monkeypatch.setenv("FAKE_RC", "0")
    assert at._systemctl(["freeze", "a.scope"])[0] == 0


def test_accion_sin_systemctl_es_127_y_no_lanza(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _solo_path(monkeypatch, tmp_path / "vacio")
    rc, salida = at._systemctl(["is-active", "a.scope"])
    assert rc == 127 and "systemctl" in salida


def test_accion_carga_con_esquema_equivocado_o_que_no_es_objeto(tmp_path: Path) -> None:
    ruta = tmp_path / "carga.json"
    ruta.write_text(json.dumps({"esquema": "otro/9", "unidades": [{"unidad": "a.scope", "pausable": True}]}), encoding="utf-8")
    assert at.lee_carga(ruta) == ([], "atlas_carga.json no es atlas-carga/1")
    ruta.write_text("[]", encoding="utf-8")
    assert at.lee_carga(ruta) == ([], "atlas_carga.json no es atlas-carga/1")
    ruta.write_text(json.dumps({"esquema": "atlas-carga/1", "unidades": [{"unidad": "a.scope", "pausable": True}]}), encoding="utf-8")
    assert at.lee_carga(ruta) == (["a.scope"], "")  # control: con el esquema bueno si lee


def test_accion_log_inservible_no_tumba_la_decision(tmp_path: Path) -> None:
    estorbo = tmp_path / "es_archivo"
    estorbo.write_text("", encoding="utf-8")
    carga = tmp_path / "carga.json"
    carga.write_text(json.dumps({"esquema": "atlas-carga/1", "unidades": []}), encoding="utf-8")
    eventos = at.aplica("sostenida", carga=carga, congeladas=tmp_path / "c.json", log=estorbo / "l.jsonl",
                        ejecutar=lambda a: (0, ""))
    assert eventos[0]["accion"] == "ninguna" and estorbo.read_text(encoding="utf-8") == ""


def test_accion_log_sano_si_escribe_la_fila(tmp_path: Path) -> None:
    """Control negativo del anterior: con un log escribible la misma decision deja su fila."""
    carga = tmp_path / "carga.json"
    carga.write_text(json.dumps({"esquema": "atlas-carga/1", "unidades": []}), encoding="utf-8")
    log = tmp_path / "l.jsonl"
    at.aplica("sostenida", carga=carga, congeladas=tmp_path / "c.json", log=log, ejecutar=lambda a: (0, ""))
    assert json.loads(log.read_text(encoding="utf-8"))["accion"] == "ninguna"


# ============================================================ aviso_termico


def _estado_termico(ruta: Path, estado: str) -> None:
    ahora = datetime.now(timezone.utc).isoformat()
    ruta.write_text(json.dumps({"esquema": "bb-estado-termico/1", "estado": estado, "desde": ahora,
                                "zona_mas_caliente": "thermal_zone0", "temp_c": 97.0, "actualizado": ahora}), encoding="utf-8")


def _lee_desde(monkeypatch: pytest.MonkeyPatch, ruta: Path) -> None:
    monkeypatch.setattr(av.lee, "__defaults__", (ruta,))


def test_aviso_una_vez_imprime_la_etiqueta_y_el_dato(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    estado = tmp_path / "estado_termico.json"
    _estado_termico(estado, "sostenida")
    _lee_desde(monkeypatch, estado)
    assert av.main(["--una-vez"]) == 0
    salida = json.loads(capsys.readouterr().out)
    assert salida["etiqueta"] == "sostenida" and salida["dato"]["zona_mas_caliente"] == "thermal_zone0"


def test_aviso_una_vez_sin_archivo_es_desconocido(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Control negativo: sin el archivo del sampler no se inventa un `normal`."""
    _lee_desde(monkeypatch, tmp_path / "no-existe.json")
    assert av.main(["--una-vez"]) == 0
    assert json.loads(capsys.readouterr().out) == {"etiqueta": "desconocido", "dato": None}


def _entorno_bucle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, estado: str) -> tuple[Path, list[tuple[str, ...]]]:
    """Archivo de estado real, notify-send de prueba que anota lo que recibe, y la accion termica real
    con sus rutas en tmp_path y un systemctl inyectado por el parametro `ejecutar` que ya ofrece."""
    ruta = tmp_path / "estado_termico.json"
    _estado_termico(ruta, estado)
    _lee_desde(monkeypatch, ruta)
    avisos = tmp_path / "avisos.txt"
    _bin(tmp_path / "bin", "notify-send", f'echo "$@" >> "{avisos}"')
    _solo_path(monkeypatch, tmp_path / "bin")
    carga = tmp_path / "carga.json"
    carga.write_text(json.dumps({"esquema": "atlas-carga/1", "unidades": [{"unidad": "job.scope", "pausable": True}]}), encoding="utf-8")
    llamadas: list[tuple[str, ...]] = []

    def sistema(args: list[str]) -> tuple[int, str]:
        llamadas.append(tuple(args))
        return 0, ""

    aplica_real = at.aplica

    def aplica(etiqueta: str) -> list[dict[str, Any]]:
        return aplica_real(etiqueta, carga=carga, congeladas=tmp_path / "c.json", log=tmp_path / "l.jsonl", ejecutar=sistema)

    monkeypatch.setattr(av.accion_termica, "aplica", aplica)
    return avisos, llamadas


def test_aviso_bucle_notifica_el_cambio_y_congela_en_cada_vuelta_caliente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    avisos, llamadas = _entorno_bucle(tmp_path, monkeypatch, "sostenida")
    pausas = _corta_en(monkeypatch, av, 2)
    with pytest.raises(_Fin):
        av.main([])
    assert pausas == [av.INTERVALO_S] * 2
    assert avisos.read_text(encoding="utf-8").count("calor sostenido") == 1  # el aviso es del CAMBIO: la 2a vuelta no repite
    assert llamadas.count(("freeze", "job.scope")) == 1  # la 2a vuelta ya la tenia congelada
    assert json.loads((tmp_path / "c.json").read_text(encoding="utf-8")) == ["job.scope"]


def test_aviso_bucle_en_normal_el_primer_arranque_no_avisa_ni_congela(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Control negativo: el mismo bucle con estado normal no notifica ni toca systemctl."""
    avisos, llamadas = _entorno_bucle(tmp_path, monkeypatch, "normal")
    _corta_en(monkeypatch, av, 1)
    with pytest.raises(_Fin):
        av.main([])
    assert not avisos.exists()
    assert [x for x in llamadas if x[0] == "freeze"] == []


def test_aviso_bucle_un_fallo_de_la_accion_se_dice_y_no_tumba_el_vigilante(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    avisos, _ = _entorno_bucle(tmp_path, monkeypatch, "sostenida")

    def averia(etiqueta: str) -> list[dict[str, Any]]:
        raise OSError("disco lleno")

    monkeypatch.setattr(av.accion_termica, "aplica", averia)
    _corta_en(monkeypatch, av, 1)
    with pytest.raises(_Fin):
        av.main([])
    assert "COULD_NOT_ACT: disco lleno" in capsys.readouterr().err
    assert "calor sostenido" in avisos.read_text(encoding="utf-8")  # el aviso salio pese a la averia


def test_aviso_como_script_con_una_vez_sale_con_0(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["aviso_termico.py", "--una-vez"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with pytest.raises(SystemExit) as salida:
            runpy.run_module("tools.aviso_termico", run_name="__main__")
    assert salida.value.code == 0
    assert set(json.loads(capsys.readouterr().out)) == {"etiqueta", "dato"}


# ============================================================ origen_proceso


def _proc(raiz: Path, pid: int, comm: str, **kw: Any) -> None:
    """Un /proc/<pid> minimo. kw: ppid, sid, inicio, cgroup, argv, env, estado, tty, exe."""
    d = raiz / str(pid)
    d.mkdir(parents=True)
    campos = [kw.get("estado", "S"), str(kw.get("ppid", 1)), str(pid), str(kw.get("sid", pid)), str(kw.get("tty", 0)),
              *(["0"] * 14), str(kw.get("inicio", 100 + pid)), "0", "10"]
    (d / "stat").write_text(f"{pid} ({comm}) {' '.join(campos)}\n", encoding="ascii")
    (d / "status").write_text("Uid:\t1000\t1000\t1000\t1000\n", encoding="ascii")
    (d / "cmdline").write_bytes("\0".join(kw.get("argv", [comm])).encode() + b"\0")
    (d / "cgroup").write_text(kw.get("cgroup_crudo", f"0::{kw.get('cgroup', '/user.slice/x.scope')}\n"), encoding="ascii")
    (d / "environ").write_bytes("\0".join(kw.get("env", [])).encode())
    (d / "cwd").symlink_to(kw.get("cwd", raiz))
    (d / "exe").symlink_to(kw.get("exe", raiz))


@pytest.fixture
def proc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    raiz = tmp_path / "proc"
    raiz.mkdir()
    corriendo = tmp_path / "run-systemd-system"
    corriendo.mkdir()
    monkeypatch.setattr(op, "SYSTEMD_CORRIENDO", corriendo)
    _proc(raiz, 1, "systemd", ppid=0, sid=1, inicio=1, cgroup="/init.scope")
    return raiz


def test_origen_un_campo_ilegible_por_otro_motivo_lleva_el_nombre_del_error(proc: Path) -> None:
    _proc(proc, 60, "python3")
    (proc / "60" / "cmdline").unlink()
    (proc / "60" / "cmdline").mkdir()  # leer un directorio: IsADirectoryError, ni permiso ni proceso terminado
    o = op.leer_proceso(60, proc)
    assert o["cmdline"] == op.NOT_COLLECTED
    assert o["no_colectado"]["cmdline"].startswith("IsADirectoryError")


def test_origen_tty_de_pts_de_otro_dispositivo_y_sin_tty() -> None:
    assert op._tty(0) is None
    assert op._tty((136 << 8) | 3) == "pts/3"
    assert op._tty((137 << 8) | 1) == "pts/257"
    assert op._tty((4 << 8) | 1) == "dev 4:1"  # control: fuera de 136..143 no es un pts


def test_origen_el_tty_sale_del_stat_del_proceso(proc: Path) -> None:
    _proc(proc, 60, "python3", tty=(136 << 8) | 5)
    assert op.leer_proceso(60, proc)["tty"] == "pts/5"


def test_origen_cgroup_v1_es_UNSUPPORTED_y_no_una_unidad_inventada(proc: Path) -> None:
    _proc(proc, 60, "python3", cgroup_crudo="12:memory:/docker/abc\n1:name=systemd:/x\n")
    o = op.leer_proceso(60, proc)
    assert o["cgroup"] == op.UNSUPPORTED and o["unit"] == op.UNSUPPORTED


def test_origen_un_ciclo_de_padres_corta_la_cadena(proc: Path) -> None:
    _proc(proc, 50, "bash", ppid=60, sid=60, inicio=10)
    _proc(proc, 60, "python3", ppid=50, sid=60, inicio=20)
    cadena = op.ancestros(op.leer_proceso(60, proc), proc)
    assert [a["pid"] for a in cadena] == [50]  # al volver a 60 se detiene: sin bucle infinito


def test_origen_kubepods_y_snap_son_contenedor_y_sin_ellos_no(proc: Path) -> None:
    _proc(proc, 60, "python3", ppid=1, sid=70, cgroup="/kubepods/burstable/pod1/abc")
    assert op.origen(60, proc)["fuente"] == {"tipo": "contenedor", "nombre": "kubernetes"}
    _proc(proc, 61, "python3", ppid=1, sid=71, env=["SNAP_NAME=firefox", "HOME=/x"])
    assert op.origen(61, proc)["fuente"] == {"tipo": "contenedor", "nombre": "snap"}
    _proc(proc, 62, "python3", ppid=1, sid=72, env=["FLATPAK_ID=org.x.App"])
    assert op.origen(62, proc)["fuente"]["nombre"] == "flatpak"
    _proc(proc, 63, "python3", ppid=1, sid=73, env=["HOME=/x"])
    assert op.origen(63, proc)["fuente"]["tipo"] != "contenedor"


def test_origen_multiplexores_y_unidad_sin_servicio() -> None:
    assert op._multiplexor("tmux") == "tmux" and op._multiplexor("tmux: server") == "tmux"
    assert op._multiplexor("screen") == "screen" and op._multiplexor("SCREEN") == "screen"
    assert op._multiplexor("bash") is None
    assert op.unidad_systemd("/user.slice/user-1000.slice") == ""
    assert op.unidad_systemd("/user.slice/app.slice/job.scope") == "job.scope"


def test_origen_un_ancestro_tmux_es_la_shell_que_lanzo(proc: Path) -> None:
    _proc(proc, 50, "tmux: server", sid=50)
    _proc(proc, 60, "python3", ppid=50, sid=50)
    assert op.origen(60, proc)["fuente"] == {"tipo": "shell", "nombre": "tmux", "pid": 50}


def _eslabon(pid: int, comm: str, argv: list[str] | None = None) -> dict[str, Any]:
    return {"pid": pid, "comm": comm, "cmdline": argv if argv is not None else [comm], "cgroup": "/x"}


def test_origen_supervisor_init_solo_sin_shell_y_gunicorn_por_su_argv() -> None:
    assert op._supervisor([_eslabon(9, "init")]) == {"tipo": "supervisor", "nombre": "init"}
    assert op._supervisor([_eslabon(9, "init"), _eslabon(8, "bash")]) is None  # control: con shell en la cadena no
    assert op._supervisor([_eslabon(9, "python3", ["/usr/bin/gunicorn", "app:x"])]) == {"tipo": "supervisor", "nombre": "gunicorn"}
    assert op._supervisor([_eslabon(9, "python3", ["python3", "app.py"])]) is None


def test_origen_init_exige_que_no_haya_shell_de_por_medio() -> None:
    sin_shell = [_eslabon(60, "x"), _eslabon(1, "minit")]
    assert op._init(sin_shell) == {"tipo": "init", "nombre": "minit"}
    con_shell = [_eslabon(60, "x"), _eslabon(50, "bash"), _eslabon(1, "minit")]
    assert op._init(con_shell) is None


def test_origen_rama_sin_cwd_con_gitdir_enlazado_y_roto(tmp_path: Path) -> None:
    assert op._rama(op.NOT_COLLECTED) == op.NOT_COLLECTED
    assert op._rama(op.UNSUPPORTED) == op.NOT_COLLECTED
    real = tmp_path / "wt" / "realgit"
    real.mkdir(parents=True)
    (real / "HEAD").write_text("ref: refs/heads/rama-x\n", encoding="utf-8")
    trabajo = tmp_path / "wt" / "arbol"
    trabajo.mkdir()
    (trabajo / ".git").write_text("gitdir: ../realgit\n", encoding="utf-8")
    assert op._rama(str(trabajo)) == "rama-x"
    roto = tmp_path / "roto"
    roto.mkdir()
    (roto / ".git").write_text("no es un gitdir\n", encoding="utf-8")
    assert op._rama(str(roto)) == op.NOT_COLLECTED
    suelto = tmp_path / "sin_repo"
    suelto.mkdir()
    assert op._rama(str(suelto)) == op.NOT_COLLECTED


def test_origen_sesion_de_claude_por_opcion_con_igual_sin_opcion_y_sin_lista() -> None:
    assert op._sesion_claude(["claude", "--session-id", "s-1"]) == "s-1"
    assert op._sesion_claude(["claude", "--resume=s-2"]) == "s-2"
    assert op._sesion_claude(["claude", "-r", "s-3"]) == "s-3"
    assert op._sesion_claude(["claude", "--resume"]) == op.NOT_COLLECTED  # la opcion sin valor
    assert op._sesion_claude(["claude", "--model", "x"]) == op.NOT_COLLECTED
    assert op._sesion_claude(op.NOT_COLLECTED) == op.NOT_COLLECTED


def test_origen_advertencias_de_zombi_detenido_y_binario_borrado(proc: Path, tmp_path: Path) -> None:
    _proc(proc, 60, "python3", estado="Z", ppid=1, sid=70)
    assert "proceso zombi (defunct)" in op.origen(60, proc)["advertencias"]
    _proc(proc, 61, "python3", estado="T", ppid=1, sid=71)
    assert "proceso detenido (estado T)" in op.origen(61, proc)["advertencias"]
    _proc(proc, 62, "python3", ppid=1, sid=72, exe=str(tmp_path / "borrado (deleted)"))
    assert "corre desde un binario borrado" in op.origen(62, proc)["advertencias"]
    _proc(proc, 63, "python3", ppid=1, sid=73)  # control: sano, sin esas tres
    w = op.origen(63, proc)["advertencias"]
    assert not any("zombi" in x or "detenido" in x or "borrado" in x for x in w)


def test_origen_la_clave_de_un_lanzador_claude_lleva_cwd_y_sesion() -> None:
    p = {"rastros": {"claude": {"cwd": "/w", "session_id": "s-9"}}, "fuente": {"tipo": "shell", "nombre": "bash"}, "unit": "u"}
    assert op.clave_lanzador(p) == "claude cwd=/w session=s-9"
    assert op.clave_lanzador({**p, "rastros": {}}) == "shell bash unit=u"  # control: sin rastro manda la fuente


def test_origen_main_con_argumentos_invalidos_es_4_y_con_ayuda_es_0(capsys: pytest.CaptureFixture[str]) -> None:
    assert op.main([]) == op.SALIDA_ENTRADA_INVALIDA
    assert "usage" in capsys.readouterr().err
    assert op.main(["--help"]) == op.SALIDA_OK
    assert "origen de procesos" in capsys.readouterr().out
    assert op.main(["capturar"]) == op.SALIDA_ENTRADA_INVALIDA  # falta --motivo

