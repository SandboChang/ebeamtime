from __future__ import annotations

import importlib
import importlib.util
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable

from .semantics import Backend


@dataclass(frozen=True, order=True)
class LayerSpec:
    layer: int
    datatype: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.layer, int) or not isinstance(self.datatype, int):
            raise TypeError("layer and datatype must be integers")
        if self.layer < 0 or self.datatype < 0:
            raise ValueError("layer and datatype must be nonnegative")

    @classmethod
    def parse(cls, value: Any) -> "LayerSpec":
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            if "layer" not in value or "datatype" not in value:
                raise ValueError("layer dictionaries must contain 'layer' and 'datatype'")
            return cls(int(value["layer"]), int(value["datatype"]))
        if isinstance(value, tuple | list):
            if len(value) != 2:
                raise ValueError("layer tuple/list must be (layer, datatype)")
            return cls(int(value[0]), int(value[1]))
        parts = str(value).strip().split(":")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"layer spec must have form L:D, got {value!r}")
        return cls(int(parts[0]), int(parts[1]))

    def to_json(self) -> dict[str, int]:
        return {"layer": self.layer, "datatype": self.datatype}

    def selector(self) -> str:
        return f"{self.layer}:{self.datatype}"


@dataclass(frozen=True)
class EbeamLayerExposure:
    config_name: str
    layer: LayerSpec
    dose_uC_cm2: float
    beam_current_nA: float

    def __post_init__(self) -> None:
        if not self.config_name:
            raise ValueError("config_name cannot be empty")
        if not math.isfinite(self.dose_uC_cm2) or self.dose_uC_cm2 <= 0:
            raise ValueError(f"{self.config_name} dose_uC_cm2 must be positive")
        if not math.isfinite(self.beam_current_nA) or self.beam_current_nA <= 0:
            raise ValueError(f"{self.config_name} beam_current_nA must be positive")

    def to_json(self) -> dict[str, object]:
        return {
            "config_name": self.config_name,
            "layer": self.layer.to_json(),
            "dose_uC_cm2": self.dose_uC_cm2,
            "beam_current_nA": self.beam_current_nA,
        }


