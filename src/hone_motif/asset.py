"""The asset model: `asset.json` as a frozen pydantic model (design §2), read without Node."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

FORMAT_VERSION = "1"

Ms = Annotated[int, Field(strict=True, ge=0)]
"""A time in integer milliseconds; floats are rejected (design §2.3)."""

Kind = Literal["overlay", "scene", "transition", "background", "loop", "caption"]
Slot = Literal["opening", "closing", "end-screen", "section-start", "cut", "anywhere", "whole-video"]
Blend = Literal["normal", "screen"]
KEBAB = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class Duration(Frozen):
    default_ms: Ms
    min_ms: Ms
    max_ms: Ms

    @model_validator(mode="after")
    def _ordered(self) -> Duration:
        if not 0 < self.min_ms <= self.default_ms <= self.max_ms:
            raise ValueError("duration needs 0 < min_ms <= default_ms <= max_ms")
        return self


class BoxRegion(Frozen):
    """Where an asset draws, as fractions of the frame: [x, y, width, height]."""

    anchor: str
    box: tuple[float, float, float, float]

    @model_validator(mode="after")
    def _inside(self) -> BoxRegion:
        x, y, w, h = self.box
        if min(self.box) < 0 or w <= 0 or h <= 0 or x + w > 1.0001 or y + h > 1.0001:
            raise ValueError("box must lie inside the frame: 0 <= x, y and x + w, y + h <= 1")
        return self


Region = Literal["full"] | BoxRegion


class Window(Frozen):
    """Where a placement may start: `from` the video's start or end, between two offsets (design §2.5).

    From the start: earliest_ms <= start <= latest_ms. From the end, offsets count back from the end, so
    earliest_ms >= latest_ms: an end screen has earliest_ms 20000 and latest_ms 5000.
    """

    from_: Literal["start", "end"] = Field(alias="from")
    earliest_ms: Ms
    latest_ms: Ms

    @model_validator(mode="after")
    def _ordered(self) -> Window:
        ordered = (
            self.earliest_ms <= self.latest_ms
            if self.from_ == "start"
            else self.earliest_ms >= self.latest_ms
        )
        if not ordered:
            raise ValueError(
                "window from the start needs earliest_ms <= latest_ms; from the end, earliest_ms >= latest_ms"
            )
        return self

    def bounds(self, video_ms: int) -> tuple[int, int]:
        """The earliest and latest start, in milliseconds from the video's start."""
        if self.from_ == "start":
            return self.earliest_ms, self.latest_ms
        return video_ms - self.earliest_ms, video_ms - self.latest_ms


class Repeat(Frozen):
    max_per_video: Annotated[int, Field(strict=True, ge=1)] | None = None
    max_per_section: Annotated[int, Field(strict=True, ge=1)] | None = None
    min_gap_ms: Ms | None = None


class TextField(Frozen):
    prop: str  # a path into the props: "title", "lines[].name", "verse[0]"
    max_chars: Annotated[int, Field(strict=True, ge=1)]
    scripts: list[str] = Field(min_length=1)
    role: str


class InputSpec(Frozen):
    prop: str
    type: Literal["image"]


class Transition(Frozen):
    cut_ms: Ms
    fx_blend: Blend


class Media(Frozen):
    file: str
    licence: Literal["CC0-1.0"]
    source: str = Field(min_length=1)


class Origin(Frozen):
    from_: str = Field(alias="from", min_length=1)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class Asset(Frozen):
    """One asset: a distinct design and its metadata (design §2); load it with `Asset.load(folder)`."""

    format_version: Literal["1"]
    id: str = Field(pattern=KEBAB)
    name: str = Field(min_length=1, max_length=80)
    version: Annotated[int, Field(strict=True, ge=1)]
    category: str
    subcategory: str
    kind: Kind
    line: str = Field(min_length=1)
    tags: list[Annotated[str, Field(pattern=KEBAB)]]
    themes: list[str] = Field(min_length=1)
    moods: list[str] = Field(min_length=1)
    duration: Duration
    poster_ms: Ms
    aspects: list[str] = Field(min_length=1)
    regions: dict[str, Region]
    over_footage: bool = False
    slots: list[Slot] = Field(min_length=1)
    when: str = Field(min_length=1)
    window: Window | None = None
    ends_with_video: bool = False
    min_video_ms: Ms | None = None
    repeat: Repeat = Repeat()
    quiet_only: bool = False
    clear_frame: bool = False
    platforms: list[str] = []
    text_fields: list[TextField] = []
    scripts: list[str] = []
    languages: list[str] = []
    inputs: list[InputSpec] = []
    props: dict[str, Any]
    samples: dict[str, dict[str, Any]] = {}  # named props; "rtl": the right-to-left sample (§12)
    transition: Transition | None = None
    licence: str
    fonts: list[str] = []
    media: list[Media] = []
    origin: Origin

    _folder: Path = PrivateAttr(default=Path())
    _props_schema: dict[str, Any] = PrivateAttr(default_factory=dict)

    @model_validator(mode="after")
    def _consistent(self) -> Asset:
        if (self.kind == "transition") != (self.transition is not None):
            raise ValueError("`transition` is required for kind transition and only for it")
        if set(self.regions) != set(self.aspects):
            raise ValueError("`regions` needs exactly one entry per aspect ratio in `aspects`")
        if self.poster_ms > self.duration.default_ms:
            raise ValueError("poster_ms must lie within the default duration")
        if self.transition and not 0 < self.transition.cut_ms < self.duration.min_ms:
            raise ValueError("transition.cut_ms must lie inside the shortest duration")
        return self

    @classmethod
    def load(cls, folder: Path) -> Asset:
        """Read `asset.json` and `props.schema.json` from an asset's folder."""
        asset = cls.model_validate(json.loads((folder / "asset.json").read_text(encoding="utf-8")))
        asset._folder = folder
        schema_file = folder / "props.schema.json"
        if schema_file.exists():
            asset._props_schema = json.loads(schema_file.read_text(encoding="utf-8"))
        return asset

    @property
    def folder(self) -> Path:
        """The folder of the asset's sources."""
        return self._folder

    @property
    def library_root(self) -> Path:
        """The library folder this asset was loaded from (assets live in `<root>/assets/<id>/`)."""
        return self._folder.parents[1]

    @property
    def props_schema(self) -> dict[str, Any]:
        """The JSON Schema (2020-12) of the asset's props, exported from its zod schema (decision D-002)."""
        return self._props_schema

    def region(self, aspect: str) -> Region | None:
        """Where the asset draws at this aspect ratio, or None when it does not support it."""
        return self.regions.get(aspect)
