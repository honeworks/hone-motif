"""Rendering through the `Renderer` port, once per key (design §8)."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, cast

from .asset import Asset, Blend, Frozen
from .cache import Cache, file_hash, folder_hash
from .errors import InvalidPropsError, InvalidRenderError
from .props import check_props, fill_defaults
from .video import Aspect

Format = Literal["webm", "h264", "prores"]
# format -> (file extension, codec, pixel format) (design §8.3, decision D-005)
ENCODINGS: dict[str, tuple[str, str, str]] = {
    "webm": ("webm", "vp9", "yuva420p"),
    "h264": ("mp4", "h264", "yuv420p"),
    "prores": ("mov", "prores", "yuva444p10le"),
}
LAYOUT = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}


def frames_for(ms: int, fps: int) -> int:
    """`ms * fps / 1000` rounded with halves up, in integers: `(ms * fps + 500) // 1000` (design §8.3)."""
    return (ms * fps + 500) // 1000


class RenderJob(Frozen):
    """Everything a renderer needs for one render (design §8.1)."""

    asset: Asset
    props: dict[str, Any]
    aspect: Aspect = "16:9"  # the layout: drawn at LAYOUT[aspect], scaled to width x height
    fps: int
    width: int
    height: int
    duration_ms: int
    frames: int
    poster_frame: int
    layers: dict[str, Format]
    inputs: dict[str, Path] = {}  # file props (an image), by prop


class Rendered(Frozen):
    """A finished render in the cache."""

    asset: str
    key: str
    folder: Path
    layers: dict[str, Path]  # {"main": ...} or {"matte": ..., "fx": ...}
    poster: Path
    cut_frame: int | None
    blend: Blend
    frames: int
    size: tuple[int, int]
    render_json: Path
    cached: bool  # True when this call found it in the cache


class Renderer(Protocol):
    """Writes a job's layer files and `poster.jpg` into `out_dir` and returns them by name (design §8.1)."""

    name: str
    version: str

    def render(self, job: RenderJob, out_dir: Path) -> dict[str, Path]: ...


def default_layers(asset: Asset) -> dict[str, Format]:
    """The layers and formats of design §8.3 for the asset's kind."""
    match asset.kind:
        case "transition":
            screen = asset.transition is not None and asset.transition.fx_blend == "screen"
            return {"matte": "h264", "fx": "h264" if screen else "webm"}
        case "background":
            return {"main": "h264"}
        case "scene":
            return {"main": "webm" if asset.over_footage else "h264"}
        case _:
            return {"main": "webm"}


def _size(aspect: str, size: tuple[int, int] | None) -> tuple[int, int]:
    layout = LAYOUT[aspect]
    width, height = size or layout
    if width <= 0 or width * layout[1] != height * layout[0] or width % 2 or height % 2:
        raise InvalidRenderError(
            f"size {width}x{height} is not an even {aspect} size (e.g. {layout[0]}x{layout[1]})"
        )
    return width, height


IMAGES = (".png", ".jpg", ".jpeg", ".webp")  # the image files a file prop may name (design/changes/0002)


def _inputs(asset: Asset, props: Mapping[str, Any]) -> dict[str, Path]:
    """The file props' paths; a path can come from a model's reply, so only image files are taken."""
    found: dict[str, Path] = {}
    for spec in asset.inputs:
        value = props.get(spec.prop)
        if value:
            path = Path(str(value))
            if path.suffix.lower() not in IMAGES:
                raise InvalidRenderError(
                    f"{asset.id}: {spec.prop} must name a .png, .jpg, .jpeg or .webp file, not {path.name}"
                )
            if not path.is_file():
                raise InvalidRenderError(f"{asset.id}: {spec.prop} names {path}, which is not a file")
            found[spec.prop] = path.resolve()
    return found


