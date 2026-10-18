"""The library (design §5, §6): loading, get, aliases and search."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import hone_motif as hm
from hone_motif.library import default_library_path


def test_loads_every_asset(lib: hm.Library) -> None:
    folders = sorted(p.name for p in (lib.root / "assets").iterdir() if (p / "asset.json").is_file())
    assert sorted(lib.assets) == folders
    assert len(folders) >= 19


def test_default_library_is_this_checkout() -> None:
    assert default_library_path() == Path(__file__).parents[2] / "library"
    assert hm.Library().root == default_library_path()


def test_get_unknown_asset(lib: hm.Library) -> None:
    with pytest.raises(hm.UnknownAssetError, match="hone-motif list"):
        lib.get("no-such-asset")


def test_aliases_resolve_to_the_new_id(lib_copy: Path) -> None:
    (lib_copy / "aliases.json").write_text(
        json.dumps({"aliases": {"subscribe-cta": "like-subscribe-glass-pill"}})
    )
    assert hm.Library(lib_copy).get("subscribe-cta").id == "like-subscribe-glass-pill"


def test_an_alias_loop_is_unknown(lib_copy: Path) -> None:
    (lib_copy / "aliases.json").write_text(json.dumps({"aliases": {"a-x": "b-x", "b-x": "a-x"}}))
    with pytest.raises(hm.UnknownAssetError):
        hm.Library(lib_copy).get("a-x")


def test_a_broken_asset_json_fails_loading_with_every_problem(lib_copy: Path) -> None:
    (lib_copy / "assets" / "bell-medallion-ring" / "asset.json").write_text("{not json")
    raw = json.loads((lib_copy / "assets" / "chapter-card-star-band" / "asset.json").read_text())
    raw["poster_ms"] = 1.5
    (lib_copy / "assets" / "chapter-card-star-band" / "asset.json").write_text(json.dumps(raw))
    with pytest.raises(hm.InvalidAssetError) as caught:
        hm.Library(lib_copy)
    assert {p.asset for p in caught.value.problems} == {"bell-medallion-ring", "chapter-card-star-band"}
    assert "hone-motif check" in str(caught.value)


def test_a_folder_without_assets_is_not_a_library(tmp_path: Path) -> None:
    with pytest.raises(hm.InvalidAssetError, match="no assets"):
        hm.Library(tmp_path)


def ids(found: list[hm.Asset]) -> list[str]:
    return [a.id for a in found]


def test_search_without_filters_returns_all_in_id_order(lib: hm.Library) -> None:
    assert ids(lib.search()) == sorted(lib.assets)


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        (
            {"kind": "transition"},
            [
                "dissolve-and-dip-dust-black",
                "film-burn-twin-holes",
                "ink-and-paint-bloom-wipe",
                "light-leak-amber-sweep",
            ],
        ),
        ({"category": "calls-to-action"}, ["bell-medallion-ring", "like-subscribe-glass-pill"]),
        ({"subcategory": "karaoke"}, ["karaoke-fill-focus", "karaoke-fill-slide", "karaoke-fill-sweep"]),
        ({"kind": "transition", "mood": "violent"}, ["film-burn-twin-holes"]),
        ({"text": "subscribe"}, ["like-subscribe-glass-pill", "two-videos-subscribe-calm-frames"]),
        ({"text": "BELL ripples"}, ["bell-medallion-ring"]),
        (
            {"kind": "scene", "text": "calligraphy"},
            ["epigraph-verse-couplet", "title-reveal-ember-calligraphy"],
        ),
    ],
)
def test_search_filters(lib: hm.Library, filters: dict[str, str], expected: list[str]) -> None:
    assert ids(lib.search(**filters)) == expected


def test_mood_any_matches_every_mood(lib: hm.Library) -> None:
    found = ids(lib.search(mood="tragic"))
    assert "like-subscribe-glass-pill" in found  # moods ["any"]
    assert "film-burn-twin-holes" not in found  # violent, tense, epic


def test_search_by_theme_aspect_and_script(lib: hm.Library) -> None:
    assert ids(lib.search(theme="pop")) == sorted(lib.assets)  # every M1 asset supports all five themes
    assert lib.search(aspect="9:16") == []  # 16:9 only until M3 (decision D-012)
    assert ids(lib.search(script="Arab")) == ids([a for a in lib.search() if "Arab" in a.scripts])
    assert "film-burn-twin-holes" not in ids(lib.search(script="Latn"))  # no text at all


def test_a_repeated_id_is_a_problem(lib_copy: Path) -> None:
    shutil.copytree(lib_copy / "assets" / "like-subscribe-glass-pill", lib_copy / "assets" / "aaa-copy")
    with pytest.raises(hm.InvalidAssetError) as caught:
        hm.Library(lib_copy)
    [problem] = caught.value.problems
    assert problem.code == "duplicate-id"
    assert "aaa-copy/" in problem.message
    assert "like-subscribe-glass-pill/" in problem.message


def test_a_missing_vocabulary_is_a_problem(lib_copy: Path) -> None:
    (lib_copy / "vocabulary.json").unlink()
    with pytest.raises(hm.InvalidAssetError, match=r"vocabulary\.json is missing"):
        hm.Library(lib_copy)


def test_the_theme_filter_drops_assets_without_the_theme(lib_copy: Path) -> None:
    pill = lib_copy / "assets" / "like-subscribe-glass-pill" / "asset.json"
    data = json.loads(pill.read_text(encoding="utf-8"))
    data["themes"] = ["cinematic", "dark"]
    pill.write_text(json.dumps(data), encoding="utf-8")
    lib = hm.Library(lib_copy)
    assert "like-subscribe-glass-pill" not in ids(lib.search(theme="pop"))
    assert "like-subscribe-glass-pill" in ids(lib.search(theme="dark"))
    assert len(lib.search(theme="pop")) == len(lib.assets) - 1
