"""The gallery (design §10): one tile per asset and theme, posters from the cache, data embedded safely."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

import hone_motif as hm
from hone_motif.gallery import sample_brand
from hone_motif.render import LAYOUT, _size  # pyright: ignore[reportPrivateUsage]
from hone_motif.testing import FakeRenderer


@pytest.fixture
def lib(lib: hm.Library) -> hm.Library:
    """The M1 assets (no loop or background among them), so the test's time does not grow with the library."""
    return lib


def data_of(index: Path) -> dict[str, Any]:
    page = index.read_text(encoding="utf-8")
    match = re.search(r"const DATA = (.*?);\n", page, re.S)
    assert match is not None, "the page embeds its data as `const DATA = ...;`"
    return json.loads(match[1].replace("<\\/", "</"))


def test_a_gallery_without_renders_lists_every_tile(lib: hm.Library, cache: hm.Cache) -> None:
    index = hm.build_gallery(lib, cache=cache, renderer=FakeRenderer())
    assert index == cache.root / "gallery" / "index.html"
    data = data_of(index)
    assert len(data["tiles"]) == sum(len(a.aspects) * (len(a.themes) + 1) for a in lib.assets.values())
    assert all(t["poster"] is None for t in data["tiles"])
    assert set(data["assets"]) == set(lib.assets)
    assert (
        "</script>" not in index.read_text(encoding="utf-8").split("const DATA = ", 1)[1].split(";\n", 1)[0]
    )


def test_render_missing_renders_once_and_links_relative_paths(
    lib: hm.Library, cache: hm.Cache, tmp_path: Path
) -> None:
    fake = FakeRenderer()
    out = tmp_path / "site"
    data = data_of(hm.build_gallery(lib, cache=cache, out=out, render_missing=True, renderer=fake))
    assert fake.calls == len(data["tiles"])
    leak = next(t for t in data["tiles"] if t["asset"] == "light-leak-amber-sweep" and t["theme"] == "warm")
    assert (out / leak["poster"]).is_file()
    assert leak["preview"].endswith("fx.mp4")
    assert leak["matte"].endswith("matte.mp4")
    assert not Path(leak["poster"]).is_absolute()
    hm.build_gallery(lib, cache=cache, out=out, render_missing=True, renderer=fake)
    assert fake.calls == len(data["tiles"])  # everything came from the cache


def test_detail_fields(lib: hm.Library, cache: hm.Cache) -> None:
    data = data_of(hm.build_gallery(lib, cache=cache, renderer=FakeRenderer()))
    pill = data["assets"]["like-subscribe-glass-pill"]
    for field in (
        "line",
        "when",
        "text_fields",
        "props_schema",
        "props",
        "licence",
        "fonts",
        "category",
        "tags",
    ):
        assert field in pill
    assert pill["props_schema"]["properties"]["channelName"]["maxLength"] == 24


def test_text_cannot_close_the_page_script(lib_copy: Path, tmp_path: Path) -> None:
    pill = lib_copy / "assets" / "like-subscribe-glass-pill" / "asset.json"
    data = json.loads(pill.read_text(encoding="utf-8"))
    data["line"] = "A pill </script><b>bold</b>"
    pill.write_text(json.dumps(data), encoding="utf-8")
    index = hm.build_gallery(hm.Library(lib_copy), cache=hm.Cache(tmp_path / "c"), renderer=FakeRenderer())
    embedded = index.read_text(encoding="utf-8").split("const DATA = ", 1)[1].split(";\n", 1)[0]
    assert "</script>" not in embedded
    assert data_of(index)["assets"]["like-subscribe-glass-pill"]["line"] == data["line"]


def test_preview_sizes_keep_the_scale() -> None:
    from hone_motif.gallery import preview_size  # noqa: PLC0415

    assert preview_size("16:9", (960, 540)) == (960, 540)
    assert preview_size("9:16", (960, 540)) == (540, 960)
    assert preview_size("1:1", (960, 540)) == (540, 540)
    for aspect in LAYOUT:  # every size must pass the renderer's own check
        for size in ((960, 540), (480, 270)):
            _size(aspect, preview_size(aspect, size))


def test_an_asset_gets_a_tile_per_aspect(lib_copy: Path, tmp_path: Path) -> None:
    for other in (lib_copy / "assets").iterdir():
        if other.name != "epigraph-verse-couplet":
            shutil.rmtree(other)
    folder = lib_copy / "assets" / "epigraph-verse-couplet"
    data = json.loads((folder / "asset.json").read_text(encoding="utf-8"))
    data["aspects"] = ["16:9", "9:16"]
    data["regions"] = {"16:9": "full", "9:16": "full"}
    (folder / "asset.json").write_text(json.dumps(data), encoding="utf-8")
    fake = FakeRenderer()
    index = hm.build_gallery(
        hm.Library(lib_copy), cache=hm.Cache(tmp_path / "c"), render_missing=True, renderer=fake
    )
    tiles = [t for t in data_of(index)["tiles"] if t["asset"] == "epigraph-verse-couplet"]
    assert sorted({t["aspect"] for t in tiles}) == ["16:9", "9:16"]
    assert len(tiles) == 12  # 5 themes and the brand, in 2 aspects
    portrait = next(t for t in tiles if t["aspect"] == "9:16")
    record = json.loads((index.parent / portrait["render_json"]).read_text(encoding="utf-8"))
    assert (record["width"], record["height"]) == (540, 960)


def test_each_asset_has_a_brand_tile_in_its_first_theme(lib: hm.Library, cache: hm.Cache) -> None:
    """Change 0003: the sample brand over the first theme, one tile per aspect."""
    data = data_of(hm.build_gallery(lib, cache=cache, renderer=FakeRenderer()))
    brand = [t for t in data["tiles"] if t["theme"] == "brand"]
    assert len(brand) == sum(len(a.aspects) for a in lib.assets.values())
    assert sample_brand(lib.root)["accent"] == "#ff7a1a"  # the same values as shared/brand.ts
