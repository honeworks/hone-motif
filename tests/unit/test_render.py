"""Rendering through the port (design §8): the job, the layers per kind, the key, render.json, the cache."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import hone_motif as hm
from hone_motif.render import cached, default_layers, frames_for, key_inputs, plan, render_key
from hone_motif.testing import FakeRenderer

PILL = "like-subscribe-glass-pill"
LEAK = "light-leak-amber-sweep"  # screen blend
INK = "ink-and-paint-bloom-wipe"  # normal blend
TITLE = "title-reveal-ember-calligraphy"  # scene over footage
END = "two-videos-subscribe-calm-frames"  # scene over footage
NEXT = "next-up-framed-still"  # takes an image input


@pytest.mark.parametrize(
    ("ms", "fps", "frames"),
    [(6000, 32, 192), (1500, 30, 45), (1500, 27, 41), (1500, 23, 35), (1, 32, 0), (16, 32, 1)],
)
def test_frames_for(ms: int, fps: int, frames: int) -> None:
    assert frames_for(ms, fps) == frames


@pytest.mark.parametrize(
    ("asset", "layers"),
    [
        (PILL, {"main": "webm"}),
        (END, {"main": "webm"}),
        (LEAK, {"matte": "h264", "fx": "h264"}),
        (INK, {"matte": "h264", "fx": "webm"}),
    ],
)
def test_layers_per_kind(lib: hm.Library, asset: str, layers: dict[str, str]) -> None:
    assert default_layers(lib.get(asset)) == layers


def test_an_opaque_scene_is_h264(lib: hm.Library) -> None:
    opaque = lib.get(TITLE).model_copy(update={"over_footage": False})
    assert default_layers(opaque) == {"main": "h264"}
    assert default_layers(lib.get(TITLE)) == {"main": "webm"}


def test_plan_fills_defaults_and_counts_frames(lib: hm.Library) -> None:
    job = plan(lib.get(PILL), {"channelName": "Hone"}, fps=30, duration_ms=5000, size=(960, 540))
    assert job.props["likeLabel"] == "Like"
    assert (job.width, job.height, job.frames) == (960, 540, 150)
    assert job.poster_frame == frames_for(lib.get(PILL).poster_ms, 30)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"aspect": "9:16"}, "made for 16:9"),
        ({"duration_ms": 9000}, "5000-8000"),
        ({"duration_ms": 6000.0}, "integer ms"),
        ({"fps": 0}, "fps"),
        ({"size": (1000, 500)}, "not an even 16:9 size"),
        ({"size": (961, 540.5)}, "not an even"),
        ({"size": (0, 0)}, "not an even"),
        ({"fps": 30.0}, "fps"),
        ({"fps": True}, "fps"),
        ({"formats": {"fx": "webm"}}, "has layers main"),
        ({"formats": {"main": "gif"}}, "not main=gif"),
    ],
)
def test_plan_rejects(lib: hm.Library, kwargs: dict[str, object], match: str) -> None:
    with pytest.raises(hm.InvalidRenderError, match=match):
        plan(lib.get(PILL), None, **kwargs)  # pyright: ignore[reportArgumentType]


def test_plan_rejects_invalid_props(lib: hm.Library) -> None:
    with pytest.raises(hm.InvalidPropsError) as caught:
        plan(lib.get(PILL), {"channelName": "x" * 40})
    assert caught.value.problems[0].code == "text-too-long"


def test_prores_on_request(lib: hm.Library) -> None:
    assert plan(lib.get(PILL), formats={"main": "prores"}).layers == {"main": "prores"}


def test_an_input_file_must_exist_and_enters_the_key(lib: hm.Library, tmp_path: Path) -> None:
    asset = lib.get(NEXT)
    with pytest.raises(hm.InvalidRenderError, match="not a file"):
        plan(asset, {**asset.props, "thumbnail": str(tmp_path / "missing.jpg")})
    image = tmp_path / "still.jpg"
    image.write_bytes(b"one")
    job = plan(asset, {**asset.props, "thumbnail": str(image)})
    assert job.inputs == {"thumbnail": image.resolve()}
    before = render_key(key_inputs(job, FakeRenderer()))
    image.write_bytes(b"two")
    assert render_key(key_inputs(job, FakeRenderer())) != before


def test_the_key_is_stable_and_covers_its_inputs(lib: hm.Library) -> None:
    job = plan(lib.get(PILL))
    inputs = key_inputs(job, FakeRenderer())
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
    assert render_key(inputs) == render_key(json.loads(json.dumps(inputs)))
    assert render_key({**inputs, "fps": 30}) != render_key(inputs)
    assert len(render_key(inputs)) == 64


def test_a_golden_key_for_a_fixed_job() -> None:
    inputs = {"asset": "x-y", "asset_version": 1, "props": {"theme": "dark"}, "fps": 32}
    assert render_key(inputs) == "e9669e6967958665fd0fa961222141b0cf9bd3c5a0b9a6d87725fb9b2205450e"


def test_render_writes_the_record_and_reuses_it(lib: hm.Library, cache: hm.Cache, fake: FakeRenderer) -> None:
    first = hm.render(lib.get(LEAK), renderer=fake, cache=cache)
    assert not first.cached
    assert set(first.layers) == {"matte", "fx"}
    assert first.layers["matte"].name == "matte.mp4"
    assert first.cut_frame == 48
    assert first.blend == "screen"
    assert (first.frames, first.size) == (96, (1920, 1080))
    record = json.loads(first.render_json.read_text(encoding="utf-8"))
    assert record["layers"]["fx"] == {
        "file": "fx.mp4",
        "codec": "h264",
        "pixel_format": "yuv420p",
        "bytes": first.layers["fx"].stat().st_size,
    }
    assert record["renderer"] == {"name": "fake", "version": "1"}
    assert record["started_at"].endswith("Z")
    second = hm.render(lib.get(LEAK), renderer=fake, cache=cache)
    assert second.cached
    assert second.key == first.key
    assert fake.calls == 1


def test_cached_finds_without_rendering(lib: hm.Library, cache: hm.Cache, fake: FakeRenderer) -> None:
    job = plan(lib.get(PILL))
    assert cached(job, fake, cache) is None
    hm.render(lib.get(PILL), renderer=fake, cache=cache)
    found = cached(job, fake, cache)
    assert found is not None
    assert found.cached
    assert fake.calls == 1


def test_render_defaults_to_the_remotion_renderer(
    lib: hm.Library, cache: hm.Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", "")
    with pytest.raises(hm.RendererUnavailableError, match="Node"):
        hm.render(lib.get(PILL), cache=cache)


def test_the_render_pipeline_is_in_the_key(lib_copy: Path) -> None:
    lib = hm.Library(lib_copy)
    before = render_key(key_inputs(plan(lib.get(PILL)), FakeRenderer()))
    render_ts = lib_copy / "scripts" / "render.ts"
    render_ts.write_text(render_ts.read_text(encoding="utf-8") + "\n// changed\n", encoding="utf-8")
    assert render_key(key_inputs(plan(lib.get(PILL)), FakeRenderer())) != before


BAR = "name-title-clean-bar"  # a starter asset that imports shared/text.tsx
WIPE = "matte-wipe-soft-edge"  # one that does not


def test_only_the_shared_files_an_asset_imports_enter_its_key(shipped_copy: Path) -> None:
    lib = hm.Library(shipped_copy)
    before = render_key(key_inputs(plan(lib.get(BAR)), FakeRenderer()))
    (shipped_copy / "shared" / "unrelated.tsx").write_text("export const x = 1;\n", encoding="utf-8")
    assert render_key(key_inputs(plan(lib.get(BAR)), FakeRenderer())) == before
    wipe = render_key(key_inputs(plan(lib.get(WIPE)), FakeRenderer()))
    text = shipped_copy / "shared" / "text.tsx"  # imported by the bar's composition
    text.write_text(text.read_text(encoding="utf-8") + "\n// changed\n", encoding="utf-8")
    assert render_key(key_inputs(plan(lib.get(BAR)), FakeRenderer())) != before
    assert render_key(key_inputs(plan(lib.get(WIPE)), FakeRenderer())) == wipe
    fonts = shipped_copy / "shared" / "fonts.tsx"  # every composition goes through it, imported or not
    fonts.write_text(fonts.read_text(encoding="utf-8") + "\n// changed\n", encoding="utf-8")
    assert render_key(key_inputs(plan(lib.get(WIPE)), FakeRenderer())) != wipe


def test_imports_are_followed_transitively(shipped_copy: Path) -> None:
    lib = hm.Library(shipped_copy)
    bar = shipped_copy / "assets" / BAR / "composition.tsx"
    (shipped_copy / "shared" / "b.ts").write_text("export {c} from './c.ts';\n", encoding="utf-8")
    (shipped_copy / "shared" / "c.ts").write_text("export const c = 1;\n", encoding="utf-8")
    bar.write_text(
        "import {c} from '../../shared/b.ts';\n" + bar.read_text(encoding="utf-8"), encoding="utf-8"
    )
    before = render_key(key_inputs(plan(lib.get(BAR)), FakeRenderer()))
    (shipped_copy / "shared" / "c.ts").write_text("export const c = 2;\n", encoding="utf-8")
    assert render_key(key_inputs(plan(lib.get(BAR)), FakeRenderer())) != before


def test_every_relative_import_in_the_library_resolves() -> None:
    """An import that does not resolve would drop out of the cache key silently (decision D-026)."""
    from hone_motif.render import IMPORT  # noqa: PLC0415

    root = Path(__file__).parents[2] / "library"
    files = [p for d in ("assets", "shared", "src") for p in (root / d).rglob("*.ts*")]
    broken = [
        f"{p.relative_to(root)}: {m}"
        for p in files
        for m in IMPORT.findall(p.read_text(encoding="utf-8"))
        if not (p.parent / m).is_file()
    ]
    assert broken == []


@pytest.mark.parametrize("name", ["secret.txt", "key", "notes.json", "clip.mp4"])
def test_an_image_input_must_be_an_image_file(lib: hm.Library, tmp_path: Path, name: str) -> None:
    """A file prop can come from a model's reply: only an image of a known type is read (0002)."""
    asset = lib.get(NEXT)
    other = tmp_path / name
    other.write_bytes(b"not an image")
    with pytest.raises(hm.InvalidRenderError, match=r"\.png, \.jpg, \.jpeg or \.webp"):
        plan(asset, {**asset.props, "thumbnail": str(other)})


@pytest.mark.parametrize("name", ["a.png", "a.JPG", "a.jpeg", "a.webp"])
def test_image_inputs_of_known_types_pass(lib: hm.Library, tmp_path: Path, name: str) -> None:
    asset = lib.get(NEXT)
    (tmp_path / name).write_bytes(b"image")
    assert plan(asset, {**asset.props, "thumbnail": str(tmp_path / name)}).inputs
