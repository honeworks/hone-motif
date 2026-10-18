"""Shared fixtures: the fixture and shipped libraries, a cache in a temporary folder, a fake renderer."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import hone_motif as hm
from hone_motif.testing import FakeRenderer

LIBRARY = Path(__file__).parents[1] / "library"


# Metadata-only assets (asset.json and props.schema.json, no compositions) that cover every placement rule;
# they are never shipped. The shipped library holds only the starter assets (design/changes/0002).
FIXTURES = Path(__file__).parent / "fixtures" / "assets"


def fixture_library(root: Path) -> Path:
    """The shipped library without its assets, plus the fixture assets, at `root`."""
    shutil.copytree(LIBRARY, root, ignore=shutil.ignore_patterns("node_modules", "build", "assets"))
    shutil.copytree(FIXTURES, root / "assets")
    return root


@pytest.fixture(scope="session")
def fixture_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixture library's folder, built once per session; tests must not change it (use lib_copy)."""
    return fixture_library(tmp_path_factory.mktemp("fixtures") / "library")


@pytest.fixture(scope="session")
def lib(fixture_root: Path) -> hm.Library:
    """The fixture library: every placement rule, metadata only."""
    return hm.Library(fixture_root)


@pytest.fixture(scope="session")
def shipped() -> hm.Library:
    """The library shipped in the package: the starter assets."""
    return hm.Library(LIBRARY)


@pytest.fixture
def cache(tmp_path: Path) -> hm.Cache:
    return hm.Cache(tmp_path / "cache")


@pytest.fixture
def fake() -> FakeRenderer:
    return FakeRenderer()


@pytest.fixture
def lib_copy(tmp_path: Path) -> Path:
    """A copy of the fixture library (no Node files) that a test may change; small, so fast."""
    return fixture_library(tmp_path / "library")


@pytest.fixture
def shipped_copy(tmp_path: Path) -> Path:
    """A copy of the shipped library (sources, no Node files) that a test may change."""
    root = tmp_path / "shipped"
    shutil.copytree(LIBRARY, root, ignore=shutil.ignore_patterns("node_modules", "build"))
    return root
