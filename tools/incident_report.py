#!/usr/bin/env python3
"""Reporte POR INCIDENTE de un reinicio de la ATOM, en el formato que la
comunidad de NVIDIA/open-gpu-kernel-modules#1358 fue consolidando.

Por que existe: `bb scan` es un volcado por sintoma (OOM, Xid, segfaults...).
Dos reportes de dos unidades no se pueden comparar asi. La issue #1358 propuso
(comentario del 2026-10-02) un resumen de incidente y una tabla de seis
timestamps SEPARADOS; otros autores aportaron la cadena de eventos con receptor
externo, la tabla de conjuncion, la matriz de mitigacion de una variable por
vez y el entorno textual. Este modulo emite todo eso desde lo que `bb` ya mide.

Reglas del formato (de la propia issue, no inventadas aqui):

* Una medida que no esta disponible se escribe `NOT_COLLECTED`, `UNSUPPORTED` o
  `COLLECTION_FAILED`. El cero se reserva para un cero OBSERVADO, y se dice el
  intervalo buscado (`0 en <ventana>`).
* Los seis timestamps van por separado, con zona horaria, fuente e
  incertidumbre. Un puerto TCP abierto no es una respuesta de aplicacion.
* Un `bootstatus=0` o un watchdog armado, solos, no dicen nada sobre lo que
  paso durante la falla.
* Se informan tambien las ventanas SANAS (exposicion, no solo uptime).

El nodo se anonimiza (hash del machine-id): ni hostname, ni serie, ni UUID.
"""

from __future__ import annotations

import os
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools import hallazgo
from tools import reboot_verdict as rv

RAIZ = Path(__file__).resolve().parents[1]
FIRMAS = RAIZ / "rules/firmas_gb10.json"
# Clase de registro BERT que el personal de NVIDIA cita (hilo 384436): ver Atlas, catalogo_destilado.md#forum:G6
ATLAS_RAIZ = "knowledge/investigations/gb10_cortes_2026-10-11/"
NOT_COLLECTED = "NOT_COLLECTED"
UNSUPPORTED = "UNSUPPORTED"
COLLECTION_FAILED = "COLLECTION_FAILED"
SALIDA = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox")) / "incidentes"
UMBRAL_ZONA_C = 94.8  # alarma de atom_gpu_telemetry: trip 104.8 C menos 10 C
NVRM_NOMEM = "NV_ERR_NO_MEMORY"
VENTANA_RELEVANTE_MIN = 30  # un evento a horas de la muerte es contexto, no su inicio
# clocks_event_reasons de nvidia-smi: bit -> nombre (spark-gpu-throttle-check; NVML)
THROTTLE_BITS = {
    0x01: "GPU_IDLE",
    0x02: "APP_CLOCKS_SETTING",
    0x04: "SW_POWER_CAP",
    0x08: "HW_SLOWDOWN",
    0x10: "SYNC_BOOST",
    0x20: "SW_THERMAL_SLOWDOWN",
    0x40: "HW_THERMAL_SLOWDOWN",
    0x80: "HW_POWER_BRAKE",
}


def decodifica_throttle(valor: str | None) -> str:
    """'0x...' -> nombres de los bits activos; 0 -> 'ninguno'. Un valor ilegible no es 'ninguno'."""
    try:
        n = int(str(valor), 16)
    except ValueError:
        return COLLECTION_FAILED
    return "+".join(nombre for bit, nombre in THROTTLE_BITS.items() if n & bit) or (
        "ninguno" if n == 0 else f"bits_desconocidos:0x{n:x}"
    )


XID = re.compile(r"NVRM: Xid \(PCI:[^)]*\): (\d+)")


# ------------------------------------------------------------------ utilidades
def _leer(ruta: str) -> str:
    """Contenido o el marcador que corresponde: nunca un vacio que se lea como cero."""
    try:
        return Path(ruta).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return UNSUPPORTED
    except OSError:
        return COLLECTION_FAILED


def _cmd(*args: str) -> str:
    try:
        r = subprocess.run(
            args, capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return COLLECTION_FAILED
    return (
        r.stdout.strip()
        if r.returncode == 0 and r.stdout.strip()
        else COLLECTION_FAILED
    )


def iso(epoch: float | None) -> str:
    """Epoch -> ISO 8601 con offset LOCAL y su equivalente UTC (los reportes ajenos mezclan ambos)."""
    if epoch is None:
        return NOT_COLLECTED
    dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
    return (
        f"{dt.astimezone().isoformat(timespec='seconds')} ({dt.strftime('%H:%M:%SZ')})"
    )


def epoch_de(ts: str | None) -> float | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts).timestamp()
    except ValueError:
        return None


def nodo_anonimo() -> str:
    return hallazgo.nodo_anonimo(_leer)


