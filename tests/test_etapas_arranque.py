"""Etapas de arranque: etapa-marca.sh (lo corre bb-etapa@.service), sus unidades y tools/etapas_arranque.py.

Cada comprobacion lleva su control negativo: la marca que falla al escribir sigue saliendo 0, el arranque que no llega
a multi-user deja la ultima etapa en basic (y el que llega, en multi-user), y la verificacion de las unidades caza un
drop-in con una clave mal escrita y un ciclo de orden sembrados a proposito.
"""

from __future__ import annotations

import configparser
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from tools import etapas_arranque as ea

RAIZ = Path(__file__).resolve().parent.parent
UNIDADES = RAIZ / "adopted" / "system-units"
MARCA = UNIDADES / "etapa-marca.sh"
LEEME = UNIDADES / "LEEME-etapas.md"
BOOT = "0f1e2d3c-4b5a-4978-8a6b-5c4d3e2f1a0b"
OTRO = "11111111-2222-4333-8444-555555555555"
DISPARADORES = {"local-fs.target": ["local-fs"], "basic.target": ["basic", "gpu-lista"],
                "network-online.target": ["network-online"], "multi-user.target": ["multi-user"],
                "graphical.target": ["graphical"], "gdm.service": ["gdm"], "user@.service": ["sesion-%i"]}


# --- etapa-marca.sh -------------------------------------------------------------------------

def _raiz_marca(tmp_path: Path) -> dict[str, str]:
    base = tmp_path / "var-lib-blackbox"
    base.mkdir(mode=0o755)
    base.chmod(0o755)
    (tmp_path / "boot_id").write_text(BOOT + "\n", encoding="utf-8")
    (tmp_path / "uptime").write_text("12.34 40.00\n", encoding="utf-8")
    return {"PATH": "/usr/bin:/bin", "BB_ETAPA_DIR": str(base / "arranque"), "BB_ETAPA_KMSG": str(tmp_path / "kmsg"),
            "BB_ETAPA_BOOT_ID": str(tmp_path / "boot_id"), "BB_ETAPA_UPTIME": str(tmp_path / "uptime")}


def _marca(env: dict[str, str], etapa: str = "basic") -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(MARCA), etapa], env=env, capture_output=True, text=True, timeout=30, check=False)


def _lineas(env: dict[str, str]) -> list[dict[str, Any]]:
    f = Path(env["BB_ETAPA_DIR"]) / "etapas.jsonl"
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()]


def test_marca_escribe_una_linea_valida_y_el_kmsg(tmp_path: Path):
    env = _raiz_marca(tmp_path)
    r = _marca(env)
    assert r.returncode == 0, r.stderr
    (fila,) = _lineas(env)
    assert set(fila) == {"boot_id", "etapa", "monotonic", "realtime"}
    assert (fila["boot_id"], fila["etapa"], fila["monotonic"]) == (BOOT, "basic", 12.34)
    assert isinstance(fila["realtime"], float) and fila["realtime"] > 1.7e9
    assert Path(env["BB_ETAPA_KMSG"]).read_text(encoding="utf-8") == f"<3>bb-etapa basic {BOOT}\n"
    d = Path(env["BB_ETAPA_DIR"])
    assert oct(d.stat().st_mode & 0o777) == "0o755" and oct((d / "etapas.jsonl").stat().st_mode & 0o777) == "0o644"


def test_marca_con_disco_imposible_sale_0_y_el_kmsg_igual_llega(tmp_path: Path):
    env = _raiz_marca(tmp_path)
    (tmp_path / "archivo").write_text("x", encoding="utf-8")
    env["BB_ETAPA_DIR"] = str(tmp_path / "archivo" / "arranque")  # su padre es un archivo: mkdir no puede
    r = _marca(env)
    assert r.returncode == 0
    assert "el arranque sigue" in r.stderr
    assert Path(env["BB_ETAPA_KMSG"]).read_text(encoding="utf-8").startswith("<3>bb-etapa basic ")


