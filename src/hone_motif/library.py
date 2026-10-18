"""The library: every asset of a library folder, searchable without Node (design §5, §6)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .asset import Asset
from .errors import InvalidAssetError, Problem, UnknownAssetError
from .library_check import check_library
from .prompt import catalog_entry
from .video import VideoInfo


def default_library_path() -> Path:
    """The checkout's `library/` in development, else the one shipped in the wheel (`hone_motif/library`)."""
    checkout = Path(__file__).parents[2] / "library"
    return checkout if (checkout / "vocabulary.json").is_file() else Path(__file__).parent / "library"


def load_assets(root: Path) -> tuple[list[Asset], list[Problem]]:
    """Every asset under `root/assets`; a problem for each asset.json that does not load or repeats an id."""
    assets: dict[str, Asset] = {}
    problems: list[Problem] = []
    for folder in sorted(p for p in (root / "assets").iterdir() if (p / "asset.json").is_file()):
        try:
            asset = Asset.load(folder)
        except (ValidationError, ValueError) as e:  # JSONDecodeError is a ValueError
            problems.append(Problem(code="invalid-asset-json", asset=folder.name, message=str(e)))
            continue
        if asset.id in assets:
            first = assets[asset.id].folder.name
            problems.append(
                Problem(
                    code="duplicate-id", asset=asset.id, message=f"both {first}/ and {folder.name}/ use it"
                )
            )
        assets.setdefault(asset.id, asset)
    return list(assets.values()), problems


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise InvalidAssetError([Problem(code="missing-file", message=f"{path} is missing")])
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


class Library:
    """The assets of one library folder: `Library()` is the installed library, `Library(path)` another."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.root = Path(path) if path is not None else default_library_path()
        if not (self.root / "assets").is_dir():
            raise InvalidAssetError(
                [Problem(code="no-library", message=f"{self.root} has no assets/ folder")]
            )
        assets, problems = load_assets(self.root)
        if problems:
            raise InvalidAssetError(problems)
        self.assets: dict[str, Asset] = {a.id: a for a in assets}
        self.vocabulary: dict[str, Any] = _read_json(self.root / "vocabulary.json")
        self.aliases: dict[str, str] = _read_json(self.root / "aliases.json")["aliases"]

    def resolve(self, asset_id: str) -> str:
        """The current id for `asset_id`, following aliases of renamed assets; raises UnknownAssetError."""
        seen: set[str] = set()
        while asset_id not in self.assets and asset_id in self.aliases and asset_id not in seen:
            seen.add(asset_id)
            asset_id = self.aliases[asset_id]
        if asset_id not in self.assets:
            raise UnknownAssetError(f"no asset {asset_id!r} in {self.root}; `hone-motif list` shows the ids")
        return asset_id

    def get(self, asset_id: str) -> Asset:
        """The asset with this id (or alias); raises UnknownAssetError."""
        return self.assets[self.resolve(asset_id)]

    def search(
        self,
        *,
        category: str | None = None,
        subcategory: str | None = None,
        kind: str | None = None,
        theme: str | None = None,
        mood: str | None = None,
        aspect: str | None = None,
        script: str | None = None,
        text: str | None = None,
    ) -> list[Asset]:
        """Assets matching every filter, in id order; each `text` word must be in id, name, line or tags."""
        words = text.lower().split() if text else []
        return [
            a
            for a in sorted(self.assets.values(), key=lambda a: a.id)
            if (category is None or a.category == category)
            and (subcategory is None or a.subcategory == subcategory)
            and (kind is None or a.kind == kind)
            and (theme is None or theme in a.themes)
            and (mood is None or mood in a.moods or "any" in a.moods)
            and (aspect is None or aspect in a.aspects)
            and (script is None or script in a.scripts)
            and all(w in _haystack(a) for w in words)
        ]

    def catalog(self, assets: list[Asset], video: VideoInfo) -> list[dict[str, Any]]:
        """The compact catalogue of `assets` for the video's placement prompt (design §7.2)."""
        return [catalog_entry(a, video.aspect) for a in assets]

    def check(self) -> list[Problem]:
        """Every problem beyond loading: vocabulary, ids, defaults, text limits, fonts (design §12)."""
        return check_library(self)


def _haystack(asset: Asset) -> str:
    return " ".join([asset.id, asset.name, asset.line, *asset.tags]).lower()
