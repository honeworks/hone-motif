"""Render tests need Node and the library's packages; without them they skip with the reason (D-008)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

LIBRARY = Path(__file__).parents[2] / "library"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    missing = [tool for tool in ("node", "ffmpeg") if shutil.which(tool) is None]
    if not (LIBRARY / "node_modules" / "remotion" / "package.json").is_file():
        missing.append("the library's packages (run `npm ci` in library/)")
    if missing:
        skip = pytest.mark.skip(reason=f"render tests need {', '.join(missing)}")
        for item in items:
            if "tests/render" in str(item.path):
                item.add_marker(skip)
