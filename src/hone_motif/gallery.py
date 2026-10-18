"""The gallery (design §10): a static page of every asset in every theme, from the catalogue and the cache."""

from __future__ import annotations

import json
import logging
import math
import os
from importlib.resources import files
from pathlib import Path
from typing import Any

from .asset import Asset
from .cache import Cache
from .errors import RendererUnavailableError
from .library import Library
from .prompt import catalog_entry
from .render import LAYOUT, Rendered, Renderer, cached, default_renderer, plan, run_job

log = logging.getLogger("hone_motif")


def _rel(path: Path, start: Path) -> str:
    return Path(os.path.relpath(path, start)).as_posix()


def preview_size(aspect: str, size: tuple[int, int]) -> tuple[int, int]:
    """The preview size for an aspect ratio, at the scale `size` gives 16:9 (960x540 -> 540x960 for 9:16)."""
    scale = size[0] / LAYOUT["16:9"][0]
    width, height = LAYOUT[aspect]
    unit = math.gcd(width, height)
    step_w, step_h = width // unit, height // unit  # the smallest size with this exact ratio
    k = max(1, round(width * scale / step_w))
    if step_w % 2 or step_h % 2:  # both sides must be even for the encoders
        k += k % 2
    return step_w * k, step_h * k


def _tile(asset: Asset, look: tuple[str, str], rendered: Rendered | None, out: Path) -> dict[str, Any]:
    theme, aspect = look
    tile: dict[str, Any] = {
        "asset": asset.id,
        "theme": theme,
        "aspect": aspect,
        "poster": None,
        "preview": None,
        "matte": None,
    }
    if rendered is not None:
        preview = rendered.layers.get("main") or rendered.layers.get("fx")
        tile.update(
            poster=_rel(rendered.poster, out),
            preview=_rel(preview, out) if preview else None,
            matte=_rel(rendered.layers["matte"], out) if "matte" in rendered.layers else None,
            render_json=_rel(rendered.render_json, out),
        )
    return tile


def _asset_entry(asset: Asset) -> dict[str, Any]:
    entry = catalog_entry(asset, asset.aspects[0])
    entry.update(
        category=asset.category,
        subcategory=asset.subcategory,
        scripts=asset.scripts,
        aspects=asset.aspects,
        tags=asset.tags,
        props=asset.props,
        licence=asset.licence,
        fonts=asset.fonts,
        origin=asset.origin.from_,
        props_schema=asset.props_schema,
    )
    return entry


def _poster_stills(renderer: Renderer, assets: list[Asset], cache: Cache) -> dict[str, Path]:
    from .remotion import RemotionRenderer, poster_stills  # noqa: PLC0415 - the adapter loads only when needed

    if not isinstance(renderer, RemotionRenderer):
        raise RendererUnavailableError("--stills needs the Remotion renderer, which renders the batch stills")
    return poster_stills(renderer, assets, cache)


def build_gallery(
    library: Library,
    *,
    cache: Cache | None = None,
    out: Path | None = None,
    render_missing: bool = False,
    size: tuple[int, int] = (960, 540),
    fps: int = 24,
    renderer: Renderer | None = None,
    stills: bool = False,
) -> Path:
    """Write the gallery's `index.html` (default `<cache>/gallery/`) and return its path.

    Each asset is shown in every theme and aspect ratio it supports with its example props;
    `render_missing` renders the previews not yet in the cache, once (needs the renderer). `stills`
    renders every poster still in one batch (the Remotion renderer; decision D-027), so every tile has a
    poster even where no preview is rendered.
    """
    cache = cache or Cache()
    out = out or cache.root / "gallery"
    out.mkdir(parents=True, exist_ok=True)
    renderer = renderer or default_renderer()
    order = list(library.vocabulary["categories"])
    assets = sorted(library.assets.values(), key=lambda a: (order.index(a.category), a.subcategory, a.id))
    posters = _poster_stills(renderer, assets, cache) if stills else {}
    tiles: list[dict[str, Any]] = []
    for asset in assets:
        for aspect in asset.aspects:
            for theme in asset.themes:
                props = {**asset.props, "theme": theme}
                job = plan(asset, props, fps=fps, aspect=aspect, size=preview_size(aspect, size))
                rendered = cached(job, renderer, cache)
                if rendered is None and render_missing:
                    log.info("rendering %s (%s, %s)", asset.id, theme, aspect)
                    rendered = run_job(job, renderer, cache)
                tile = _tile(asset, (theme, aspect), rendered, out)
                still = (
                    posters.get(asset.id, Path("-"))
                    / f"{theme if aspect == '16:9' else f'{theme}@{aspect}'}.jpg"
                )
                if tile["poster"] is None and still.is_file():
                    tile["poster"] = _rel(still, out)
                tiles.append(tile)
    data = {
        "assets": {a.id: _asset_entry(a) for a in assets},
        "tiles": tiles,
        "vocabulary": library.vocabulary,
    }
    page = files("hone_motif").joinpath("gallery.html").read_text(encoding="utf-8")
    index = out / "index.html"
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    index.write_text(page.replace("/*GALLERY_DATA*/null", payload), encoding="utf-8")
    return index
