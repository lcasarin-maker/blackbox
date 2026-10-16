import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tools import dmem_tope as dt, interruptores

RAIZ = Path(__file__).resolve().parents[1]
APLICAR = RAIZ / "adopted" / "root-scripts" / "dmem-tope-aplicar.sh"
QUITAR = RAIZ / "adopted" / "root-scripts" / "dmem-tope-quitar.sh"
REGION = "nvidia/0000000F:01:00.0/vidmem"
CAPACIDAD = 53794045952
ID = "d" * 64


# ---- parte pura y de medicion ----

def test_lee_region_exige_una_sola_region():
    assert dt.lee_region(f"{REGION} {CAPACIDAD}\n") == (REGION, CAPACIDAD)
    for malo in ("", f"{REGION} max\n", f"{REGION}\n", f"{REGION} 1\n{REGION}2 2\n", "a b c\n"):
        assert dt.lee_region(malo) is None


def test_lee_consumo_busca_la_region_exacta():
    assert dt.lee_consumo(f"otra 5\n{REGION} 7\n", REGION) == 7
    assert dt.lee_consumo(f"{REGION} max\n", REGION) is None
    assert dt.lee_consumo("", REGION) is None


def test_evalua_cabe_y_cada_causa_de_rechazo():
    ok = {"motor": 30 * dt.GIB, "user": 5 * dt.GIB}
    assert dt.evalua(CAPACIDAD, ok) == (True, [])
    cabe, m = dt.evalua(None, ok)
    assert not cabe and "sin region" in m[0]
    cabe, m = dt.evalua(40 * dt.GIB, ok)
    assert not cabe and "capacidad" in m[0]
    cabe, m = dt.evalua(CAPACIDAD, {"motor": 41 * dt.GIB, "user": 5 * dt.GIB})
    assert not cabe and "motor usa" in m[0]
    cabe, m = dt.evalua(CAPACIDAD, {"motor": 1, "user": 9 * dt.GIB})
    assert not cabe and "user usa" in m[0]
    cabe, m = dt.evalua(CAPACIDAD, {"motor": None, "user": None})
    assert not cabe and len(m) == 2 and all("NOT_COLLECTED" in x for x in m)


def arbol(tmp_path: Path, motor: int | str = 30 * dt.GIB, user: int | str = 5 * dt.GIB, id_: str = ID) -> tuple[Path, Path]:
    raiz = tmp_path / "cg"
    (raiz / "docker.slice" / f"docker-{id_}.scope").mkdir(parents=True)
    (raiz / "user.slice").mkdir()
    (raiz / "dmem.capacity").write_text(f"{REGION} {CAPACIDAD}\n", encoding="utf-8")
    for cg, v in ((raiz / "docker.slice" / f"docker-{id_}.scope", motor), (raiz / "user.slice", user)):
        (cg / "dmem.current").write_text(f"{REGION} {v}\n", encoding="utf-8")
        (cg / "dmem.max").write_text(f"{REGION} max\n", encoding="utf-8")
    (raiz / "docker.slice" / f"docker-{id_}.scope" / "memory.max").write_text("80530636800\n", encoding="utf-8")
    (raiz / "user.slice" / f"user-{os.getuid()}.slice").mkdir()
    (raiz / "user.slice" / f"user-{os.getuid()}.slice" / "memory.max").write_text("max\n", encoding="utf-8")
    proc = tmp_path / "proc"
    (proc / "4242").mkdir(parents=True)
    (proc / "4242" / "cgroup").write_text(f"0::/docker.slice/docker-{id_}.scope\n", encoding="utf-8")
    (proc / "4242" / "comm").write_text("VLLM::EngineCor\n", encoding="utf-8")
    (proc / "1").mkdir()
    (proc / "1" / "comm").write_text("systemd\n", encoding="utf-8")
    (proc / "1" / "cgroup").write_text("0::/init.scope\n", encoding="utf-8")
    return raiz, proc


