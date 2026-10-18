"""Real renders (design §12, §14 cases 13, 14 and 17): golden posters, alpha, mattes, cut frames, fit.

Run only through the machine-wide lock: `scripts/gpu-lock.sh uv run pytest -m render`. Posters are
stills at 960x540 (16:9; other aspects at the same scale), rendered in one batch and kept in the user's
cache by key (decision D-027); alpha and matte tests render small videos (480x270 at 8 fps). After an
intended visual change, `HONE_MOTIF_UPDATE_GOLDEN=1` rewrites tests/golden/posters.json; say why in the
commit.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Iterator
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest

import hone_motif as hm
from hone_motif.asset import BoxRegion
from hone_motif.library_check import RTL_SCRIPTS
from hone_motif.remotion import RemotionRenderer, poster_stills
from tests.render.phash import Box, distance, mean_difference, mean_rgb, phash

pytestmark = pytest.mark.render

ROOT = Path(__file__).parents[2]
GOLDEN = ROOT / "tests" / "golden" / "posters.json"
LIB = hm.Library(ROOT / "library")
SIZE = (480, 270)  # alpha and matte renders
TEXT_SIZE = (960, 540)  # right-to-left samples: large enough for letter shapes to count
FPS = 8
MAX_DISTANCE = 6  # of 64 bits (decision D-007)
MAX_TEXT_DISTANCE = 24  # of 256 bits
MAX_COLOUR = 12  # per channel, of 255
UPDATE = os.environ.get("HONE_MOTIF_UPDATE_GOLDEN") == "1"
POSTERS = [(a.id, theme, aspect) for a in LIB.assets.values() for aspect in a.aspects for theme in a.themes]
RTL = [a.id for a in LIB.assets.values() if RTL_SCRIPTS.intersection(a.scripts) and "rtl" in a.samples]
Golden = dict[str, dict[str, dict[str, Any]]]


def _golden() -> Golden:
    return json.loads(GOLDEN.read_text(encoding="utf-8")) if GOLDEN.is_file() else {}


FOUND: Golden = {}


@pytest.fixture(scope="module", autouse=True)
def write_golden() -> Iterator[None]:
    yield
    if UPDATE:  # rewrite what this run checked; keep what it did not run (e.g. with -k)
        merged = {a: {**_golden().get(a, {}), **FOUND.get(a, {})} for a in LIB.assets}
        names = {
            a.id: {*(_name(t, x) for x in a.aspects for t in a.themes), *(["rtl"] if a.id in RTL else [])}
            for a in LIB.assets.values()
        }
        ordered = {a: {n: merged[a][n] for n in sorted(merged[a]) if n in names[a]} for a in sorted(merged)}
        GOLDEN.write_text(
            json.dumps({a: v for a, v in ordered.items() if v}, indent=1) + "\n", encoding="utf-8"
        )


def _name(theme: str, aspect: str) -> str:
    """The golden's key: the theme, with the aspect ratio when it is not 16:9 (`warm@9:16`)."""
    return theme if aspect == "16:9" else f"{theme}@{aspect}"


def _text_box(asset: hm.Asset, aspect: str = "16:9") -> Box | None:
    region = asset.region(aspect)
    return region.box if isinstance(region, BoxRegion) else None


def _measure(asset: hm.Asset, name: str, poster: Path) -> dict[str, Any]:
    """The hash and the mean colour of the asset's region (an overlay's colours, not the backdrop's)."""
    box = _text_box(asset, name.split("@")[1] if "@" in name else "16:9")
    if name == "rtl":
        return {"phash": phash(poster, keep=16, box=box), "rgb": mean_rgb(poster, box)}
    return {"phash": phash(poster), "rgb": mean_rgb(poster, box)}


def _check(asset: hm.Asset, name: str, poster: Path) -> None:
    found = _measure(asset, name, poster)
    if UPDATE:
        FOUND.setdefault(asset.id, {})[name] = found
        return
    golden = _golden().get(asset.id, {}).get(name)
    assert golden is not None, f"no golden hash for {asset.id} ({name}): run with HONE_MOTIF_UPDATE_GOLDEN=1"
    limit = MAX_TEXT_DISTANCE if name == "rtl" else MAX_DISTANCE
    assert distance(found["phash"], golden["phash"]) <= limit, (
        f"{asset.id} ({name}) looks different: {poster}"
    )
    colour = max(abs(a - b) for a, b in zip(found["rgb"], golden["rgb"], strict=True))
    assert colour <= MAX_COLOUR, f"{asset.id} ({name}) has other colours: {poster}"


@pytest.fixture(scope="module")
def stills() -> dict[str, Path]:
    """Every poster still, rendered in batch and kept by key (decision D-027)."""
    return poster_stills(RemotionRenderer(), list(LIB.assets.values()), hm.Cache())


