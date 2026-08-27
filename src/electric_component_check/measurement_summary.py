"""Reduces a full LCR sweep to the scalar values written to OpenBIS, plus the
DataFrame shape report_generator/plot_measurement expect.

Pure module: no Qt, no pybis, so it is unit-testable without hardware or a
server. Keep it that way -- GUI/network concerns belong in the callers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .config import MeasurementPropertyConfig, ReferencePoint

# SI prefix factor -> vocabulary prefix name, ascending. Matches the UNITS
# vocabulary on ELEKTRONISCHES_BAUTEIL (see docs/openbis-object-types.xlsx):
# terms are named {PREFIX}{FULL_UNIT_NAME}, e.g. MICROFARAD, KILOOHM.
_SI_PREFIXES: tuple[tuple[float, str], ...] = (
    (1e-12, "PICO"),
    (1e-9, "NANO"),
    (1e-6, "MICRO"),
    (1e-3, "MILLI"),
    (1.0, ""),
    (1e3, "KILO"),
    (1e6, "MEGA"),
    (1e9, "GIGA"),
)

# lcr_controller.component_to_meastype()'s primary_name -> base SI unit code.
_BASE_UNIT_SYMBOL = {"C": "F", "L": "H", "Z": "OHM"}
_BASE_UNIT_NAME = {"F": "FARAD", "H": "HENRY", "OHM": "OHM"}


@dataclass(frozen=True, slots=True)
class SweepSummary:
    """Scalar summary of one component sweep, reduced to a single reference point."""

    component: str
    primary_name: str
    secondary_name: str
    reference_frequency_hz: int
    reference_level_mv: int
    reference_exact: bool  # False if no point matched the reference exactly
    primary_value: float | None
    primary_uncertainty: float | None
    secondary_value: float | None
    secondary_uncertainty: float | None
    primary_min: float | None
    primary_max: float | None
    n_points: int
    n_expected: int
    measured_at: str  # "YYYY-MM-DD"
    instrument_id: str | None
    calibration_open: bool
    calibration_short: bool


def _valid_points(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drops points with missing or absurd values (mirrors measure_sweep's own filter)."""
    valid = []
    for r in results:
        primary, secondary = r.get("primary_value"), r.get("secondary_value")
        if primary is None or secondary is None:
            continue
        if abs(primary) >= 1e50 or abs(secondary) >= 1e50:
            continue
        valid.append(r)
    return valid


def _nearest_by_log_frequency(points: list[dict[str, Any]], target_freq_hz: int) -> dict[str, Any]:
    def distance(point: dict[str, Any]) -> float:
        freq = point["frequency_hz"]
        if freq <= 0 or target_freq_hz <= 0:
            return abs(freq - target_freq_hz)
        return abs(math.log10(freq) - math.log10(target_freq_hz))

    return min(points, key=distance)


def summarise(
    results: list[dict[str, Any]],
    component: str,
    ref: ReferencePoint,
    *,
    expected: int | None = None,
    instrument_id: str | None = None,
    calibration_open: bool = False,
    calibration_short: bool = False,
    measured_at: str | None = None,
) -> SweepSummary:
    """Reduces a sweep to its reference-point value plus a few sanity stats.

    Picks the point matching ``ref`` exactly if present. Otherwise falls back
    to the measured point nearest ``ref.frequency_hz`` in log-frequency space,
    preferring points at ``ref.level_mv`` before considering other levels.
    Never fabricates a value -- if no points were measured at all, every
    numeric field is None and the caller (to_openbis_properties) skips writing
    anything rather than guess.
    """
    points = _valid_points(results)
    n_expected = expected if expected is not None else len(results)
    measured_at = measured_at or datetime.now().strftime("%Y-%m-%d")

    primary_name = points[0]["primary_name"] if points else ""
    secondary_name = points[0]["secondary_name"] if points else ""

    reference_point: dict[str, Any] | None = None
    reference_exact = False
    reference_level_mv = ref.level_mv

    exact = [
        p
        for p in points
        if p["frequency_hz"] == ref.frequency_hz and p.get("level_mv") == ref.level_mv
    ]
    if exact:
        reference_point = exact[0]
        reference_exact = True
    else:
        at_level = [p for p in points if p.get("level_mv") == ref.level_mv]
        candidates = at_level or points
        if candidates:
            reference_point = _nearest_by_log_frequency(candidates, ref.frequency_hz)
            reference_level_mv = reference_point.get("level_mv", ref.level_mv)

    primary_values = [p["primary_value"] for p in points]

    return SweepSummary(
        component=component,
        primary_name=primary_name,
        secondary_name=secondary_name,
        reference_frequency_hz=ref.frequency_hz,
        reference_level_mv=reference_level_mv,
        reference_exact=reference_exact,
        primary_value=reference_point["primary_value"] if reference_point else None,
        primary_uncertainty=(
            reference_point.get("primary_uncertainty") if reference_point else None
        ),
        secondary_value=reference_point["secondary_value"] if reference_point else None,
        secondary_uncertainty=(
            reference_point.get("secondary_uncertainty") if reference_point else None
        ),
        primary_min=min(primary_values) if primary_values else None,
        primary_max=max(primary_values) if primary_values else None,
        n_points=len(points),
        n_expected=n_expected,
        measured_at=measured_at,
        instrument_id=instrument_id,
        calibration_open=calibration_open,
        calibration_short=calibration_short,
    )


