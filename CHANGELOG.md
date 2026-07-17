# Changelog

## 0.1.2 - 2026-07-18

- Present one concise, self-contained multiple-layer example with write times
  in seconds and hours.
- Document optional CUDA setup and backend selection in collapsed sections.
- Promote the approved `0.1.2rc3` content without runtime behavior changes.

## 0.1.2rc3 - 2026-07-18

- Streamline the README to one self-contained multiple-layer example.

## 0.1.2rc2 - 2026-07-18

- Make both README usage examples independently copyable by including their
  own imports and absolute GDS path setup.

## 0.1.2rc1 - 2026-07-18

- Add concise first-time CUDA setup and backend-selection instructions.
- Keep GPU code examples collapsed by default on GitHub and PyPI.
- Show example write times in both seconds and hours.

## 0.1.1 - 2026-07-18 (TestPyPI only)

- Replace the project page with concise, commented single-layer and
  multiple-layer examples.
- Clarify absolute and working-directory-relative GDS paths.

## 0.1.0 - 2026-07-18

- Promote the independently verified `0.1.0rc1` package without behavior
  changes.
- Require the stable standalone `gdsdiff>=0.1.0,<0.2` release.
- Use a reproducible `uv.lock` workflow backed only by production dependencies,
  while retaining TestPyPI solely for verification of the `ebeamtime` release
  artifact.

## 0.1.0rc1 - 2026-07-17

- Extracted `ebeamtime` from `scgds` with history and public API compatibility.
- Made standalone `gdsdiff` the sole geometry-extraction dependency.
- Added package metadata, report schema, diagnostics, and qualification gates.
- Added explicit CUDA preparation, side-effect-free capability inspection,
  hardened native cache identity, installed-package smoke tests, and release
  workflows.
- Enforced authoritative GPU requirements and CPU-first small-AUTO selection.