def plan(
    asset: Asset,
    props: Mapping[str, Any] | None = None,
    *,
    fps: int = 32,
    aspect: str = "16:9",
    duration_ms: int | None = None,
    size: tuple[int, int] | None = None,
    formats: Mapping[str, Format] | None = None,
) -> RenderJob:
    """The render job for these inputs, checked; raises InvalidPropsError or InvalidRenderError."""
    given = dict(asset.props if props is None else props)
    problems = check_props(asset, given)
    if problems:
        raise InvalidPropsError(asset.id, problems)
    if aspect not in asset.aspects:
        raise InvalidRenderError(f"{asset.id} is made for {', '.join(asset.aspects)}, not {aspect}")
    duration = asset.duration.default_ms if duration_ms is None else duration_ms
    if (
        isinstance(duration, bool)
        or not isinstance(duration, int)  # pyright: ignore[reportUnnecessaryIsInstance] - callers may pass floats
        or not asset.duration.min_ms <= duration <= asset.duration.max_ms
    ):
        raise InvalidRenderError(
            f"{asset.id} lasts {asset.duration.min_ms}-{asset.duration.max_ms} integer ms, not {duration!r}"
        )
    if isinstance(fps, bool) or not isinstance(fps, int) or not 1 <= fps <= 120:  # pyright: ignore[reportUnnecessaryIsInstance]
        raise InvalidRenderError(f"fps must be 1-120, not {fps}")
    layers = default_layers(asset)
    for layer, fmt in (formats or {}).items():
        if layer not in layers or fmt not in ENCODINGS:
            raise InvalidRenderError(
                f"{asset.id} has layers {', '.join(layers)} and formats {', '.join(ENCODINGS)}; "
                f"not {layer}={fmt}"
            )
        layers[layer] = fmt
    width, height = _size(aspect, size)
    frames = frames_for(duration, fps)
    return RenderJob(
        asset=asset,
        props=fill_defaults(asset, given),
        aspect=cast(Aspect, aspect),  # checked against asset.aspects above
        fps=fps,
        width=width,
        height=height,
        duration_ms=duration,
        frames=frames,
        poster_frame=min(frames - 1, frames_for(asset.poster_ms, fps)),
        layers=layers,
        inputs=_inputs(asset, given),
    )


def pipeline_hash(library: Path) -> str:
    """SHA-256 of what turns a composition into files: render.ts and the exact packages (decision D-022)."""
    digest = hashlib.sha256()
    for name in ("scripts/render.ts", "package-lock.json"):
        digest.update(name.encode() + b"\0" + file_hash(library / name).encode())
    return digest.hexdigest()


IMPORT = re.compile(r"""(?:from|import)\s*['"](\.{1,2}/[^'"]+)['"]""")
ALWAYS = ("shared/frame.tsx", "shared/fonts.tsx")  # every composition is registered and gated through these


def shared_hash(asset: Asset) -> str:
    """SHA-256 of the library files outside the asset's folder that its sources import, transitively.

    Only what the asset uses enters its key, so adding a shared file for other assets keeps its renders
    (decision D-026).
    """
    root = asset.library_root.resolve()
    folder = asset.folder.resolve()
    todo = [p.resolve() for p in folder.glob("*.ts*")] + [root / name for name in ALWAYS]
    seen: set[Path] = set()
    while todo:
        path = todo.pop()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        if path.suffix in (".ts", ".tsx"):
            todo += [(path.parent / m).resolve() for m in IMPORT.findall(path.read_text(encoding="utf-8"))]
    digest = hashlib.sha256()
    for path in sorted(p for p in seen if not p.is_relative_to(folder) and p.is_relative_to(root)):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def key_inputs(job: RenderJob, renderer: Renderer) -> dict[str, Any]:
    """Every input of the cache key (design §8.4)."""
    library = job.asset.library_root
    return {
        "asset": job.asset.id,
        "asset_version": job.asset.version,
        "asset_hash": folder_hash(job.asset.folder),
        "shared_hash": shared_hash(job.asset),
        "fonts_hash": folder_hash(library / "fonts"),
        "pipeline_hash": pipeline_hash(library),
        "props": job.props,
        "input_files": {k: file_hash(v) for k, v in sorted(job.inputs.items())},
        "fps": job.fps,
        "width": job.width,
        "height": job.height,
        "frames": job.frames,
        "layers": job.layers,
        "renderer": {"name": renderer.name, "version": renderer.version},
    }


