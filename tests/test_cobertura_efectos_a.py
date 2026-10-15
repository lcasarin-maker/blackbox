"""Cobertura de efectos (parte A): gpuoom_bb, bb_oci_runtime, limita_cuda, dmem_monitor,
vigilante_memavail e interruptores.

Cada prueba corre el codigo REAL contra archivos reales en `tmp_path` y afirma un efecto observable (fila
escrita, codigo de salida, texto impreso). Lo externo (nvidia-smi, modinfo, libcuda) se sustituye por un
ejecutable o biblioteca minima puesta en un PATH/LD_LIBRARY_PATH propio: nunca se lanza el binario del
sistema. Los bucles `while True` no se ejecutan; cuando una prueba los cruza, el `sleep` de su iteracion
lanza una excepcion que los corta (solo en el hilo principal).
"""

from __future__ import annotations

import functools
import json
import os
import runpy
import shutil
import subprocess
import sys
import threading
import warnings
from pathlib import Path
from time import sleep as _dormir_real
from typing import Any, Callable

import pytest

from tools import bb_oci_runtime as oci
from tools import dmem_monitor as dm
from tools import gpuoom_bb as g
from tools import interruptores, limita_cuda as lc
from tools import vigilante_memavail as vm

KIB = 1024
GIB = 1024**3


class _Fin(Exception):
    """Corta un `while True` desde el sleep de su iteracion."""


def _corta_en(monkeypatch: pytest.MonkeyPatch, modulo: Any, iteraciones: int) -> list[float]:
    """Sustituye el sleep del modulo: tras `iteraciones` pausas lanza _Fin (hilo principal)."""
    pausas: list[float] = []

    def pausa(segundos: float) -> None:
        if threading.current_thread() is not threading.main_thread():
            _dormir_real(segundos)  # blocking-sleep: los hilos que no son el principal (muestreador de GPU) conservan su pausa real; el principal levanta _Fin -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01  # sunset-reviewed: 4.1 -- re-revisado 2026-10-15 contra 4.0 (`git log -L` c4977a8b..HEAD sobre la linea +-6: 0 commits, linea identica a la revision 4.0 c4977a8b; sigue en la rama de hilos no principales del sleep sustituto _corta_en); re-revisado 2026-10-15 contra 3.9 (`git log -L`: ultimo cambio de la linea anterior a la revision 3.9, 9aec733f); re-revisado 2026-10-13 contra 3.5: `git blame` de la linea 48 (7280a6a4) es anterior al bump 3.5.0 (b99560e8), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.4: `git blame` de la linea 48 (095c3a35) es anterior al bump 3.4.1 (eb89c383), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.3: `git blame` de la linea 48 (b008b6ee) es anterior al bump 3.3.0 (3512a16a), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.2: `git blame` de la linea 48 (804713d5) es anterior al bump 3.2.0 (e8e5aa8d), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.1: `git blame` de la linea 48 (93850773) es anterior al bump 3.1.0 (7a5bd48b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 3.0: `git blame` de la linea 48 (4df311d3) es anterior al bump 2.9.1 (ab63e2b), la linea no cambio desde su revision anterior; la razon sigue valiendo: revisado 2026-10-12: doble de prueba de `time.sleep`, acotado por el segundo parametro de cada prueba ; re-revisado 2026-10-13 contra 3.1: la linea no cambio desde 20256295 (git blame de esta linea)
            return
        pausas.append(segundos)
        if len(pausas) >= iteraciones:
            raise _Fin()

    monkeypatch.setattr(modulo.time, "sleep", pausa)
    return pausas


def _bin(directorio: Path, nombre: str, cuerpo: str) -> Path:
    """Un ejecutable de shell minimo (solo builtins) en `directorio`."""
    directorio.mkdir(parents=True, exist_ok=True)
    f = directorio / nombre
    f.write_text("#!/bin/sh\n" + cuerpo + "\n", encoding="utf-8")
    f.chmod(0o755)
    return f


def _solo_path(monkeypatch: pytest.MonkeyPatch, directorio: Path) -> None:
    directorio.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PATH", str(directorio))


# ============================================================ gpuoom_bb


