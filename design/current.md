# hone-motif: the design (0.1)

**Status:** accepted in [changes/0001](changes/0001-initial-design.md) on 2026-10-10 and changed by
[changes/0002](changes/0002-engine-and-starter-assets.md) on 2026-10-18: the engine (model, search, checks,
renderer port, cache, CLI, gallery) with three starter assets; projects write their own assets. Section
numbers are stable; code comments will refer to them ("design §7.3"). The evidence behind the defaults is
in [history/0000-research.md](history/0000-research.md); smaller choices are in
[decisions.md](decisions.md).

## 1. What it does

hone-motif is the engine for a library of video assets built in code: intros, outros, like & subscribe
and bell overlays, end screens, chapter cards, lower thirds, credits, transitions, backgrounds,
atmospheric loops, captions and more (§3). It ships three starter assets; a project copies the library
(`hone-motif init`) and writes its own. A consumer (hone-music-video first; later hone-frame,
oneshot-studio or anyone):

1. **searches** the catalogue by category, kind, theme, mood, aspect ratio, script and text (§6);
2. gives a model the video's facts, the filtered catalogue, a reply schema and a short guide, and makes
   **one placement call for the whole video** (§7.2);
3. **checks** every returned placement against each asset's props schema and placement rules (§7.3);
4. **renders** each placed asset once, through a renderer port, into a local cache (§8);
5. lays the rendered layers over its own footage, following the recipe of §8.5.

People browse the same catalogue in a generated **gallery** (§10).

### Goals

- A broad visual range: every category in several themes (§4), so a project finds assets that match its
  style and mood, not one house look.
- Every asset is safe to place unattended: typed props with text limits, declared scripts and aspect
  ratios, and placement rules that code checks.
- One placement call per video, never one per asset; the checks are code, not the model's word.
- Metadata, search, checks and records are independent of Remotion; only the renderer adapter knows it.
- Render once: identical inputs never render twice; media is never committed.
- Right-to-left scripts (Arabic, Hebrew) are first-class, not an afterthought.

### Non-goals (0.1)

AI image or video generation, an editing timeline, compositing whole videos, hosting media, AI calls made
by hone-motif itself (the consumer makes the placement call; decision D-010), platform logos and brand
assets, audio (assets are silent; sound effects may come later as their own change).

### Responsibilities

hone-motif owns the asset domain: the asset model, the library and its sources, the catalogue, the props
and placement checks, rendering through its `Renderer` port, the cache and the gallery. Consumers own
their videos: the facts given to `check_placements` (§7.1), the placement call and its model, and the
final composite. hone-motif depends on no other honeworks package.

## 2. The asset model

An asset is one visibly distinct design (decision D-006): a layout and motion of its own, not a colour
change. Its metadata is `asset.json` next to its sources (§5), validated by a pydantic model
(`extra="forbid"`) in Python and by the library check in Node (§11).

### 2.1 Identity and classification

| Field | Meaning |
|---|---|
| `id` | kebab-case, unique, stable forever: `<subcategory>-<two or three words naming the design>` (`like-subscribe-glass-pill`). Never reused; a renamed or removed asset keeps its id as an alias (`replaced_by`) |
| `name` | a short human name ("Like & subscribe, glass pill") |
| `version` | integer, bumped when a change breaks old props or changes the look visibly |
| `category`, `subcategory` | from the taxonomy of §3 |
| `kind` | one of §2.2 |
| `line` | one sentence describing what a viewer sees, for people and planners |
| `tags` | free lowercase kebab-case words (`gold`, `calligraphy`, `glass`, `particles`) |
| `themes` | the themes of §4 the asset is designed and tested for (at least one) |
| `moods` | from the mood vocabulary of §4.2, or `["any"]` |

### 2.2 Kinds

| Kind | What it is | Delivered as (§8.3) |
|---|---|---|
| `overlay` | part of the frame, over the footage (a button, a lower third, a badge) | one layer with alpha |
| `scene` | owns the whole frame for a while (an intro title, an end screen); may let the footage show through | one layer, with alpha when `over_footage` is true |
| `transition` | joins two shots at a cut | two layers: a **matte** (white where the incoming shot shows) and an **fx** layer, plus the cut frame (§2.7) |
| `background` | an opaque full frame (behind a text card, under an intro) | one opaque layer |
| `loop` | an overlay or background whose last frame meets its first, repeatable for any length (a watermark, dust, grain) | one layer, alpha or opaque |
| `caption` | text timed to speech or song across a span (karaoke, word by word) | one layer with alpha; its props carry the timed words (§2.6) |

### 2.3 Time

All times are integer milliseconds; frames exist only inside a render.