@dataclass(frozen=True)
class EstimateConfig:
    gds_path: Path | str
    exposures: tuple[EbeamLayerExposure, ...]
    top: str | None = None
    writefield_indicator_layer: LayerSpec | None = None
    writefield_indicator_name: str | None = None
    max_write_field_um: tuple[float, float] | None = None
    stage_speed_mm_s: float | None = None
    stage_settle_s: float = 0.0
    ignore_stage: bool = False
    beam_voltage_kV: float | None = None
    backend: Backend | str = Backend.AUTO
    require_gpu: bool = False
    gpu_min_polygons: int = 4096
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "gds_path", Path(self.gds_path))
        object.__setattr__(self, "backend", Backend.coerce(self.backend))
        exposures = tuple(self.exposures)
        if not exposures:
            raise ValueError("at least one ebeam exposure layer is required")
        if len({item.config_name for item in exposures}) != len(exposures):
            raise ValueError("exposure config names must be unique")
        if len({item.layer for item in exposures}) != len(exposures):
            raise ValueError("exposure layer/datatype pairs must be unique")
        object.__setattr__(self, "exposures", exposures)
        if self.max_write_field_um is not None:
            width, height = self.max_write_field_um
            if not math.isfinite(width) or not math.isfinite(height) or width <= 0 or height <= 0:
                raise ValueError("max_write_field_um values must be positive")
            object.__setattr__(self, "max_write_field_um", (float(width), float(height)))
        if self.stage_speed_mm_s is not None and (not math.isfinite(self.stage_speed_mm_s) or self.stage_speed_mm_s <= 0):
            raise ValueError("stage_speed_mm_s must be positive when supplied")
        if not math.isfinite(self.stage_settle_s) or self.stage_settle_s < 0:
            raise ValueError("stage_settle_s must be nonnegative")
        if self.beam_voltage_kV is not None and (not math.isfinite(self.beam_voltage_kV) or self.beam_voltage_kV <= 0):
            raise ValueError("beam_voltage_kV must be positive when supplied")
        if self.gpu_min_polygons < 0:
            raise ValueError("gpu_min_polygons must be nonnegative")

    @property
    def exposed_layers(self) -> tuple[LayerSpec, ...]:
        return tuple(item.layer for item in self.exposures)

    @property
    def selected_layers(self) -> tuple[LayerSpec, ...]:
        layers = set(self.exposed_layers)
        if self.writefield_indicator_layer is not None:
            layers.add(self.writefield_indicator_layer)
        return tuple(sorted(layers))

    def with_overrides(
        self,
        *,
        gds_path: str | Path | None = None,
        top: str | None = None,
        backend: Backend | str | None = None,
        require_gpu: bool | None = None,
        writefield_indicator_layer: LayerSpec | None = None,
        writefield_indicator_name: str | None = None,
        max_write_field_um: tuple[float, float] | None = None,
        stage_speed_mm_s: float | None = None,
        stage_settle_s: float | None = None,
        ignore_stage: bool | None = None,
        gpu_min_polygons: int | None = None,
    ) -> "EstimateConfig":
        kwargs: dict[str, object] = {}
        if gds_path is not None:
            kwargs["gds_path"] = gds_path
        if top is not None:
            kwargs["top"] = top
        if backend is not None:
            kwargs["backend"] = backend
        if require_gpu is not None:
            kwargs["require_gpu"] = require_gpu
        if writefield_indicator_layer is not None:
            kwargs["writefield_indicator_layer"] = writefield_indicator_layer
        if writefield_indicator_name is not None:
            kwargs["writefield_indicator_name"] = writefield_indicator_name
        if max_write_field_um is not None:
            kwargs["max_write_field_um"] = max_write_field_um
        if stage_speed_mm_s is not None:
            kwargs["stage_speed_mm_s"] = stage_speed_mm_s
        if stage_settle_s is not None:
            kwargs["stage_settle_s"] = stage_settle_s
        if ignore_stage is not None:
            kwargs["ignore_stage"] = ignore_stage
        if gpu_min_polygons is not None:
            kwargs["gpu_min_polygons"] = gpu_min_polygons
        return replace(self, **kwargs)


def load_project_config(value: str | Path | ModuleType) -> ModuleType:
    if isinstance(value, ModuleType):
        return value
    raw = str(value)
    path = Path(raw)
    if path.exists():
        module_name = f"_ebeamtime_config_{abs(hash(path.resolve()))}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ValueError(f"cannot import project config from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return importlib.import_module(raw)


def load_project_estimate_config(
    project_config: str | Path | ModuleType,
    *,
    gds_path: str | Path,
    top: str | None = None,
    backend: Backend | str = Backend.AUTO,
    require_gpu: bool = False,
    writefield_indicator_layer: str | LayerSpec | None = None,
    max_write_field_um: tuple[float, float] | None = None,
    stage_speed_mm_s: float | None = None,
    stage_settle_s: float | None = None,
    ignore_stage: bool = False,
    gpu_min_polygons: int | None = None,
) -> EstimateConfig:
    module = load_project_config(project_config)
    exposures = _load_exposures_from_module(module)

    indicator_name = None
    indicator_layer = None
    configured_indicator = writefield_indicator_layer
    if configured_indicator is None and hasattr(module, "ebeamtime_writefield_indicator_layer"):
        configured_indicator = getattr(module, "ebeamtime_writefield_indicator_layer")
    if configured_indicator is not None:
        if isinstance(configured_indicator, LayerSpec):
            indicator_layer = configured_indicator
        elif isinstance(configured_indicator, str) and hasattr(module, configured_indicator):
            indicator_name = configured_indicator
            indicator_layer = LayerSpec.parse(getattr(module, configured_indicator))
        else:
            indicator_layer = LayerSpec.parse(configured_indicator)

    if max_write_field_um is None and hasattr(module, "ebeamtime_max_write_field_um"):
        max_write_field_um = _size_pair(getattr(module, "ebeamtime_max_write_field_um"), "ebeamtime_max_write_field_um")
    if stage_speed_mm_s is None and hasattr(module, "ebeamtime_stage_speed_mm_s"):
        stage_speed_mm_s = float(getattr(module, "ebeamtime_stage_speed_mm_s"))
    if stage_settle_s is None and hasattr(module, "ebeamtime_stage_settle_s"):
        stage_settle_s = float(getattr(module, "ebeamtime_stage_settle_s"))
    beam_voltage_kV = float(getattr(module, "ebeamtime_beam_voltage_kV")) if hasattr(module, "ebeamtime_beam_voltage_kV") else None
    notes = str(getattr(module, "ebeamtime_notes", ""))

    return EstimateConfig(
        gds_path=gds_path,
        top=top,
        exposures=exposures,
        writefield_indicator_layer=indicator_layer,
        writefield_indicator_name=indicator_name,
        max_write_field_um=max_write_field_um,
        stage_speed_mm_s=stage_speed_mm_s,
        stage_settle_s=0.0 if stage_settle_s is None else stage_settle_s,
        ignore_stage=ignore_stage,
        beam_voltage_kV=beam_voltage_kV,
        backend=backend,
        require_gpu=require_gpu,
        gpu_min_polygons=4096 if gpu_min_polygons is None else gpu_min_polygons,
        notes=notes,
    )


