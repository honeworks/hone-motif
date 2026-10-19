# Implementation decisions

Choices too small for a change record. They are numbered in the order they were made, and code comments
refer to them by number. Entries marked **awaiting owner review** are proposals until the owner confirms.

## Awaiting owner review

| Entry | Question for the owner |
|---|---|
| (none) | |

On 2026-10-10 the owner said "just continue, don't stop for me"; the coordinator accepted every open
question with its recommended option on that instruction (D-003, D-004, D-005, D-006, D-008, D-010,
D-011, D-012).

## D-001: jsonschema is a core dependency  (2026-10-10)

- **Question:** Python must validate props against each asset's JSON Schema without Node.
- **Choice:** `jsonschema` (MIT, pure Python) as a core dependency next to pydantic, added in M1. The
  props schemas are JSON Schema 2020-12, which pydantic cannot validate against directly.
- **Status:** follows the design (0001).

## D-002: props schemas are written once, in zod  (2026-10-10)

- **Choice:** an asset's props are a zod schema in `schema.ts` (the composition uses its types); `npm run
  export` writes `props.schema.json`, which is committed; the library check fails when it is out of date.
- **Why:** one source for the types and the limits; Python reads the exported file and never runs Node.
  The prototype did exactly this with zod 4's `toJSONSchema` (history §1).

## D-003: captions belong in hone-motif  (2026-10-10)

- **Question:** the brief asks whether the 34 caption styles of the second gallery belong here or stay in
  hone-music-video.
- **Choice:** here, as the kind `caption` and the category `captions`. A caption asset's props carry the
  timed lines and words (relative milliseconds); hone-music-video keeps owning the timing and fills them
  from its timeline.
- **Why:** caption styles need the same things as every other asset (themes, OFL fonts, the right-to-left
  rules, Remotion rendering, the gallery, golden posters), and other projects want them; the only
  music-video part is the timing, which stays where it is.
- **Status:** accepted 2026-10-10 by the coordinator on the owner's instruction ("just continue").

## D-004: one render cache per user  (2026-10-10)

- **Choice:** `HONE_MOTIF_CACHE`, default `~/.cache/hone-motif` (the XDG cache folder), shared by all
  projects on the machine, rather than the family's per-project `.hone/` folder.
- **Why:** "render once" pays off across projects: the same end screen with the same props is reused by
  every video of a channel; a render is a pure function of its key, so sharing is safe.
- **Status:** accepted 2026-10-10 by the coordinator on the owner's instruction ("just continue").

## D-005: WebM with alpha by default  (2026-10-10)

- **Choice:** overlays, captions and alpha scenes and loops as WebM VP9 `yuva420p`; ProRes 4444 when a
  caller asks; transitions as an H.264 matte plus a WebM fx layer (H.264 on black for screen blends).
- **Why:** measured: 0.09–1.3 MB for WebM against 14–371 MB for ProRes (history §1). ffmpeg reads VP9
  alpha (with the libvpx decoder); some editors don't, hence ProRes on request.
- **Status:** accepted 2026-10-10 by the coordinator on the owner's instruction ("just continue").

## D-006: an asset is a distinct design; themes are props  (2026-10-10)

- **Choice:** an asset is one layout and motion; a theme changes its palette, fonts, pace and texture
  through the `theme` prop. Target counts (design §3) count designs. A recolour is never a new asset.
- **Why:** the owner wants a broad visual range; counting recolours would inflate the numbers without
  adding choice, and a planner searching 1000 near-duplicates chooses worse.
- **Status:** accepted 2026-10-10 by the coordinator on the owner's instruction ("just continue").

## D-007: golden posters are hashes  (2026-10-10)

- **Choice:** `tests/golden/posters.json` holds a 64-bit perceptual hash per asset and theme; the render
  suite compares within a Hamming distance of 6.
- **Why:** "media is never committed" (the owner's rule) also covers test images; a hash catches a broken
  render without storing pictures, and tolerates encoder noise.

## D-008: render tests under the machine-wide lock  (2026-10-10)

- **Choice:** render tests (`-m render`, `tests/render/`) are deselected by default, not run in CI, and
  run through `scripts/gpu-lock.sh`, the same lock every honeworks project uses for real-model tests.
  hone-motif has no real-model tests, so the family's `gpu` / `ollama` / `comfyui` / `hosted` markers are
  replaced by `render`, and the `real-model-tests` skill by `render-tests`.
- **Why:** a render of many assets takes the machine for minutes to hours, and Chrome may use the GPU; it
  must not run beside another project's model run. CI would need Node, Chrome and long runs for little
  gain while the default suite checks every `asset.json`.
- **Status:** accepted 2026-10-10 by the coordinator on the owner's instruction ("just continue").

## D-009: Remotion is pinned  (2026-10-10)

- **Choice:** exact versions in `library/package.json` (Remotion 4.0.534, as in the prototypes); an
  upgrade within 4.x is a small change with the render suite green; Remotion 5.0 needs a change record
  that re-reads its licence.
- **Why:** renders must not change under a cache key, and the licence terms change in 5.0.

## D-010: no AI calls in hone-motif 0.1  (2026-10-10)

- **Choice:** hone-motif gives the catalogue, the reply schema, the guide and the checks; the consumer
  makes the one placement call with its own model client (hone-music-video through hone-models).
- **Why:** the consumer already has the model, the prompt context (story, timeline, shots) and the review
  gate; hone-motif stays free of model dependencies.
- **Question:** a `place(video, candidates, client)` helper through the family's `TextClient` port
  (optional, hone-models implements it) would save every consumer the same prompt and repair loop. Add it
  later?
- **Answer:** not now. The consumer makes the placement call; a `place()` helper through `TextClient` would be
  its own change record later.
- **Status:** accepted 2026-10-10 by the coordinator on the owner's instruction ("just continue").

## D-011: the compositing recipe and a filter-graph helper  (2026-10-10)

- **Choice:** design §8.5 documents how to lay the layers, and hone-motif also ships a small helper,
  `compose_filter(...)`, that builds the ffmpeg filter graph (inputs, blends, the matte, frame-exact start
  times) for a list of placements and their renders. The consumer still runs ffmpeg.
- **Why:** every consumer would write the same graph, and the blends, the matte and the frame arithmetic
  are easy to get subtly wrong; the helper only returns text, so it adds no dependency.
- **Status:** accepted 2026-10-10 by the coordinator on the owner's instruction ("just continue").

## D-012: 16:9 first  (2026-10-10)

- **Choice:** every asset supports 16:9 (the YouTube version); 9:16 and 1:1 are added where the layout
  works, from M3, each with its own regions and golden posters.
- **Status:** accepted 2026-10-10 by the coordinator on the owner's instruction ("just continue").

## D-013: no platform logos  (2026-10-10)

- **Choice:** no YouTube logo, play-button icon or wordmark, and no platform logos for social handles;
  generic buttons in the channel's colours and neutral icons (history §3).
- **Why:** YouTube's brand rules forbid altering its icon and require a request for broader use; generic
  assets work for every platform.

## D-014: the library ships in the wheel  (2026-10-10)

- **Choice:** `library/` (sources, fonts, metadata; a few megabytes) is packaged as `hone_motif/library`;
  the Remotion renderer installs its Node packages into the cache on first render (`npm ci`).
- **Why:** `pip install hone-motif` is enough to search and check; rendering needs only Node on top.

## D-015: render.json is the record  (2026-10-10)

- **Choice:** no span store in 0.1; each cache entry has `render.json` (design §8.4). A consumer running
  inside hone-flow records the render in its run folder.
- **Why:** hone-motif makes no model calls; its one operation worth recording is a render, and the cache
  entry is where people look for it.

## D-016: the Node check covers what only Node can see  (2026-10-10)

- **Choice:** `npm run check` runs `tsc` and `scripts/check.ts`: the derived files (`props.schema.json`,
  `src/Root.tsx`, `themes.json`) are up to date, the default props and samples pass each zod schema, and
  the sources keep the readable authoring rules (no `Math.random`, clock, network or per-character text
  splitting). Everything about `asset.json` (the model, the vocabulary, ids, text limits, fonts, media)
  is checked once, in Python (`hone-motif check`, run by the default suite), not again against
  `asset.schema.json` in Node.
- **Why:** one implementation of each rule; validating `asset.schema.json` in Node would need a JSON
  Schema library and would repeat the Python check, which already runs in every `scripts/check.sh`.

## D-017: the command line is argparse, with no extra  (2026-10-10)

- **Choice:** `hone-motif` uses the standard library's `argparse` and ships with the core; design §9's
  "extra `cli`" is not needed.
- **Why:** the commands are few and flat; argparse adds no dependency, so an extra would only make users
  type more.

## D-018: render tests render posters small and reuse the user's cache  (2026-10-10)

(Golden posters: replaced by D-027, batch stills. Alpha and matte renders still follow this.)

- **Choice:** the render suite renders each asset and theme at 480×270 and 8 fps (motion is in seconds,
  so the poster moment is the same at any frame rate) through `hm.render`, into the user's cache, so a
  second run reuses the renders. Golden hashes are a DCT perceptual hash of `poster.jpg` (via ffmpeg),
  compared within a Hamming distance of 6; `HONE_MOTIF_UPDATE_GOLDEN=1` rewrites them.
- **Why:** a full-size render of every asset in five themes takes the machine for an hour; the small
  render checks the same composition, alpha, matte and cut frame in minutes. The cache key covers every
  input, so a cached render is the render.

## D-019: gallery previews at 960×540 and 24 fps  (2026-10-10)

- **Choice:** `hone-motif gallery --render-missing` renders each asset and theme with its example props
  at 960×540 and 24 fps (`--size`, `--fps` change it).
- **Why:** a preview is watched in a tile or a dialog, not at 1080p; it is a quarter of the pixels and
  three quarters of the frames of a full render, and text stays legible.

## D-020: Node 22.18 or newer  (2026-10-10)

- **Choice:** the renderer needs Node 22.18 or newer (`library/package.json` engines, `NODE_MIN`), not
  Node 20 as design §8.2 first said.
- **Why:** from 22.18 Node runs TypeScript files directly, so `scripts/render.ts`, `export.ts`,
  `check.ts` and `stills.ts` need no build step or extra tool.

## D-021: frames round halves up  (2026-10-10)

- **Choice:** a time becomes a frame as `(ms * fps + 500) // 1000` (design §8.3), stated in the design
  instead of `round(...)`.
