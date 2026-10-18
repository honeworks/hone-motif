"""A fake renderer and the `Renderer` contract checker (design §8.1), for tests that must not need Node."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from .render import ENCODINGS, Renderer, RenderJob


class FakeRenderer:
    """Writes small deterministic files instead of rendering; counts its calls.

    `delay_s` waits that long before writing the poster, so a test can kill a render halfway.
    """

    name = "fake"
    version = "1"

    def __init__(self, delay_s: float = 0.0) -> None:
        self.delay_s = delay_s
        self.calls = 0

    def render(self, job: RenderJob, out_dir: Path) -> dict[str, Path]:
        self.calls += 1
        seed = hashlib.sha256(
            job.model_dump_json(exclude={"asset"}).encode() + job.asset.id.encode()
        ).hexdigest()
        files: dict[str, Path] = {}
        for layer, fmt in job.layers.items():
            files[layer] = out_dir / f"{layer}.{ENCODINGS[fmt][0]}"
            files[layer].write_bytes(f"fake {fmt} {layer} {seed}\n".encode())
        if self.delay_s:
            time.sleep(self.delay_s)
        files["poster"] = out_dir / "poster.jpg"
        files["poster"].write_bytes(f"fake poster {seed}\n".encode())
        return files


def check_renderer_contract(renderer: Renderer, job: RenderJob, out_dir: Path) -> list[str]:
    """Run one job through `renderer`; list every way it breaks the `Renderer` contract (empty: it holds)."""
    found: list[str] = []
    if not (renderer.name and renderer.version):
        found.append("name and version must be non-empty strings")
    files = renderer.render(job, out_dir)
    expected = {*job.layers, "poster"}
    if set(files) != expected:
        found.append(f"returned {sorted(files)}, expected {sorted(expected)}")
    for name, path in files.items():
        if path.parent.resolve() != out_dir.resolve():
            found.append(f"{name}: {path} is not directly inside {out_dir}")
        elif not path.is_file() or path.stat().st_size == 0:
            found.append(f"{name}: {path} is missing or empty")
    for layer, fmt in job.layers.items():
        if layer in files and files[layer].suffix != f".{ENCODINGS[fmt][0]}":
            found.append(f"{layer}: {files[layer].name} should end in .{ENCODINGS[fmt][0]} for {fmt}")
    if "poster" in files and files["poster"].name != "poster.jpg":
        found.append("the poster must be poster.jpg")
    return found
