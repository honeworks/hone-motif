"""Brand tokens: draw an asset in a channel's own colours and fonts.

What: gives the end-of-video title a channel's brand over the dark theme, checks it, and shows the two
ways a brand goes wrong: a font outside the registry (refused) and ink too close to the backdrop (a
warning).
How: only the public API (`check_props`, `brand_warnings`, `check_placements`); no Node, no rendering.
Why: a channel's thumbnails, banner and motion assets should look like one channel (change 0003); the
theme still gives the motion and texture, the brand gives the colours and type.
"""

from __future__ import annotations

import hone_motif as hm

lib = hm.Library()
asset = lib.get("big-title-clean-rise")
brand = {
    "bg": "#0e2a2f",
    "ink": "#e8fff6",
    "inkSoft": "#9fd6c6",
    "accent": "#ff7a1a",
    "fonts": {"display": "Montserrat", "body": "Inter"},  # families from library/fonts/fonts.json
}
props = {**asset.props, "theme": "dark", "brand": brand}
print("branded props:", hm.check_props(asset, props) or "valid", "|", hm.brand_warnings(props) or "readable")

# A font the registry does not have is refused, naming the families it does have.
[problem] = hm.check_props(asset, {**props, "brand": {**brand, "fonts": {"display": "Comic Sans MS"}}})
print(f"{problem.code} at {problem.field}: {problem.message[:60]}…")

# Grey on grey is legal but hard to read: a warning, so the consumer decides.
grey = {**props, "brand": {**brand, "bg": "#777777", "ink": "#888888"}}
print("low contrast:", [w.code for w in hm.brand_warnings(grey)])
