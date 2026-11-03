"""`sudo panic`: un solo comando que regresa la maquina al ultimo punto de restauracion sano (docs/PANIC.md).

Pedido de Luis (2026-11-03): "sudo panic = 1 solo comando que haga lo que sea necesario para salir del
problema ... como un restore point en un videojuego". Sustituye al boton rojo (`sudo rojo`): la suspension
sigue siendo tools/boton_rojo.py y es UNO de los pasos.

    sudo panic                  todo lo de abajo
    sudo panic restaura         deshace SOLO la suspension (motor y contenedores GPU: `restaura todo si`);
                                el kernel lo cambia el humano

Orden: primero lo que PERSISTE y es rapido, despues lo vivo, al final lo lento. Sin red. No reinicia.
  (a) elige el punto valido mas reciente (tools/punto_restauracion.py) y comprueba sus sha256, que su kernel,
      sus modulos y su entrada de GRUB existen; uno que no cuadra queda `invalido` y no se elige;
  (c1) devuelve a su estado del punto los archivos de /etc/default/grub y /etc/default/grub.d que difieran
      (el actual se respalda antes en /var/lib/blackbox/restore/panic-<fecha>/; lo anadido despues del
      punto no se toca, se nombra);
  (b) fija el kernel del punto como arranque: `grub-set-default <submenu>><entrada>` si GRUB_DEFAULT
      efectivo es `saved` (capa grub-default-guardado); si no, `grub-reboot` (solo el proximo arranque) y lo
      dice;
  (e) `bb_intentos=0` y `bb_punto_entry=<entrada>` en el grubenv (contador del autoarmado);
  (d) la suspension de tools/boton_rojo.py (todo lo no-KEEP, contenedores con GPU);
  (c2) si (c1) cambio algo: grub-mkconfig a un archivo aparte, grub-script-check, la entrada del punto
      presente, y solo entonces sustituye a /boot/grub/grub.cfg (el viejo queda en el respaldo);
  (f) imprime que hizo, que no pudo (COULD_NOT_RUN) y no reinicia.
Sin punto valido hace (d) igual, pone el contador a 0 y dice "COULD_NOT_RUN: sin punto de restauracion".

Se instala como /usr/local/sbin/panic (bin/panic), que ejecuta la COPIA root-owned de este archivo en
/usr/local/lib/blackbox/tools/ con `python3 -I`; nunca el repo. Pruebas: BB_ROJO_RAIZ y shims en PATH
(tests/test_panic.py). rc: 0 todo hecho; 1 hubo could_not_run; 2 no pudo empezar o uso equivocado.
"""

from __future__ import annotations

import datetime as dt
import os
import shutil
import sys
import time
from pathlib import Path

if __package__ in (None, ""):  # `python3 -I .../tools/panic.py`: -I no pone el directorio en sys.path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import boton_rojo as br  # noqa: E402
from tools import punto_restauracion as pr  # noqa: E402

T_MKCONFIG = 300
# Lo que se instala en /usr/local/lib/blackbox/tools/ (docs/PANIC.md, Instalacion): panic, punto_restauracion y
# todo lo que importan, transitivamente (reboot_verdict arrastra cinco modulos), mas la lista KEEP.
# tests/test_panic.py comprueba que con exactamente esto `python3 -I` importa, y que sin uno no.
INSTALA = ("tools/__init__.py", "tools/panic.py", "tools/punto_restauracion.py", "tools/boton_rojo.py",
           "tools/modulo_nvidia_registro.py", "tools/reboot_verdict.py", "tools/etapas_arranque.py",
           "tools/hallazgo.py", "tools/medidor_energia.py", "tools/observador_ping.py", "tools/ultimo_aliento.py",
           "tools/interruptores.py", "adopted/boton-rojo-keep.txt")
USO = "uso: sudo panic            (regresa al punto de restauracion y suspende)\n" \
      "     sudo panic restaura   (deshace solo la suspension; motor: sudo panic restaura todo si)"
Dic = pr.Dic


