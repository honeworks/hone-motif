"""The render cache (design §5, §8.4; decision D-004): root, entries, atomic builds, info and prune."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

import hone_motif as hm
from hone_motif.cache import folder_hash


def test_default_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("HONE_MOTIF_CACHE", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    assert hm.default_cache_root() == Path.home() / ".cache" / "hone-motif"
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert hm.default_cache_root() == tmp_path / "xdg" / "hone-motif"
    monkeypatch.setenv("HONE_MOTIF_CACHE", str(tmp_path / "mine"))
    assert hm.default_cache_root() == tmp_path / "mine"
    assert hm.Cache().root == tmp_path / "mine"


def test_folder_hash_follows_content_and_names_not_node_files(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("one")
    before = folder_hash(tmp_path)
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("ignored")
    assert folder_hash(tmp_path) == before
    (tmp_path / "a.txt").write_text("two")
    assert folder_hash(tmp_path) != before
    (tmp_path / "a.txt").rename(tmp_path / "b.txt")
    renamed = folder_hash(tmp_path)
    (tmp_path / "b.txt").write_text("one")
    assert folder_hash(tmp_path) != renamed


def _build(record: dict[str, Any]) -> Any:
    def build(tmp: Path) -> dict[str, Any]:
        (tmp / "main.webm").write_bytes(b"media")
        return record

    return build


def test_create_builds_once_and_reopens(tmp_path: Path) -> None:
    cache = hm.Cache(tmp_path)
    assert cache.read("ab12") is None
    record, built = cache.create("ab12", _build({"started_at": "2026-10-10T00:00:00Z"}))
    assert built
    assert cache.entry("ab12") == tmp_path / "renders" / "ab" / "ab12"
    assert (cache.entry("ab12") / "main.webm").read_bytes() == b"media"
    again, built_again = hm.Cache(tmp_path).create("ab12", _build({"other": True}))
    assert not built_again
    assert again == record == json.loads((cache.entry("ab12") / "render.json").read_text())


def test_a_failed_build_leaves_nothing(tmp_path: Path) -> None:
    cache = hm.Cache(tmp_path)

    def fail(tmp: Path) -> dict[str, Any]:
        (tmp / "half.webm").write_bytes(b"x")
        raise hm.RenderError("boom")

    with pytest.raises(hm.RenderError):
        cache.create("cd34", fail)
    assert cache.read("cd34") is None
    assert [p.name for p in (tmp_path / "renders" / "cd").iterdir()] == ["cd34.lock"]


def test_info_and_prune(tmp_path: Path) -> None:
    cache = hm.Cache(tmp_path)
    old = (datetime.now(UTC) - timedelta(days=40)).isoformat().replace("+00:00", "Z")
    new = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    cache.create("aa01", _build({"started_at": old}))
    cache.create("bb02", _build({"started_at": new}))
    cache.create("cc03", _build({}))  # no start time: pruned, it cannot be dated
    info = cache.info()
    assert (info.root, info.entries) == (tmp_path, 3)
    assert info.bytes > 3 * len(b"media")
    assert cache.prune(timedelta(days=30)) == 2
    assert cache.read("bb02") is not None
    assert cache.info().entries == 1


def test_info_of_an_empty_cache(tmp_path: Path) -> None:
    assert hm.Cache(tmp_path / "none").info().entries == 0


def _whole(record: dict[str, Any]) -> Any:
    """A build that writes the layer its record names, as a renderer's record does."""

    def build(tmp: Path) -> dict[str, Any]:
        (tmp / "main.webm").write_bytes(b"media")
        (tmp / "poster.jpg").write_bytes(b"poster")
        return {**record, "layers": {"main": {"file": "main.webm"}}, "poster": "poster.jpg"}

    return build


@pytest.mark.parametrize(
    "damage",
    [
        lambda e: (e / "render.json").write_text("{not json", encoding="utf-8"),
        lambda e: (e / "main.webm").unlink(),
        lambda e: (e / "poster.jpg").unlink(),
    ],
    ids=["unreadable-record", "missing-layer", "missing-poster"],
)
def test_ac19_a_damaged_entry_is_built_again(tmp_path: Path, damage: Any) -> None:
    cache = hm.Cache(tmp_path)
    cache.create("ef56", _whole({"started_at": "2026-10-10T00:00:00Z"}))
    damage(cache.entry("ef56"))
    assert cache.read("ef56") is None
    record, built = cache.create("ef56", _whole({"started_at": "2026-10-11T00:00:00Z"}))
    assert built
    assert record["started_at"] == "2026-10-11T00:00:00Z"
    assert cache.read("ef56") == record
    assert (cache.entry("ef56") / "main.webm").is_file()


def test_prune_removes_node_copies_not_used_lately(tmp_path: Path) -> None:
    cache = hm.Cache(tmp_path)
    for name, days in (("old", 40), ("new", 1)):
        marker = tmp_path / "node" / name / "node_modules" / ".hone-motif-ready"
        marker.parent.mkdir(parents=True)
        marker.touch()
        stamp = (datetime.now(UTC) - timedelta(days=days)).timestamp()
        os.utime(marker, (stamp, stamp))
    (tmp_path / "node" / "half").mkdir()  # an install that never finished: no marker, nothing to date
    assert cache.prune(timedelta(days=30)) == 1
    assert sorted(p.name for p in (tmp_path / "node").iterdir()) == ["half", "new"]


def test_the_lock_excludes_a_second_holder(tmp_path: Path) -> None:
    """file_lock is exclusive across processes: a second process blocks until the first lets go."""
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415

    from hone_motif.cache import file_lock  # noqa: PLC0415

    lock = tmp_path / "x.lock"
    probe = (
        "import sys; from pathlib import Path; from hone_motif.cache import file_lock\n"
        "with file_lock(Path(sys.argv[1])): print('got it')\n"
    )
    with file_lock(lock):
        command = [sys.executable, "-c", probe, str(lock)]
        waiting = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
        with pytest.raises(subprocess.TimeoutExpired):
            waiting.communicate(timeout=1)
    assert waiting.communicate(timeout=30)[0] == "got it\n"


def test_prune_removes_a_render_whose_record_does_not_parse(tmp_path: Path) -> None:
    cache = hm.Cache(tmp_path)
    cache.create("ab12", _build({"started_at": datetime.now(UTC).isoformat()}))
    (cache.entry("ab12") / "render.json").write_text("[", encoding="utf-8")
    assert cache.prune(timedelta(days=30)) == 1
    assert not cache.entry("ab12").exists()


@pytest.mark.parametrize("started", ["not a date", None, 5])
def test_prune_removes_a_render_it_cannot_date(tmp_path: Path, started: Any) -> None:
    cache = hm.Cache(tmp_path)
    cache.create("ab12", _build({"started_at": started}))
    assert cache.prune(timedelta(days=30)) == 1
