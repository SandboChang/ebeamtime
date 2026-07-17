# ebeamtime

`ebeamtime` estimates analytical electron-beam lithography write time from GDSII
polygon area, exposure dose, beam current, and optional stage/write-field
metadata. It preserves raw polygon-instance area semantics: overlapping source
polygons are counted separately because each is written separately.

```bash
python -m pip install ebeamtime
ebeamtime layout.gds --exposure 1:0:100:1 --backend cpu
```

For reproducible local development on WSL, synchronize the committed
production-index lock into the platform-specific environment:

```bash
UV_PROJECT_ENVIRONMENT=.venv_wsl UV_LINK_MODE=copy uv sync --locked --no-dev
UV_PROJECT_ENVIRONMENT=.venv_wsl_test UV_LINK_MODE=copy uv sync --locked --extra test
TMPDIR=/tmp .venv_wsl_test/bin/python -m pytest
```

On WSL, `.venv_wsl` remains the clean runtime environment and all test tooling
lives in `.venv_wsl_test`.

When qualifying coordinated unpublished changes, a sibling `gdsdiff` checkout
may be installed editable for that local test, but it must not be recorded in
package metadata or `uv.lock`.

Python usage:

```python
from ebeamtime import EbeamLayerExposure, EstimateConfig, LayerSpec
from ebeamtime import estimate_gds_write_time

config = EstimateConfig(
    "layout.gds",
    (EbeamLayerExposure("metal", LayerSpec(1, 0), 100, 1),),
    backend="cpu",
)
report = estimate_gds_write_time(config).report
print(report.total_s)
```

CUDA and Apple Metal are runtime options. They require compatible hardware and
the platform toolchain (`nvcc` or Xcode command-line tools); CPU requires
neither. See `ebeamtime-diagnostics` and `docs/semantics.md`.
On-demand builds default to NVIDIA's `-arch=native`, which detects visible GPUs
and emits native SASS without PTX. For cross-machine builds, set
`EBEAMTIME_CUDA_ARCHITECTURES` to comma-separated compute capabilities without
decimals (for example, `89,120`); targets and standard `NVCC_*_FLAGS` become
part of the content-addressed cache key.

Installation and import never compile GPU code. Inspect the shared CUDA
toolchain through `ebeamtime.inspect_cuda_toolchain()`, then build and verify
only the estimator kernel with `ebeamtime.prepare_cuda()` or
`ebeamtime-prepare-cuda --json`. Explicit `backend="cuda"` use retains lazy
preparation. `backend="auto"` does not probe or compile a GPU backend for
workloads below `gpu_min_polygons`. Metal is experimental until validated on
Apple Silicon hardware.

`--project-config` loads and executes Python. Use it only with trusted project
configuration files.

The project is early-stage software and is licensed under GPL-3.0-only.
