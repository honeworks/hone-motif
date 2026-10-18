"""The render cache (design §5, §8.4; decision D-004): one entry per key, written atomically."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SKIP = ("node_modules", "build")
READY = ".hone-motif-ready"  # in node/<hash>/node_modules/: the install finished; touched on every use


def default_cache_root() -> Path:
    """`HONE_MOTIF_CACHE`, else `$XDG_CACHE_HOME/hone-motif`, else `~/.cache/hone-motif`."""
    env = os.environ.get("HONE_MOTIF_CACHE")
    if env:
        return Path(env).expanduser()
    xdg = os.environ.get("XDG_CACHE_HOME")
    return (Path(xdg) if xdg else Path.home() / ".cache") / "hone-motif"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def folder_hash(folder: Path) -> str:
    """SHA-256 over every file's relative path and bytes, in a stable order; skips node_modules and build."""
    digest = hashlib.sha256()
    for path in sorted(
        p
        for p in folder.rglob("*")
        if p.is_file() and not any(s in p.relative_to(folder).parts for s in SKIP)
    ):
        digest.update(path.relative_to(folder).as_posix().encode() + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


@contextmanager
def file_lock(path: Path) -> Generator[None]:
    """An exclusive lock on `path` (created if missing), held for the block; a second process waits.

    `fcntl.flock` on POSIX, `msvcrt.locking` on Windows (decision D-029).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        _lock(handle.fileno())
        try:
            yield
        finally:
            _unlock(handle.fileno())


if sys.platform == "win32":  # pragma: no cover - the suite runs on POSIX
    import msvcrt

    def _lock(fd: int) -> None:
        while True:  # LK_LOCK gives up after ten seconds; a lock is held as long as a render takes
            try:
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
                return
            except OSError:
                continue

    def _unlock(fd: int) -> None:
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _lock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_EX)

    def _unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


@dataclass(frozen=True)
class CacheInfo:
    root: Path
    entries: int
    bytes: int


class Cache:
    """Renders by key under `<root>/renders/<key[:2]>/<key>/`, each with its `render.json`."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else default_cache_root()

    def entry(self, key: str) -> Path:
        return self.root / "renders" / key[:2] / key

    def read(self, key: str) -> dict[str, Any] | None:
        """The entry's render.json, or None when there is no whole entry: a record that does not parse, or
        a layer or poster it names that is missing, counts as no entry (design/changes/0002)."""
        folder = self.entry(key)
        try:
            data: Any = json.loads((folder / "render.json").read_text(encoding="utf-8"))
            names = [str(layer["file"]) for layer in data.get("layers", {}).values()]
            names += [str(data["poster"])] if "poster" in data else []
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            return None
        if not all((folder / name).is_file() for name in names):
            return None
        record: dict[str, Any] = data
        return record

    def create(self, key: str, build: Callable[[Path], dict[str, Any]]) -> tuple[dict[str, Any], bool]:
        """The entry for `key`, built by `build(tmp_dir)` unless present; True when this call built it.

        The build writes into a temporary folder that is renamed into place when complete, so a build
        killed halfway leaves no entry; a lock per key makes a second process wait and reuse the result.
        """
        existing = self.read(key)
        if existing is not None:
            return existing, False
        entry = self.entry(key)
        with file_lock(entry.parent / f"{key}.lock"):
            existing = self.read(key)
            if existing is not None:
                return existing, False
            tmp = entry.parent / f".tmp-{key}"
            shutil.rmtree(tmp, ignore_errors=True)  # left by a build that was killed
            shutil.rmtree(entry, ignore_errors=True)  # a damaged entry, which read() did not accept
            tmp.mkdir(parents=True)
            try:
                record = build(tmp)
                (tmp / "render.json").write_text(
                    json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
                )
                tmp.rename(entry)
            except BaseException:
                shutil.rmtree(tmp, ignore_errors=True)
                raise
        return record, True

    def _entries(self) -> list[Path]:
        return sorted(p.parent for p in (self.root / "renders").glob("*/*/render.json"))

    def info(self) -> CacheInfo:
        """How many renders the cache holds and their size in bytes."""
        entries = self._entries()
        size = sum(f.stat().st_size for e in entries for f in e.iterdir() if f.is_file())
        return CacheInfo(root=self.root, entries=len(entries), bytes=size)

    def prune(self, older_than: timedelta) -> int:
        """Remove renders started, and Node copies last used, more than `older_than` ago; returns how
        many were removed."""
        cutoff = datetime.now(UTC) - older_than
        removed = 0
        for entry in self._entries():
            if _started(entry) < cutoff:  # a render that cannot be dated goes too
                shutil.rmtree(entry)
                removed += 1
        for marker in (self.root / "node").glob(f"*/node_modules/{READY}"):
            if datetime.fromtimestamp(marker.stat().st_mtime, UTC) < cutoff:
                shutil.rmtree(marker.parents[1])
                removed += 1
        return removed


def _started(entry: Path) -> datetime:
    """When the entry's render started, or the earliest date when its record does not say."""
    try:
        record = json.loads((entry / "render.json").read_text(encoding="utf-8"))
        return datetime.fromisoformat(str(record["started_at"]).replace("Z", "+00:00"))
    except (OSError, ValueError, TypeError, KeyError):
        return datetime.min.replace(tzinfo=UTC)
