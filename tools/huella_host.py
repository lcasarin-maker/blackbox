#!/usr/bin/env python3
"""Huella de identidad y estado del host (un solo nodo GB10) con deteccion de cambios (interruptor `huella_host`).

Sirve para validar en vivo, sin intervenir, afirmaciones de hilos del foro de NVIDIA: version de SO, kernel, driver,
paquetes OTA, firmware del CX7, driver por interfaz de red (binding equivocado de Realtek tras reinicio), velocidad USB
(caida a 480 Mbps), fuentes apt (mezcla archive y ports en arm64), watchdog, GSP/GPU, pstore y clock lock.

Cada sonda devuelve un valor o la cadena "NOT_COLLECTED: <motivo>": nunca un valor inventado ni un vacio silencioso.
Todas son de solo lectura, sin sudo, con la raiz y el ejecutor inyectables. `diferencias` compara dos huellas y
no oculta una sonda que pierde o recupera su lectura. En `observar` registra "habria actuado" cuando algo cambio; en
`actuar` NO hay accion cableada: declara UNSUPPORTED.
Limite declarado: el watchdog reporta solo lo leido; quien es su propietario no se infiere.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tools import interruptores

NOMBRE = "huella_host"
NC = "NOT_COLLECTED"
PAQUETES_OTA = ("dgx-spark-ota-update-meta", "nvidia-spark-ota-check")

Correr = Callable[..., Any]


def _nc(motivo: str) -> str:
    return f"{NC}: {motivo}"


def es_nc(valor: Any) -> bool:
    return isinstance(valor, str) and valor.startswith(NC)


def _lee(ruta: Path) -> str | None:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _comando(correr: Correr, args: list[str]) -> str | None:
    """Salida estandar de un comando, o None si no corre, falla o excede 10 s."""
    try:
        r = correr(args, capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return str(r.stdout).strip()


def _hijos(directorio: Path, patron: str) -> list[Path]:
    return sorted(directorio.glob(patron))  # un directorio ausente da lista vacia


def sonda_os_release(raiz: Path, correr: Correr) -> Any:
    txt = _lee(raiz / "etc/os-release")
    if txt is None:
        return _nc("/etc/os-release ilegible")
    m = re.search(r'^PRETTY_NAME="?([^"\n]*)"?', txt, re.M)
    out: dict[str, str] = {"pretty_name": m.group(1) if m else _nc("sin PRETTY_NAME")}
    dgx = _lee(raiz / "etc/dgx-release")
    if dgx is not None:
        # el numero de serie no entra a la huella: el archivo viaja a evidencias y a posts publicos
        out["dgx_release"] = "\n".join(l for l in dgx.splitlines() if "SERIAL" not in l.upper())
    return out


def sonda_kernel(raiz: Path, correr: Correr) -> Any:
    return platform.release() or _nc("platform.release vacio")


def sonda_driver_nvidia(raiz: Path, correr: Correr) -> Any:
    txt = _lee(raiz / "proc/driver/nvidia/version")
    if not txt:
        return _nc("/proc/driver/nvidia/version ausente o vacio")
    return txt.splitlines()[0]


def sonda_ota(raiz: Path, correr: Correr) -> Any:
    out: dict[str, str] = {}
    for p in PAQUETES_OTA:
        v = _comando(correr, ["dpkg-query", "-W", "-f=${Version}", p])
        out[p] = v if v else _nc(f"{p} no instalado o dpkg-query no corre")
    return out


def sonda_firmware_cx7(raiz: Path, correr: Correr) -> Any:
    out: dict[str, dict[str, str]] = {}
    for fw in _hijos(raiz / "sys/class/infiniband", "*/fw_ver"):
        dev = fw.parent
        v = _lee(fw)
        psid = _lee(dev / "board_id")
        out[dev.name] = {"fw_ver": v or _nc("fw_ver ilegible"), "psid": psid or _nc("psid no expuesto")}
    return out or _nc("sin /sys/class/infiniband/*/fw_ver")


def sonda_driver_red(raiz: Path, correr: Correr) -> Any:
    out: dict[str, str] = {}
    for iface in _hijos(raiz / "sys/class/net", "*"):
        enlace = iface / "device/driver"
        if enlace.is_symlink():
            out[iface.name] = os.path.basename(os.readlink(enlace))
    return out or _nc("ninguna interfaz con device/driver")


def sonda_usb(raiz: Path, correr: Correr) -> Any:
    out: dict[str, dict[str, str]] = {}
    for s in _hijos(raiz / "sys/bus/usb/devices", "*/speed"):
        dev = s.parent
        out[dev.name] = {"speed_mbps": _lee(s) or _nc("speed ilegible"), "product": _lee(dev / "product") or _nc("sin product")}
    return out or _nc("sin /sys/bus/usb/devices/*/speed")


def _fuentes_apt(raiz: Path) -> list[Path]:
    base = raiz / "etc/apt"
    return [base / "sources.list", *_hijos(base / "sources.list.d", "*.sources"), *_hijos(base / "sources.list.d", "*.list")]


def sonda_apt(raiz: Path, correr: Correr) -> Any:
    textos = [t for t in (_lee(f) for f in _fuentes_apt(raiz)) if t is not None]
    if not textos:
        return _nc("sin fuentes apt legibles")
    todo = "\n".join(l for t in textos for l in t.splitlines() if not l.lstrip().startswith("#"))
    archive, ports = "archive.ubuntu.com" in todo, "ports.ubuntu.com" in todo
    return {"archive": archive, "ports": ports, "mezcla_archive_y_ports": archive and ports}


def sonda_watchdog(raiz: Path, correr: Correr) -> Any:
    sysfs: dict[str, dict[str, str]] = {}
    for wd in _hijos(raiz / "sys/class/watchdog", "*"):
        sysfs[wd.name] = {k: _lee(wd / k) or _nc(f"{k} ilegible") for k in ("identity", "state")}
    dev = [p.name for p in _hijos(raiz / "dev", "watchdog*")]
    if not sysfs and not dev:
        return _nc("sin /sys/class/watchdog ni /dev/watchdog*")
    return {"sysfs": sysfs, "dev": dev}


def _smi(correr: Correr, consulta: str, extra: str = "") -> str | None:
    return _comando(correr, ["nvidia-smi", f"--query-gpu={consulta}", f"--format=csv,noheader{extra}"])


def sonda_gpu(raiz: Path, correr: Correr) -> Any:
    smi = _smi(correr, "name,driver_version,vbios_version")
    pci = [p.name for p in _hijos(raiz / "sys/bus/pci/devices", "*") if (_lee(p / "vendor") or "") == "0x10de" and (_lee(p / "class") or "").startswith("0x03")]
    if not smi:
        return {"smi": _nc("nvidia-smi sin salida"), "pci_nvidia": pci}
    return {"smi": smi, "pci_nvidia": pci}


_GSP_LINEA = re.compile(r"GSP|NVRM.*(?:timeout|failed|RPC)", re.I)
_GSP_ERROR = re.compile(r"NVRM.*(?:timeout|failed|RPC)|GSP.*(?:timeout|fail|error)", re.I)


def sonda_gpu_gsp(raiz: Path, correr: Correr) -> Any:
    """Veredicto de tres estados que NO se infiere del PCI: `disponible` exige PCI display NVIDIA + respuesta de nvidia-smi + journal
    legible sin errores GSP; `PCI_SIN_GSP` si hay PCI y (nvidia-smi falla o hay errores GSP); `INDETERMINADO` en lo demas."""
    pci = [p.name for p in _hijos(raiz / "sys/bus/pci/devices", "*") if (_lee(p / "vendor") or "") == "0x10de" and (_lee(p / "class") or "").startswith("0x03")]
    smi = _smi(correr, "name,driver_version")
    diario = _comando(correr, ["journalctl", "-k", "-b", "--no-pager"])
    out: dict[str, Any] = {"pci_display_nvidia": pci, "smi": smi if smi else _nc("nvidia-smi sin respuesta")}
    if diario is None:
        out["kernel_gsp"] = _nc("journalctl -k -b no corre o sin permiso")
        errores: list[str] = []
    else:
        lineas = [l.split("kernel: ", 1)[-1] for l in diario.splitlines() if _GSP_LINEA.search(l)]  # sin el prefijo con el hostname
        errores = [l for l in lineas if _GSP_ERROR.search(l)]
        out["kernel_gsp"] = {"lineas": len(lineas), "errores": len(errores), "ultima": lineas[-1] if lineas else None}
    if not pci:
        out["veredicto"] = "INDETERMINADO"  # sin PCI no hay GPU que juzgar, aunque nvidia-smi conteste
    elif not smi or errores:
        out["veredicto"] = "PCI_SIN_GSP"
    elif diario is None:
        out["veredicto"] = "INDETERMINADO"  # nvidia-smi contesta, pero sin journal no se descartan errores GSP
    else:
        out["veredicto"] = "disponible"
    return out


def sonda_pstore(raiz: Path, correr: Correr) -> Any:
    out: dict[str, Any] = {}
    for rel in ("sys/fs/pstore", "var/lib/systemd/pstore"):
        d = raiz / rel
        try:
            out[rel] = len(list(d.iterdir()))
        except OSError:
            out[rel] = _nc(f"{rel} ausente o ilegible")
    return out


def sonda_clock_lock(raiz: Path, correr: Correr) -> Any:
    v = _smi(correr, "clocks.max.sm", ",nounits")
    return v if v else _nc("nvidia-smi sin salida")


# Archivos que trae el paquete de DGX OS (`dpkg -L nvidia-drm-options-modeset0` -> zz-nvidia-drm-override.conf; el de
# nvidia-graphics-drivers-kms.conf lo trae el paquete del driver). La ficha FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT NO define
# "unsupported override": solo pide detectar `modeset` fijado por un override ajeno al OTA y no retirarlo sin fuente oficial.
# Criterio operativo (de quien encarga esta sonda, no de NVIDIA): modeset/fbdev fijado en un archivo que no trae un paquete
# de NVIDIA, o en /proc/cmdline, es override propio. Declarado, no una verdad del fabricante.
ARCHIVOS_PAQUETE_NVIDIA = ("zz-nvidia-drm-override.conf", "nvidia-graphics-drivers-kms.conf")
_OPT_DRM = re.compile(r"^\s*options\s+nvidia[-_]drm\s+(.*)$", re.M)
_PARAM_DRM = re.compile(r"\b(modeset|fbdev)=(\w+)")
_CMD_DRM = re.compile(r"(?:^|\s)nvidia[-_]drm\.(modeset|fbdev)=(\w+)")


def sonda_drm_modeset(raiz: Path, correr: Correr) -> Any:
    """Valor DECLARADO (modprobe.d y cmdline) de nvidia-drm modeset/fbdev; el valor vivo de sysfs va aparte y puede ser NOT_COLLECTED."""
    decl: list[dict[str, str]] = []
    leidos = 0
    # /etc tapa a /usr/lib con el mismo nombre; modprobe aplica en orden de nombre y gana la ultima declaracion
    archivos: dict[str, Path] = {}
    for d in ("usr/lib/modprobe.d", "etc/modprobe.d"):
        for f in _hijos(raiz / d, "*.conf"):
            archivos[f.name] = f
    for nombre in sorted(archivos):
        txt = _lee(archivos[nombre])
        if txt is None:
            continue
        leidos += 1
        for linea in _OPT_DRM.findall(txt):
            decl += [{"param": k, "valor": v, "archivo": nombre} for k, v in _PARAM_DRM.findall(linea)]
    cmd = _lee(raiz / "proc/cmdline")
    if cmd is not None:
        leidos += 1
        decl += [{"param": k, "valor": v, "archivo": "/proc/cmdline"} for k, v in _CMD_DRM.findall(cmd)]  # el cmdline pesa mas que modprobe.d
    if not leidos:
        return _nc("sin modprobe.d ni /proc/cmdline legibles")
    out: dict[str, Any] = {}
    for param in ("modeset", "fbdev"):
        propias = [d for d in decl if d["param"] == param]
        out[param] = {"efectivo": propias[-1]["valor"] if propias else None, "fuente": propias[-1]["archivo"] if propias else None, "declaraciones": propias}
    vivo = _lee(raiz / "sys/module/nvidia_drm/parameters/modeset")
    out["sysfs_modeset"] = vivo if vivo else _nc("/sys/module/nvidia_drm/parameters/modeset ilegible o ausente")
    out["override_no_soportado"] = any(d["param"] in ("modeset", "fbdev") and d["archivo"] not in ARCHIVOS_PAQUETE_NVIDIA for d in decl)
    return out


def _clave_version(v: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", v))


def _initrd_ok(ruta: Path) -> bool | str:
    """True solo si existe y no esta vacio; False si falta; NOT_COLLECTED si no se pudo leer."""
    try:
        st = ruta.stat()
    except FileNotFoundError:
        return False
    except OSError as e:
        return _nc(f"{ruta}: {type(e).__name__}")
    return st.st_size > 0


def _modulos_nvidia(d: Path) -> list[Path]:
    return [*_hijos(d / "updates", "**/nvidia.ko*"), *_hijos(d / "kernel", "nvidia*/**/nvidia.ko*")]


def _secure_boot(raiz: Path, correr: Correr) -> bool | str:
    ilegibles: list[str] = []
    for var in _hijos(raiz / "sys/firmware/efi/efivars", "SecureBoot-*"):
        try:
            b = var.read_bytes()
        except OSError as e:
            ilegibles.append(f"{var.name}: {type(e).__name__}")
            continue
        if len(b) >= 5:  # 4 bytes de atributos + 1 de valor
            return b[4] == 1
    out = _comando(correr, ["mokutil", "--sb-state"])
    if out and "enabled" in out.lower():
        return True
    if out and "disabled" in out.lower():
        return False
    return _nc("ni efivars SecureBoot ni mokutil --sb-state dieron estado" + (f" (ilegibles: {'; '.join(ilegibles)})" if ilegibles else ""))


def _dkms_sin_firmar(raiz: Path, correr: Correr, ver: str, d: Path, sb: bool | str) -> bool | str:
    """True solo si dkms registra nvidia para este kernel, hay Secure Boot y algun .ko de updates/ no lleva firma."""
    if not (raiz / "usr/sbin/dkms").exists():
        return False  # sin dkms no hay modulos DKMS que firmar
    estado = _comando(correr, ["dkms", "status"])
    if estado is None:
        return _nc("dkms presente pero `dkms status` no corre")
    if not any("nvidia" in l and f", {ver}," in l for l in estado.splitlines()):
        return False
    if sb is False:
        return False
    if not isinstance(sb, bool):
        return sb
    for ko in _hijos(d / "updates", "**/nvidia*.ko*"):
        if ko.suffix != ".ko":
            return _nc(f"{ko.name} comprimido: firma no legible")
        try:
            if not ko.read_bytes().endswith(b"~Module signature appended~\n"):
                return True
        except OSError as e:
            return _nc(f"{ko.name}: {type(e).__name__}")
    return False


def sonda_arranque_tras_actualizacion(raiz: Path, correr: Correr) -> Any:
    """Por kernel instalado: initrd no vacio, modulos nvidia.ko y DKMS sin firmar bajo Secure Boot. `listo_para_reiniciar` mira solo al mas alto."""
    mods, boot = raiz / "lib/modules", raiz / "boot"
    vers = {d.name for d in _hijos(mods, "[0-9]*") if d.is_dir()} | {f.name[len("vmlinuz-"):] for f in _hijos(boot, "vmlinuz-*")}
    if not vers:
        return _nc("sin kernels en /lib/modules ni /boot/vmlinuz-*")
    sb = _secure_boot(raiz, correr)
    en_uso = platform.release()
    kernels: dict[str, dict[str, Any]] = {}
    for v in sorted(vers, key=_clave_version):
        kernels[v] = {
            "initrd": _initrd_ok(boot / f"initrd.img-{v}"),
            "modulos_nvidia": bool(_modulos_nvidia(mods / v)),
            "dkms_sin_firmar": _dkms_sin_firmar(raiz, correr, v, mods / v, sb),
            "kernel_en_uso": v == en_uso,
        }
    nuevo = list(kernels)[-1]
    k = kernels[nuevo]
    if k["initrd"] is False or k["modulos_nvidia"] is False or k["dkms_sin_firmar"] is True:
        listo: bool | str = False
    elif k["initrd"] is True and k["dkms_sin_firmar"] is False:
        listo = True
    else:
        listo = _nc("initrd o firma DKMS del kernel nuevo sin leer")
    return {"kernels": kernels, "kernel_nuevo": nuevo, "secure_boot": sb, "listo_para_reiniciar": listo}


# Recomendaciones de personal de NVIDIA en hilos del foro (evidencia: tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/
# ola2-etapa2-tramo1/<hilo>.json). Es un reporte de DIFERENCIAS, nunca una orden: ninguna esta verificada en esta maquina.
_CMD_IOMMU = re.compile(r"(?:^|\s)iommu\.passthrough=(\w+)")
_OPT_GWDT = re.compile(r"^\s*options\s+sbsa_gwdt\s+(.*)$", re.M)
_ACCION_GWDT = re.compile(r"\baction=(\w+)")
_DPMS = re.compile(r"DPMS is (Enabled|Disabled)", re.I)
_QUIEN_IOMMU = "personal de NVIDIA confirma el ajuste (post 5); el nombre no consta en la evidencia"


def _rec(actual: Any, recomendado: str, hilo: int, post: int, quien: str, cumple: bool | None, nota: str) -> dict[str, Any]:
    return {"actual": actual, "recomendado": recomendado, "hilo": hilo, "post": post, "quien": quien, "cumple": cumple, "nota": nota}


def _rec_iommu(raiz: Path) -> dict[str, Any]:
    nota = "Medido por un usuario en GX10 (RDMA CX7); riesgo declarado en el hilo: menos aislamiento por IOMMU, no evaluado. No es una orden."
    cmd = _lee(raiz / "proc/cmdline")
    if cmd is None:
        return _rec(_nc("/proc/cmdline ilegible"), "iommu.passthrough=1", 384436, 5, _QUIEN_IOMMU, None, nota)
    m = _CMD_IOMMU.findall(cmd)
    if not m:
        return _rec("ausente de /proc/cmdline", "iommu.passthrough=1", 384436, 5, _QUIEN_IOMMU, None, nota + " Ausente en cmdline: el valor efectivo depende del kernel y no se leyo.")
    return _rec(f"iommu.passthrough={m[-1]}", "iommu.passthrough=1", 384436, 5, _QUIEN_IOMMU, m[-1] == "1", nota)


def _rec_overcommit(raiz: Path) -> dict[str, Any]:
    nota = ("overcommit_memory=2 puede rechazar asignaciones de CUDA y contenedores que reservan mucha memoria virtual; el hilo no da cifras "
            "de prueba y el autor no lo probo. Medir con la carga real antes de adoptarlo. No es una orden.")
    act = {k: _lee(raiz / f"proc/sys/vm/{k}") for k in ("overcommit_memory", "overcommit_ratio")}
    rec = {"overcommit_memory": "2", "overcommit_ratio": "90"}
    actual: dict[str, str] = {k: v if v else _nc(f"/proc/sys/vm/{k} ilegible") for k, v in act.items()}
    if any(act[k] and act[k] != rec[k] for k in rec):
        cumple: bool | None = False  # una diferencia leida decide, aunque la otra no se lea
    elif any(not act[k] for k in rec):
        cumple = None
    else:
        cumple = True
    return _rec(actual, "vm.overcommit_memory=2 y vm.overcommit_ratio=90", 368536, 23, "personal de NVIDIA (Neill)", cumple, nota)


def _rec_sbsa(raiz: Path) -> dict[str, Any]:
    nota = ("action=1 hace panic del kernel en WS0: un wedge produce reinicio automatico y pstore quedo vacio en el hilo. Si el parametro no se expone "
            "en sysfs solo se ve lo DECLARADO en modprobe.d, no el valor vivo del modulo. No es una orden.")
    quien = "hilo de usuario; DGX OS lo trae en el paquete nvidia-sbsa-gwdt-options (post 3)"
    rec = "options sbsa_gwdt action=1"
    vivo = _lee(raiz / "sys/module/sbsa_gwdt/parameters/action")
    if vivo:
        return _rec(f"action={vivo} (vivo)", rec, 379959, 3, quien, vivo == "1", nota)
    decl: list[str] = []
    leidos = 0
    for d in ("usr/lib/modprobe.d", "etc/modprobe.d"):
        for f in _hijos(raiz / d, "*.conf"):
            txt = _lee(f)
            if txt is None:
                continue  # ponytail: un .conf ilegible no tumba la sonda, trigger: si importa cual, registrarlo
            leidos += 1
            for linea in _OPT_GWDT.findall(txt):
                decl += _ACCION_GWDT.findall(linea)
    if decl:
        return _rec(f"action={decl[-1]} (declarado en modprobe.d; el parametro no se expone en sysfs)", rec, 379959, 3, quien, decl[-1] == "1", nota)
    motivo = "parametro action no expuesto en /sys/module/sbsa_gwdt/parameters y sin declaracion en modprobe.d" if leidos else "action no expuesto en sysfs y sin modprobe.d legible"
    return _rec(_nc(motivo), rec, 379959, 3, quien, None, nota)


def _rec_dpms(correr: Correr) -> dict[str, Any]:
    nota = "Workaround del personal para ventiladores parados en idle/headless; sin fix y sin medir aqui. Solo lee `xset q`; no cambia nada. No es una orden."
    quien = "personal de NVIDIA (post 20; el nombre no consta en la evidencia)"
    rec = "DPMS deshabilitado (xset -dpms)"
    if not os.environ.get("DISPLAY"):
        return _rec(_nc("sin DISPLAY: no hay servidor X que consultar"), rec, 378945, 20, quien, None, nota)
    q = _comando(correr, ["xset", "q"])
    if q is None:
        return _rec(_nc("`xset q` no corre o falla"), rec, 378945, 20, quien, None, nota)
    m = _DPMS.search(q)
    if not m:
        return _rec(_nc("`xset q` sin linea 'DPMS is ...'"), rec, 378945, 20, quien, None, nota)
    return _rec(f"DPMS {m.group(1).lower()}", rec, 378945, 20, quien, m.group(1).lower() == "disabled", nota)


def sonda_recomendaciones_personal(raiz: Path, correr: Correr) -> Any:
    """Diferencias entre el estado actual y cuatro recomendaciones de personal de NVIDIA. `cumple` es None si no se pudo leer, jamas True por defecto."""
    return {"iommu_passthrough": _rec_iommu(raiz), "overcommit": _rec_overcommit(raiz), "sbsa_gwdt_action": _rec_sbsa(raiz), "dpms": _rec_dpms(correr)}


SONDAS: dict[str, Callable[[Path, Correr], Any]] = {
    "os_release": sonda_os_release,
    "kernel": sonda_kernel,
    "driver_nvidia": sonda_driver_nvidia,
    "ota": sonda_ota,
    "firmware_cx7": sonda_firmware_cx7,
    "driver_red": sonda_driver_red,
    "usb": sonda_usb,
    "apt": sonda_apt,
    "watchdog": sonda_watchdog,
    "gpu": sonda_gpu,
    "gpu_gsp": sonda_gpu_gsp,
    "pstore": sonda_pstore,
    "clock_lock": sonda_clock_lock,
    "drm_modeset": sonda_drm_modeset,
    "arranque_tras_actualizacion": sonda_arranque_tras_actualizacion,
    "recomendaciones_personal": sonda_recomendaciones_personal,
}


def recoge(raiz: Path = Path("/"), correr: Correr = subprocess.run) -> dict[str, Any]:
    """Una lectura de todas las sondas; una sonda que lanza se registra como NOT_COLLECTED, no tumba la huella."""
    out: dict[str, Any] = {}
    for nombre, f in SONDAS.items():
        try:
            out[nombre] = f(raiz, correr)
        except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as e:  # una sonda rota (lectura, formato, subproceso) no oculta las demas
            out[nombre] = _nc(f"{type(e).__name__}: {e}")
    return out


def diferencias(previo: dict[str, Any], ahora: dict[str, Any]) -> list[dict[str, Any]]:
    """Pura. Una entrada por sonda cuyo valor cambio; pasar a/desde NOT_COLLECTED lleva etiqueta propia."""
    out: list[dict[str, Any]] = []
    for sonda in sorted(set(previo) | set(ahora)):
        antes = previo.get(sonda, _nc("sonda ausente en la huella previa"))
        despues = ahora.get(sonda, _nc("sonda ausente en la huella actual"))
        if antes == despues:
            continue
        fila: dict[str, Any] = {"sonda": sonda, "antes": antes, "despues": despues}
        if es_nc(despues) and not es_nc(antes):
            fila["etiqueta"] = "perdida_de_lectura"
        elif es_nc(antes) and not es_nc(despues):
            fila["etiqueta"] = "lectura_recuperada"
        out.append(fila)
    return out


def _ruta_huella() -> Path:
    return Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox")) / "huella_host.json"


def paso(modo_actual: str, ahora: dict[str, Any] | None = None, estado: Path | None = None, directorio: Path | None = None) -> dict[str, Any] | None:
    """`off` no lee ni escribe. En `observar` guarda siempre la huella; registra un evento si es la primera o si hubo cambios."""
    if modo_actual == "off":
        return None
    ahora = recoge() if ahora is None else ahora
    estado = estado or _ruta_huella()
    try:
        previo = json.loads(estado.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previo = None
    estado.parent.mkdir(parents=True, exist_ok=True)
    estado.write_text(json.dumps(ahora, indent=1, ensure_ascii=False), encoding="utf-8")
    if not isinstance(previo, dict):
        ev: dict[str, Any] = {"modo": modo_actual, "primera": True, "habria_actuado": False}
    else:
        difs = diferencias(previo, ahora)
        if not difs:
            return None
        ev = {"modo": modo_actual, "primera": False, "habria_actuado": True, "diferencias": difs}
    if modo_actual == "actuar":
        ev["accion"] = "UNSUPPORTED: sin accion cableada; la huella solo observa"
    interruptores.registra(NOMBRE, ev, directorio)
    return ev


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="huella_host")
    ap.add_argument("--paso", action="store_true", help="un paso segun el interruptor huella_host (lo corre bb-huella.timer)")
    a = ap.parse_args(argv)
    if a.paso:
        paso(interruptores.modo(NOMBRE))
    else:
        print(json.dumps(recoge(), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