def _de_grub_default(ruta: str) -> bool:
    return ruta == "/etc/default/grub" or ruta.startswith("/etc/default/grub.d/")


def restaura_archivos(d: Path, p: Dic, respaldo: Path, cnr: list[str]) -> list[str]:
    """(c1) Cada archivo de /etc/default/grub* del punto que hoy difiere vuelve a su copia. Devuelve los cambiados."""
    cambiados: list[str] = []
    del_punto = {a["ruta"] for a in p["archivos"]}
    for a in p["archivos"]:
        if not _de_grub_default(a["ruta"]):
            continue
        actual = pr.en_raiz(a["ruta"])
        if br.sha256(actual) == a["sha256"] and br.modo(actual) == a["modo"]:
            continue
        copia = d / a["copia"]
        if br.sha256(copia) != a["sha256"]:
            cnr.append(f"{a['ruta']}: la copia del punto no tiene su sha256; no se toca")
            continue
        try:
            if os.path.lexists(actual):
                (respaldo / a["ruta"].lstrip("/")).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(actual, respaldo / a["ruta"].lstrip("/"), follow_symlinks=False)
            actual.parent.mkdir(parents=True, exist_ok=True)
            tmp = actual.with_name(actual.name + ".bb-panic")
            shutil.copyfile(copia, tmp)
            os.chmod(tmp, int(a["modo"], 8))
            os.replace(tmp, actual)
        except OSError as e:
            cnr.append(f"{a['ruta']}: no se pudo devolver ({e})")
            continue
        cambiados.append(a["ruta"])
    for x in sorted(pr.en_raiz("/etc/default/grub.d").glob("*")):
        ruta = f"/etc/default/grub.d/{x.name}"
        if x.is_file() and ruta not in del_punto:
            print(f"AVISO: {ruta} no esta en el punto (anadido despues): no se toca")
    return cambiados


def fija_kernel(ej: br.Ejecutor, cnr: list[str], ruta_id: str) -> str:
    """(b) El kernel del punto como arranque por defecto; si GRUB_DEFAULT no es saved, solo el proximo."""
    boot = str(pr.en_raiz("/boot"))
    efectivo = pr.grub_default_efectivo()
    if efectivo == "saved":
        rc, _, err = ej.corre(["grub-set-default", f"--boot-directory={boot}", ruta_id], pr.T_CMD)
        if rc == 0:
            return f"grub-set-default {ruta_id} (GRUB_DEFAULT=saved: queda fijo)"
        cnr.append(f"grub-set-default: {br.motivo_de(rc, err)}")
        return "grub-set-default FALLO"
    rc, _, err = ej.corre(["grub-reboot", f"--boot-directory={boot}", ruta_id], pr.T_CMD)
    cnr.append(f"GRUB_DEFAULT efectivo es {efectivo!r}, no saved: el kernel del punto vale SOLO para el proximo "
               "arranque (grub-reboot); para que quede fijo: aplica la capa grub-default-guardado")
    if rc == 0:
        return f"grub-reboot {ruta_id} (solo el proximo arranque)"
    cnr.append(f"grub-reboot: {br.motivo_de(rc, err)}")
    return "grub-reboot FALLO"