def test_gpuoom_nvidia_smi_real_del_path_se_parsea_y_la_copia_lo_devuelve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _bin(tmp_path / "bin", "nvidia-smi", 'echo "7, 2048"')
    _solo_path(monkeypatch, tmp_path / "bin")
    m = g.MuestreadorGpu()
    m.muestrea(1.0)
    assert m.lee(2.0) == ({7: 2048 * KIB}, "")


def test_gpuoom_sin_nvidia_smi_no_hay_copia_y_se_declara(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Control negativo: el instrumento caido no inventa una copia, dice NOT_COLLECTED."""
    _solo_path(monkeypatch, tmp_path / "vacio")
    m = g.MuestreadorGpu()
    m.muestrea(1.0)
    mapa, nota = m.lee(2.0)
    assert mapa == {} and nota.startswith("NOT_COLLECTED")


def test_gpuoom_nvidia_smi_que_expira_tampoco_deja_copia() -> None:
    def expira() -> str:
        raise subprocess.TimeoutExpired("nvidia-smi", 20)

    m = g.MuestreadorGpu(ejecuta=expira)
    m.muestrea(1.0)
    assert m.lee(2.0)[1].startswith("NOT_COLLECTED")


def test_gpuoom_paso_en_calma_y_pendiente_no_dispara_ni_registra(tmp_path: Path) -> None:
    gpu = g.MuestreadorGpu(ejecuta=lambda: "")
    filas: Callable[[], tuple[list[tuple[int, str, int, int, int, int]], int]] = lambda: ([], 0)
    assert g.paso("observar", 50.0, 0.0, 1.0, None, filas, gpu, tmp_path) == (None, None)
    assert g.paso("observar", 6.0, 20.0, 100.0, None, filas, gpu, tmp_path) == (100.0, None)
    assert not list(tmp_path.iterdir())


def test_gpuoom_principal_cruza_una_vuelta_y_se_corta_en_el_sleep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    arrancado: list[bool] = []
    monkeypatch.setattr(g.MuestreadorGpu, "arranca", lambda self, intervalo=0.0: arrancado.append(True))
    pausas = _corta_en(monkeypatch, g, 2)
    with pytest.raises(_Fin):
        g.principal()
    assert arrancado == [True] and pausas == [1, 1]  # dos vueltas completas; modo `off` (sin interruptores.json): nada registrado
    assert not (tmp_path / "interruptores").exists()


def test_gpuoom_lee_meminfo_y_psi_reales_son_numeros() -> None:
    total = g._meminfo_kib("MemTotal")
    assert total is not None and total > 0
    assert g._meminfo_kib("ClaveQueNoExiste") is None
    psi = g._psi_some()
    assert psi is not None and psi >= 0.0


def test_gpuoom_lee_psi_y_meminfo_de_archivos_propios(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    f = tmp_path / "psi"
    f.write_text("some avg10=12.50 avg60=1.00 avg300=0.00 total=1\nfull avg10=3.00 avg60=0 avg300=0 total=1\n", encoding="utf-8")
    monkeypatch.setattr(g, "Path", lambda _ruta: f)
    assert g._psi_some() == 12.5
    f.write_text("sin la linea esperada\n", encoding="utf-8")
    assert g._psi_some() is None
    assert g._meminfo_kib("MemAvailable") is None


def test_gpuoom_sin_archivo_de_proc_no_inventa_cero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ausente = tmp_path / "no-existe"
    monkeypatch.setattr(g, "Path", lambda _ruta: ausente)
    assert g._meminfo_kib("MemAvailable") is None
    assert g._psi_some() is None


# ============================================================ bb_oci_runtime


SPEC_MIN = {"ociVersion": "1.2.1", "process": {"args": ["sh"], "env": ["PATH=/bin"]}, "linux": {"namespaces": [{"type": "pid"}]}}


def _bundle(tmp_path: Path, nombre: str, spec: object) -> Path:
    b = tmp_path / nombre
    b.mkdir()
    (b / "config.json").write_text(json.dumps(spec), encoding="utf-8")
    return b


def _filas(tmp_path: Path) -> list[dict[str, Any]]:
    f = tmp_path / "oci_runtime.jsonl"
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()]


def test_oci_suelo_de_entorno_valido_ilegible_y_ausente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BB_OCI_GPU_FLOOR_GIB", "20")
    assert oci._suelo() == (20.0, "BB_OCI_GPU_FLOOR_GIB")
    monkeypatch.setenv("BB_OCI_GPU_FLOOR_GIB", "x")
    valor, origen = oci._suelo()
    assert valor == oci.SUELO_GPU_GIB and "ilegible" in origen
    monkeypatch.delenv("BB_OCI_GPU_FLOOR_GIB")
    assert oci._suelo() == (oci.SUELO_GPU_GIB, oci.SUELO_GPU_ORIGEN)


def test_oci_escribe_spec_atomico_sin_dejar_temporal(tmp_path: Path) -> None:
    ruta = tmp_path / "config.json"
    ruta.write_text("{}", encoding="utf-8")
    oci._escribe_spec(ruta, {"a": 1})
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"a": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["config.json"]


def test_oci_spec_ilegible_es_NO_ACTUAR_y_no_toca_el_bundle(tmp_path: Path) -> None:
    vacio = tmp_path / "sin_config"
    vacio.mkdir()
    spec, error = oci._leer_spec(vacio)
    assert spec is None and error is not None and error.startswith("NOT_COLLECTED")
    fila = oci.gobernar_create(["--bundle", str(vacio), "c1"], None, (50.1, "x"))
    assert fila["decision"] == "NO_ACTUAR" and fila["motivo"].startswith("NOT_COLLECTED")
    assert list(vacio.iterdir()) == []


def test_oci_create_sin_registro_corrige_el_config_y_declara_la_nota(tmp_path: Path) -> None:
    b = _bundle(tmp_path, "b", SPEC_MIN)
    fila = oci.gobernar_create(["--bundle", str(b), "c1"], None, (50.1, "x"))
    assert fila["decision"] == "CORREGIR" and fila["registro_nota"].startswith("NOT_COLLECTED")
    reescrito = json.loads((b / "config.json").read_text(encoding="utf-8"))
    assert reescrito["linux"]["resources"]["memory"] == {"limit": 3 * GIB, "swap": 3 * GIB}


def test_oci_create_con_registro_suma_los_reclamos_previos(tmp_path: Path) -> None:
    spec = {**SPEC_MIN, "process": {"env": ["NVIDIA_VISIBLE_DEVICES=all"]}, "annotations": {oci.ANOTACION_GPU: "10"}}
    b = _bundle(tmp_path, "b", spec)
    previo = {"evento": "create", "contenedor": "otro", "decision": "ADMITIR", "gpu_gib": 36.0}
    with (tmp_path / "reg.jsonl").open("w+", encoding="utf-8") as reg:
        reg.write(json.dumps(previo) + "\n")
        fila = oci.gobernar_create(["--bundle", str(b), "nuevo"], reg, (50.1, "x"))
    assert fila["decision"] == "CORREGIR" and fila["reclamos_previos_gib"] == 36.0 and fila["registro_nota"] is None


def test_oci_registro_inservible_se_avisa_y_se_sigue_sin_historia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    estorbo = tmp_path / "es_archivo"
    estorbo.write_text("", encoding="utf-8")
    monkeypatch.setenv("BLACKBOX_DATA", str(estorbo))
    with oci.contextlib.ExitStack() as pila:
        assert oci._abrir_registro(pila) is None
    assert "registro no disponible" in capsys.readouterr().err


def test_oci_registro_utilizable_es_un_archivo_abierto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Control negativo del anterior: con un directorio de datos sano si hay registro."""
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path / "datos"))
    with oci.contextlib.ExitStack() as pila:
        registro = oci._abrir_registro(pila)
        assert registro is not None
        oci._anotar(registro, {"evento": "x", "decision": "NO_ACTUAR"})
    assert _filas(tmp_path / "datos")[0]["evento"] == "x"


