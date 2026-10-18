---
name: render-tests
description: Run or write render tests (tests/render, marker render) safely on a shared machine - the machine-wide lock, Node and Remotion present, skips with reasons, golden poster hashes. Use before running or changing anything under tests/render, library/, or code that drives a real renderer.
---

# Render tests

Details: CONTRIBUTING.md, "Render tests and `scripts/gpu-lock.sh`". hone-motif calls no AI model; its
heavy tests render assets with Node and Remotion. hone-motif has no render tests yet.

**Run**
- Only through the lock: `scripts/gpu-lock.sh uv run pytest -m render -q`. It waits for the machine-wide
  lock (`$HONE_GPU_LOCK`), so a long render never runs beside another project's model run.
- They need Node and the library's packages (`npm ci` in `library/`); without them they skip with a reason.
- Never delete or rebuild the shared render cache (`HONE_MOTIF_CACHE`) to make a test pass; use a
  temporary cache folder.

**Write**
- Put the test in `tests/render/` with `@pytest.mark.render`.
- Render small: a poster still or a few frames at a small size, not the whole asset at 1080p.
- Compare posters by perceptual hash against `tests/golden/posters.json` within the documented distance
  (design §12), never by exact bytes; check alpha, matte values and the cut frame exactly.
- An intended visual change updates the golden hash in the same commit, with the reason in the body.

**Report** what ran and what was skipped, with reasons, in the PR's "How it was tested".