def test_marca_crea_var_lib_blackbox_si_falta_pero_no_mas_arriba(tmp_path: Path):
    env = _raiz_marca(tmp_path) | {"BB_ETAPA_DIR": str(tmp_path / "nuevo" / "arranque")}
    assert _marca(env).returncode == 0 and [f["etapa"] for f in _lineas(env)] == ["basic"]
    env["BB_ETAPA_DIR"] = str(tmp_path / "no" / "existe" / "arranque")
    r = _marca(env)
    assert r.returncode == 0 and "no pude crear" in r.stderr and not (tmp_path / "no").exists()


def test_marca_sin_kmsg_escribe_el_archivo_y_sale_0(tmp_path: Path):
    env = _raiz_marca(tmp_path) | {"BB_ETAPA_KMSG": "/dev/full"}
    r = _marca(env)
    assert r.returncode == 0 and "no pude escribir en /dev/full" in r.stderr
    assert [f["etapa"] for f in _lineas(env)] == ["basic"]


@pytest.mark.parametrize("cual", ["directorio", "archivo"])
def test_control_negativo_un_symlink_no_se_sigue(tmp_path: Path, cual: str):
    env = _raiz_marca(tmp_path)
    ajeno = tmp_path / "ajeno"
    ajeno.mkdir()
    d = Path(env["BB_ETAPA_DIR"])
    if cual == "directorio":
        d.symlink_to(ajeno)
    else:
        d.mkdir()
        (d / "etapas.jsonl").symlink_to(ajeno / "victima")
    r = _marca(env)
    assert r.returncode == 0 and "el arranque sigue" in r.stderr
    assert list(ajeno.iterdir()) == []


def test_control_negativo_un_directorio_escribible_por_otros_se_rechaza(tmp_path: Path):
    env = _raiz_marca(tmp_path)
    d = Path(env["BB_ETAPA_DIR"])
    d.mkdir()
    d.chmod(0o777)
    assert _marca(env).returncode == 0
    assert not (d / "etapas.jsonl").exists()


@pytest.mark.parametrize("etapa", ["", "Basic", "../x", "a b", "a" * 42, "-x"])
def test_marca_con_nombre_invalido_sale_2_sin_escribir(tmp_path: Path, etapa: str):
    env = _raiz_marca(tmp_path)
    assert _marca(env, etapa).returncode == 2
    assert not Path(env["BB_ETAPA_DIR"]).exists() and not Path(env["BB_ETAPA_KMSG"]).exists()


def test_marca_sin_boot_id_ni_uptime_sigue_dando_json_valido(tmp_path: Path):
    env = _raiz_marca(tmp_path) | {"BB_ETAPA_BOOT_ID": str(tmp_path / "no"), "BB_ETAPA_UPTIME": str(tmp_path / "no")}
    assert _marca(env).returncode == 0
    (fila,) = _lineas(env)
    assert fila["boot_id"] == "desconocido" and fila["monotonic"] is None


def test_marca_rota_por_tamano_y_el_lector_ve_las_dos_generaciones(tmp_path: Path):
    env = _raiz_marca(tmp_path) | {"BB_ETAPA_MAX_BYTES": "300"}
    etapas = ["local-fs", "basic", "multi-user", "gdm", "graphical"]  # ~116 bytes cada una: rota en la cuarta
    for e in etapas:
        assert _marca(env, e).returncode == 0
    d = Path(env["BB_ETAPA_DIR"])
    assert (d / "etapas.jsonl.1").stat().st_size >= 300 > (d / "etapas.jsonl").stat().st_size
    marcas, descartadas = ea.leer_marcas(d / "etapas.jsonl")
    assert [m["etapa"] for m in marcas] == etapas and descartadas == 0


def test_marca_que_pierde_la_carrera_del_mkdir_igual_anota(tmp_path: Path):
    """Otra etapa crea el directorio entre la comprobacion y el mkdir de esta: un mkdir que lo crea y falla lo emula.

    Determinista a proposito: la carrera real (el test de abajo) se atrapo en 5 de 10 corridas con el arreglo quitado.
    """
    env = _raiz_marca(tmp_path)
    falso = tmp_path / "bin"
    falso.mkdir()
    (falso / "mkdir").write_text('#!/bin/sh\n/bin/mkdir "$@"\necho "mkdir: File exists" >&2\nexit 1\n', encoding="utf-8")
    (falso / "mkdir").chmod(0o755)
    env["PATH"] = f"{falso}:{env['PATH']}"
    assert _marca(env).returncode == 0 and [f["etapa"] for f in _lineas(env)] == ["basic"]


