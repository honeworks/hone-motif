"""The guarantees of design §14, through the public API and the command line only.

Cases 13, 14 and 17 render with Node and Remotion; they are in tests/render/test_posters.py. The
placement cases run against the fixture library (tests/fixtures), which covers every rule.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pydantic
import pytest

import hone_motif as hm
from hone_motif.cli import main
from hone_motif.remotion import RemotionRenderer
from hone_motif.testing import FakeRenderer
from tests import fake_node
from tests.conftest import FIXTURES

pytestmark = pytest.mark.e2e

ROOT = Path(__file__).parents[2]
PILL = "like-subscribe-glass-pill"
LEAK = "light-leak-amber-sweep"
END = "two-videos-subscribe-calm-frames"
TITLE = "title-reveal-ember-calligraphy"
WATERMARK = "watermark-star-monogram"
SONG: dict[str, Any] = {
    "duration_ms": 214380,
    "aspect": "16:9",
    "fps": 32,
    "cuts": [6210, 12040, 41010, 60000, 90000],
    "sections": [{"id": "verse-1", "kind": "verse", "start_ms": 12000, "end_ms": 60000}],
    "busy": [{"start_ms": 14000, "end_ms": 30000}],
    "scripts": ["Arab", "Latn"],
    "platform": "youtube",
}


def song(**changes: Any) -> hm.VideoInfo:
    return hm.VideoInfo.model_validate({**SONG, **changes})


def python(code: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run `code` in a fresh interpreter, so imports and PATH are those of a new process."""
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False, env=env, cwd=ROOT
    )


@pytest.mark.parametrize("which", ["shipped", "fixtures"])
def test_ac1_every_asset_loads_and_the_check_passes(
    which: str, shipped: hm.Library, lib: hm.Library, capsys: pytest.CaptureFixture[str]
) -> None:
    library = shipped if which == "shipped" else lib
    folders = {p.name for p in (library.root / "assets").iterdir() if (p / "asset.json").is_file()}
    assert set(library.assets) == folders
    assert len(folders) >= 3
    assert library.check() == []
    for asset in library.assets.values():
        assert hm.check_props(asset, asset.props) == [], asset.id
    assert main(["check", str(library.root)]) == 0
    assert "0 problem(s)" in capsys.readouterr().out


FILTERS: dict[str, dict[str, str]] = {
    "kind": {"kind": "transition"},
    "category": {"category": "captions"},
    "theme": {"theme": "pop"},
    "mood": {"mood": "violent", "kind": "transition"},
    "aspect": {"aspect": "9:16"},
    "script": {"script": "Arab"},
    "text": {"text": "subscribe glass"},
    "all": {},
}


def _matches(asset: hm.Asset, f: dict[str, str]) -> bool:
    """What each filter means (design §6), written out independently of `search`."""
    hay = " ".join([asset.id, asset.name, asset.line, *asset.tags]).lower()
    return (
        asset.kind == f.get("kind", asset.kind)
        and asset.category == f.get("category", asset.category)
        and f.get("theme", asset.themes[0]) in asset.themes
        and (f.get("mood") is None or f["mood"] in asset.moods or "any" in asset.moods)
        and f.get("aspect", asset.aspects[0]) in asset.aspects
        and (f.get("script") is None or f["script"] in asset.scripts)
        and all(word in hay for word in f.get("text", "").split())
    )


def test_ac2_search_filters_in_a_stable_order_without_node(lib: hm.Library) -> None:
    code = f"""
import json, hone_motif as hm
lib = hm.Library({str(lib.root)!r})
print(json.dumps({{name: [a.id for a in lib.search(**f)] for name, f in {FILTERS!r}.items()}}))
"""
    done = python(code, env={**os.environ, "PATH": os.path.dirname(sys.executable)})
    assert done.returncode == 0, done.stderr
    found = json.loads(done.stdout)
    for name, f in FILTERS.items():
        expected = sorted(a.id for a in lib.assets.values() if _matches(a, f))
        assert found[name] == expected, name
    assert LEAK in found["kind"]
    assert PILL in found["text"]
    assert "film-burn-twin-holes" in found["mood"]
    assert "karaoke-fill-sweep" in found["category"]
    assert len(found["all"]) == len(lib.assets)


def test_ac3_check_props_names_the_prop_and_the_limit(lib: hm.Library) -> None:
    problems = hm.check_props(lib.get(PILL), {"channelName": "x" * 30, "likeLabel": 3, "glow": True})
    by_code = {p.code: p for p in problems}
    assert set(by_code) == {"text-too-long", "wrong-type", "unknown-prop"}
    assert by_code["text-too-long"].field == "channelName"
    assert "limit is 24" in by_code["text-too-long"].message
    assert by_code["wrong-type"].field == "likeLabel"
    assert "glow" in by_code["unknown-prop"].message