def test_avisos_solo_cuando_managed_y_pinned_quedan_sin_tope():
    assert dt.avisos({"motor": "80530636800", "user": "51539607552"}) == []
    a = dt.avisos({"motor": "max", "user": None})
    assert len(a) == 2 and "motor: memory.max=max" in a[0] and "user: memory.max=ilegible" in a[1]


def test_estado_dice_si_el_tope_esta_puesto(tmp_path, capsys):
    raiz, proc = arbol(tmp_path)
    assert dt.principal(["--estado"], lambda a: (0, ""), raiz, proc) == 1  # dmem.max = max: sin tope
    assert capsys.readouterr().out.strip() == "motor=sin tope user=sin tope"
    (raiz / "docker.slice" / f"docker-{ID}.scope" / "dmem.max").write_text(f"{REGION} {40 * dt.GIB}\n", encoding="utf-8")
    (raiz / "user.slice" / "dmem.max").write_text(f"{REGION} {8 * dt.GIB}\n", encoding="utf-8")
    assert dt.principal(["--estado"], lambda a: (0, ""), raiz, proc) == 0
    assert capsys.readouterr().out.strip() == "motor=40GiB user=8GiB"
    (raiz / "dmem.capacity").write_text("", encoding="utf-8")  # sin region no se puede leer ningun tope
    assert dt.topes_puestos(raiz, proc) == {"motor": None, "user": None}


def test_un_argumento_desconocido_se_rechaza_y_no_corre_una_pasada(datos, tmp_path, capsys):
    fija_modo(datos, "observar")
    llamadas: list[list[str]] = []
    assert dt.principal(["--estadoX"], lambda a: (llamadas.append(a), (0, ""))[1], *arbol(tmp_path)) == 2
    assert "uso:" in capsys.readouterr().err
    assert llamadas == [] and not (datos / "interruptores").exists()  # no midio ni registro nada


def test_cgroup_motor_y_sus_negativos(tmp_path):
    _, proc = arbol(tmp_path)
    assert dt.cgroup_motor(proc) == f"/docker.slice/docker-{ID}.scope"
    (proc / "4243").mkdir()  # un segundo proceso del motor en OTRO cgroup: ambiguo, no se elige
    (proc / "4243" / "comm").write_text("VLLM::EngineCor\n", encoding="utf-8")
    (proc / "4243" / "cgroup").write_text("0::/docker.slice/docker-" + "e" * 64 + ".scope\n", encoding="utf-8")
    assert dt.cgroup_motor(proc) is None
    (proc / "4243" / "cgroup").write_text(f"0::/docker.slice/docker-{ID}.scope\n", encoding="utf-8")  # el mismo cgroup: vale
    assert dt.cgroup_motor(proc) == f"/docker.slice/docker-{ID}.scope"
    (proc / "4242" / "cgroup").write_text("0::/user.slice/otra\n", encoding="utf-8")
    (proc / "4243" / "cgroup").write_text("0::/user.slice/otra\n", encoding="utf-8")
    assert dt.cgroup_motor(proc) is None  # forma que no es un scope
    (proc / "4242" / "cgroup").write_text("sin linea cgroup v2\n", encoding="utf-8")
    assert dt.cgroup_motor(proc) is None
    assert dt.cgroup_motor(proc / "no-existe") is None


def test_mide_lee_los_dos_consumos_y_se_calla_sin_region(tmp_path):
    raiz, proc = arbol(tmp_path)
    m = dt.mide(raiz, proc)
    assert m["capacidad"] == CAPACIDAD and m["consumo"] == {"motor": 30 * dt.GIB, "user": 5 * dt.GIB}
    assert m["memory_max"] == {"motor": "80530636800", "user": "max"}
    (raiz / "dmem.capacity").write_text("", encoding="utf-8")
    sin_region = dt.mide(raiz, proc)
    assert sin_region["capacidad"] is None and sin_region["consumo"] == {"motor": None, "user": None}
    raiz2, proc2 = arbol(tmp_path / "b")
    (proc2 / "4242" / "comm").write_text("otro\n", encoding="utf-8")  # sin proceso del motor
    sin_motor = dt.mide(raiz2, proc2)
    assert sin_motor["consumo"] == {"motor": None, "user": 5 * dt.GIB} and sin_motor["memory_max"]["motor"] is None


