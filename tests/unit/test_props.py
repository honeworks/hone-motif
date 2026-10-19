"""Props checks (design §2.6, §7.3): schema, text limits, scripts, defaults."""

from __future__ import annotations

from pathlib import Path

import pytest

import hone_motif as hm
from hone_motif.props import fill_defaults, scripts_of, values_at

PILL = "like-subscribe-glass-pill"


@pytest.mark.parametrize(
    ("text", "scripts"),
    [
        ("Subscribe", {"Latn"}),
        ("اشترك الآن", {"Arab"}),
        ("Road طريق", {"Latn", "Arab"}),
        ("Привет", {"Cyrl"}),
        ("שלום", {"Hebr"}),
        ("١٢٣ 123 !?", set()),
        ("ئ", {"Arab"}),
        ("你好", {"Zzzz"}),
    ],
)
def test_scripts_of_letters(text: str, scripts: set[str]) -> None:
    assert scripts_of(text) == scripts


def test_values_at_paths() -> None:
    props = {"title": "A", "lines": [{"name": "x"}, {"name": "y"}], "verse": ["one", "two"]}
    assert list(values_at(props, "title")) == [("title", "A")]
    assert list(values_at(props, "lines[].name")) == [("lines[0].name", "x"), ("lines[1].name", "y")]
    assert list(values_at(props, "verse[1]")) == [("verse[1]", "two")]
    assert list(values_at(props, "verse[5]")) == []
    assert list(values_at(props, "missing")) == []
    assert list(values_at({"lines": "not a list"}, "lines[].name")) == []


def test_example_props_pass(lib: hm.Library) -> None:
    for asset in lib.assets.values():
        assert hm.check_props(asset, asset.props) == [], asset.id


def test_unknown_prop_is_named(lib: hm.Library) -> None:
    [problem] = hm.check_props(lib.get(PILL), {"channelName": "Hone", "colour": "red"})
    assert problem.code == "unknown-prop"
    assert "colour" in problem.message
    assert "channelName" in problem.message  # lists the props there are


def test_text_too_long_names_the_prop_and_the_limit(lib: hm.Library) -> None:
    [problem] = hm.check_props(lib.get(PILL), {"channelName": "x" * 30})
    assert (problem.code, problem.field) == ("text-too-long", "channelName")
    assert "limit is 24" in problem.message
    assert "by 6" in problem.message


def test_wrong_type_missing_prop_and_enum(lib: hm.Library) -> None:
    problems = hm.check_props(lib.get(PILL), {"likeLabel": 5, "corner": "middle"})
    assert {(p.code, p.field) for p in problems} == {
        ("wrong-type", "likeLabel"),
        ("not-allowed", "corner"),
        ("missing-prop", None),
    }


def test_theme_must_be_one_the_asset_supports(lib: hm.Library) -> None:
    [problem] = hm.check_props(lib.get(PILL), {"channelName": "Hone", "theme": "neon"})
    assert (problem.code, problem.field) == ("not-allowed", "theme")


def test_other_schema_failures_are_invalid_prop(lib: hm.Library) -> None:
    [problem] = hm.check_props(lib.get(PILL), {"channelName": "Hone", "accent": "gold"})
    assert (problem.code, problem.field) == ("invalid-prop", "accent")


def test_text_in_an_unlisted_script_is_rejected(lib: hm.Library) -> None:
    [problem] = hm.check_props(lib.get(PILL), {"channelName": "Привет"})
    assert (problem.code, problem.field) == ("script-not-allowed", "channelName")
    assert "Cyrl" in problem.message


def test_scripts_are_checked_inside_arrays(lib: hm.Library) -> None:
    props = {"lines": [{"role": "Music", "name": "Hone"}, {"role": "Words", "name": "שלום"}]}
    [problem] = hm.check_props(lib.get("side-panel-bilingual-roles"), props)
    assert (problem.code, problem.field) == ("script-not-allowed", "lines[1].name")


def test_fill_defaults_fills_only_missing_props(lib: hm.Library) -> None:
    full = fill_defaults(lib.get(PILL), {"channelName": "Hone", "likeLabel": "Thumbs"})
    assert full == {
        "theme": "cinematic",
        "likeLabel": "Thumbs",
        "subscribeLabel": "Subscribe",
        "subscribedLabel": "Subscribed",
        "channelName": "Hone",
        "corner": "bottom-left",
    }


def test_an_asset_without_a_schema_fails_every_check(lib_copy: Path) -> None:
    (lib_copy / "assets" / PILL / "props.schema.json").unlink()
    [problem] = hm.check_props(hm.Asset.load(lib_copy / "assets" / PILL), {"anything": 1})
    assert problem.code == "no-props-schema"


# --- brand tokens (change 0003) ---

BRAND = {"bg": "#101114", "ink": "#f4f1ea", "accent": "#e8a33d", "fonts": {"display": "Montserrat"}}


def test_a_brand_with_registry_fonts_passes(shipped: hm.Library) -> None:
    for asset in shipped.assets.values():
        assert hm.check_props(asset, {**asset.props, "brand": BRAND}) == [], asset.id


def test_a_brand_font_outside_the_registry_is_refused(shipped: hm.Library) -> None:
    asset = next(iter(shipped.assets.values()))
    [problem] = hm.check_props(asset, {**asset.props, "brand": {"fonts": {"body": "Comic Sans MS"}}})
    assert (problem.code, problem.field) == ("brand-font-unknown", "brand.fonts.body")
    assert "Montserrat" in problem.message  # it names the registry's families


def test_a_brand_with_a_bad_colour_or_key_is_refused(shipped: hm.Library) -> None:
    asset = next(iter(shipped.assets.values()))
    assert hm.check_props(asset, {**asset.props, "brand": {"ink": "white"}})
    assert hm.check_props(asset, {**asset.props, "brand": {"glow": "#ffffff"}})


def test_low_contrast_is_a_warning_not_a_problem(shipped: hm.Library) -> None:
    asset = next(iter(shipped.assets.values()))
    grey = {"bg": "#777777", "ink": "#888888"}
    assert hm.check_props(asset, {**asset.props, "brand": grey}) == []
    [warning] = hm.brand_warnings({"brand": grey}, asset.id)
    assert (warning.code, warning.field) == ("brand-low-contrast", "brand.ink")
    assert hm.brand_warnings({"brand": BRAND}) == []
    assert hm.brand_warnings({}) == []


def test_contrast_ratio() -> None:
    from hone_motif.props import contrast  # noqa: PLC0415

    assert round(contrast("#000000", "#ffffff"), 1) == 21.0
    assert contrast("#123456", "#123456") == 1.0


def test_the_brand_is_in_the_key_only_when_given(shipped: hm.Library) -> None:
    from hone_motif.render import key_inputs, plan  # noqa: PLC0415
    from hone_motif.testing import FakeRenderer  # noqa: PLC0415

    asset = next(iter(shipped.assets.values()))
    plain = key_inputs(plan(asset, dict(asset.props)), FakeRenderer())
    branded = key_inputs(plan(asset, {**asset.props, "brand": BRAND}), FakeRenderer())
    assert "brand" not in plain["props"]  # no default is filled in, so old props keep their key
    assert branded["props"]["brand"] == BRAND
    assert {k: v for k, v in branded.items() if k != "props"} == {
        k: v for k, v in plain.items() if k != "props"
    }