@pytest.mark.parametrize(
    ("placements", "video", "code"),
    [
        ([{"asset": "no-such-asset", "start_ms": 0}], {}, "unknown-asset"),
        ([{"asset": PILL, "start_ms": 31000, "props": {"channelName": 5}}], {}, "wrong-type"),
        ([{"asset": WATERMARK, "start_ms": 214000, "props": {"channelName": "x"}}], {}, "outside-video"),
        (
            [{"asset": PILL, "start_ms": 31000, "duration_ms": 1000, "props": {"channelName": "x"}}],
            {},
            "duration-out-of-range",
        ),
        (
            [{"asset": TITLE, "start_ms": 0, "props": {"title": "x"}}],
            {"aspect": "9:16"},
            "aspect-unsupported",
        ),
        ([{"asset": TITLE, "start_ms": 0, "props": {"title": "Ростам"}}], {}, "script-not-allowed"),
        (
            [{"asset": PILL, "start_ms": 31000, "props": {"channelName": "x"}}] * 2,
            {"busy": []},
            "repeat-per-video",
        ),
        (
            [
                {"asset": "chapter-card-star-band", "start_ms": s, "props": {"label": "V"}}
                for s in (31000, 41000)
            ],
            {},
            "repeat-gap",
        ),
        ([{"asset": END, "start_ms": 214380 - 25000}], {}, "outside-window"),
        (
            [{"asset": END, "start_ms": 4000}],
            {"duration_ms": 24000, "cuts": [], "sections": [], "busy": []},
            "video-too-short",
        ),
        ([{"asset": PILL, "start_ms": 13000, "props": {"channelName": "x"}}], {}, "over-busy"),
        (
            [
                {"asset": "now-playing-equaliser-bilingual", "start_ms": 1000, "props": {"title": "x"}},
                {"asset": PILL, "start_ms": 2000, "props": {"channelName": "x"}},
            ],
            {"busy": []},
            "region-overlap",
        ),
        (
            [
                {"asset": END, "start_ms": 214380 - 20000},
                {"asset": WATERMARK, "start_ms": 200000, "props": {"channelName": "x"}},
            ],
            {},
            "clear-frame",
        ),
        ([{"asset": LEAK, "start_ms": 40000}], {}, "off-cut"),
    ],
)
def test_ac4_check_placements_rejects(
    lib: hm.Library, placements: list[dict[str, Any]], video: dict[str, Any], code: str
) -> None:
    report = hm.check_placements(placements, song(**video), lib)
    assert code in [p.code for p in report.errors], report.errors
    assert not report.ok


def test_ac5_passing_placements_come_back_complete(lib: hm.Library) -> None:
    report = hm.check_placements(
        [
            {"asset": PILL, "start_ms": 31000, "props": {"channelName": "Hone"}},
            {"asset": END, "start_ms": 214380 - 15000},
        ],
        song(),
        lib,
    )
    assert report.ok, report.errors
    pill, end = report.placements
    assert pill.duration_ms == 6000
    assert set(pill.props) >= {
        "theme",
        "likeLabel",
        "subscribeLabel",
        "subscribedLabel",
        "channelName",
        "corner",
    }
    assert end.duration_ms == 15000
    assert end.start_ms + end.duration_ms == 214380
    for p in report.placements:
        assert hm.check_props(lib.get(p.asset), p.props) == []


def test_ac6_the_schema_and_catalogue_hold_only_the_candidates(lib: hm.Library) -> None:
    candidates = lib.search(kind="transition")
    schema = hm.placement_schema(candidates)
    ids = schema["properties"]["placements"]["items"]["properties"]["asset"]["enum"]
    assert ids == sorted(a.id for a in candidates)
    catalog = lib.catalog(candidates, song())
    assert [e["id"] for e in catalog] == [a.id for a in candidates]
    for entry in catalog:
        assert {"id", "name", "kind", "line", "themes", "moods", "slots", "when", "duration_ms"} <= set(entry)
        assert {"region", "text_fields", "props_schema", "cut_ms"} <= set(entry)


def test_ac7_the_same_inputs_render_once(lib: hm.Library, tmp_path: Path) -> None:
    fake = FakeRenderer()
    cache = hm.Cache(tmp_path)
    first = hm.render(lib.get(PILL), renderer=fake, cache=cache)
    second = hm.render(lib.get(PILL), dict(lib.get(PILL).props), renderer=fake, cache=cache)
    assert (first.cached, second.cached, fake.calls) == (False, True, 1)
    assert second.layers == first.layers
    other = hm.render(lib.get(PILL), {**lib.get(PILL).props, "theme": "pop"}, renderer=fake, cache=cache)
    assert other.key != first.key
    assert fake.calls == 2


