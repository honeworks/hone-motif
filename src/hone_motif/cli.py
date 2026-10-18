"""The command line (design §9): list, show, search, check, check-placements, render, gallery, init, cache."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

from .asset import Asset
from .cache import Cache
from .errors import HoneMotifError, InvalidAssetError, Problem
from .gallery import build_gallery
from .library import Library, default_library_path
from .placement import check_placements
from .render import Renderer, render
from .video import VideoInfo

FILTERS = ("category", "kind", "theme", "mood", "aspect", "script")


def _size(text: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", text)
    if match is None:
        raise argparse.ArgumentTypeError(f"{text!r} is not WIDTHxHEIGHT, e.g. 960x540")
    return int(match[1]), int(match[2])


def _age(text: str) -> timedelta:
    match = re.fullmatch(r"(\d+)([dh])", text)
    if match is None:
        raise argparse.ArgumentTypeError(f"{text!r} is not an age such as 30d or 12h")
    return timedelta(days=int(match[1])) if match[2] == "d" else timedelta(hours=int(match[1]))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hone-motif", description="Code-built video assets: search, check, render, browse."
    )
    parser.add_argument(
        "--library", type=Path, help="a library folder (default: the one installed with hone-motif)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, text in (("list", False), ("search", True)):
        p = sub.add_parser(
            name,
            help="the catalogue as a table" if name == "list" else "text search over names, lines and tags",
        )
        if text:
            p.add_argument("text")
        for f in FILTERS:
            p.add_argument(f"--{f}")
        p.add_argument("--json", action="store_true", help="print JSON")
    sub.add_parser("show", help="an asset's metadata, props schema and placement rules").add_argument("id")
    sub.add_parser("check", help="validate every asset.json (exit 1 on any problem)").add_argument(
        "path", nargs="?", type=Path
    )
    p = sub.add_parser("check-placements", help="check a placement reply against the video (design §7.3)")
    p.add_argument("placements", type=Path)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("render", help="render one asset into the cache")
    p.add_argument("id")
    p.add_argument("--props", type=Path, help="a JSON file of props (default: the asset's example props)")
    p.add_argument("--theme")
    p.add_argument("--fps", type=int, default=32)
    p.add_argument("--aspect", default="16:9")
    p.add_argument("--duration-ms", type=int)
    p.add_argument("--size", type=_size)
    p.add_argument("--out", type=Path, help="also copy the layers and poster here")
    p = sub.add_parser("gallery", help="build the gallery page (design §10)")
    p.add_argument("--out", type=Path)
    p.add_argument("--render-missing", action="store_true")
    p.add_argument(
        "--stills", action="store_true", help="a poster still for every tile, rendered in one batch"
    )
    p.add_argument("--size", type=_size, default=(960, 540))
    p.add_argument("--fps", type=int, default=24)
    p = sub.add_parser("init", help="copy the installed library into a folder, to write your own assets")
    p.add_argument("path", type=Path)
    p = sub.add_parser("cache", help="cache size and clean-up")
    p.add_argument("action", choices=["info", "prune"])
    p.add_argument("--older-than", type=_age, default=timedelta(days=30))
    return parser


def _table(assets: list[Asset]) -> str:
    lines = [f"{'id':<38} {'kind':<10} {'category':<20} themes"]
    lines += [f"{a.id:<38} {a.kind:<10} {a.category:<20} {','.join(a.themes)}" for a in assets]
    return "\n".join(lines)


def _list(lib: Library, args: argparse.Namespace) -> int:
    filters = {f: getattr(args, f) for f in FILTERS}
    found = lib.search(text=getattr(args, "text", None), **filters)
    print(
        json.dumps([a.model_dump(by_alias=True) for a in found], ensure_ascii=False, indent=1)
        if args.json
        else _table(found)
    )
    return 0


def _show(lib: Library, args: argparse.Namespace) -> int:
    asset = lib.get(args.id)
    print(
        json.dumps(
            {**asset.model_dump(by_alias=True), "props_schema": asset.props_schema},
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0


def _print_problems(problems: list[Problem]) -> None:
    for p in problems:
        print(p)


def _check(args: argparse.Namespace) -> int:
    path = args.path or args.library or default_library_path()
    try:
        problems = Library(path).check()
    except InvalidAssetError as e:
        problems = e.problems
    _print_problems(problems)
    print(f"{len(problems)} problem(s) in {path}")
    return 1 if problems else 0


def _check_placements(lib: Library, args: argparse.Namespace) -> int:
    reply: Any = json.loads(args.placements.read_text(encoding="utf-8"))
    placements = cast(list[dict[str, Any]], reply["placements"] if isinstance(reply, dict) else reply)
    video = VideoInfo.model_validate_json(args.video.read_text(encoding="utf-8"))
    report = check_placements(placements, video, lib)
    if args.json:
        print(report.model_dump_json(indent=1))
    else:
        _print_problems(report.errors)
        _print_problems([p.model_copy(update={"code": f"warning {p.code}"}) for p in report.warnings])
        passed = len(report.placements)
        print(
            f"{len(report.errors)} error(s), {len(report.warnings)} warning(s), {passed} placement(s) passed"
        )
    return 0 if report.ok else 1


def _render(lib: Library, args: argparse.Namespace, renderer: Renderer | None) -> int:
    asset = lib.get(args.id)
    props: dict[str, Any] = (
        json.loads(args.props.read_text(encoding="utf-8")) if args.props else dict(asset.props)
    )
    if args.theme:
        props["theme"] = args.theme
    done = render(
        asset,
        props,
        fps=args.fps,
        aspect=args.aspect,
        duration_ms=args.duration_ms,
        size=args.size,
        renderer=renderer,
    )
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        for path in [*done.layers.values(), done.poster, done.render_json]:
            shutil.copy2(path, args.out / path.name)
    print(f"{'cached' if done.cached else 'rendered'}: {done.folder}")
    return 0


def _gallery(lib: Library, args: argparse.Namespace, renderer: Renderer | None) -> int:
    index = build_gallery(
        lib,
        out=args.out,
        render_missing=args.render_missing,
        size=args.size,
        fps=args.fps,
        renderer=renderer,
        stills=args.stills,
    )
    print(index)
    return 0


def main(argv: Sequence[str] | None = None, *, renderer: Renderer | None = None) -> int:
    """Run the command line and return its exit code; `renderer` replaces the default (tests pass a fake)."""
    args = _parser().parse_args(argv)
    try:
        if args.command == "check":
            return _check(args)
        if args.command == "cache":
            return _cache(args)
        if args.command == "init":
            return _init(args)
        lib = Library(args.library)
        commands = {
            "list": lambda: _list(lib, args),
            "search": lambda: _list(lib, args),
            "show": lambda: _show(lib, args),
            "check-placements": lambda: _check_placements(lib, args),
            "render": lambda: _render(lib, args, renderer),
            "gallery": lambda: _gallery(lib, args, renderer),
        }
        return commands[args.command]()
    except HoneMotifError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError) as e:  # an input file that is missing or malformed
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


IGNORE = "node_modules/\nbuild/\n"  # the new library's .gitignore: what npm and the renderer write


def _init(args: argparse.Namespace) -> int:
    """Copy the library (--library, else the installed one) into an empty or new folder."""
    target: Path = args.path
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        print(f"error: {target} exists and is not empty; give a new or empty folder", file=sys.stderr)
        return 2
    source = args.library or default_library_path()
    shutil.copytree(
        source, target, ignore=shutil.ignore_patterns("node_modules", "build"), dirs_exist_ok=True
    )
    (target / ".gitignore").write_text(IGNORE, encoding="utf-8")
    print(f"a library with {len(Library(target).assets)} asset(s) in {target}")
    print(f"next: cd {target} && npm ci && npm run check; then hone-motif --library {target} list")
    return 0


def _cache(args: argparse.Namespace) -> int:
    cache = Cache()
    if args.action == "prune":
        print(f"removed {cache.prune(args.older_than)} render(s) and Node copies from {cache.root}")
        return 0
    info = cache.info()
    print(f"{info.root}: {info.entries} render(s), {info.bytes / 1e6:.1f} MB")
    return 0


def run() -> None:
    """The `hone-motif` console script."""
    sys.exit(main())