| Field | Meaning |
|---|---|
| `duration` | `{"default_ms", "min_ms", "max_ms"}`; equal values mean a fixed length. A loop's `default_ms` is one cycle: it renders once and a placement may last any length from `min_ms` up, the consumer repeating it (decision D-023) |
| `poster_ms` | the moment shown as the asset's still (gallery, golden posters) |
| `fps` | not stored: assets render at the consumer's frame rate (§8.2); motion is written in seconds, not frames |

### 2.4 Frame

| Field | Meaning |
|---|---|
| `aspects` | supported aspect ratios: `16:9` always; `9:16`, `1:1`, `4:5` where the layout works (decision D-012). The asset lays itself out in the aspect's frame, 1920×1080, 1080×1920, 1080×1080 or 1080×1350 (`shared/layout.ts`), scaled to the render's size (decision D-024) |
| `regions` | per aspect ratio, where the asset draws: `"full"` or `{"anchor": "bottom-left", "box": [x, y, w, h]}` as fractions of the frame; for an asset with a `corner` prop (any anchor: corners, `top-center`, `center-left`, …), the box is for the default anchor and moves with it: mirrored to the opposite edge, centred for `center`, and 5% from the edge when it leaves the centre |
| `over_footage` | for scenes: true when the footage shows through (an end screen over dimmed footage) |

### 2.5 Placement rules

The rules a planner reads and `check_placements` enforces (§7.3).

| Field | Meaning |
|---|---|
| `slots` | where it belongs: `opening`, `closing`, `end-screen`, `section-start`, `cut` (transitions), `anywhere`, `whole-video` (loops, captions) |
| `when` | one or two sentences of advice for the planner ("the first instrumental gap after 30–60 s") |
| `window` | optional: `{"from": "start" \| "end", "earliest_ms", "latest_ms"}`: where the start may fall, measured from the video's start or end |
| `ends_with_video` | true for end screens: the placement must end exactly at the video's end |
| `min_video_ms` | the shortest video it may appear in (an end screen needs 25 000 ms) |
| `repeat` | `{"max_per_video", "max_per_section", "min_gap_ms"}`, each optional |
| `quiet_only` | true when it must not overlap the consumer's busy spans (sung lines, speech) |
| `clear_frame` | true when no overlay or loop may show while it does (end screens) |
| `platforms` | platform features it is made for (`["youtube"]` for end screens); empty for generic assets |

### 2.6 Text, scripts and props

| Field | Meaning |
|---|---|
| `props_schema` | the file `props.schema.json`: JSON Schema (2020-12) exported from the asset's zod schema (decision D-002); text props carry `maxLength` |
| `props` | default props: a complete, valid example, used for the poster and the gallery |
| `text_fields` | every text prop: `{"prop": "titleEn", "max_chars": 32, "scripts": ["Latn"], "role": "title"}`; array items as `"lines[].name"`. `max_chars` equals the schema's `maxLength` |
| `scripts` | ISO 15924 codes the asset can set (`Latn`, `Arab`, `Hebr`, `Cyrl`, `Deva`, …); right-to-left follows from the script |
| `languages` | BCP 47 tags of a fixed bilingual layout (`["en", "ar"]`), or empty when any language of its scripts works |
| `inputs` | file props (an image for a "next video" teaser): `{"prop": "thumbnail", "type": "image"}` |
| `samples` | named example props beside `props`; `rtl` is the right-to-left sample every asset that sets `Arab` or `Hebr` text carries, rendered for its golden poster (§14 case 14) |

Every asset also accepts `theme` (one of its `themes`) and an optional `accent` colour. A caption asset's
props carry the timed text: `lines: [{"start_ms", "end_ms", "text", "words": [{"text", "start_ms",
"end_ms"}]}]`, relative to the placement's start.

### 2.7 Transitions