- **Why:** integer arithmetic gives the same answer in Python, TypeScript and ffmpeg filters; Python's
  `round` rounds halves to even, so `round(1500 * 27 / 1000)` is 40 where every other tool says 41.

## D-022: the render pipeline is part of the cache key  (2026-10-10)

- **Choice:** the key also holds `pipeline_hash`: SHA-256 of `library/scripts/render.ts` and
  `library/package-lock.json`. The generated registry `src/Root.tsx` is left out.
- **Why:** a change to how layers are encoded or to a package version changes the output, so it must
  not reuse old renders (the test-auditor found render tests could pass on stale posters). `Root.tsx`
  changes whenever any asset is added, which would throw away every render for nothing; an asset's own
  entry in it follows from its folder, which is hashed.

## D-023: a loop renders one cycle and is placed for any length  (2026-10-10)

- **Choice:** a `loop` asset's duration is one cycle (min = default = max); a placement of it may last
  any length from `min_ms` up, and `compose_filter` repeats the rendered cycle (`-stream_loop -1`) and
  cuts it to the placement. The guide tells the planner so.
- **Why:** design §2.2 says a loop is "repeatable for any length", but the duration check capped it at
  one cycle, so a planner could not place a 4 s dust loop over a whole video (found by the M2 workers).

## D-024: every aspect ratio has a layout frame  (2026-10-10)

