"""Typed errors (design §6, §13) and `Problem`, one finding of a check."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Problem(BaseModel):
    """One finding of a check: a stable `code`, where it is, and a message that says what to do."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    message: str
    index: int | None = None  # the placement's position in the reply, for placement checks
    asset: str | None = None
    field: str | None = None

    def __str__(self) -> str:
        where = " ".join(
            part
            for part in (
                f"#{self.index}" if self.index is not None else "",
                self.asset or "",
                f"[{self.field}]" if self.field else "",
            )
            if part
        )
        return f"{self.code}: {where}: {self.message}" if where else f"{self.code}: {self.message}"


class HoneMotifError(Exception):
    """Base of every error hone-motif raises."""


class UnknownAssetError(HoneMotifError, KeyError):
    """No asset with this id (or alias) is in the library."""

    def __str__(self) -> str:  # KeyError would quote the message
        return str(self.args[0]) if self.args else ""


class InvalidAssetError(HoneMotifError, ValueError):
    """An asset.json (or the library around it) does not load; `problems` lists every finding."""

    def __init__(self, problems: list[Problem]) -> None:
        self.problems = problems
        lines = "\n".join(f"  {p}" for p in problems)
        super().__init__(f"the library has {len(problems)} problem(s); run `hone-motif check`:\n{lines}")


class InvalidPropsError(HoneMotifError, ValueError):
    """Props that fail the asset's checks were given to `render`; `problems` lists them."""

    def __init__(self, asset: str, problems: list[Problem]) -> None:
        self.problems = problems
        lines = "\n".join(f"  {p}" for p in problems)
        super().__init__(f"props for {asset} fail {len(problems)} check(s):\n{lines}")


class InvalidRenderError(HoneMotifError, ValueError):
    """A render was asked for with an aspect ratio, size, frame rate or duration the asset does not take."""


class RendererUnavailableError(HoneMotifError):
    """The renderer cannot run here (no Node, or no library packages); the message says how to install."""


class RenderError(HoneMotifError):
    """The renderer ran and failed; `log` holds its output."""

    def __init__(self, message: str, log: str = "") -> None:
        self.log = log
        tail = "\n".join(log.strip().splitlines()[-30:])
        super().__init__(f"{message}\n--- renderer log (last lines) ---\n{tail}" if tail else message)
