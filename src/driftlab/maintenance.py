"""Consistent SQLite/artifact backups and verified restores into a new workspace."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from dataclasses import asdict
from filelock import FileLock
from driftlab import __version__


def file_hash(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def backup_workspace(lab, destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("Backup destination already exists")
    if (
        lab.engine.dialect.name != "sqlite"
        or not lab.engine.url.database
        or lab.engine.url.database == ":memory:"
    ):
        raise ValueError("Workspace backups require a file-backed SQLite database")
    if destination.is_relative_to(lab.workspace / "data"):
        raise ValueError("Write backups outside the artifact directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with (
        FileLock(str(lab.workspace / ".execution.lock"), timeout=0),
        tempfile.TemporaryDirectory(prefix="driftlab-backup-") as temp,
    ):
        root = Path(temp)
        database = root / "driftlab.db"
        with (
            sqlite3.connect(lab.engine.url.database) as source,
            sqlite3.connect(database) as target,
        ):
            source.backup(target)
            for run_id, value in target.execute("SELECT id,jsonl_path FROM runs"):
                if value and Path(value).is_absolute():
                    original = Path(value).resolve()
                    if not original.is_relative_to(lab.workspace):
                        raise ValueError(
                            "Run artifacts outside the workspace cannot be included in a portable backup"
                        )
                    target.execute(
                        "UPDATE runs SET jsonl_path=? WHERE id=?",
                        (str(original.relative_to(lab.workspace)), run_id),
                    )
            target.commit()
        sources = {"driftlab.db": database}
        for name in ("runs", "benchmarks", "study"):
            for path in (lab.workspace / "data" / name).rglob("*"):
                if path.is_symlink():
                    raise ValueError("Symlinks are not allowed in workspace backups")
                if path.is_file():
                    sources[path.relative_to(lab.workspace).as_posix()] = path
        policy_path = root / "policies.json"
        policy_path.write_text(json.dumps([asdict(p) for p in lab.policies.values()], indent=2))
        sources["policies.json"] = policy_path
        manifest = {
            "format": 1,
            "driftlab": __version__,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": {
                name: {"sha256": file_hash(path), "bytes": path.stat().st_size}
                for name, path in sources.items()
            },
        }
        temporary = destination.with_name(destination.name + ".tmp")
        try:
            with (
                os.fdopen(
                    os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
                ) as output,
                zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive,
            ):
                for name, path in sources.items():
                    archive.write(path, name)
                archive.writestr("backup-manifest.json", json.dumps(manifest, indent=2))
            with temporary.open("rb") as stream:
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    return destination


def restore_workspace(archive_path, destination, max_bytes=10 * 1024**3):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError(
            "Restore destination must not exist; existing workspaces are never overwritten"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with (
        FileLock(str(destination) + ".restore.lock", timeout=0),
        zipfile.ZipFile(archive_path) as archive,
    ):
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if (
            len(names) != len(set(names))
            or len(entries) > 100000
            or sum(e.file_size for e in entries) > max_bytes
        ):
            raise ValueError("Backup exceeds limits or contains duplicate entries")
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in entry.filename
                or stat.S_ISLNK(entry.external_attr >> 16)
            ):
                raise ValueError("Unsafe path in backup")
        manifest = json.loads(archive.read("backup-manifest.json"))
        if (
            manifest.get("format") != 1
            or set(names) != {"backup-manifest.json", *manifest.get("files", {})}
            or "driftlab.db" not in manifest.get("files", {})
        ):
            raise ValueError("Invalid backup manifest")
        with tempfile.TemporaryDirectory(
            prefix=".driftlab-restore-", dir=destination.parent
        ) as temporary:
            staging = Path(temporary) / "workspace"
            staging.mkdir(mode=0o700)
            for name, record in manifest["files"].items():
                path = staging / name
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with (
                    archive.open(name) as source,
                    os.fdopen(
                        os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
                    ) as target,
                ):
                    shutil.copyfileobj(source, target, 1024 * 1024)
                    target.flush()
                    os.fsync(target.fileno())
                if path.stat().st_size != record["bytes"] or file_hash(path) != record["sha256"]:
                    raise ValueError("Backup content failed checksum verification")
            with sqlite3.connect(f"file:{staging / 'driftlab.db'}?mode=ro", uri=True) as connection:
                if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Backup database failed integrity check")
                if connection.execute("PRAGMA foreign_key_check").fetchone():
                    raise ValueError("Backup database has invalid references")
            os.replace(staging, destination)
    return destination
