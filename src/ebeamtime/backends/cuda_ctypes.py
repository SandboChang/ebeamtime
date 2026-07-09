from __future__ import annotations

import ctypes
import subprocess
from pathlib import Path
from time import perf_counter

import numpy as np

from ..native_cache import cached_native_library_path
from .base import AreaAggregation


class CudaCtypesUnavailable(RuntimeError):
    pass


def cuda_ctypes_available() -> bool:
    try:
        library = _load_library()
        return bool(library.ebeamtime_cuda_available())
    except CudaCtypesUnavailable:
        return False


def release_cuda_device_memory() -> None:
    library = _load_library()
    status = library.ebeamtime_cuda_release_device_memory()
    if status != 0:
        message = library.ebeamtime_cuda_last_error()
        raise CudaCtypesUnavailable(message.decode("utf-8") if message else "CUDA cleanup failed")


def run_cuda_area_aggregation(buffer, exposure_ids: np.ndarray, exposure_count: int) -> AreaAggregation:
    library = _load_library()
    start = perf_counter()
    vertices = np.ascontiguousarray(buffer.vertices_xy.reshape(-1), dtype=np.int64)
    offsets = np.ascontiguousarray(buffer.polygon_offsets, dtype=np.uint64)
    exposure_ids = np.ascontiguousarray(exposure_ids, dtype=np.int32)
    twice_areas = np.zeros((exposure_count,), dtype=np.uint64)
    counts = np.zeros((exposure_count,), dtype=np.uint64)
    zero_count = ctypes.c_uint64(0)
    elapsed_ms = ctypes.c_float(0.0)
    if exposure_ids.shape != (buffer.polygon_count,):
        raise ValueError("exposure_ids shape must match polygon count")
    status = library.ebeamtime_cuda_area_totals(
        _ptr_i64(vertices),
        _ptr_u64(offsets),
        _ptr_i32(exposure_ids),
        ctypes.c_uint64(buffer.polygon_count),
        ctypes.c_uint32(exposure_count),
        _ptr_u64(twice_areas),
        _ptr_u64(counts),
        ctypes.byref(zero_count),
        ctypes.byref(elapsed_ms),
    )
    cleanup_start = perf_counter()
    cleanup_error = None
    try:
        release_cuda_device_memory()
    except CudaCtypesUnavailable as exc:
        cleanup_error = str(exc)
    cleanup_s = perf_counter() - cleanup_start
    if status != 0:
        message = library.ebeamtime_cuda_last_error()
        raise CudaCtypesUnavailable(message.decode("utf-8") if message else "CUDA area aggregation failed")
    details: dict[str, object] = {
        "cuda_kernel_elapsed_s": float(elapsed_ms.value) / 1000.0,
        "transferred_bytes": int(vertices.nbytes + offsets.nbytes + exposure_ids.nbytes + twice_areas.nbytes + counts.nbytes),
    }
    if cleanup_error:
        details["cuda_release_error"] = cleanup_error
    return AreaAggregation(
        twice_area_dbu2=twice_areas,
        polygon_counts=counts,
        zero_area_polygon_count=int(zero_count.value),
        backend="cuda",
        timings={
            "area_aggregate_s": perf_counter() - start,
            "cuda_kernel_s": float(elapsed_ms.value) / 1000.0,
            "cuda_release_s": cleanup_s,
        },
        details=details,
    )


def _load_library() -> ctypes.CDLL:
    path = _library_path()
    source = _source_path()
    if not source.exists():
        raise CudaCtypesUnavailable(f"CUDA source not found: {source}")
    if not path.exists() or source.stat().st_mtime > path.stat().st_mtime:
        _build_library(path)
    try:
        library = ctypes.CDLL(str(path))
    except OSError as exc:
        raise CudaCtypesUnavailable(str(exc)) from exc
    library.ebeamtime_cuda_last_error.argtypes = []
    library.ebeamtime_cuda_last_error.restype = ctypes.c_char_p
    library.ebeamtime_cuda_available.argtypes = []
    library.ebeamtime_cuda_available.restype = ctypes.c_int
    library.ebeamtime_cuda_release_device_memory.argtypes = []
    library.ebeamtime_cuda_release_device_memory.restype = ctypes.c_int
    library.ebeamtime_cuda_area_totals.argtypes = [
        ctypes.POINTER(ctypes.c_int64),
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.c_uint64,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_float),
    ]
    library.ebeamtime_cuda_area_totals.restype = ctypes.c_int
    return library


def _build_library(path: Path) -> None:
    source = _source_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "nvcc",
        "-O3",
        "-std=c++17",
        "--shared",
        "-Xcompiler",
        "-fPIC",
        str(source),
        "-o",
        str(path),
    ]
    try:
        completed = subprocess.run(command, check=False, text=True, capture_output=True)
    except FileNotFoundError as exc:
        raise CudaCtypesUnavailable("nvcc is not available") from exc
    if completed.returncode != 0:
        raise CudaCtypesUnavailable((completed.stderr or completed.stdout).strip() or "nvcc failed")


def _library_path() -> Path:
    return cached_native_library_path("_ebeamtime_cuda_area.so")


def _source_path() -> Path:
    return Path(__file__).resolve().parents[1] / "native_src" / "ebeamtime_cuda_area.cu"


def _ptr_i64(array: np.ndarray):
    return array.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))


def _ptr_u64(array: np.ndarray):
    return array.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64))


def _ptr_i32(array: np.ndarray):
    return array.ctypes.data_as(ctypes.POINTER(ctypes.c_int32))
