from __future__ import annotations

from time import perf_counter

import numpy as np

from .base import AreaAggregation, BackendCapabilities


class CpuAreaBackend:
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(name="cpu", deterministic=True, requires_gpu=False)

    def aggregate(self, buffer, exposure_ids: np.ndarray, exposure_count: int) -> AreaAggregation:
        start = perf_counter()
        twice_areas = np.zeros((exposure_count,), dtype=np.uint64)
        counts = np.zeros((exposure_count,), dtype=np.uint64)
        zero_area_count = 0
        for index in range(buffer.polygon_count):
            exposure_index = int(exposure_ids[index])
            if exposure_index < 0:
                continue
            counts[exposure_index] += 1
            twice_area = _polygon_twice_area(buffer.polygon_vertices(index))
            if twice_area == 0:
                zero_area_count += 1
            twice_areas[exposure_index] += np.uint64(twice_area)
        return AreaAggregation(
            twice_area_dbu2=twice_areas,
            polygon_counts=counts,
            zero_area_polygon_count=zero_area_count,
            backend="cpu",
            timings={"area_aggregate_s": perf_counter() - start},
        )


def _polygon_twice_area(points: np.ndarray) -> int:
    if len(points) < 3:
        return 0
    x = points[:, 0].astype(np.int64, copy=False)
    y = points[:, 1].astype(np.int64, copy=False)
    area = int(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))
    return abs(area)
