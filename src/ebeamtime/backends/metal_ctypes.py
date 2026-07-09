from __future__ import annotations

import ctypes
import platform
import subprocess
from pathlib import Path
from time import perf_counter

import numpy as np

from ..native_cache import cached_native_library_path
from .base import AreaAggregation


class MetalCtypesUnavailable(RuntimeError):
    pass


def metal_ctypes_available() -> bool:
    if platform.system() != "Darwin":
        return False
    try:
        library = _load_library()
        return bool(library.ebeamtime_metal_available())
    except MetalCtypesUnavailable:
        return False


def release_metal_device_memory() -> None:
    if platform.system() != "Darwin":
        raise MetalCtypesUnavailable("Metal backend is only available on macOS")


def run_metal_area_aggregation(buffer, exposure_ids: np.ndarray, exposure_count: int) -> AreaAggregation:
    if platform.system() != "Darwin":
        raise MetalCtypesUnavailable("Metal backend is only available on macOS")
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
    status = library.ebeamtime_metal_area_totals(
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
    if status != 0:
        message = library.ebeamtime_metal_last_error()
        raise MetalCtypesUnavailable(message.decode("utf-8") if message else "Metal area aggregation failed")
    return AreaAggregation(
        twice_area_dbu2=twice_areas,
        polygon_counts=counts,
        zero_area_polygon_count=int(zero_count.value),
        backend="metal",
        timings={
            "area_aggregate_s": perf_counter() - start,
            "metal_kernel_s": float(elapsed_ms.value) / 1000.0,
        },
        details={
            "metal_kernel_elapsed_s": float(elapsed_ms.value) / 1000.0,
            "transferred_bytes": int(vertices.nbytes + offsets.nbytes + exposure_ids.nbytes + twice_areas.nbytes + counts.nbytes),
        },
    )


def _load_library() -> ctypes.CDLL:
    path = _library_path()
    source = _source_path()
    if not source.exists():
        raise MetalCtypesUnavailable(f"Metal source not found: {source}")
    if not path.exists() or source.stat().st_mtime > path.stat().st_mtime:
        _build_library(path)
    try:
        library = ctypes.CDLL(str(path))
    except OSError as exc:
        raise MetalCtypesUnavailable(str(exc)) from exc
    library.ebeamtime_metal_last_error.argtypes = []
    library.ebeamtime_metal_last_error.restype = ctypes.c_char_p
    library.ebeamtime_metal_available.argtypes = []
    library.ebeamtime_metal_available.restype = ctypes.c_int
    library.ebeamtime_metal_area_totals.argtypes = [
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
    library.ebeamtime_metal_area_totals.restype = ctypes.c_int
    return library


def _build_library(path: Path) -> None:
    clang = _xcrun_value("--find", "clang++")
    sdk = _xcrun_value("--show-sdk-path")
    source = _source_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        clang,
        "-std=c++17",
        "-O3",
        "-dynamiclib",
        "-fobjc-arc",
        "-isysroot",
        sdk,
        "-framework",
        "Foundation",
        "-framework",
        "Metal",
        str(source),
        "-o",
        str(path),
    ]
    completed = subprocess.run(command, check=False, text=True, capture_output=True)
    if completed.returncode != 0:
        raise MetalCtypesUnavailable((completed.stderr or completed.stdout).strip() or "clang++ failed")


def _xcrun_value(*args: str) -> str:
    try:
        completed = subprocess.run(["xcrun", *args], check=False, text=True, capture_output=True)
    except FileNotFoundError as exc:
        raise MetalCtypesUnavailable("xcrun is not available") from exc
    if completed.returncode != 0:
        raise MetalCtypesUnavailable((completed.stderr or completed.stdout).strip() or "xcrun failed")
    return completed.stdout.strip()


def _library_path() -> Path:
    return cached_native_library_path("_ebeamtime_metal_area.dylib")


def _source_path() -> Path:
    return Path(__file__).resolve().parents[1] / "native_src" / "ebeamtime_metal_area.mm"


def _ptr_i64(array: np.ndarray):
    return array.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))


def _ptr_u64(array: np.ndarray):
    return array.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64))


def _ptr_i32(array: np.ndarray):
    return array.ctypes.data_as(ctypes.POINTER(ctypes.c_int32))
