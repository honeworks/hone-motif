# 0001: Initial design: a library of code-built video assets, placed by AI (v0.1)

## Status

`accepted 2026-10-10 by the owner ("just continue")`. Proposed the same day; the open questions in
[decisions.md](../decisions.md) were answered with their recommended options. Partly superseded by
[0002](0002-engine-and-starter-assets.md) (2026-10-18): the library ships three starter assets instead of
the milestone counts below, and the M1–M4 assets were removed.

## Context

hone-music-video turns a song into a music video. For the video's YouTube version the owner wants the
pieces every channel video carries: an intro title, a "like and subscribe" nudge, a notification bell, a
now-playing lower third, chapter cards, transitions, credits, an outro, an end screen, and lyric
captions. On 2026-10-10 two prototype galleries were built by hand: 16 assets in Remotion over footage of
a real song, and 34 caption styles in Remotion and two community packages
([history/0000-research.md](../history/0000-research.md)). The owner then decided, in their words and
answers of the same day:

- a **reference library of 500 to 1000+ pre-made, code-built assets**, categorised, tagged, filterable
  and themed, usable by any hone-* project: hone-music-video's YouTube version first (intros, outros, like
  & subscribe and other overlays, end screens, chapter cards, transitions), later hone-frame,
  oneshot-studio and others;
- a **broad visual range**: every category in several themes (cinematic and epic, dark and moody,
  documentary and clean, warm and romantic, energetic and pop), matched to a project's style and mood;
- **sources in the repository; media rendered once into a local cache, never committed**;
- **the AI chooses the assets**: a consumer makes one whole-video placement call that returns
  `[{asset, start_ms, props}]`, validated against each asset's schema;
- **Remotion** as the engine, its licence stated plainly, with the asset metadata, the search API and
  the records independent of Remotion behind a renderer port, so another renderer could be added;
- a new repository, `hone-motif`; local git only until the owner says to publish.

## Problem

Generative pipelines can't make crisp, on-brand graphics (text, buttons, end-screen frames) with image or
video models, and editor templates can't be searched, filled or rendered unattended. Each project draws
its own, in one look, and nothing checks where a model puts them: over a sung line, inside the end-screen
area, with a title too long for its box, or with right-to-left letters torn apart by a per-character animation.

## Options

**Engine.**

1. **Remotion** (React, TypeScript; chosen by the owner). Mature rendering of frames with alpha, typed
   props through zod that export to JSON Schema, `calculateMetadata` for durations from props, a large
   ecosystem; the prototypes were built with it in a day. Its licence is not open source: free for
   individuals, for-profit companies with up to three employees and non-profits; larger companies need a
   Company License; the terms change slightly in Remotion 5.0.
2. **Motion Canvas or Revideo** (TypeScript, MIT). Open licences and a generator-based animation model;
   smaller ecosystems, and Motion Canvas is built for an editor workflow more than headless rendering
   from data. Revideo is a Motion Canvas fork for programmatic rendering, with a smaller community.
3. **Python** (Pillow, Cairo, Manim or MoviePy). One language with the rest of honeworks, but text
   shaping (right-to-left, ligatures), effects and alpha video are far more work, and Manim is built for
   mathematics.

The renderer port (current.md §8.1) keeps option 2 open: metadata, search, checks and the cache do not
depend on the engine.

**Where it lives.**

1. **Inside hone-music-video.** Rejected: the assets are wanted by other projects, and the library will
   be far larger than the music-video code.
2. **Its own repository** (chosen): a library any project depends on, with its own design and tests.

**Media.**

1. **Commit the rendered media.** Rejected: 1000 assets in five themes would be gigabytes in git, and
   every change would add more.
2. **Render once into a local cache** (chosen): sources and metadata in git; a render keyed by its inputs;
   tests compare posters by perceptual hash.

**Placement.** One call per asset (rejected: loses the whole video, many calls), rules applied by people
(rejected: the pipeline runs unattended), or **one whole-video call checked by code** (chosen).

## Decision

Build `hone-motif` as described in [current.md](../current.md):

- the asset model of §2 (identity, kind, themes and moods, time in milliseconds, frame and regions,
  placement rules, text fields and scripts, props schema, transitions with matte, fx and cut, licence
  and provenance) as `asset.json`, read by Python without Node;
- seventeen categories with target counts (§3) and five themes (§4);
- the library layout of §5: Remotion sources in `library/`, shipped in the wheel; a cache outside the
  repository;
- the Python API of §6, the placement catalogue, reply schema, guide and checks of §7;
- the `Renderer` port and the Remotion renderer of §8, the CLI of §9 and the gallery of §10;
- the authoring rules of §11 and the tests of §12.

### Milestones

Each milestone ends with `scripts/check.sh` green, a review (simplicity and tests), an update of
`design/current.md`, and a short demo for the owner (the gallery).

| # | Milestone | Done when |
|---|---|---|
| M1 | The skeleton: the asset model and `asset.json` schema, the vocabulary and themes, `Library`, `search`, `check_props`, `check_placements`, the `Renderer` port with the fake and the Remotion renderer, the cache, the CLI, the generated gallery; the **16 prototypes carried over** as the first assets (cinematic theme), with golden posters | `hone-motif gallery` shows the 16 assets, and a placement reply for a real song checks and renders |
| M2 | **200 assets**: every category of §3 in all five themes; the first captions (the karaoke fill the owner chose) | the M2 column of §3 is met |
| M3 | **500 assets**; 9:16 and 1:1 where the layouts allow; every subcategory in three themes | the M3 column is met |
| M4 | **1000+ assets** | the M4 column is met |
| M5 | **hone-music-video integration**: its YouTube version places, checks and renders assets in one call (a change record in hone-music-video); what it needs from hone-motif (`VideoInfo` fields, the compositing recipe, D-011) is done here | a real song's YouTube version is rendered with intro, overlays, transitions, end screen and captions |

M5 can start after M2: it needs a working library, not the full count.

## Consequences

- Better: assets are searchable, typed, themed and checked before they render; a model places them in one
  call; renders are reused; projects share one library instead of drawing their own.
- Costs: Node 20+ and Remotion on any machine that renders, and Remotion's licence for whoever renders
  (a Company License for companies with more than three employees). Rendering is CPU-heavy (about 17 s of
  Chrome per asset at 1080p on the reference machine); a full gallery takes about a day once.
- Harder: two languages in one repository (Python for the API, TypeScript for the assets) and two sets of
  checks; keeping 1000 assets consistent needs the library check, golden posters and the authoring rules
  of §11. Platform rules (YouTube's end screens) change and must be re-checked.
- Remotion is pinned; moving to 5.0 needs its own change record after reading the new terms.

## Migration and compatibility

A new library; nothing to migrate. `asset.json` and `render.json` start at `format_version: "1"`. The 16
prototype assets get new ids by the rule of current.md §2.1; the prototypes stay outside the repository as
evidence.
