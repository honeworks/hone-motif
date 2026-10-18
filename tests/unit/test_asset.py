"""The asset model (design §2): asset.json loads into a strict, frozen model."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

import hone_motif as hm
from hone_motif.asset import Window
from tests.conftest import FIXTURES


def _raw(asset_id: str = "like-subscribe-glass-pill") -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / asset_id / "asset.json").read_text(encoding="utf-8"))
    return data


def test_an_asset_loads_with_its_schema_and_folder(lib: hm.Library) -> None:
    asset = lib.get("like-subscribe-glass-pill")
    assert asset.kind == "overlay"
    assert asset.folder == lib.root / "assets" / "like-subscribe-glass-pill"
    assert asset.props_schema["properties"]["channelName"]["maxLength"] == 24


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError, match="extra"):
        hm.Asset.model_validate({**_raw(), "colour": "gold"})


@pytest.mark.parametrize("field", ["poster_ms", "min_video_ms"])
def test_float_times_are_rejected(field: str) -> None:
    with pytest.raises(ValidationError, match="integer"):
        hm.Asset.model_validate({**_raw(), field: 3600.0})


def test_float_duration_is_rejected() -> None:
    raw = _raw()
    raw["duration"]["default_ms"] = 6000.5
    with pytest.raises(ValidationError):
        hm.Asset.model_validate(raw)


def test_duration_must_be_ordered() -> None:
    raw = _raw()
    raw["duration"] = {"default_ms": 9000, "min_ms": 5000, "max_ms": 8000}
    with pytest.raises(ValidationError, match="min_ms <= default_ms <= max_ms"):
        hm.Asset.model_validate(raw)


def test_a_transition_needs_its_cut_and_only_transitions_have_one() -> None:
    raw = _raw("light-leak-amber-sweep")
    with pytest.raises(ValidationError, match="transition"):
        hm.Asset.model_validate({k: v for k, v in raw.items() if k != "transition"})
    with pytest.raises(ValidationError, match="transition"):
        hm.Asset.model_validate({**_raw(), "transition": {"cut_ms": 100, "fx_blend": "normal"}})


def test_cut_must_fall_inside_the_shortest_duration() -> None:
    raw = _raw("light-leak-amber-sweep")
    raw["transition"]["cut_ms"] = 3000
    with pytest.raises(ValidationError, match="cut_ms"):
        hm.Asset.model_validate(raw)


def test_regions_match_aspects_and_lie_inside_the_frame() -> None:
    raw = _raw()
    with pytest.raises(ValidationError, match="one entry per aspect"):
        hm.Asset.model_validate({**raw, "aspects": ["16:9", "9:16"]})
    raw["regions"]["16:9"]["box"] = [0.9, 0.5, 0.2, 0.2]
    with pytest.raises(ValidationError, match="inside the frame"):
        hm.Asset.model_validate(raw)


def test_poster_lies_within_the_default_duration() -> None:
    with pytest.raises(ValidationError, match="poster_ms"):
        hm.Asset.model_validate({**_raw(), "poster_ms": 6001})


def test_the_model_is_frozen(lib: hm.Library) -> None:
    with pytest.raises(ValidationError):
        lib.get("like-subscribe-glass-pill").name = "other"  # pyright: ignore[reportAttributeAccessIssue]


def test_window_bounds_from_the_start_and_from_the_end() -> None:
    assert Window.model_validate({"from": "start", "earliest_ms": 0, "latest_ms": 30000}).bounds(100000) == (
        0,
        30000,
    )
    assert Window.model_validate({"from": "end", "earliest_ms": 20000, "latest_ms": 5000}).bounds(100000) == (
        80000,
        95000,
    )


@pytest.mark.parametrize(("frm", "earliest", "latest"), [("start", 5000, 0), ("end", 5000, 20000)])
def test_window_offsets_must_be_ordered(frm: str, earliest: int, latest: int) -> None:
    with pytest.raises(ValidationError, match="window"):
        Window.model_validate({"from": frm, "earliest_ms": earliest, "latest_ms": latest})


def test_asset_json_round_trips_through_the_model() -> None:
    raw = _raw("two-videos-subscribe-calm-frames")
    assert hm.Asset.model_validate(raw).model_dump(by_alias=True, exclude_defaults=True) == raw
