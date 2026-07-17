from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter

import numpy as np

from .backends.base import AreaAggregation
from .backends.cpu import CpuAreaBackend
from .config import EstimateConfig, load_project_estimate_config
from .extraction import dbu_area_to_um2, exposure_id_vector, extract_estimation_geometry
from .native import discover_native_capabilities
from .report import EstimateReport, layer_estimate_from_area
from .semantics import Backend
from .stage import estimate_stage_movement
from .units import beam_on_seconds


@dataclass(frozen=True)
class EstimateRunResult:
    report: EstimateReport
    aggregation: AreaAggregation
    artifacts: dict[str, str] = field(default_factory=dict)


def estimate_gds_write_time(
    config: EstimateConfig,
    *,
    json_report_path: str | Path | None = None,
) -> EstimateRunResult:
    start = perf_counter()
    extraction_start = perf_counter()
    geometry = extract_estimation_geometry(config)
    extraction_s = perf_counter() - extraction_start
    exposure_ids = exposure_id_vector(geometry, config)
    aggregation = _aggregate_area(config, geometry.buffer, exposure_ids)

    layers = []
    for index, exposure in enumerate(config.exposures):
        area_um2 = dbu_area_to_um2(int(aggregation.twice_area_dbu2[index]), geometry.extraction.precision_m)
        layers.append(
            layer_estimate_from_area(
                exposure,
                polygon_count=int(aggregation.polygon_counts[index]),
                area_um2=area_um2,
                beam_on_s=beam_on_seconds(area_um2, exposure.dose_uC_cm2, exposure.beam_current_nA),
            )
        )

    stage_start = perf_counter()
    stage = estimate_stage_movement(geometry, config, exposure_ids)
    stage_s = perf_counter() - stage_start

    timings = {
        "total_s": perf_counter() - start,
        "extract_s": extraction_s,
        "stage_s": stage_s,
        **aggregation.timings,
    }
    backend = {
        "requested": config.backend.value,
        "name": aggregation.backend,
        "requires_gpu": aggregation.details.get("requires_gpu", aggregation.backend in {"cuda", "metal"}),
        "details": dict(aggregation.details),
    }
    report = EstimateReport(
        path=Path(config.gds_path),
        top_name=geometry.top_name,
        backend=backend,
        layers=tuple(layers),
        stage=stage,
        extraction=geometry.extraction.to_json(),
        timings=timings,
        beam_voltage_kV=config.beam_voltage_kV,
        notes=config.notes,
    )
    artifacts = {}
    if json_report_path is not None:
        path = report.write_json(json_report_path)
        artifacts["json_report"] = str(path)
    return EstimateRunResult(report=report, aggregation=aggregation, artifacts=artifacts)


def estimate_gds_write_time_from_project_config(
    gds_path: str | Path,
    project_config: str | Path | object,
    *,
    top: str | None = None,
    backend: Backend | str = Backend.AUTO,
    require_gpu: bool = False,
    json_report_path: str | Path | None = None,
    max_write_field_um: tuple[float, float] | None = None,
    stage_speed_mm_s: float | None = None,
    stage_settle_s: float | None = None,
    ignore_stage: bool = False,
    gpu_min_polygons: int | None = None,
) -> EstimateRunResult:
    config = load_project_estimate_config(
        project_config,
        gds_path=gds_path,
        top=top,
        backend=backend,
        require_gpu=require_gpu,
        max_write_field_um=max_write_field_um,
        stage_speed_mm_s=stage_speed_mm_s,
        stage_settle_s=stage_settle_s,
        ignore_stage=ignore_stage,
        gpu_min_polygons=gpu_min_polygons,
    )
    return estimate_gds_write_time(config, json_report_path=json_report_path)


def _aggregate_area(config: EstimateConfig, buffer, exposure_ids: np.ndarray) -> AreaAggregation:
    backend = _select_backend(config, buffer.polygon_count)
    try:
        return backend.aggregate(buffer, exposure_ids, len(config.exposures))
    except Exception as exc:
        if config.backend != Backend.AUTO or config.require_gpu:
            raise
        fallback = CpuAreaBackend().aggregate(buffer, exposure_ids, len(config.exposures))
        details = dict(fallback.details)
        details["fallback_reason"] = str(exc)
        details["requested_gpu_backend_failed"] = backend.capabilities().name
        return AreaAggregation(
            twice_area_dbu2=fallback.twice_area_dbu2,
            polygon_counts=fallback.polygon_counts,
            zero_area_polygon_count=fallback.zero_area_polygon_count,
            backend=fallback.backend,
            timings=fallback.timings,
            details=details,
        )


def _select_backend(config: EstimateConfig, polygon_count: int):
    requested = config.backend
    if requested == Backend.CPU:
        return CpuAreaBackend()
    if requested == Backend.CUDA:
        from .backends.cuda import CudaAreaBackend

        return CudaAreaBackend()
    if requested == Backend.METAL:
        from .backends.metal import MetalAreaBackend

        return MetalAreaBackend()

    use_gpu_for_size = polygon_count >= config.gpu_min_polygons or config.require_gpu
    if not use_gpu_for_size:
        return CpuAreaBackend()
    capabilities = discover_native_capabilities()
    if use_gpu_for_size and capabilities.cuda_available:
        from .backends.cuda import CudaAreaBackend

        return CudaAreaBackend()
    if use_gpu_for_size and capabilities.metal_available:
        from .backends.metal import MetalAreaBackend

        return MetalAreaBackend()
    if config.require_gpu:
        if capabilities.nvcc_available:
            from .backends.cuda import CudaAreaBackend

            return CudaAreaBackend()
        if capabilities.xcrun_available:
            from .backends.metal import MetalAreaBackend

            return MetalAreaBackend()
        raise RuntimeError("GPU backend is required but no CUDA or Metal backend is available")
    backend = CpuAreaBackend()
    if requested == Backend.AUTO:
        return backend
    return backend
