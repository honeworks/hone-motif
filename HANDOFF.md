# hone-motif: where the work stands (2026-10-19)

Read this first in a new session, then `AGENTS.md` and `design/current.md`.

## Done

- **Published** on 2026-10-19 to https://github.com/honeworks/hone-motif as one squashed commit on `main`.
  The full local history (M1–M4 and the 1040 removed assets) is archived outside the repository as
  `project-design/archive/hone-motif/history-2026-10-19.bundle` in the workspace.
- **Change 0002** (`design/changes/0002-engine-and-starter-assets.md`, accepted 2026-10-18) is built: the M1–M4 catalogue is gone, the library ships three starter assets
  (`name-title-clean-bar`, `matte-wipe-soft-edge`, `big-title-clean-rise`), right-to-left support is
  described and tested in neutral terms, and the production fixes of the 2026-10-18 review are in
  (portable lock, damaged cache entries rebuilt, renders killed as a process group, image-only file
  props, Node copies pruned, a reply that is not a list, `hone-motif init`). Version 0.1.0.
- **Checks:** `scripts/check.sh` green; the render suite (70 tests, about 2 minutes uncached) green,
  including case 17 (the longest text stays in its region and the title-safe area), which fails as it
  should when a panel is widened past its region.
- Decisions D-029 to D-031 were added; D-025 was rewritten in neutral terms.

## Next steps

1. On GitHub: rulesets for `main` and `v*` tags, and the review workflow's secret, as CLAUDE.md
   describes; from now on every change goes through a pull request.
2. M5: integrate with hone-music-video, starting with a change record there; it starts from the starter
   assets and its own library (`hone-motif init`).
3. Windows: run the suite on a Windows machine before claiming it.
4. Publishing (GitHub, PyPI) only when the owner asks.

## Useful commands

```bash
unset VIRTUAL_ENV; scripts/check.sh                        # all gates
uv run hone-motif check                                     # library metadata
cd library && npm run stills -- <dir> <id or prefix*>       # poster stills for authors
scripts/gpu-lock.sh uv run pytest -m render --timeout 3600  # render suite
HONE_MOTIF_UPDATE_GOLDEN=1 ... -k <asset>                   # refresh goldens after an intended change
```
