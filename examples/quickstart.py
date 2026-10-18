"""Quickstart: find assets for a video, check a placement reply, and see what to fix.

What: searches the library for a dark music video's candidates, builds what goes into the one placement
call (catalogue, reply schema, guide), and checks a reply as a model might write it.
How: only the public API, from the asset.json files alone; no Node, no model call, no rendering.
Why: this is the path every consumer takes before it renders anything (design §7); the checks are
code, so a wrong reply is caught and repaired before a single frame is drawn.
"""

from __future__ import annotations

import json

import hone_motif as hm

lib = hm.Library()
video = hm.VideoInfo(
    duration_ms=214380,
    aspect="16:9",
    fps=32,
    cuts=[6210, 12040, 41010, 60000],
    busy=[{"start_ms": 14000, "end_ms": 30000}],  # a sung line: quiet_only assets may not go here
    scripts=["Arab", "Latn"],
    platform="youtube",
)

# 1. Candidates: everything that suits the dark theme and the video's frame (the starter assets here;
#    a project points hm.Library at its own library, made with `hone-motif init`).
candidates = lib.search(theme="dark", aspect="16:9")
print(f"{len(candidates)} candidates, e.g. {', '.join(a.id for a in candidates[:3])}")

# 2. What goes into the one placement call (the consumer makes it with its own model).
prompt_parts = {
    "catalog": lib.catalog(candidates, video),
    "reply_schema": hm.placement_schema(candidates),
    "guide": hm.placement_guide(),
}
print(f"catalogue entry keys: {sorted(prompt_parts['catalog'][0])[:6]} ...")

# 3. A reply as a model might write it: the wipe misses the cut, and the name is too long for its bar.
reply = {
    "placements": [
        {
            "asset": "big-title-clean-rise",
            "start_ms": 0,
            "props": {"theme": "dark", "title": "The Long Road"},
        },
        {"asset": "matte-wipe-soft-edge", "start_ms": 40000, "props": {"theme": "dark"}},
        {
            "asset": "name-title-clean-bar",
            "start_ms": 13000,
            "props": {"theme": "dark", "name": "Alexandra Morgan-Whitfield, vocals", "role": "Singer"},
        },
    ]
}
report = hm.check_placements(reply["placements"], video, lib)
for problem in report.errors:
    print(problem)  # each message says what to change; the consumer sends them back in one repair call

# 4. The repaired reply passes, with every default filled in and every duration resolved.
reply["placements"][1]["start_ms"] = 41010 - 750
reply["placements"][2]["props"]["name"] = "Alexandra Morgan"
report = hm.check_placements(reply["placements"], video, lib)
if not report.ok:
    raise SystemExit(f"still failing: {report.errors}")
print(json.dumps([(p.asset, p.start_ms, p.duration_ms) for p in report.placements]))
