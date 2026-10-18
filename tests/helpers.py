"""Helpers shared by the tests."""

from __future__ import annotations

from typing import Any

import hone_motif as hm


def video(**changes: Any) -> hm.VideoInfo:
    """A 3:34 song in 16:9 at 32 fps, with cuts, two sections and one sung line, for YouTube."""
    facts: dict[str, Any] = {
        "duration_ms": 214380,
        "aspect": "16:9",
        "fps": 32,
        "cuts": [6210, 12040, 41010, 60000, 90000],
        "sections": [
            {"id": "verse-1", "kind": "verse", "start_ms": 12000, "end_ms": 60000},
            {"id": "chorus-1", "kind": "chorus", "start_ms": 60000, "end_ms": 120000},
        ],
        "busy": [{"start_ms": 14000, "end_ms": 30000}],
        "scripts": ["Arab", "Latn"],
        "platform": "youtube",
    }
    facts.update(changes)
    return hm.VideoInfo.model_validate(facts)
