"""hone-motif: code-built video assets, searched, placed in one whole-video call, checked and rendered once.

The design is in design/current.md (accepted in design/changes/0001). Everything here works from the
asset.json files alone; only rendering needs Node, through `hone_motif.remotion` (design §8).
"""

from .asset import Asset
from .cache import Cache, default_cache_root
from .compose import ComposeLayer, FilterGraph, compose_filter
from .errors import (
    HoneMotifError,
    InvalidAssetError,
    InvalidPropsError,
    InvalidRenderError,
    Problem,
    RenderError,
    RendererUnavailableError,
    UnknownAssetError,
)
from .gallery import build_gallery
from .library import Library
from .placement import Placement, PlacementReport, check_placements
from .prompt import placement_guide, placement_schema
from .props import brand_warnings, check_props
from .render import Rendered, Renderer, RenderJob, render
from .video import Section, Span, VideoInfo

__all__ = [
    "Asset",
    "Cache",
    "ComposeLayer",
    "FilterGraph",
    "HoneMotifError",
    "InvalidAssetError",
    "InvalidPropsError",
    "InvalidRenderError",
    "Library",
    "Placement",
    "PlacementReport",
    "Problem",
    "RenderError",
    "RenderJob",
    "Rendered",
    "Renderer",
    "RendererUnavailableError",
    "Section",
    "Span",
    "UnknownAssetError",
    "VideoInfo",
    "__version__",
    "brand_warnings",
    "build_gallery",
    "check_placements",
    "check_props",
    "compose_filter",
    "default_cache_root",
    "placement_guide",
    "placement_schema",
    "render",
]

__version__ = "0.1.0"
