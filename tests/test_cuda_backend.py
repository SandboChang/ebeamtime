from __future__ import annotations

import gdstk
import pytest

import ebeamtime.native as native_module
from ebeamtime.api import estimate_gds_write_time
from ebeamtime.config import EbeamLayerExposure, EstimateConfig, LayerSpec
from ebeamtime.native import CUDA_ARCH_ENV, LEGACY_CUDA_ARCH_ENV, discover_native_capabilities, nvcc_architecture_flags


def test_cuda_architecture_configuration_generates_native_sass(monkeypatch):
    monkeypatch.setenv(CUDA_ARCH_ENV, "89;120")
    assert discover_native_capabilities().cuda_architectures == ("89", "120")
    assert nvcc_architecture_flags() == (
        "--generate-code=arch=compute_89,code=sm_89",
        "--generate-code=arch=compute_120,code=sm_120",
    )


def test_default_cuda_architecture_is_native(monkeypatch):
    monkeypatch.delenv(CUDA_ARCH_ENV, raising=False)
    monkeypatch.delenv(LEGACY_CUDA_ARCH_ENV, raising=False)

    assert nvcc_architecture_flags() == ("-arch=native",)


def test_tool_lookup_cache_tracks_path_changes(monkeypatch):
    calls = []

    def fake_which(name, *, path=None):
        calls.append((name, path))
        return f"{path}/{name}" if path == "with-tools" else None

    native_module._which_tool.cache_clear()
    monkeypatch.setattr(native_module.shutil, "which", fake_which)
    assert native_module._which_tool("nvcc", "without-tools") is None
    assert native_module._which_tool("nvcc", "with-tools") == "with-tools/nvcc"
    assert native_module._which_tool("nvcc", "with-tools") == "with-tools/nvcc"
    assert calls == [("nvcc", "without-tools"), ("nvcc", "with-tools")]
    native_module._which_tool.cache_clear()


def test_cuda_backend_matches_cpu_when_available(tmp_path):
    if not discover_native_capabilities().cuda_available:
        pytest.skip("CUDA ebeamtime backend is not available")
    cell = gdstk.Cell("top")
    for index in range(32):
        cell.add(gdstk.rectangle((index * 2, 0), (index * 2 + 1, 3), layer=1, datatype=0))
    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    lib.add(cell)
    path = tmp_path / "cuda.gds"
    lib.write_gds(str(path))
    exposures = (
        EbeamLayerExposure("ld_rod", LayerSpec(1, 0), dose_uC_cm2=100, beam_current_nA=1),
    )
    cpu = estimate_gds_write_time(EstimateConfig(path, exposures, backend="cpu")).report
    cuda = estimate_gds_write_time(EstimateConfig(path, exposures, backend="cuda")).report
    assert cuda.backend["name"] == "cuda"
    assert cuda.layers[0].area_um2 == pytest.approx(cpu.layers[0].area_um2)
    assert cuda.total_beam_on_s == pytest.approx(cpu.total_beam_on_s)


def test_experimental_metal_backend_matches_cpu_when_available(tmp_path):
    if not discover_native_capabilities().metal_available:
        pytest.skip("Metal ebeamtime backend requires prepared Apple Silicon hardware")
    cell = gdstk.Cell("top")
    for index in range(32):
        cell.add(gdstk.rectangle((index * 2, 0), (index * 2 + 1, 3), layer=1, datatype=0))
    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    lib.add(cell)
    path = tmp_path / "metal.gds"
    lib.write_gds(str(path))
    exposures = (EbeamLayerExposure("ld_rod", LayerSpec(1, 0), 100, 1),)
    cpu = estimate_gds_write_time(EstimateConfig(path, exposures, backend="cpu")).report
    metal = estimate_gds_write_time(EstimateConfig(path, exposures, backend="metal")).report
    assert metal.backend["name"] == "metal"
    assert metal.layers[0].area_um2 == pytest.approx(cpu.layers[0].area_um2)
    assert metal.total_beam_on_s == pytest.approx(cpu.total_beam_on_s)