def render_key(inputs: Mapping[str, Any]) -> str:
    """SHA-256 of the canonical JSON of the key inputs."""
    canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _record(
    job: RenderJob,
    *,
    key: str,
    inputs: dict[str, Any],
    files: dict[str, Path],
    started: datetime,
    elapsed_ms: int,
) -> dict[str, Any]:
    transition = job.asset.transition
    layers = {
        name: {
            "file": files[name].name,
            "codec": ENCODINGS[fmt][1],
            "pixel_format": ENCODINGS[fmt][2],
            "bytes": files[name].stat().st_size,
        }
        for name, fmt in job.layers.items()
    }
    return {
        "format_version": "1",
        "key": key,
        "asset": job.asset.id,
        "asset_version": job.asset.version,
        "props": job.props,
        "fps": job.fps,
        "width": job.width,
        "height": job.height,
        "frames": job.frames,
        "duration_ms": job.duration_ms,
        "layers": layers,
        "cut_frame": frames_for(transition.cut_ms, job.fps) if transition else None,
        "blend": transition.fx_blend if transition else "normal",
        "poster": files["poster"].name,
        "renderer": inputs["renderer"],
        "inputs": inputs,
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "render_ms": elapsed_ms,
    }


def _rendered(record: dict[str, Any], folder: Path, cached: bool) -> Rendered:
    return Rendered(
        asset=record["asset"],
        key=record["key"],
        folder=folder,
        layers={name: folder / layer["file"] for name, layer in record["layers"].items()},
        poster=folder / record["poster"],
        cut_frame=record["cut_frame"],
        blend=record["blend"],
        frames=record["frames"],
        size=(record["width"], record["height"]),
        render_json=folder / "render.json",
        cached=cached,
    )


def cached(job: RenderJob, renderer: Renderer, cache: Cache) -> Rendered | None:
    """The render of this job if the cache has it, without rendering."""
    key = render_key(key_inputs(job, renderer))
    record = cache.read(key)
    return _rendered(record, cache.entry(key), True) if record else None


def run_job(job: RenderJob, renderer: Renderer, cache: Cache) -> Rendered:
    """Render the job once: from the cache when its key is there, else through the renderer into the cache."""
    inputs = key_inputs(job, renderer)
    key = render_key(inputs)

    def build(tmp: Path) -> dict[str, Any]:
        started = datetime.now(UTC)
        t0 = time.monotonic()
        files = renderer.render(job, tmp)
        return _record(
            job,
            key=key,
            inputs=inputs,
            files=files,
            started=started,
            elapsed_ms=round((time.monotonic() - t0) * 1000),
        )

    record, built = cache.create(key, build)
    return _rendered(record, cache.entry(key), cached=not built)


def render(
    asset: Asset,
    props: Mapping[str, Any] | None = None,
    *,
    fps: int = 32,
    aspect: str = "16:9",
    duration_ms: int | None = None,
    size: tuple[int, int] | None = None,
    formats: Mapping[str, Format] | None = None,
    renderer: Renderer | None = None,
    cache: Cache | None = None,
) -> Rendered:
    """Render an asset with these props (its example props when None), once per set of inputs (design §8).

    The default renderer is Remotion's (needs Node; see `hone_motif.remotion`), the default cache the user's
    (decision D-004). Raises InvalidPropsError, InvalidRenderError, RendererUnavailableError or RenderError.
    """
    job = plan(asset, props, fps=fps, aspect=aspect, duration_ms=duration_ms, size=size, formats=formats)
    return run_job(job, renderer or default_renderer(), cache or Cache())


def default_renderer() -> Renderer:
    """The Remotion renderer, imported only now: the core never loads it on import (design §14 case 11)."""
    from .remotion import RemotionRenderer  # noqa: PLC0415

    return RemotionRenderer()
