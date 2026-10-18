"""The Remotion renderer's process handling (design §8.2), with stand-ins for node and npm."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

import hone_motif as hm
from hone_motif.remotion import RemotionRenderer, job_payload
from hone_motif.render import plan
from tests import fake_node

PILL = "like-subscribe-glass-pill"
LEAK = "light-leak-amber-sweep"


@pytest.fixture
def tools(tmp_path: Path) -> tuple[str, str]:
    return fake_node.install(tmp_path / "bin")


def renderer(tools: tuple[str, str], tmp_path: Path) -> RemotionRenderer:
    node, npm = tools
    return RemotionRenderer(node=node, npm=npm, cache_root=tmp_path / "cache", concurrency=3)


def test_job_payload(lib: hm.Library, tmp_path: Path) -> None:
    job = plan(lib.get(LEAK), fps=24, size=(960, 540))
    payload = job_payload(job, tmp_path / "out", tmp_path / "bundle", 3)
    assert payload["asset"] == LEAK
    assert payload["layers"] == {"matte": "h264", "fx": "h264"}
    assert (payload["fps"], payload["width"], payload["frames"], payload["concurrency"]) == (24, 960, 72, 3)
    assert payload["out_dir"] == str((tmp_path / "out").resolve())
    assert payload["props"]["theme"] == "cinematic"
    assert (payload["aspect"], payload["base"]) == ("16:9", [1920, 1080])


def test_installs_a_copy_once_and_renders(
    lib_copy: Path, tools: tuple[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = renderer(tools, tmp_path)
    lib = hm.Library(lib_copy)
    first = hm.render(lib.get(LEAK), renderer=r, cache=hm.Cache(tmp_path / "cache"))
    assert first.layers["matte"].read_bytes() == b"fake media"
    projects = list((tmp_path / "cache" / "node").iterdir())
    copy = next(p for p in projects if p.is_dir())
    assert (copy / "node_modules" / ".hone-motif-ready").is_file()
    assert (copy / "assets" / LEAK / "asset.json").is_file()
    monkeypatch.setenv("FAKE_NPM_FAIL", "would fail if npm ran again")
    hm.render(lib.get(PILL), renderer=r, cache=hm.Cache(tmp_path / "cache"))
    assert r.project(lib_copy) == copy


def test_a_checkout_with_packages_is_used_in_place(
    lib_copy: Path, tools: tuple[str, str], tmp_path: Path
) -> None:
    (lib_copy / "node_modules" / "remotion").mkdir(parents=True)
    (lib_copy / "node_modules" / "remotion" / "package.json").write_text("{}")
    assert renderer(tools, tmp_path).project(lib_copy) == lib_copy


def test_npm_failure_is_unavailable(
    lib_copy: Path, tools: tuple[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_NPM_FAIL", "network down")
    with pytest.raises(hm.RendererUnavailableError, match="network down") as caught:
        renderer(tools, tmp_path).project(lib_copy)
    assert "Remotion Company License" in str(caught.value)
    assert not [p for p in (tmp_path / "cache" / "node").iterdir() if p.is_dir()]


@pytest.mark.parametrize("version", ["v18.19.0", "v22.17.9", "nonsense"])
def test_old_node_is_unavailable(
    lib: hm.Library, tools: tuple[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    monkeypatch.setenv("FAKE_NODE_VERSION", version)
    with pytest.raises(hm.RendererUnavailableError, match="too old"):
        renderer(tools, tmp_path).check_node()


def test_missing_node_says_how_to_install(tmp_path: Path) -> None:
    r = RemotionRenderer(node=str(tmp_path / "no-node"), cache_root=tmp_path)
    with pytest.raises(hm.RendererUnavailableError, match=r"nodejs\.org"):
        r.check_node()


def test_a_failed_render_carries_the_log(
    lib: hm.Library, tools: tuple[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_NODE_FAIL", "composition not found")
    cache = hm.Cache(tmp_path / "renders")
    with pytest.raises(hm.RenderError, match="exit 3") as caught:
        hm.render(lib.get(PILL), renderer=renderer(tools, tmp_path), cache=cache)
    assert "composition not found" in caught.value.log
    assert cache.info().entries == 0


def test_missing_files_after_a_render_are_an_error(
    lib: hm.Library, tools: tuple[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_NODE_SKIP_WRITE", "1")
    with pytest.raises(hm.RenderError, match="did not write"):
        hm.render(lib.get(PILL), renderer=renderer(tools, tmp_path), cache=hm.Cache(tmp_path / "renders"))


def test_the_job_file_is_left_for_people(lib: hm.Library, tools: tuple[str, str], tmp_path: Path) -> None:
    done = hm.render(lib.get(PILL), renderer=renderer(tools, tmp_path), cache=hm.Cache(tmp_path / "renders"))
    job = json.loads((done.folder / "job.json").read_text(encoding="utf-8"))
    assert job["asset"] == PILL


def test_a_render_that_takes_too_long(
    lib: hm.Library, tools: tuple[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_NODE_SLEEP", "5")
    node, npm = tools
    slow = RemotionRenderer(node=node, npm=npm, cache_root=tmp_path / "cache", timeout_s=0.5)
    cache = hm.Cache(tmp_path / "renders")
    with pytest.raises(hm.RenderError, match=r"took longer than 0\.5 s") as caught:
        hm.render(lib.get(PILL), renderer=slow, cache=cache)
    assert "starting" in caught.value.log
    assert cache.info().entries == 0


@pytest.mark.skipif(sys.platform == "win32", reason="process groups are POSIX")
def test_a_timeout_stops_the_browser_too(
    lib: hm.Library, tools: tuple[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A render's children (Remotion's Chrome) die with it on a timeout, and hold up nothing."""
    pid_file = tmp_path / "child.pid"
    monkeypatch.setenv("FAKE_NODE_CHILD", str(pid_file))
    monkeypatch.setenv("FAKE_NODE_SLEEP", "60")
    node, npm = tools
    slow = RemotionRenderer(node=node, npm=npm, cache_root=tmp_path / "cache", timeout_s=1)
    started = time.monotonic()
    with pytest.raises(hm.RenderError, match="took longer"):
        hm.render(lib.get(PILL), renderer=slow, cache=hm.Cache(tmp_path / "renders"))
    assert time.monotonic() - started < 20
    child = int(pid_file.read_text(encoding="utf-8"))
    for _ in range(100):
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    os.kill(child, 9)
    raise AssertionError("the render's child process outlived the timeout")


