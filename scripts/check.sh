#!/usr/bin/env bash
# All quality gates. "Green" means this script exits 0.
set -euo pipefail
cd "$(dirname "$0")/.."
unset VIRTUAL_ENV   # never use another project's active venv
PKG_IMPORT="$(python3 - <<'PY'
import tomllib; d = tomllib.load(open("pyproject.toml", "rb"))
print(d["project"]["name"].replace("-", "_"))
PY
)"
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "sync"
if [ -f uv.lock ]; then uv sync --all-extras --frozen; else uv sync --all-extras; fi
step "ruff check";   uv run ruff check .
step "ruff format";  uv run ruff format --check .
step "pyright";      uv run pyright
step "pytest (default suite + coverage)"
uv run pytest --cov="src/${PKG_IMPORT}" --cov-branch --cov-report=term-missing:skip-covered --cov-fail-under=90
if [ -f library/package.json ]; then   # the asset library's Node side (design §11): types, props schemas, asset.json
  # npm ci only when the lock's content changed: it deletes node_modules, and with it Remotion's downloaded
  # Chrome (a worktree may share the main checkout's node_modules through a symlink)
  step "library (node)"
  (cd library && LOCK_SHA="$(sha256sum package-lock.json | cut -d' ' -f1)" \
    && { [ "$(cat node_modules/.hone-lock-sha 2>/dev/null)" = "$LOCK_SHA" ] \
         || { npm ci --silent && echo "$LOCK_SHA" > node_modules/.hone-lock-sha; }; } \
    && npm run --silent check)
fi
step "build";        rm -rf dist && uv build
step "wheel smoke test (fresh venv, no extras)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
uv venv -q "$TMP/venv"
# honeworks siblings not on PyPI yet come from their git sources first (hone-motif depends on none today)
mapfile -t SIBLINGS < <(scripts/git-sources.py)
if [ "${#SIBLINGS[@]}" -gt 0 ]; then uv pip install -q --python "$TMP/venv/bin/python" "${SIBLINGS[@]}"; fi
uv pip install -q --python "$TMP/venv/bin/python" dist/*.whl
"$TMP/venv/bin/python" - <<PY
import importlib, sys
m = importlib.import_module("${PKG_IMPORT}")
assert m.__version__, "missing __version__"
print("import ok:", m.__name__, m.__version__)
PY
if [ -f examples/quickstart.py ]; then   # the README quickstart, with only the wheel installed
  (cd "$TMP" && "$TMP/venv/bin/python" "$OLDPWD/examples/quickstart.py")
fi
printf '\n\033[32mALL GATES GREEN\033[0m\n'
