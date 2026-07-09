from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import numpy as np

from scgds.gdsdiff.extract import extract_gds_polygons
from scgds.gdsdiff.gds_metadata import read_gds_metadata

from .config import EstimateConfig, LayerSpec


@dataclass(frozen=True)
class ExtractionSummary:
    raw_polygon_count: int
    kept_polygon_count: int
    vertex_count: int
    precision_m: Decimal
    unit_m: Decimal
    max_snap_error_dbu: str

    def to_json(self) -> dict[str, object]:
        return {
            "raw_polygon_count": self.raw_polygon_count,
            "kept_polygon_count": self.kept_polygon_count,
            "vertex_count": self.vertex_count,
            "precision_m": str(self.precision_m),
            "unit_m": str(self.unit_m),
            "max_snap_error_dbu": self.max_snap_error_dbu,
        }


@dataclass(frozen=True)
class ExtractedGeometry:
    path: Path
    top_name: str
    buffer: object
    layer_by_buffer_id: tuple[LayerSpec, ...]
    extraction: ExtractionSummary


def extract_estimation_geometry(config: EstimateConfig) -> ExtractedGeometry:
    metadata = read_gds_metadata(config.gds_path)
    selector = tuple((layer.layer, layer.datatype) for layer in config.selected_layers)
    result = extract_gds_polygons(config.gds_path, top_name=config.top, layers=selector)
    layer_by_buffer_id = tuple(LayerSpec(layer.layer, layer.datatype) for layer in result.buffer.layer_table.layers)
    return ExtractedGeometry(
        path=Path(config.gds_path),
        top_name=result.top_name,
        buffer=result.buffer,
        layer_by_buffer_id=layer_by_buffer_id,
        extraction=ExtractionSummary(
            raw_polygon_count=result.stats.raw_polygon_count,
            kept_polygon_count=result.stats.kept_polygon_count,
            vertex_count=result.stats.vertex_count,
            precision_m=metadata.precision_m,
            unit_m=metadata.unit_m,
            max_snap_error_dbu=str(result.stats.max_snap_error_dbu),
        ),
    )


def exposure_id_vector(geometry: ExtractedGeometry, config: EstimateConfig) -> np.ndarray:
    exposure_by_layer = {exposure.layer: index for index, exposure in enumerate(config.exposures)}
    out = np.full((geometry.buffer.polygon_count,), -1, dtype=np.int32)
    for index, layer_id in enumerate(geometry.buffer.layer_ids):
        layer = geometry.layer_by_buffer_id[int(layer_id)]
        exposure_index = exposure_by_layer.get(layer)
        if exposure_index is not None:
            out[index] = exposure_index
    return out


def polygon_layer(geometry: ExtractedGeometry, polygon_index: int) -> LayerSpec:
    return geometry.layer_by_buffer_id[int(geometry.buffer.layer_ids[polygon_index])]


def dbu_area_to_um2(twice_area_dbu2: int, precision_m: Decimal) -> float:
    dbu_um = float(precision_m / Decimal("0.000001"))
    return float(twice_area_dbu2) * 0.5 * dbu_um * dbu_um


def bbox_dbu_to_um(bbox: np.ndarray | tuple[int, int, int, int], precision_m: Decimal) -> tuple[float, float, float, float]:
    dbu_um = float(precision_m / Decimal("0.000001"))
    x0, y0, x1, y1 = bbox
    return float(x0) * dbu_um, float(y0) * dbu_um, float(x1) * dbu_um, float(y1) * dbu_um


def bbox_center_um(bbox: np.ndarray | tuple[int, int, int, int], precision_m: Decimal) -> tuple[float, float]:
    x0, y0, x1, y1 = bbox_dbu_to_um(bbox, precision_m)
    return (x0 + x1) * 0.5, (y0 + y1) * 0.5
