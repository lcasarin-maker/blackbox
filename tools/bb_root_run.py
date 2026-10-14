#!/usr/bin/python3 -I
"""bb-root-run: corre como root SOLO scripts sellados por hash (voto de Luis 2026-10-14).

Forma instalada: `/usr/local/sbin/bb-root-run` (copia root:root 0755 de este fichero),
invocada como `sudo bb-root-run <nombre>`. Solo stdlib: corre con `python3 -I`, que no
mete el directorio del script en sys.path ni lee PYTHON* del entorno.

Reglas, cada una con su control negativo en tests/test_bb_root_run.py:
- argv es exactamente UN nombre que casa ^[a-z0-9][a-z0-9-]{0,40}$ (fullmatch: un
  salto de linea final no cuela). El glob de sudoers no puede acotar esto, asi que la
  guarda vive aqui.
- el nombre es una clave del manifiesto root-owned ({nombre: {file, sha256,
  descripcion, timeout?}}); el manifiesto y su directorio deben ser del uid de
  confianza (root) y no escribibles por grupo ni otros.
- los bytes del script se leen UNA vez (O_NOFOLLOW, fichero regular, sin symlink);
  su sha256 se compara con el manifiesto; si coincide, son ESOS bytes los que se
  copian a un directorio 0700 creado por el runner bajo un padre root-only y se
  ejecutan desde ahi con /bin/bash. Reescribir el repo despues del hash no cambia
  lo que corre: no hay carrera entre comprobar y usar.
- shebang en lista blanca: `#!/usr/bin/env bash` o `#!/bin/bash`; el interprete lo
  elige el runner (/bin/bash), nunca una busqueda en PATH.
- entorno construido desde cero (PATH fijo, LC_ALL, HOME, SUDO_UID numerico): no
  pasa LD_*, PYTHON*, BASH_ENV ni BASH_FUNC_*.
- timeout 120 s por defecto, override por entrada con techo 600; al vencer se mata
  el grupo de procesos entero y el rc es 124.
- salida (stdout+stderr) a `out_dir/<nombre>-<ts UTC>.txt` 0644 y eco; rc propagado.
- cada invocacion deja lineas JSON en `out_dir/auditoria.jsonl` (rechazo, o
  inicio + fin) con nombre, sha256, rc, ts y el uid llamante (SUDO_UID).
- todo rechazo sale con rc 3 y un mensaje que dice por que.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import pwd
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import BinaryIO, Mapping, TypeGuard

MANIFEST = "/etc/bb-root-run/manifest.json"
# Relativo al home del llamante (SUDO_UID). No es frontera de seguridad: lo que corre lo
# decide el sha256 del manifiesto, no el sitio de donde se lee.
SCRIPTS_REL = "projects/blackbox/adopted/root-scripts"
OUT_DIR = "/var/lib/bb-root-run"
TMP_PARENT = "/run"  # root:root 0755: el usuario no puede renombrar lo que se crea dentro

RECHAZO = 3
RC_TIMEOUT = 124
TIMEOUT_DEFECTO = 120
TIMEOUT_TECHO = 600
MAX_BYTES = 256 * 1024

NOMBRE = re.compile(r"[a-z0-9][a-z0-9-]{0,40}")
FICHERO = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}")
SHA256 = re.compile(r"[0-9a-f]{64}")
SHEBANGS = (b"#!/usr/bin/env bash", b"#!/bin/bash")
BASH = "/bin/bash"
PATH_FIJO = "/usr/sbin:/usr/bin:/sbin:/bin"


class Rechazo(Exception):
    """Algo no cumple las reglas: no se ejecuta nada y el rc es 3."""


@dataclass(frozen=True)
class Entrada:
    file: str
    sha256: str
    timeout: int


@dataclass
class Opciones:
    """Lo inyectable para probar sin root. Los valores por defecto son los de produccion."""

    trusted_uid: int = 0
    tmp_parent: str = TMP_PARENT
    environ: Mapping[str, str] | None = None
    salida: BinaryIO | None = None


def nombre_valido(name: object) -> TypeGuard[str]:
    return isinstance(name, str) and NOMBRE.fullmatch(name) is not None


def confiable(st: os.stat_result, trusted_uid: int, que: str) -> None:
    if st.st_uid != trusted_uid:
        raise Rechazo(f"{que}: su dueno es uid {st.st_uid}, se exige uid {trusted_uid}")
    if st.st_mode & 0o022:
        raise Rechazo(f"{que}: escribible por grupo u otros (modo {stat.S_IMODE(st.st_mode):04o})")


def directorio_confiable(path: str, trusted_uid: int, que: str) -> None:
    try:
        st = os.lstat(path)
    except OSError as e:
        raise Rechazo(f"{que} {path}: no se puede leer ({e.strerror})") from e
    if not stat.S_ISDIR(st.st_mode):
        raise Rechazo(f"{que} {path}: no es un directorio (o es un symlink)")
    confiable(st, trusted_uid, f"{que} {path}")


def leer_una_vez(path: str, que: str, trusted_uid: int | None = None) -> bytes:
    """Lee un fichero regular sin seguir symlinks, una sola vez, con techo de tamano."""
    try:
        if stat.S_ISLNK(os.lstat(path).st_mode):
            raise Rechazo(f"{que} {path}: es un symlink")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError as e:
        raise Rechazo(f"{que} {path}: no se puede abrir ({e.strerror})") from e
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise Rechazo(f"{que} {path}: no es un fichero regular")
        if trusted_uid is not None:
            confiable(st, trusted_uid, f"{que} {path}")
        trozos: list[bytes] = []
        total = 0
        while total <= MAX_BYTES:
            b = os.read(fd, 65536)
            if not b:
                break
            trozos.append(b)
            total += len(b)
    finally:
        os.close(fd)
    if total > MAX_BYTES:
        raise Rechazo(f"{que} {path}: mas de {MAX_BYTES} bytes")
    return b"".join(trozos)


def leer_manifiesto(path: str, trusted_uid: int) -> dict[str, object]:
    directorio_confiable(os.path.dirname(path) or ".", trusted_uid, "directorio del manifiesto")
    crudo = leer_una_vez(path, "manifiesto", trusted_uid)
    try:
        datos = json.loads(crudo)
    except ValueError as e:
        raise Rechazo(f"manifiesto {path}: JSON invalido ({e})") from e
    if not isinstance(datos, dict):
        raise Rechazo(f"manifiesto {path}: no es un objeto JSON")
    return datos


def entrada(manifest: Mapping[str, object], name: str) -> Entrada:
    e = manifest.get(name)
    if not isinstance(e, dict):
        raise Rechazo(f"nombre desconocido: {name!r} no esta en el manifiesto")
    file, sha, timeout = e.get("file"), e.get("sha256"), e.get("timeout", TIMEOUT_DEFECTO)
    if not isinstance(file, str) or FICHERO.fullmatch(file) is None:
        raise Rechazo(f"{name}: 'file' debe ser un nombre de fichero simple, sin '/'")
    if not isinstance(sha, str) or SHA256.fullmatch(sha) is None:
        raise Rechazo(f"{name}: 'sha256' debe ser 64 hex en minusculas")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout < 1:
        raise Rechazo(f"{name}: 'timeout' debe ser un entero >= 1")
    return Entrada(file, sha, min(timeout, TIMEOUT_TECHO))


def comprobar_shebang(data: bytes) -> None:
    primera = data.split(b"\n", 1)[0]
    if primera not in SHEBANGS:
        raise Rechazo(f"shebang fuera de la lista blanca: {primera[:60]!r}")


def entorno(environ: Mapping[str, str]) -> dict[str, str]:
    env = {"PATH": PATH_FIJO, "LC_ALL": "C", "HOME": "/root"}
    uid = uid_llamante(environ)
    if uid is not None:
        env["SUDO_UID"] = uid
    return env


def uid_llamante(environ: Mapping[str, str]) -> str | None:
    uid = environ.get("SUDO_UID", "")
    return uid if uid.isascii() and uid.isdigit() else None


def ejecutar(data: bytes, file: str, timeout: int, env: dict[str, str], opts: Opciones) -> tuple[int, bytes]:
    """Ejecuta LOS BYTES HASHEADOS desde un directorio 0700 propio. Devuelve (rc, salida)."""
    directorio_confiable(opts.tmp_parent, opts.trusted_uid, "padre del directorio temporal")
    d = tempfile.mkdtemp(prefix="bb-root-run-", dir=opts.tmp_parent)  # 0700, nombre aleatorio
    try:
        p = os.path.join(d, file)
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o500)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return _correr([BASH, p], timeout, env)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _correr(argv: list[str], timeout: int, env: dict[str, str]) -> tuple[int, bytes]:
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, env=env, cwd="/",
                            start_new_session=True, close_fds=True)
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _matar_grupo(proc)
        try:
            out, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:  # un nieto escapo del grupo con el pipe abierto
            out = b""
        msg = f"\n[bb-root-run] TIMEOUT: {timeout} s vencidos, grupo de procesos matado\n"
        return RC_TIMEOUT, (out or b"") + msg.encode()
    finally:
        if proc.poll() is None:
            _matar_grupo(proc)
            proc.wait()
    rc = proc.returncode
    return (128 - rc if rc < 0 else rc), out


def _matar_grupo(proc: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def preparar_out_dir(out_dir: str, trusted_uid: int) -> None:
    try:
        os.mkdir(out_dir, 0o755)
        os.chmod(out_dir, 0o755)  # la umask de sudo podria dejarlo 0700 y el usuario no leeria
    except FileExistsError:
        pass
    except OSError as e:
        raise Rechazo(f"directorio de salida {out_dir}: no se puede crear ({e.strerror})") from e
    directorio_confiable(out_dir, trusted_uid, "directorio de salida")


def _crear_0644(path: str, data: bytes, flags: int) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | flags, 0o644)
    try:
        os.fchmod(fd, 0o644)
        os.write(fd, data)
    finally:
        os.close(fd)


def auditar(out_dir: str, registro: dict[str, object]) -> None:
    linea = json.dumps(registro, ensure_ascii=True, sort_keys=True) + "\n"
    _crear_0644(os.path.join(out_dir, "auditoria.jsonl"), linea.encode(), os.O_APPEND)


def scripts_dir_por_defecto(environ: Mapping[str, str]) -> str:
    uid = uid_llamante(environ)
    try:
        home = pwd.getpwuid(os.getuid() if uid is None else int(uid)).pw_dir
    except KeyError as e:
        raise Rechazo(f"uid llamante {uid} sin entrada en passwd") from e
    return os.path.join(home, SCRIPTS_REL)


def run(name: str | None, manifest_path: str = MANIFEST, scripts_dir: str | None = None,
        out_dir: str = OUT_DIR, opts: Opciones | None = None) -> int:
    opts = opts or Opciones()
    environ = os.environ if opts.environ is None else opts.environ
    salida = opts.salida or sys.stdout.buffer
    ahora = datetime.datetime.now(datetime.timezone.utc)
    registro: dict[str, object] = {
        "ts": ahora.isoformat(timespec="microseconds"),
        "name": name[:64] if isinstance(name, str) else None,
        "sha256": None, "rc": None, "caller_uid": uid_llamante(environ),
    }
    try:
        preparar_out_dir(out_dir, opts.trusted_uid)
    except Rechazo as e:
        print(f"[bb-root-run] RECHAZADO (sin auditoria posible): {e}", file=sys.stderr)
        return RECHAZO
    try:
        if not nombre_valido(name):
            raise Rechazo("se exige exactamente un argumento, un nombre que case "
                          f"^{NOMBRE.pattern}$ (sin rutas ni espacios): {name!r}")
        ent = entrada(leer_manifiesto(manifest_path, opts.trusted_uid), name)
        base = scripts_dir_por_defecto(environ) if scripts_dir is None else scripts_dir
        data = leer_una_vez(os.path.join(base, ent.file), "script")
        registro["sha256"] = hashlib.sha256(data).hexdigest()
        if registro["sha256"] != ent.sha256:
            raise Rechazo(f"{name}: el sha256 del script ({registro['sha256']}) no es el "
                          f"aprobado ({ent.sha256}); el script cambio desde la aprobacion")
        comprobar_shebang(data)
        env = entorno(environ)
        auditar(out_dir, registro | {"evento": "inicio"})
        rc, out = ejecutar(data, ent.file, ent.timeout, env, opts)
    except Rechazo as e:
        auditar(out_dir, registro | {"evento": "rechazo", "rc": RECHAZO, "motivo": str(e)})
        print(f"[bb-root-run] RECHAZADO: {e}", file=sys.stderr)
        return RECHAZO
    fichero = os.path.join(out_dir, f"{name}-{ahora.strftime('%Y%m%dT%H%M%S.%fZ')}.txt")
    _crear_0644(fichero, out, os.O_EXCL)
    salida.write(out)
    salida.flush()
    auditar(out_dir, registro | {"evento": "fin", "rc": rc, "salida": fichero})
    print(f"[bb-root-run] rc={rc} salida={fichero}", file=sys.stderr)
    return rc


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    return run(argv[0] if len(argv) == 1 else None)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
