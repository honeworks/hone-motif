"""The video's facts (design §7.1): spans and sections are ordered, times are integers."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.helpers import video


@pytest.mark.parametrize(
    "changes",
    [
        {"busy": [{"start_ms": 5000, "end_ms": 5000}]},
        {"busy": [{"start_ms": 5000, "end_ms": 4000}]},
        {"sections": [{"id": "x", "start_ms": 9000, "end_ms": 1000}]},
    ],
)
def test_spans_and_sections_end_after_they_start(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="after start_ms"):
        video(**changes)


@pytest.mark.parametrize(
    "changes", [{"fps": 30.0}, {"aspect": "21:9"}, {"platform": "tiktok"}, {"cuts": [-1]}]
)
def test_bad_facts_are_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        video(**changes)
