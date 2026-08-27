"""Tests for electric_component_check.vcr_uncertainties.MeasurementError.

Uses the packaged vcr_uncertainties.json (via importlib.resources), so this
runs correctly regardless of the pytest invocation's cwd -- the previous
version hardcoded a relative path that only worked from inside src/.
"""

from __future__ import annotations

from importlib import resources

import pytest

from electric_component_check.vcr_uncertainties import MeasurementError


@pytest.fixture(scope="module")
def m_error() -> MeasurementError:
    with resources.as_file(
        resources.files("electric_component_check") / "vcr_uncertainties.json"
    ) as spec_path:
        return MeasurementError(spec_path)


def test_uncertainty_capacitance(m_error):
    uC, uD, r = m_error.uncertainty_capacitance(1e-6, 10000, 0.01, 0.005)
    assert isinstance(uC, float)
    assert isinstance(uD, float)
    assert isinstance(r, dict)


def test_uncertainty_inductance(m_error):
    uL, uD, r = m_error.uncertainty_inductance(1e-3, 4000, 0.02, 0.01)
    assert isinstance(uL, float)
    assert isinstance(uD, float)
    assert isinstance(r, dict)


def test_uncertainty_impedance(m_error):
    uZ, uTh, r = m_error.uncertainty_impedance(100, 100, 0.05, 0.1)
    assert isinstance(uZ, float)
    assert isinstance(uTh, float)
    assert isinstance(r, dict)


def test_uncertainty_q_from_d(m_error):
    blk = m_error.select_block("capacitance", 10000)
    r, _ = m_error.match_range(blk, 1e-6)
    uq = m_error.uncertainty_Q_from_D(0.5, r, 0.01)
    assert isinstance(uq, float)


def test_find_equiv_mode(m_error):
    equiv = m_error.find_equiv_mode("capacitance", 1e-6, 10000)
    assert isinstance(equiv, str)


def test_value_outside_all_ranges_raises(m_error):
    with pytest.raises(ValueError):
        m_error.uncertainty_capacitance(1.0, 10000)  # 1 F is absurdly out of range
