from __future__ import annotations

import numpy as np

from .base import AreaAggregation, BackendCapabilities


class CudaAreaUnavailable(RuntimeError):
    pass


class CudaAreaBackend:
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(name="cuda", deterministic=True, requires_gpu=True)

    def aggregate(self, buffer, exposure_ids: np.ndarray, exposure_count: int) -> AreaAggregation:
        from .cuda_ctypes import CudaCtypesUnavailable, run_cuda_area_aggregation

        try:
            return run_cuda_area_aggregation(buffer, exposure_ids, exposure_count)
        except CudaCtypesUnavailable as exc:
            raise CudaAreaUnavailable(str(exc)) from exc