WORKER = """
import json, sys
import hone_motif as hm
from hone_motif.testing import FakeRenderer
fake = FakeRenderer(delay_s=float(sys.argv[2]))
lib = hm.Library(sys.argv[3])
done = hm.render(lib.get("like-subscribe-glass-pill"), renderer=fake, cache=hm.Cache(sys.argv[1]))
print(json.dumps({"calls": fake.calls, "cached": done.cached}))
"""


def _worker(cache: Path, delay: float, library: Path) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-c", WORKER, str(cache), str(delay), str(library)],
        stdout=subprocess.PIPE,
        text=True,
        cwd=ROOT,
    )


def _started(cache: Path) -> None:
    for _ in range(400):
        if list(cache.glob("renders/*/.tmp-*/main.webm")):
            return
        subprocess.run(["sleep", "0.05"], check=True)
    raise AssertionError("the render never started")


def test_ac8_a_killed_render_leaves_nothing_and_two_processes_render_once(
    tmp_path: Path, fixture_root: Path
) -> None:
    killed = _worker(tmp_path / "a", 60, fixture_root)
    _started(tmp_path / "a")
    killed.kill()
    killed.wait()
    assert hm.Cache(tmp_path / "a").info().entries == 0
    first = _worker(tmp_path / "b", 1.5, fixture_root)
    _started(tmp_path / "b")
    second = _worker(tmp_path / "b", 0, fixture_root)
    results = [json.loads(p.communicate(timeout=60)[0]) for p in (first, second)]
    assert sum(r["calls"] for r in results) == 1
    assert hm.Cache(tmp_path / "b").info().entries == 1


def test_ac9_a_transition_delivers_matte_fx_and_its_cut_frame(lib: hm.Library, tmp_path: Path) -> None:
    asset = lib.get(LEAK)
    assert asset.transition is not None
    for fps in (23, 24, 27, 30, 31, 32):  # 23, 27 and 31 put 1500 ms on a half frame
        done = hm.render(asset, fps=fps, renderer=FakeRenderer(), cache=hm.Cache(tmp_path))
        assert set(done.layers) == {"matte", "fx"}
        assert all(p.is_file() for p in done.layers.values())
        assert done.cut_frame == (asset.transition.cut_ms * fps + 500) // 1000  # halves up (design §8.3)
        assert done.blend == "screen"


def test_ac10_without_node_search_and_checks_work_and_render_says_how_to_install(
    tmp_path: Path, fixture_root: Path
) -> None:
    code = f"""
import hone_motif as hm
lib = hm.Library(r"{fixture_root}")
assert lib.search(kind="overlay")
assert hm.check_props(lib.get("like-subscribe-glass-pill"), {{"channelName": "x"}}) == []
video = hm.VideoInfo(duration_ms=60000, aspect="16:9", fps=30)
assert hm.check_placements([{{"asset": "light-leak-amber-sweep", "start_ms": 0}}], video, lib).errors
try:
    hm.render(lib.get("like-subscribe-glass-pill"), cache=hm.Cache(r"{tmp_path / "cache"}"))
except hm.RendererUnavailableError as e:
    print(e)
"""
    done = python(code, env={**os.environ, "PATH": os.path.dirname(sys.executable)})
    assert done.returncode == 0, done.stderr
    assert "Node" in done.stdout
    assert "https://nodejs.org" in done.stdout
    assert "Remotion" in done.stdout


def test_ac11_the_core_imports_no_adapter_extra_or_sibling() -> None:
    done = python("import sys, hone_motif; print('\\n'.join(sorted(sys.modules)))")
    assert done.returncode == 0, done.stderr
    modules = set(done.stdout.split())
    assert "hone_motif.remotion" not in modules
    assert "hone_motif.cli" not in modules
    assert not {m for m in modules if m.startswith("hone_") and not m.startswith("hone_motif")}
    assert not {m for m in modules if m.split(".")[0] in {"subprocess_tee", "PIL", "numpy", "remotion"}}


