# Changelog

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
