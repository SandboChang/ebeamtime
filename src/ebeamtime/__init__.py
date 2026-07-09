"""Analytical ebeam write-time estimation for GDS layouts."""
from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MODULES = {
    "Backend": ".semantics",
    "EbeamLayerExposure": ".config",
    "EstimateConfig": ".config",
    "EstimateRunResult": ".api",
    "EstimateReport": ".report",
    "ExtractionSummary": ".extraction",
    "LayerEstimate": ".report",
    "LayerSpec": ".config",
    "NativeCapabilities": ".native",
    "StageEstimate": ".report",
    "beam_on_seconds": ".units",
    "discover_native_capabilities": ".native",
    "estimate_gds_write_time": ".api",
    "estimate_gds_write_time_from_project_config": ".api",
    "estimate_from_area": ".units",
    "load_project_config": ".config",
    "load_project_estimate_config": ".config",
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted((*globals(), *__all__))