def test_ac12_render_json_holds_its_key_inputs_and_the_renderer(lib: hm.Library, tmp_path: Path) -> None:
    done = hm.render(
        lib.get(PILL), fps=30, size=(960, 540), renderer=FakeRenderer(), cache=hm.Cache(tmp_path)
    )
    record = json.loads(done.render_json.read_text(encoding="utf-8"))
    assert record["format_version"] == "1"
    assert record["key"] == done.key
    assert record["renderer"] == {"name": "fake", "version": "1"}
    inputs = record["inputs"]
    assert set(inputs) == {
        "asset",
        "asset_version",
        "asset_hash",
        "shared_hash",
        "fonts_hash",
        "pipeline_hash",
        "props",
        "input_files",
        "fps",
        "width",
        "height",
        "frames",
        "layers",
        "renderer",
    }
    assert (inputs["fps"], inputs["width"], inputs["height"], inputs["frames"]) == (30, 960, 540, 180)
    canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert hashlib.sha256(canonical.encode()).hexdigest() == record["key"]  # the record reproduces its key
    assert inputs["props"] == record["props"]


def test_ac15_times_are_integer_milliseconds(lib: hm.Library, tmp_path: Path) -> None:
    data = json.loads((FIXTURES / PILL / "asset.json").read_text(encoding="utf-8"))
    with pytest.raises(pydantic.ValidationError):
        hm.Asset.model_validate({**data, "poster_ms": 3600.0})
    with pytest.raises(pydantic.ValidationError):
        hm.Asset.model_validate({**data, "duration": {"default_ms": 6000.5, "min_ms": 5000, "max_ms": 8000}})
    with pytest.raises(pydantic.ValidationError):
        song(duration_ms=214380.0)
    with pytest.raises(pydantic.ValidationError):
        song(cuts=[6210.5])
    report = hm.check_placements([{"asset": LEAK, "start_ms": 39510.0}], song(), lib)
    assert [p.code for p in report.errors] == ["bad-placement"]
    with pytest.raises(hm.InvalidRenderError):
        hm.render(lib.get(PILL), duration_ms=6000.0, renderer=FakeRenderer(), cache=hm.Cache(tmp_path))  # pyright: ignore[reportArgumentType]
    done = hm.render(lib.get(PILL), renderer=FakeRenderer(), cache=hm.Cache(tmp_path))
    record = json.loads(done.render_json.read_text(encoding="utf-8"))
    assert all(
        type(record[k]) is int for k in ("fps", "width", "height", "frames", "duration_ms", "render_ms")
    )


def test_ac16_no_media_is_tracked_and_the_cache_is_outside_the_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    media = (".webm", ".mp4", ".mov", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".avi", ".mkv")
    assert [f for f in tracked if f.lower().endswith(media)] == []
    monkeypatch.delenv("HONE_MOTIF_CACHE", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    root = hm.default_cache_root().resolve()
    assert ROOT.resolve() not in root.parents
    assert root != ROOT.resolve()


def test_records_hold_no_secrets(lib: hm.Library, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CONTRIBUTING: a planted fake secret appears in no record, job file, gallery page or log."""
    planted = "sk-hone-fake-0123456789"
    monkeypatch.setenv("HONE_FAKE_SECRET", planted)
    monkeypatch.setenv("ANTHROPIC_API_KEY", planted)
    cache = hm.Cache(tmp_path / "cache")
    node, npm = fake_node.install(tmp_path / "bin")  # a stand-in node: the adapter writes its job file
    hm.render(lib.get(PILL), renderer=RemotionRenderer(node=node, npm=npm, cache_root=tmp_path), cache=cache)
    hm.build_gallery(lib, cache=cache, out=tmp_path / "gallery", renderer=FakeRenderer())
    stills_renderer = RemotionRenderer(node=node, npm=npm, cache_root=tmp_path)
    hm.build_gallery(lib, cache=cache, out=tmp_path / "gallery-stills", renderer=stills_renderer, stills=True)
    written = [p for p in tmp_path.rglob("*") if p.is_file() and "bin" not in p.parts]
    assert any(p.name == "job.json" for p in written)
    for path in written:
        assert planted.encode() not in path.read_bytes(), path


def test_ac18_init_copies_a_library_that_checks_and_refuses_a_full_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "my-assets"
    assert main(["init", str(target)]) == 0
    assert "my-assets" in capsys.readouterr().out
    copied = hm.Library(target)
    assert set(copied.assets) == set(hm.Library().assets)
    assert copied.check() == []
    assert main(["--library", str(target), "check"]) == 0
    assert not (target / "node_modules").exists()
    assert {"package.json", "package-lock.json", "scripts", "shared", "fonts", "src"} <= {
        p.name for p in target.iterdir()
    }
    assert main(["init", str(target)]) == 2
    assert "not empty" in capsys.readouterr().err
    (tmp_path / "empty").mkdir()
    assert main(["init", str(tmp_path / "empty")]) == 0
