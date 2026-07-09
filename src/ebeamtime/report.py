from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import EbeamLayerExposure, LayerSpec

TOOL_VERSION = "0.1.0"


def hours_from_seconds(seconds: float) -> float:
    return float(seconds) / 3600.0


def days_from_seconds(seconds: float) -> float:
    return float(seconds) / 86400.0


def duration_companions(seconds: float) -> dict[str, float]:
    return {"hr": hours_from_seconds(seconds), "days": days_from_seconds(seconds)}


def add_duration_unit_fields(data: dict[str, object], *, skip: set[str] | None = None) -> dict[str, object]:
    skip = set() if skip is None else set(skip)
    result = dict(data)
    for key, value in list(data.items()):
        if key in skip or not key.endswith("_s") or not isinstance(value, int | float):
            continue
        stem = key[:-2]
        result[f"{stem}_hr"] = hours_from_seconds(float(value))
        result[f"{stem}_days"] = days_from_seconds(float(value))
    return result


@dataclass(frozen=True)
class LayerEstimate:
    config_name: str
    layer: LayerSpec
    polygon_count: int
    area_um2: float
    dose_uC_cm2: float
    beam_current_nA: float
    beam_on_s: float

    def to_json(self) -> dict[str, object]:
        return {
            "config_name": self.config_name,
            "layer": self.layer.to_json(),
            "polygon_count": self.polygon_count,
            "area_um2": self.area_um2,
            "dose_uC_cm2": self.dose_uC_cm2,
            "beam_current_nA": self.beam_current_nA,
            "beam_on_s": self.beam_on_s,
            "beam_on_hr": hours_from_seconds(self.beam_on_s),
            "beam_on_days": days_from_seconds(self.beam_on_s),
        }


@dataclass(frozen=True)
class StageEstimate:
    enabled: bool
    field_count: int = 0
    indicator_field_count: int = 0
    synthetic_field_count: int = 0
    outside_indicator_polygon_count: int = 0
    movement_distance_um: float = 0.0
    movement_s: float = 0.0
    settle_s: float = 0.0
    stage_speed_mm_s: float | None = None
    route_start: tuple[float, float] | None = None
    route_end: tuple[float, float] | None = None

    @property
    def total_s(self) -> float:
        return self.movement_s + self.settle_s

    def to_json(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "field_count": self.field_count,
            "indicator_field_count": self.indicator_field_count,
            "synthetic_field_count": self.synthetic_field_count,
            "outside_indicator_polygon_count": self.outside_indicator_polygon_count,
            "movement_distance_um": self.movement_distance_um,
            "movement_s": self.movement_s,
            "movement_hr": hours_from_seconds(self.movement_s),
            "movement_days": days_from_seconds(self.movement_s),
            "settle_s": self.settle_s,
            "settle_hr": hours_from_seconds(self.settle_s),
            "settle_days": days_from_seconds(self.settle_s),
            "total_s": self.total_s,
            "total_hr": hours_from_seconds(self.total_s),
            "total_days": days_from_seconds(self.total_s),
            "stage_speed_mm_s": self.stage_speed_mm_s,
            "route_start": list(self.route_start) if self.route_start is not None else None,
            "route_end": list(self.route_end) if self.route_end is not None else None,
        }


@dataclass(frozen=True)
class EstimateReport:
    path: Path
    top_name: str
    backend: dict[str, object]
    layers: tuple[LayerEstimate, ...]
    stage: StageEstimate
    extraction: dict[str, object]
    timings: dict[str, float] = field(default_factory=dict)
    beam_voltage_kV: float | None = None
    notes: str = ""
    tool_version: str = TOOL_VERSION

    @property
    def total_beam_on_s(self) -> float:
        return sum(layer.beam_on_s for layer in self.layers)

    @property
    def total_s(self) -> float:
        return self.total_beam_on_s + self.stage.total_s

    def to_json_dict(self) -> dict[str, object]:
        backend = dict(self.backend)
        details = backend.get("details")
        if isinstance(details, dict):
            backend["details"] = add_duration_unit_fields(details)
        return {
            "tool": "ebeamtime",
            "tool_version": self.tool_version,
            "path": str(self.path),
            "top_name": self.top_name,
            "backend": backend,
            "beam_voltage_kV": self.beam_voltage_kV,
            "notes": self.notes,
            "total_beam_on_s": self.total_beam_on_s,
            "total_beam_on_hr": hours_from_seconds(self.total_beam_on_s),
            "total_beam_on_days": days_from_seconds(self.total_beam_on_s),
            "total_stage_s": self.stage.total_s,
            "total_stage_hr": hours_from_seconds(self.stage.total_s),
            "total_stage_days": days_from_seconds(self.stage.total_s),
            "total_s": self.total_s,
            "total_hr": hours_from_seconds(self.total_s),
            "total_days": days_from_seconds(self.total_s),
            "layers": [layer.to_json() for layer in self.layers],
            "stage": self.stage.to_json(),
            "extraction": dict(self.extraction),
            "timings": add_duration_unit_fields(dict(self.timings)),
        }

    def write_json(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path


def layer_estimate_from_area(
    exposure: EbeamLayerExposure,
    *,
    polygon_count: int,
    area_um2: float,
    beam_on_s: float,
) -> LayerEstimate:
    return LayerEstimate(
        config_name=exposure.config_name,
        layer=exposure.layer,
        polygon_count=polygon_count,
        area_um2=area_um2,
        dose_uC_cm2=exposure.dose_uC_cm2,
        beam_current_nA=exposure.beam_current_nA,
        beam_on_s=beam_on_s,
    )