def _still(stills: dict[str, Path], asset_id: str, name: str) -> Path:
    assert asset_id in stills, (
        f"the stills of {asset_id} did not render (`npm run stills -- <dir> {asset_id}`)"
    )
    return stills[asset_id] / f"{name}.jpg"


@pytest.mark.parametrize(
    ("asset_id", "theme", "aspect"), POSTERS, ids=[f"{a}-{_name(t, x)}" for a, t, x in POSTERS]
)
def test_ac13_every_poster_matches_its_golden_hash(
    stills: dict[str, Path], asset_id: str, theme: str, aspect: str
) -> None:
    name = _name(theme, aspect)
    _check(LIB.get(asset_id), name, _still(stills, asset_id, name))


@pytest.mark.timeout(1800)
def test_the_themes_of_an_asset_look_different(stills: dict[str, Path]) -> None:
    """A theme that changed nothing would pass its own golden; in every aspect, some theme's still must
    differ in colour from the first theme's (pixels, as a thin callout barely moves a mean colour)."""
    same = []
    for asset in LIB.assets.values():
        for aspect in asset.aspects:
            first, *others = (_name(t, aspect) for t in asset.themes)
            base = _still(stills, asset.id, first)
            if others and not any(
                mean_difference(base, _still(stills, asset.id, o), fmt="rgb24") > 0 for o in others
            ):
                same.append(f"{asset.id} ({aspect})")
    assert same == [], f"every theme looks the same: {same}"


@pytest.mark.parametrize("asset_id", RTL)
def test_ac14_the_rtl_sample_renders_as_whole_words(stills: dict[str, Path], asset_id: str) -> None:
    asset = LIB.get(asset_id)
    rtl = _still(stills, asset_id, "rtl")
    _check(asset, "rtl", rtl)
    # the right-to-left poster must differ from the Latin one (it is rendered at all)
    latin = str(asset.props["theme"])
    difference = mean_difference(rtl, _still(stills, asset_id, latin), _text_box(asset))
    assert difference > 0, f"{asset_id}: the right-to-left sample looks like the Latin one; is it rendered?"


def test_ac14_the_text_hash_sees_letters_pulled_apart() -> None:
    """The negative control: the same right-to-left title with every letter forced apart (a zero-width
    non-joiner between letters) must miss the golden, or the golden could not catch split letters."""
    asset = LIB.get("big-title-clean-rise")
    sample = asset.samples["rtl"]
    split = {**sample, "title": "\u200c".join(sample["title"])}
    assert len(split["title"]) <= 32  # the title's limit
    whole = hm.render(asset, sample, fps=FPS, size=TEXT_SIZE)
    apart = hm.render(asset, split, fps=FPS, size=TEXT_SIZE)
    assert distance(phash(whole.poster, keep=16), phash(apart.poster, keep=16)) > MAX_TEXT_DISTANCE


def _render(asset: hm.Asset, props: dict[str, Any]) -> hm.Rendered:
    return hm.render(asset, props, fps=FPS, size=SIZE)


def _frame(video: Path, index: int, filters: str) -> bytes:
    """One decoded frame as raw grey bytes (VP9 alpha needs the libvpx decoder)."""
    decoder = ["-c:v", "libvpx-vp9"] if video.suffix == ".webm" else []
    return subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            *decoder,
            "-i",
            str(video),
            "-vf",
            f"select=eq(n\\,{index}),{filters}",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-",
        ],
        capture_output=True,
        check=True,
    ).stdout


ALPHA = [a.id for a in LIB.assets.values() if a.kind in ("overlay", "caption")]


