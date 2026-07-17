from __future__ import annotations

import pytest

from ebeamtime.units import beam_on_seconds


def test_beam_on_formula_lab_units():
    assert beam_on_seconds(1_000_000, 100, 1) == pytest.approx(1000.0)


@pytest.mark.parametrize(
    ("area", "dose", "current"),
    [
        (-1, 100, 1),
        (1, 0, 1),
        (1, 100, 0),
        (float("nan"), 100, 1),
        (1, float("inf"), 1),
        (1, 100, float("nan")),
    ],
)
def test_beam_on_formula_rejects_invalid_values(area, dose, current):
    with pytest.raises(ValueError):
        beam_on_seconds(area, dose, current)