def test_oci_anotar_sin_registro_o_de_solo_lectura_lo_dice_por_stderr(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    oci._anotar(None, {"evento": "create"})
    assert "no se pudo registrar la decision" in capsys.readouterr().err
    f = tmp_path / "ro.jsonl"
    f.write_text("", encoding="utf-8")
    with f.open("r", encoding="utf-8") as solo_lectura:
        oci._anotar(solo_lectura, {"evento": "create"})
    assert "no se pudo registrar la decision" in capsys.readouterr().err
    assert f.read_text(encoding="utf-8") == ""


def test_oci_gobernar_deja_pasar_otros_subcomandos_y_registra_delete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    assert oci.gobernar(["kill", "c1", "KILL"]) is None
    assert oci.gobernar(["--debug"]) is None
    assert not (tmp_path / "oci_runtime.jsonl").exists()
    assert oci.gobernar(["delete", "--force", "c1"]) is None
    assert oci.gobernar(["delete", "--force"]) is None
    filas = _filas(tmp_path)
    assert [f["contenedor"] for f in filas] == ["c1", None] and all(f["evento"] == "delete" for f in filas)


def test_oci_gobernar_create_admitido_devuelve_None_y_rechazado_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path / "datos"))
    monkeypatch.delenv("BB_OCI_GPU_FLOOR_GIB", raising=False)
    ok = _bundle(tmp_path, "ok", SPEC_MIN)
    assert oci.gobernar(["create", "--bundle", str(ok), "c1"]) is None
    gpu_sin_reclamo = _bundle(tmp_path, "gpu", {**SPEC_MIN, "process": {"env": ["NVIDIA_VISIBLE_DEVICES=all"]}})
    assert oci.gobernar(["create", "--bundle", str(gpu_sin_reclamo), "c2"]) == 3
    assert "RECHAZADO c2" in capsys.readouterr().err
    assert [f["decision"] for f in _filas(tmp_path / "datos")] == ["CORREGIR", "RECHAZAR"]


