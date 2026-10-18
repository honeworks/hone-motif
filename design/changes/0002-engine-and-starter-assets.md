# 0002: The engine with three starter assets, ready for production (v0.1)

## Status

`accepted (approved by the maintainer 2026-10-18)`. Asked for on 2026-10-18 ("remove any predefined lib
or assets … make it fully production ready"); the open questions were answered the same day: keep the
engine with two or three small assets, keep right-to-left support under neutral names, and treat the
request as the approval of this record.

## Context

Milestones M1–M4 of [0001](0001-initial-design.md) built the engine (asset model, search, checks,
renderer port, cache, CLI, gallery) and 1040 assets. A review on 2026-10-18 found the engine sound but not
ready for production: rendering imports `fcntl` (no Windows), a damaged cache entry is returned as if it
were whole, a file prop may name any file, a timed-out render can leave Chrome running, the Node copies
in the cache are never pruned, a reply that is not a list raises `TypeError`, and nothing checks that
text at its maximum length stays inside its region. The maintainer also decided the library ships no
pre-made catalogue: projects bring their own assets, and the samples and fonts are not tied to one
language.

## Problem

1. 1040 pre-made assets are a catalogue the maintainer does not want to ship or maintain; the engine is
   the product.
2. The library, its samples, fonts, digits and documents are written around one language. The
   right-to-left support should stay, described and tested in neutral terms.
3. The defects above stand between the engine and production use.

## Options

1. **Leave it as it is.** Rejected: the maintainer asked for the catalogue to go, and the defects remain.
2. **Delete `library/` entirely** (Python only). Rejected: nothing could render or be tested end to end
   until a new library is written, and authors would have no working starting point.
3. **Keep the engine and a minimal starter library** (chosen): three small, neutral assets that exercise
   each output path (an overlay with alpha, a transition with matte and fx, an opaque scene), every
   theme and aspect; a command that copies the library as a starting point for a project's own.

## Decision

### The library

- `library/assets/` holds three starter assets, written new, each in all five themes and in 16:9, 9:16
  and 1:1:
  - `name-title-clean-bar` (lower-thirds, overlay): a name and a role on a bar, in any anchor;
  - `matte-wipe-soft-edge` (transitions): a soft diagonal wipe with a thin accent line on its edge;
  - `big-title-clean-rise` (titles-and-chapters, scene): a title and subtitle rising on the theme's
    backdrop.
- `library/shared/` keeps only what they and the registry use: `frame.tsx`, `fonts.tsx`, `layout.ts`,
  `motion.ts`, `schema.ts`, `text.tsx`, `themes.ts`, `color.ts`. Everything else goes.
- The categories, subcategories, kinds, themes and moods (§3, §4) stay as the vocabulary authors write
  against; the target counts go. Nothing was released, so the ids of M1–M4 bind no one
  (`aliases.json` is already empty).
- The test suite keeps a metadata-only fixture library (`tests/fixtures/assets/`, no compositions) that
  covers every placement rule; it is never shipped.

### Right-to-left, in neutral terms

- Fonts: the three fonts tied to that language are removed; Noto Naskh Arabic sets Arabic-script text in
  every theme. The theme font roles for right-to-left text become `rtl` and `rtlDisplay`.
- The right-to-left sample is `samples.rtl`: every asset that sets a right-to-left script carries one,
  rendered for its golden poster. Its check code is `no-rtl-sample`.
- Locale digit helpers are removed; digits are written as given.
- No document, test or sample refers to one language or country; examples use neutral Arabic text.

### Production fixes

| Defect | Fix |
|---|---|
| `fcntl` only | `file_lock` uses `fcntl.flock` on POSIX and `msvcrt.locking` on Windows |
| damaged cache entry returned | `Cache.read` treats an entry whose `render.json` does not parse, or whose files are missing, as absent; `create` replaces it under the key's lock |
| any file as a file prop | an `image` input must be a `.png`, `.jpg`, `.jpeg` or `.webp` file |
| Chrome left after a timeout | the renderer runs in its own process group (POSIX) and the whole group is killed on a timeout |
| Node copies never pruned | `Cache.prune` (and `hone-motif cache prune`) also removes `node/` copies not used within `older_than`; each use touches the copy's ready marker |
| `check_placements(None)` raises | a reply that is not a list gives one `bad-placement` error |
| text overflow unchecked | acceptance case 17 (below) |

### Authoring outside the package

`hone-motif init <dir>` copies the installed library (sources, fonts, scripts, the starter assets) into
`<dir>` so a project writes its own assets there, then uses `hone-motif --library <dir> …` or
`hm.Library("<dir>")`. It refuses a folder that exists and is not empty.

```bash
hone-motif init ./my-assets
cd my-assets && npm ci && npm run export && npm run check
hone-motif --library ./my-assets check
hone-motif --library ./my-assets render name-title-clean-bar --theme warm --out ./out
```

### Acceptance cases

- Case 14 becomes: every asset that declares a right-to-left script renders its `rtl` sample as whole
  words (its golden hash), never as separated letters.
- Case 17 (new, render suite): at the maximum length of every text field, in every aspect it supports,
  an overlay draws nothing outside its region box (with a margin of 1% of the frame) and nothing outside
  the title-safe area (90% of the frame).
- Case 18 (new): `hone-motif init` copies a library that loads and passes `hone-motif check`, and refuses
  a non-empty folder.
- Case 19 (new): a damaged cache entry (unreadable `render.json`, a missing layer) is rendered again.

Tests: `tests/render/test_posters.py` (14, 17), `tests/unit/test_cli.py` and `tests/e2e` (18),
`tests/unit/test_cache.py` (19, the lock and pruning), `tests/unit/test_render.py` (image inputs),
`tests/integration/test_remotion_adapter.py` (the process group), `tests/unit/test_placement.py` (a reply
that is not a list).

## Consequences

- Better: a small engine with a working starting library; every defect of the review fixed; nothing tied
  to one language.
- Costs: consumers who expected the catalogue must write or bring assets; the gallery shows three.
- Windows: the lock and the code paths are portable, but no Windows machine runs the suite yet; rendering
  on Windows is untested and the classifiers say Linux and macOS.

## Migration and compatibility

Nothing was released, so no deprecation period. Stored formats keep `format_version: "1"`: `samples` is
still a map of named props (the right-to-left sample's key is now `rtl`), and `render.json` is unchanged. Render
cache entries of removed assets are never read again; `hone-motif cache prune` removes them by age. M5
(hone-music-video) starts from the starter assets and the project's own.
