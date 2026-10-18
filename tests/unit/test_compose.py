"""The ffmpeg filter graph (design §8.5, decision D-011): order, start frames, blends, the matte."""

from __future__ import annotations

from pathlib import Path

import pytest

import hone_motif as hm
from hone_motif.testing import FakeRenderer

PILL = "like-subscribe-glass-pill"
LEAK = "light-leak-amber-sweep"
INK = "ink-and-paint-bloom-wipe"
CAPTION = "karaoke-fill-sweep"


def layer(
    lib: hm.Library, cache: hm.Cache, asset: str, start_ms: int, shots: tuple[Path, Path] | None = None
) -> hm.ComposeLayer:
    a = lib.get(asset)
    rendered = hm.render(a, renderer=FakeRenderer(), cache=cache)
    placement = hm.Placement(asset=asset, start_ms=start_ms, duration_ms=a.duration.default_ms, props=a.props)
    out, inc = shots or (None, None)
    return hm.ComposeLayer(placement=placement, rendered=rendered, kind=a.kind, outgoing=out, incoming=inc)


def test_layers_are_laid_bottom_to_top_from_absolute_frames(lib: hm.Library, cache: hm.Cache) -> None:
    caption = layer(lib, cache, CAPTION, 1000)
    pill = layer(lib, cache, PILL, 31001)
    graph = hm.compose_filter([caption, pill], fps=32, size=(1920, 1080))
    assert graph.output == "[v]"
    assert graph.inputs == [
        "-c:v",
        "libvpx-vp9",
        "-i",
        str(pill.rendered.layers["main"]),
        "-c:v",
        "libvpx-vp9",
        "-i",
        str(caption.rendered.layers["main"]),
    ]
    chains = graph.filter.split(";")
    assert chains[0] == "[0:v]fps=32,scale=1920:1080,setsar=1,format=yuva420p[base]"
    assert "+992/(32*TB)" in chains[1]  # round(31001 * 32 / 1000) = 992: the overlay comes first
    assert "+32/(32*TB)" in chains[3]  # the caption on top
    assert chains[-1].endswith("format=yuv420p[v]")


def test_a_transition_masks_the_incoming_shot_and_screens_its_fx(
    lib: hm.Library, cache: hm.Cache, tmp_path: Path
) -> None:
    shots = (tmp_path / "out.mp4", tmp_path / "in.mp4")
    leak = layer(lib, cache, LEAK, 39510, shots)
    graph = hm.compose_filter([leak], fps=32, size=(1920, 1080))
    assert graph.inputs == [
        "-i",
        str(shots[0]),
        "-i",
        str(shots[1]),
        "-i",
        str(leak.rendered.layers["matte"]),
        "-i",
        str(leak.rendered.layers["fx"]),
    ]
    assert "format=gray" in graph.filter
    assert "alphamerge" in graph.filter
    assert "tpad=start=1264" in graph.filter  # round(39510 * 32 / 1000)
    assert "blend=all_mode=screen" in graph.filter


def test_a_normal_transition_lays_its_fx_over(lib: hm.Library, cache: hm.Cache, tmp_path: Path) -> None:
    ink = layer(lib, cache, INK, 6210 - 1500, (tmp_path / "a.mp4", tmp_path / "b.mp4"))
    graph = hm.compose_filter([ink], fps=24, size=(960, 540))
    assert "blend=" not in graph.filter
    assert graph.inputs[-4:] == ["-c:v", "libvpx-vp9", "-i", str(ink.rendered.layers["fx"])]


def test_a_transition_needs_its_shots(lib: hm.Library, cache: hm.Cache) -> None:
    with pytest.raises(ValueError, match="outgoing and incoming"):
        hm.compose_filter([layer(lib, cache, LEAK, 39510)], fps=32, size=(1920, 1080))


def test_a_loop_input_repeats_and_is_cut_to_its_placement(lib: hm.Library, cache: hm.Cache) -> None:
    snow = lib.get("weather-snow-drift")
    rendered = hm.render(snow, renderer=FakeRenderer(), cache=cache)
    placement = hm.Placement(asset=snow.id, start_ms=0, duration_ms=30000, props=snow.props)
    loop = hm.ComposeLayer(placement=placement, rendered=rendered, kind="loop")
    graph = hm.compose_filter([loop], fps=32, size=(1920, 1080))
    i = graph.inputs.index("-stream_loop")
    assert graph.inputs[i : i + 5] == ["-stream_loop", "-1", "-c:v", "libvpx-vp9", "-i"]
    assert "trim=end_frame=960," in graph.filter
    overlay = layer(lib, cache, PILL, 0)
    plain = hm.compose_filter([overlay], fps=32, size=(1920, 1080))
    assert "-stream_loop" not in plain.inputs
    assert "trim=" not in plain.filter
