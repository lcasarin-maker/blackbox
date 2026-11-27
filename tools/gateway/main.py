#!/usr/bin/env python3
"""Local LLM inference gateway launcher.

Reads engine configuration (CLI arg, BB_GATEWAY_CONFIG, or sibling active_engine.json)
and execs `docker run` with loopback isolation, memory/swap limits, and `--pids-limit 2048`.
"""
import json
import os
import sys
from pathlib import Path

GATEWAY_DIR = Path(__file__).resolve().parent
CONTAINER_NAME = "nemotron-server"
NETWORK_MODES = ("host", "bridge_loopback")


def build_env_args(cfg: dict) -> list[str]:
    env = {"NVIDIA_VISIBLE_DEVICES": "all"}
    extra = cfg.get("env", {})
    if not isinstance(extra, dict):
        raise ValueError(f"active_engine.json: 'env' debe ser un objeto K:V, no {type(extra).__name__}")
    bad = [k for k, v in extra.items() if not isinstance(k, str) or not isinstance(v, str)]
    if bad:
        raise ValueError(f"active_engine.json: 'env' solo admite strings; claves invalidas: {bad}")
    env.update(extra)
    return [arg for k, v in env.items() for arg in ("-e", f"{k}={v}")]


def build_network_args(cfg: dict) -> list[str]:
    mode = cfg.get("network", "host")
    if mode not in NETWORK_MODES:
        raise ValueError(f"active_engine.json: 'network' desconocido {mode!r} — admitidos: {list(NETWORK_MODES)}")
    if mode == "host":
        return ["--network", "host"]
    if cfg.get("host") != "0.0.0.0":
        raise ValueError(
            f"active_engine.json: con network='bridge_loopback' el bind del motor "
            f"debe ser 'host': '0.0.0.0' (llegó {cfg.get('host')!r})."
        )
    port = cfg["port"]
    return ["-p", f"127.0.0.1:{port}:{port}"]


def build_volume_args(cfg: dict) -> list[str]:
    extra = cfg.get("extra_volumes", [])
    if not isinstance(extra, list) or any(
        not isinstance(v, str) or ":" not in v or not v.strip() for v in extra
    ):
        raise ValueError("active_engine.json: 'extra_volumes' debe ser lista de strings 'origen:destino[:modo]'")
    models_dir = cfg.get("models_dir", "/models")
    return ["-v", f"{models_dir}:/models", *(arg for v in extra for arg in ("-v", v))]


def build_vllm_args(cfg: dict) -> list[str]:
    required = [
        "image", "model_path", "served_model_name", "host", "port",
        "gpu_memory_utilization", "max_model_len", "container_memory_gb",
    ]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"active_engine.json missing required fields for engine=vllm: {missing}")

    mem = f"{cfg['container_memory_gb']}g"
    swap_gb = cfg.get("container_memory_swap_gb", cfg["container_memory_gb"])
    if isinstance(swap_gb, bool) or not isinstance(swap_gb, (int, float)) or swap_gb <= 0:
        raise ValueError(f"active_engine.json: 'container_memory_swap_gb' invalido: {swap_gb!r}")
    swap = f"{swap_gb}g"
    return [
        "/usr/bin/docker", "run", "--rm", "--name", CONTAINER_NAME,
        *build_network_args(cfg), "--runtime", "nvidia",
        *build_env_args(cfg),
        *build_volume_args(cfg),
        "--memory", mem, "--memory-swap", swap, "--pids-limit", "2048",
        "--oom-score-adj", "500",
        cfg["image"],
        cfg["model_path"],
        "--served-model-name", cfg["served_model_name"],
        "--gpu-memory-utilization", str(cfg["gpu_memory_utilization"]),
        "--max-model-len", str(cfg["max_model_len"]),
        "--host", cfg["host"], "--port", str(cfg["port"]),
        *cfg.get("extra_args", []),
    ]


ENGINE_BUILDERS = {
    "vllm": build_vllm_args,
}


def main() -> int:
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
    elif os.environ.get("BB_GATEWAY_CONFIG"):
        config_path = Path(os.environ["BB_GATEWAY_CONFIG"])
    else:
        config_path = GATEWAY_DIR / "active_engine.json"
    cfg = json.loads(config_path.read_text(encoding="utf-8"))

    engine = cfg.get("engine")
    builder = ENGINE_BUILDERS.get(engine)
    if builder is None:
        sys.stderr.write(
            f"[gateway] Unknown or unimplemented engine {engine!r} in {config_path} "
            f"— supported: {sorted(ENGINE_BUILDERS)}\n"
        )
        return 1

    argv = builder(cfg)
    sys.stderr.write(
        f"[gateway] engine={engine} served_model_name={cfg.get('served_model_name')} "
        f"host={cfg.get('host')} port={cfg.get('port')} "
        f"network={cfg.get('network', 'host')}\n"
    )
    os.execvp(argv[0], argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
