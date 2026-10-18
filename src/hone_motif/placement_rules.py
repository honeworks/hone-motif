"""The rules of design §7.3, each a small function returning problems."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations, pairwise
from typing import Any

from .asset import Asset, BoxRegion
from .errors import Problem
from .video import Span, VideoInfo

LAYERED = ("overlay", "loop", "caption")  # kinds that claim a region of the frame


@dataclass(frozen=True)
class Placed:
    """A placement resolved against its asset: duration known, props complete."""

    index: int
    asset: Asset
    start_ms: int
    duration_ms: int
    props: dict[str, Any]
    why: str

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.duration_ms

    def problem(self, code: str, message: str, field: str | None = None) -> Problem:
        return Problem(code=code, index=self.index, asset=self.asset.id, field=field, message=message)


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def _time_rules(p: Placed, video: VideoInfo) -> list[Problem]:
    a = p.asset
    found: list[Problem] = []
    if p.end_ms > video.duration_ms:
        found.append(
            p.problem(
                "outside-video", f"ends at {p.end_ms} ms, after the video's end at {video.duration_ms} ms"
            )
        )
    longest = None if a.kind == "loop" else a.duration.max_ms  # a loop repeats for any length (D-023)
    if p.duration_ms < a.duration.min_ms or (longest is not None and p.duration_ms > longest):
        span = f"at least {a.duration.min_ms}" if longest is None else f"{a.duration.min_ms}-{longest}"
        found.append(
            p.problem(
                "duration-out-of-range", f"{p.duration_ms} ms; this asset lasts {span} ms", "duration_ms"
            )
        )
    if a.window:
        earliest, latest = a.window.bounds(video.duration_ms)
        if not earliest <= p.start_ms <= latest:
            found.append(
                p.problem(
                    "outside-window",
                    f"starts at {p.start_ms} ms; it must start between {earliest} and {latest} ms",
                    "start_ms",
                )
            )
    return found


def _video_length_rules(p: Placed, video: VideoInfo) -> list[Problem]:
    a = p.asset
    found: list[Problem] = []
    if a.ends_with_video and p.end_ms != video.duration_ms:
        found.append(
            p.problem(
                "must-end-with-video",
                f"ends at {p.end_ms} ms; it must end at the video's end, {video.duration_ms} ms",
            )
        )
    if a.min_video_ms is not None and video.duration_ms < a.min_video_ms:
        found.append(
            p.problem(
                "video-too-short",
                f"needs a video of at least {a.min_video_ms} ms; this one is {video.duration_ms} ms",
            )
        )
    return found


def _frame_rules(p: Placed, video: VideoInfo) -> list[Problem]:
    a = p.asset
    found: list[Problem] = []
    if video.aspect not in a.aspects:
        found.append(p.problem("aspect-unsupported", f"made for {', '.join(a.aspects)}, not {video.aspect}"))
    if video.platform is not None and a.platforms and video.platform not in a.platforms:
        found.append(p.problem("wrong-platform", f"made for {', '.join(a.platforms)}, not {video.platform}"))
    if a.quiet_only:
        busy = [s for s in video.busy if overlaps(p.start_ms, p.end_ms, s.start_ms, s.end_ms)]
        if busy:
            found.append(
                p.problem(
                    "over-busy",
                    f"must not overlap singing or speech; it overlaps {busy[0].start_ms}-{busy[0].end_ms} ms",
                )
            )
    if a.transition:
        cut = p.start_ms + a.transition.cut_ms
        tolerance = 500 / video.fps  # half a frame
        if not any(abs(cut - c) <= tolerance for c in video.cuts):
            nearest = min(video.cuts, key=lambda c: abs(c - cut), default=None)
            hint = (
                f"; the nearest cut is {nearest} ms, so start at {nearest - a.transition.cut_ms} ms"
                if nearest is not None
                else ""
            )
            found.append(
                p.problem("off-cut", f"its cut falls at {cut} ms, on no cut of the video{hint}", "start_ms")
            )
    return found


def single_rules(p: Placed, video: VideoInfo) -> list[Problem]:
    """The rules one placement must meet on its own."""
    return _time_rules(p, video) + _video_length_rules(p, video) + _frame_rules(p, video)


def _section_of(p: Placed, video: VideoInfo) -> str | None:
    return next((s.id for s in video.sections if s.start_ms <= p.start_ms < s.end_ms), None)


def _repeat_rules(placed: list[Placed], video: VideoInfo) -> list[Problem]:
    found: list[Problem] = []
    by_asset: dict[str, list[Placed]] = {}
    for p in placed:
        by_asset.setdefault(p.asset.id, []).append(p)
    for group in by_asset.values():
        rule = group[0].asset.repeat
        ordered = sorted(group, key=lambda p: p.start_ms)
        if rule.max_per_video is not None:
            found += [
                p.problem("repeat-per-video", f"at most {rule.max_per_video} per video")
                for p in ordered[rule.max_per_video :]
            ]
        if rule.max_per_section is not None:
            seen: Counter[str | None] = Counter()
            for p in ordered:
                section = _section_of(p, video)
                seen[section] += 1
                if section is not None and seen[section] > rule.max_per_section:
                    found.append(
                        p.problem(
                            "repeat-per-section", f"at most {rule.max_per_section} per section ({section})"
                        )
                    )
        if rule.min_gap_ms is not None:
            found += [
                b.problem(
                    "repeat-gap",
                    f"starts {b.start_ms - a.end_ms} ms after the previous one; "
                    f"the gap must be at least {rule.min_gap_ms} ms",
                )
                for a, b in pairwise(ordered)
                if b.start_ms - a.end_ms < rule.min_gap_ms
            ]
    return found


def region_box(p: Placed, aspect: str) -> tuple[float, float, float, float] | None:
    """The placement's box in the frame, mirrored to its `corner` prop; None for a full-frame region."""
    region = p.asset.region(aspect)
    if not isinstance(region, BoxRegion):
        return None
    x, y, w, h = region.box
    default = _parts(str(p.asset.props.get("corner", "")))
    corner = _parts(str(p.props.get("corner", ""))) if p.props.get("corner") else default
    if default is None or corner is None:
        return x, y, w, h
    return _move(default[1], corner[1], x, w), _move(default[0], corner[0], y, h), w, h