- **Choice:** an asset is laid out in a fixed frame per aspect ratio, 1920×1080 (16:9), 1080×1920 (9:16),
  1080×1080 (1:1) and 1080×1350 (4:5), and Remotion scales that frame to the render's size. The renderer
  passes the frame (`aspect`, `base`) with the job; `shared/layout.ts` gives assets `useLayout()` (size,
  aspect, a unit of 1% of the shorter side). Assets that declare more than 16:9 lay out with it instead of
  fixed 1920/1080 coordinates. Stills, golden posters (`<theme>@<aspect>`) and gallery tiles exist per
  aspect; gallery previews keep the 16:9 scale (540×960 for 9:16).
- **Why:** M3 adds 9:16 and 1:1 (D-012); one coordinate system per aspect keeps assets simple and lets
  every existing 16:9 asset stay as it is.

## D-025: one rule for right-to-left text in the library  (2026-10-11, revised 2026-10-18)

- **Choice:** `scriptType` in `library/shared/text.tsx` sets right-to-left text: the theme's
  right-to-left role (`rtlDisplay` for display and title, `rtl` otherwise), at the same size as the
  Latin text, without capitals, tracking or a slant, with a line height of 1.45. Latin text keeps the
  caller's line height. Since 0002 every theme sets Arabic-script text in Noto Naskh Arabic.
- **Why:** helpers written in parallel disagreed on size and line height; the same size is the plain
  choice, since text is fitted to its box by measurement anyway.

