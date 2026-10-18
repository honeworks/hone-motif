"""The video's facts a consumer gives to the placement checks (design §7.1)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .asset import Frozen, Ms

Aspect = Literal["16:9", "9:16", "1:1", "4:5"]


class Span(Frozen):
    """A stretch of the video in milliseconds, end exclusive."""

    start_ms: Ms
    end_ms: Ms

    @model_validator(mode="after")
    def _ordered(self) -> Span:
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be after start_ms")
        return self


class Section(Frozen):
    """A section of the video: a verse, a chorus, a chapter."""

    id: str
    kind: str = ""
    start_ms: Ms
    end_ms: Ms

    @model_validator(mode="after")
    def _ordered(self) -> Section:
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be after start_ms")
        return self


class VideoInfo(Frozen):
    """What the checks need to know about the video: its length, frame, cuts, sections and busy spans."""

    duration_ms: Annotated[int, Field(strict=True, gt=0)]
    aspect: Aspect
    fps: Annotated[int, Field(strict=True, ge=1, le=240)]
    cuts: list[Ms] = []  # every cut between two shots
    sections: list[Section] = []
    busy: list[Span] = []  # where quiet_only assets may not go: sung lines, speech
    scripts: list[str] = []  # the scripts of the video's text, for search
    platform: Literal["youtube"] | None = None  # platform rules apply only when set