| Field | Meaning |
|---|---|
| `transition.cut_ms` | the moment, from the asset's start, at which the consumer's cut lies (the middle of the prototypes' 96 frames) |
| `transition.fx_blend` | how the fx layer is laid: `normal` (alpha) or `screen` (opaque on black, for light leaks) |

The consumer lays the outgoing shot, then the incoming shot through the matte, then the fx layer (§8.5).

### 2.8 Licence and provenance

| Field | Meaning |
|---|---|
| `licence` | the asset's code licence (`Apache-2.0`) |
| `fonts` | font families used; each is in the font registry (`library/fonts/fonts.json`) with its licence (SIL OFL 1.1 only) and source |
| `media` | any non-procedural media (a texture): `{"file", "licence": "CC0-1.0", "source": "<url>"}`; empty for procedural assets |
| `origin` | where the design came from (`"prototype asset-gallery #1"`, `"new"`) and the date |

### 2.9 Example

The starter lower third (`library/assets/name-title-clean-bar/asset.json`, shortened):

```json
{"format_version": "1", "id": "name-title-clean-bar", "name": "Name and title, clean bar",
 "version": 1, "category": "lower-thirds", "subcategory": "name-title", "kind": "overlay",
 "line": "A panel opens from its edge with an accent bar on the reading side; the name and then the role rise into it, and it closes the way it came.",
 "tags": ["panel", "bar", "clean", "name", "broadcast"], "themes": ["cinematic", "dark", "documentary", "warm", "pop"],
 "moods": ["any"], "duration": {"default_ms": 6000, "min_ms": 4000, "max_ms": 12000}, "poster_ms": 3000,
 "aspects": ["16:9", "9:16", "1:1"],
 "regions": {"16:9": {"anchor": "bottom-left", "box": [0.05, 0.75, 0.4, 0.2]}, "9:16": {"...": "..."}, "1:1": {"...": "..."}},
 "slots": ["anywhere", "section-start"],
 "when": "The first time a person speaks or appears on screen, a second or two after their shot starts.",
 "repeat": {"max_per_section": 1, "min_gap_ms": 20000}, "quiet_only": false,
 "text_fields": [{"prop": "name", "max_chars": 28, "scripts": ["Latn", "Arab"], "role": "name"},
                 {"prop": "role", "max_chars": 40, "scripts": ["Latn", "Arab"], "role": "title"}],
 "scripts": ["Latn", "Arab"],
 "props": {"theme": "cinematic", "name": "Alex Morgan", "role": "Composer and producer", "corner": "bottom-left"},
 "samples": {"rtl": {"theme": "cinematic", "name": "ليلى حسن", "role": "ملحنة ومنتجة موسيقية", "corner": "bottom-left"}},
 "licence": "Apache-2.0", "fonts": ["Bebas Neue", "Inter", "Montserrat", "Noto Naskh Arabic", "Playfair Display"],
 "origin": {"from": "new (0002 starter)", "date": "2026-10-18"}}
```

## 3. Categories

Seventeen categories, each with its subcategories and the kinds its assets may be. They are the vocabulary
authors write against (`library/vocabulary.json`); adding one is a design change. The shipped library has
three starter assets (changes/0002), marked ★.

| # | Category | Subcategories | Kinds |
|---|---|---|---|
| 1 | `intros` | title-reveal, logo-sting, cold-open, countdown | scene, overlay |
| 2 | `outros` | thank-you, signature, fade-out, next-up | scene |
| 3 | `end-screens` | two-videos-subscribe, video-subscribe, four-elements, end-card | scene |
| 4 | `calls-to-action` | like-subscribe, bell, comment, share, support | overlay |
| 5 | `lower-thirds` | name-title ★, now-playing, location-date, source, speaker | overlay |
| 6 | `titles-and-chapters` | chapter-card, section-label, numbered, big-title ★ | scene, overlay |
| 7 | `text-cards` | epigraph, quote, verse, statement, fact | scene |
| 8 | `credits` | roll, card, side-panel | overlay, scene |
| 9 | `channel-branding` | watermark, badge, social-handles | overlay, loop |
| 10 | `transitions` | matte-wipe ★, ink-and-paint, light-leak, film-burn, dissolve-and-dip, shape-wipe, glitch, whip-and-zoom | transition |
| 11 | `atmospherics` | particles, light, texture, weather | loop |
| 12 | `backgrounds` | gradient, abstract-motion, pattern, paper, studio | background, loop |
| 13 | `frames-and-borders` | letterbox, vignette, ornamental, film-frame, picture-frame | overlay, loop |
| 14 | `info-graphics` | counter, timeline, list, progress, map-callout | overlay, scene |
| 15 | `callouts` | arrow, highlight, circle, pointer, label | overlay |
| 16 | `music-visuals` | equaliser, waveform, beat-pulse, track-info | overlay, loop |
| 17 | `captions` | karaoke, word-by-word, line, bilingual, short-pages | caption |

## 4. Themes and moods

### 4.1 Themes

A theme is a set of tokens in `library/shared/themes.ts` (exported to `library/themes.json` for Python):
a palette (background, ink, accent, second accent, muted), fonts per role and script, a motion character
(pace and easing) and texture (grain, glow). An asset lists the themes it supports and takes `theme` as a
prop; "supports" means its poster in that theme is reviewed and has a golden hash (§12).

| Theme | Look | Typical moods |
|---|---|---|
| `cinematic` (cinematic and epic) | deep black, gold and ember; serif type (Playfair Display, EB Garamond); slow eases; light rays, dust, embers | epic, triumphant, tragic |
| `dark` (dark and moody) | desaturated, cold steel and teal, a crimson accent; condensed sans; slow fades, heavy grain | tense, mysterious, melancholic |
| `documentary` (documentary and clean) | white and neutral greys, one accent; Inter and plain sans; precise linear motion, no effects | calm, informative, neutral |
| `warm` (warm and romantic) | cream, rose, peach and soft gold; rounded serif; soft glows and light leaks | romantic, tender, nostalgic, hopeful |
| `pop` (energetic and pop) | saturated colours; bold display sans (Bebas Neue, Montserrat); springs, bounces, shapes | playful, energetic, upbeat |

### 4.2 Moods

A closed vocabulary (`library/vocabulary.json`): `epic`, `triumphant`, `tragic`, `melancholic`,
`reflective`, `mysterious`, `mystic`, `tense`, `violent`, `romantic`, `tender`, `nostalgic`, `hopeful`,
`calm`, `playful`, `energetic`, `upbeat`, `informative`, `neutral`, and `any`. Unknown moods are rejected.

## 5. The library layout

```text
library/                         the Node project (Remotion); shipped in the wheel as hone_motif/library
  package.json  package-lock.json  tsconfig.json
  vocabulary.json                categories, subcategories, kinds, slots, moods (§3, §4.2)
  themes.json                    exported theme tokens (§4.1)
  asset.schema.json              JSON Schema of asset.json (exported from the pydantic model)
  fonts/  fonts.json             OFL fonts and their registry (§2.8)
  shared/                        themes.ts, text.tsx (RTL-safe text), random.ts, layers.tsx, safe.ts, …
  assets/<id>/
    composition.tsx              the component and its calculateMetadata (duration from props)
    schema.ts                    the zod props schema with text limits and defaults
    props.schema.json            exported from schema.ts, committed (decision D-002)
    asset.json                   the metadata of §2
  src/Root.tsx                   registers every asset (generated from the folders)
  scripts/                       export.ts (derived files), check.ts (the Node check), stills.ts (posters
                                 for authors), render.ts (the renderer's entry, §8.2)
src/hone_motif/                  the Python package (§6)
tests/golden/posters.json        golden poster hashes per asset, theme and aspect (`warm@9:16`), and `rtl` sample (§12)
tests/fixtures/assets/           metadata-only assets covering every placement rule, for the tests (decision D-030)
```

Committed: sources, metadata, exported schemas, fonts and golden hashes. Never committed: rendered media,
previews, posters, `node_modules/` (`.gitignore`). The wheel ships `library/` (sources and fonts, a few
megabytes), so search and checks work from the wheel alone and the renderer can build from it.

**A project's own library.** `hone-motif init <dir>` copies the installed library (the layout above, the
starter assets included) into a new or empty folder with a `.gitignore` (decision D-031). The project
writes its assets there, runs `npm ci`, `npm run export` and `npm run check`, and passes the folder to
`hm.Library(<dir>)` or `hone-motif --library <dir>`. The renderer copies and installs that folder like the
shipped one (§8.2).

