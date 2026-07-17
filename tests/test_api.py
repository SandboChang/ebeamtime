from __future__ import annotations

import json
import subprocess
import sys
import textwrap

import gdstk
import pytest

from ebeamtime.api import estimate_gds_write_time
from ebeamtime.config import EbeamLayerExposure, EstimateConfig, LayerSpec


def _write_gds(path, cell):
    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    lib.add(cell)
    lib.write_gds(str(path))
    return path


def _rect(x0, y0, x1, y1, *, layer=1, datatype=0):
    return gdstk.rectangle((x0, y0), (x1, y1), layer=layer, datatype=datatype)


def _config(path, *, backend="cpu", **kwargs):
    return EstimateConfig(
        gds_path=path,
        exposures=(
            EbeamLayerExposure(
                config_name="ld_rod",
                layer=LayerSpec(1, 0),
                dose_uC_cm2=100,
                beam_current_nA=1,
            ),
        ),
        backend=backend,
        **kwargs,
    )


def test_overlap_counts_raw_polygon_instance_area(tmp_path):
    cell = gdstk.Cell("top")
    cell.add(_rect(0, 0, 10, 10), _rect(0, 0, 10, 10))
    path = _write_gds(tmp_path / "overlap.gds", cell)
    result = estimate_gds_write_time(_config(path))
    layer = result.report.layers[0]
    assert layer.polygon_count == 2
    assert layer.area_um2 == pytest.approx(200.0)
    assert layer.beam_on_s == pytest.approx(0.2)


def test_hierarchy_repetition_and_paths_are_expanded(tmp_path):
    child = gdstk.Cell("child")
    child.add(_rect(0, 0, 10, 10))
    top = gdstk.Cell("top")
    top.add(gdstk.Reference(child, origin=(0, 0)))
    top.add(gdstk.Reference(child, origin=(20, 0)))
    top.add(gdstk.FlexPath([(0, 20), (10, 20)], 2, layer=1, datatype=0))
    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    lib.add(child, top)
    path = tmp_path / "hier.gds"
    lib.write_gds(str(path))
    result = estimate_gds_write_time(_config(path))
    layer = result.report.layers[0]
    assert layer.polygon_count == 3
    assert layer.area_um2 > 200.0


def test_writefield_indicator_and_outside_stage_movement(tmp_path):
    cell = gdstk.Cell("top")
    cell.add(_rect(0, 0, 10, 10))
    cell.add(_rect(100, 0, 110, 10))
    cell.add(_rect(-5, -5, 15, 15, layer=51))
    path = _write_gds(tmp_path / "fields.gds", cell)
    result = estimate_gds_write_time(
        _config(
            path,
            writefield_indicator_layer=LayerSpec(51, 0),
            stage_speed_mm_s=1.0,
        )
    )
    stage = result.report.stage
    assert stage.enabled
    assert stage.field_count == 2
    assert stage.indicator_field_count == 1
    assert stage.synthetic_field_count == 1
    assert stage.outside_indicator_polygon_count == 1
    assert stage.movement_distance_um == pytest.approx(100.0)
    assert stage.movement_s == pytest.approx(0.1)
    stage_json = stage.to_json()
    assert stage_json["movement_hr"] == pytest.approx(0.1 / 3600)
    assert stage_json["movement_days"] == pytest.approx(0.1 / 86400)
    assert stage_json["total_hr"] == pytest.approx(stage.total_s / 3600)
    assert stage_json["total_days"] == pytest.approx(stage.total_s / 86400)


def test_ignore_stage_suppresses_project_indicator_work(tmp_path):
    cell = gdstk.Cell("top")
    cell.add(_rect(0, 0, 10, 10))
    cell.add(_rect(-5, -5, 15, 15, layer=51))
    path = _write_gds(tmp_path / "ignore_stage.gds", cell)
    result = estimate_gds_write_time(
        _config(
            path,
            writefield_indicator_layer=LayerSpec(51, 0),
            ignore_stage=True,
        )
    )
    assert not result.report.stage.enabled
    assert result.report.total_s == pytest.approx(result.report.total_beam_on_s)


def test_synthetic_writefield_tiling_without_indicator(tmp_path):
    cell = gdstk.Cell("top")
    cell.add(_rect(0, 0, 10, 10))
    cell.add(_rect(60, 0, 70, 10))
    path = _write_gds(tmp_path / "tiles.gds", cell)
    result = estimate_gds_write_time(
        _config(
            path,
            max_write_field_um=(50, 50),
            stage_speed_mm_s=1.0,
        )
    )
    assert result.report.stage.field_count == 2
    assert result.report.stage.synthetic_field_count == 2
    assert result.report.stage.movement_distance_um == pytest.approx(50.0)


def test_cli_table_and_json_report(tmp_path):
    cell = gdstk.Cell("top")
    cell.add(_rect(0, 0, 10, 10))
    gds_path = _write_gds(tmp_path / "cli.gds", cell)
    config_path = tmp_path / "config.py"
    config_path.write_text(
        textwrap.dedent(
            """
            ld_rod = {"layer": 1, "datatype": 0}
            ebeamtime_layer_exposures = {
                "ld_rod": {"dose_uC_cm2": 100, "beam_current_nA": 1},
            }
            """
        ),
        encoding="utf-8",
    )
    json_path = tmp_path / "report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "ebeamtime",
            str(gds_path),
            "--project-config",
            str(config_path),
            "--backend",
            "cpu",
            "--json-report",
            str(json_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "status=estimated" in completed.stdout
    assert "total_days=" in completed.stdout
    assert "beam_on_hr" in completed.stdout
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["layers"][0]["area_um2"] == pytest.approx(100.0)
    assert report["layers"][0]["beam_on_hr"] == pytest.approx(report["layers"][0]["beam_on_s"] / 3600)
    assert report["layers"][0]["beam_on_days"] == pytest.approx(report["layers"][0]["beam_on_s"] / 86400)
    assert report["total_hr"] == pytest.approx(report["total_s"] / 3600)
    assert report["total_days"] == pytest.approx(report["total_s"] / 86400)
    assert report["total_beam_on_hr"] == pytest.approx(report["total_beam_on_s"] / 3600)
    assert report["total_stage_days"] == pytest.approx(report["total_stage_s"] / 86400)
    assert report["timings"]["total_hr"] == pytest.approx(report["timings"]["total_s"] / 3600)


def test_backend_auto_falls_back_to_cpu_for_small_layout(tmp_path, monkeypatch):
    cell = gdstk.Cell("top")
    cell.add(_rect(0, 0, 10, 10))
    path = _write_gds(tmp_path / "small.gds", cell)

    class Capabilities:
        cuda_available = True
        metal_available = False

    import ebeamtime.api as api_module

    monkeypatch.setattr(api_module, "discover_native_capabilities", lambda: Capabilities())
    result = estimate_gds_write_time(_config(path, backend="auto", gpu_min_polygons=999))
    assert result.report.backend["name"] == "cpu"
