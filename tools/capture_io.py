"""Small fail-closed readers for bounded evidence captures."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from typing import Any


def read_regular_bytes(path: Path, max_bytes: int) -> bytes:
    """Read one bounded regular file without following any path symlink."""
    if max_bytes < 0:
        raise ValueError("max_bytes must be non-negative")
    if ".." in path.parts:
        raise OSError("evidence path must not contain parent traversal")
    absolute = path if path.is_absolute() else Path.cwd() / path
    directory = os.open(
        absolute.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    )
    try:
        for component in absolute.parts[1:-1]:
            child = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=directory,
            )
            os.close(directory)
            directory = child
        descriptor = os.open(
            absolute.name,
            os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=directory,
        )
    finally:
        os.close(directory)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError("evidence input must be a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            return stream.read(max_bytes + 1)
    finally:
        os.close(descriptor)


def strict_json_loads(text: str) -> Any:
    """Decode JSON while rejecting duplicate keys and non-standard constants."""
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise json.JSONDecodeError("duplicate object key", text, 0)
            result[key] = value
        return result

    def reject_constant(_value: str) -> Any:
        raise json.JSONDecodeError("non-finite JSON constant", text, 0)

    return json.loads(
        text, object_pairs_hook=object_pairs, parse_constant=reject_constant
    )
