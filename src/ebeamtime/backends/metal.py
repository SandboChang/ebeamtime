from __future__ import annotations

import numpy as np

from .base import AreaAggregation, BackendCapabilities


class MetalAreaUnavailable(RuntimeError):
    pass


class MetalAreaBackend:
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(name="metal", deterministic=True, requires_gpu=True)

    def aggregate(self, buffer, exposure_ids: np.ndarray, exposure_count: int) -> AreaAggregation:
        from .metal_ctypes import MetalCtypesUnavailable, run_metal_area_aggregation

        try:
            return run_metal_area_aggregation(buffer, exposure_ids, exposure_count)
        except MetalCtypesUnavailable as exc:
            raise MetalAreaUnavailable(str(exc)) from exc
