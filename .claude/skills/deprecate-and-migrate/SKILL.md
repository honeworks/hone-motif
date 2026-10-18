---
name: deprecate-and-migrate
description: Change or remove public API, CLI flags or stored formats without breaking users - deprecation warnings, a compatibility period, migrations. Use when a change renames, removes or changes the meaning of anything users or their saved data depend on.
---

# Deprecate and migrate

Users and their saved data outlive any version. Break nothing silently.

**Public API and CLI**
1. Keep the old name working for at least one minor release: it calls the new one and warns with
   `warnings.warn("<old> is deprecated, use <new>; it will be removed in <version>", DeprecationWarning, stacklevel=2)`.
   CLI: the same message on stderr.
2. Docs and examples show only the new form. `CHANGELOG.md`: **Deprecated** now, **Removed** when it goes.
3. Tests: the old form still works and warns; the new form works.

**Asset ids and props** (consumers store placements that name them)
1. An asset id never changes meaning and is never reused. Renaming or removing an asset keeps the old id
   as a deprecated alias (`asset.json` `replaced_by`) for at least one minor release; `get` and
   `check_placements` warn on it.
2. A props change that breaks old placements (a removed or renamed prop, a tighter limit) bumps the
   asset's `version`; old props still validate against the old version or are refused with a message
   that names the change.

**Stored formats** (anything hone-motif writes that a later version reads)
1. New optional data is fine. Removing data or changing its meaning needs a format version and a change
   record (`plan-change`) with a "Migration and compatibility" section.
2. Old data still opens, or is refused with a typed error that says how to migrate. Never guess.
3. Keep a small sample of the old format in the tests and test both reading it and the refusal message.
4. Document the format and its version history in `docs/`.
