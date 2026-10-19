"""The Remotion renderer (design §8.2): the only part of hone-motif that runs Node."""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .asset import Asset
from .cache import READY, SKIP, Cache, default_cache_root, file_hash, file_lock, folder_hash
from .errors import RenderError, RendererUnavailableError
from .render import LAYOUT, RenderJob, pipeline_hash, shared_hash

REMOTION_VERSION = "4.0.534"  # pinned in library/package.json (decision D-009)
NODE_MIN = (22, 18)  # runs the library's TypeScript scripts without a build step
log = logging.getLogger("hone_motif")
INSTALL = (
    "Rendering needs Node {need} or newer (https://nodejs.org) with npm; hone-motif installs the "
    "library's packages (Remotion {remotion}) into its cache on first use, which needs the network once. "
    "Remotion has its own licence: free for individuals, for-profit companies with up to three employees "
    "and non-profits; larger companies need a Remotion Company License (https://www.remotion.dev/license)."
).format(need=".".join(map(str, NODE_MIN)), remotion=REMOTION_VERSION)


def job_payload(job: RenderJob, out_dir: Path, bundle_dir: Path, concurrency: int) -> dict[str, Any]:
    """The job file `library/scripts/render.ts` reads."""
    return {
        "format_version": "1",
        "asset": job.asset.id,
        "kind": job.asset.kind,
        "props": job.props,
        "aspect": job.aspect,
        "base": list(LAYOUT[job.aspect]),
        "fps": job.fps,
        "width": job.width,
        "height": job.height,
        "frames": job.frames,
        "poster_frame": job.poster_frame,
        "layers": job.layers,
        "out_dir": str(out_dir.resolve()),
        "bundle_dir": str(bundle_dir.resolve()),
        "concurrency": concurrency,
        "inputs": {k: str(v) for k, v in job.inputs.items()},
    }


class RemotionRenderer:
    """Renders with Node and Remotion on the CPU (SwiftShader).

    Concurrency comes from `HONE_MOTIF_RENDER_CONCURRENCY` (default 2).
    """

    name = "remotion"
    version = REMOTION_VERSION

    def __init__(
        self,
        *,
        node: str = "node",
        npm: str = "npm",
        cache_root: Path | None = None,
        concurrency: int | None = None,
        timeout_s: float = 3600,
    ) -> None:
        self.node = node
        self.npm = npm
        self.cache_root = cache_root or default_cache_root()
        self.concurrency = concurrency or int(os.environ.get("HONE_MOTIF_RENDER_CONCURRENCY", "2"))
        self.timeout_s = timeout_s

    def check_node(self) -> None:
        """Raise RendererUnavailableError, saying how to install, when Node is missing or too old."""
        found = shutil.which(self.node)
        if found is None:
            raise RendererUnavailableError(f"Node was not found ({self.node!r}). {INSTALL}")
        version = subprocess.run(  # noqa: S603 - our own command line
            [found, "--version"], capture_output=True, text=True, check=False
        ).stdout.strip()
        match = re.match(r"v(\d+)\.(\d+)", version)
        if match is None or (int(match[1]), int(match[2])) < NODE_MIN:
            raise RendererUnavailableError(f"Node {version or '(unknown version)'} is too old. {INSTALL}")

    def project(self, library: Path) -> Path:
        """The library with its Node packages: the checkout in development, else a copy in the cache."""
        if (library / "node_modules" / "remotion" / "package.json").is_file():
            return library
        target = self.cache_root / "node" / folder_hash(library)[:16]
        ready = target / "node_modules" / READY
        with file_lock(target.parent / f"{target.name}.lock"):
            if ready.is_file():
                ready.touch()  # last used now: `cache prune` keeps it
                return target
            tmp = target.parent / f".tmp-{target.name}"
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.copytree(library, tmp, ignore=shutil.ignore_patterns(*SKIP))
            npm = shutil.which(self.npm)
            if npm is None:
                raise RendererUnavailableError(f"npm was not found ({self.npm!r}). {INSTALL}")
            done = subprocess.run(  # noqa: S603 - our own command line
                [npm, "ci", "--no-audit", "--no-fund"], cwd=tmp, capture_output=True, text=True, check=False
            )
            if done.returncode != 0:
                shutil.rmtree(tmp, ignore_errors=True)
                raise RendererUnavailableError(
                    f"`npm ci` failed in a copy of the library:\n{done.stdout}{done.stderr}\n{INSTALL}"
                )
            (tmp / "node_modules" / READY).touch()
            shutil.rmtree(target, ignore_errors=True)
            tmp.rename(target)
        return target

    def render(self, job: RenderJob, out_dir: Path) -> dict[str, Path]:
        self.check_node()
        library = job.asset.library_root
        project = self.project(library)
        bundle = project / "build" / f"bundle-{folder_hash(library)[:16]}"
        job_file = out_dir / "job.json"
        job_file.write_text(
            json.dumps(job_payload(job, out_dir, bundle, self.concurrency), ensure_ascii=False),
            encoding="utf-8",
        )
        log = self._run(job, project, job_file)
        return _files(job, out_dir, log)

    def _run(self, job: RenderJob, project: Path, job_file: Path) -> str:
        """Run render.ts on the job file; returns its output, or raises RenderError carrying it."""
        node = shutil.which(self.node) or self.node
        try:
            code, out, err = run_group([node, "scripts/render.ts", str(job_file)], project, self.timeout_s)
        except subprocess.TimeoutExpired as e:
            raise RenderError(
                f"rendering {job.asset.id} took longer than {self.timeout_s} s", log=_output(e)
            ) from e
        if code != 0:
            raise RenderError(f"Remotion failed to render {job.asset.id} (exit {code})", log=out + err)
        return out