@pytest.mark.parametrize("asset_id", ALPHA)
def test_overlays_and_captions_have_alpha(asset_id: str) -> None:
    asset = LIB.get(asset_id)
    done = _render(asset, dict(asset.props))
    alpha = _frame(done.layers["main"], done.frames // 2, "format=yuva420p,alphaextract,format=gray")
    assert alpha, "no frame decoded"
    assert min(alpha) == 0, "nothing is transparent"
    assert max(alpha) > 64, "nothing is drawn (a watermark may be half transparent)"


TRANSITIONS = [a.id for a in LIB.assets.values() if a.kind == "transition"]


@pytest.mark.parametrize("asset_id", TRANSITIONS)
def test_transitions_matte_runs_black_to_white(asset_id: str) -> None:
    asset = LIB.get(asset_id)
    assert asset.transition is not None
    done = _render(asset, dict(asset.props))
    assert done.cut_frame == round(asset.transition.cut_ms * FPS / 1000)

    def mean(index: int) -> float:
        pixels = _frame(done.layers["matte"], index, "format=gray")
        return sum(pixels) / len(pixels)

    assert mean(0) < 8, "the first matte frame must be black (the outgoing shot)"
    assert mean(done.frames - 1) > 247, "the last matte frame must be white (the incoming shot)"
    assert done.cut_frame is not None
    cut, last = done.cut_frame, done.frames - 1
    means = [mean(i) for i in (0, cut // 2, cut, (cut + last) // 2, last)]
    assert all(b >= a - 2 for a, b in pairwise(means)), f"the matte must only grow: {means}"


def test_a_tall_render_matches_its_still(stills: dict[str, Path]) -> None:
    """render.ts lays a 9:16 job out in its own frame (D-024), and its poster shows what the batch still
    shows (D-027)."""
    asset = next(a for a in LIB.assets.values() if a.kind == "overlay" and "9:16" in a.aspects)
    done = hm.render(
        asset, {**asset.props, "theme": asset.themes[0]}, fps=FPS, aspect="9:16", size=(540, 960)
    )
    assert done.size == (540, 960)
    still = _still(stills, asset.id, f"{asset.themes[0]}@9:16")
    assert distance(phash(done.poster), phash(still)) <= MAX_DISTANCE + 4


# Case 17: text at its longest stays in its region and the title-safe area, in every aspect.
LONGEST = {"Latn": "WMQW ", "Arab": "مشمش "}  # wide letters, with spaces to break on
SAFE = (0.05, 0.05, 0.9, 0.9)  # the title-safe area: 90% of the frame
SLACK = 0.01  # of the frame, for anti-aliased edges
ANCHORS = ("default", "top-right", "center")
FITS = [
    (a.id, aspect, script, anchor)
    for a in LIB.assets.values()
    if a.kind == "overlay" and a.text_fields
    for aspect in a.aspects
    for script in sorted({s for f in a.text_fields for s in f.scripts} & set(LONGEST))
    for anchor in (ANCHORS if "corner" in a.props else ("default",))
]
Rect = tuple[float, float, float, float]


def _longest(asset: hm.Asset, script: str, anchor: str) -> dict[str, Any]:
    props = dict(asset.props)
    for field in asset.text_fields:
        assert not set(field.prop) & {"[", "."}, "nested text fields: extend _longest"
        if script in field.scripts:
            props[field.prop] = (LONGEST[script] * field.max_chars)[: field.max_chars].strip()
    if anchor != "default":
        props["corner"] = anchor
    return props


def _drawn(video: Path, index: int, size: tuple[int, int]) -> Rect:
    """The box (x, y, w, h as fractions of the frame) of every pixel the frame draws (alpha > 8)."""
    width, height = size
    alpha = _frame(video, index, "format=yuva420p,alphaextract,format=gray")
    rows = [y for y in range(height) if max(alpha[y * width : (y + 1) * width]) > 8]
    cols = [x for x in range(width) if max(alpha[x::width]) > 8]
    assert rows, "nothing is drawn"
    x, y = cols[0] / width, rows[0] / height
    return x, y, (cols[-1] + 1) / width - x, (rows[-1] + 1) / height - y


def _outside(inner: Rect, outer: Rect) -> list[str]:
    """The edges of `inner` that cross `outer` by more than SLACK."""
    (x, y, w, h), (ox, oy, ow, oh) = inner, outer
    edges = {"left": ox - x, "top": oy - y, "right": x + w - ox - ow, "bottom": y + h - oy - oh}
    return [f"{edge} by {over:.3f}" for edge, over in edges.items() if over > SLACK]


@pytest.mark.parametrize(("asset_id", "aspect", "script", "anchor"), FITS)
def test_ac17_the_longest_text_stays_in_its_region(
    asset_id: str, aspect: str, script: str, anchor: str
) -> None:
    from hone_motif.placement_rules import Placed, region_box  # noqa: PLC0415

    asset = LIB.get(asset_id)
    props = _longest(asset, script, anchor)
    assert hm.check_props(asset, props) == []
    done = hm.render(asset, props, fps=FPS, aspect=aspect, size=ASPECT_SIZE[aspect])
    placed = Placed(
        index=0, asset=asset, start_ms=0, duration_ms=asset.duration.default_ms, props=props, why=""
    )
    box = region_box(placed, aspect)
    assert box is not None, "an overlay with text declares a box"
    poster = min(done.frames - 1, (asset.poster_ms * FPS + 500) // 1000)  # the asset fully in (design §8.3)
    drawn = _drawn(done.layers["main"], poster, done.size)
    assert _outside(drawn, box) == [], f"drawn {drawn} leaves its region {box}"
    assert _outside(drawn, SAFE) == [], f"drawn {drawn} leaves the title-safe area"


ASPECT_SIZE = {"16:9": (640, 360), "9:16": (360, 640), "1:1": (480, 480), "4:5": (480, 600)}
