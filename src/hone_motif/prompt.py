"""What a consumer puts in its one placement call (design §7.2): catalogue, reply schema and guide."""

from __future__ import annotations

from typing import Any

from .asset import Asset, BoxRegion


def _without_defaults(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _without_defaults(v) for k, v in node.items() if k not in ("default", "$schema")}  # pyright: ignore[reportUnknownVariableType]
    if isinstance(node, list):
        return [_without_defaults(v) for v in node]  # pyright: ignore[reportUnknownVariableType]
    return node


def catalog_entry(asset: Asset, aspect: str) -> dict[str, Any]:
    """One candidate for the prompt: what it is, where it may go, what it takes (design §7.2)."""
    region = asset.region(aspect)
    entry: dict[str, Any] = {
        "id": asset.id,
        "name": asset.name,
        "kind": asset.kind,
        "line": asset.line,
        "themes": asset.themes,
        "moods": asset.moods,
        "slots": asset.slots,
        "when": asset.when,
        "duration_ms": asset.duration.model_dump(),
        "region": region.model_dump() if isinstance(region, BoxRegion) else region,
        "text_fields": [t.model_dump() for t in asset.text_fields],
        "props_schema": _without_defaults(asset.props_schema),
    }
    rules: dict[str, Any] = {
        "window": asset.window.model_dump(by_alias=True) if asset.window else None,
        "repeat": asset.repeat.model_dump(exclude_none=True) or None,
        "ends_with_video": asset.ends_with_video or None,
        "min_video_ms": asset.min_video_ms,
        "quiet_only": asset.quiet_only or None,
        "clear_frame": asset.clear_frame or None,
        "platforms": asset.platforms or None,
        "cut_ms": asset.transition.cut_ms if asset.transition else None,
    }
    entry.update({k: v for k, v in rules.items() if v is not None})
    return entry


def placement_schema(candidates: list[Asset]) -> dict[str, Any]:
    """The JSON Schema of the reply, `{"placements": [...]}`, with asset ids limited to the candidates."""
    placement = {
        "type": "object",
        "additionalProperties": False,
        "required": ["asset", "start_ms"],
        "properties": {
            "asset": {"enum": sorted(a.id for a in candidates)},
            "start_ms": {"type": "integer", "minimum": 0},
            "duration_ms": {"type": "integer", "minimum": 1},
            "props": {"type": "object"},
            "why": {"type": "string", "maxLength": 300},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["placements"],
        "properties": {"placements": {"type": "array", "items": placement}},
    }


GUIDE = """\
# Placing assets

Place assets across the whole video in one reply:
`{"placements": [{"asset", "start_ms", "duration_ms", "props", "why"}]}`.

- Times are integer milliseconds from the video's start. `duration_ms` is optional (the asset's
  default) and must lie in the asset's `duration_ms` range; a placement ends by the video's end. A
  `loop` is one cycle that repeats: give it any `duration_ms` from its minimum up, e.g. the whole video.
- Use only the candidates' ids, and only the props their `props_schema` lists. Text must fit
  `max_chars` and be in one of the field's `scripts`. `theme` is one of the asset's themes; keep one
  theme across the video unless the story turns.
- `window` limits where a placement starts: from the video's start, or counted back from its end.
  `ends_with_video` placements end exactly at the video's end; `min_video_ms` is the shortest video
  the asset may appear in.
- `repeat` limits how often an asset appears: per video, per section, and the gap between two.
- `quiet_only` assets must not overlap a busy span (singing, speech). Two overlays whose regions
  overlap must not show at the same time. Nothing else may show during a `clear_frame` asset.
- A transition's `start_ms + cut_ms` must fall on one of the video's cuts. Use transitions
  sparingly: at most one every 20 s.
- Follow each asset's `when` advice and match its moods to the video. Say briefly in `why` why each
  placement is there.
"""


def placement_guide() -> str:
    """The placement rules (design §7.2, §7.3) as short Markdown for the prompt."""
    return GUIDE
