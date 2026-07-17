from __future__ import annotations

import importlib
import json
import math
import sys
from importlib.resources import files
from importlib.metadata import version
from types import ModuleType

import gdstk
import numpy as np
import pytest
import jsonschema

import ebeamtime.api as api_module
from ebeamtime import (
    __version__,
    EbeamLayerExposure,
    EstimateConfig,
    LayerSpec,
    backend_diagnostics,
    estimate_gds_write_time,
    load_project_config,
    load_project_estimate_config,
    validate_report_dict,
)


def _exposure(layer: int = 1) -> tuple[EbeamLayerExposure, ...]:
    return (EbeamLayerExposure("ld_expose", LayerSpec(layer, 0), 100.0, 1.0),)


def _write(path, *cells, unit=1e-6, precision=1e-9):
    library = gdstk.Library(unit=unit, precision=precision)
    library.add(*cells)
    library.write_gds(str(path))
    return path


def test_multiple_tops_require_explicit_selection(tmp_path):
    first = gdstk.Cell("first")
    first.add(gdstk.rectangle((0, 0), (10, 10), layer=1))
    second = gdstk.Cell("second")
    second.add(gdstk.rectangle((0, 0), (20, 10), layer=1))
    path = _write(tmp_path / "multiple.gds", first, second)

    with pytest.raises(ValueError, match="top"):
        estimate_gds_write_time(EstimateConfig(path, _exposure(), backend="cpu"))

    result = estimate_gds_write_time(EstimateConfig(path, _exposure(), top="second", backend="cpu"))
    assert result.report.top_name == "second"
    assert result.report.layers[0].area_um2 == pytest.approx(200.0)


@pytest.mark.parametrize(
    ("unit", "precision", "side", "expected_um2"),
    [(1e-6, 1e-9, 10.0, 100.0), (1e-3, 1e-9, 0.01, 100.0), (1e-6, 1e-8, 10.0, 100.0)],
)
def test_gds_units_and_precision_preserve_physical_area(tmp_path, unit, precision, side, expected_um2):
    cell = gdstk.Cell("top")
    cell.add(gdstk.rectangle((0, 0), (side, side), layer=1))
    path = _write(tmp_path / "units.gds", cell, unit=unit, precision=precision)
    result = estimate_gds_write_time(EstimateConfig(path, _exposure(), backend="cpu"))
    assert result.report.layers[0].area_um2 == pytest.approx(expected_um2)


def test_absent_exposure_layer_reports_zero(tmp_path):
    cell = gdstk.Cell("top")
    cell.add(gdstk.rectangle((0, 0), (10, 10), layer=2))
    path = _write(tmp_path / "empty-layer.gds", cell)
    layer = estimate_gds_write_time(EstimateConfig(path, _exposure(1), backend="cpu")).report.layers[0]
    assert layer.polygon_count == 0
    assert layer.area_um2 == 0.0
    assert layer.beam_on_s == 0.0


def test_extraction_buffer_is_forwarded_to_aggregation_by_identity(tmp_path, monkeypatch):
    cell = gdstk.Cell("top")
    cell.add(gdstk.rectangle((0, 0), (10, 10), layer=1))
    path = _write(tmp_path / "identity.gds", cell)
    seen = {}
    real_extract = api_module.extract_estimation_geometry
    real_aggregate = api_module._aggregate_area

    def capture_extract(config):
        geometry = real_extract(config)
        seen["extracted"] = geometry.buffer
        return geometry

    def capture_aggregate(config, buffer, exposure_ids):
        seen["aggregated"] = buffer
        return real_aggregate(config, buffer, exposure_ids)

    monkeypatch.setattr(api_module, "extract_estimation_geometry", capture_extract)
    monkeypatch.setattr(api_module, "_aggregate_area", capture_aggregate)
    estimate_gds_write_time(EstimateConfig(path, _exposure(), backend="cpu"))
    assert seen["aggregated"] is seen["extracted"]


