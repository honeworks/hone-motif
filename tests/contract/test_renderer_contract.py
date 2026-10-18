"""Every `Renderer` keeps the contract of design §8.1: the fake, and the Remotion renderer's process side."""

from __future__ import annotations

from pathlib import Path

import pytest

import hone_motif as hm
from hone_motif.remotion import RemotionRenderer
from hone_motif.render import RenderJob, plan
from hone_motif.testing import FakeRenderer, check_renderer_contract
from tests import fake_node

JOBS = [
    "like-subscribe-glass-pill",
    "light-leak-amber-sweep",
    "ink-and-paint-bloom-wipe",
    "karaoke-fill-sweep",
]


def renderers(tmp_path: Path) -> list[hm.Renderer]:
    node, npm = fake_node.install(tmp_path / "bin")
    return [FakeRenderer(), RemotionRenderer(node=node, npm=npm, cache_root=tmp_path / "cache")]


@pytest.mark.parametrize("asset", JOBS)
@pytest.mark.parametrize("which", [0, 1], ids=["fake", "remotion"])
def test_the_contract_holds(lib: hm.Library, tmp_path: Path, asset: str, which: int) -> None:
    renderer = renderers(tmp_path)[which]
    out = tmp_path / "out"
    out.mkdir()
    assert check_renderer_contract(renderer, plan(lib.get(asset), fps=24, size=(960, 540)), out) == []


class Broken:
    """Breaks every rule: no version, a file outside out_dir, a wrong suffix, an empty, odd poster."""

    name = "broken"
    version = ""

    def render(self, job: RenderJob, out_dir: Path) -> dict[str, Path]:
        outside = out_dir.parent / "elsewhere.webm"
        outside.write_bytes(b"x")
        (out_dir / "fx.mov").write_bytes(b"x")
        (out_dir / "cover.png").write_bytes(b"")
        return {"matte": outside, "fx": out_dir / "fx.mov", "poster": out_dir / "cover.png"}


def test_the_checker_finds_every_break(lib: hm.Library, tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    found = check_renderer_contract(Broken(), plan(lib.get("ink-and-paint-bloom-wipe")), out)
    text = "\n".join(found)
    assert "name and version" in text
    assert "not directly inside" in text
    assert "should end in .webm" in text
    assert "missing or empty" in text
    assert "poster.jpg" in text


def test_the_checker_finds_missing_layers(lib: hm.Library, tmp_path: Path) -> None:
    class Partial(FakeRenderer):
        def render(self, job: RenderJob, out_dir: Path) -> dict[str, Path]:
            files = super().render(job, out_dir)
            del files["fx"]
            return files

    out = tmp_path / "out"
    out.mkdir()
    [problem] = check_renderer_contract(Partial(), plan(lib.get("ink-and-paint-bloom-wipe")), out)
    assert "expected" in problem
