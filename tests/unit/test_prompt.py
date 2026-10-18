"""What goes into the one placement call (design §7.2): catalogue entries, the reply schema, the guide."""

from __future__ import annotations

from typing import Any

import jsonschema
import pytest

import hone_motif as hm
from tests.helpers import video

END = "two-videos-subscribe-calm-frames"
LEAK = "light-leak-amber-sweep"
PILL = "like-subscribe-glass-pill"


def _has_key(node: Any, key: str) -> bool:
    if isinstance(node, dict):
        return key in node or any(_has_key(v, key) for v in node.values())  # pyright: ignore[reportUnknownVariableType,reportUnknownArgumentType]
    if isinstance(node, list):
        return any(_has_key(v, key) for v in node)  # pyright: ignore[reportUnknownVariableType]
    return False


def test_a_catalogue_entry_has_the_fields_of_7_2(lib: hm.Library) -> None:
    [entry] = lib.catalog([lib.get(PILL)], video())
    assert {"id", "name", "kind", "line", "themes", "moods", "slots", "when", "duration_ms", "region"} <= set(
        entry
    )
    assert {"text_fields", "props_schema", "repeat", "quiet_only"} <= set(entry)
    assert entry["region"] == {"anchor": "bottom-left", "box": (0.03, 0.72, 0.31, 0.24)}
    assert entry["repeat"] == {"max_per_video": 1}
    assert not _has_key(entry["props_schema"], "default")
    assert "$schema" not in entry["props_schema"]


def test_rules_appear_only_when_set(lib: hm.Library) -> None:
    end, leak = lib.catalog([lib.get(END), lib.get(LEAK)], video())
    assert end["window"] == {"from": "end", "earliest_ms": 20000, "latest_ms": 5000}
    assert end["ends_with_video"] is True
    assert end["clear_frame"] is True
    assert end["platforms"] == ["youtube"]
    assert end["min_video_ms"] == 25000
    assert "cut_ms" not in end
    assert leak["cut_ms"] == 1500
    assert leak["region"] == "full"
    assert "window" not in leak
    assert "quiet_only" not in leak


def test_the_schema_accepts_exactly_the_candidates(lib: hm.Library) -> None:
    schema = hm.placement_schema([lib.get(PILL), lib.get(LEAK)])
    jsonschema.Draft202012Validator.check_schema(schema)
    good = {"placements": [{"asset": PILL, "start_ms": 0, "duration_ms": 6000, "props": {}, "why": "x"}]}
    jsonschema.validate(good, schema)
    for bad in (
        {"placements": [{"asset": END, "start_ms": 0}]},
        {"placements": [{"asset": PILL, "start_ms": 1.5}]},
        {"placements": [{"asset": PILL}]},
        {"placements": [{"asset": PILL, "start_ms": 0, "extra": 1}]},
        {"placements": [], "notes": ""},
    ):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)


def test_the_guide_names_every_rule() -> None:
    guide = hm.placement_guide()
    for rule in ("integer milliseconds", "window", "ends_with_video", "repeat", "quiet_only", "clear_frame"):
        assert rule in guide
    assert "cut_ms" in guide