def _auto_scale_unit(value_si: float, base_symbol: str) -> tuple[float, float, str]:
    """Scales an SI value into the nicest UNITS vocabulary term.

    Returns (scaled_value, scale_factor, vocabulary_term). The base-scale term
    is the bare symbol (e.g. "OHM"); prefixed terms are {PREFIX}{FULL_NAME}
    (e.g. "MICROFARAD"), matching the server's UNITS vocabulary exactly.
    """
    if not base_symbol:
        return value_si, 1.0, ""

    base_name = _BASE_UNIT_NAME.get(base_symbol, base_symbol)
    abs_value = abs(value_si)
    factor, prefix = 1.0, ""
    for f, p in _SI_PREFIXES:
        if abs_value >= f:
            factor, prefix = f, p

    term = f"{prefix}{base_name}" if prefix else base_symbol
    return value_si / factor, factor, term


def to_openbis_properties(
    summary: SweepSummary, measurement_properties: MeasurementPropertyConfig
) -> dict[str, Any]:
    """Maps a summary onto the EQUIPMENT.MEASUREMENT_* property quartet.

    One universal set of four properties for every component type (there is
    no per-measurand slot on ELEKTRONISCHES_BAUTEIL) -- see
    docs/openbis-object-types.xlsx, section "Messung". Returns {} if there is
    no reference value to write.
    """
    if summary.primary_value is None:
        return {}

    base_symbol = _BASE_UNIT_SYMBOL.get(summary.primary_name, "")
    scaled_value, factor, unit_term = _auto_scale_unit(summary.primary_value, base_symbol)

    props: dict[str, Any] = {
        measurement_properties.value: scaled_value,
        measurement_properties.date: summary.measured_at,
    }
    if unit_term:
        props[measurement_properties.unit] = unit_term
    if summary.primary_uncertainty is not None:
        props[measurement_properties.uncertainty] = summary.primary_uncertainty / factor
    return props


def to_dataframe(
    results: list[dict[str, Any]], primary_name: str, secondary_name: str
) -> pd.DataFrame:
    """Builds the DataFrame report_generator.MeasurementReport / MeasurementPlotter expect.

    Column order is LOAD-BEARING: MeasurementPlotter reads the primary/secondary
    measurand columns *positionally* (columns[4], columns[5] -- see
    plot_measurement.py), so this order must never change without updating that
    reader too. "equiv"/"range_name" are placeholders today -- the live sweep
    does not yet select or record an equivalent-circuit mode per point (that
    logic exists only in the retired lcr_testing.py and hasn't been ported into
    the live controller).
    """
    rows = [
        {
            "timestamp": r.get("timestamp"),
            "freq_hz": r.get("frequency_hz"),
            "level_v": r.get("voltage_v"),
            "equiv": r.get("equiv", ""),
            primary_name: r.get("primary_value"),
            secondary_name: r.get("secondary_value"),
            "u_primary": r.get("primary_uncertainty"),
            "u_secondary": r.get("secondary_uncertainty"),
            "range_name": r.get("range_name", ""),
        }
        for r in results
    ]
    columns = [
        "timestamp",
        "freq_hz",
        "level_v",
        "equiv",
        primary_name,
        secondary_name,
        "u_primary",
        "u_secondary",
        "range_name",
    ]
    return pd.DataFrame(rows, columns=columns)


def write_csv(df: pd.DataFrame, path: Path) -> Path:
    """Writes the sweep DataFrame to CSV, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path
