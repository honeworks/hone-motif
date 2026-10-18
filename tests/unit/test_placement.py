"""`check_placements` (design §7.3): every rule, its error code and the message a model acts on."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import hone_motif as hm
from tests.helpers import video

PILL = "like-subscribe-glass-pill"  # overlay, bottom-left, quiet_only, once per video
WATERMARK = "watermark-star-monogram"  # overlay, bottom-right, up to 4 per video
BELL = "bell-medallion-ring"  # overlay, top-right, corner prop
END = "two-videos-subscribe-calm-frames"  # end screen: last 5-20 s, ends with the video, clear frame
LEAK = "light-leak-amber-sweep"  # transition, cut at 1500 ms, up to 3 per video
CHAPTER = "chapter-card-star-band"  # scene, once per section, 20 s apart
TITLE = "title-reveal-ember-calligraphy"  # opening scene, starts in the first 2 s
NOW = "now-playing-equaliser-bilingual"  # overlay, bottom-left, first 30 s


def check(lib: hm.Library, *placements: dict[str, Any], **video_changes: Any) -> hm.PlacementReport:
    """Check the placements, each with its asset's example props under the props it gives."""
    filled = [
        {**p, "props": {**lib.get(p["asset"]).props, **p.get("props", {})}}
        if p.get("asset") in lib.assets
        else p
        for p in placements
    ]
    return hm.check_placements(filled, video(**video_changes), lib)


def codes(report: hm.PlacementReport) -> list[str]:
    return [p.code for p in report.errors]


def test_a_good_reply_passes_with_defaults_and_durations(lib: hm.Library) -> None:
    report = check(
        lib,
        {"asset": TITLE, "start_ms": 0, "props": {"title": "رستم و سهراب"}, "why": "the intro"},
        {"asset": LEAK, "start_ms": 41010 - 1500},
        {"asset": PILL, "start_ms": 31000, "props": {"channelName": "Hone Studio"}},
        {"asset": END, "start_ms": 214380 - 20000},
    )
    assert report.ok, report.errors
    title, leak, pill, end = report.placements
    assert title.duration_ms == 8000
    assert title.props["theme"] == "cinematic"
    assert title.why == "the intro"
    assert leak.duration_ms == 3000
    assert pill.props["likeLabel"] == "Like"  # filled from the schema's default
    assert end.end_ms == 214380  # an end screen without duration_ms runs to the video's end


def test_unknown_asset(lib: hm.Library) -> None:
    report = check(lib, {"asset": "no-such-thing", "start_ms": 0})
    assert codes(report) == ["unknown-asset"]
    assert report.errors[0].index == 0
    assert report.placements == []


def test_an_alias_warns_and_passes(lib_copy: Path) -> None:
    (lib_copy / "aliases.json").write_text('{"aliases": {"old-pill": "like-subscribe-glass-pill"}}')
    placement = {"asset": "old-pill", "start_ms": 31000, "props": {"channelName": "x"}}
    report = hm.check_placements([placement], video(), hm.Library(lib_copy))
    assert report.ok
    assert [w.code for w in report.warnings] == ["alias"]
    assert report.placements[0].asset == PILL


@pytest.mark.parametrize(
    "raw",
    [
        {"asset": PILL, "start_ms": 1.5},
        {"asset": PILL, "start_ms": -1},
        {"asset": PILL},
        {"asset": PILL, "start_ms": 0, "colour": "red"},
        {"asset": PILL, "start_ms": 0, "duration_ms": 6000.0},
    ],
)
def test_a_malformed_placement(lib: hm.Library, raw: dict[str, Any]) -> None:
    report = check(lib, raw)
    assert codes(report) == ["bad-placement"]
    assert "integer milliseconds" in report.errors[0].message


def test_invalid_props_carry_the_placement_index(lib: hm.Library) -> None:
    report = check(
        lib, {"asset": TITLE, "start_ms": 0}, {"asset": PILL, "start_ms": 31000, "props": {"x": 1}}
    )
    assert [(p.code, p.index) for p in report.errors] == [("unknown-prop", 1)]
    assert [p.asset for p in report.placements] == [TITLE]


def test_text_in_a_script_the_field_does_not_set(lib: hm.Library) -> None:
    report = check(lib, {"asset": TITLE, "start_ms": 0, "props": {"subtitle": "Ростам"}})
    assert codes(report) == ["script-not-allowed"]


def test_outside_the_video(lib: hm.Library) -> None:
    report = check(lib, {"asset": WATERMARK, "start_ms": 212000})
    assert codes(report) == ["outside-video"]
    assert "214380" in report.errors[0].message


def test_duration_out_of_range(lib: hm.Library) -> None:
    report = check(lib, {"asset": PILL, "start_ms": 31000, "duration_ms": 9000})
    assert codes(report) == ["duration-out-of-range"]
    assert "5000-8000" in report.errors[0].message