**The cache** (`HONE_MOTIF_CACHE`, default `~/.cache/hone-motif`; decision D-004):

```text
<cache>/
  node/<library hash>/           the library copied with node_modules installed (npm ci), once per version;
                                 node_modules/.hone-motif-ready is touched on every use (for pruning)
  renders/<key[:2]>/<key>/       main.webm | matte.mp4 + fx.webm, poster.jpg, render.json (§8.4)
  gallery/                       the generated gallery (§10)
```

## 6. Python API

```python
import hone_motif as hm

lib = hm.Library()                       # the library in the wheel; hm.Library(path) for a checkout
found = lib.search(kind="overlay", category="calls-to-action", theme="cinematic", mood="tragic",
                   aspect="16:9", script="Arab", text="subscribe")       # -> list[Asset], stable order
asset = lib.get("like-subscribe-glass-pill")                             # UnknownAssetError if missing
asset.props_schema                                                       # JSON Schema (dict)
problems = hm.check_props(asset, {"subscribeLabel": "Subscribe"})        # -> list[Problem]

video = hm.VideoInfo(duration_ms=214380, aspect="16:9", fps=32, cuts=[6210, 12040],
                     sections=[...], busy=[...], scripts=["Arab", "Latn"], platform="youtube")
catalog = lib.catalog(found, video)      # compact JSON for the prompt (§7.2)
schema = hm.placement_schema(found)      # JSON Schema of the reply; asset ids limited to `found`
guide = hm.placement_guide()             # the rules of §7.2 as short Markdown for the prompt

report = hm.check_placements(reply["placements"], video, lib)   # -> PlacementReport
report.errors, report.warnings, report.placements               # placements: defaults filled, durations set

clip = hm.render(asset, props, fps=32, aspect="16:9", duration_ms=6000)  # -> Rendered (cached)
clip.layers        # {"main": Path} or {"matte": Path, "fx": Path}
clip.cut_frame     # transitions only; clip.blend, clip.frames, clip.size, clip.render_json
```

