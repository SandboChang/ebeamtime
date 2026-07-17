from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from functools import lru_cache

from .report import TOOL_VERSION

CUDA_ARCH_ENV = "EBEAMTIME_CUDA_ARCHITECTURES"
LEGACY_CUDA_ARCH_ENV = "SCGDS_EBEAMTIME_CUDA_ARCHITECTURES"


@dataclass(frozen=True)
class NativeCapabilities:
    tool_version: str
    cuda_ctypes_available: bool
    metal_ctypes_available: bool
    nvcc_available: bool
    xcrun_available: bool
    cuda_architectures: tuple[str, ...] = ()
    cuda_compile_flags: tuple[str, ...] = ()

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
            "cuda_architectures": list(self.cuda_architectures),
            "cuda_compile_flags": list(self.cuda_compile_flags),
        }


def discover_native_capabilities() -> NativeCapabilities:
    """Inspect prepared backends without compiling or loading native code."""

    return NativeCapabilities(
        tool_version=TOOL_VERSION,
        cuda_ctypes_available=_cuda_ctypes_available(),
        metal_ctypes_available=_metal_ctypes_available(),
        nvcc_available=resolve_nvcc_path() is not None,
        xcrun_available=_which_tool("xcrun", os.environ.get("PATH")) is not None,
        cuda_architectures=_cuda_architectures_from_env(),
        cuda_compile_flags=nvcc_architecture_flags(),
    )


def _cuda_ctypes_available() -> bool:
    from .backends.cuda_ctypes import prepared_cuda_library_path

    return prepared_cuda_library_path().is_file()


@lru_cache(maxsize=16)
def _which_tool(name: str, path: str | None) -> str | None:
    """Resolve a tool once per PATH value while honoring runtime PATH changes."""

    return shutil.which(name, path=path)


def _metal_ctypes_available() -> bool:
    from .native_cache import native_cache_dir

    return any(native_cache_dir().glob("_ebeamtime_metal_area-*.dylib"))


def resolve_nvcc_path() -> str | None:
    """Reuse gdsdiff's documented CUDA toolchain inspection contract."""

    from gdsdiff import inspect_cuda_toolchain

    return inspect_cuda_toolchain().nvcc_path


def _cuda_architectures_from_env() -> tuple[str, ...]:
    raw = os.environ.get(CUDA_ARCH_ENV) or os.environ.get(LEGACY_CUDA_ARCH_ENV) or ""
    return tuple(part.strip() for part in raw.replace(";", ",").split(",") if part.strip())


def nvcc_architecture_flags() -> tuple[str, ...]:
    """Translate configured CUDA architectures into native-SASS nvcc flags."""

    configured_architectures = _cuda_architectures_from_env()
    if not configured_architectures:
        return ("-arch=native",)
    flags = []
    for configured in configured_architectures:
        architecture = configured.lower()
        for prefix in ("sm_", "compute_"):
            if architecture.startswith(prefix):
                architecture = architecture[len(prefix) :]
                break
        if not architecture.isdigit():
            raise ValueError(f"invalid CUDA architecture {configured!r}; expected values such as '89' or '120'")
        flags.append(f"--generate-code=arch=compute_{architecture},code=sm_{architecture}")
    return tuple(flags)
