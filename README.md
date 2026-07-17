# ebeamtime

`ebeamtime` estimates electron-beam lithography write time from the polygon
area, exposure dose, and beam current in a GDSII file.

## Install

```bash
python -m pip install ebeamtime
```

## One layer

An absolute GDS path is preferred. A relative path such as
`Path("layouts/device.gds")` starts at the directory where you run Python.

```python
from pathlib import Path

from ebeamtime import EbeamLayerExposure, EstimateConfig, LayerSpec
from ebeamtime import estimate_gds_write_time

# Preferred: an absolute path to the input GDS file.
gds_path = Path("/absolute/path/to/device.gds")

junction = EbeamLayerExposure(
    config_name="junction",       # Label shown in the report.
    layer=LayerSpec(1, 0),        # GDS layer 1, datatype 0.
    dose_uC_cm2=700,              # Dose (µC/cm²).
    beam_current_nA=1,            # Beam current (nA).
)

config = EstimateConfig(
    gds_path=gds_path,            # GDSII file to analyse.
    exposures=(junction,),        # Keep the comma: this is a one-item tuple.
)

report = estimate_gds_write_time(config).report
print(f"Estimated write time: {report.total_s:.3f} s")
```

## Multiple layers

Using the same imports and `gds_path`, add one exposure per layer/datatype pair:

```python
exposures = (
    EbeamLayerExposure(
        config_name="junction",   # Label shown in the report.
        layer=LayerSpec(1, 0),    # Junction GDS layer and datatype.
        dose_uC_cm2=700,          # Dose (µC/cm²).
        beam_current_nA=1,        # Beam current (nA).
    ),
    EbeamLayerExposure(
        config_name="undercut",   # Label shown in the report.
        layer=LayerSpec(2, 0),    # Undercut GDS layer and datatype.
        dose_uC_cm2=100,          # Dose (µC/cm²).
        beam_current_nA=1,        # Beam current (nA).
    ),
)

config = EstimateConfig(
    gds_path=gds_path,            # GDSII file to analyse.
    exposures=exposures,          # Every layer to include in the estimate.
)

report = estimate_gds_write_time(config).report
for layer in report.layers:
    print(f"{layer.config_name}: {layer.beam_on_s:.3f} s")
print(f"Total: {report.total_s:.3f} s")
```

Names are report labels; `LayerSpec(layer, datatype)` selects the GDS polygons.
Overlapping polygon instances count separately because each is written.

CUDA and Apple Metal are optional; CPU needs no GPU or compiler. Run
`ebeamtime-diagnostics` to inspect the available backend.

Licensed under GPL-3.0-only. Development instructions are in
[CONTRIBUTING.md](https://github.com/SandboChang/ebeamtime/blob/main/CONTRIBUTING.md).