def test_oci_una_averia_propia_no_bloquea_y_queda_registrada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Un registro con bytes que no son UTF-8 hace fallar la lectura: el create pasa (NO_ACTUAR) y lo dice."""
    datos = tmp_path / "datos"
    datos.mkdir()
    (datos / "oci_runtime.jsonl").write_bytes(b"\xff\xfe\xfa\n")
    monkeypatch.setenv("BLACKBOX_DATA", str(datos))
    b = _bundle(tmp_path, "b", SPEC_MIN)
    assert oci.gobernar(["create", "--bundle", str(b), "c1"]) is None
    ultima = (datos / "oci_runtime.jsonl").read_bytes().splitlines()[-1]
    fila = json.loads(ultima)
    assert fila["decision"] == "NO_ACTUAR" and "averia del envoltorio UnicodeDecodeError" in fila["motivo"]


def test_oci_main_delega_al_runtime_real_con_el_argv_intacto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    monkeypatch.setenv("BB_OCI_REAL_RUNTIME", "runtime-falso")
    llamadas: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(oci.os, "execvp", lambda archivo, args: llamadas.append((archivo, list(args))))
    assert oci.main(["state", "c1"]) == 127  # execvp (sustituido) vuelve: solo los tests llegan aqui
    assert llamadas == [("runtime-falso", ["runtime-falso", "state", "c1"])]


def test_oci_main_con_averia_del_envoltorio_pasa_intacto_y_lo_avisa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    monkeypatch.setenv("BB_OCI_REAL_RUNTIME", "runtime-falso")
    llamadas: list[list[str]] = []
    monkeypatch.setattr(oci.os, "execvp", lambda archivo, args: llamadas.append(list(args)))
    argv_roto: Any = [7]  # un argumento que no es str rompe `subcomando` antes de cualquier decision
    assert oci.main(argv_roto) == 127
    assert "NOT_COLLECTED: averia del envoltorio AttributeError" in capsys.readouterr().err
    assert llamadas == [["runtime-falso", 7]]


def test_oci_main_rechazo_devuelve_3_y_no_ejecuta_nada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Control negativo: un rechazo por politica no llega a execvp."""
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path / "datos"))
    llamadas: list[str] = []
    monkeypatch.setattr(oci.os, "execvp", lambda archivo, args: llamadas.append(archivo))
    b = _bundle(tmp_path, "gpu", {**SPEC_MIN, "process": {"env": ["NVIDIA_VISIBLE_DEVICES=all"]}})
    assert oci.main(["create", "--bundle", str(b), "c1"]) == 3
    assert llamadas == []


# ============================================================ limita_cuda


