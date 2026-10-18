"""Props: checks against an asset's schema and text fields, and default filling (design §2.6, §7.3)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator, Mapping
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .asset import Asset
from .errors import Problem

# The first word of a letter's Unicode name, and its ISO 15924 script.
_SCRIPT_NAMES = {
    "LATIN": "Latn",
    "ARABIC": "Arab",
    "HEBREW": "Hebr",
    "CYRILLIC": "Cyrl",
    "GREEK": "Grek",
    "DEVANAGARI": "Deva",
}
PATH_PART = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\[(?P<index>\d*)\])?$")


def scripts_of(text: str) -> set[str]:
    """The ISO 15924 scripts of the letters in `text` (`Zzzz` for unknown); digits and marks have none."""
    found: set[str] = set()
    for ch in text:
        if ch.isalpha():
            found.add(_SCRIPT_NAMES.get(unicodedata.name(ch, "?").split(" ")[0], "Zzzz"))
    return found


def values_at(props: Mapping[str, Any], path: str) -> Iterator[tuple[str, Any]]:
    """Every value at a text-field path ("title", "lines[].name", "verse[0]"), with its concrete path."""
    yield from _walk(props, path.split("."), "")


def _walk(node: Any, parts: list[str], prefix: str) -> Iterator[tuple[str, Any]]:
    if not parts:
        yield prefix, node
        return
    match = PATH_PART.match(parts[0])
    if match is None or not isinstance(node, Mapping):
        return
    mapping = cast(Mapping[str, Any], node)
    if match["name"] not in mapping:
        return
    child = mapping[match["name"]]
    here = f"{prefix}.{match['name']}" if prefix else match["name"]
    index = match["index"]
    if index is None:
        yield from _walk(child, parts[1:], here)
    elif isinstance(child, list):
        items = cast(list[Any], child)
        positions = range(len(items)) if index == "" else [int(index)] if int(index) < len(items) else []
        for i in positions:
            yield from _walk(items[i], parts[1:], f"{here}[{i}]")


def _schema_problem(error: ValidationError, asset: Asset) -> Problem:
    field = ".".join(str(p) for p in error.absolute_path) or None
    match error.validator:
        case "additionalProperties":
            known = ", ".join(sorted(error.schema.get("properties", {})))  # pyright: ignore[reportUnknownArgumentType,reportUnknownMemberType,reportAttributeAccessIssue]
            return Problem(
                code="unknown-prop",
                asset=asset.id,
                field=field,
                message=f"{error.message}; the props are: {known}",
            )
        case "maxLength":
            limit = int(cast(int, error.validator_value))
            text = str(error.instance)
            return Problem(
                code="text-too-long",
                asset=asset.id,
                field=field,
                message=f"{len(text)} characters, the limit is {limit}: shorten it by {len(text) - limit}",
            )
        case "type":
            return Problem(code="wrong-type", asset=asset.id, field=field, message=error.message)
        case "enum":
            return Problem(code="not-allowed", asset=asset.id, field=field, message=error.message)
        case "required":
            return Problem(code="missing-prop", asset=asset.id, field=field, message=error.message)
        case _:
            return Problem(code="invalid-prop", asset=asset.id, field=field, message=error.message)


def check_props(asset: Asset, props: Mapping[str, Any]) -> list[Problem]:
    """Check props against the asset's schema (unknown props, types, enums, `maxLength`) and text scripts."""
    if not asset.props_schema:
        return [
            Problem(
                code="no-props-schema",
                asset=asset.id,
                message="props.schema.json is missing, so nothing can be checked: run `npm run export`",
            )
        ]
    validator = Draft202012Validator(asset.props_schema)
    problems = [
        _schema_problem(e, asset)
        for e in sorted(validator.iter_errors(dict(props)), key=lambda e: list(e.absolute_path))  # pyright: ignore[reportUnknownMemberType]
    ]
    for text_field in asset.text_fields:
        for where, value in values_at(props, text_field.prop):
            if not isinstance(value, str):
                continue
            unlisted = scripts_of(value) - set(text_field.scripts)
            if unlisted:
                problems.append(
                    Problem(
                        code="script-not-allowed",
                        asset=asset.id,
                        field=where,
                        message=f"text in {', '.join(sorted(unlisted))}; "
                        f"this field sets only {', '.join(text_field.scripts)}",
                    )
                )
    return problems


def fill_defaults(asset: Asset, props: Mapping[str, Any]) -> dict[str, Any]:
    """The props with every missing top-level prop that has a default in the schema filled in."""
    full = dict(props)
    properties: dict[str, Any] = asset.props_schema.get("properties", {})
    for name, spec in properties.items():
        if name not in full and isinstance(spec, dict) and "default" in spec:
            full[name] = spec["default"]
    return full