@pytest.mark.parametrize("output", ["Remotion says hello", "{}", " "])
def test_output_without_a_result_is_a_render_error(
    lib: hm.Library, tools: tuple[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str
) -> None:
    monkeypatch.setenv("FAKE_NODE_GARBAGE", output)
    with pytest.raises(hm.RenderError, match="printed no result"):
        hm.render(lib.get(PILL), renderer=renderer(tools, tmp_path), cache=hm.Cache(tmp_path / "renders"))


def test_missing_npm_says_how_to_install(lib_copy: Path, tools: tuple[str, str], tmp_path: Path) -> None:
    r = RemotionRenderer(node=tools[0], npm=str(tmp_path / "no-npm"), cache_root=tmp_path / "cache")
    with pytest.raises(hm.RendererUnavailableError, match="npm was not found"):
        r.project(lib_copy)


def test_poster_stills_render_once_per_asset(
    lib: hm.Library, tools: tuple[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hone_motif.remotion import poster_stills, still_names  # noqa: PLC0415

    cache = hm.Cache(tmp_path / "c")
    assets = [lib.get(PILL), lib.get(LEAK)]
    folders = poster_stills(renderer(tools, tmp_path), assets, cache)
    assert set(folders) == {PILL, LEAK}
    assert sorted(p.name for p in folders[PILL].glob("*.jpg")) == sorted(
        f"{n}.jpg" for n in still_names(lib.get(PILL))
    )
    assert "rtl.jpg" in {p.name for p in folders[PILL].iterdir()}
    monkeypatch.setenv("FAKE_NODE_FAIL", "must not run again")
    assert poster_stills(renderer(tools, tmp_path), assets, cache) == folders


def test_a_stills_run_that_renders_nothing_is_an_error(
    lib: hm.Library, tools: tuple[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hone_motif.remotion import poster_stills  # noqa: PLC0415

    monkeypatch.setenv("FAKE_NODE_FAIL", "no browser")
    with pytest.raises(hm.RenderError, match="rendered no still") as caught:
        poster_stills(renderer(tools, tmp_path), [lib.get(PILL)], hm.Cache(tmp_path / "c"))
    assert "no browser" in caught.value.log


def test_an_asset_whose_stills_failed_is_left_out_and_retried(
    lib: hm.Library,
    tools: tuple[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from hone_motif.remotion import poster_stills  # noqa: PLC0415

    cache = hm.Cache(tmp_path / "c")
    assets = [lib.get(PILL), lib.get(LEAK)]
    monkeypatch.setenv("FAKE_STILLS_SKIP", LEAK)
    assert set(poster_stills(renderer(tools, tmp_path), assets, cache)) == {PILL}
    assert f"stills missing for {LEAK}" in caplog.text
    monkeypatch.delenv("FAKE_STILLS_SKIP")
    assert set(poster_stills(renderer(tools, tmp_path), assets, cache)) == {PILL, LEAK}


def test_changing_an_asset_renders_its_stills_again(
    lib_copy: Path, tools: tuple[str, str], tmp_path: Path
) -> None:
    from hone_motif.remotion import poster_stills  # noqa: PLC0415

    cache = hm.Cache(tmp_path / "c")
    first = poster_stills(renderer(tools, tmp_path), [hm.Library(lib_copy).get(PILL)], cache)[PILL]
    (lib_copy / "assets" / PILL / "composition.tsx").write_text("// changed\n", encoding="utf-8")
    second = poster_stills(renderer(tools, tmp_path), [hm.Library(lib_copy).get(PILL)], cache)[PILL]
    assert second != first
    assert (second / ".done").is_file()


def test_the_gallery_uses_stills_where_nothing_is_rendered(
    lib_copy: Path, tools: tuple[str, str], tmp_path: Path
) -> None:
    from tests.unit.test_gallery import data_of  # noqa: PLC0415

    folder = lib_copy / "assets" / "epigraph-verse-couplet"
    data = json.loads((folder / "asset.json").read_text(encoding="utf-8"))
    data["aspects"], data["regions"] = ["16:9", "9:16"], {"16:9": "full", "9:16": "full"}
    (folder / "asset.json").write_text(json.dumps(data), encoding="utf-8")
    index = hm.build_gallery(
        hm.Library(lib_copy), cache=hm.Cache(tmp_path / "c"), renderer=renderer(tools, tmp_path), stills=True
    )
    for tile in data_of(index)["tiles"]:
        name = tile["theme"] if tile["aspect"] == "16:9" else f"{tile['theme']}@{tile['aspect']}"
        assert tile["poster"].endswith(f"/{name}.jpg"), tile
        assert (index.parent / tile["poster"]).is_file()


def test_gallery_stills_need_the_remotion_renderer(lib: hm.Library, tmp_path: Path) -> None:
    from hone_motif.testing import FakeRenderer  # noqa: PLC0415

    with pytest.raises(hm.RendererUnavailableError, match="needs the Remotion renderer"):
        hm.build_gallery(lib, cache=hm.Cache(tmp_path / "c"), renderer=FakeRenderer(), stills=True)
