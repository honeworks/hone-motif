"""Import boundaries (CONTRIBUTING "The core is useful alone", design §8): only the Remotion adapter runs
Node, no module imports another honeworks package, and adapters load lazily."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).parents[2] / "src" / "hone_motif"


def imports(path: Path) -> list[tuple[str, int]]:
    """Every imported module name, with the column of its statement (0: at module level)."""
    found: list[tuple[str, int]] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found += [(alias.name, node.col_offset) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            found.append(("." * node.level + (node.module or ""), node.col_offset))
    return found


def test_only_the_remotion_adapter_starts_processes() -> None:
    users = sorted(p.name for p in SRC.glob("*.py") if any(m == "subprocess" for m, _ in imports(p)))
    assert users == ["remotion.py"]


def test_no_sibling_packages() -> None:
    for path in SRC.glob("*.py"):
        for module, _ in imports(path):
            assert not (module.startswith("hone_") and not module.startswith("hone_motif")), (
                path.name,
                module,
            )


def test_the_adapter_is_imported_only_inside_functions() -> None:
    for path in SRC.glob("*.py"):
        for module, column in imports(path):
            if module.endswith("remotion"):
                assert column > 0, f"{path.name} imports the Remotion adapter at module level"
