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
hours = report.total_s / 3600
print(f"Estimated write time: {report.total_s:.3f} s ({hours:.6f} h)")
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
    hours = layer.beam_on_s / 3600
    print(f"{layer.config_name}: {layer.beam_on_s:.3f} s ({hours:.6f} h)")
total_hours = report.total_s / 3600
print(f"Total: {report.total_s:.3f} s ({total_hours:.6f} h)")
```

Names are report labels; `LayerSpec(layer, datatype)` selects the GDS polygons.
Overlapping polygon instances count separately because each is written.

## GPU acceleration (optional)

CPU needs no GPU or compiler. NVIDIA users need a compatible GPU and driver,
the CUDA Toolkit with `nvcc`, and a host C++ compiler such as `g++`.

On WSL, install the NVIDIA display driver on Windows and install only the CUDA
Toolkit inside WSL. Do not install a Linux NVIDIA display driver in WSL. See
the [NVIDIA CUDA on WSL guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html).

<details>
<summary>First-time CUDA setup</summary>

```bash
ebeamtime-diagnostics
ebeamtime-prepare-cuda --json
ebeamtime-diagnostics
```

</details>

The preparation command detects the toolchain and GPU, compiles the packaged
kernel, verifies a known geometry, and stores the result in the user cache.
Run it once per Python, toolkit, GPU architecture, or package-source change.

<details>
<summary>Force CUDA from Python</summary>

```python
config = EstimateConfig(
    gds_path=gds_path,            # GDSII file to analyse.
    exposures=exposures,          # Exposure layers to include.
    backend="cuda",               # Force the NVIDIA CUDA backend.
    require_gpu=True,             # Fail clearly instead of using CPU.
)
```

</details>

<details>
<summary>Force CUDA from the command line</summary>

```bash
ebeamtime /absolute/path/to/device.gds \
  --exposure 1:0:700:1 \
  --backend cuda \
  --require-gpu
```

</details>

<details>
<summary>Allow automatic CPU/GPU selection</summary>

```python
config = EstimateConfig(
    gds_path=gds_path,            # GDSII file to analyse.
    exposures=exposures,          # Exposure layers to include.
    backend="auto",               # Use a prepared GPU when worthwhile.
)
```

</details>

`auto` does not perform first-time compilation. It uses a prepared GPU backend
for at least 4,096 polygons by default and otherwise uses CPU. Prepared CUDA
libraries are normally cached under `~/.cache/ebeamtime/native/`.

Apple Metal is available experimentally on Apple Silicon with the Xcode
command-line tools.

Licensed under GPL-3.0-only. Development instructions are in
[CONTRIBUTING.md](https://github.com/SandboChang/ebeamtime/blob/main/CONTRIBUTING.md).
