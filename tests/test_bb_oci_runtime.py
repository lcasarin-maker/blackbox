"""Suite de `tools/bb_oci_runtime.py` -- el envoltorio de runtime OCI de bb.

## Por que existe

La regla (voto de Luis, 2026-10-12) es que todo contenedor nazca con tope
propio de memoria, swap y procesos. Esta suite guarda que la politica pueda
salir en TODAS sus direcciones: corrige lo que no trae tope, deja intacto lo
que trae uno, rechaza la GPU sin reclamo o con la suma desbordada, y no actua
(pasando el spec intacto) cuando la averia es suya. Una politica que solo se
probara por su caso positivo seria un gate sin verificar.

Las pruebas dorado parten del `config.json` que genera `runc spec` cuando hay
runc; si no, de un spec escrito a mano con la misma forma.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import bb_oci_runtime as oci

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "tools" / "bb_oci_runtime.py"
GIB = 1024**3

SPEC_A_MANO = {
    "ociVersion": "1.2.1",
    "process": {"terminal": True, "args": ["sh"], "cwd": "/",
                "env": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "TERM=xterm"]},
    "root": {"path": "rootfs", "readonly": True},
    "hostname": "runc",
    "mounts": [{"destination": "/proc", "type": "proc", "source": "proc"}],
    "linux": {"namespaces": [{"type": "pid"}, {"type": "mount"}],
              "maskedPaths": ["/proc/kcore"], "readonlyPaths": ["/proc/sys"]},
}


@pytest.fixture(scope="module")
def spec_base(tmp_path_factory) -> dict:
    """El spec de `runc spec` (sin `linux.resources` de memoria ni pids)."""
    if shutil.which("runc") is None:
        return copy.deepcopy(SPEC_A_MANO)
    d = tmp_path_factory.mktemp("runc_spec")
    subprocess.run(["runc", "spec"], cwd=d, check=True, capture_output=True, timeout=30)
    return json.loads((d / "config.json").read_text(encoding="utf-8"))


def _con(spec: dict, env=(), anot=None, recursos=None, **otros) -> dict:
    """Copia de `spec` con env/anotaciones/recursos; `devices` va a linux, `hooks` a la raiz."""
    s = copy.deepcopy(spec)
    s["process"]["env"] = list(s["process"]["env"]) + list(env)
    if anot is not None:
        s["annotations"] = anot
    if recursos is not None:
        s["linux"]["resources"] = recursos
    if "devices" in otros:
        s["linux"]["devices"] = otros["devices"]
    if "hooks" in otros:
        s["hooks"] = otros["hooks"]
    return s


GPU = ["NVIDIA_VISIBLE_DEVICES=all"]


# ---------------------------------------------------------------- dorado

def test_dorado_sin_tope_se_corrige_con_la_clase_general(spec_base):
    d = oci.decidir(spec_base, {}, 50.1, "c1")
    assert d["decision"] == "CORREGIR"
    assert d["clase"] == "general"
    esperado = copy.deepcopy(spec_base)
    recursos = esperado["linux"].setdefault("resources", {})
    recursos["memory"] = {"limit": 3 * GIB, "swap": 3 * GIB}
    recursos["pids"] = {"limit": 2048}
    assert d["spec"] == esperado  # solo cambian los topes; el resto, byte a byte igual
    assert spec_base["linux"].get("resources", {}).get("memory") is None  # sin efecto lateral


def test_tope_propio_mas_estricto_queda_intacto(spec_base):
    s = _con(spec_base, recursos={"memory": {"limit": 64 * 1024**2, "swap": 64 * 1024**2},
                                  "pids": {"limit": 16}})
    d = oci.decidir(s, {}, 50.1, "c1")
    assert d["decision"] == "ADMITIR"
    assert d["spec"] is None and d["cambios"] == []


def test_limite_declarado_sin_swap_solo_recibe_el_swap(spec_base):
    """El caso vLLM de hoy: 75 GiB declarados, swap ilimitado (-1)."""
    s = _con(spec_base, env=GPU, anot={"bb.gpu_budget_gib": "36"},
             recursos={"memory": {"limit": 75 * GIB, "swap": -1}})
    d = oci.decidir(s, {}, 50.1, "vllm")
    assert d["decision"] == "CORREGIR"
    mem = d["spec"]["linux"]["resources"]["memory"]
    assert mem == {"limit": 75 * GIB, "swap": 75 * GIB}  # el limite declarado no se toca
    assert d["spec"]["linux"]["resources"]["pids"] == {"limit": 2048}
    assert d["gpu_gib"] == 36.0


@pytest.mark.parametrize("swap", [None, 0, -1])
def test_swap_ausente_cero_o_ilimitado_cuenta_como_sin_tope(spec_base, swap):
    s = _con(spec_base, recursos={"memory": {"limit": GIB, "swap": swap}, "pids": {"limit": 8}})
    d = oci.decidir(s, {}, 50.1, "c")
    assert d["spec"]["linux"]["resources"]["memory"]["swap"] == GIB


def test_sin_gpu_no_exige_reclamo(spec_base):
    s = _con(spec_base, env=["NVIDIA_VISIBLE_DEVICES=void"])
    d = oci.decidir(s, {"otro": 50.0}, 50.1, "c")
    assert d["decision"] == "CORREGIR" and d["gpu"] is None and d["clase"] == "general"


def test_gpu_con_etiqueta_se_admite_con_la_clase_gpu(spec_base):
    s = _con(spec_base, env=GPU, anot={"bb.gpu_budget_gib": "36"})
    d = oci.decidir(s, {}, 50.1, "c")
    assert d["decision"] == "CORREGIR" and d["clase"] == "gpu"
    assert d["spec"]["linux"]["resources"]["memory"] == {"limit": 14 * GIB, "swap": 14 * GIB}


def test_gpu_sin_etiqueta_se_rechaza(spec_base):
    d = oci.decidir(_con(spec_base, env=GPU), {}, 50.1, "c")
    assert d["decision"] == "RECHAZAR"
    assert "sin anotacion bb.gpu_budget_gib" in d["motivo"]
    assert d["spec"] is None


@pytest.mark.parametrize("valor", ["abc", "-1", "0", "inf", "nan"])
def test_gpu_con_etiqueta_ilegible_se_rechaza(spec_base, valor):
    d = oci.decidir(_con(spec_base, env=GPU, anot={"bb.gpu_budget_gib": valor}), {}, 50.1, "c")
    assert d["decision"] == "RECHAZAR"


@pytest.mark.parametrize("via", ["device", "hook"])
def test_gpu_por_dispositivo_o_hook_tambien_cuenta(spec_base, via):
    if via == "device":
        s = _con(spec_base, devices=[{"path": "/dev/nvidia0", "type": "c", "major": 195, "minor": 0}])
    else:
        s = _con(spec_base, hooks={"prestart": [{"path": "/usr/bin/nvidia-container-runtime-hook"}]})
    assert oci.decidir(s, {}, 50.1, "c")["decision"] == "RECHAZAR"


def test_suma_desbordada_se_rechaza(spec_base):
    s = _con(spec_base, env=GPU, anot={"bb.gpu_budget_gib": "20"})
    d = oci.decidir(s, {"vllm": 36.0}, 50.1, "nuevo")
    assert d["decision"] == "RECHAZAR"
    assert "56.0 GiB supera el suelo de GPU 50.1" in d["motivo"]


def test_suma_justo_en_el_suelo_se_admite(spec_base):
    s = _con(spec_base, env=GPU, anot={"bb.gpu_budget_gib": "14.1"})
    assert oci.decidir(s, {"vllm": 36.0}, 50.1, "nuevo")["decision"] == "CORREGIR"


def test_recrear_el_mismo_id_no_se_cuenta_dos_veces(spec_base):
    s = _con(spec_base, env=GPU, anot={"bb.gpu_budget_gib": "36"})
    assert oci.decidir(s, {"vllm": 36.0}, 50.1, "vllm")["decision"] == "CORREGIR"


@pytest.mark.parametrize("spec", [None, [], "x", {"ociVersion": "1.2.1"}])
def test_spec_sin_linux_no_actua(spec):
    d = oci.decidir(spec, {}, 50.1, "c")
    assert d["decision"] == "NO_ACTUAR" and d["motivo"].startswith("UNSUPPORTED")


# ---------------------------------------------------------------- registro

def test_registro_repliega_admitidos_menos_liberados():
    filas = [
        {"evento": "create", "contenedor": "a", "decision": "CORREGIR", "gpu_gib": 36.0},
        {"evento": "create", "contenedor": "b", "decision": "ADMITIR", "gpu_gib": 5.0},
        {"evento": "create", "contenedor": "c", "decision": "RECHAZAR", "gpu_gib": None},
        {"evento": "create", "contenedor": "d", "decision": "CORREGIR", "gpu_gib": None},
        {"evento": "delete", "contenedor": "b"},
    ]
    lineas = [json.dumps(f) for f in filas] + ["{roto", "", "[]"]
    vivos, ilegibles = oci.reclamos_vigentes(lineas)
    assert vivos == {"a": 36.0}
    assert ilegibles == 2


# ---------------------------------------------------------------- argv

def test_argv_al_estilo_containerd():
    argv = ["--root", "/run/docker/runtime-runc/moby", "--log", "/x/log.json",
            "--log-format", "json", "--systemd-cgroup", "create", "--bundle", "/b",
            "--pid-file", "/b/init.pid", "--console-socket", "/tmp/s", "abc123"]
    i = oci.subcomando(argv)
    assert i is not None and argv[i] == "create"
    assert oci.args_create(argv[i + 1:]) == (Path("/b"), "abc123")


def test_argv_formas_cortas_y_con_igual():
    assert oci.args_create(["-b", "/x", "id1"]) == (Path("/x"), "id1")
    assert oci.args_create(["--bundle=/y", "--no-pivot", "id2"]) == (Path("/y"), "id2")
    assert oci.args_create(["id3"])[1] == "id3"
    assert oci.subcomando(["--rootless=true", "state", "x"]) == 1
    assert oci.subcomando(["--debug"]) is None


# ---------------------------------------------------------------- de punta a punta

@pytest.fixture
def entorno(tmp_path):
    """Un runtime real falso que deja constancia de con que spec lo llamaron."""
    falso = tmp_path / "runtime_real"
    falso.write_text('#!/bin/sh\necho "$@" > "$RASTRO"\n'
                     'b=""; prev=""; for a in "$@"; do [ "$prev" = "--bundle" ] && b="$a"; prev="$a"; done\n'
                     '[ -n "$b" ] && cp "$b/config.json" "$RASTRO.spec"\nexit 0\n', encoding="utf-8")
    falso.chmod(0o755)
    env = {**os.environ, "BB_OCI_REAL_RUNTIME": str(falso), "BLACKBOX_DATA": str(tmp_path / "data"),
           "RASTRO": str(tmp_path / "rastro")}
    env.pop("BB_OCI_GPU_FLOOR_GIB", None)
    return tmp_path, env


def _bundle(tmp_path, nombre, spec) -> Path:
    b = tmp_path / nombre
    b.mkdir()
    texto = spec if isinstance(spec, str) else json.dumps(spec)
    (b / "config.json").write_text(texto, encoding="utf-8")
    return b


def _corre(env, *args):
    return subprocess.run([sys.executable, str(WRAPPER), *args], env=env, capture_output=True,
                          text=True, timeout=60)


def _registro(tmp_path) -> list[dict]:
    f = tmp_path / "data" / "oci_runtime.jsonl"
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()]


def test_e2e_corrige_y_delega(entorno, spec_base):
    tmp, env = entorno
    b = _bundle(tmp, "b1", spec_base)
    r = _corre(env, "--root", "/r", "create", "--bundle", str(b), "c1")
    assert r.returncode == 0, r.stderr
    delegado = json.loads((tmp / "rastro.spec").read_text(encoding="utf-8"))
    assert delegado["linux"]["resources"]["memory"] == {"limit": 3 * GIB, "swap": 3 * GIB}
    assert (tmp / "rastro").read_text(encoding="utf-8").split() == ["--root", "/r", "create", "--bundle", str(b), "c1"]
    assert _registro(tmp)[-1]["decision"] == "CORREGIR"


def test_e2e_rechazo_no_llama_al_runtime_real(entorno, spec_base):
    tmp, env = entorno
    b = _bundle(tmp, "b1", _con(spec_base, env=GPU))
    r = _corre(env, "create", "--bundle", str(b), "c1")
    assert r.returncode == 3
    assert "RECHAZADO c1" in r.stderr and "bb.gpu_budget_gib" in r.stderr
    assert not (tmp / "rastro").exists()
    assert _registro(tmp)[-1]["decision"] == "RECHAZAR"


def test_e2e_spec_ilegible_pasa_intacto(entorno):
    tmp, env = entorno
    roto = '{"ociVersion": "1.2.1", "linux": '
    b = _bundle(tmp, "b1", roto)
    r = _corre(env, "create", "--bundle", str(b), "c1")
    assert r.returncode == 0  # el runtime real decide, como hoy
    assert (tmp / "rastro.spec").read_text(encoding="utf-8") == roto
    fila = _registro(tmp)[-1]
    assert fila["decision"] == "NO_ACTUAR" and fila["motivo"].startswith("NOT_COLLECTED")


def test_e2e_la_suma_cruza_contenedores_y_delete_libera(entorno, spec_base):
    tmp, env = entorno
    s = _con(spec_base, env=GPU, anot={"bb.gpu_budget_gib": "30"})
    assert _corre(env, "create", "--bundle", str(_bundle(tmp, "b1", s)), "g1").returncode == 0
    r = _corre(env, "create", "--bundle", str(_bundle(tmp, "b2", s)), "g2")
    assert r.returncode == 3 and "30.0 GiB ya registrados" in r.stderr
    assert _corre(env, "delete", "--force", "g1").returncode == 0
    assert _corre(env, "create", "--bundle", str(tmp / "b2"), "g2").returncode == 0


def test_e2e_suelo_configurable_y_su_origen(entorno, spec_base):
    tmp, env = entorno
    s = _con(spec_base, env=GPU, anot={"bb.gpu_budget_gib": "30"})
    r = _corre({**env, "BB_OCI_GPU_FLOOR_GIB": "20"}, "create", "--bundle", str(_bundle(tmp, "b1", s)), "g1")
    assert r.returncode == 3
    assert _registro(tmp)[-1]["suelo_origen"] == "BB_OCI_GPU_FLOOR_GIB"
    r = _corre({**env, "BB_OCI_GPU_FLOOR_GIB": "x"}, "create", "--bundle", str(tmp / "b1"), "g1")
    assert r.returncode == 0 and "ilegible" in _registro(tmp)[-1]["suelo_origen"]


def test_e2e_registro_inservible_no_bloquea(entorno, spec_base):
    tmp, env = entorno
    estorbo = tmp / "no_es_dir"
    estorbo.write_text("", encoding="utf-8")
    r = _corre({**env, "BLACKBOX_DATA": str(estorbo)}, "create", "--bundle", str(_bundle(tmp, "b1", spec_base)), "c1")
    assert r.returncode == 0
    assert "registro no disponible" in r.stderr
    delegado = json.loads((tmp / "rastro.spec").read_text(encoding="utf-8"))
    assert delegado["linux"]["resources"]["pids"] == {"limit": 2048}  # la politica sigue aplicando


def test_e2e_otros_subcomandos_pasan_tal_cual(entorno):
    tmp, env = entorno
    r = _corre(env, "--root", "/r", "kill", "c1", "KILL")
    assert r.returncode == 0
    assert (tmp / "rastro").read_text(encoding="utf-8").split() == ["--root", "/r", "kill", "c1", "KILL"]
    assert not (tmp / "data" / "oci_runtime.jsonl").exists()


# ---------------------------------------------------------------- laboratorio (nivel 2)

LAB = ROOT / "tools" / "portero_docker_lab.sh"


@pytest.mark.parametrize("socket", ["/var/run/docker.sock", "/run/docker.sock", "enlace"])
def test_lab_se_niega_a_apuntar_al_socket_de_produccion(tmp_path, socket):
    """La guarda corre ANTES que cualquier docker; un enlace al socket de produccion tambien cae."""
    if socket == "enlace":
        socket = str(tmp_path / "lab.sock")
        os.symlink("/var/run/docker.sock", socket)
    r = subprocess.run(["bash", str(LAB), "status"], env={**os.environ, "BB_LAB_SOCK": socket},
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 1
    assert "es el de produccion" in r.stderr and "no se actua" in r.stderr


def test_lab_status_con_el_socket_propio_no_se_niega():
    """Control de la guarda: con el socket del laboratorio NO se niega (si no, nunca actuaria)."""
    env = {k: v for k, v in os.environ.items() if k != "BB_LAB_SOCK"}
    r = subprocess.run(["bash", str(LAB), "status"], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert "es el de produccion" not in r.stderr


def test_lab_solo_habla_con_produccion_para_docker_save():
    """Todo `docker` del script va por `labdocker` (-H del laboratorio) salvo el save de lectura."""
    lineas = [x for x in LAB.read_text(encoding="utf-8").splitlines()
              if " docker -H" in x and not x.lstrip().startswith("#")]
    assert len(lineas) == 2
    assert 'docker -H "$LAB_HOST" "$@"' in lineas[0]
    assert 'save "$IMAGE" | labdocker load' in lineas[1]
