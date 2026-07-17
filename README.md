# ebeamtime

`ebeamtime` estimates analytical electron-beam lithography write time from GDSII
polygon area, exposure dose, beam current, and optional stage/write-field
metadata. It preserves raw polygon-instance area semantics: overlapping source
polygons are counted separately because each is written separately.

```bash
python -m pip install ebeamtime
ebeamtime layout.gds --exposure 1:0:100:1 --backend cpu
```

For local development before the packages are released, install sibling
checkouts explicitly without putting local paths in package metadata:

```bash
python -m pip install -e ../gdsdiff -e ".[test]"
```

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

The project is pre-release software and is licensed under GPL-3.0-only.
