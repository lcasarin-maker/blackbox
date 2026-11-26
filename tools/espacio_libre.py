#!/usr/bin/env python3
"""Vigilancia continua de espacio libre, inodos, tendencia y bloques fisicos (ATOM y equipo testigo).

Implementa `FEATURE-ESPACIO-LIBRE-DE-DISCO-ATOM-Y-DELL-01`:
- Mide espacio e inodos locales con `os.statvfs` (sin shell).
- Lee el estado de disco del equipo testigo desde `bb-estado-externo/1` (`/run/bb-estado-externo/estado_externo.json`).
- Calcula tendencia en dias hasta llenarse sobre una ventana sostenida (>= 3 muestras y >= 30 min).
- Evalua umbrales (85/92/96 % y < 7 dias) con histeresis y disciplina de rafaga unica.
- Recoge metricas fisicas de bloque (`/proc/diskstats`, `/sys/fs/cgroup/*/io.stat`, temperaturas NVMe en sysfs)
  y FDs `(deleted)` retenidos en el mismo dispositivo raiz (`st_dev == dev_raiz`), sin root.
- Calcula Top-10 de directorios de primer nivel con `st_blocks * 512` y deduplicacion de hardlinks.
- Publica `bb-estado-disco/1` de forma atomica y anexa a `$BLACKBOX_DATA/disco/espacio_libre.jsonl`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
from typing import Any, Callable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ESQUEMA_SERIE = "bb-espacio-libre/1"
ESQUEMA_ESTADO = "bb-estado-disco/1"
ESQUEMA_EXTERNO = "bb-estado-externo/1"

UMBRAL_AVISO_PCT = 85.0
UMBRAL_URGENTE_PCT = 92.0
UMBRAL_CRITICO_PCT = 96.0
UMBRAL_DIAS_RESTANTES = 7.0
HISTERESIS_PCT = 2.0

MIN_MUESTRAS_TENDENCIA = 3
MIN_VENTANA_TENDENCIA_S = 1800.0
ROTACION_MAX_BYTES = 16 * 1024 * 1024
FD_DELETED_MIN_BYTES = 100 * 1024 * 1024

ESTADO_EXTERNO_POR_DEFECTO = Path("/run/bb-estado-externo/estado_externo.json")
ESTADO_DISCO_RUN_POR_DEFECTO = Path("/run/bb-estado-disco/estado_disco.json")

_ORDEN_NIVEL = {"normal": 0, "aviso": 1, "urgente": 2, "critico": 3}


def _ahora_iso(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).isoformat(timespec="seconds")


def _data_dir_por_defecto() -> Path:
    env = os.environ.get("BLACKBOX_DATA")
    if env:
        return Path(env)
    return Path.home() / ".local" / "share" / "blackbox"


def _boot_id(proc_root: Path = Path("/proc")) -> str | None:
    try:
        txt = (proc_root / "sys" / "kernel" / "random" / "boot_id").read_text(encoding="utf-8").strip()
        return txt or None
    except OSError:
        return None


def _escribir_json_atomico(ruta: Path, payload: dict[str, Any]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(dir=ruta.parent, prefix=f".tmp-{ruta.name}-")
    try:
        os.chmod(tmp_name, 0o644)
        with os.fdopen(fd, "wb") as fh:
            fh.write(encoded)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, ruta)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _rotar_si_supera(ruta: Path, max_bytes: int = ROTACION_MAX_BYTES) -> None:
    try:
        if ruta.exists() and ruta.stat().st_size >= max_bytes:
            respaldo = ruta.with_name(ruta.name + ".1")
            os.replace(ruta, respaldo)
    except OSError:
        pass


def medir_volumen_local(
    ruta: Path,
    *,
    statvfs_fn: Callable[[Path], os.statvfs_result] = os.statvfs,
) -> dict[str, Any]:
    """Mide espacio e inodos de un volumen local via `statvfs`."""
    try:
        st = statvfs_fn(ruta)
    except OSError as exc:
        return {
            "ruta": str(ruta),
            "estado": "COULD_NOT_RUN",
            "motivo": f"{type(exc).__name__}: {exc}",
            "total_bytes": None,
            "usado_bytes": None,
            "libre_bytes": None,
            "uso_pct": None,
            "inodos_total": None,
            "inodos_usados": None,
            "inodos_libres": None,
            "inodos_pct": None,
        }

    if st.f_blocks <= 0 or st.f_frsize <= 0:
        return {
            "ruta": str(ruta),
            "estado": "COULD_NOT_RUN",
            "motivo": "statvfs devolvio bloques o tamano de bloque no positivos",
            "total_bytes": None,
            "usado_bytes": None,
            "libre_bytes": None,
            "uso_pct": None,
            "inodos_total": None,
            "inodos_usados": None,
            "inodos_libres": None,
            "inodos_pct": None,
        }

    total_bytes = int(st.f_frsize * st.f_blocks)
    libre_bytes = int(st.f_frsize * st.f_bavail)
    usado_bytes = max(0, total_bytes - int(st.f_frsize * st.f_bfree))
    uso_pct = round((usado_bytes / total_bytes) * 100.0, 2)

    inodos_total = int(st.f_files)
    inodos_libres = int(st.f_ffree)
    inodos_usados = max(0, inodos_total - inodos_libres)
    inodos_pct = round((inodos_usados / inodos_total) * 100.0, 2) if inodos_total > 0 else None

    return {
        "ruta": str(ruta),
        "estado": "OK",
        "motivo": None,
        "total_bytes": total_bytes,
        "usado_bytes": usado_bytes,
        "libre_bytes": libre_bytes,
        "uso_pct": uso_pct,
        "inodos_total": inodos_total,
        "inodos_usados": inodos_usados,
        "inodos_libres": inodos_libres,
        "inodos_pct": inodos_pct,
    }


def _parsear_ts(val: Any) -> float | None:
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    if isinstance(val, str) and val.strip():
        try:
            return dt.datetime.fromisoformat(val.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def leer_disco_externo(
    ruta_estado_externo: Path,
    *,
    ahora_ts: float,
    max_edad_s: float = 180.0,
) -> dict[str, Any]:
    """Lee la seccion `disco` de `bb-estado-externo/1` con reglas estrictas de frescura."""
    if not ruta_estado_externo.exists():
        return {"estado": "COULD_NOT_RUN", "motivo": f"ausente: {ruta_estado_externo}", "volumenes": []}
    try:
        doc = json.loads(ruta_estado_externo.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"estado": "COULD_NOT_RUN", "motivo": f"ilegible: {type(exc).__name__}: {exc}", "volumenes": []}

    if not isinstance(doc, dict) or doc.get("esquema") != ESQUEMA_EXTERNO:
        return {"estado": "COULD_NOT_RUN", "motivo": "esquema invalido en estado externo", "volumenes": []}
    if doc.get("vigente") is False:
        return {"estado": "COULD_NOT_RUN", "motivo": "estado externo marcado vigente=false", "volumenes": []}

    ts_ext = _parsear_ts(doc.get("ts"))
    if ts_ext is None:
        return {"estado": "COULD_NOT_RUN", "motivo": "ts ausente o invalido en estado externo", "volumenes": []}
    edad = ahora_ts - ts_ext
    if edad > max_edad_s:
        return {"estado": "COULD_NOT_RUN", "motivo": f"estado externo vencido ({edad:.0f}s > {max_edad_s:.0f}s)", "volumenes": []}
    if edad < -max_edad_s:
        return {"estado": "COULD_NOT_RUN", "motivo": "estado externo en el futuro", "volumenes": []}

    bloque_disco = doc.get("disco")
    if not isinstance(bloque_disco, dict) or bloque_disco.get("ok") is False:
        return {"estado": "COULD_NOT_RUN", "motivo": "bloque disco ausente o ok=false en estado externo", "volumenes": []}

    vols_raw = bloque_disco.get("volumenes")
    if not isinstance(vols_raw, list) or not vols_raw:
        return {"estado": "COULD_NOT_RUN", "motivo": "sin volumenes validos en estado externo", "volumenes": []}

    volumenes: list[dict[str, Any]] = []
    for v in vols_raw:
        if not isinstance(v, dict):
            continue
        tot = v.get("total_bytes")
        usa = v.get("usado_bytes")
        lib = v.get("libre_bytes")
        if not (isinstance(tot, (int, float)) and isinstance(usa, (int, float)) and isinstance(lib, (int, float))):
            continue
        if tot <= 0:
            continue
        volumenes.append(
            {
                "nombre": str(v.get("nombre") or v.get("ruta") or "externo"),
                "total_bytes": int(tot),
                "usado_bytes": int(usa),
                "libre_bytes": int(lib),
                "uso_pct": round((float(usa) / float(tot)) * 100.0, 2),
            }
        )

    if not volumenes:
        return {"estado": "COULD_NOT_RUN", "motivo": "volumenes externos malformados", "volumenes": []}

    return {"estado": "OK", "motivo": None, "volumenes": volumenes}


def calcular_tendencia(
    muestras: list[dict[str, Any]],
    *,
    min_muestras: int = MIN_MUESTRAS_TENDENCIA,
    min_ventana_s: float = MIN_VENTANA_TENDENCIA_S,
) -> dict[str, Any]:
    """Calcula tasa de llenado y dias hasta llenarse sobre muestras sostenidas."""
    validas: list[tuple[float, int, int]] = []
    vistos_ts: set[float] = set()
    for m in muestras:
        if not isinstance(m, dict) or m.get("estado") != "OK":
            continue
        ts_val = m.get("ts")
        usa = m.get("usado_bytes")
        lib = m.get("libre_bytes")
        if (
            isinstance(ts_val, (int, float))
            and not isinstance(ts_val, bool)
            and isinstance(usa, int)
            and not isinstance(usa, bool)
            and isinstance(lib, int)
            and not isinstance(lib, bool)
            and usa >= 0
            and lib >= 0
        ):
            t_f = float(ts_val)
            if t_f not in vistos_ts:
                vistos_ts.add(t_f)
                validas.append((t_f, usa, lib))

    validas.sort(key=lambda x: x[0])
    if len(validas) < min_muestras:
        return {
            "estado": "NOT_COLLECTED",
            "motivo": f"muestras insuficientes ({len(validas)} < {min_muestras})",
            "tasa_bytes_por_dia": None,
            "dias_hasta_llenarse": None,
            "ventana_s": 0.0,
        }

    dt_s = validas[-1][0] - validas[0][0]
    if dt_s < min_ventana_s:
        return {
            "estado": "NOT_COLLECTED",
            "motivo": f"ventana insuficiente ({dt_s:.0f}s < {min_ventana_s:.0f}s)",
            "tasa_bytes_por_dia": None,
            "dias_hasta_llenarse": None,
            "ventana_s": round(dt_s, 1),
        }

    t0 = validas[0][0]
    xs = [t - t0 for t, _, _ in validas]
    ys = [float(u) for _, u, _ in validas]
    n = float(len(xs))
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom <= 0:
        return {
            "estado": "NOT_COLLECTED",
            "motivo": "varianza temporal nula",
            "tasa_bytes_por_dia": None,
            "dias_hasta_llenarse": None,
            "ventana_s": round(dt_s, 1),
        }

    pendiente_seg = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    delta_neto = validas[-1][1] - validas[0][1]
    tasa_dia = pendiente_seg * 86400.0

    if pendiente_seg <= 0 or delta_neto <= 0:
        return {
            "estado": "OK",
            "motivo": None,
            "tasa_bytes_por_dia": round(tasa_dia, 2),
            "dias_hasta_llenarse": None,
            "ventana_s": round(dt_s, 1),
        }

    libre_final = float(validas[-1][2])
    dias = round(libre_final / tasa_dia, 2) if tasa_dia > 0 else None
    return {
        "estado": "OK",
        "motivo": None,
        "tasa_bytes_por_dia": round(tasa_dia, 2),
        "dias_hasta_llenarse": dias,
        "ventana_s": round(dt_s, 1),
    }


def _medir_dir_acotado(
    directorio: Path,
    *,
    root_dev: int,
    max_depth: int,
    vistos_hardlinks: set[tuple[int, int]],
    cnr: list[str],
) -> int:
    total = 0
    stack: list[tuple[Path, int]] = [(directorio, 0)]
    while stack:
        actual, prof = stack.pop()
        try:
            with os.scandir(actual) as it:
                entries = list(it)
        except OSError as exc:
            cnr.append(f"{actual}: {type(exc).__name__}: {exc}")
            continue

        for entry in entries:
            try:
                if entry.is_symlink():
                    continue
                st = entry.stat(follow_symlinks=False)
            except OSError as exc:
                cnr.append(f"{entry.path}: {type(exc).__name__}: {exc}")
                continue
            if st.st_dev != root_dev:
                continue
            if stat.S_ISDIR(st.st_mode):
                if prof < max_depth:
                    stack.append((Path(entry.path), prof + 1))
            elif stat.S_ISREG(st.st_mode):
                if st.st_nlink > 1:
                    clave = (st.st_dev, st.st_ino)
                    if clave in vistos_hardlinks:
                        continue
                    vistos_hardlinks.add(clave)
                total += int(getattr(st, "st_blocks", 0)) * 512
    return total


def top_directorios_primer_nivel(
    raices: list[Path],
    *,
    prev_mapa: dict[str, int] | None = None,
    max_depth_files: int = 2,
) -> dict[str, Any]:
    """Calcula tamano fisico (`st_blocks * 512`) y deltas de subdirectorios de primer nivel."""
    cnr: list[str] = []
    actual_mapa: dict[str, int] = {}
    vistos_hardlinks: set[tuple[int, int]] = set()

    for raiz in raices:
        if not raiz.exists():
            continue
        try:
            st_raiz = os.lstat(raiz)
        except OSError as exc:
            cnr.append(f"{raiz}: {type(exc).__name__}: {exc}")
            continue
        if stat.S_ISLNK(st_raiz.st_mode) or not stat.S_ISDIR(st_raiz.st_mode):
            continue
        root_dev = st_raiz.st_dev

        try:
            with os.scandir(raiz) as it:
                hijos = sorted(it, key=lambda e: e.name)
        except OSError as exc:
            cnr.append(f"{raiz}: {type(exc).__name__}: {exc}")
            continue

        for hijo in hijos:
            try:
                if hijo.is_symlink():
                    continue
                st_h = hijo.stat(follow_symlinks=False)
            except OSError as exc:
                cnr.append(f"{hijo.path}: {type(exc).__name__}: {exc}")
                continue
            if st_h.st_dev != root_dev:
                continue
            if stat.S_ISDIR(st_h.st_mode):
                tam = _medir_dir_acotado(
                    Path(hijo.path),
                    root_dev=root_dev,
                    max_depth=max_depth_files,
                    vistos_hardlinks=vistos_hardlinks,
                    cnr=cnr,
                )
                actual_mapa[hijo.path] = tam

    top_tamano = [
        {"ruta": k, "bytes": v}
        for k, v in sorted(actual_mapa.items(), key=lambda kv: kv[1], reverse=True)[:10]
    ]

    top_crecimiento: list[dict[str, Any]] = []
    if prev_mapa is not None:
        deltas = [
            {"ruta": k, "bytes": v, "delta_bytes": v - prev_mapa.get(k, 0)}
            for k, v in actual_mapa.items()
            if v - prev_mapa.get(k, 0) > 0
        ]
        deltas.sort(key=lambda item: item["delta_bytes"], reverse=True)
        top_crecimiento = deltas[:10]

    return {
        "mapa_bytes": actual_mapa,
        "top_tamano": top_tamano,
        "top_crecimiento": top_crecimiento,
        "could_not_run": cnr,
    }


def metricas_fisicas_bloque(
    *,
    proc_root: Path = Path("/proc"),
    sys_root: Path = Path("/sys"),
    dev_raiz: int | None = None,
) -> dict[str, Any]:
    """Lee diskstats, cgroup io.stat, temperaturas NVMe y FDs (deleted) retenidos sin root."""
    cnr: list[str] = []

    diskstats: dict[str, dict[str, int]] = {}
    ds_path = proc_root / "diskstats"
    try:
        for linea in ds_path.read_text(encoding="utf-8", errors="replace").splitlines():
            partes = linea.split()
            if len(partes) < 14:
                continue
            dev_name = partes[2]
            if dev_name.startswith("nvme"):
                diskstats[dev_name] = {
                    "read_bytes": int(partes[5]) * 512,
                    "write_bytes": int(partes[9]) * 512,
                    "io_ticks_ms": int(partes[12]),
                    "time_in_queue_ms": int(partes[13]),
                }
    except (OSError, ValueError) as exc:
        cnr.append(f"{ds_path}: {type(exc).__name__}: {exc}")

    slices_io: dict[str, dict[str, int]] = {}
    cg_base = sys_root / "fs" / "cgroup"
    for slice_name in ("user.slice", "docker.slice", "system.slice"):
        io_stat = cg_base / slice_name / "io.stat"
        if not io_stat.exists():
            continue
        try:
            r_tot = 0
            w_tot = 0
            for linea in io_stat.read_text(encoding="utf-8", errors="replace").splitlines():
                for tok in linea.split()[1:]:
                    if tok.startswith("rbytes="):
                        r_tot += int(tok.split("=", 1)[1])
                    elif tok.startswith("wbytes="):
                        w_tot += int(tok.split("=", 1)[1])
            slices_io[slice_name] = {"rbytes": r_tot, "wbytes": w_tot}
        except (OSError, ValueError) as exc:
            cnr.append(f"{io_stat}: {type(exc).__name__}: {exc}")

    nvme_temps_c: dict[str, float] = {}
    nvme_base = sys_root / "class" / "nvme"
    if nvme_base.exists():
        try:
            for ctrl in sorted(nvme_base.iterdir()):
                for hwmon in sorted(ctrl.glob("hwmon*")):
                    for t_in in sorted(hwmon.glob("temp*_input")):
                        lbl_path = t_in.with_name(t_in.name.replace("_input", "_label"))
                        label = lbl_path.read_text(encoding="utf-8").strip() if lbl_path.exists() else t_in.name
                        milli = int(t_in.read_text(encoding="utf-8").strip())
                        nvme_temps_c[f"{ctrl.name}:{label}"] = round(milli / 1000.0, 2)
        except (OSError, ValueError) as exc:
            cnr.append(f"{nvme_base}: {type(exc).__name__}: {exc}")

    deleted_fds: list[dict[str, Any]] = []
    pids_sin_permiso = 0
    if dev_raiz is not None and proc_root.exists():
        vistos_deleted: set[tuple[int, int]] = set()
        try:
            with os.scandir(proc_root) as it:
                pid_dirs = [e for e in it if e.name.isdigit()]
        except OSError as exc:
            cnr.append(f"{proc_root}: {type(exc).__name__}: {exc}")
            pid_dirs = []

        for pid_entry in pid_dirs:
            fd_dir = Path(pid_entry.path) / "fd"
            try:
                with os.scandir(fd_dir) as fd_it:
                    fd_entries = list(fd_it)
            except PermissionError:
                pids_sin_permiso += 1
                continue
            except OSError:
                continue

            for fd_entry in fd_entries:
                try:
                    target = os.readlink(fd_entry.path)
                except OSError:
                    continue
                if not target.endswith(" (deleted)"):
                    continue
                try:
                    st_fd = os.stat(fd_entry.path)
                except OSError:
                    continue
                if st_fd.st_dev != dev_raiz:
                    continue
                alloc = int(getattr(st_fd, "st_blocks", 0)) * 512
                if alloc < FD_DELETED_MIN_BYTES:
                    continue
                clave = (st_fd.st_dev, st_fd.st_ino)
                if clave in vistos_deleted:
                    continue
                vistos_deleted.add(clave)
                deleted_fds.append(
                    {
                        "pid": int(pid_entry.name),
                        "bytes": alloc,
                        "objetivo": target,
                    }
                )

    deleted_fds.sort(key=lambda item: item["bytes"], reverse=True)
    return {
        "diskstats": diskstats,
        "slices_io": slices_io,
        "nvme_temps_c": nvme_temps_c,
        "deleted_fds_retenidos": deleted_fds[:10],
        "pids_fd_sin_permiso": pids_sin_permiso,
        "could_not_run": cnr,
    }


def evaluar_nivel_y_aviso(
    uso_pct: float | None,
    dias_restantes: float | None,
    *,
    estado_previo: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evalua umbral (85/92/96 % o < 7 dias) con histeresis y rafaga unica."""
    if uso_pct is None:
        return {
            "nivel": "COULD_NOT_RUN",
            "debe_avisar": False,
            "nivel_avisado": (estado_previo or {}).get("nivel_avisado"),
            "aviso_dias_activo": bool((estado_previo or {}).get("aviso_dias_activo", False)),
            "motivo": "uso_pct ausente",
        }

    prev = estado_previo or {}
    nivel_prev = str(prev.get("nivel") or "normal")
    nivel_avisado = prev.get("nivel_avisado")
    aviso_dias_prev = bool(prev.get("aviso_dias_activo", False))

    if uso_pct >= UMBRAL_CRITICO_PCT:
        nivel_cap = "critico"
    elif uso_pct >= UMBRAL_URGENTE_PCT:
        nivel_cap = "urgente"
    elif uso_pct >= UMBRAL_AVISO_PCT:
        nivel_cap = "aviso"
    else:
        nivel_cap = "normal"

    # Histeresis para bajar de nivel
    if _ORDEN_NIVEL.get(nivel_cap, 0) < _ORDEN_NIVEL.get(nivel_prev, 0):
        if nivel_prev == "critico" and uso_pct > UMBRAL_CRITICO_PCT - HISTERESIS_PCT:
            nivel_cap = "critico"
        elif nivel_prev == "urgente" and uso_pct > UMBRAL_URGENTE_PCT - HISTERESIS_PCT:
            nivel_cap = "urgente"
        elif nivel_prev == "aviso" and uso_pct > UMBRAL_AVISO_PCT - HISTERESIS_PCT:
            nivel_cap = "aviso"

    aviso_por_dias = dias_restantes is not None and dias_restantes < UMBRAL_DIAS_RESTANTES
    nivel = "aviso" if (nivel_cap == "normal" and aviso_por_dias) else nivel_cap

    sube_capacidad = _ORDEN_NIVEL.get(nivel_cap, 0) > _ORDEN_NIVEL.get(str(nivel_avisado or "normal"), 0)
    entra_dias = aviso_por_dias and not aviso_dias_prev
    debe_avisar = bool((nivel_cap != "normal" and sube_capacidad) or entra_dias)

    nuevo_avisado = nivel_avisado
    if nivel_cap == "normal" and not aviso_por_dias:
        nuevo_avisado = None
    elif debe_avisar:
        nuevo_avisado = nivel_cap if _ORDEN_NIVEL.get(nivel_cap, 0) > 0 else "aviso"

    return {
        "nivel": nivel,
        "debe_avisar": debe_avisar,
        "nivel_avisado": nuevo_avisado,
        "aviso_dias_activo": aviso_por_dias,
        "motivo": None,
    }