# ---- interruptor ----

@pytest.fixture()
def datos(tmp_path, monkeypatch):
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path / "datos"))
    return tmp_path / "datos"


def fija_modo(datos: Path, modo: str) -> None:
    datos.mkdir(parents=True, exist_ok=True)
    (datos / "interruptores.json").write_text(json.dumps({"modos": {dt.NOMBRE: modo}}), encoding="utf-8")


def filas(datos: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in (datos / "interruptores" / f"{dt.NOMBRE}.jsonl").read_text(encoding="utf-8").splitlines()]


def test_off_no_mide_ni_registra(datos, tmp_path, capsys):
    llamadas: list[list[str]] = []
    assert dt.principal([], lambda a: (llamadas.append(a), (0, ""))[1], *arbol(tmp_path)) == 0
    assert llamadas == [] and not (datos / "interruptores").exists()
    assert "off" in capsys.readouterr().out


def test_observar_registra_y_no_escribe(datos, tmp_path):
    fija_modo(datos, "observar")
    llamadas: list[list[str]] = []

    def ejecuta(argv):
        llamadas.append(argv)
        return 0, ""

    assert dt.principal([], ejecuta, *arbol(tmp_path)) == 0
    assert llamadas == []  # observar nunca llama a sudo
    assert filas(datos)[0]["accion"] == "aplicaria"
    assert filas(datos)[0]["avisos"] == ["user: memory.max=max; managed y pinned no tienen tope"]


def test_observar_con_consumo_sobre_el_tope_rechaza(datos, tmp_path):
    fija_modo(datos, "observar")
    assert dt.principal([], lambda a: (0, ""), *arbol(tmp_path, motor=41 * dt.GIB)) == 3
    assert filas(datos)[0]["accion"] == "rechaza"


def test_actuar_llama_al_script_sellado_solo_si_cabe(datos, tmp_path):
    fija_modo(datos, "actuar")
    llamadas: list[list[str]] = []

    def ejecuta(argv):
        llamadas.append(argv)
        return 0, "listo"

    assert dt.principal([], ejecuta, *arbol(tmp_path)) == 0
    assert ["sudo", "-n", "bb-root-run", "dmem-tope-aplicar"] in llamadas
    assert filas(datos)[-1]["accion"] == "aplicado"
    llamadas.clear()
    assert dt.principal([], ejecuta, *arbol(tmp_path / "x", motor=41 * dt.GIB)) == 3
    assert not any(a[0] == "sudo" for a in llamadas)  # control negativo: no cabe, no escribe


def test_actuar_con_el_script_fallando_devuelve_rc_3(datos, tmp_path):
    fija_modo(datos, "actuar")

    def ejecuta(argv):
        return 3, "dmem-tope-aplicar: no"

    assert dt.principal([], ejecuta, *arbol(tmp_path)) == 3
    assert filas(datos)[-1]["accion"] == "fallo_al_aplicar"


def test_ejecuta_real_y_sus_fallos():
    assert dt._ejecuta(["echo", "hola"]) == (0, "hola\n")
    assert dt._ejecuta(["/no/existe"])[0] == 127
    assert dt._lee(Path("/no/existe")) == ""


# ---- scripts sellados, con arbol de cgroup falso ----

def entorno(tmp_path: Path, raiz: Path, proc: Path) -> dict[str, str]:
    estado = tmp_path / "estado"
    estado.mkdir(exist_ok=True)
    return {**os.environ, "BB_DMEM_CGROUP_RAIZ": str(raiz), "BB_DMEM_PROC": str(proc),
            "BB_DMEM_ESTADO": str(estado), "BB_DMEM_UID_ESPERADO": str(os.getuid())}