def test_window_from_the_start(lib: hm.Library) -> None:
    report = check(lib, {"asset": TITLE, "start_ms": 2500})
    assert codes(report) == ["outside-window"]
    assert "between 0 and 2000" in report.errors[0].message


@pytest.mark.parametrize(
    ("start", "ok"), [(214380 - 20000, True), (214380 - 5000, True), (214380 - 21000, False)]
)
def test_an_end_screen_starts_in_the_last_5_to_20_s(lib: hm.Library, start: int, ok: bool) -> None:
    report = check(lib, {"asset": END, "start_ms": start})
    assert report.ok is ok
    if not ok:
        assert "outside-window" in codes(report)


def test_an_end_screen_must_end_with_the_video(lib: hm.Library) -> None:
    report = check(lib, {"asset": END, "start_ms": 214380 - 20000, "duration_ms": 10000})
    assert codes(report) == ["must-end-with-video"]


def test_an_end_screen_needs_a_video_of_25_s(lib: hm.Library) -> None:
    report = check(lib, {"asset": END, "start_ms": 4000}, duration_ms=24000, cuts=[], sections=[], busy=[])
    assert codes(report) == ["video-too-short"]


def test_unsupported_aspect(lib: hm.Library) -> None:
    report = check(lib, {"asset": TITLE, "start_ms": 0}, aspect="9:16")
    assert codes(report) == ["aspect-unsupported"]


def test_platform_assets_need_their_platform_only_when_one_is_set(lib: hm.Library) -> None:
    end = {"asset": END, "start_ms": 214380 - 20000}
    assert check(lib, end, platform=None).ok


def test_quiet_only_over_a_busy_span(lib: hm.Library) -> None:
    report = check(lib, {"asset": PILL, "start_ms": 12000})
    assert codes(report) == ["over-busy"]
    assert "14000-30000" in report.errors[0].message


def test_a_transition_off_the_cut_says_where_to_start(lib: hm.Library) -> None:
    report = check(lib, {"asset": LEAK, "start_ms": 40000})
    assert codes(report) == ["off-cut"]
    assert "start at 39510 ms" in report.errors[0].message


def test_a_transition_within_half_a_frame_of_a_cut_passes(lib: hm.Library) -> None:
    assert check(lib, {"asset": LEAK, "start_ms": 41010 - 1500 + 15}).ok  # half a frame at 32 fps is 15.6 ms
    assert not check(lib, {"asset": LEAK, "start_ms": 41010 - 1500 + 16}).ok


def test_a_transition_in_a_video_without_cuts(lib: hm.Library) -> None:
    report = check(lib, {"asset": LEAK, "start_ms": 40000}, cuts=[])
    assert codes(report) == ["off-cut"]
    assert "nearest" not in report.errors[0].message


def test_repeat_per_video(lib: hm.Library) -> None:
    pill = {"asset": PILL}
    report = check(lib, {**pill, "start_ms": 31000}, {**pill, "start_ms": 130000})
    assert [(p.code, p.index) for p in report.errors] == [("repeat-per-video", 1)]
    assert len(report.placements) == 1


def test_repeat_per_section_and_gap(lib: hm.Library) -> None:
    report = check(lib, {"asset": CHAPTER, "start_ms": 60000}, {"asset": CHAPTER, "start_ms": 70000})
    assert sorted(codes(report)) == ["repeat-gap", "repeat-per-section"]
    assert "chorus-1" in next(p.message for p in report.errors if p.code == "repeat-per-section")
    spaced = check(lib, {"asset": CHAPTER, "start_ms": 30000}, {"asset": CHAPTER, "start_ms": 60000})
    assert spaced.ok, spaced.errors


def test_overlays_in_one_region_must_not_overlap(lib: hm.Library) -> None:
    report = check(
        lib,
        {"asset": NOW, "start_ms": 1000},
        {"asset": WATERMARK, "start_ms": 0},
        {"asset": PILL, "start_ms": 5000},
        busy=[],
    )
    assert [(p.code, p.index) for p in report.errors] == [("region-overlap", 2)]


def test_a_corner_prop_moves_the_region(lib: hm.Library) -> None:
    pill = {"asset": PILL, "start_ms": 31000}
    watermark = {"asset": WATERMARK, "start_ms": 30000}
    moved = {**pill, "props": {"corner": "bottom-right"}}
    assert check(lib, pill, watermark).ok
    assert codes(check(lib, moved, watermark)) == ["region-overlap"]


def test_nothing_shows_during_a_clear_frame_asset(lib: hm.Library) -> None:
    report = check(lib, {"asset": END, "start_ms": 214380 - 20000}, {"asset": WATERMARK, "start_ms": 200000})
    assert [(p.code, p.index) for p in report.errors] == [("clear-frame", 1)]
    assert [p.asset for p in report.placements] == [END]


