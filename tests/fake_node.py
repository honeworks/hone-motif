"""Stand-ins for `node` and `npm` that the Remotion renderer can run without Node (tests only).

`node --version` prints `FAKE_NODE_VERSION` (default v24.0.0); `node scripts/render.ts job.json` writes
the job's layers and poster as small files and prints the result line render.ts prints. Switches:
`FAKE_NODE_FAIL` (exit 3 with that error), `FAKE_NODE_SLEEP` (seconds to wait first),
`FAKE_NODE_GARBAGE` (print that instead of a result), `FAKE_NODE_SKIP_WRITE`, `FAKE_NODE_CHILD` (start
a child that sleeps, holding the output pipes as a browser would, and write its pid there); `npm ci` makes a
node_modules folder, or fails with `FAKE_NPM_FAIL`.
"""

from __future__ import annotations

import stat
from pathlib import Path

NODE = """#!/usr/bin/env python3
import json, os, sys
if sys.argv[1:] == ["--version"]:
    print(os.environ.get("FAKE_NODE_VERSION", "v24.0.0"))
    sys.exit(0)
if os.environ.get("FAKE_NODE_CHILD"):
    import subprocess
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    open(os.environ["FAKE_NODE_CHILD"], "w").write(str(child.pid))
if os.environ.get("FAKE_NODE_SLEEP"):
    import time
    print("starting", flush=True)
    time.sleep(float(os.environ["FAKE_NODE_SLEEP"]))
if os.environ.get("FAKE_NODE_GARBAGE"):
    print(os.environ["FAKE_NODE_GARBAGE"])
    sys.exit(0)
if os.environ.get("FAKE_NODE_FAIL"):
    print("Error: " + os.environ["FAKE_NODE_FAIL"], file=sys.stderr)
    sys.exit(3)
if sys.argv[1] == "scripts/stills.ts":
    out, ids = sys.argv[2], open(sys.argv[sys.argv.index("--ids-file") + 1]).read().split()
    if os.environ.get("FAKE_NODE_FAIL"):
        print("stills failed: " + os.environ["FAKE_NODE_FAIL"], file=sys.stderr)
        sys.exit(1)
    for i in ids:
        if i == os.environ.get("FAKE_STILLS_SKIP"):
            continue
        meta = json.load(open(os.path.join("assets", i, "asset.json")))
        names = meta["themes"] + list(meta.get("samples", {}))
        for aspect in meta["aspects"]:
            for n in names:
                name = n if aspect == "16:9" else n + "@" + aspect
                open(os.path.join(out, i + "--" + name + ".jpg"), "wb").write(b"fake still")
    sys.exit(0)
job = json.load(open(sys.argv[2]))
ext = {"webm": "webm", "h264": "mp4", "prores": "mov"}
layers = {}
for layer, fmt in job["layers"].items():
    layers[layer] = f"{layer}.{ext[fmt]}"
    if not os.environ.get("FAKE_NODE_SKIP_WRITE"):
        open(os.path.join(job["out_dir"], layers[layer]), "wb").write(b"fake media")
open(os.path.join(job["out_dir"], "poster.jpg"), "wb").write(b"fake poster")
print("bundling...")
print(json.dumps({"layers": layers, "poster": "poster.jpg"}))
"""

NPM = """#!/usr/bin/env python3
import os, sys
if os.environ.get("FAKE_NPM_FAIL"):
    print("npm ERR! " + os.environ["FAKE_NPM_FAIL"])
    sys.exit(1)
os.makedirs("node_modules/remotion", exist_ok=True)
"""


def install(folder: Path) -> tuple[str, str]:
    """Write the fake `node` and `npm` into `folder`; returns their paths."""
    folder.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for name, source in (("node", NODE), ("npm", NPM)):
        path = folder / name
        path.write_text(source, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        paths.append(str(path))
    return paths[0], paths[1]