def regenera_grub(ej: br.Ejecutor, cnr: list[str], entry_id: str, respaldo: Path) -> str:
    """(c2) grub.cfg nuevo aparte, validado, y solo entonces en su sitio. El viejo queda en el respaldo."""
    cfg = pr.grub_cfg_ruta()
    nuevo = cfg.with_name("grub.cfg.bb-panic")
    rc, _, err = ej.corre(["grub-mkconfig", "-o", str(nuevo)], T_MKCONFIG)
    if rc != 0:
        cnr.append(f"grub-mkconfig: {br.motivo_de(rc, err)}; grub.cfg no se toco")
        return "update-grub FALLO"
    rc, _, err = ej.corre(["grub-script-check", str(nuevo)], pr.T_CMD)
    if rc != 0:
        cnr.append(f"grub-script-check rechaza el grub.cfg nuevo ({br.motivo_de(rc, err)}); grub.cfg no se toco")
        return "update-grub RECHAZADO"
    texto = nuevo.read_text(encoding="utf-8", errors="replace")
    if entry_id not in {e["id"] for e in pr.entradas_grub(texto)}:
        cnr.append(f"el grub.cfg nuevo no tiene la entrada {entry_id}; grub.cfg no se toco")
        return "update-grub RECHAZADO"
    try:
        (respaldo / "boot/grub").mkdir(parents=True, exist_ok=True)
        if cfg.exists():
            shutil.copy2(cfg, respaldo / "boot/grub/grub.cfg")
            shutil.copymode(cfg, nuevo)
        os.replace(nuevo, cfg)
    except OSError as e:
        cnr.append(f"no se pudo sustituir grub.cfg: {e}")
        return "update-grub FALLO"
    return "grub.cfg regenerado y validado (grub-script-check, entrada del punto presente)"


def panic(keep: Path, motivo: str) -> int:
    t0 = time.monotonic()
    ej = br.Ejecutor()
    cnr: list[str] = []
    hecho: list[str] = []
    print("== sudo panic: regreso al punto de restauracion")
    puntos = pr.revisa_puntos(cnr)  # (a)
    for d, p in puntos:
        if p.get("invalido"):
            print(f"  punto {d.name}: INVALIDO -- {p['invalido']['motivo']}")
    v = pr.validos(puntos)
    respaldo = pr.restore_dir() / f"panic-{dt.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}"
    cambiados: list[str] = []
    punto: tuple[Path, Dic] | None = v[0] if v else None
    if punto is None:
        cnr.insert(0, "COULD_NOT_RUN: sin punto de restauracion valido en /var/lib/blackbox/restore: el kernel y "
                      "GRUB NO se tocan; se suspende igual")
        if pr.grubenv_cambia(ej, cnr, "set", "bb_intentos=0"):
            hecho.append("bb_intentos=0 en el grubenv")
    else:
        d, p = punto
        print(f"  punto elegido: {d.name}  kernel {p['kernel']}  entrada {p['grub']['ruta_id']}")
        cambiados = restaura_archivos(d, p, respaldo, cnr)  # (c1)
        hecho += [f"devuelto {r} (el anterior en {respaldo})" for r in cambiados]
        hecho.append(fija_kernel(ej, cnr, p["grub"]["ruta_id"]))  # (b)
        if pr.grubenv_cambia(ej, cnr, "set", "bb_intentos=0", f"bb_punto_entry={p['grub']['ruta_id']}"):  # (e)
            hecho.append("bb_intentos=0 y bb_punto_entry en el grubenv")
    rc_s = br.suspende(keep, motivo)  # (d)
    if rc_s != 0:
        cnr.append(f"suspension: rc={rc_s} (su COULD_NOT_RUN va impreso arriba)")
    else:
        hecho.append("suspension completa (manifiesto impreso arriba)")
    if punto is not None and cambiados:  # (c2) lo unico lento, al final y solo si hace falta
        hecho.append(regenera_grub(ej, cnr, punto[1]["grub"]["entry_id"], respaldo))
    print("\n== sudo panic: resumen")
    for h in hecho:
        print(f"  HECHO: {h}")
    print(f"  COULD_NOT_RUN: {len(cnr)}")
    for c in cnr:
        print(f"    {c}")
    print(f"  duracion: {time.monotonic() - t0:.2f} s")
    print("  NO se reinicio. Cuando quieras: sudo reboot   (deshacer la suspension: sudo panic restaura)")
    return 1 if cnr else 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if os.geteuid() != 0 and not os.environ.get("BB_ROJO_RAIZ"):
        print("COULD_NOT_RUN: necesita root: sudo panic")
        return 2
    if not args:
        return panic(br.KEEP, "sudo panic")
    if args[0] == "restaura" and args[1:] in ([], ["todo"], ["todo", "si"]):
        return br.restaura("todo" in args, "si" in args)
    print(USO)
    return 2


if __name__ == "__main__":
    sys.exit(main())