def test_warnings_mixed_themes_moods_dense_transitions_and_scene_over_busy(lib: hm.Library) -> None:
    report = check(
        lib,
        {"asset": TITLE, "start_ms": 0, "props": {"theme": "pop"}},
        {"asset": LEAK, "start_ms": 6210 - 1500},
        {"asset": LEAK, "start_ms": 12040 - 1500},
        {"asset": CHAPTER, "start_ms": 13000},
    )
    assert report.ok, report.errors
    found = {p.code for p in report.warnings}
    assert found == {"mixed-themes", "mixed-moods", "dense-transitions", "scene-over-busy"}


def test_the_report_counts(lib: hm.Library) -> None:
    report = check(lib)
    assert report.ok
    assert report.placements == report.errors == report.warnings == []


def test_an_asset_for_another_platform(lib_copy: Path) -> None:
    data = json.loads((lib_copy / "assets" / END / "asset.json").read_text(encoding="utf-8"))
    data["platforms"] = ["vimeo"]
    (lib_copy / "assets" / END / "asset.json").write_text(json.dumps(data), encoding="utf-8")
    report = hm.check_placements([{"asset": END, "start_ms": 214380 - 20000}], video(), hm.Library(lib_copy))
    assert [p.code for p in report.errors] == ["wrong-platform"]
    assert "vimeo, not youtube" in report.errors[0].message


def test_a_corner_prop_moves_the_region_vertically(lib: hm.Library) -> None:
    bell = {"asset": BELL, "start_ms": 31000, "props": {"corner": "bottom-right"}}
    watermark = {"asset": WATERMARK, "start_ms": 30000}
    assert check(lib, {**bell, "props": {"corner": "top-right"}}, watermark).ok
    assert codes(check(lib, bell, watermark)) == ["region-overlap"]


def test_a_full_frame_overlay_claims_no_region(lib: hm.Library) -> None:
    report = check(
        lib, {"asset": "karaoke-fill-focus", "start_ms": 31000}, {"asset": PILL, "start_ms": 31000}, busy=[]
    )
    assert report.ok, report.errors


def test_an_asset_that_cannot_set_the_videos_scripts_warns(lib: hm.Library) -> None:
    report = check(lib, {"asset": PILL, "start_ms": 31000}, scripts=["Latn", "Cyrl"])
    assert report.ok
    assert [p.code for p in report.warnings] == ["scripts-differ"]
    assert "Cyrl" in report.warnings[0].message


def test_a_loop_may_last_as_long_as_the_video(lib: hm.Library) -> None:
    snow = lib.get("weather-snow-drift")
    assert snow.kind == "loop"
    whole = check(lib, {"asset": snow.id, "start_ms": 0, "duration_ms": 214380})
    assert whole.ok, whole.errors
    short = check(lib, {"asset": snow.id, "start_ms": 0, "duration_ms": snow.duration.min_ms - 1})
    assert codes(short) == ["duration-out-of-range"]
    assert "at least" in short.errors[0].message


def test_region_boxes_follow_centre_and_side_anchors(lib: hm.Library) -> None:
    from hone_motif.placement_rules import EDGE, Placed, region_box  # noqa: PLC0415

    bell = lib.get(BELL)  # default top-right, box (0.6, 0.04, 0.37, 0.14)
    x, y, w, h = bell.regions["16:9"].box  # pyright: ignore[reportAttributeAccessIssue]

    def box(corner: str) -> tuple[float, ...] | None:
        placed = Placed(index=0, asset=bell, start_ms=0, duration_ms=4000, props={"corner": corner}, why="")
        return region_box(placed, "16:9")

    assert box("top-right") == (x, y, w, h)
    assert box("top-left") == pytest.approx((1 - x - w, y, w, h))
    assert box("bottom-right") == pytest.approx((x, 1 - y - h, w, h))
    assert box("top-center") == pytest.approx((0.5 - w / 2, y, w, h))
    assert box("center-right") == pytest.approx((x, 0.5 - h / 2, w, h))
    assert box("center") == pytest.approx((0.5 - w / 2, 0.5 - h / 2, w, h))
    centred = bell.model_copy(update={"props": {**bell.props, "corner": "top-center"}})
    placed = Placed(
        index=0, asset=centred, start_ms=0, duration_ms=4000, props={"corner": "top-left"}, why=""
    )
    assert region_box(placed, "16:9") == pytest.approx((EDGE, y, w, h))
    placed = Placed(
        index=0, asset=centred, start_ms=0, duration_ms=4000, props={"corner": "top-right"}, why=""
    )
    assert region_box(placed, "16:9") == pytest.approx((1 - EDGE - w, y, w, h))


@pytest.mark.parametrize("reply", [None, "placements", {"asset": PILL, "start_ms": 0}, 7])
def test_a_reply_that_is_not_a_list_is_one_error(lib: hm.Library, reply: Any) -> None:
    report = hm.check_placements(reply, video(), lib)
    assert [p.code for p in report.errors] == ["bad-placement"]
    assert "a list of placements" in report.errors[0].message
    assert report.placements == []