def corre(script: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, timeout=60, check=False)


def valor(cg: Path) -> str:
    return (cg / "dmem.max").read_text(encoding="utf-8").split()[1]


def test_script_aplica_guarda_previos_y_quitar_los_devuelve(tmp_path):
    raiz, proc = arbol(tmp_path)
    env = entorno(tmp_path, raiz, proc)
    motor = raiz / "docker.slice" / f"docker-{ID}.scope"
    r = corre(APLICAR, env)
    assert r.returncode == 0, r.stderr
    assert valor(motor) == str(dt.TOPE_MOTOR_GIB * dt.GIB) and valor(raiz / "user.slice") == str(dt.TOPE_USER_GIB * dt.GIB)
    previo = json.loads((tmp_path / "estado" / "dmem-tope-previo.json").read_text(encoding="utf-8"))
    assert previo["motor"]["previo"] == "max" and previo["region"] == REGION
    q = corre(QUITAR, env)
    assert q.returncode == 0, q.stderr
    assert valor(motor) == "max" and valor(raiz / "user.slice") == "max"
    assert not (tmp_path / "estado" / "dmem-tope-previo.json").exists()


def test_script_aplica_no_toca_nada_cuando_el_consumo_pasa_el_tope(tmp_path):
    raiz, proc = arbol(tmp_path, motor=41 * dt.GIB)
    r = corre(APLICAR, entorno(tmp_path, raiz, proc))
    assert r.returncode == 3 and "por encima del tope" in r.stderr
    assert valor(raiz / "docker.slice" / f"docker-{ID}.scope") == "max"  # control negativo: sin escritura


def _dos_cgroups(raiz: Path, proc: Path, env: dict[str, str], tmp_path: Path) -> None:
    (proc / "4243").mkdir()
    (proc / "4243" / "comm").write_text("VLLM::EngineCor\n", encoding="utf-8")
    (proc / "4243" / "cgroup").write_text("0::/docker.slice/docker-" + "e" * 64 + ".scope\n", encoding="utf-8")


def _motor(raiz: Path) -> Path:
    return raiz / "docker.slice" / f"docker-{ID}.scope"


ROMPE = {
    "capacity_vacio": (lambda raiz, proc, env, tmp: (raiz / "dmem.capacity").write_text("", encoding="utf-8"), "UNA region"),
    "capacity_ilegible": (lambda raiz, proc, env, tmp: (raiz / "dmem.capacity").write_text(f"{REGION} mucho\n", encoding="utf-8"), "capacidad ilegible"),
    "sin_motor": (lambda raiz, proc, env, tmp: (proc / "4242" / "comm").write_text("otro\n", encoding="utf-8"), "no esta corriendo"),
    "dos_cgroups": (lambda raiz, proc, env, tmp: _dos_cgroups(raiz, proc, env, tmp), "mas de un cgroup"),
    "cgroup_raro": (lambda raiz, proc, env, tmp: (proc / "4242" / "cgroup").write_text("0::/system.slice/otro.service\n", encoding="utf-8"), "cgroup inesperado"),
    "sin_dmem": (lambda raiz, proc, env, tmp: (_motor(raiz) / "dmem.max").unlink(), "no tiene archivos dmem"),
    "topes_no_caben": (lambda raiz, proc, env, tmp: (raiz / "dmem.capacity").write_text(f"{REGION} {10 * dt.GIB}\n", encoding="utf-8"), "no caben"),
    "estado_ausente": (lambda raiz, proc, env, tmp: env.update(BB_DMEM_ESTADO=str(tmp / "no-existe")), "no es un directorio normal"),
    "consumo_ilegible": (lambda raiz, proc, env, tmp: (_motor(raiz) / "dmem.current").write_text(f"{REGION} mucho\n", encoding="utf-8"), "consumo ilegible"),
    "user_sobre_tope": (lambda raiz, proc, env, tmp: (raiz / "user.slice" / "dmem.current").write_text(f"{REGION} {9 * dt.GIB}\n", encoding="utf-8"), "user.slice usa"),
}