## D-026: an asset's key holds only the shared files it imports  (2026-10-11)

- **Choice:** `shared_hash` in the cache key covers the library files outside the asset's folder that its
  `.ts`/`.tsx` sources import, followed transitively, plus `shared/frame.tsx` and `shared/fonts.tsx`
  (every composition goes through them), instead of the whole `library/shared/` folder.
- **Why:** with a thousand assets, each worker's new shared helper changed every key and threw away
  every render; now a render is kept unless something it uses changed.

## D-027: golden posters and gallery posters are batch stills  (2026-10-11)

- **Choice:** `scripts/stills.ts` renders every poster still (each theme, aspect and sample, at half the
  layout size: 960×540 for 16:9) in one browser with several stills at a time; `poster_stills()` in the
  Remotion adapter keeps them in `<cache>/stills/<key>/` (the key: the asset's folder, the shared files
  it imports, the fonts, `render.ts`, the lock and `stills.ts`). The render suite's golden posters
  (§14 cases 13 and 14) hash these stills; alpha, mattes and the negative control still render video.
  `hone-motif gallery --stills` gives every tile a poster this way, previews being rendered where wanted.
- **Why:** rendering a whole video for each poster took about 4 s per poster with a new Chrome each
  time; a thousand assets in five themes and three aspects meant about 13 000 posters, over a working
  day. In one browser a still takes a fraction of a second. The still is the same `--poster`
  composition at the same moment (`poster_ms`), so it shows what the render's poster shows.

## D-028: a corner prop may name any anchor  (2026-10-11)

- **Choice:** an asset's `corner` prop may take any anchor of the vocabulary (`top-left`, `top-center`,
  `center-right`, `center`, …). The region is given for the default anchor; for another one each axis is
  mirrored to the opposite edge, centred for `center`, or placed 5% from the edge when it leaves the
  centre (`placement_rules.region_box`).
- **Why:** M3 assets slide along edges and sit in the middle of a side; mirroring alone gave wrong boxes
  for those (found by the M3 review), so the overlap check missed real collisions. The 5% edge is an
  approximation: assets inset by their own margins (2.8% to 14% of the frame), so a moved box can be off
  by a few per cent.

## D-029: the cache lock is portable  (2026-10-18)

- **Choice:** `file_lock` takes `fcntl.flock` on POSIX and `msvcrt.locking` (retried, since `LK_LOCK`
  gives up after ten seconds) on Windows. Renders run in their own process group on POSIX, so a timeout
  kills Remotion's browser too.
- **Why:** importing `fcntl` made every render fail on Windows (review of 2026-10-18). No Windows machine
  runs the suite yet, so the classifiers name Linux and macOS only (0002).

## D-030: the tests keep their own fixture library  (2026-10-18)

- **Choice:** `tests/fixtures/assets/` holds metadata-only assets (`asset.json` and `props.schema.json`,
  no compositions) that cover every placement rule: an end screen, captions, a loop, a screen-blend
  transition, an image input, overlays in each corner. `tests/conftest.py` builds a library from them and
  the shipped library's vocabulary, themes and fonts. Render tests use the shipped starter assets.
- **Why:** the shipped library has three assets (0002); the rules of §7.3 need more kinds of asset than
  that to be tested, and those need no sources to be checked.

## D-031: `hone-motif init` copies the whole library  (2026-10-18)

- **Choice:** `init` copies the installed library (sources, shared code, fonts, scripts, the starter
  assets, the lock file) into a new or empty folder with a `.gitignore` for `node_modules/` and `build/`,
  and never a project template of its own.
- **Why:** a project's assets need the same registry, shared code and scripts to export, check and
  render; one copy is the simplest way to get all of it, and the starter assets show the authoring rules.


## D-032: brand tokens as built  (2026-10-19)

- **Choice:** change 0003 as proposed, with three details settled in the build. The contrast warning is
  `brand_warnings(props)` and a placement warning, since `check_props` returns only errors. The brand
  posters are named `brand` (and `brand@<aspect>`) like the theme posters, so the stills, the gallery and
  the golden file need no second naming rule. The panel and over-footage tokens follow the brand only
  when the brand's `bg` and the theme's are on the same side of mid-grey (luma 128).
- **Why:** keeps `check_props` a list of reasons to refuse, and one naming rule everywhere; the
  same-side rule is the proposal's "light theme, dark brand keeps the theme's panels" in one test.
