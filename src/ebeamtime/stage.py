from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from .config import EstimateConfig
from .extraction import ExtractedGeometry, bbox_dbu_to_um, bbox_center_um, polygon_layer
from .report import StageEstimate

BBox = tuple[float, float, float, float]
Point = tuple[float, float]


@dataclass(frozen=True)
class _Field:
    bbox: BBox
    center: Point
    synthetic: bool = False


def estimate_stage_movement(geometry: ExtractedGeometry, config: EstimateConfig, exposure_ids: np.ndarray) -> StageEstimate:
    if config.ignore_stage:
        return StageEstimate(enabled=False)
    enabled = (
        config.writefield_indicator_layer is not None
        or config.max_write_field_um is not None
        or config.stage_speed_mm_s is not None
    )
    if not enabled:
        return StageEstimate(enabled=False)

    exposed_indices = tuple(index for index, exposure_id in enumerate(exposure_ids) if int(exposure_id) >= 0)
    if not exposed_indices:
        return StageEstimate(enabled=True, stage_speed_mm_s=config.stage_speed_mm_s)

    indicator_fields = _indicator_fields(geometry, config)
    active_indicator_fields: dict[int, _Field] = {}
    outside_bboxes: list[BBox] = []
    outside_count = 0

    if indicator_fields:
        for index in exposed_indices:
            bbox = bbox_dbu_to_um(geometry.buffer.bboxes[index], geometry.extraction.precision_m)
            field_index = _containing_field_index(bbox, indicator_fields)
            if field_index is None:
                outside_bboxes.append(bbox)
                outside_count += 1
            else:
                active_indicator_fields[field_index] = indicator_fields[field_index]
        fields = list(active_indicator_fields.values())
        synthetic_fields = _synthetic_fields(outside_bboxes, config.max_write_field_um)
        fields.extend(synthetic_fields)
    else:
        exposed_bboxes = [
            bbox_dbu_to_um(geometry.buffer.bboxes[index], geometry.extraction.precision_m)
            for index in exposed_indices
        ]
        synthetic_fields = _synthetic_fields(exposed_bboxes, config.max_write_field_um)
        fields = synthetic_fields

    centers = tuple(field.center for field in fields)
    distance_um, route_start, route_end = _greedy_route_distance(centers)
    move_s = 0.0
    settle_s = 0.0
    if config.stage_speed_mm_s is not None and config.stage_speed_mm_s > 0:
        move_s = (distance_um / 1000.0) / config.stage_speed_mm_s
    if len(centers) > 1:
        settle_s = (len(centers) - 1) * config.stage_settle_s

    return StageEstimate(
        enabled=True,
        field_count=len(fields),
        indicator_field_count=len(active_indicator_fields),
        synthetic_field_count=sum(1 for field in fields if field.synthetic),
        outside_indicator_polygon_count=outside_count,
        movement_distance_um=distance_um,
        movement_s=move_s,
        settle_s=settle_s,
        stage_speed_mm_s=config.stage_speed_mm_s,
        route_start=route_start,
        route_end=route_end,
    )


def _indicator_fields(geometry: ExtractedGeometry, config: EstimateConfig) -> tuple[_Field, ...]:
    if config.writefield_indicator_layer is None:
        return ()
    fields = []
    for index in range(geometry.buffer.polygon_count):
        if polygon_layer(geometry, index) != config.writefield_indicator_layer:
            continue
        bbox = bbox_dbu_to_um(geometry.buffer.bboxes[index], geometry.extraction.precision_m)
        fields.append(_Field(bbox=bbox, center=_bbox_center(bbox), synthetic=False))
    return tuple(fields)


def _containing_field_index(bbox: BBox, fields: tuple[_Field, ...]) -> int | None:
    matches = [
        (index, _distance(_bbox_center(bbox), field.center), _bbox_area(field.bbox))
        for index, field in enumerate(fields)
        if _bbox_contains(field.bbox, bbox)
    ]
    if not matches:
        return None
    matches.sort(key=lambda item: (item[1], item[2], item[0]))
    return matches[0][0]


def _synthetic_fields(bboxes: list[BBox], max_write_field_um: tuple[float, float] | None) -> list[_Field]:
    if not bboxes:
        return []
    if max_write_field_um is None:
        seen: set[tuple[float, float, float, float]] = set()
        fields = []
        for bbox in bboxes:
            key = tuple(round(value, 9) for value in bbox)
            if key in seen:
                continue
            seen.add(key)
            fields.append(_Field(bbox=bbox, center=_bbox_center(bbox), synthetic=True))
        return fields

    width, height = max_write_field_um
    tiles: set[tuple[int, int]] = set()
    for x0, y0, x1, y1 in bboxes:
        ix0 = math.floor(x0 / width)
        iy0 = math.floor(y0 / height)
        ix1 = math.floor(math.nextafter(x1, -math.inf) / width)
        iy1 = math.floor(math.nextafter(y1, -math.inf) / height)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                tiles.add((ix, iy))
    fields = []
    for ix, iy in sorted(tiles):
        bbox = (ix * width, iy * height, (ix + 1) * width, (iy + 1) * height)
        fields.append(_Field(bbox=bbox, center=_bbox_center(bbox), synthetic=True))
    return fields


def _greedy_route_distance(centers: tuple[Point, ...]) -> tuple[float, Point | None, Point | None]:
    if len(centers) <= 1:
        return 0.0, centers[0] if centers else None, centers[0] if centers else None
    candidates = _route_start_candidates(centers)
    best_distance = math.inf
    best_start = None
    best_end = None
    for start_index in candidates:
        distance, end = _greedy_route_from(centers, start_index)
        if distance < best_distance:
            best_distance = distance
            best_start = centers[start_index]
            best_end = end
    return best_distance, best_start, best_end


def _route_start_candidates(centers: tuple[Point, ...]) -> tuple[int, ...]:
    if len(centers) <= 256:
        return tuple(range(len(centers)))
    xs = [point[0] for point in centers]
    ys = [point[1] for point in centers]
    centroid = (sum(xs) / len(xs), sum(ys) / len(ys))
    targets = [
        (min(xs), min(ys)),
        (min(xs), max(ys)),
        (max(xs), min(ys)),
        (max(xs), max(ys)),
        centroid,
        (min(xs), centroid[1]),
        (max(xs), centroid[1]),
        (centroid[0], min(ys)),
        (centroid[0], max(ys)),
    ]
    indices = {min(range(len(centers)), key=lambda index, target=target: _distance(centers[index], target)) for target in targets}
    return tuple(sorted(indices))


def _greedy_route_from(centers: tuple[Point, ...], start_index: int) -> tuple[float, Point]:
    remaining = set(range(len(centers)))
    current = start_index
    remaining.remove(current)
    distance = 0.0
    while remaining:
        next_index = min(remaining, key=lambda index: (_distance(centers[current], centers[index]), centers[index]))
        distance += _distance(centers[current], centers[next_index])
        current = next_index
        remaining.remove(current)
    return distance, centers[current]


def _bbox_contains(outer: BBox, inner: BBox) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def _bbox_center(bbox: BBox) -> Point:
    return (bbox[0] + bbox[2]) * 0.5, (bbox[1] + bbox[3]) * 0.5


def _bbox_area(bbox: BBox) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def _distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])
