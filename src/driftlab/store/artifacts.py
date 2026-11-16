"""Atomic metadata writes and explicit recovery of interrupted JSONL tails."""

import json
import os
from pathlib import Path
import uuid


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with os.fdopen(
            os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8"
        ) as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def recover_tail(path: Path):
    """Quarantine a partial final write before resuming. Complete corrupt lines fail closed."""
    if not path.exists():
        return
    data = path.read_bytes()
    if not data or data.endswith(b"\n"):
        return
    split = data.rfind(b"\n") + 1
    tail = data[split:]
    quarantine = path.with_name(path.name + ".interrupted-" + uuid.uuid4().hex)
    with quarantine.open("xb") as stream:
        stream.write(tail)
        stream.flush()
        os.fsync(stream.fileno())
    with path.open("r+b") as stream:
        stream.truncate(split)
        stream.flush()
        os.fsync(stream.fileno())


def write_error(path: Path, message: str):
    with os.fdopen(
        os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8"
    ) as stream:
        stream.write(message)
        stream.flush()
        os.fsync(stream.fileno())