def test_marcas_concurrentes_no_se_pisan(tmp_path: Path):
    env = _raiz_marca(tmp_path)
    procs = [subprocess.Popen(["bash", str(MARCA), f"e{i}"], env=env, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL) for i in range(16)]
    assert [p.wait(timeout=30) for p in procs] == [0] * 16
    assert sorted(f["etapa"] for f in _lineas(env)) == sorted(f"e{i}" for i in range(16))


# --- las unidades ----------------------------------------------------------------------------

def _ini(ruta: Path) -> configparser.ConfigParser:
    c = configparser.ConfigParser(strict=False, interpolation=None)
    c.optionxform = str  # pyright: ignore[reportAttributeAccessIssue]  # systemd distingue mayusculas
    c.read_string(ruta.read_text(encoding="utf-8"))
    return c


def test_la_plantilla_corre_sin_dependencias_por_defecto_y_con_tope():
    c = _ini(UNIDADES / "bb-etapa@.service")
    assert c["Unit"]["DefaultDependencies"] == "no" and c["Unit"]["After"] == "local-fs.target"
    assert c["Service"]["Type"] == "oneshot" and c["Service"]["RemainAfterExit"] == "yes"
    assert c["Service"]["ExecStart"] == "/usr/local/sbin/bb-etapa-marca %i"
    assert c["Service"]["TimeoutStartSec"] == "30"
    assert not c.has_section("Install")  # nada se habilita: lo piden los drop-ins


@pytest.mark.parametrize("unidad,etapas", DISPARADORES.items())
def test_cada_disparador_pide_su_etapa_y_se_ordena_antes(unidad: str, etapas: list[str]):
    c = _ini(UNIDADES / f"{unidad}.d" / "bb-etapa.conf")
    assert c["Unit"]["Wants"].split() == [f"bb-etapa@{e}.service" for e in etapas]
    assert c["Unit"]["Before"] == f"bb-etapa@{etapas[0]}.service"


def test_gpu_lista_exige_una_gpu_listada_con_timeout_y_reintenta_acotado():
    c = _ini(UNIDADES / "bb-etapa@gpu-lista.service.d" / "bb-etapa.conf")
    assert c["Service"]["ExecStartPre"] == """/bin/sh -c 'timeout 10 nvidia-smi -L | grep -q "^GPU "'"""
    assert c["Service"]["Restart"] == "on-failure" and int(c["Unit"]["StartLimitBurst"]) == 20


def test_toda_etapa_de_la_cadena_y_de_las_ramas_tiene_disparador():
    pedidas = {ea.canonica(e.replace("%i", "1000")) for es in DISPARADORES.values() for e in es}
    assert pedidas == set(ea.CADENA) | set(ea.RAMAS)
    drop = sorted(str(p.relative_to(UNIDADES)) for p in UNIDADES.rglob("*.conf"))
    assert drop == sorted([f"{u}.d/bb-etapa.conf" for u in DISPARADORES] + ["bb-etapa@gpu-lista.service.d/bb-etapa.conf"])


_ANALYZE = shutil.which("systemd-analyze")
_NO_EJECUTABLE = re.compile(r"^bb-etapa@[a-z0-9-]+\.service: Command /usr/local/sbin/bb-etapa-marca is not executable")


def _verify(dir_unidades: Path, *unidades: str, todo: bool = False) -> list[str]:
    """Lineas de `systemd-analyze verify` que hablan de lo nuestro, salvo la del binario aun no instalado.

    verify sale 0 hasta con unidades rotas (tests/test_atom_slice.py), asi que el criterio es la salida. `todo`
    devuelve todas: un ciclo se anuncia desde la unidad en que systemd lo encuentra, que cambia de corrida en corrida.
    """
    (dir_unidades / "gdm.service").write_text("[Unit]\nDescription=stub\n[Service]\nExecStart=/bin/true\n", encoding="utf-8")
    env = {**os.environ, "SYSTEMD_UNIT_PATH": f"{dir_unidades}:"}  # ':' final: despues, las rutas de siempre
    r = subprocess.run([str(_ANALYZE), "verify", *unidades], env=env, capture_output=True, text=True, timeout=60, check=False)
    lineas = (r.stdout + r.stderr).splitlines()
    return lineas if todo else [ln for ln in lineas if "bb-etapa" in ln and not _NO_EJECUTABLE.match(ln)]


