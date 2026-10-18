"""Perceptual hashes and mean colour of a poster, through ffmpeg (decisions D-007, D-018).

`phash` is a DCT hash of a grey thumbnail: 64 bits by default, 256 for text (`keep=16`), optionally of
one region of the image. `mean_rgb` adds the colour a grey hash cannot see (themes differ by hue).
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

Box = tuple[float, float, float, float]  # x, y, width, height as fractions of the image


def _pixels(image: Path, size: int, fmt: str, box: Box | None) -> bytes:
    crop = f"crop=iw*{box[2]}:ih*{box[3]}:iw*{box[0]}:ih*{box[1]}," if box else ""
    return subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(image),
            "-vf",
            f"{crop}scale={size}:{size}:flags=area,format={fmt}",
            "-f",
            "rawvideo",
            "-",
        ],
        capture_output=True,
        check=True,
    ).stdout


def _dct_rows(rows: list[list[float]], keep: int) -> list[list[float]]:
    n = len(rows[0])
    table = [[math.cos(math.pi * (2 * x + 1) * u / (2 * n)) for x in range(n)] for u in range(keep)]
    return [[sum(row[x] * table[u][x] for x in range(n)) for u in range(keep)] for row in rows]


def phash(image: Path, *, keep: int = 8, box: Box | None = None) -> str:
    """The hash as hex: bit set where a low-frequency DCT coefficient is above their median."""
    size = keep * 4
    raw = _pixels(image, size, "gray", box)
    grey = [[float(raw[y * size + x]) for x in range(size)] for y in range(size)]
    rows = _dct_rows(grey, keep)
    cols = _dct_rows([list(c) for c in zip(*rows, strict=True)], keep)
    coeffs = [cols[u][v] for v in range(keep) for u in range(keep)]
    median = sorted(coeffs[1:])[len(coeffs[1:]) // 2]  # the DC term would dominate
    bits = "".join("1" if c > median else "0" for c in coeffs)
    return f"{int(bits, 2):0{keep * keep // 4}x}"


def mean_rgb(image: Path, box: Box | None = None) -> list[int]:
    """The mean red, green and blue (0-255) of the image, or of one region of it."""
    raw = _pixels(image, 16, "rgb24", box)
    return [round(sum(raw[c::3]) / (len(raw) // 3)) for c in range(3)]


def distance(a: str, b: str) -> int:
    """The Hamming distance between two hashes."""
    return (int(a, 16) ^ int(b, 16)).bit_count()


def mean_difference(a: Path, b: Path, box: Box | None = None, fmt: str = "gray") -> float:
    """The mean absolute difference (0-255) of two images' 128x128 thumbnails (grey, or `fmt`), or of one
    region."""
    pa, pb = _pixels(a, 128, fmt, box), _pixels(b, 128, fmt, box)
    return sum(abs(x - y) for x, y in zip(pa, pb, strict=True)) / len(pa)
