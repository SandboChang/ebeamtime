# Agent Notes

This repository is the standalone `ebeamtime` GDSII electron-beam write-time
estimator. Durable implementation belongs under `src/ebeamtime/`; tests belong
under `tests/`.

## Environment

- Use `.venv_wsl/bin/python` for normal imports and runtime development on
  Windows 11 through WSL, and `.venv_wsl_test/bin/python` for every test run.
  Use `.venv_mac/bin/python` on macOS and `.venv/bin/python` on native Linux.
- Keep the CPU path usable without CUDA, Metal, a compiler, or a GPU.
- CUDA and Metal are exposed optional runtime capabilities, not installation
  dependencies. A requested or required unavailable GPU backend must fail
  clearly; `auto` may fall back to CPU.
- Use the exact `uv` version required by `pyproject.toml`. On WSL under
  `/mnt/f`, keep `.venv_wsl` synchronized without test extras, target
  `.venv_wsl_test` with test extras, use `UV_LINK_MODE=copy`, and set
  `TMPDIR=/tmp` for pytest. Do not commit a sibling path source for `gdsdiff`.

## Development Rules

- Work on the current branch unless the user explicitly requests another one.
- Treat root exports, CLI behavior, report schema, units, raw polygon-instance
  area semantics, and stage-field assignment as public contracts.
- Depend on `gdsdiff` only through its documented package-root API.
- Do not commit generated GDS, build products, native binaries, caches, or
  benchmark results.
- Use `.tmp/` for disposable work and ignored `results/` for local evidence.
- Run `python -m pytest`, distribution inspection, and a clean-wheel install
  for packaging changes.
- Compare exact correctness before performance; use a warm-up and at least
  seven measured runs.
