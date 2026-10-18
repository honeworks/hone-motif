# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow semantic versioning. Why the
design changed is in [`design/changes/`](design/changes/).

## [Unreleased]

Version 0.1.0 ([0002](design/changes/0002-engine-and-starter-assets.md)).

### Changed

- The library ships three starter assets (`name-title-clean-bar`, `matte-wipe-soft-edge`,
  `big-title-clean-rise`), each in five themes and in 16:9, 9:16 and 1:1, instead of a catalogue;
  projects write their own.
- Right-to-left support in neutral terms: the right-to-left sample is `samples.rtl` (check code
  `no-rtl-sample`), the theme roles are `rtl` and `rtlDisplay`, and every theme sets Arabic-script text in
  Noto Naskh Arabic.
- `hone-motif cache prune` also removes Node copies of the library not used within the given age.
- The package claims Linux and macOS (no Windows machine runs the suite yet); CI runs on both.

### Added

- `hone-motif init <dir>`: copies the library into a new or empty folder to write a project's own assets.
- Design §14 cases 17 (the longest text stays inside its region and the title-safe area, render suite),
  18 (`init`) and 19 (a damaged cache entry is rendered again).
- A metadata-only fixture library for the tests (`tests/fixtures/assets/`, decision D-030).

### Fixed

- The cache lock no longer needs `fcntl`: it takes `msvcrt` on Windows (decision D-029; untested there).
- A cache entry whose `render.json` does not parse, or whose layers or poster are missing, is rendered
  again instead of being returned.
- A render that times out kills its whole process group, Remotion's browser included, and no longer waits
  on pipes the browser holds.
- A file prop must name a `.png`, `.jpg`, `.jpeg` or `.webp` file (its path can come from a model's reply).
- `check_placements` given a reply that is not a list returns one `bad-placement` error instead of raising.

### Removed

- The 1040 assets of milestones M1–M4, the shared helpers only they used, three language-specific fonts
  and the locale digit helpers.

### Added (before 0002)

- Milestone M4 of [0001](design/changes/0001-initial-design.md): 540 new assets, 1040 in all, every
  category at its M4 count of design §3, each in five themes and nearly all in 16:9, 9:16 and 1:1.
- Batch poster stills (`npm run stills`, `poster_stills()`, `hone-motif gallery --stills`; D-027) for
  golden hashes and gallery posters; corner props with any anchor (D-028); cache keys that hold only the
  shared files an asset imports (D-026).
- Milestone M3 of [0001](design/changes/0001-initial-design.md): 300 new assets, 500 in all, every
  category at its M3 count of design §3; 9:16 and 1:1 layouts (288 assets take all three aspect ratios)
  through per-aspect layout frames (D-024), with stills, golden posters and gallery tiles per aspect.
- Loops placed for any length: one rendered cycle repeated by `compose_filter` (D-023).
- Milestone M2 of [0001](design/changes/0001-initial-design.md): 181 new assets, 200 in all, every one in
  the five themes, every category at its M2 count of design §3: intros, outros, end screens, calls to
  action, lower thirds, titles and chapters, text cards, credits, channel branding, 26 transitions, 20
  atmospheric loops, 16 backgrounds, frames and borders, info-graphics, callouts, music visuals and 8
  caption styles.
- Milestone M1 of the initial design ([0001](design/changes/0001-initial-design.md)): the asset model
  (`asset.json`, `Asset`), the vocabulary and five themes, `Library` with `search`, `catalog` and
  `check`, `check_props`, `check_placements` with every rule of design §7.3, `placement_schema` and
  `placement_guide`, the `Renderer` port with `FakeRenderer`, its contract checker and the Remotion
  renderer, the render cache with `render.json`, `compose_filter` for ffmpeg, the `hone-motif` command
  line and the generated gallery.
- The first 19 assets, each in five themes: the 16 prototypes of 2026-10-10 under descriptive ids, and
  three karaoke caption styles (fill sweep, slide and focus).
- Tests for design §14's sixteen guarantees, golden poster hashes for every asset and theme and each
  right-to-left sample (`tests/golden/posters.json`), and the Node library check (`npm run check`).
- Repository created with the design ([0001](design/changes/0001-initial-design.md)).