def _cargar_serie(serie_path: Path) -> list[dict[str, Any]]:
    if not serie_path.exists():
        return []
    filas: list[dict[str, Any]] = []
    try:
        for linea in serie_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not linea.strip():
                continue
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            if isinstance(d, dict):
                filas.append(d)
    except OSError:
        return []
    return filas


def _enviar_aviso_ntfy(mensaje: str, *, ntfy_url_path: Path | None = None) -> tuple[bool, str]:
    url_file = ntfy_url_path or (Path.home() / ".config" / "blackbox" / "ntfy_url")
    if not url_file.exists():
        return False, "sin archivo ntfy_url"
    try:
        url = url_file.read_text(encoding="utf-8").strip()
        if not url:
            return False, "ntfy_url vacio"
        req = urllib.request.Request(url, data=mensaje.encode("utf-8"), method="POST")
        with urllib.request.urlopen(req, timeout=10):
            pass
        return True, "enviado"
    except OSError as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _enviar_notificacion_escritorio(titulo: str, cuerpo: str) -> None:
    try:
        subprocess.run(["notify-send", titulo, cuerpo], check=False, capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass


def ejecutar_muestra(
    *,
    raiz: Path = Path("/"),
    data_dir: Path | None = None,
    estado_externo: Path = ESTADO_EXTERNO_POR_DEFECTO,
    estado_salida: Path | None = None,
    raices_top: list[Path] | None = None,
    ahora_ts: float | None = None,
    enviar_aviso: bool = False,
    statvfs_fn: Callable[[Path], os.statvfs_result] = os.statvfs,
) -> dict[str, Any]:
    """Ejecuta una muestra completa de espacio libre, tendencia, fisica y alertas."""
    ts = time.time() if ahora_ts is None else float(ahora_ts)
    base = data_dir if data_dir is not None else _data_dir_por_defecto()
    disco_dir = base / "disco"
    disco_dir.mkdir(parents=True, exist_ok=True)
    serie_path = disco_dir / "espacio_libre.jsonl"
    estado_path = estado_salida if estado_salida is not None else (disco_dir / "estado_disco.json")

    local = medir_volumen_local(raiz, statvfs_fn=statvfs_fn)
    externo = leer_disco_externo(estado_externo, ahora_ts=ts)

    prev_serie = _cargar_serie(serie_path)
    prev_estado: dict[str, Any] | None = None
    if estado_path.exists():
        try:
            prev_estado = json.loads(estado_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prev_estado = None

    muestras_tend = [
        {
            "ts": r.get("ts"),
            "estado": (r.get("local") or {}).get("estado"),
            "usado_bytes": (r.get("local") or {}).get("usado_bytes"),
            "libre_bytes": (r.get("local") or {}).get("libre_bytes"),
        }
        for r in prev_serie[-200:]
    ]
    muestras_tend.append(
        {
            "ts": ts,
            "estado": local.get("estado"),
            "usado_bytes": local.get("usado_bytes"),
            "libre_bytes": local.get("libre_bytes"),
        }
    )
    tendencia = calcular_tendencia(muestras_tend)

    prev_mapa = (prev_estado or {}).get("top_directorios_mapa") if isinstance(prev_estado, dict) else None
    raices = raices_top if raices_top is not None else [Path.home(), Path("/srv"), Path("/var/log")]
    top_dirs = top_directorios_primer_nivel(raices, prev_mapa=prev_mapa if isinstance(prev_mapa, dict) else None)

    try:
        dev_raiz: int | None = os.stat(raiz).st_dev
    except OSError:
        dev_raiz = None
    fisica = metricas_fisicas_bloque(dev_raiz=dev_raiz)

    alerta = evaluar_nivel_y_aviso(
        local.get("uso_pct"),
        tendencia.get("dias_hasta_llenarse"),
        estado_previo=(prev_estado or {}).get("alerta") if isinstance(prev_estado, dict) else None,
    )

    if enviar_aviso and alerta.get("debe_avisar"):
        msg = (
            f"ATOM disco {alerta['nivel'].upper()}: {local.get('uso_pct')}% usado "
            f"({(local.get('libre_bytes') or 0) / (1024**3):.1f} GiB libres)"
        )
        if tendencia.get("dias_hasta_llenarse") is not None:
            msg += f", ETA {tendencia['dias_hasta_llenarse']} dias"
        _enviar_notificacion_escritorio("Blackbox Disco", msg)
        _enviar_aviso_ntfy(msg)

    cnr_list: list[str] = []
    if local.get("estado") != "OK":
        cnr_list.append(f"local: {local.get('motivo')}")
    if externo.get("estado") != "OK":
        cnr_list.append(f"externo: {externo.get('motivo')}")
    cnr_list.extend(top_dirs.get("could_not_run", []))
    cnr_list.extend(fisica.get("could_not_run", []))

    fila_serie = {
        "esquema": ESQUEMA_SERIE,
        "ts": ts,
        "ts_iso": _ahora_iso(ts),
        "boot_id": _boot_id(),
        "local": local,
        "externo_estado": externo.get("estado"),
        "tendencia": tendencia,
        "alerta": {"nivel": alerta["nivel"], "debe_avisar": alerta["debe_avisar"]},
    }
    _rotar_si_supera(serie_path)
    with serie_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(fila_serie, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())

    estado_doc = {
        "esquema": ESQUEMA_ESTADO,
        "ts": ts,
        "ts_iso": _ahora_iso(ts),
        "boot_id": fila_serie["boot_id"],
        "local": local,
        "externo": externo,
        "tendencia": tendencia,
        "alerta": alerta,
        "top_tamano": top_dirs["top_tamano"],
        "top_crecimiento": top_dirs["top_crecimiento"],
        "top_directorios_mapa": top_dirs["mapa_bytes"],
        "fisica": fisica,
        "could_not_run": cnr_list,
        "could_not_run_count": len(cnr_list),
    }
    _escribir_json_atomico(estado_path, estado_doc)

    if estado_salida is None and ESTADO_DISCO_RUN_POR_DEFECTO.parent.exists() and os.access(ESTADO_DISCO_RUN_POR_DEFECTO.parent, os.W_OK):
        try:
            _escribir_json_atomico(ESTADO_DISCO_RUN_POR_DEFECTO, estado_doc)
        except OSError:
            pass

    return estado_doc


def _formatear_texto(doc: dict[str, Any]) -> str:
    loc = doc["local"]
    lineas = [f"=== Blackbox Disco ({doc['ts_iso']}) | nivel={doc['alerta']['nivel']} ==="]
    if loc["estado"] == "OK":
        gb_u = loc["usado_bytes"] / (1024**3)
        gb_t = loc["total_bytes"] / (1024**3)
        gb_l = loc["libre_bytes"] / (1024**3)
        lineas.append(
            f"ATOM {loc['ruta']}: {gb_u:.1f}/{gb_t:.1f} GiB ({loc['uso_pct']}% usado, {gb_l:.1f} GiB libres) | "
            f"inodos {loc['inodos_usados']}/{loc['inodos_total']} ({loc['inodos_pct']}%)"
        )
    else:
        lineas.append(f"ATOM {loc['ruta']}: COULD_NOT_RUN ({loc['motivo']})")

    tend = doc["tendencia"]
    if tend["estado"] == "OK" and tend["dias_hasta_llenarse"] is not None:
        gb_d = tend["tasa_bytes_por_dia"] / (1024**3)
        lineas.append(f"Tendencia: +{gb_d:.2f} GiB/dia -> llenado estimado en {tend['dias_hasta_llenarse']} dias")
    else:
        lineas.append(f"Tendencia: {tend['estado']} ({tend.get('motivo') or 'estable/bajando'})")

    ext = doc["externo"]
    lineas.append(f"Equipo testigo: {ext['estado']}" + (f" ({ext['motivo']})" if ext.get("motivo") else ""))
    for v in ext.get("volumenes", []):
        lineas.append(f"  - {v['nombre']}: {v['uso_pct']}% usado ({v['libre_bytes'] / (1024**3):.1f} GiB libres)")

    if doc["top_crecimiento"]:
        lineas.append("Top crecimiento reciente:")
        for item in doc["top_crecimiento"][:5]:
            lineas.append(f"  +{item['delta_bytes'] / (1024**2):.1f} MiB  {item['ruta']}")
    elif doc["top_tamano"]:
        lineas.append("Top directorios por peso:")
        for item in doc["top_tamano"][:5]:
            lineas.append(f"  {item['bytes'] / (1024**3):.2f} GiB  {item['ruta']}")

    lineas.append(f"could_not_run: {doc['could_not_run_count']}")
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="Imprime salida JSON estructurada")
    ap.add_argument("--raiz", type=Path, default=Path("/"), help="Ruta raiz a medir con statvfs")
    ap.add_argument("--data-dir", type=Path, default=None, help="Directorio BLACKBOX_DATA")
    ap.add_argument("--estado-externo", type=Path, default=ESTADO_EXTERNO_POR_DEFECTO)
    ap.add_argument("--estado-salida", type=Path, default=None)
    ap.add_argument("--enviar-aviso", action="store_true", help="Envia notify-send y ntfy si debe_avisar")
    args = ap.parse_args(argv)

    doc = ejecutar_muestra(
        raiz=args.raiz,
        data_dir=args.data_dir,
        estado_externo=args.estado_externo,
        estado_salida=args.estado_salida,
        enviar_aviso=args.enviar_aviso,
    )
    if args.json:
        sys.stdout.write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(_formatear_texto(doc))
    return 0 if doc["local"]["estado"] == "OK" else 2


if __name__ == "__main__":
    sys.exit(main())