# --------------------------------------------------------------------- plataforma
def plataforma() -> dict[str, Any]:
    dgx = {}
    for linea in _leer("/etc/dgx-release").splitlines():
        k, _, v = linea.partition("=")
        if k in ("DGX_PLATFORM", "DGX_SWBUILD_VERSION", "DGX_SWBUILD_DATE") and v:
            dgx[k] = v.strip('"')
    gpu = _cmd(
        "nvidia-smi",
        "--query-gpu=name,driver_version,vbios_version",
        "--format=csv,noheader",
    )
    modulo = _cmd("modinfo", "-F", "filename", "nvidia")
    tam = COLLECTION_FAILED
    if modulo != COLLECTION_FAILED:
        try:
            tam = str(Path(modulo).stat().st_size)
        except OSError:
            tam = COLLECTION_FAILED
    sb = COLLECTION_FAILED
    try:
        sb = (
            "enabled"
            if Path(
                "/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c"
            ).read_bytes()[-1]
            == 1
            else "disabled"
        )
    except (OSError, IndexError):
        pass
    return {
        "oem": _leer("/sys/class/dmi/id/sys_vendor"),
        "producto": _leer("/sys/class/dmi/id/product_name"),
        "dgx": dgx or UNSUPPORTED,
        "bios": f"{_leer('/sys/class/dmi/id/bios_version')} ({_leer('/sys/class/dmi/id/bios_date')})",
        "placa": f"{_leer('/sys/class/dmi/id/board_name')} rev {_leer('/sys/class/dmi/id/board_version')}",
        "kernel": _cmd("uname", "-r"),
        "gpu_driver_vbios": gpu,
        "modulo_nvidia": {
            "licencia": _cmd("modinfo", "-F", "license", "nvidia"),
            "bytes": tam,
        },
        "secure_boot": sb,
        "serie_y_uuid": "REDACTED",
    }


def config_vigente() -> dict[str, Any]:
    """Configuracion AL GENERAR el reporte. Solo vale para el incidente si no cambio desde entonces:
    por eso el reporte la rotula y trae aparte lo que el journal de ESE boot si registro."""
    wd = "/sys/class/watchdog/watchdog0"
    return {
        "uvm_global_oversubscription": _leer(
            "/sys/module/nvidia_uvm/parameters/uvm_global_oversubscription"
        ),
        "swap_kib": _swap(),
        "sysctl_panic": {
            k: _cmd("sysctl", "-n", k)
            for k in (
                "kernel.panic",
                "kernel.hung_task_panic",
                "kernel.softlockup_panic",
            )
        },
        "watchdog_hw": {
            "identidad": _leer(f"{wd}/identity"),
            "timeout_s": _leer(f"{wd}/timeout"),
            "estado": _leer(f"{wd}/state"),
            "bootstatus_boot_actual": _leer(f"{wd}/bootstatus"),
        },
        "watchdog_systemd": _cmd(
            "systemctl", "show", "-p", "RuntimeWatchdogUSec", "--value"
        ),
    }


def _swap() -> str:
    try:
        lineas = Path("/proc/swaps").read_text(encoding="utf-8").splitlines()[1:]
        return str(sum(int(x.split()[2]) for x in lineas))
    except (OSError, ValueError, IndexError):
        return COLLECTION_FAILED


def config_del_boot(idx: int) -> dict[str, Any]:
    """Lo que el journal de ESE boot registro sobre su propia configuracion."""
    cmdline = rv._journal(
        "-b", str(idx), "-k", "--grep", "Kernel command line", "-n", "1", "-o", "cat"
    ).stdout.strip()
    cap = rv._journal(
        "-b", str(idx), "--grep", "gpuClkMax", "-o", "cat", "-n", "1"
    ).stdout.strip()
    m = re.search(r"gpuClkMin (\d+), gpuClkMax (\d+)", cap)
    return {
        "cmdline_del_boot": re.sub(r"UUID=[0-9a-fA-F-]+", "UUID=REDACTED", cmdline)[
            :300
        ]
        or NOT_COLLECTED,
        "clock_cap_confirmado_por_driver": f"{m.group(1)}-{m.group(2)} MHz"
        if m
        else NOT_COLLECTED,
    }


# ------------------------------------------------------------------ evidencia del boot
def telemetria_del_boot(boot_id: str) -> list[dict[str, Any]]:
    marca = (
        boot_id
        if "-" in boot_id
        else f"{boot_id[:8]}-{boot_id[8:12]}-{boot_id[12:16]}-{boot_id[16:20]}-{boot_id[20:]}"
    )
    filas = []
    if not rv.TELEMETRIA.exists():
        return filas
    with rv.TELEMETRIA.open(encoding="utf-8") as fh:
        for linea in fh:
            if marca in linea:
                try:
                    filas.append(json.loads(linea))
                except json.JSONDecodeError:
                    continue  # la ultima fila puede estar truncada por la muerte subita (playbooks#116)
    return filas


def zmax(fila: dict[str, Any]) -> float | None:
    z = fila.get("zonas") or []
    return max((x["temp_c"] for x in z), default=None) if z else None


