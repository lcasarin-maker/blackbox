"""Contrato del lanzador recibido, con configuración sintética y sin iniciar motores."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "tools" / "gateway"


def cargar():
    path = GATEWAY / "main.py"
    assert path.is_file(), "falta el lanzador recibido"
    spec = importlib.util.spec_from_file_location("gateway_handoff", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def config():
    return {"engine": "vllm", "image": "example.invalid/engine:fixed",
            "model_path": "/models/example", "served_model_name": "example-model",
            "host": "0.0.0.0", "port": 8000, "network": "bridge_loopback",
            "gpu_memory_utilization": 0.5, "max_model_len": 2048,
            "container_memory_gb": 4, "admission_check_gb": 6}


def test_lanzador_recibido_conserva_aislamiento_y_memoria(config):
    module = cargar()
    args = module.build_vllm_args(config)
    assert "127.0.0.1:8000:8000" in args
    assert "--network" not in args
    assert args[args.index("--memory") + 1] == "4g"
    assert args[args.index("--memory-swap") + 1] == "4g"
    assert "NVIDIA_VISIBLE_DEVICES=all" in args
    assert args[args.index("--served-model-name") + 1] == "example-model"


@pytest.mark.parametrize("mutation", [{"network": "typo"}, {"host": "127.0.0.1"},
                                      {"env": []}, {"env": {"X": 3}}])
def test_configuracion_invalida_bloquea(config, mutation):
    module = cargar()
    config.update(mutation)
    with pytest.raises(ValueError):
        module.build_vllm_args(config)


def test_fuente_de_configuracion_explicita_y_ausencia(tmp_path, monkeypatch, config):
    import json

    module = cargar()
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setenv("BB_GATEWAY_CONFIG", str(path))
    monkeypatch.setattr(module.sys, "argv", ["main.py"])
    invocations = []
    monkeypatch.setattr(module.os, "execvp", lambda cmd, argv: invocations.append(argv))
    module.main()
    assert len(invocations) == 1
    assert config["image"] in invocations[0]
    monkeypatch.setenv("BB_GATEWAY_CONFIG", str(tmp_path / "ausente.json"))
    with pytest.raises(FileNotFoundError):
        module.main()
    assert len(invocations) == 1


def test_unit_parametrizada_y_sin_rutas_del_donante():
    path = GATEWAY / "ai-nemotron.service"
    assert path.is_file(), "falta la unit recibida"
    text = path.read_text()
    assert "EnvironmentFile=%h/.config/blackbox/gateway.env" in text
    assert "${BB_GATEWAY_DIR}/main.py ${BB_GATEWAY_CONFIG}" in text
    assert "${BB_GATEWAY_DIR}/admission_check_wrapper.sh ${BB_GATEWAY_CONFIG}" in text
    assert "/srv/" not in text
    assert "Restart=on-failure" in text


def test_wrapper_requiere_configuracion_sin_tocar_admision(tmp_path):
    import subprocess

    wrapper = GATEWAY / "admission_check_wrapper.sh"
    assert wrapper.is_file(), "falta el adaptador de admisión"
    result = subprocess.run(["bash", str(wrapper)], cwd=tmp_path,
                            capture_output=True, text=True, timeout=5)
    assert result.returncode != 0
    assert "config" in result.stderr.lower()
