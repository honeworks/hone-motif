"""The filter graph run through real ffmpeg (design §8.5): layers land on their start frame."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Literal

import pytest

import hone_motif as hm

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
FPS = 10
SIZE = (64, 36)


def clip(path: Path, colour: str, seconds: float) -> Path:
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color={colour}:s=64x36:r={FPS}:d={seconds}",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(path),
        ],
        check=True,
    )
    return path


def lumas(graph: hm.FilterGraph, footage: Path) -> list[int]:
    raw = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(footage),
            *graph.inputs,
            "-filter_complex",
            f"{graph.filter};{graph.output}scale=1:1,format=gray[probe]",
            "-map",
            "[probe]",
            "-f",
            "rawvideo",
            "-",
        ],
        capture_output=True,
        check=True,
    ).stdout
    return list(raw)


def rendered(tmp: Path, layers: dict[str, Path], blend: Literal["normal", "screen"]) -> hm.Rendered:
    return hm.Rendered(
        asset="x-y",
        key="k",
        folder=tmp,
        layers=layers,
        poster=tmp / "p.jpg",
        cut_frame=5,
        blend=blend,
        frames=10,
        size=SIZE,
        render_json=tmp / "r.json",
        cached=False,  # pyright: ignore[reportArgumentType]
    )


@pytest.mark.parametrize("blend", ["screen", "normal"])
def test_a_transition_fx_lands_on_its_start_frame(tmp_path: Path, blend: Literal["normal", "screen"]) -> None:
    black = clip(tmp_path / "black.mp4", "black", 5)
    fx = clip(tmp_path / "fx.mp4", "white", 1)  # a white flash for the transition's 10 frames
    matte = clip(tmp_path / "matte.mp4", "black", 1)  # keeps the outgoing (black) shot
    layer = hm.ComposeLayer(
        placement=hm.Placement(asset="x-y", start_ms=1000, duration_ms=1000, props={}),
        rendered=rendered(tmp_path, {"matte": matte, "fx": fx}, blend),
        kind="transition",
        outgoing=black,
        incoming=black,
    )
    graph = hm.compose_filter([layer], fps=FPS, size=SIZE)
    bright = [i for i, v in enumerate(lumas(graph, black)) if v > 128]
    assert bright == list(range(10, 20))


def test_a_loop_repeats_for_its_placement(tmp_path: Path) -> None:
    black = clip(tmp_path / "black.mp4", "black", 6)
    cycle = clip(tmp_path / "cycle.mp4", "white", 1)  # one 1 s cycle, placed for 3 s from 1 s
    layer = hm.ComposeLayer(
        placement=hm.Placement(asset="x-y", start_ms=1000, duration_ms=3000, props={}),
        rendered=rendered(tmp_path, {"main": cycle}, "normal"),
        kind="loop",
    )
    graph = hm.compose_filter([layer], fps=FPS, size=SIZE)
    bright = [i for i, v in enumerate(lumas(graph, black)) if v > 128]
    assert bright == list(range(10, 40))