def exposures_from_cli(values: Iterable[str]) -> tuple[EbeamLayerExposure, ...]:
    exposures = []
    for index, value in enumerate(values):
        parts = [part.strip() for part in value.split(":")]
        if len(parts) != 4:
            raise ValueError("--exposure must have form L:D:DOSE_UC_CM2:CURRENT_NA")
        layer = LayerSpec(int(parts[0]), int(parts[1]))
        exposures.append(
            EbeamLayerExposure(
                config_name=f"cli_{layer.layer}_{layer.datatype}_{index}",
                layer=layer,
                dose_uC_cm2=_positive_float(parts[2], f"{value} dose_uC_cm2"),
                beam_current_nA=_positive_float(parts[3], f"{value} beam_current_nA"),
            )
        )
    return tuple(exposures)


def _load_exposures_from_module(module: ModuleType) -> tuple[EbeamLayerExposure, ...]:
    if not hasattr(module, "ebeamtime_layer_exposures"):
        raise ValueError("project config must define ebeamtime_layer_exposures")
    raw = getattr(module, "ebeamtime_layer_exposures")
    if not isinstance(raw, dict):
        raise ValueError("ebeamtime_layer_exposures must be a dict mapping ld_* names to dose/current records")
    exposures = []
    for name, entry in raw.items():
        if not isinstance(name, str) or not name:
            raise ValueError("ebeamtime_layer_exposures keys must be nonempty layer variable names")
        if not hasattr(module, name):
            raise ValueError(f"ebeamtime layer name {name!r} does not exist in project config")
        if not isinstance(entry, dict):
            raise ValueError(f"ebeamtime exposure for {name} must be a dict")
        if "dose_uC_cm2" not in entry:
            raise ValueError(f"ebeamtime exposure for {name} is missing dose_uC_cm2")
        if "beam_current_nA" not in entry:
            raise ValueError(f"ebeamtime exposure for {name} is missing beam_current_nA")
        exposures.append(
            EbeamLayerExposure(
                config_name=name,
                layer=LayerSpec.parse(getattr(module, name)),
                dose_uC_cm2=_positive_float(entry["dose_uC_cm2"], f"{name} dose_uC_cm2"),
                beam_current_nA=_positive_float(entry["beam_current_nA"], f"{name} beam_current_nA"),
            )
        )
    return tuple(exposures)


def _positive_float(value: object, context: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{context} must be positive")
    return result


def _size_pair(value: object, context: str) -> tuple[float, float]:
    if not isinstance(value, tuple | list) or len(value) != 2:
        raise ValueError(f"{context} must be a two-value size")
    return _positive_float(value[0], f"{context}[0]"), _positive_float(value[1], f"{context}[1]")