@pytest.mark.parametrize("rompe", sorted(ROMPE))
def test_script_aplica_se_niega_en_cada_guarda(tmp_path, rompe):
    raiz, proc = arbol(tmp_path)
    env = entorno(tmp_path, raiz, proc)
    cambio, mensaje = ROMPE[rompe]
    cambio(raiz, proc, env, tmp_path)
    r = corre(APLICAR, env)
    assert r.returncode == 3 and mensaje in r.stderr, (r.returncode, r.stderr)


@pytest.mark.skipif(os.getuid() == 0, reason="root escribe en archivos de solo lectura")
def test_script_aplica_revierte_si_la_segunda_escritura_falla(tmp_path):
    raiz, proc = arbol(tmp_path)
    (raiz / "user.slice" / "dmem.max").chmod(stat.S_IRUSR)
    r = corre(APLICAR, entorno(tmp_path, raiz, proc))
    assert r.returncode == 3 and "se devolvieron los valores previos" in r.stderr
    assert valor(raiz / "docker.slice" / f"docker-{ID}.scope") == "max"  # el motor volvio a su valor previo


def test_script_quitar_sus_guardas(tmp_path):
    raiz, proc = arbol(tmp_path)
    env = entorno(tmp_path, raiz, proc)
    assert corre(QUITAR, env).returncode == 3  # sin previo
    assert corre(APLICAR, env).returncode == 0
    previo_ruta = tmp_path / "estado" / "dmem-tope-previo.json"
    previo = json.loads(previo_ruta.read_text(encoding="utf-8"))
    malo = {**previo, "motor": {**previo["motor"], "cgroup": str(raiz / "system.slice" / "x")}}
    previo_ruta.write_text(json.dumps(malo), encoding="utf-8")
    r = corre(QUITAR, env)
    assert r.returncode == 3 and "fuera de lo permitido" in r.stderr
    malo = {**previo, "user": {**previo["user"], "previo": "mucho"}}
    previo_ruta.write_text(json.dumps(malo), encoding="utf-8")
    assert "ilegible" in corre(QUITAR, env).stderr
    previo_ruta.write_text(json.dumps(previo), encoding="utf-8")
    assert corre(QUITAR, {**env, "BB_DMEM_UID_ESPERADO": "999999"}).returncode == 3  # no es de root
    # el motor ya no existe: se omite y el resto se restaura
    import shutil
    shutil.rmtree(raiz / "docker.slice" / f"docker-{ID}.scope")
    r = corre(QUITAR, env)
    assert r.returncode == 0 and "se omite" in r.stdout and valor(raiz / "user.slice") == "max"


def _constante(texto: str, nombre: str) -> int:
    m = re.search(rf"^{nombre}=(\d+)$", texto, re.M)
    assert m is not None, nombre
    return int(m.group(1))


def test_los_topes_del_script_y_del_modulo_coinciden():
    texto = APLICAR.read_text(encoding="utf-8")
    assert _constante(texto, "tope_motor_gib") == dt.TOPE_MOTOR_GIB
    assert _constante(texto, "tope_user_gib") == dt.TOPE_USER_GIB
    assert f"comm_motor={dt.COMM_MOTOR}" in texto


def test_main_corre_el_modulo(tmp_path, monkeypatch):
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    r = subprocess.run(["python3", "-m", "tools.dmem_tope"], cwd=RAIZ, capture_output=True, text=True, timeout=60, check=False,
                       env={**os.environ, "BLACKBOX_DATA": str(tmp_path)})
    assert r.returncode == 0 and "interruptor off" in r.stdout
    assert interruptores.modo(dt.NOMBRE) == "off"
