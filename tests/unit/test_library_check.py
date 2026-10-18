"""The library check (design §11, §12): every rule finds a broken asset."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, get_args

import pytest

import hone_motif as hm
from hone_motif.asset import Kind, Slot
from hone_motif.library_check import schema_at

PILL = "like-subscribe-glass-pill"


def edit(
    root: Path, asset_id: str, change: Callable[[dict[str, Any]], None], file: str = "asset.json"
) -> None:
    path = root / "assets" / asset_id / file
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def codes(root: Path) -> set[tuple[str, str | None]]:
    return {(p.code, p.asset) for p in hm.Library(root).check()}


def test_the_library_is_clean(lib: hm.Library) -> None:
    assert lib.check() == []


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (lambda d: d.update(category="memes"), "unknown-word"),
        (lambda d: d.update(subcategory="rocket"), "unknown-word"),
        (lambda d: d.update(moods=["sleepy"]), "unknown-word"),
        (lambda d: d.update(moods=["any", "epic"]), "any-mood-alone"),
        (lambda d: d.update(themes=["cinematic", "neon"]), "unknown-word"),
        (lambda d: d["regions"]["16:9"].update(anchor="somewhere"), "unknown-word"),
        (lambda d: d.update(platforms=["myspace"]), "unknown-word"),
        (lambda d: d["text_fields"][0].update(scripts=["Hebr"]), "unknown-word"),
        (lambda d: d.update(themes=["cinematic", "dark"]), "themes-differ"),
        (lambda d: d["props"].update(channelName="x" * 40), "text-too-long"),
        (lambda d: d["samples"]["rtl"].update(likeLabel=7), "wrong-type"),
        (lambda d: d.pop("samples"), "no-rtl-sample"),
        (lambda d: d["text_fields"][0].update(max_chars=13), "limit-differs"),
        (lambda d: d.update(fonts=["Comic Sans MS"]), "font-not-registered"),
        (
            lambda d: d.update(
                media=[{"file": "dust.png", "licence": "CC0-1.0", "source": "https://example.org"}]
            ),
            "media-missing",
        ),
        (lambda d: d.update(inputs=[{"prop": "logo", "type": "image"}]), "unknown-input"),
    ],
)
def test_each_rule_finds_its_problem(
    lib_copy: Path, change: Callable[[dict[str, Any]], None], code: str
) -> None:
    edit(lib_copy, PILL, change)
    assert (code, PILL) in codes(lib_copy)


def test_ids_follow_the_subcategory_and_the_folder(lib_copy: Path) -> None:
    (lib_copy / "assets" / PILL).rename(lib_copy / "assets" / "pill")
    assert ("folder-not-id", PILL) in codes(lib_copy)
    edit(lib_copy, "pill", lambda d: d.update(id="glass-pill"))
    assert ("id-rule", "glass-pill") in codes(lib_copy)


def test_missing_props_schema(lib_copy: Path) -> None:
    (lib_copy / "assets" / PILL / "props.schema.json").unlink()
    assert ("no-props-schema", PILL) in codes(lib_copy)


def test_an_alias_must_not_shadow_an_id(lib_copy: Path) -> None:
    (lib_copy / "aliases.json").write_text(json.dumps({"aliases": {PILL: "bell-medallion-ring"}}))
    assert ("alias-is-an-id", PILL) in codes(lib_copy)


def test_fonts_need_their_licence_file(lib_copy: Path) -> None:
    (lib_copy / "fonts" / "inter" / "OFL.txt").unlink()
    assert ("font-not-registered", PILL) in codes(lib_copy)


def test_schema_at_paths(lib: hm.Library) -> None:
    credits = lib.get("side-panel-bilingual-roles").props_schema
    assert schema_at(credits, "lines[].name") == {
        "type": "string",
        "maxLength": 28,
        "description": "the name",
    }
    epigraph = lib.get("epigraph-verse-couplet").props_schema
    assert schema_at(epigraph, "verse[1]")["maxLength"] == 40  # pyright: ignore[reportOptionalSubscript]
    assert schema_at(epigraph, "verse[7]") is None
    assert schema_at(epigraph, "nothing.here") is None
    assert schema_at(epigraph, "bad path!") is None


def test_every_registered_font_is_ofl_with_its_files(lib: hm.Library) -> None:
    registry = json.loads((lib.root / "fonts" / "fonts.json").read_text(encoding="utf-8"))["fonts"]
    for family, entry in registry.items():
        assert entry["licence"] == "OFL-1.1", family
        assert (lib.root / "fonts" / entry["file"]).is_file(), family
        assert "SIL Open Font License" in (lib.root / "fonts" / entry["licence_file"]).read_text(
            encoding="utf-8"
        )


def test_asset_schema_json_is_up_to_date(lib: hm.Library) -> None:
    exported = json.loads((lib.root / "asset.schema.json").read_text(encoding="utf-8"))
    assert exported == hm.Asset.model_json_schema(by_alias=True), (
        "run `uv run scripts/export-asset-schema.py`"
    )


def test_vocabulary_matches_the_model_and_the_themes(lib: hm.Library) -> None:
    assert lib.vocabulary["kinds"] == list(get_args(Kind))
    assert lib.vocabulary["slots"] == list(get_args(Slot))
    assert (
        list(json.loads((lib.root / "themes.json").read_text(encoding="utf-8"))) == lib.vocabulary["themes"]
    )
