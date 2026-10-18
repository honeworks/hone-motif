"""The library check (design §11, §12): what `hone-motif check` finds beyond an asset.json that loads."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .asset import Asset, BoxRegion
from .errors import Problem
from .props import PATH_PART, check_props

RTL_SCRIPTS = frozenset({"Arab", "Hebr"})  # the right-to-left scripts of the vocabulary

if TYPE_CHECKING:
    from .library import Library


def check_library(lib: Library) -> list[Problem]:
    """Every problem of every asset: vocabulary, ids, schema, defaults, samples, text limits, fonts, media."""
    fonts = json.loads((lib.root / "fonts" / "fonts.json").read_text(encoding="utf-8"))["fonts"]
    problems: list[Problem] = []
    for asset in lib.assets.values():
        problems += _vocabulary(asset, lib.vocabulary)
        problems += _identity(asset)
        problems += _schema(asset)
        problems += _fonts_and_media(asset, fonts, lib)
    problems += [
        Problem(code="alias-is-an-id", asset=old, message="an alias must not be the id of an existing asset")
        for old in lib.aliases
        if old in lib.assets
    ]
    return problems


def _unknown(asset: Asset, field: str, values: list[str], allowed: list[str]) -> list[Problem]:
    bad = [v for v in values if v not in allowed]
    if not bad:
        return []
    return [
        Problem(
            code="unknown-word",
            asset=asset.id,
            field=field,
            message=f"{', '.join(bad)} not in library/vocabulary.json; known: {', '.join(allowed)}",
        )
    ]


def _vocabulary(asset: Asset, vocab: dict[str, Any]) -> list[Problem]:
    category = vocab["categories"].get(asset.category)
    if category is None:
        return _unknown(asset, "category", [asset.category], list(vocab["categories"]))
    anchors = [r.anchor for r in asset.regions.values() if isinstance(r, BoxRegion)]
    problems = (
        _unknown(asset, "subcategory", [asset.subcategory], category["subcategories"])
        + _unknown(asset, "kind", [asset.kind], category["kinds"])
        + _unknown(asset, "themes", asset.themes, vocab["themes"])
        + _unknown(asset, "moods", asset.moods, vocab["moods"])
        + _unknown(asset, "aspects", asset.aspects, vocab["aspects"])
        + _unknown(asset, "regions", anchors, vocab["anchors"])
        + _unknown(asset, "scripts", asset.scripts, vocab["scripts"])
        + _unknown(asset, "platforms", asset.platforms, vocab["platforms"])
    )
    for text_field in asset.text_fields:
        problems += _unknown(
            asset, f"text_fields[{text_field.prop}].scripts", text_field.scripts, asset.scripts
        )
    if "any" in asset.moods and len(asset.moods) > 1:
        problems.append(
            Problem(code="any-mood-alone", asset=asset.id, field="moods", message='"any" stands alone')
        )
    return problems


def _identity(asset: Asset) -> list[Problem]:
    problems: list[Problem] = []
    if asset.folder.name != asset.id:
        problems.append(
            Problem(
                code="folder-not-id",
                asset=asset.id,
                message=f"the folder is {asset.folder.name}; name it {asset.id}",
            )
        )
    if not asset.id.startswith(f"{asset.subcategory}-"):
        problems.append(
            Problem(
                code="id-rule",
                asset=asset.id,
                field="id",
                message=f"ids are <subcategory>-<words> (design §2.1): start it with {asset.subcategory}-",
            )
        )
    return problems


def schema_at(schema: dict[str, Any], path: str) -> dict[str, Any] | None:
    """The sub-schema at a text-field path ("title", "lines[].name", "verse[0]"), or None."""
    node: dict[str, Any] | None = schema
    for part in path.split("."):
        match = PATH_PART.match(part)
        if match is None or node is None:
            return None
        node = node.get("properties", {}).get(match["name"])
        if node is not None and match["index"] == "":
            node = node.get("items")
        elif node is not None and match["index"] is not None:
            prefix: list[dict[str, Any]] = node.get("prefixItems", [])
            index = int(match["index"])
            node = prefix[index] if index < len(prefix) else None
    return node


def _schema(asset: Asset) -> list[Problem]:
    if not asset.props_schema:
        return [
            Problem(
                code="no-props-schema",
                asset=asset.id,
                message="props.schema.json is missing: run `npm run export` in library/",
            )
        ]
    return _theme_enum(asset) + _examples(asset) + _text_limits(asset) + _unknown_inputs(asset)


def _theme_enum(asset: Asset) -> list[Problem]:
    theme_enum = asset.props_schema.get("properties", {}).get("theme", {}).get("enum")
    if theme_enum == asset.themes:
        return []
    message = f"the schema's theme enum is {theme_enum}; asset.json lists {asset.themes}"
    return [Problem(code="themes-differ", asset=asset.id, field="themes", message=message)]


def _examples(asset: Asset) -> list[Problem]:
    """The default props and every sample pass the checks; an asset that sets right-to-left text has an
    `rtl` sample."""
    problems: list[Problem] = []
    for name, props in [("props", asset.props), *((f"samples.{k}", v) for k, v in asset.samples.items())]:
        problems += [
            p.model_copy(update={"message": f"{name}: {p.message}"}) for p in check_props(asset, props)
        ]
    if RTL_SCRIPTS.intersection(asset.scripts) and asset.text_fields and "rtl" not in asset.samples:
        problems.append(
            Problem(
                code="no-rtl-sample",
                asset=asset.id,
                field="samples",
                message="an asset that sets right-to-left text needs samples.rtl (design §14 case 14)",
            )
        )
    return problems


def _text_limits(asset: Asset) -> list[Problem]:
    problems: list[Problem] = []
    for text_field in asset.text_fields:
        sub = schema_at(asset.props_schema, text_field.prop)
        limit = sub.get("maxLength") if sub else None
        if limit != text_field.max_chars:
            problems.append(
                Problem(
                    code="limit-differs",
                    asset=asset.id,
                    field=text_field.prop,
                    message=f"max_chars is {text_field.max_chars}, the schema's maxLength is {limit}",
                )
            )
    return problems


def _unknown_inputs(asset: Asset) -> list[Problem]:
    known = asset.props_schema.get("properties", {})
    return [
        Problem(code="unknown-input", asset=asset.id, field=i.prop, message="not a prop of the schema")
        for i in asset.inputs
        if i.prop not in known
    ]


def _fonts_and_media(asset: Asset, fonts: dict[str, Any], lib: Library) -> list[Problem]:
    problems: list[Problem] = []
    for family in asset.fonts:
        entry = fonts.get(family)
        if (
            entry is None
            or entry.get("licence") != "OFL-1.1"
            or not (lib.root / "fonts" / entry["licence_file"]).is_file()
        ):
            problems.append(
                Problem(
                    code="font-not-registered",
                    asset=asset.id,
                    field="fonts",
                    message=f"{family} must be in fonts/fonts.json under OFL-1.1 with its licence file",
                )
            )
    for media in asset.media:
        if not (asset.folder / media.file).is_file():
            problems.append(
                Problem(
                    code="media-missing",
                    asset=asset.id,
                    field="media",
                    message=f"{media.file} is not in the asset's folder",
                )
            )
    return problems