EDGE = 0.05  # where a box moved out of the centre sits: the title-safe margin


def _parts(anchor: str) -> tuple[str, str] | None:
    """An anchor as (vertical, horizontal): "top-left" -> (top, left), "center-right" -> (center, right)."""
    if not anchor:
        return None
    vertical, _, horizontal = anchor.partition("-")
    return (vertical, horizontal or "center") if anchor != "center" else ("center", "center")


def _move(was: str, now: str, start: float, size: float) -> float:
    """A box's start along one axis when its anchor moves from `was` to `now` (left/center/right)."""
    if was == now:
        return start
    if now == "center":
        return 0.5 - size / 2
    if was == "center":
        return EDGE if now in ("left", "top") else 1 - EDGE - size
    return 1 - start - size  # mirrored to the opposite edge


def _boxes_meet(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def _frame_sharing(placed: list[Placed], video: VideoInfo) -> list[Problem]:
    found: list[Problem] = []
    for a, b in combinations(sorted(placed, key=lambda p: p.index), 2):
        if not overlaps(a.start_ms, a.end_ms, b.start_ms, b.end_ms):
            continue
        for first, other in ((a, b), (b, a)):
            if first.asset.clear_frame:
                found.append(
                    other.problem(
                        "clear-frame",
                        f"shows during {first.asset.id} (#{first.index}), which needs a clear frame",
                    )
                )
        if a.asset.kind in LAYERED and b.asset.kind in LAYERED:
            box_a, box_b = region_box(a, video.aspect), region_box(b, video.aspect)
            if box_a and box_b and _boxes_meet(box_a, box_b):
                found.append(
                    b.problem(
                        "region-overlap",
                        f"its region overlaps {a.asset.id} (#{a.index}) while both show; "
                        "move one in time or to another corner",
                    )
                )
    return found


def video_rules(placed: list[Placed], video: VideoInfo) -> list[Problem]:
    """The rules placements must meet together."""
    return _repeat_rules(placed, video) + _frame_sharing(placed, video)


def _themes_and_moods(placed: list[Placed]) -> list[Problem]:
    found: list[Problem] = []
    themes = Counter(str(p.props.get("theme")) for p in placed)
    if len(themes) > 1:
        main = themes.most_common(1)[0][0]
        found += [
            p.problem(
                "mixed-themes", f"theme {p.props.get('theme')}; most placements use {main}", "props.theme"
            )
            for p in placed
            if p.props.get("theme") != main
        ]
    moods = Counter(m for p in placed for m in p.asset.moods if m != "any")
    if moods:
        main_mood = moods.most_common(1)[0][0]
        found += [
            p.problem(
                "mixed-moods",
                f"its moods ({', '.join(p.asset.moods)}) differ from the video's main mood, {main_mood}",
            )
            for p in placed
            if "any" not in p.asset.moods and main_mood not in p.asset.moods
        ]
    return found


def _scripts(placed: list[Placed], video: VideoInfo) -> list[Problem]:
    """Assets with text that cannot set every script of the video's text."""
    return [
        p.problem(
            "scripts-differ",
            f"sets {', '.join(p.asset.scripts)}; the video's text also uses "
            f"{', '.join(sorted(set(video.scripts) - set(p.asset.scripts)))}",
        )
        for p in placed
        if p.asset.text_fields and not set(video.scripts) <= set(p.asset.scripts)
    ]


def warnings(placed: list[Placed], video: VideoInfo) -> list[Problem]:
    """What may be fine but deserves a look (design §7.3)."""
    found = _themes_and_moods(placed) + _scripts(placed, video)
    starts = sorted((p for p in placed if p.asset.kind == "transition"), key=lambda p: p.start_ms)
    found += [
        b.problem(
            "dense-transitions",
            f"{b.start_ms - a.start_ms} ms after the previous transition; keep them 20 s apart",
        )
        for a, b in pairwise(starts)
        if b.start_ms - a.start_ms < 20000
    ]
    busy: list[Span] = video.busy
    found += [
        p.problem("scene-over-busy", "a scene over singing or speech hides the main action")
        for p in placed
        if p.asset.kind == "scene"
        and not p.asset.quiet_only
        and any(overlaps(p.start_ms, p.end_ms, s.start_ms, s.end_ms) for s in busy)
    ]
    return found