def _ciclo_con(lineas: list[str], unidad: str) -> bool:
    return any("ordering cycle" in ln for ln in lineas) and any(unidad in ln for ln in lineas)


_TODAS = ["graphical.target", "network-online.target", "gdm.service", "user@1000.service", "user@120.service",
          *(f"bb-etapa@{e}.service" for e in ("local-fs", "basic", "gpu-lista", "multi-user", "gdm", "sesion-1000"))]


@pytest.mark.skipif(_ANALYZE is None, reason="systemd-analyze no disponible: queda el parser ini de arriba")
def test_systemd_analyze_verify_no_dice_nada_de_las_unidades(tmp_path: Path):
    d = tmp_path / "u"
    shutil.copytree(UNIDADES, d)
    assert _verify(d, *_TODAS) == []


@pytest.mark.skipif(_ANALYZE is None, reason="systemd-analyze no disponible")
def test_control_negativo_verify_caza_una_clave_mal_escrita_y_un_ciclo(tmp_path: Path):
    d = tmp_path / "u"
    shutil.copytree(UNIDADES, d)
    conf = d / "basic.target.d" / "bb-etapa.conf"
    conf.write_text(conf.read_text(encoding="utf-8").replace("Wants=", "Wnats="), encoding="utf-8")
    assert any("Unknown key name 'Wnats'" in ln for ln in _verify(d, "basic.target"))
    shutil.copy(UNIDADES / "basic.target.d" / "bb-etapa.conf", conf)
    (d / "bb-etapa@multi-user.service.d").mkdir()
    (d / "bb-etapa@multi-user.service.d" / "ciclo.conf").write_text("[Unit]\nBefore=multi-user.target\n", encoding="utf-8")
    assert _ciclo_con(_verify(d, "multi-user.target", todo=True), "bb-etapa@multi-user.service")
    # el %i del drop-in de user@ resuelve al uid: user@1000 pide sesion-1000 (el ciclo lo delata) y user@1001 no
    (d / "bb-etapa@sesion-1000.service.d").mkdir()
    (d / "bb-etapa@sesion-1000.service.d" / "ciclo.conf").write_text("[Unit]\nBefore=user@1000.service\n", encoding="utf-8")
    assert _ciclo_con(_verify(d, "user@1000.service", todo=True), "bb-etapa@sesion-1000.service")
    assert _verify(d, "user@1001.service") == []


def test_el_leeme_instala_cada_drop_in_y_el_sha256_es_el_del_script():
    texto = LEEME.read_text(encoding="utf-8")
    for u in [*DISPARADORES, "bb-etapa@gpu-lista.service"]:
        assert u in texto, u
    assert hashlib.sha256(MARCA.read_bytes()).hexdigest() in texto, "LEEME-etapas.md tiene un sha256 viejo"
    codigo = "\n".join(re.findall(r"```sh\n(.*?)```", texto, re.S))
    assert "systemctl daemon-reload" in codigo and "rm -f /etc/systemd/system/bb-etapa@.service" in codigo
    assert not re.search(r"grub|initramfs|kernelstub|/proc/cmdline|systemctl enable", codigo, re.I)


# --- tools/etapas_arranque.py -----------------------------------------------------------------

def _etapas(tmp_path: Path, arranques: list[tuple[str, list[str]]]) -> Path:
    f = tmp_path / "etapas.jsonl"
    filas = [{"boot_id": b, "etapa": e, "monotonic": float(i), "realtime": 1.8e9 + i}
             for b, es in arranques for i, e in enumerate(es, 1)]
    f.write_text("".join(json.dumps(x) + "\n" for x in filas), encoding="utf-8")
    return f


