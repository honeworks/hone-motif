"""The ffmpeg filter graph that lays rendered assets over footage (design §8.5, decision D-011).

hone-motif only builds the graph; the consumer runs ffmpeg:

    ffmpeg -i footage.mp4 *graph.inputs -filter_complex graph.filter -map graph.output ... out.mp4
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .placement import Placement
from .render import Rendered, frames_for

# bottom to top after the footage (design §8.5); transitions sit on the footage itself
ORDER = ("transition", "background", "scene", "loop", "overlay", "caption")


@dataclass(frozen=True)
class ComposeLayer:
    """One placement and its render; a transition also needs the outgoing and incoming shots over its span."""

    placement: Placement
    rendered: Rendered
    kind: str
    outgoing: Path | None = None
    incoming: Path | None = None


@dataclass(frozen=True)
class FilterGraph:
    """ffmpeg arguments for the inputs after the footage (input 0), the filter graph, and its output label."""

    inputs: list[str] = field(default_factory=list[str])
    filter: str = ""
    output: str = "[v]"


@dataclass
class _Builder:
    fps: int
    size: tuple[int, int]
    inputs: list[str] = field(default_factory=list[str])
    chains: list[str] = field(default_factory=list[str])
    last: str = "[base]"
    count: int = 0  # labels made so far
    files: int = 0  # inputs after the footage

    def add_input(self, path: Path, *, repeat: bool = False) -> int:
        if repeat:  # a loop's one cycle, played again and again (D-023)
            self.inputs += ["-stream_loop", "-1"]
        if path.suffix == ".webm":  # VP9 alpha decodes only with libvpx
            self.inputs += ["-c:v", "libvpx-vp9"]
        self.inputs += ["-i", str(path)]
        self.files += 1
        return self.files

    def stream(self, path: Path, start_frame: int, fmt: str, *, loop_frames: int | None = None) -> str:
        """An input as a label: at the frame rate and size, shifted to start at `start_frame`; a loop is
        repeated and cut to `loop_frames`."""
        index = self.add_input(path, repeat=loop_frames is not None)
        self.count += 1
        label = f"[s{self.count}]"
        w, h = self.size
        shift = f"setpts=PTS-STARTPTS+{start_frame}/({self.fps}*TB)"
        cut = f"trim=end_frame={loop_frames}," if loop_frames is not None else ""
        self.chains.append(
            f"[{index}:v]fps={self.fps},{cut}scale={w}:{h},setsar=1,format={fmt},{shift}{label}"
        )
        return label

    def over(self, top: str) -> None:
        self.count += 1
        out = f"[b{self.count}]"
        self.chains.append(f"{self.last}{top}overlay=eof_action=pass:format=auto{out}")
        self.last = out

    def screen(self, top: str, start_frame: int) -> None:
        """A screen blend; the layer is padded with black before its start so both streams line up."""
        self.count += 1
        padded, base, out = f"[p{self.count}]", f"[g{self.count}]", f"[b{self.count}]"
        self.chains.append(f"{top}tpad=start={start_frame}:stop=-1:color=black,format=gbrp{padded}")
        self.chains.append(f"{self.last}format=gbrp{base}")
        self.chains.append(f"{base}{padded}blend=all_mode=screen:shortest=1,format=yuva420p{out}")
        self.last = out


def _transition(b: _Builder, layer: ComposeLayer, start: int) -> None:
    if layer.outgoing is None or layer.incoming is None:
        raise ValueError(
            f"the transition {layer.placement.asset} at {layer.placement.start_ms} ms needs its outgoing "
            "and incoming shots"
        )
    b.over(b.stream(layer.outgoing, start, "yuva420p"))
    incoming = b.stream(layer.incoming, start, "yuva420p")
    matte = b.stream(layer.rendered.layers["matte"], start, "gray")
    b.count += 1
    masked = f"[m{b.count}]"
    b.chains.append(f"{incoming}{matte}alphamerge{masked}")
    b.over(masked)
    if (
        layer.rendered.blend == "screen"
    ):  # tpad delays the fx; shifting its timestamps too would delay it twice
        b.screen(b.stream(layer.rendered.layers["fx"], 0, "yuva420p"), start)
    else:
        b.over(b.stream(layer.rendered.layers["fx"], start, "yuva420p"))


def compose_filter(layers: Sequence[ComposeLayer], *, fps: int, size: tuple[int, int]) -> FilterGraph:
    """The filter graph laying `layers` over the footage (input 0), bottom to top as design §8.5 says.

    Start frames come from absolute milliseconds, `(start_ms * fps + 500) // 1000` (design §8.3), never
    from summed durations.
    """
    w, h = size
    b = _Builder(fps=fps, size=size)
    b.chains.append(f"[0:v]fps={fps},scale={w}:{h},setsar=1,format=yuva420p[base]")
    ordered = sorted(layers, key=lambda layer: (ORDER.index(layer.kind), layer.placement.start_ms))
    for layer in ordered:
        start = frames_for(layer.placement.start_ms, fps)
        if layer.kind == "transition":
            _transition(b, layer, start)
        else:
            frames = frames_for(layer.placement.duration_ms, fps) if layer.kind == "loop" else None
            b.over(b.stream(layer.rendered.layers["main"], start, "yuva420p", loop_frames=frames))
    b.chains.append(f"{b.last}format=yuv420p[v]")
    return FilterGraph(inputs=b.inputs, filter=";".join(b.chains), output="[v]")
