from __future__ import annotations

import json

import ebeamtime.cuda_setup as cuda_setup
from gdsdiff import CudaToolchainReport


def test_toolchain_report_uses_ebeamtime_build_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv("EBEAMTIME_CUDA_ARCHITECTURES", "89;120")
    monkeypatch.setenv("EBEAMTIME_NATIVE_CACHE_DIR", str(tmp_path))
    base = CudaToolchainReport(
        available=True,
        platform="Linux",
        machine="x86_64",
        nvcc_path="/usr/local/cuda/bin/nvcc",
        nvcc_version="13.3",
        host_compiler="/usr/bin/g++",
        driver_version="596.36",
        devices=("GPU",),
        architectures=(),
        compile_flags=("-arch=native",),
        cache_path="/gdsdiff-cache",
    )

    report = cuda_setup._ebeamtime_toolchain_report(base)

    assert report.architectures == ("89", "120")
    assert report.compile_flags == (
        "--generate-code=arch=compute_89,code=sm_89",
        "--generate-code=arch=compute_120,code=sm_120",
    )
    assert report.cache_path.startswith(str(tmp_path))


def test_prepare_cuda_cli_uses_exit_two_for_unavailable_backend(monkeypatch, capsys):
    monkeypatch.setattr(
        cuda_setup,
        "prepare_cuda",
        lambda: (_ for _ in ()).throw(cuda_setup.CudaPreparationError("unavailable")),
    )
    assert cuda_setup.main(["--json"]) == 2
    assert json.loads(capsys.readouterr().out) == {"ready": False, "error": "unavailable"}
