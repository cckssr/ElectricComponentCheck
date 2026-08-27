"""Tests for electric_component_check.measurement_summary."""

from __future__ import annotations

from electric_component_check.config import MeasurementPropertyConfig, ReferencePoint
from electric_component_check.measurement_summary import (
    summarise,
    to_dataframe,
    to_openbis_properties,
)

MEASUREMENT_PROPS = MeasurementPropertyConfig(
    value="equipment.measurement_value",
    uncertainty="equipment.measurement_uncert",
    unit="equipment.measurement_unit",
    date="equipment.measurement_date",
)


def make_point(freq_hz, level_mv, primary, secondary, *, u_primary=0.0, u_secondary=0.0):
    return {
        "timestamp": "2026-08-27T10:00:00",
        "frequency_hz": freq_hz,
        "level_mv": level_mv,
        "voltage_v": level_mv / 1000.0,
        "primary_name": "C",
        "primary_value": primary,
        "primary_uncertainty": u_primary,
        "secondary_name": "D",
        "secondary_value": secondary,
        "secondary_uncertainty": u_secondary,
    }


def golden_sweep():
    """10 freqs x 2 levels, capacitor-shaped, 1kHz/600mV is the configured reference."""
    freqs = [100, 120, 400, 1000, 4000, 10000, 40000, 50000, 75000, 100000]
    results = []
    for level in (300, 600):
        for f in freqs:
            # Slight, deterministic variation so min/max aren't degenerate.
            value = 1e-6 * (1.0 + 0.001 * (f % 7))
            results.append(make_point(f, level, value, 0.02, u_primary=1e-9))
    return results


def test_golden_sweep_picks_exact_reference_point():
    ref = ReferencePoint(frequency_hz=1000, level_mv=600)
    summary = summarise(golden_sweep(), "capacitor", ref, expected=20)

    assert summary.reference_exact is True
    assert summary.reference_frequency_hz == 1000
    assert summary.reference_level_mv == 600
    assert summary.primary_value == 1e-6 * (1.0 + 0.001 * (1000 % 7))
    assert summary.n_points == 20
    assert summary.n_expected == 20
    assert summary.primary_min is not None
    assert summary.primary_max is not None
    assert summary.primary_min <= summary.primary_value <= summary.primary_max


def test_missing_exact_point_falls_back_to_nearest_log_frequency():
    results = [
        make_point(100, 600, 1e-6, 0.01),
        make_point(4000, 600, 2e-6, 0.01),  # nearest to 1000 in log space among these two
        make_point(100, 300, 5e-6, 0.01),
    ]
    ref = ReferencePoint(frequency_hz=1000, level_mv=600)
    summary = summarise(results, "capacitor", ref)

    assert summary.reference_exact is False
    assert summary.reference_level_mv == 600
    assert summary.primary_value == 2e-6  # 4000Hz is closer to 1000Hz in log10 than 100Hz


def test_missing_level_falls_back_across_levels():
    results = [make_point(1000, 300, 3e-6, 0.01)]
    ref = ReferencePoint(frequency_hz=1000, level_mv=600)
    summary = summarise(results, "capacitor", ref)

    assert summary.reference_exact is False
    assert summary.reference_level_mv == 300
    assert summary.primary_value == 3e-6


def test_empty_sweep_never_fabricates_a_value():
    ref = ReferencePoint(frequency_hz=1000, level_mv=600)
    summary = summarise([], "capacitor", ref)

    assert summary.primary_value is None
    assert summary.primary_uncertainty is None
    assert summary.n_points == 0
    assert summary.reference_exact is False
    # The requested reference point is still recorded even with no data.
    assert summary.reference_frequency_hz == 1000
    assert summary.reference_level_mv == 600


def test_invalid_points_are_dropped():
    results = [
        make_point(1000, 600, 1e-6, 0.01),
        {**make_point(2000, 600, 1e30, 0.01), "primary_value": 1e60},  # absurd, dropped
        {**make_point(3000, 600, 1e-6, 0.01), "secondary_value": None},  # incomplete, dropped
    ]
    ref = ReferencePoint(frequency_hz=1000, level_mv=600)
    summary = summarise(results, "capacitor", ref)

    assert summary.n_points == 1


def test_to_openbis_properties_scales_capacitance_to_microfarad():
    ref = ReferencePoint(frequency_hz=1000, level_mv=600)
    summary = summarise([make_point(1000, 600, 4.7e-6, 0.02, u_primary=5e-9)], "capacitor", ref)
    props = to_openbis_properties(summary, MEASUREMENT_PROPS)

    assert props["equipment.measurement_unit"] == "MICROFARAD"
    assert props["equipment.measurement_value"] == 4.7
    assert abs(props["equipment.measurement_uncert"] - 0.005) < 1e-9
    assert props["equipment.measurement_date"] == summary.measured_at


def test_to_openbis_properties_bare_ohm_at_unity_scale():
    point = make_point(100, 600, 470.0, 0.0)
    point["primary_name"] = "Z"
    ref = ReferencePoint(frequency_hz=100, level_mv=600)
    summary = summarise([point], "resistor", ref)
    props = to_openbis_properties(summary, MEASUREMENT_PROPS)

    assert props["equipment.measurement_unit"] == "OHM"
    assert props["equipment.measurement_value"] == 470.0


def test_to_openbis_properties_empty_when_no_value():
    ref = ReferencePoint(frequency_hz=1000, level_mv=600)
    summary = summarise([], "capacitor", ref)
    assert to_openbis_properties(summary, MEASUREMENT_PROPS) == {}


def test_dataframe_column_order_is_fixed_for_positional_readers():
    df = to_dataframe(golden_sweep()[:2], "C", "D")
    assert list(df.columns) == [
        "timestamp",
        "freq_hz",
        "level_v",
        "equiv",
        "C",
        "D",
        "u_primary",
        "u_secondary",
        "range_name",
    ]
    # MeasurementPlotter reads columns[4]/columns[5] positionally.
    assert df.columns[4] == "C"
    assert df.columns[5] == "D"
