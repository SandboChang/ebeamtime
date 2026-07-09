from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class BackendCapabilities:
    name: str
    deterministic: bool = True
    requires_gpu: bool = False


@dataclass(frozen=True)
class AreaAggregation:
    twice_area_dbu2: np.ndarray
    polygon_counts: np.ndarray
    zero_area_polygon_count: int
    backend: str
    timings: dict[str, float] = field(default_factory=dict)
    details: dict[str, object] = field(default_factory=dict)


class AreaBackend(Protocol):
    def capabilities(self) -> BackendCapabilities:
        ...

    def aggregate(
        self,
        buffer,
        exposure_ids: np.ndarray,
        exposure_count: int,
    ) -> AreaAggregation:
        ...