- `Asset`, `VideoInfo`, `Placement`, `PlacementReport`, `Problem` and `Rendered` are frozen pydantic
  models; times are `int` milliseconds and floats are rejected.
- `Problem`: `code` (stable, e.g. `text-too-long`), `index` (placement number), `asset`, `field`,
  `message` (what is wrong, by how much, what to do).
- Errors (all `HoneMotifError`): `UnknownAssetError`, `InvalidAssetError` (the library does not load:
  an `asset.json`, a repeated id, a missing file; carries `problems`), `InvalidPropsError` (render with
  props that fail `check_props`), `InvalidRenderError` (an aspect ratio, size, frame rate or duration
  the asset does not take), `RendererUnavailableError` (Node, npm or the library's packages missing;
  says how to install), `RenderError` (the renderer failed; carries its log).
- `render(..., renderer=None, cache=None)`: the default renderer is the Remotion one (§8.2), the default
  cache §5; both can be passed in.
- Also public: `Section` and `Span` (parts of `VideoInfo`), `Cache` and `default_cache_root()` (§8.4),
  `build_gallery()` (§10), `compose_filter()` with `ComposeLayer` and `FilterGraph` (§8.5), and in
  `hone_motif.testing` the `FakeRenderer` and `check_renderer_contract()` (§8.1).

## 7. Placement: how consumers use it

### 7.1 The video's facts (`VideoInfo`)

| Field | Meaning |
|---|---|
| `duration_ms`, `aspect`, `fps` | the video |
| `cuts` | every cut between shots, in ms (transitions must sit on one) |
| `sections` | `[{"id", "kind", "start_ms", "end_ms"}]` (verse, chorus, chapter, …) |
| `busy` | spans where `quiet_only` assets may not go (sung lines, speech) |
| `scripts` | the scripts of the video's text, for search and the script check |
| `platform` | `"youtube"` or null; platform rules apply only when set |

hone-music-video fills it from its `timeline.json` and `shots.json`: cuts from the shot boundaries, busy
spans from the sung lines, sections from the timeline.

### 7.2 The placement call

The consumer makes **one** call for the whole video (never one per asset) with: the video's facts, the
story or style notes it has, `lib.catalog(...)` for a filtered set of candidates (typically 30–150), the
reply schema `placement_schema(...)`, and `placement_guide()`. The reply:

```json
{"placements": [
  {"asset": "big-title-clean-rise", "start_ms": 0, "duration_ms": 6000,
   "props": {"theme": "cinematic", "title": "The Long Road", "subtitle": "A story in three parts"},
   "why": "the song's 12 s intro; sets the epic tone"},
  {"asset": "matte-wipe-soft-edge", "start_ms": 40260, "props": {"theme": "cinematic"},
   "why": "into the first chorus"}]}
```

`duration_ms` is optional (the asset's default); `why` is kept for the people reviewing. The catalogue
gives each candidate its id, name, kind, `line`, themes, moods, slots, `when`, window and repeat rules,
duration range, region, text fields with limits and its props schema without defaults. Errors from §7.3
go back in one repair call (the previous reply and the list of problems), at most twice; that loop is
the consumer's, and `Problem.message` is written for a model to act on.

### 7.3 Checks (`check_placements`)

Errors:

- the asset exists (aliases warn) and supports the video's aspect ratio;
- the props pass the asset's schema (unknown props, types, enums, `maxLength`); text in a script the
  field does not list is rejected;
- `0 <= start_ms` and `start_ms + duration_ms <= duration_ms` of the video; the duration lies in the
  asset's range (a loop's from its `min_ms` up);
- `window`, `ends_with_video` and `min_video_ms` hold (an end screen starts 5–20 s before the end of a
  video at least 25 s long);
- `repeat` limits hold (per video, per section, minimum gap);
- `quiet_only` placements overlap no busy span;
- two overlays or loops whose regions intersect do not overlap in time; nothing but the asset itself
  shows during a `clear_frame` placement;
- a transition's `start_ms + cut_ms` lies on one of the video's cuts (within half a frame).

Warnings: an asset whose themes or moods differ from those of the other placements; an asset with text
that cannot set every script of the video (`VideoInfo.scripts`); more than one transition per 20 s; a
scene over a busy span.

### 7.4 First consumer: hone-music-video's YouTube version