def test_auto_backend_runtime_failure_falls_back_but_required_gpu_raises(tmp_path, monkeypatch):
    cell = gdstk.Cell("top")
    cell.add(gdstk.rectangle((0, 0), (10, 10), layer=1))
    path = _write(tmp_path / "fallback.gds", cell)

    class FailingBackend:
        def aggregate(self, *args):
            raise RuntimeError("simulated GPU failure")

        def capabilities(self):
            return type("Capabilities", (), {"name": "cuda"})()

    monkeypatch.setattr(api_module, "_select_backend", lambda config, polygon_count: FailingBackend())
    result = estimate_gds_write_time(EstimateConfig(path, _exposure(), backend="auto"))
    assert result.report.backend["name"] == "cpu"
    assert result.report.backend["details"]["fallback_reason"] == "simulated GPU failure"

    with pytest.raises(RuntimeError, match="simulated GPU failure"):
        estimate_gds_write_time(EstimateConfig(path, _exposure(), backend="auto", require_gpu=True))


def test_exact_writefield_boundary_does_not_create_extra_tile(tmp_path):
    cell = gdstk.Cell("top")
    cell.add(gdstk.rectangle((0, 0), (50, 10), layer=1))
    path = _write(tmp_path / "boundary.gds", cell)
    result = estimate_gds_write_time(
        EstimateConfig(path, _exposure(), backend="cpu", max_write_field_um=(50, 50))
    )
    assert result.report.stage.field_count == 1


def test_project_config_accepts_module_path_and_import_name(tmp_path, monkeypatch):
    body = (
        'ld_expose = {"layer": 1, "datatype": 0}\n'
        'ebeamtime_layer_exposures = {"ld_expose": {"dose_uC_cm2": 100, "beam_current_nA": 1}}\n'
    )
    path = tmp_path / "example_config.py"
    path.write_text(body, encoding="utf-8")
    module = ModuleType("object_config")
    exec(body, module.__dict__)

    assert load_project_config(path).ld_expose["layer"] == 1
    assert load_project_config(module) is module
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("example_config", None)
    assert load_project_config("example_config").ld_expose["layer"] == 1
    assert load_project_estimate_config(module, gds_path="dummy.gds").exposures[0].layer == LayerSpec(1, 0)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_process_values_are_rejected(value):
    with pytest.raises(ValueError):
        EbeamLayerExposure("bad", LayerSpec(1, 0), value, 1.0)
    with pytest.raises(ValueError):
        EbeamLayerExposure("bad", LayerSpec(1, 0), 100.0, value)
    with pytest.raises(ValueError):
        EstimateConfig("dummy.gds", _exposure(), stage_settle_s=value)


def test_report_schema_and_cpu_safe_diagnostics(tmp_path):
    cell = gdstk.Cell("top")
    cell.add(gdstk.rectangle((0, 0), (10, 10), layer=1))
    path = _write(tmp_path / "report.gds", cell)
    report = estimate_gds_write_time(EstimateConfig(path, _exposure(), backend="cpu")).report.to_json_dict()
    validate_report_dict(report)
    schema = json.loads(files("ebeamtime").joinpath("schemas/ebeamtime-report-v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(report, schema)
    assert report["schema_version"] == "ebeamtime-report-v1"
    diagnostics = backend_diagnostics()
    assert diagnostics["capabilities"]["cpu_available"] is True
    assert diagnostics["native_cache"]["environment"] == "EBEAMTIME_NATIVE_CACHE_DIR"


def test_report_version_matches_installed_distribution():
    assert __version__ == version("ebeamtime")


def test_cpu_backend_cannot_claim_gpu_requirement():
    with pytest.raises(ValueError, match="conflicts"):
        EstimateConfig("dummy.gds", _exposure(), backend="cpu", require_gpu=True)


def test_small_auto_workload_does_not_probe_native_backends(tmp_path, monkeypatch):
    cell = gdstk.Cell("top")
    cell.add(gdstk.rectangle((0, 0), (10, 10), layer=1))
    path = _write(tmp_path / "small-auto.gds", cell)

    def unexpected_probe():
        raise AssertionError("small AUTO workload must not probe or compile native backends")

    monkeypatch.setattr(api_module, "discover_native_capabilities", unexpected_probe)
    result = estimate_gds_write_time(EstimateConfig(path, _exposure(), backend="auto", gpu_min_polygons=2))
    assert result.report.backend["name"] == "cpu"