C_CUDA_FALSO = """
#include <stddef.h>
int cuInit(unsigned f) { return 0; }
int cuDeviceGet(int *d, int o) { *d = 0; return 0; }
int cuDevicePrimaryCtxRetain(void **c, int d) { *c = (void *)1; return 0; }
int cuCtxSetCurrent(void *c) { return 0; }
int cuMemAlloc_v2(void **p, size_t n) { if (n > 1048576) return 2; *p = (void *)1; return 0; }
int cuMemFree_v2(void *p) { return 0; }
"""


def _compila(tmp_path: Path, nombre: str, *extra: str, fuente_c: str = C_CUDA_FALSO) -> Path:
    cc = shutil.which("gcc")
    assert cc is not None, "COULD_NOT_RUN: sin gcc no se puede construir la biblioteca de prueba"
    fuente = tmp_path / (nombre + ".c")
    fuente.write_text(fuente_c, encoding="utf-8")
    salida = tmp_path / nombre
    subprocess.run([cc, "-shared", "-fPIC", *extra, "-o", str(salida), str(fuente)], check=True, capture_output=True, timeout=60)
    return salida


def test_limita_exporta_cu_con_una_biblioteca_que_exporta_y_otra_que_no(tmp_path: Path) -> None:
    visible = _compila(tmp_path, "libvisible.so")
    oculta = _compila(tmp_path, "liboculta.so", "-fvisibility=hidden")
    assert lc.exporta_cu(visible) is True
    assert lc.exporta_cu(oculta) is False  # control negativo: una Release oculta los simbolos


def test_limita_exporta_cu_con_un_archivo_que_no_es_elf_o_sin_nm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    texto = tmp_path / "x.so"
    texto.write_text("no soy ELF", encoding="utf-8")
    assert lc.exporta_cu(texto) is False
    _solo_path(monkeypatch, tmp_path / "vacio")
    assert lc.exporta_cu(texto) is False


def test_limita_centinela_real_contra_una_libcuda_de_prueba(tmp_path: Path) -> None:
    """La centinela corre en un hijo con LD_LIBRARY_PATH apuntando a una libcuda.so.1 propia: sobre el
    tope devuelve CUDA_OOM (2); bajo el tope, 0. No toca la GPU."""
    (tmp_path / "lib").mkdir()
    cuda = _compila(tmp_path / "lib", "libcuda.so.1")
    entorno = {**os.environ, "LD_LIBRARY_PATH": str(cuda.parent)}
    assert lc.centinela_driver(64 << 20, entorno) == lc.CUDA_OOM
    assert lc.centinela_driver(1024, entorno) == 0


