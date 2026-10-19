# hone-motif

**The engine for a library of video assets that code builds and an AI places.** Intros, lower thirds,
like & subscribe overlays, end screens, chapter cards, transitions, backgrounds, loops and captions,
written as code, each with a typed props schema, five looks (cinematic, dark, documentary, warm,
energetic) and the placement rules a planner needs. Search your catalogue, let a model place assets
across a whole video in one call, check the placements in code, and render each asset once into a local
cache.

Part of **[honeworks](https://github.com/honeworks)**: small, standalone tools for reliable generative-AI
workflows. Made first for [hone-music-video](https://github.com/honeworks/hone-music-video)'s YouTube
version; usable by any project that cuts a video.

> **Status: 0.1.0, unreleased.** The asset model, search, props and placement checks, the renderer port
> with the Remotion renderer, the render cache, the command line and the gallery, with three starter
> assets. Projects write their own assets (below). The design is in [design/current.md](design/current.md).

## What it does

1. **A catalogue you can filter:** every asset has an id, a category, a kind (overlay, scene, transition,
   background, loop, caption), tags, themes, moods, scripts (right-to-left included), aspect ratios, a
   duration, a screen region and the rules for where it may go.
2. **Typed props:** each asset's text and settings have a JSON Schema with maximum lengths, so a
   planner's choices are checked before anything renders.
3. **One placement call per video:** the catalogue, a reply schema and a short guide go into one call
   that returns every placement (`asset`, `start_ms`, `props`); `check_placements` validates them all.
4. **Render once:** a renderer turns an asset and its props into WebM with alpha (or a matte and an
   effect layer for transitions, with the cut frame); the result is cached by its inputs.
5. **A gallery:** a generated page shows every asset in every theme, for people choosing by eye.

## The starter assets

| Asset | Kind | What it is |
|---|---|---|
| `name-title-clean-bar` | overlay | a name and a role on a panel with an accent bar, in any of nine anchors |
| `matte-wipe-soft-edge` | transition | a soft diagonal wipe with a thin accent line on its edge |
| `big-title-clean-rise` | scene | a big title and a subtitle rising on the theme's backdrop |

Each comes in five themes and in 16:9, 9:16 and 1:1, and sets Latin and Arabic-script text. Any asset
also takes a `brand`, a channel's own colours and registry fonts over its theme
([examples/brand.py](examples/brand.py), design §4.3).

## Quickstart

```bash
pip install .            # from a checkout; hone-motif is not published yet
```

```python
import hone_motif as hm

lib = hm.Library()  # the library shipped in the package; hm.Library("my-assets") for your own
video = hm.VideoInfo(
    duration_ms=214380,
    aspect="16:9",
    fps=32,
    cuts=[6210, 41010],
    busy=[{"start_ms": 14000, "end_ms": 30000}],
    platform="youtube",
)
candidates = lib.search(theme="dark", aspect="16:9")
catalog, schema, guide = lib.catalog(candidates, video), hm.placement_schema(candidates), hm.placement_guide()
# ... one call to your model with the video's facts, catalog, schema and guide returns `reply` ...
report = hm.check_placements(reply["placements"], video, lib)
for problem in report.errors:  # each says what to change, for one repair call
    print(problem)
clip = hm.render(lib.get(report.placements[0].asset), report.placements[0].props, fps=32)  # needs Node
print(clip.layers, clip.poster)
```

[examples/quickstart.py](examples/quickstart.py) runs the same path end to end without Node or a model.
The command line does the same from a shell:

```bash
hone-motif list --kind transition --theme warm      # the catalogue as a table (or --json)
hone-motif show name-title-clean-bar                # metadata, props schema, placement rules
hone-motif check-placements reply.json --video video.json
hone-motif render name-title-clean-bar --theme pop --out ./out
hone-motif gallery --render-missing                 # every asset in every theme, in ~/.cache/hone-motif/gallery
hone-motif cache prune --older-than 30d             # renders and Node copies not used for 30 days
```

Search, checks and the gallery page work from the package alone. Rendering needs Node 22.18 or newer;
on first use hone-motif installs the library's packages (Remotion) into its cache, which needs the
network once. Renders go to `HONE_MOTIF_CACHE` (default `~/.cache/hone-motif`) and are reused by every
project on the machine.

## Your own assets

```bash
hone-motif init ./my-assets                 # a copy of the library: shared code, fonts, scripts, starters
cd my-assets && npm ci                      # the library's packages (Remotion), once
# write your assets in assets/<id>/: composition.tsx, schema.ts, asset.json (design §11)
npm run export && npm run check             # props schemas and the registry; types and authoring rules
hone-motif --library . check                # every asset.json against the model and the vocabulary
npm run stills -- ./stills <id>             # look at every theme and aspect before you commit
hone-motif --library . render <id> --out ./out
```

In Python, pass the folder: `hm.Library("my-assets")`. The authoring rules (deterministic, whole-word
right-to-left text, text that fits, no platform logos, OFL fonts) are in
[design/current.md §11](design/current.md); the starter assets follow them.

## Platforms

Linux and macOS. The code paths are portable, but no Windows machine runs the test suite yet.

## Rendering and Remotion's licence

The assets are [Remotion](https://www.remotion.dev) compositions. hone-motif itself is Apache-2.0, but
rendering needs Remotion, which has its own licence: it is free for individuals, for-profit companies
with up to three employees, and non-profits; larger companies need a Remotion Company License. The
terms change slightly in Remotion 5.0. Searching the catalogue, checking props and placements, and
reading cached renders do not use Remotion; rendering goes through a renderer port, so another renderer
can be added.

## How this is being built

Specified by a human; designed and built by AI against a written design and tests; every decision is
reviewed by a human. The design history is in [design/changes/](design/changes/) and
[design/decisions.md](design/decisions.md); the evidence behind the choices is in
[design/history/0000-research.md](design/history/0000-research.md).

## License

Apache-2.0. Fonts in the library are under the SIL Open Font License; rendering needs Remotion under its
own licence (above).
