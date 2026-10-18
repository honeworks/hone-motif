"""The command line (design §9), run in-process with the fake renderer."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import hone_motif as hm
from hone_motif.cli import main
from hone_motif.testing import FakeRenderer
from tests.helpers import video

LIBRARY = ""  # the fixture library's folder, set for every test by `own_cache`
PILL = "like-subscribe-glass-pill"


@pytest.fixture(autouse=True)
def own_cache(tmp_path: Path, fixture_root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HONE_MOTIF_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(sys.modules[__name__], "LIBRARY", str(fixture_root))
    return tmp_path / "cache"


def run(
    capsys: pytest.CaptureFixture[str], *argv: str, renderer: hm.Renderer | None = None
) -> tuple[int, str]:
    code = main(["--library", LIBRARY, *argv], renderer=renderer)
    return code, capsys.readouterr().out


def test_list_and_filters(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(capsys, "list", "--kind", "transition")
    assert code == 0
    assert "light-leak-amber-sweep" in out
    assert PILL not in out
    code, out = run(capsys, "list", "--category", "captions", "--json")
    found = json.loads(out)
    assert {"karaoke-fill-focus", "karaoke-fill-slide", "karaoke-fill-sweep"} <= {a["id"] for a in found}
    assert {a["category"] for a in found} == {"captions"}


def test_search(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(capsys, "search", "subscribe", "--json")
    assert code == 0
    assert PILL in [a["id"] for a in json.loads(out)]


def test_show(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(capsys, "show", PILL)
    shown = json.loads(out)
    assert code == 0
    assert shown["id"] == PILL
    assert shown["props_schema"]["properties"]["channelName"]["maxLength"] == 24


def test_unknown_asset_is_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--library", LIBRARY, "show", "nope"]) == 2
    assert "hone-motif list" in capsys.readouterr().err


def test_check(capsys: pytest.CaptureFixture[str], lib_copy: Path) -> None:
    assert main(["check", LIBRARY]) == 0
    assert "0 problem(s)" in capsys.readouterr().out
    (lib_copy / "assets" / PILL / "asset.json").write_text("{not json")
    assert main(["check", str(lib_copy)]) == 1
    assert "invalid-asset-json" in capsys.readouterr().out


def test_check_placements(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    (tmp_path / "video.json").write_text(video().model_dump_json())
    good = {"placements": [{"asset": "light-leak-amber-sweep", "start_ms": 39510}]}
    (tmp_path / "good.json").write_text(json.dumps(good))
    code, out = run(
        capsys, "check-placements", str(tmp_path / "good.json"), "--video", str(tmp_path / "video.json")
    )
    assert (code, out.strip().splitlines()[-1]) == (0, "0 error(s), 0 warning(s), 1 placement(s) passed")
    bad = [
        {"asset": "light-leak-amber-sweep", "start_ms": 1000},
        {"asset": "chapter-card-star-band", "start_ms": 13000, "props": {"label": "Verse"}},
    ]
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    code, out = run(
        capsys, "check-placements", str(tmp_path / "bad.json"), "--video", str(tmp_path / "video.json")
    )
    assert code == 1
    assert "off-cut" in out
    assert "warning scene-over-busy" in out
    code, out = run(
        capsys,
        "check-placements",
        str(tmp_path / "bad.json"),
        "--video",
        str(tmp_path / "video.json"),
        "--json",
    )
    assert json.loads(out)["errors"][0]["code"] == "off-cut"


def test_render_and_copy_out(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    fake = FakeRenderer()
    (tmp_path / "props.json").write_text(json.dumps({"channelName": "Hone"}))
    argv = ["render", PILL, "--props", str(tmp_path / "props.json"), "--theme", "pop", "--size", "960x540"]
    code, out = run(capsys, *argv, "--out", str(tmp_path / "out"), renderer=fake)
    assert code == 0
    assert out.startswith("rendered: ")
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["main.webm", "poster.jpg", "render.json"]
    record = json.loads((tmp_path / "out" / "render.json").read_text())
    assert record["props"]["theme"] == "pop"
    assert record["width"] == 960
    code, out = run(capsys, *argv, renderer=fake)
    assert out.startswith("cached: ")
    assert fake.calls == 1


def test_render_rejects_bad_props(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--library", LIBRARY, "render", PILL, "--theme", "neon"], renderer=FakeRenderer())
    assert code == 2
    assert "not-allowed" in capsys.readouterr().err


def test_gallery(capsys: pytest.CaptureFixture[str], tmp_path: Path, lib: hm.Library) -> None:
    argv = ["--library", str(lib.root), "gallery", "--out", str(tmp_path / "g"), "--render-missing"]
    code = main(argv, renderer=FakeRenderer())
    out = capsys.readouterr().out
    assert code == 0
    assert Path(out.strip()) == tmp_path / "g" / "index.html"
    assert (tmp_path / "g" / "index.html").is_file()


def test_cache_info_and_prune(capsys: pytest.CaptureFixture[str], own_cache: Path) -> None:
    run(capsys, "render", PILL, renderer=FakeRenderer())
    assert main(["cache", "info"]) == 0
    assert "1 render(s)" in capsys.readouterr().out
    assert main(["cache", "prune", "--older-than", "12h"]) == 0
    assert "removed 0 render(s)" in capsys.readouterr().out
    assert main(["cache", "prune", "--older-than", "0d"]) == 0
    assert "removed 1 render(s)" in capsys.readouterr().out


def test_a_bad_age_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["cache", "prune", "--older-than", "soon"])
    assert caught.value.code == 2
    assert "30d or 12h" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("content", "error"),
    [(None, "FileNotFoundError"), ("{not json", "JSONDecodeError"), ('{"nothing": []}', "KeyError")],
)
def test_a_bad_placements_file_is_one_line_and_exit_2(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, content: str | None, error: str
) -> None:
    (tmp_path / "video.json").write_text(video().model_dump_json())
    if content is not None:
        (tmp_path / "reply.json").write_text(content)
    code = main(
        [
            "--library",
            LIBRARY,
            "check-placements",
            str(tmp_path / "reply.json"),
            "--video",
            str(tmp_path / "video.json"),
        ]
    )
    err = capsys.readouterr().err
    assert code == 2
    assert err.startswith(f"error: {error}")
    assert "Traceback" not in err


def test_a_bad_video_file_is_exit_2(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    (tmp_path / "reply.json").write_text('{"placements": []}')
    (tmp_path / "video.json").write_text('{"duration_ms": 1.5}')
    assert (
        main(
            [
                "--library",
                LIBRARY,
                "check-placements",
                str(tmp_path / "reply.json"),
                "--video",
                str(tmp_path / "video.json"),
            ]
        )
        == 2
    )
    assert "duration_ms" in capsys.readouterr().err


def test_usage_errors_exit_2_with_a_message(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--library", LIBRARY, "render", PILL, "--size", "big"])
    assert caught.value.code == 2
    assert "not WIDTHxHEIGHT" in capsys.readouterr().err


def test_the_console_script_runs() -> None:
    done = subprocess.run(
        [str(Path(sys.executable).parent / "hone-motif"), "check", LIBRARY],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert "0 problem(s)" in done.stdout


def test_gallery_stills_reach_build_gallery(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def fake_build(lib: hm.Library, **kwargs: object) -> Path:
        seen.update(kwargs)
        return tmp_path / "index.html"

    monkeypatch.setattr("hone_motif.cli.build_gallery", fake_build)
    assert main(["--library", LIBRARY, "gallery", "--stills"]) == 0
    assert seen["stills"] is True