def ventana_previa(muestras: list[dict[str, Any]], minutos: int = 5) -> dict[str, Any]:
    if not muestras:
        return {"estado": NOT_COLLECTED}
    fin = epoch_de(muestras[-1]["ts"]) or 0.0
    w = [m for m in muestras if (epoch_de(m["ts"]) or 0.0) >= fin - minutos * 60]

    def serie(clave: str) -> list[float]:
        return [float(m[clave]) for m in w if m.get(clave) is not None]

    def rango(v: list[float]) -> Any:
        return {"min": min(v), "max": max(v)} if v else NOT_COLLECTED

    zs = [z for z in (zmax(m) for m in w) if z is not None]
    return {
        "ventana": f"ultimos {minutos} min antes de la ultima muestra ({len(w)} muestras)",
        "gpu_temp_c": rango(serie("gpu_temp_c")),
        "zona_acpi_max_c": rango(zs),
        "sm_clk_mhz": rango(serie("sm_clk_mhz")),
        "gpu_power_w": rango(serie("gpu_power_w")),
        "gpu_util_pct": rango(serie("gpu_util_pct")),
        "mem_avail_mb": rango(serie("mem_avail_mb")),
        "psi_mem_full_avg10": rango(serie("psi_mem_full_avg10")),
        "vllm_requests_running": rango(serie("vllm_num_requests_running")),
        "vllm_kv_cache_pct": {
            "max": round(100 * max(serie("vllm_kv_cache_usage_perc")), 1)
        }
        if serie("vllm_kv_cache_usage_perc")
        else NOT_COLLECTED,
        "throttle": _throttle_en(w),
    }


def _throttle_en(w: list[dict[str, Any]]) -> dict[str, Any]:
    por: dict[str, int] = {}
    for m in w:
        nombre = decodifica_throttle(m.get("throttle"))
        por[nombre] = por.get(nombre, 0) + 1
    return {"muestras_por_razon": por, "total": len(w)}


def throttle_del_boot(muestras: list[dict[str, Any]]) -> dict[str, Any]:
    """Historial de clocks_event_reasons del boot. `bb scan` solo informa el throttle de AHORA:
    en el boot del corte del 2026-10-11 hubo 6 muestras HW_THERMAL y 66 SW_THERMAL que nadie leyo."""
    if not muestras:
        return {"estado": NOT_COLLECTED}
    por: dict[str, int] = {}
    ultima: dict[str, str] = {}
    for m in muestras:
        nombre = decodifica_throttle(m.get("throttle"))
        por[nombre] = por.get(nombre, 0) + 1
        ultima[nombre] = m["ts"]
    fin = epoch_de(muestras[-1]["ts"])
    termicas = {k: v for k, v in por.items() if "THERMAL" in k}
    lag = (
        {k: round((fin - (epoch_de(ultima[k]) or fin)) / 60, 1) for k in termicas}
        if fin
        else {}
    )
    return {
        "muestras_por_razon": por,
        "muestras_con_throttle_termico_hw": sum(
            v for k, v in por.items() if "HW_THERMAL" in k
        ),
        "minutos_entre_la_ultima_muestra_con_cada_razon_termica_y_la_ultima_muestra_del_boot": lag,
        "nota": "bb scan imprime solo el throttle actual; este historial viene del sampler de 5 s",
    }


def residencia_termica(muestras: list[dict[str, Any]]) -> dict[str, Any]:
    """Calor SOSTENIDO, no eventos de flanco (DEBT-TERMICA-CORROBORACION-DE-ALARMA-SIEMPRE-DESCARTA-01)."""
    if not muestras:
        return {"estado": NOT_COLLECTED}
    paso = 5.0
    zs = [zmax(m) for m in muestras]
    out: dict[str, Any] = {"cadencia_s": paso, "muestras": len(zs)}
    for umbral in (85.0, 90.0, UMBRAL_ZONA_C):
        out[f"minutos_sobre_{umbral:g}C"] = round(
            sum(1 for z in zs if z is not None and z >= umbral) * paso / 60, 1
        )
    racha = cur = 0
    for z in zs:
        cur = cur + 1 if z is not None and z >= 90.0 else 0
        racha = max(racha, cur)
    out["racha_maxima_sobre_90C_min"] = round(racha * paso / 60, 1)
    out["pico_zona_c"] = max((z for z in zs if z is not None), default=NOT_COLLECTED)
    return out