def _raiz_sys(tmp_path: Path, boot: str = BOOT) -> Path:
    r = tmp_path / "raiz"
    (r / "proc/sys/kernel/random").mkdir(parents=True)
    (r / "proc/sys/kernel/random/boot_id").write_text(boot + "\n", encoding="utf-8")
    (r / "proc/cmdline").write_text("BOOT_IMAGE=/vmlinuz-x ro console=ttyS0,921600\n", encoding="utf-8")
    wd = r / "sys/class/watchdog/watchdog0"
    wd.mkdir(parents=True)
    for a, v in {"identity": "SBSA Generic Watchdog", "state": "active", "timeout": "60", "bootstatus": "32"}.items():
        (wd / a).write_text(v + "\n", encoding="utf-8")
    (r / "sys/module/nvidia").mkdir(parents=True)
    (r / "sys/module/nvidia/srcversion").write_text("73BC7E52961D5FE2E16A551\n", encoding="utf-8")
    (r / "sys/fs/cgroup").mkdir(parents=True)
    (r / "sys/fs/cgroup/dmem.capacity").write_text("", encoding="utf-8")
    return r


def _modinfo_falso(args: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
    valores = {"filename": "/lib/modules/k/updates/nvidia.ko", "srcversion": "73BC7E52961D5FE2E16A551", "signer": "bb MOK"}
    return subprocess.CompletedProcess(args, 0, valores[args[2]] + "\n", "")


SANO = ["local-fs", "basic", "gpu-lista", "network-online", "multi-user", "gdm", "sesion-120", "graphical", "sesion-1000"]
AHORA = datetime(2026, 11, 1, tzinfo=timezone.utc)


def _fila(tmp_path: Path, anterior: list[str]) -> dict[str, Any]:
    marcas, desc = ea.leer_marcas(_etapas(tmp_path, [(OTRO, anterior), (BOOT, SANO)]))
    f = ea.fila(marcas, desc, BOOT, _raiz_sys(tmp_path), _modinfo_falso, AHORA)
    assert f is not None
    return f


def test_un_arranque_sin_multi_user_deja_la_ultima_etapa_en_basic(tmp_path: Path):
    f = _fila(tmp_path, ["local-fs", "basic", "network-online", "gpu-lista", "guardia-dmem-retrocede"])
    assert (f["boot_id_anterior"], f["ultima_etapa_anterior"]) == (OTRO, "basic")
    assert f["anterior"]["faltan"] == ["multi-user", "gdm", "graphical", "sesion-usuario"]
    assert f["anterior"]["ramas"] == {"network-online": 3.0, "gpu-lista": 4.0}
    assert f["anterior"]["otras"] == ["guardia-dmem-retrocede"]


def test_control_negativo_el_que_si_llega_a_multi_user_no_se_queda_en_basic(tmp_path: Path):
    assert _fila(tmp_path, ["local-fs", "basic", "multi-user"])["ultima_etapa_anterior"] == "multi-user"


def test_el_saludo_de_gdm_no_cuenta_como_sesion_de_usuario(tmp_path: Path):
    f = _fila(tmp_path, ["local-fs", "basic", "multi-user", "gdm", "graphical", "sesion-120"])
    assert f["ultima_etapa_anterior"] == "graphical" and f["anterior"]["sesiones_sistema"] == ["sesion-120"]
    (tmp_path / "b").mkdir()
    assert _fila(tmp_path / "b", SANO)["ultima_etapa_anterior"] == "sesion-usuario"


def test_el_contexto_lee_watchdog_cmdline_nvidia_y_dmem(tmp_path: Path):
    c = _fila(tmp_path, ["local-fs"])["contexto"]
    assert c["bootstatus"] == {"watchdog0": "32"} and c["watchdog"]["watchdog0"]["identity"] == "SBSA Generic Watchdog"
    assert c["watchdog"]["watchdog0"]["nowayout"].startswith("NOT_COLLECTED: ")
    assert c["cmdline"].endswith("console=ttyS0,921600") and c["dmem_capacity"] == ""
    assert c["nvidia"]["srcversion_cargado"] == "73BC7E52961D5FE2E16A551"
    assert c["nvidia"]["firmante_archivo"] == "bb MOK" and c["nvidia"]["version_cargado"].startswith("NOT_COLLECTED")


def test_el_contexto_sin_sysfs_ni_modinfo_declara_not_collected(tmp_path: Path):
    def roto(args: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(args, 10)
    c = ea.contexto(tmp_path / "vacia", roto)
    assert all(str(v).startswith("NOT_COLLECTED: ") for v in (c["cmdline"], c["bootstatus"], c["watchdog"], c["dmem_capacity"]))
    assert c["nvidia"]["firmante_archivo"] == "NOT_COLLECTED: modinfo -F signer nvidia no corrio (TimeoutExpired)"
    sin_salida = ea._modinfo(lambda a, **_: subprocess.CompletedProcess(a, 1, "", ""), "signer")
    assert sin_salida == "NOT_COLLECTED: modinfo -F signer nvidia rc=1 sin salida"


def test_un_arranque_actual_que_no_es_sano_no_anota_nada(tmp_path: Path):
    marcas, desc = ea.leer_marcas(_etapas(tmp_path, [(OTRO, ["local-fs"]), (BOOT, ["local-fs", "basic"])]))
    assert ea.fila(marcas, desc, BOOT, _raiz_sys(tmp_path), _modinfo_falso, AHORA) is None


def test_sin_arranque_anterior_lo_declara(tmp_path: Path):
    marcas, desc = ea.leer_marcas(_etapas(tmp_path, [(BOOT, SANO)]))
    f = ea.fila(marcas, desc, BOOT, _raiz_sys(tmp_path), _modinfo_falso, AHORA)
    assert f is not None and f["boot_id_anterior"] == f["ultima_etapa_anterior"] == f["anterior"]
    assert f["anterior"] == "NOT_COLLECTED: sin marcas de un arranque anterior en etapas.jsonl"


def test_el_anterior_que_no_llego_a_ninguna_etapa_de_la_cadena(tmp_path: Path):
    assert _fila(tmp_path, ["gpu-lista"])["ultima_etapa_anterior"].startswith("NOT_COLLECTED: el anterior no llego")


def test_lineas_rotas_se_cuentan_y_la_generacion_vieja_va_primero(tmp_path: Path):
    f = _etapas(tmp_path, [(BOOT, ["basic"])])
    (tmp_path / "etapas.jsonl.1").write_text(json.dumps({"boot_id": OTRO, "etapa": "local-fs", "monotonic": 1,
                                                         "realtime": None}) + "\n{no json\n[1]\n"
                                             + json.dumps({"boot_id": OTRO, "etapa": "x", "monotonic": True,
                                                           "realtime": 1}) + "\n\n", encoding="utf-8")
    marcas, descartadas = ea.leer_marcas(f)
    assert [(m["boot_id"], m["etapa"]) for m in marcas] == [(OTRO, "local-fs"), (BOOT, "basic")] and descartadas == 3


def _main(tmp_path: Path, *extra: str) -> tuple[int, Path]:
    salida = tmp_path / "datos" / "etapas_arranque.jsonl"
    argv = ["--etapas", str(tmp_path / "etapas.jsonl"), "--out", str(salida), "--raiz", str(tmp_path / "raiz"), *extra]
    return ea.main(argv, correr=_modinfo_falso), salida


def test_main_anota_una_sola_vez_por_arranque(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _etapas(tmp_path, [(OTRO, ["local-fs", "basic"]), (BOOT, SANO)])
    _raiz_sys(tmp_path)
    rc, salida = _main(tmp_path)
    assert rc == 0 and "llego a basic" in capsys.readouterr().out
    assert _main(tmp_path) == (0, salida) and "ya esta anotado" in capsys.readouterr().out
    (fila,) = [json.loads(x) for x in salida.read_text(encoding="utf-8").splitlines()]
    assert fila["esquema"] == 1 and fila["boot_id_actual"] == BOOT and fila["etapas_actual"] == SANO


def test_main_imprime_sin_escribir_y_los_rc_de_no_sano_y_could_not_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _etapas(tmp_path, [(BOOT, SANO)])
    _raiz_sys(tmp_path)
    rc, salida = _main(tmp_path, "--imprime")
    assert rc == 0 and json.loads(capsys.readouterr().out)["boot_id_actual"] == BOOT and not salida.exists()
    _etapas(tmp_path, [(BOOT, ["basic"])])
    assert _main(tmp_path)[0] == 1 and not salida.exists()
    (tmp_path / "etapas.jsonl").unlink()
    assert _main(tmp_path)[0] == 2 and "COULD_NOT_RUN" in capsys.readouterr().err
    (tmp_path / "raiz/proc/sys/kernel/random/boot_id").unlink()
    assert _main(tmp_path)[0] == 2


def test_ya_anotado_tolera_lineas_ajenas(tmp_path: Path):
    s = tmp_path / "s.jsonl"
    s.write_text("basura\n[1]\n" + json.dumps({"boot_id_actual": BOOT}) + "\n", encoding="utf-8")
    assert ea.ya_anotado(s, BOOT) and not ea.ya_anotado(s, OTRO) and not ea.ya_anotado(tmp_path / "no", BOOT)


def test_salida_por_defecto_sigue_blackbox_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    assert ea.salida_por_defecto() == tmp_path / "etapas_arranque.jsonl"


def test_de_la_marca_al_resumen_sin_intermediarios(tmp_path: Path):
    """La linea que escribe etapa-marca.sh es la que lee etapas_arranque.py (mismo esquema, sin adaptador)."""
    env = _raiz_marca(tmp_path)
    for e in ["local-fs", "basic", "gpu-lista"]:
        assert _marca(env, e).returncode == 0
    marcas, desc = ea.leer_marcas(Path(env["BB_ETAPA_DIR"]) / "etapas.jsonl")
    assert desc == 0 and ea.resumir(BOOT, marcas)["ultima_etapa"] == "basic"


def _bloque(nombre: str, tmp: Path) -> str:
    """El bloque ```sh del LEEME que empieza con `# <nombre>`, apuntado a una raiz falsa y sin sudo ni chown."""
    (cuerpo,) = [b for b in re.findall(r"```sh\n(.*?)```", LEEME.read_text(encoding="utf-8"), re.S)
                 if b.startswith(f"# {nombre}\n")]
    for a, b in {"sudo ": "", "-o root -g root ": "", "cd ~/projects/blackbox": f"cd {RAIZ}",
                 "/etc/systemd/system": str(tmp / "etc"), "/usr/local/sbin": str(tmp / "sbin")}.items():
        cuerpo = cuerpo.replace(a, b)
    return "set -eu\n" + cuerpo


def test_los_comandos_del_leeme_instalan_y_retroceden_sin_dejar_restos(tmp_path: Path):
    (tmp_path / "sbin").mkdir()
    ajeno = tmp_path / "etc" / "user@.service.d" / "99-blackbox-escritorio.conf"
    ajeno.parent.mkdir(parents=True)
    ajeno.write_text("[Slice]\n", encoding="utf-8")
    r = subprocess.run(["bash", "-c", _bloque("instala", tmp_path)], capture_output=True, text=True, timeout=30, check=False)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "sbin" / "bb-etapa-marca").read_bytes() == MARCA.read_bytes()
    assert oct((tmp_path / "sbin" / "bb-etapa-marca").stat().st_mode & 0o777) == "0o755"
    instalados = sorted(str(p.relative_to(tmp_path / "etc")) for p in (tmp_path / "etc").rglob("bb-etapa*") if p.is_file())
    assert instalados == sorted(str(p.relative_to(UNIDADES)) for p in UNIDADES.rglob("bb-etapa*") if p.is_file())
    r = subprocess.run(["bash", "-c", _bloque("retrocede", tmp_path)], capture_output=True, text=True, timeout=30, check=False)
    assert r.returncode == 0, r.stderr
    assert [p for p in (tmp_path / "etc").rglob("*")] == [ajeno.parent, ajeno] and not list((tmp_path / "sbin").iterdir())


def test_control_negativo_un_script_cambiado_tras_la_revision_no_se_instala(tmp_path: Path):
    (tmp_path / "sbin").mkdir()
    script = _bloque("instala", tmp_path).replace('"$d/etapa-marca.sh"', str(tmp_path / "otro.sh"))
    (tmp_path / "otro.sh").write_text(MARCA.read_text(encoding="utf-8") + "# cambio\n", encoding="utf-8")
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30, check=False)
    assert r.returncode != 0 and "FAILED" in r.stdout + r.stderr
    assert not (tmp_path / "sbin" / "bb-etapa-marca").exists() and not (tmp_path / "etc").exists()
