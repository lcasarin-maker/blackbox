#!/usr/bin/env python3
"""Marca temporal de diagnóstico para consumidores cooperativos."""
import argparse
import json
import math
import os
import stat
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from tools.capture_io import read_regular_bytes, strict_json_loads

ESQUEMA = 'bb-marca-diagnostico/1'
MAX_BYTES = 4096


@contextmanager
def directorio_seguro(ruta: Path, crear: bool):
    if '..' in ruta.parts:
        raise ValueError('la ruta no admite componentes ..')
    absoluta = ruta if ruta.is_absolute() else Path.cwd() / ruta
    fd = os.open(absoluta.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for parte in absoluta.parent.parts[1:]:
            try:
                hijo = os.open(parte, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            except FileNotFoundError:
                if not crear:
                    raise
                try:
                    os.mkdir(parte, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                hijo = os.open(parte, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = hijo
        try:
            modo = os.stat(absoluta.name, dir_fd=fd, follow_symlinks=False).st_mode
        except FileNotFoundError:
            pass
        else:
            if not stat.S_ISREG(modo):
                raise ValueError('la marca debe ser un archivo regular sin enlaces')
        yield fd
    finally:
        os.close(fd)


def activa(ruta: Path, ahora: float) -> bool:
    try:
        contenido = read_regular_bytes(ruta, MAX_BYTES)
        if len(contenido) > MAX_BYTES:
            raise ValueError('marca excede el tamaño permitido')
        dato = strict_json_loads(contenido.decode('utf-8'))
    except FileNotFoundError:
        return False
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f'marca ilegible: {exc}') from exc
    try:
        valido = (isinstance(dato, dict) and dato.get('esquema') == ESQUEMA
                  and type(dato.get('vence')) in (int, float)
                  and math.isfinite(dato['vence']))
    except OverflowError as exc:
        raise ValueError('marca inválida: vence fuera de rango') from exc
    if not valido:
        raise ValueError('marca inválida')
    return ahora < dato['vence']


def activar(ruta: Path, duracion: int, ahora: float) -> None:
    if type(duracion) is not int or duracion <= 0:
        raise ValueError('la duración debe ser un entero positivo en segundos')
    try:
        vence = ahora + duracion
    except OverflowError as exc:
        raise ValueError('duración fuera de rango') from exc
    if not math.isfinite(vence):
        raise ValueError('duración fuera de rango')
    with directorio_seguro(ruta, True) as fd:
        os.fchmod(fd, 0o700)
        temporal = f'.{ruta.name}.{uuid.uuid4().hex}.tmp'
        descriptor = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as archivo:
                archivo.write(json.dumps({'esquema': ESQUEMA, 'vence': vence}) + '\n')
                archivo.flush()
                os.fsync(archivo.fileno())
            os.replace(temporal, ruta.name, src_dir_fd=fd, dst_dir_fd=fd)
            os.fsync(fd)
        finally:
            try:
                os.unlink(temporal, dir_fd=fd)
            except FileNotFoundError:
                pass


def desactivar(ruta: Path) -> None:
    try:
        with directorio_seguro(ruta, False) as fd:
            os.fchmod(fd, 0o700)
            try:
                os.unlink(ruta.name, dir_fd=fd)
            except FileNotFoundError:
                pass
    except FileNotFoundError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='accion', required=True)
    sub.add_parser('activar').add_argument('duracion_s', type=int)
    sub.add_parser('desactivar')
    args = parser.parse_args()
    ruta = Path(os.environ.get('BLACKBOX_DATA') or Path.home() / '.local/share/blackbox') / 'marca-diagnostico.json'
    try:
        if args.accion == 'activar':
            activar(ruta, args.duracion_s, time.time())
        else:
            desactivar(ruta)
    except (ValueError, OSError) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    main()
