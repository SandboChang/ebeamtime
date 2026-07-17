from __future__ import annotations

import math


def beam_on_seconds(area_um2: float, dose_uC_cm2: float, beam_current_nA: float) -> float:
    """Return beam-on exposure time for area, dose, and beam current.

    Unit identity:
    1 um^2 = 1e-8 cm^2, 1 uC = 1e-6 C, and 1 nA = 1e-9 C/s,
    therefore seconds = area_um2 * dose_uC_cm2 * 1e-5 / beam_current_nA.
    """

    if not math.isfinite(area_um2) or area_um2 < 0:
        raise ValueError("area_um2 must be nonnegative")
    if not math.isfinite(dose_uC_cm2) or dose_uC_cm2 <= 0:
        raise ValueError("dose_uC_cm2 must be positive")
    if not math.isfinite(beam_current_nA) or beam_current_nA <= 0:
        raise ValueError("beam_current_nA must be positive")
    return float(area_um2) * float(dose_uC_cm2) * 1e-5 / float(beam_current_nA)


def estimate_from_area(area_um2: float, dose_uC_cm2: float, beam_current_nA: float) -> float:
    return beam_on_seconds(area_um2, dose_uC_cm2, beam_current_nA)
