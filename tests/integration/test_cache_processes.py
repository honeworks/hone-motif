"""The cache across processes (design §8.4, §14 case 8).

A render killed halfway leaves nothing; two processes rendering one key render once.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import hone_motif as hm

LIBRARY = Path(__file__).parents[2] / "library"
WORKER = """
import json, sys
from pathlib import Path
import hone_motif as hm
from hone_motif.testing import FakeRenderer
lib = hm.Library(sys.argv[1])
fake = FakeRenderer(delay_s=float(sys.argv[3]))
done = hm.render(lib.get("name-title-clean-bar"), renderer=fake, cache=hm.Cache(sys.argv[2]))
print(json.dumps({"calls": fake.calls, "cached": done.cached, "key": done.key}), flush=True)
"""


def start(cache: Path, delay_s: float) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-c", WORKER, str(LIBRARY), str(cache), str(delay_s)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def wait_for_tmp(cache: Path, timeout_s: float = 20) -> None:
    deadline = time.monotonic() + timeout_s
    while not list(cache.glob("renders/*/.tmp-*/main.webm")):
        assert time.monotonic() < deadline, "the render never started"
        time.sleep(0.05)


def test_a_render_killed_halfway_leaves_no_entry(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    worker = start(cache, delay_s=30)
    wait_for_tmp(cache)
    os.kill(worker.pid, signal.SIGKILL)
    worker.wait()
    assert hm.Cache(cache).info().entries == 0
    again = start(cache, delay_s=0)  # the next render cleans the half-written folder and completes
    out, err = again.communicate(timeout=60)
    assert again.returncode == 0, err
    assert json.loads(out)["calls"] == 1
    assert hm.Cache(cache).info().entries == 1
    assert not list(cache.glob("renders/*/.tmp-*"))


def test_two_processes_render_once(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    first = start(cache, delay_s=1.5)
    wait_for_tmp(cache)
    second = start(cache, delay_s=0)
    results = [json.loads(p.communicate(timeout=60)[0]) for p in (first, second)]
    assert [r["calls"] for r in results] == [1, 0]
    assert results[1]["cached"] is True
    assert results[0]["key"] == results[1]["key"]
    assert hm.Cache(cache).info().entries == 1