def run_group(command: list[str], cwd: Path, timeout_s: float) -> tuple[int, str, str]:
    """Run `command` in its own process group; returns (exit code, stdout, stderr).

    On a timeout the whole group is killed, Remotion's browser included, before TimeoutExpired is raised
    with the output so far; a browser left holding the pipes would otherwise keep this call waiting.
    """
    posix = sys.platform != "win32"
    with subprocess.Popen(  # noqa: S603 - our own command line
        command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=posix
    ) as process:
        try:
            out, err = process.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            _kill(process, posix)
            out, err = process.communicate()
            raise subprocess.TimeoutExpired(command, timeout_s, output=out, stderr=err) from None
        except BaseException:  # interrupted: leave no browser behind
            _kill(process, posix)
            raise
    return process.returncode, out, err


def _kill(process: subprocess.Popen[str], posix: bool) -> None:
    if posix:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    process.kill()


def _output(e: subprocess.TimeoutExpired) -> str:
    parts = (e.stdout, e.stderr)
    return "".join(x.decode(errors="replace") if isinstance(x, bytes) else x or "" for x in parts)


def _files(job: RenderJob, out_dir: Path, log: str) -> dict[str, Path]:
    """The files render.ts reports on its last line of output, each checked to exist."""
    try:
        result = json.loads(log.strip().splitlines()[-1])
        files = {name: out_dir / file for name, file in result["layers"].items()}
        files["poster"] = out_dir / result["poster"]
    except (IndexError, ValueError, KeyError, TypeError, AttributeError) as e:
        raise RenderError(f"Remotion finished but printed no result for {job.asset.id} ({e})", log=log) from e
    missing = [str(p) for p in files.values() if not p.is_file()]
    if missing:
        raise RenderError(f"Remotion finished but did not write {', '.join(missing)}", log=log)
    return files


def still_names(asset: Asset) -> list[str]:
    """The poster stills `scripts/stills.ts` writes for an asset: `<theme, sample or brand>[@<aspect>]`
    (`brand`: the first theme under the sample brand, change 0003)."""
    names = [*asset.themes, *asset.samples, "brand"]
    return [n if aspect == "16:9" else f"{n}@{aspect}" for aspect in asset.aspects for n in names]


def _stills_key(asset: Asset, fonts: str, tool: str) -> str:
    inputs = [asset.id, folder_hash(asset.folder), shared_hash(asset), fonts, tool]
    return hashlib.sha256(json.dumps(inputs).encode()).hexdigest()


def poster_stills(renderer: RemotionRenderer, assets: list[Asset], cache: Cache) -> dict[str, Path]:
    """Every asset's poster stills (each theme, aspect and sample, at half the layout size), rendered once
    in one browser and kept in `<cache>/stills/<key>/` (decision D-027); returns the folder per asset id."""
    if not assets:
        return {}
    library = assets[0].library_root
    fonts = folder_hash(library / "fonts")
    tool = pipeline_hash(library) + file_hash(library / "scripts" / "stills.ts")
    folders = {a.id: cache.root / "stills" / _stills_key(a, fonts, tool) for a in assets}
    missing = [a for a in assets if not (folders[a.id] / ".done").is_file()]
    if missing:
        renderer.check_node()
        _render_stills(renderer, library, missing, folders, cache.root / "stills")
    return {a.id: folders[a.id] for a in assets if (folders[a.id] / ".done").is_file()}


def _render_stills(
    renderer: RemotionRenderer, library: Path, assets: list[Asset], folders: dict[str, Path], root: Path
) -> None:
    project = renderer.project(library)
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root, prefix=".tmp-") as tmp:
        ids = Path(tmp) / "ids.txt"
        ids.write_text("\n".join(a.id for a in assets) + "\n", encoding="utf-8")
        bundle = (project / "build" / f"stills-bundle-{folder_hash(library)[:16]}").resolve()
        node = shutil.which(renderer.node) or renderer.node
        command = [node, "scripts/stills.ts", tmp, "--ids-file", str(ids), "--bundle", str(bundle)]
        try:
            code, out, err = run_group(command, project, renderer.timeout_s * 4)
        except subprocess.TimeoutExpired as e:
            _keep_finished(Path(tmp), assets, folders)  # a timeout keeps what finished
            raise RenderError(f"scripts/stills.ts took longer than {e.timeout} s", log=_output(e)) from e
        kept = _keep_finished(Path(tmp), assets, folders)  # failed stills show as missing files
        if code != 0 and not kept:
            raise RenderError("scripts/stills.ts rendered no still", log=out + err)
        left = sorted({a.id for a in assets} - kept)
        if left:
            failed = [line for line in err.splitlines() if line.startswith("FAILED")]
            log.warning("stills missing for %s; %s", ", ".join(left), "; ".join(failed[:20]))


def _keep_finished(tmp: Path, assets: list[Asset], folders: dict[str, Path]) -> set[str]:
    """Move the stills of every asset that has all of them into its cache folder; returns their ids."""
    kept: set[str] = set()
    for asset in assets:
        files = [tmp / f"{asset.id}--{n}.jpg" for n in still_names(asset)]
        if not all(f.is_file() for f in files):
            continue
        folder = folders[asset.id]
        folder.mkdir(parents=True, exist_ok=True)
        for f in files:
            f.replace(folder / f.name.split("--", 1)[1])
        (folder / ".done").touch()
        kept.add(asset.id)
    return kept