def residencia_ventana(
    desde: float, hasta: float, ruta: Path | None = None
) -> dict[str, Any]:
    """Calor sostenido y throttle decodificado en [desde, hasta] (epoch UTC), sobre TODOS los boots de la
    ventana. Es lo que `bb scan` no medía: contaba alarmas de flanco, cuyo campo `corroboracion` vale
    `descarta` en 395 de 395 eventos (DEBT-TERMICA-CORROBORACION-DE-ALARMA-SIEMPRE-DESCARTA-01)."""
    ruta = ruta or rv.TELEMETRIA
    if not ruta.exists():
        return {"estado": NOT_COLLECTED}
    d0 = datetime.fromtimestamp(desde, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    d1 = datetime.fromtimestamp(hasta, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    muestras = []
    with ruta.open(encoding="utf-8") as fh:
        for linea in fh:
            if not linea.startswith('{"ts": "') or not (d0 <= linea[8:27] <= d1):
                continue  # filtro barato por el sello UTC fijo: no se parsea el resto del archivo
            try:
                m = json.loads(linea)
            except json.JSONDecodeError:
                continue  # la ultima fila puede estar truncada por la muerte subita
            if m.get("evento") == "muestra":
                muestras.append(m)
    if not muestras:
        return {"estado": f"0 muestras de telemetria entre {d0}Z y {d1}Z"}
    return {
        "estado": "ok",
        "muestras": len(muestras),
        "residencia": residencia_termica(muestras),
        "throttle": throttle_del_boot(muestras)["muestras_por_razon"],
        "gpu_temp_max_c": max(
            (m["gpu_temp_c"] for m in muestras if m.get("gpu_temp_c") is not None),
            default=NOT_COLLECTED,
        ),
    }


def lineas_scan(r: dict[str, Any]) -> list[str]:
    """Texto para `bb scan`. Un estado que no es `ok` sale como tal, no como ceros."""
    if r.get("estado") != "ok":
        return [f"  calor sostenido:             {r.get('estado')}"]
    z = r["residencia"]
    return [
        f"  calor sostenido (zona ACPI): >85C {z['minutos_sobre_85C']} min | >90C {z['minutos_sobre_90C']} min | >94.8C {z['minutos_sobre_94.8C']} min",
        f"  racha maxima >90C:           {z['racha_maxima_sobre_90C_min']} min; pico de zona {z['pico_zona_c']} C; GPU max {r['gpu_temp_max_c']} C",
        "  throttle decodificado:       "
        + ", ".join(
            f"{k}={v}" for k, v in sorted(r["throttle"].items(), key=lambda kv: -kv[1])
        ),
    ]


def exposicion(muestras: list[dict[str, Any]]) -> dict[str, Any]:
    """Uptime NO es exposicion: minutos con GPU cargada son los que cuentan (peticion de la issue)."""
    if not muestras:
        return {"estado": NOT_COLLECTED}
    primero, ultimo = (
        epoch_de(muestras[0]["ts"]) or 0.0,
        epoch_de(muestras[-1]["ts"]) or 0.0,
    )
    carga = sum(1 for m in muestras if (m.get("gpu_util_pct") or 0) >= 80)
    return {
        "uptime_min": round((ultimo - primero) / 60, 1),
        "minutos_gpu_util_80_o_mas": round(carga * 5 / 60, 1),
        "minutos_con_vllm_peticiones": round(
            sum(1 for m in muestras if (m.get("vllm_num_requests_running") or 0) > 0)
            * 5
            / 60,
            1,
        ),
    }


def lineas_nvrm(idx: int) -> dict[str, Any]:
    r = rv._journal("-b", str(idx), "-k", "--grep", "NVRM:", "-o", "short-iso")
    if r.returncode not in (0, 1):
        return {"estado": COLLECTION_FAILED}
    ls = [x for x in r.stdout.splitlines() if "NVRM:" in x]
    nomem = [x for x in ls if NVRM_NOMEM in x]
    xids: dict[str, int] = {}
    for x in ls:
        m = XID.search(x)
        if m:
            xids[m.group(1)] = xids.get(m.group(1), 0) + 1
    primero = nomem[0].split()[0] if nomem else None
    ultimo = nomem[-1].split()[0] if nomem else None
    return {
        "lineas_NVRM_total": len(ls),
        "NV_ERR_NO_MEMORY": {
            "cuenta": len(nomem),
            "primera": primero or f"0 en el journal del boot {idx} (-k --grep NVRM:)",
            "ultima": ultimo,
        },
        "xid_por_codigo_en_journal": xids
        or f"0 en el journal del boot {idx} (-k --grep NVRM:)",
        "baseline_boot_sano": "1 linea NVRM de plataforma por boot (mpingwst, #1358 c3: ~200x en el incidente)",
    }


bert_registro = rv.bert_registro
GUID_MTKID = rv.GUID_MTKID
BERT_GUID = rv.BERT_GUID


# ------------------------------------------------------- conocimiento destilado
def coincidencias_firmas(idx: int) -> dict[str, Any]:
    """Busca en el journal del kernel del boot las firmas de `rules/firmas_gb10.json` (instrumento de bb).
    Separa INCIDENTES de ruido conocido: el ruido se cuenta aparte y no se lee como incidente. El
    conocimiento que respalda cada firma NO se copia aqui: cada una apunta a su documento en Atlas."""
    try:
        firmas = json.loads(FIRMAS.read_text(encoding="utf-8"))["firmas"]
    except (OSError, json.JSONDecodeError, KeyError):
        return {"estado": COLLECTION_FAILED, "detalle": f"{FIRMAS} ilegible"}
    out: dict[str, list[dict[str, Any]]] = {
        "incidente": [],
        "ruido_conocido": [],
        "ambiguo": [],
    }
    for f in firmas:
        r = rv._journal("-b", str(idx), "-k", "--grep", f["regex"], "-o", "cat")
        if r.returncode not in (0, 1):
            obs: Any = COLLECTION_FAILED
        else:
            n = len([x for x in r.stdout.splitlines() if x.strip()])
            obs = n if n else f"0 en el journal del kernel del boot {idx}"
        out[f["clase"]].append(
            {"id": f["id"], "lineas": obs, "atlas": ATLAS_RAIZ + f["atlas"]}
        )
    return {
        "incidente": out["incidente"],
        "ruido_conocido_contado_aparte": out["ruido_conocido"],
        "ambiguo": out["ambiguo"],
        "nota": "bb solo busca estas firmas; lo que no esta en rules/firmas_gb10.json no se busca (el conocimiento vive en Atlas)",
    }


def silencio_del_kernel(idx: int, muestras: list[dict[str, Any]]) -> dict[str, Any]:
    """Firma S4 (ver Atlas, catalogo_destilado.md#github:S4): el kernel calla mientras el resto sigue vivo. Mide cuanto antes de la
    ultima muestra de telemetria escribio por ultima vez el journal del kernel."""
    if not muestras:
        return {"estado": NOT_COLLECTED}
    r = rv._journal("-b", str(idx), "-k", "-n", "1", "-o", "short-iso")
    ultimo = (
        epoch_de(r.stdout.split()[0])
        if r.returncode == 0 and r.stdout.strip()
        else None
    )
    fin = epoch_de(muestras[-1]["ts"])
    if ultimo is None or fin is None:
        return {"estado": COLLECTION_FAILED}
    return {
        "ultima_linea_del_kernel": iso(ultimo),
        "ultima_muestra_de_telemetria": iso(fin),
        "segundos_de_silencio_del_kernel_antes_de_la_ultima_muestra": round(
            fin - ultimo, 1
        ),
        "lectura": "el journal puede cortarse antes que la telemetria (el dossier tecnico reporta que journald "
        "no hace fsync inmediato salvo CRIT); la hora de muerte la da la telemetria de 5 s, no el journal",
    }


def estado_mitigaciones(
    muestras: list[dict[str, Any]], cfg: dict[str, Any], cap_boot: dict[str, Any]
) -> list[dict[str, Any]]:
    """Estado, en ESTA maquina, de las mitigaciones que bb puede leer. Nivel de evidencia, quien las reporta
    y su n viven en Atlas: cada entrada apunta a su id en `catalogo_destilado.md`. Las demas (variables del
    contenedor, prompts) NO son observables por bb."""

    def ent(i: str, titulo: str) -> dict[str, Any]:
        return {
            "id": f"github:{i}",
            "titulo": titulo,
            "atlas": f"{ATLAS_RAIZ}catalogo_destilado.md#github:{i}",
        }

    declarado = re.search(
        r"-lgc \d+,(\d+)", _leer("/etc/systemd/system/atom-clock-lock.service")
    )
    cargadas = [
        m["sm_clk_mhz"]
        for m in muestras
        if (m.get("gpu_util_pct") or 0) >= 80 and m.get("sm_clk_mhz")
    ]
    maximo = max(cargadas) if cargadas else None
    cap = int(declarado.group(1)) if declarado else None
    if cap is None or maximo is None:
        acota = NOT_COLLECTED
    else:
        acota = (
            "si"
            if maximo >= cap - 50
            else f"NO: el maximo bajo carga ({maximo:g} MHz) queda a {cap - maximo:g} MHz del tope"
        )
    hw = cfg["watchdog_hw"]
    return [
        {
            **ent("D1", "cap de reloj de la GPU (nvidia-smi -lgc)"),
            "cap_declarado_mhz": cap or NOT_COLLECTED,
            "cap_confirmado_por_driver_en_ese_boot": cap_boot.get(
                "clock_cap_confirmado_por_driver"
            ),
            "maximo_sm_medido_bajo_carga_en_el_boot": maximo or NOT_COLLECTED,
            "el_cap_acota": acota,
        },
        {
            **ent("D2", "watchdog de servicio atado a PSI sostenido"),
            "estado": _cmd("systemctl", "is-active", "bb-usable.service"),
        },
        {
            **ent("D4", "watchdog hardware SBSA"),
            "estado": f"{hw['estado']}, timeout {hw['timeout_s']} s",
            "advertencia": "bootstatus=0 solo no prueba que dispare ante un cuelgue (DEBT-WATCHDOG-SIN-CONTROL-NEGATIVO-01)",
        },
        {
            **ent("D5", "uvm_global_oversubscription"),
            "uvm_global_oversubscription": cfg["uvm_global_oversubscription"],
        },
        {
            **ent("D13", "earlyoom"),
            "earlyoom": _cmd("systemctl", "is-active", "earlyoom.service"),
        },
        {
            **ent("D28", "journal persistente, netconsole y telemetria en disco"),
            "journal_persistente": "si" if Path("/var/log/journal").is_dir() else "no",
            "netconsole_cargado": "si"
            if Path("/sys/module/netconsole").exists()
            else "no",
            "telemetria_en": _cmd(
                "findmnt",
                "-no",
                "FSTYPE",
                "-T",
                str(Path.home() / ".local/share/blackbox"),
            ),
        },
        {
            "id": "no_observables_por_bb",
            "titulo": "PYTORCH_ALLOC_CONF, gpu_memory_utilization, largo de prompt, MTP: viven en el contenedor del workload",
            "estado": NOT_COLLECTED,
        },
    ]


def adjuntos_y_ruta(plat: dict[str, Any]) -> dict[str, Any]:
    """Que pide NVIDIA, en que orden y con que comando (dossier de foros F1-F3), y el estado de cada
    uno aqui. La ruta de soporte apunta a Atlas: lo dicho por el personal de NVIDIA es OFICIAL
    solo como declaracion en un foro, no como politica verificada con soporte de esta unidad."""
    sb = plat.get("secure_boot")
    return {
        "adjuntos_en_orden": [
            {
                "que": "nvidia-bug-report.log.gz (obligatorio, si cuelga se envia el parcial)",
                "comando": "sudo nvidia-bug-report.sh",
                "root": True,
                "estado": NOT_COLLECTED,
            },
            {
                "que": "bundle completo de dgx-spark-fieldiag (.tgz, no un solo log; incluye summary.json)",
                "comando": "sudo init 3; cd /opt/nvidia/dgx-spark-fieldiag; sudo ./partnerdiag --field",
                "root": True,
                "estado": f"NOT_COLLECTED; bloqueado: Secure Boot {sb} y fieldiag exige apagarlo (foro 358951 #12)"
                if sb != "disabled"
                else NOT_COLLECTED,
            },
            {
                "que": "journal del kernel del boot del incidente",
                "comando": "journalctl -k -b -1 -e",
                "root": False,
                "estado": "se escribe con --guarda (hostname sustituido por el nodo anonimo)",
            },
            {
                "que": "version de UEFI/EC/PD y BIOS",
                "comando": 'sudo dmidecode -t 45 | grep -A2 -E "UEFI|EC|PD|FLASH"; sudo dmidecode -t bios',
                "root": True,
                "estado": NOT_COLLECTED,
            },
            {
                "que": "sos report",
                "comando": "sudo sos report",
                "root": True,
                "estado": NOT_COLLECTED,
            },
            {
                "que": "numero de caso de soporte",
                "comando": "lo da NVIDIA u OEM",
                "root": False,
                "estado": NOT_COLLECTED,
            },
        ],
        "ruta_de_soporte": {
            "oem": plat.get("oem"),
            "donde_leerla": [
                ATLAS_RAIZ
                + "catalogo_destilado.md (respuestas oficiales: ids forum:E1..E5; patrones forum:G1..G10)",
                ATLAS_RAIZ + "dossier_foros_primera_pasada.md",
            ],
            "advertencia": "bb no guarda lo que dijo el personal de NVIDIA: se consulta en Atlas, y son declaraciones de foro no confirmadas con soporte de esta unidad",
        },
    }


# --------------------------------------------------------------------- el reporte
def seis_timestamps(
    ev: dict[str, Any],
    tele: list[dict[str, Any]],
    nvrm: dict[str, Any],
    sig_primero: float | None,
) -> list[dict[str, str]]:
    ultima = tele[-1] if tele else None
    vllm = [
        m
        for m in tele
        if m.get("vllm_num_requests_running") is not None and not m.get("vllm_ausente")
    ]
    fin = epoch_de(ultima["ts"]) if ultima else None
    ventana = [
        m
        for m in tele
        if fin is not None
        and (epoch_de(m["ts"]) or 0.0) >= fin - VENTANA_RELEVANTE_MIN * 60
    ]
    psi = next(
        (
            m
            for m in ventana
            if (m.get("psi_mem_full_avg10") or 0) >= rv.PSI_FULL_COLAPSO
        ),
        None,
    )
    nomem = nvrm.get("NV_ERR_NO_MEMORY", {}) if isinstance(nvrm, dict) else {}
    ult_nomem = epoch_de(nomem.get("ultima"))
    if ult_nomem is None:
        ts_nvrm = str(nomem.get("primera", NOT_COLLECTED))
    else:
        lag = (
            f", {round((fin - ult_nomem) / 60, 1)} min antes de la ultima muestra"
            if fin
            else ""
        )
        if fin is None:
            juicio = f"{NOT_COLLECTED}: sin telemetria valida no se puede decir si es relevante"
        elif fin - ult_nomem <= VENTANA_RELEVANTE_MIN * 60:
            juicio = "RELEVANTE"
        else:
            juicio = f"NO relevante: fuera de los {VENTANA_RELEVANTE_MIN} min previos"
        ts_nvrm = (
            f"{iso(ult_nomem)} ({juicio}{lag}; "
            f"{nomem.get('cuenta')} en el boot, la primera {nomem.get('primera')})"
        )
    return [
        {
            "evento": "Primer error de asignacion NVRM (NV_ERR_NO_MEMORY)",
            "ts": ts_nvrm,
            "fuente": "journal del kernel del boot",
            "incertidumbre": "journald hace fsync inmediato solo de CRIT o superior: los ultimos 7-14 s pueden faltar",
        },
        {
            "evento": "Primer stall de PSI o fallo de progreso del engine",
            "ts": iso(epoch_de(psi["ts"]))
            if psi
            else f"0 de {len(ventana)} muestras con PSI full avg10 >= {rv.PSI_FULL_COLAPSO:g} en los {VENTANA_RELEVANTE_MIN} min previos",
            "fuente": "atom_gpu_telemetry (5 s)",
            "incertidumbre": "+-5 s; progreso del engine NO se mide (solo peticiones en curso)",
        },
        {
            "evento": "Ultima respuesta correcta de aplicacion",
            "ts": iso(epoch_de(vllm[-1]["ts"])) if vllm else NOT_COLLECTED,
            "fuente": "ultima muestra con /metrics de vLLM respondiendo",
            "incertidumbre": "+-5 s; es una lectura de metricas, no una peticion de usuario",
        },
        {
            "evento": "Ultima muestra de telemetria / recibo externo",
            "ts": iso(epoch_de(ultima["ts"])) if ultima else NOT_COLLECTED,
            "fuente": "disco local (sin receptor externo: " + NOT_COLLECTED + ")",
            "incertidumbre": "+-5 s; el receptor externo faltante no permite acotar mas",
        },
        {
            "evento": "Accion del watchdog o reinicio manual",
            "ts": NOT_COLLECTED,
            "fuente": f"bootstatus del arranque siguiente = {ev.get('bootstatus_siguiente', NOT_COLLECTED)}",
            "incertidumbre": "bootstatus=0 solo, no dice que hizo el watchdog durante la falla; reinicio manual: lo anota el operador",
        },
        {
            "evento": "Siguiente boot / primera respuesta de aplicacion",
            "ts": iso(sig_primero),
            "fuente": "primera entrada del journal del boot siguiente",
            "incertidumbre": "+-1 s; la primera respuesta de aplicacion no se mide",
        },
    ]


def reporte(
    boot_idx: int | None = None, *, anotaciones: dict[str, str] | None = None
) -> dict[str, Any]:
    r = rv._journal("--list-boots", "-o", "json")
    if r.returncode != 0:
        raise SystemExit(
            f"COULD_NOT_RUN: journalctl --list-boots fallo: {r.stderr.strip()}"
        )
    boots = json.loads(r.stdout)
    terminados = boots[:-1]
    if boot_idx is None:
        boot_idx = terminados[-1]["index"]
    i = next((k for k, b in enumerate(terminados) if b["index"] == boot_idx), None)
    if i is None:
        raise SystemExit(
            f"COULD_NOT_RUN: el boot {boot_idx} no esta entre los terminados (vivo = {boots[-1]['index']})"
        )
    b = terminados[i]
    ev = rv.recoge(boots, i)
    v = rv.veredicto(ev)
    tele = telemetria_del_boot(b["boot_id"])
    muestras = [m for m in tele if m.get("evento") == "muestra"]
    nvrm = lineas_nvrm(b["index"])
    sig = boots[i + 1]["first_entry"] / 1e6
    fecha = (
        datetime.fromtimestamp(b["last_entry"] / 1e6, tz=timezone.utc)
        .astimezone()
        .strftime("%Y-%m-%d")
    )
    ultima_muestra = muestras[-1] if muestras else None
    plat = plataforma()
    return {
        "formato": "bb-incident/1",
        "resumen": {
            "incident_id": f"bb-{fecha}-{b['boot_id'][:8]}",
            "nodo_anonimizado": nodo_anonimo(),
            "boot_id": b["boot_id"],
            "veredicto": v["etiqueta"],
            "razones": v["razones"],
            "hueco_hasta_el_siguiente_boot_s": v["hueco_s"],
            "observacion_fisica_del_operador": {
                "quedo_apagado_hasta_pulsar_boton": (anotaciones or {}).get(
                    "boton", NOT_COLLECTED
                ),
                "estado": (anotaciones or {}).get("estado", NOT_COLLECTED),
                "led_de_encendido": (anotaciones or {}).get("led", NOT_COLLECTED),
                "ventiladores": (anotaciones or {}).get("ventiladores", NOT_COLLECTED),
                "ac_desconectada_para_recuperar": (anotaciones or {}).get(
                    "ac", NOT_COLLECTED
                ),
                "pantalla_sin_imagen": (anotaciones or {}).get(
                    "pantalla", NOT_COLLECTED
                ),
                "nota": "NVIDIA pregunta siempre: apagado completo, cuelgue o degradado; reinicio normal o desconexion de AC",
            },
            "fase_de_carga": NOT_COLLECTED
            if not ultima_muestra
            else f"no inferible con certeza; en la ultima muestra: {ultima_muestra.get('vllm_num_requests_running')} peticiones en curso, KV {round(100 * (ultima_muestra.get('vllm_kv_cache_usage_perc') or 0), 1)} %",
        },
        "plataforma": plat,
        "configuracion_al_generar_el_reporte": config_vigente(),
        "configuracion_registrada_por_el_journal_de_ese_boot": config_del_boot(
            b["index"]
        ),
        "seis_timestamps": seis_timestamps(ev, muestras, nvrm, sig),
        "ventana_previa_a_la_muerte": ventana_previa(muestras),
        "residencia_termica_del_boot": residencia_termica(muestras),
        "throttle_del_boot": throttle_del_boot(muestras),
        "nvrm_y_xid": nvrm,
        "silencio_del_kernel": silencio_del_kernel(b["index"], muestras),
        "firmas_en_el_journal": coincidencias_firmas(b["index"]),
        "mitigaciones_en_esta_maquina": estado_mitigaciones(
            muestras, config_vigente(), config_del_boot(b["index"])
        ),
        "exposicion_del_boot": exposicion(muestras),
        "captura": {
            "fuentes": [
                "journal del kernel (persistente)",
                "atom_gpu_telemetry.jsonl (5 s, disco local)",
                "bb sample (1 min)",
            ],
            "receptor_externo": NOT_COLLECTED,
            "pstore": "COULD_NOT_RUN (/sys/fs/pstore es root)",
            "huecos": v["could_not_run"],
            "bert_en_el_arranque_siguiente": bert_registro(boots[i + 1]["index"]),
        },
        "soporte": adjuntos_y_ruta(plat),
    }


def md(rep: dict[str, Any]) -> str:
    def bloque(titulo: str, d: Any) -> str:
        return f"## {titulo}\n\n```json\n{json.dumps(d, ensure_ascii=False, indent=2)}\n```\n"

    r = rep["resumen"]
    out = [
        f"# Incidente {r['incident_id']}\n",
        f"Formato `{rep['formato']}`; nodo `{r['nodo_anonimizado']}`; veredicto **{r['veredicto']}**.\n",
    ]
    out.append(bloque("Resumen del incidente", r))
    out.append(
        "## Seis timestamps separados\n\n| Evento | Timestamp (offset / UTC) | Fuente | Incertidumbre |\n|---|---|---|---|"
    )
    out.extend(
        f"| {t['evento']} | {t['ts']} | {t['fuente']} | {t['incertidumbre']} |"
        for t in rep["seis_timestamps"]
    )
    out.append("")
    for k, v in rep.items():
        if k in ("formato", "resumen", "seis_timestamps"):
            continue
        out.append(bloque(k.replace("_", " ").capitalize(), v))
    return "\n".join(out)


def journal_kernel_anonimo(idx: int, nodo: str, lineas: int = 300) -> str:
    """Ultimas lineas del journal del kernel del boot (`journalctl -k -b N -e`, lo primero que pide el
    personal de NVIDIA), con el hostname sustituido por el nodo anonimo."""
    k = rv._journal("-b", str(idx), "-k", "-e", "-n", str(lineas), "-o", "short-iso")
    if k.returncode != 0:
        return f"{COLLECTION_FAILED}: journalctl -b {idx} -k fallo\n"
    host = _cmd("hostname")
    return k.stdout if host == COLLECTION_FAILED else k.stdout.replace(host, nodo)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "boot",
        nargs="?",
        type=int,
        help="indice de `journalctl --list-boots` (def: el ultimo terminado)",
    )
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--ventana",
        nargs=2,
        type=float,
        metavar=("DESDE", "HASTA"),
        help="lineas de calor sostenido para `bb scan` (epoch UTC)",
    )
    ap.add_argument(
        "--guarda", action="store_true", help=f"escribe .md y .json en {SALIDA}"
    )
    for flag, opciones, ayuda in (
        (
            "--estado",
            ["apagado", "colgado", "degradado", "no_se"],
            "como estaba la maquina: apagada, colgada o degradada",
        ),
        ("--led", ["encendido", "apagado", "no_se"], "LED de encendido al llegar"),
        ("--ventiladores", ["girando", "detenidos", "no_se"], "ventiladores al llegar"),
        (
            "--ac",
            ["si", "no"],
            "hubo que desconectar la corriente (AC) para recuperarla",
        ),
        ("--pantalla", ["sin_imagen", "con_imagen"], "estado de la pantalla"),
    ):
        ap.add_argument(flag, choices=opciones, help=ayuda)
    ap.add_argument(
        "--boton",
        choices=["si", "no"],
        help="anotacion del operador: hubo que pulsar el boton de encendido",
    )
    a = ap.parse_args(argv)
    notas = {
        k: v
        for k, v in (
            ("boton", a.boton),
            ("estado", a.estado),
            ("led", a.led),
            ("ventiladores", a.ventiladores),
            ("ac", a.ac),
            ("pantalla", a.pantalla),
        )
        if v
    }
    if a.ventana:
        r = residencia_ventana(*a.ventana)
        print("\n".join(lineas_scan(r)))
        return 0 if r.get("estado") == "ok" else 2
    rep = reporte(a.boot, anotaciones=notas or None)
    texto = json.dumps(rep, ensure_ascii=False, indent=2) if a.json else md(rep)
    if a.guarda:
        SALIDA.mkdir(parents=True, exist_ok=True)
        base = SALIDA / rep["resumen"]["incident_id"]
        base.with_suffix(".md").write_text(md(rep), encoding="utf-8")
        base.with_suffix(".json").write_text(
            json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        idx = next(
            (
                x["index"]
                for x in json.loads(rv._journal("--list-boots", "-o", "json").stdout)
                if x["boot_id"] == rep["resumen"]["boot_id"]
            ),
            None,
        )
        if idx is not None:
            nodo = rep["resumen"]["nodo_anonimizado"]
            (SALIDA / f"{base.name}.kernel-ultimas-300.log").write_text(
                journal_kernel_anonimo(idx, nodo), encoding="utf-8"
            )
        print(f"escrito {base}.md, .json y .kernel-ultimas-300.log", file=sys.stderr)
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