def test_limita_centinela_que_no_se_pudo_medir_es_menos_uno(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Una libcuda de prueba cuyo cuInit falla (el hijo sale 90): -1, sin tocar la GPU real."""
    (tmp_path / "lib").mkdir()
    cuda = _compila(tmp_path / "lib", "libcuda.so.1", fuente_c=C_CUDA_FALSO.replace("int cuInit(unsigned f) { return 0; }", "int cuInit(unsigned f) { return 1; }"))
    assert lc.centinela_driver(1 << 20, {**os.environ, "LD_LIBRARY_PATH": str(cuda.parent)}) == -1
    monkeypatch.setattr(lc.sys, "executable", str(tmp_path / "sin-interprete"))
    assert lc.centinela_driver(1 << 20, dict(os.environ)) == -1  # el hijo ni arranca: no hay GPU de por medio


def test_limita_main_como_script_sin_comando_sale_con_2(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["limita", "--lib", "/x/libvgpu.so"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # runpy avisa: el modulo ya estaba importado
        with pytest.raises(SystemExit) as salida:
            runpy.run_module("tools.limita_cuda", run_name="__main__")
    assert salida.value.code == 2
    assert "falta el comando" in capsys.readouterr().err


# ============================================================ dmem_monitor


def _modulos(tmp_path: Path) -> tuple[Path, Path, Path]:
    base = tmp_path / "modulos"
    (base / "kernel/nvidia-580-open").mkdir(parents=True)
    (base / "updates").mkdir()
    (base / "kernel/nvidia-580-open/nvidia.ko").write_text("stock", encoding="utf-8")
    (base / "updates/nvidia.ko").write_text("parche", encoding="utf-8")
    sysmod = tmp_path / "sys_nvidia"
    sysmod.mkdir()
    (sysmod / "version").write_text("580.178.04\n", encoding="utf-8")
    (sysmod / "srcversion").write_text("AAA\n", encoding="utf-8")
    cap = tmp_path / "dmem.capacity"
    cap.write_text("region 1\n", encoding="utf-8")
    return base, sysmod, cap


MODINFO_FALSO = (
    'case "$2" in\n'
    '  version) case "$3" in *updates*) echo "$MI_PARCHE";; *) echo "$MI_STOCK";; esac;;\n'
    '  vermagic) echo "$MI_VERMAGIC";;\n'
    '  srcversion) echo AAA;;\n'
    'esac'
)


def _prepara_dmem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, parche: str, stock: str) -> None:
    base, sysmod, cap = _modulos(tmp_path)
    _bin(tmp_path / "bin", "modinfo", MODINFO_FALSO)
    _solo_path(monkeypatch, tmp_path / "bin")
    monkeypatch.setenv("MI_PARCHE", parche)
    monkeypatch.setenv("MI_STOCK", stock)
    monkeypatch.setenv("MI_VERMAGIC", os.uname().release + " SMP preempt")
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path / "datos"))
    monkeypatch.setattr(dm, "lee_estado", functools.partial(dm.lee_estado, base, sysmod, cap))


def test_dmem_modinfo_sin_binario_y_lee_sin_archivo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _solo_path(monkeypatch, tmp_path / "vacio")
    assert dm._modinfo(tmp_path / "x.ko", "version") is None
    assert dm._lee(tmp_path / "no-existe") is None
    f = tmp_path / "v"
    f.write_text(" 580.1 \n", encoding="utf-8")
    assert dm._lee(f) == "580.1"


def test_dmem_main_parche_vigente_sale_0_y_escribe_la_fila(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _prepara_dmem(tmp_path, monkeypatch, parche="580.178.04", stock="580.178.04")
    assert dm.main() == 0
    assert "vigente" in capsys.readouterr().out
    filas = [json.loads(x) for x in (tmp_path / "datos/dmem_parche.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [f["codigo"] for f in filas] == ["vigente"] and filas[0]["kernel"] == os.uname().release


def test_dmem_main_driver_nuevo_sale_1_y_dice_el_comando(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Control negativo del anterior: con un driver nuevo el mismo camino sale 1 e imprime la accion."""
    _prepara_dmem(tmp_path, monkeypatch, parche="580.100.00", stock="580.178.04")
    assert dm.main() == 1
    salida = capsys.readouterr().out
    assert "driver_nuevo" in salida and "bash tools/dmem_reconstruye.sh" in salida and salida.rstrip().endswith("580.178.04")


def test_dmem_como_script_termina_con_el_codigo_de_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _prepara_dmem(tmp_path, monkeypatch, parche="580.178.04", stock="580.178.04")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with pytest.raises(SystemExit) as salida:
            runpy.run_module("tools.dmem_monitor", run_name="__main__")
    assert salida.value.code in (0, 1)
    assert (tmp_path / "datos/dmem_parche.jsonl").read_text(encoding="utf-8").count("\n") >= 1


# ============================================================ vigilante_memavail


def test_vigilante_lee_meminfo_de_un_archivo_propio(tmp_path: Path) -> None:
    f = tmp_path / "meminfo"
    f.write_text("MemTotal: 999 kB\nMemAvailable:   123456 kB\n", encoding="utf-8")
    assert vm.lee_meminfo(f) == 123456
    f.write_text("MemTotal: 999 kB\n", encoding="utf-8")
    assert vm.lee_meminfo(f) is None
    assert vm.lee_meminfo(tmp_path / "no-existe") is None


def test_vigilante_main_cruza_una_vuelta_y_registra_el_disparo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    (tmp_path / "interruptores.json").write_text(json.dumps({"modos": {"memavail": "observar"}}), encoding="utf-8")
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemAvailable: 1048576 kB\n", encoding="utf-8")  # 1 GiB < 8 GiB
    psi = tmp_path / "psi"
    psi.write_text("some avg10=1.00\nfull avg10=40.00 avg60=0 avg300=0 total=0\n", encoding="utf-8")
    monkeypatch.setattr(vm, "lee_meminfo", functools.partial(vm.lee_meminfo, meminfo))
    monkeypatch.setattr(vm, "lee_psi_full", functools.partial(vm.lee_psi_full, psi))
    pausas = _corta_en(monkeypatch, vm, 1)
    with pytest.raises(_Fin):
        vm.main()
    assert pausas == [1]
    assert interruptores.resumen("memavail") == {"disparos": 1, "confirmados": 1, "falsos_positivos": 0}


def test_vigilante_main_en_off_no_registra_nada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Control negativo: la misma vuelta con el interruptor en `off` no escribe."""
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemAvailable: 1048576 kB\n", encoding="utf-8")
    monkeypatch.setattr(vm, "lee_meminfo", functools.partial(vm.lee_meminfo, meminfo))
    _corta_en(monkeypatch, vm, 1)
    with pytest.raises(_Fin):
        vm.main()
    assert interruptores.resumen("memavail") == {"disparos": 0, "confirmados": 0, "falsos_positivos": 0}


# ============================================================ interruptores


def test_interruptores_usa_blackbox_data_para_modo_registro_y_resumen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    assert interruptores._datos() == tmp_path
    assert interruptores.modo("x") == "off"
    (tmp_path / "interruptores.json").write_text(json.dumps({"modos": {"x": "actuar"}}), encoding="utf-8")
    assert interruptores.modo("x") == "actuar"
    interruptores.registra("x", {"habria_actuado": True, "confirmado_por_psi": True})
    assert interruptores.resumen("x") == {"disparos": 1, "confirmados": 1, "falsos_positivos": 0}


def test_interruptores_resumen_salta_lineas_corruptas_y_sin_archivo_da_ceros(tmp_path: Path) -> None:
    (tmp_path / "x.jsonl").write_text(
        '{"habria_actuado": true, "confirmado_por_psi": true}\n{roto\n{"habria_actuado": true}\n{"otro": 1}\n', encoding="utf-8")
    assert interruptores.resumen("x", tmp_path) == {"disparos": 2, "confirmados": 1, "falsos_positivos": 1}
    assert interruptores.resumen("no-existe", tmp_path) == {"disparos": 0, "confirmados": 0, "falsos_positivos": 0}


def test_interruptores_modo_con_json_que_no_es_objeto_vale_off(tmp_path: Path) -> None:
    f = tmp_path / "i.json"
    f.write_text("[1, 2]", encoding="utf-8")
    assert interruptores.modo("x", f) == "off"



def test_gpuoom_lee_proc_cuenta_los_procesos_que_no_pudo_leer(tmp_path: Path) -> None:
    sano = tmp_path / "10"
    sano.mkdir()
    (sano / "status").write_text("Name:\tpytest\nRssAnon:\t2048 kB\nRssShmem:\t4 kB\nVmSwap:\t8 kB\n", encoding="utf-8")
    (sano / "oom_score_adj").write_text("200\n", encoding="utf-8")
    (tmp_path / "20").mkdir()  # sin status: murio durante el barrido
    (tmp_path / "30").mkdir()
    (tmp_path / "30" / "status").write_text("Name:\tx\n", encoding="utf-8")
    (tmp_path / "30" / "oom_score_adj").write_text("no-es-numero\n", encoding="utf-8")
    (tmp_path / "self").mkdir()  # no es un pid
    filas, ilegibles = g.lee_proc(tmp_path)
    assert filas == [(10, "pytest", 2048, 4, 8, 200)] and ilegibles == 2


def test_oci_como_script_sale_por_el_exec_del_runtime_real(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Un runtime real inexistente hace fallar el exec REAL (nada se sustituye): el error sale de `sys.exit(main(...))`."""
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    monkeypatch.setenv("BB_OCI_REAL_RUNTIME", str(tmp_path / "no-existe"))
    monkeypatch.setattr(sys, "argv", ["bb_oci_runtime.py", "state", "c1"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with pytest.raises(FileNotFoundError, match="No such file") as caso:
            runpy.run_module("tools.bb_oci_runtime", run_name="__main__")
    assert caso.value.errno == 2


def test_vigilante_como_script_entra_al_bucle_y_se_corta_en_el_sleep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))  # sin interruptores.json: modo off, no registra
    pausas = _corta_en(monkeypatch, vm, 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with pytest.raises(_Fin):
            runpy.run_module("tools.vigilante_memavail", run_name="__main__")
    assert pausas == [1] and not (tmp_path / "interruptores").exists()