hone-music-video (its own change record, milestone M5) adds a stage after assembly: the catalogue filtered
by its style and aspect ratio, one placement call with the timed lyrics and shot list, `check_placements`
with repairs, a review gate, `render` per placement, and an ffmpeg composite that keeps every cut on its
frame. Captions (decision D-003) are placed the same way, with the timed words as props.

## 8. Rendering

### 8.1 The `Renderer` port

```python
class Renderer(Protocol):
    name: str
    version: str
    def render(self, job: RenderJob, out_dir: Path) -> dict[str, Path]: ...
```

`RenderJob` holds the asset's folder and metadata, the complete props, the `aspect` (its layout frame,
§2.4), `fps`, `width`, `height`, `frames`, the layers wanted and their formats. The renderer writes the layer files and a poster into
`out_dir` and returns them by layer name; hone-motif owns keys, caching and `render.json`. A renderer
that cannot render an asset (sources it does not understand) raises `RenderError` saying so. A fake
renderer (`hone_motif.testing.FakeRenderer`) writes small deterministic files, so the default suite never
needs Node; a contract checker runs against both.

### 8.2 The Remotion renderer (default)

Needs Node 22.18 or newer (it runs the library's TypeScript scripts without a build step; decision D-020).
On first use it copies `library/` into `<cache>/node/<library hash>/` and runs
`npm ci` there (Remotion downloads its headless Chrome then; rendering itself needs no network). Each job
runs `node scripts/render.ts <job.json>`, which bundles once, selects the composition with the props, and
renders the layers with Remotion's renderer at the job's size and frame rate (`gl: "swangle"`, CPU,
concurrency from `HONE_MOTIF_RENDER_CONCURRENCY`, default 2). Each run is its own process group (POSIX):
on a timeout (an hour by default) the whole group, the browser included, is killed (decision D-029).
Remotion is pinned to an exact version
(4.0.534, the prototypes'); moving to Remotion 5.0 is a change record, because its licence terms change
(decision D-009).

Remotion's licence applies to whoever renders: free for individuals, for-profit companies with up to three
employees and non-profits; larger companies need a Remotion Company License. hone-motif says this in its
README and in `RendererUnavailableError`'s install message.

### 8.3 Outputs per kind

| Kind | Layers | Default format (decision D-005) |
|---|---|---|
| `overlay`, `caption`, alpha `loop` | `main` | WebM, VP9, `yuva420p` (alpha); ProRes 4444 `.mov` when asked (`formats={"main": "prores"}`) |
| `scene` | `main` | WebM VP9 with alpha when `over_footage`, else H.264 MP4 |
| `background`, opaque `loop` | `main` | H.264 MP4, `yuv420p` |
| `transition` | `matte`, `fx` | matte: H.264 greyscale (white = incoming shot); fx: WebM VP9 alpha, or H.264 on black for `fx_blend: screen` |

Every render also writes `poster.jpg` at `poster_ms`. A time becomes a frame by rounding `ms * fps / 1000`
with halves up, in integers: `(ms * fps + 500) // 1000` (Python's `round` would round halves to even).
Frames: that of `duration_ms`; a transition's cut frame: that of `cut_ms`.

### 8.4 The cache and `render.json`

The key is the SHA-256 of canonical JSON of: asset id and version, the hash of the asset's folder, of
the `library/shared/` files its sources import (transitively; decision D-026) and of `library/fonts/`, and of `scripts/render.ts` with `package-lock.json` (decision
D-022), the complete props (defaults filled), fps, size, frames, layers and formats, and the renderer's
name and version. A render goes to a temporary folder next to its entry
and is renamed into place when complete; a lock file per key makes a second process wait for the first
instead of rendering again (`fcntl` on POSIX, `msvcrt` on Windows; decision D-029). An entry whose
`render.json` does not parse, or whose layers or poster are missing, counts as absent and is rendered again.
A file prop (`inputs`, an image) must be a `.png`, `.jpg`, `.jpeg` or `.webp` file: its path may come from
a model's reply. `render.json`:

```json
{"format_version": "1", "key": "9f2c…", "asset": "like-subscribe-glass-pill", "asset_version": 1,
 "props": {"...": "..."}, "fps": 32, "width": 1920, "height": 1080, "frames": 192, "duration_ms": 6000,
 "layers": {"main": {"file": "main.webm", "codec": "vp9", "pixel_format": "yuva420p", "bytes": 158636}},
 "cut_frame": null, "blend": "normal", "poster": "poster.jpg",
 "renderer": {"name": "remotion", "version": "4.0.534"},
 "started_at": "2026-10-10T18:20:11.120Z", "render_ms": 21840}
```

hone-motif keeps no span store in 0.1: `render.json` is its record, and a consumer running inside
hone-flow records the call in its run folder (decision D-015).

### 8.5 Compositing recipe (for consumers)

Lay, bottom to top: the footage; `background`; `scene`; `loop`; `overlay`; `caption`. A transition at a
cut: the outgoing shot, the incoming shot masked by the matte, then the fx layer (alpha over, or a screen
blend for `fx_blend: screen`). Overlays are laid at their region's position for the frame size; frame
positions come from absolute milliseconds (`(start_ms * fps + 500) // 1000`, §8.3), never by adding durations.
hone-motif also builds the ffmpeg filter graph for a list of placements and their renders
(`compose_filter`, decision D-011); the consumer runs ffmpeg.

## 9. The command line

Part of the core, with the standard library's argparse (decision D-017).

| Command | Does |
|---|---|
| `hone-motif list [--category --kind --theme --mood --aspect --script]` | the catalogue as a table, or `--json` |
| `hone-motif show <id>` | an asset's metadata, props schema and placement rules |
| `hone-motif search <text> [filters]` | text search over names, lines and tags |
| `hone-motif check [<library>]` | validates every `asset.json` (exit 1 on any error) |
| `hone-motif check-placements <placements.json> --video <video.json>` | the checks of §7.3 |
| `hone-motif render <id> [--props f.json] [--theme --fps --aspect --duration-ms] [--out dir]` | renders one asset (cached) |
| `hone-motif gallery [--out dir] [--render-missing] [--stills] [--size 960x540]` | builds the gallery (§10) |
| `hone-motif init <dir>` | copies the library into a new or empty folder, to write a project's own assets (§5) |
| `hone-motif cache info \| prune [--older-than 30d]` | cache size; prune removes renders started, and Node copies last used, before then |

Every command takes `--library <dir>` (default: the installed library).

## 10. The gallery

A static HTML page generated from the catalogue and the cache (never committed): filters for category,
kind, theme, mood, aspect ratio and script; a tile per asset, theme and aspect ratio with its poster and a
muted preview on hover (960×540 WebM for 16:9, the same scale for the others, e.g. 540×960; alpha shown on a
checkerboard); a detail view with the line, the placement rules,
the text limits, the props schema and default props, the licence and fonts. `--render-missing` renders
the previews not yet in the cache, once; `--stills` gives every tile a poster from the batch stills
(decision D-027) where no preview is rendered. The prototype gallery of 2026-10-10 is its model (history).

## 11. Building assets (rules for authors)

- **Files:** `composition.tsx`, `schema.ts`, `asset.json` in `library/assets/<id>/`; `npm run export`
  writes `props.schema.json`, the registry `src/Root.tsx` and `themes.json`. `hone-motif check` (Python,
  in the default suite) validates every `asset.json` against the model and the vocabulary, checks that
  ids are unique and follow §2.1, that the default props and samples pass the props schema, and that
  every text field's `max_chars` equals its `maxLength`; `npm run check` checks the types, that the
  derived files are up to date and that the defaults pass the zod schemas, and the source rules below
  that can be read from the code (decision D-016).
- **Look at it:** `npm run stills -- <dir> [id or prefix* ...]` writes each asset's poster still in every
  theme, aspect ratio and sample (`<id>--<theme>[@<aspect>].jpg`, half the layout size); every one is
  looked at before an asset is committed.
- **Deterministic:** randomness only from Remotion's seeded `random(seed)`; no `Math.random`, no clock,
  no network; images and fonts only through `staticFile` from the library.
- **Fonts and media:** fonts under the SIL Open Font License 1.1, in `library/fonts/` and the registry;
  visuals procedural, or CC0 media with its source in `asset.json`.
- **Right-to-left:** text is set as whole-word runs with `dir` and isolation (`shared/text.tsx`);
  animations move or reveal whole words, lines, or masks over them, never single characters of a
  joining script; bilingual layouts set each language in its own run.
- **Text fits:** at `max_chars` in every supported aspect ratio the text stays inside its region and the
  title-safe area (90% of the frame), by measured scaling, never by overflow.
- **Platforms:** no YouTube logo, play-button icon or wordmark, and no platform logos for social handles;
  generic buttons in the channel's colours and neutral icons. End screens leave calm areas for the
  platform's own elements inside the practical safe box of history §3.
- **Counting:** a new asset is a new layout or motion, not a recolour; recolours are themes.

## 12. Testing

| Suite | What it checks |
|---|---|
| Unit (default) | the pydantic models, search and filters, `check_props`, every rule of §7.3, cache keys (a golden key for a fixed job), `render.json`, errors and their messages |
| Library (default) | every `asset.json` in `library/` through the Python model: vocabulary, unique ids, defaults valid, text limits consistent, `cut_ms` and `poster_ms` within the duration, fonts in the registry with OFL, media with a CC0 source |
| Contract (default) | `FakeRenderer` and the Remotion renderer's job writer against the `Renderer` contract |
| Integration (default) | the cache with the fake renderer: a render killed halfway leaves no entry; two processes, one render |
| Acceptance (default) | the cases of §14 through the public API and CLI, with the fake renderer |
| Node (`scripts/check.sh`) | TypeScript types, exported schemas and the registry up to date, the library check of §11 |
| Render (`-m render`, through `scripts/gpu-lock.sh`) | per asset, theme and aspect: the poster still (batch stills at half size, decision D-027), compared by 64-bit perceptual hash with `tests/golden/posters.json` (Hamming distance ≤ 6); overlays have alpha; transitions' mattes are black at the first frame and white at the last, and the cut frame is where §8.3 says; the `rtl` sample of every right-to-left asset matches its golden hash; overlays at their longest text stay in their region and the title-safe area (case 17) |

Golden posters are hashes, not images (decision D-007), so no media is committed; an intended visual
change updates the hash in the same commit with the reason.

## 13. Errors and records

Typed errors (§6) with messages that say what to do; nothing is swallowed. `render.json` is the only
record hone-motif writes (§8.4); it holds no secrets (hone-motif needs none). Logging goes to
`logging.getLogger("hone_motif")`.

## 14. Guarantees (acceptance cases)

Each gets a test in `tests/e2e/` that runs offline with the fake renderer, except 13, 14 and 17,
which run in the render suite, and 19, in `tests/unit/test_cache.py`.

1. Every asset in the library loads and validates (complete metadata, known vocabulary, unique ids,
   default props valid against the props schema, text limits consistent); `hone-motif check` exits 0.
2. `search` filters by category, kind, theme, mood, aspect ratio, script and text, in a stable order, with
   only the wheel installed and no Node.
3. `check_props` rejects unknown props, wrong types and text longer than its limit, naming the prop and
   the limit.
4. `check_placements` rejects unknown assets, invalid props, placements outside the video, durations
   outside the asset's range, unsupported aspect ratios and scripts, repeat and gap violations, window
   violations (an end screen outside the last 5–20 s, or in a video shorter than 25 s), `quiet_only`
   assets over busy spans, overlapping overlays in one region, anything over a `clear_frame` asset, and
   transitions off a cut.
5. Placements that pass come back with complete props (defaults filled) and resolved durations.
6. `placement_schema` accepts exactly the candidate ids; `catalog` lists only the candidates, with the
   fields of §7.2.
7. Rendering the same inputs twice renders once; the second call returns the cached result.
8. A render killed halfway leaves no cache entry; two processes rendering the same key produce one render.
9. A transition render delivers a matte and an fx layer, and its cut frame is `(cut_ms * fps + 500) // 1000` (§8.3).
10. Without Node, search and the checks work and `render` raises `RendererUnavailableError` saying how to
    install.
11. The core imports no renderer adapter, optional extra or other honeworks package at import time.
12. `render.json` has `format_version: "1"`, every input of the key and the renderer's version.
13. Every asset's poster in every theme it supports matches its golden hash.
14. Every asset that declares a right-to-left script renders its `rtl` sample as whole words (its golden
    hash), never as separated letters.
15. Metadata, placements and records hold integer milliseconds; a float time is rejected.
16. No rendered media is tracked by git (a test over `git ls-files`), and the default cache lies outside
    the repository.
17. At the maximum length of every text field, in every aspect it supports and in each script it takes,
    an overlay draws nothing outside its region box (at its default anchor and when moved) and nothing
    outside the title-safe area (90% of the frame), within 1% of the frame.
18. `hone-motif init <dir>` copies a library that loads and passes `hone-motif check`, and refuses a
    folder that is not empty.
19. A damaged cache entry (a `render.json` that does not parse, a missing layer or poster) is rendered
    again.

## 15. Known limits (0.1)

- Rendering is CPU-heavy: about 17 s of Chrome per asset at 1080p on the reference machine (history), so
  previews are rendered on demand and cached.
- The shipped library holds three starter assets; a project brings its own (§5).
- Windows: the code paths are portable (decision D-029) but no Windows machine runs the suite; the
  package claims Linux and macOS.
- WebM with VP9 alpha is not read by every editor; ProRes 4444 works almost everywhere but was 100 to
  1200 times larger for the same overlays (history).
- Right-to-left text is correct in Chrome only as whole-word runs; per-character effects are not
  available for joining scripts.
- YouTube publishes no pixel safe area for end screens; the practical box may need updating when YouTube
  changes its player.
- Rendering needs Node, an installed copy of the library's packages and Remotion's licence.
