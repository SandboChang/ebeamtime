from __future__ import annotations

import shutil
from dataclasses import dataclass

from .report import TOOL_VERSION


@dataclass(frozen=True)
class NativeCapabilities:
    tool_version: str
    cuda_ctypes_available: bool
    metal_ctypes_available: bool
    nvcc_available: bool
    xcrun_available: bool

    @property
    def cpu_available(self) -> bool:
        return True

    @property
    def cuda_available(self) -> bool:
        return self.cuda_ctypes_available

    @property
    def metal_available(self) -> bool:
        return self.metal_ctypes_available

    def to_json(self) -> dict[str, object]:
        return {
            "tool_version": self.tool_version,
            "cpu_available": self.cpu_available,
            "cuda_ctypes_available": self.cuda_ctypes_available,
            "cuda_available": self.cuda_available,
            "metal_ctypes_available": self.metal_ctypes_available,
            "metal_available": self.metal_available,
            "nvcc_available": self.nvcc_available,
            "xcrun_available": self.xcrun_available,
        }


def discover_native_capabilities() -> NativeCapabilities:
    return NativeCapabilities(
        tool_version=TOOL_VERSION,
        cuda_ctypes_available=_cuda_ctypes_available(),
        metal_ctypes_available=_metal_ctypes_available(),
        nvcc_available=shutil.which("nvcc") is not None,
        xcrun_available=shutil.which("xcrun") is not None,
    )


def _cuda_ctypes_available() -> bool:
    try:
        from .backends.cuda_ctypes import cuda_ctypes_available

        return cuda_ctypes_available()
    except Exception:
        return False


def _metal_ctypes_available() -> bool:
    try:
        from .backends.metal_ctypes import metal_ctypes_available

        return metal_ctypes_available()
    except Exception:
        return False
