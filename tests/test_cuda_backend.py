from __future__ import annotations

import gdstk
import pytest

from scgds.ebeamtime.api import estimate_gds_write_time
from scgds.ebeamtime.config import EbeamLayerExposure, EstimateConfig, LayerSpec
from scgds.ebeamtime.native import discover_native_capabilities


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
