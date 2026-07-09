from __future__ import annotations

import textwrap

import pytest

from scgds.ebeamtime.config import LayerSpec, load_project_estimate_config


def _write_config(tmp_path, body: str):
    path = tmp_path / "config.py"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_project_config_resolves_layer_names_without_touching_ld_dicts(tmp_path):
    path = _write_config(
        tmp_path,
        """
        ld_rod = {"layer": 1, "datatype": 0}
        ld_wf = {"layer": 51, "datatype": 0}
        ebeamtime_layer_exposures = {
            "ld_rod": {"dose_uC_cm2": 100, "beam_current_nA": 1},
        }
        ebeamtime_writefield_indicator_layer = "ld_wf"
        """,
    )
    config = load_project_estimate_config(path, gds_path=tmp_path / "dummy.gds")
    assert config.exposures[0].config_name == "ld_rod"
    assert config.exposures[0].layer == LayerSpec(1, 0)
    assert config.writefield_indicator_layer == LayerSpec(51, 0)


def test_project_config_rejects_missing_layer_name(tmp_path):
    path = _write_config(
        tmp_path,
        """
        ebeamtime_layer_exposures = {
            "ld_missing": {"dose_uC_cm2": 100, "beam_current_nA": 1},
        }
        """,
    )
    with pytest.raises(ValueError, match="ld_missing"):
        load_project_estimate_config(path, gds_path=tmp_path / "dummy.gds")


@pytest.mark.parametrize(
    "entry",
    [
        '{"beam_current_nA": 1}',
        '{"dose_uC_cm2": 100}',
        '{"dose_uC_cm2": 100, "beam_current_nA": 0}',
    ],
)
def test_project_config_rejects_missing_or_invalid_dose_current(tmp_path, entry):
    path = _write_config(
        tmp_path,
        f"""
        ld_rod = {{"layer": 1, "datatype": 0}}
        ebeamtime_layer_exposures = {{"ld_rod": {entry}}}
        """,
    )
    with pytest.raises(ValueError):
        load_project_estimate_config(path, gds_path=tmp_path / "dummy.gds")
