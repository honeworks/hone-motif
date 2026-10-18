# AGENTS.md: hone-motif

A brief for AI coding tools (Claude Code, Codex, Cursor and others) helping with this repository.
People follow the same rules; they are in [CONTRIBUTING.md](CONTRIBUTING.md).

## What this is

`hone-motif` (import `hone_motif`) is the engine for libraries of code-built video assets (intros,
outros, like & subscribe and other overlays, end screens, chapter cards, lower thirds, transitions,
backgrounds, loops, captions), categorised, tagged, filterable and themed, for any project that cuts a
video. It ships three starter assets. Asset sources are Remotion compositions in `library/`; their
metadata, the search API, the placement checks and the records are Python and do not depend on Remotion
(rendering goes through a renderer port). Media is rendered once into a local cache and never committed. Read
[design/current.md](design/current.md) before changing behaviour; its §14 lists the guarantees the
tests check. Why the design looks like this: [design/changes/](design/changes/) and
[design/decisions.md](design/decisions.md).

**Status:** the design (0001) is `accepted` (2026-10-10) and changed by 0002 (2026-10-18): the engine ships
three starter assets, and projects write their own (`hone-motif init`). M5 (hone-music-video integration)
is next. Build only what the accepted design and change records say.

## Layout

| Path | What |
|---|---|
| `src/hone_motif/asset.py` | the asset model, `asset.json` (design §2) |
| `library.py`, `library_check.py` | loading, aliases, search, catalogue; the library check (§5, §11) |
| `props.py` | `check_props`, scripts of text, default filling (§2.6) |
| `video.py`, `placement.py`, `placement_rules.py`, `prompt.py` | the video's facts, `check_placements` and its rules, the prompt parts (§7) |
| `render.py`, `cache.py`, `remotion.py`, `testing.py` | the `Renderer` port, keys and `render.json`, the cache, the Remotion adapter, the fake (§8) |
| `compose.py` | the ffmpeg filter graph (§8.5) |
| `gallery.py`, `gallery.html`, `cli.py`, `errors.py` | the gallery (§10), the command line (§9), typed errors (§13) |
| `library/` | the Node side: assets, shared TypeScript, fonts, vocabulary, themes, scripts (§5) |
| `tests/` | unit, contract, integration, e2e (design §14), render (`-m render`), golden hashes; `tests/fixtures/assets/` holds metadata-only assets for the placement rules (D-030) |

## Commands

```bash
uv sync --all-extras                 # install everything (dev included)
scripts/check.sh                     # all quality gates: lint, format, types, tests + coverage, build, wheel smoke test
                                     # (plus the library's Node checks once library/package.json exists)
uv run pytest                        # default suite (fast, offline, deterministic)
scripts/gpu-lock.sh uv run pytest -m render   # render tests (Node + Remotion), under the machine-wide lock
```

## Rules

1. **Simple first** ([CONTRIBUTING.md](CONTRIBUTING.md#keep-it-simple)): the plainest code that meets the
   guarantees; complexity ≤ 10, functions ~40 lines, modules ~300 lines.
2. **Design before code:** a new need or change starts as `design/changes/NNNN-<name>.md` with status
   `proposed`; the maintainer accepts it before it is built. Small choices go into `design/decisions.md`.
3. **Remotion stays behind the renderer port:** asset metadata (`asset.json`), search, props and placement
   checks, the cache and the records never import or call Node; only the Remotion renderer adapter does
   (design §8).
4. **Placement is one whole-video call, made by the consumer:** hone-motif gives the catalogue, the reply
   schema and the checks; it never plans one asset at a time (design §7).
5. **Times are integer milliseconds** in metadata, placements and records; frames exist only inside a
   render.
6. **Assets are deterministic and offline:** seeded randomness only, no network at render time, fonts
   under the SIL Open Font License shipped in the library, visuals procedural or CC0 with their source
   recorded; right-to-left text is laid out as whole-word runs, never split per character (design §11).
7. **Media is never committed:** renders, previews and posters live in the cache; tests compare posters by
   perceptual hash (design §12).
8. **The default suite is offline and deterministic**; render tests (`-m render`) need Node and run only
   through `scripts/gpu-lock.sh`.
9. Never commit secrets, generated media, or third-party fonts, images or code without a licence that
   allows it.
10. **Git**: Conventional Commits, small commits; AI-written commits end with a `Co-Authored-By:` line.
    Push a branch and open a pull request only when the user asks ("push", "ship it"). Inside that pull
    request's flow, reviewing it on GitHub and pushing fixes the user asked for need no new request.
    Never push to `main`, tag or publish unless the maintainer asks.
