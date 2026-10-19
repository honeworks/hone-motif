"""`check_placements`: every placement of a reply against its asset and the video (design §7.3)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import Field, ValidationError

from .asset import Frozen, Ms
from .errors import Problem, UnknownAssetError
from .library import Library
from .placement_rules import Placed, single_rules, video_rules, warnings
from .props import brand_warnings, check_props, fill_defaults
from .video import VideoInfo


class PlacementIn(Frozen):
    """One placement as the model wrote it."""

    asset: str
    start_ms: Ms
    duration_ms: Ms | None = None
    props: dict[str, Any] = {}
    why: str = ""


class Placement(Frozen):
    """A placement that passed: complete props (defaults filled) and a resolved duration (design §7.3)."""

    asset: str
    start_ms: Ms
    duration_ms: Ms
    props: dict[str, Any]
    why: str = ""

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.duration_ms


class PlacementReport(Frozen):
    """What `check_placements` found: errors to repair, warnings, and the placements that passed."""

    placements: list[Placement] = Field(default_factory=list[Placement])
    errors: list[Problem] = Field(default_factory=list[Problem])
    warnings: list[Problem] = Field(default_factory=list[Problem])

    @property
    def ok(self) -> bool:
        return not self.errors


def _parse(index: int, raw: Any) -> PlacementIn | Problem:
    try:
        return PlacementIn.model_validate(raw)
    except ValidationError as e:
        details = "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors())
        return Problem(
            code="bad-placement", index=index, message=f"{details} (times are integer milliseconds)"
        )


def _resolve(
    index: int, raw: Any, video: VideoInfo, lib: Library
) -> tuple[Placed | None, list[Problem], list[Problem]]:
    """The placement with its asset, duration and full props, its own errors, and warnings."""
    parsed = _parse(index, raw)
    if isinstance(parsed, Problem):
        return None, [parsed], []
    try:
        asset = lib.get(parsed.asset)
    except UnknownAssetError as e:
        return None, [Problem(code="unknown-asset", index=index, asset=parsed.asset, message=str(e))], []
    notes = [p.model_copy(update={"index": index}) for p in brand_warnings(parsed.props, asset.id)]
    if asset.id != parsed.asset:
        notes.append(
            Problem(code="alias", index=index, asset=parsed.asset, message=f"renamed: use {asset.id}")
        )
    duration = parsed.duration_ms
    if duration is None:
        duration = video.duration_ms - parsed.start_ms if asset.ends_with_video else asset.duration.default_ms
    props = fill_defaults(asset, parsed.props)
    errors = [p.model_copy(update={"index": index}) for p in check_props(asset, parsed.props)]
    placed = Placed(
        index=index, asset=asset, start_ms=parsed.start_ms, duration_ms=duration, props=props, why=parsed.why
    )
    return placed, errors, notes


def _is_list(reply: object) -> bool:
    return isinstance(reply, Sequence) and not isinstance(reply, str | bytes)


def check_placements(
    placements: Sequence[Mapping[str, Any]], video: VideoInfo, library: Library
) -> PlacementReport:
    """Check a whole reply's placements; errors and warnings say what to change (design §7.3)."""
    if not _is_list(placements):  # a model's reply: its type is not to be trusted
        message = f"the reply must hold a list of placements, not {type(placements).__name__}"
        return PlacementReport(errors=[Problem(code="bad-placement", message=message)])
    errors: list[Problem] = []
    notes: list[Problem] = []
    placed: list[Placed] = []
    for index, raw in enumerate(placements):
        one, its_errors, its_notes = _resolve(index, raw, video, library)
        errors += its_errors
        notes += its_notes
        if one is not None:
            placed.append(one)
            errors += single_rules(one, video)
    errors += video_rules(placed, video)
    failed = {p.index for p in errors}
    passed = [
        Placement(asset=p.asset.id, start_ms=p.start_ms, duration_ms=p.duration_ms, props=p.props, why=p.why)
        for p in placed
        if p.index not in failed
    ]
    return PlacementReport(placements=passed, errors=errors, warnings=notes + warnings(placed, video))
