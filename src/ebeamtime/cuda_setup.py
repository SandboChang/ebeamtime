from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, replace
from typing import Sequence

import numpy as np

from gdsdiff import CudaToolchainReport, inspect_cuda_toolchain

from .native import _cuda_architectures_from_env, nvcc_architecture_flags
from .native_cache import native_cache_dir


class CudaPreparationError(RuntimeError):
    """Raised when the optional ebeamtime CUDA backend cannot be prepared."""


@dataclass(frozen=True)
class CudaPreparationReport:
    ready: bool
    built: bool
    reused: bool
    verified: bool
    library_path: str
    toolchain: CudaToolchainReport

    def to_json(self) -> dict[str, object]:
        payload = asdict(self)
        payload["toolchain"] = self.toolchain.to_json()
        return payload


def prepare_cuda() -> CudaPreparationReport:
    """Build the ebeamtime CUDA area kernel and verify a known triangle."""

    try:
        toolchain = _ebeamtime_toolchain_report(inspect_cuda_toolchain())
    except (OSError, ValueError) as exc:
        raise CudaPreparationError(str(exc)) from exc
    if not toolchain.available:
        raise CudaPreparationError(toolchain.reason or "CUDA toolchain is unavailable")
    try:
        from .backends.cuda_ctypes import prepared_cuda_library_path, run_cuda_area_aggregation

        library = prepared_cuda_library_path()
        existed = library.is_file()
        class _SmokeBuffer:
            vertices_xy = np.asarray(((0, 0), (10, 0), (0, 10)), dtype=np.int64)
            polygon_offsets = np.asarray((0, 3), dtype=np.uint64)
            polygon_count = 1

        result = run_cuda_area_aggregation(_SmokeBuffer(), np.asarray((0,), dtype=np.int32), 1)
        if int(result.twice_area_dbu2[0]) != 100 or int(result.polygon_counts[0]) != 1:
            raise CudaPreparationError("CUDA smoke area aggregation returned an incorrect result")
    except CudaPreparationError:
        raise
    except Exception as exc:
        raise CudaPreparationError(str(exc)) from exc
    if not library.is_file():
        raise CudaPreparationError("CUDA preparation did not publish the expected native library")
    built = not existed
    return CudaPreparationReport(True, built, not built, True, str(library), toolchain)


def _ebeamtime_toolchain_report(report: CudaToolchainReport) -> CudaToolchainReport:
    """Apply ebeamtime's package-specific CUDA build configuration."""

    return replace(
        report,
        architectures=_cuda_architectures_from_env(),
        compile_flags=nvcc_architecture_flags(),
        cache_path=str(native_cache_dir()),
    )


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="ebeamtime-prepare-cuda", description="Build and verify the optional ebeamtime CUDA backend.")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report.")
    args = parser.parse_args(argv)
    try:
        report = prepare_cuda()
    except CudaPreparationError as exc:
        if args.json:
            print(json.dumps({"ready": False, "error": str(exc)}, indent=2, sort_keys=True))
        else:
            print(f"ebeamtime-prepare-cuda: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report.to_json(), indent=2, sort_keys=True))
    else:
        action = "built" if report.built else "reused"
        print(f"CUDA backend ready ({action}): {report.library_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
