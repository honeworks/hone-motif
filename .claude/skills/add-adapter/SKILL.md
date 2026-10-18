---
name: add-adapter
description: Add an implementation of one of hone-motif's ports, or another optional integration, with its extra, fake, contract test and docs. Use when adding support for a new service, library or data source.
---

# Add an adapter

hone-motif has one port, `Renderer` (`design/current.md` §8, `src/hone_motif/ports.py`), whose default
implementation is the Remotion renderer. A new renderer (Motion Canvas, Revideo, a Python renderer) is an
adapter of that port; it renders only the assets whose sources it understands and says so. A new port,
or a change to one, is a design change: `plan-change` first. For a new port, follow the family pattern:

1. **Where.** Each port is a small `typing.Protocol` owned by hone-motif, in `src/hone_motif/ports.py`. Adapters go in an `adapters` subpackage and are imported lazily.
2. **Optional dependency.** Add an extra in `pyproject.toml`. Import the third-party library only inside
   the adapter module. The core must still import without it: `tests/unit/test_import_boundaries.py`
   (add the library to its blocked list).
3. **Contract.** Every port has a fake and a contract checker in a `hone_motif.testing` subpackage; run
   the checker against the adapter in `tests/contract/`.
4. **Behaviour the port promises.** Write it in `design/current.md` and test it; an adapter that can't
   keep a promise fails clearly instead of pretending.
5. **Tests with recorded data or a real local service**, never a remote one, in the default suite; real
   renders only in `tests/render/` (`render-tests`).
6. **Entry point** when the port is found by name (`hone.<port>` entry points in `pyproject.toml`).
7. `sync-docs`: the install line in `README.md`, a page in `docs/`, an example if it's new.
