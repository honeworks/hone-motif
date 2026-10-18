"""Every example runs, and the README's quickstart is the one in examples/ (CONTRIBUTING, "Tests")."""

from __future__ import annotations

import re
import runpy
from pathlib import Path

import pytest

import hone_motif as hm
from hone_motif.testing import FakeRenderer

EXAMPLES = Path(__file__).parents[2] / "examples"


@pytest.mark.parametrize("example", sorted(EXAMPLES.glob("*.py")), ids=lambda p: p.name)
def test_example_runs(example: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = example.read_text(encoding="utf-8")
    assert all(word in source for word in ("What:", "How:", "Why:")), "examples open with What / How / Why"
    assert example.name in (EXAMPLES / "README.md").read_text(encoding="utf-8")
    runpy.run_path(str(example), run_name="__main__")
    assert capsys.readouterr().out


def test_the_readme_quickstart_runs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The README's Python block, with the model's reply given and the fake renderer instead of Node."""
    readme = (EXAMPLES.parent / "README.md").read_text(encoding="utf-8")
    [block] = re.findall(r"```python\n(.*?)```", readme, re.S)
    real_render = hm.render
    monkeypatch.setattr(
        hm, "render", lambda *a, **k: real_render(*a, **k, renderer=FakeRenderer(), cache=hm.Cache(tmp_path))
    )
    reply = {"placements": [{"asset": "matte-wipe-soft-edge", "start_ms": 40260, "props": {"theme": "dark"}}]}
    namespace: dict[str, object] = {"reply": reply}
    exec(compile(block, "README.md", "exec"), namespace)  # noqa: S102 - our own README
    assert isinstance(namespace["clip"], hm.Rendered)
    assert "examples/quickstart.py" in readme
