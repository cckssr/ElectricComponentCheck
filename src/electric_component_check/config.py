"""Application configuration: OpenBIS target, dataset schema, sweep parameters.

Resolved from a TOML file, overlaid on the shipped default so a user config
only needs to state what differs. Search order (first match wins):

1. ``$ECC_CONFIG`` -- an explicit path
2. ``./ecc.toml`` -- convenient for running from a repo checkout
3. the OS user-config directory (``platformdirs.user_config_dir``)

Nothing in this application writes the config back, so it is read with the
stdlib ``tomllib`` rather than a round-tripping TOML library.
"""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

import platformdirs

APP_NAME = "ElectricComponentCheck"
APP_AUTHOR = "TU-Berlin"

# The LCR-500 accepts exactly these two drive levels (see voltcraft_lcr500.py
# _LEVELS_MVRMS); anything else is a config authoring error, not a runtime one.
_ALLOWED_VOLTAGE_LEVELS_MV = frozenset({300, 600})

_KNOWN_COMPONENTS = ("capacitor", "inductor", "resistor")


class ConfigError(Exception):
    """Invalid or missing configuration. The message names the dotted key."""


@dataclass(frozen=True, slots=True)
class ReferencePoint:
    frequency_hz: int
    level_mv: int


@dataclass(frozen=True, slots=True)
class OpenBISTarget:
    collection: str
    space: str
    project: str


@dataclass(frozen=True, slots=True)
class DatasetConfig:
    type: str
    lab_name: str
    lab_property: str
    date_property: str
    device_property: str


@dataclass(frozen=True, slots=True)
class MeasurementPropertyConfig:
    value: str
    uncertainty: str
    unit: str
    date: str


@dataclass(frozen=True, slots=True)
class MeasurementConfig:
    frequencies_hz: tuple[int, ...]
    voltage_levels_mv: tuple[int, ...]
    reference: Mapping[str, ReferencePoint]


@dataclass(frozen=True, slots=True)
class AppConfig:
    source_path: Path | None
    server_url: str
    object_type: str
    target: OpenBISTarget
    general_properties: Mapping[str, str]
    measurement_properties: MeasurementPropertyConfig
    dataset: DatasetConfig
    measurement: MeasurementConfig
    keep_last_type: bool

    def reference_for(self, component: str) -> ReferencePoint:
        try:
            return self.measurement.reference[component]
        except KeyError as exc:
            raise ConfigError(
                f"measurement.reference.{component}: no reference point configured"
            ) from exc


def config_search_paths() -> list[Path]:
    """Candidate config file locations, in priority order."""
    paths: list[Path] = []
    env_path = os.environ.get("ECC_CONFIG")
    if env_path:
        paths.append(Path(env_path))
    paths.append(Path.cwd() / "ecc.toml")
    paths.append(Path(platformdirs.user_config_dir(APP_NAME, APP_AUTHOR)) / "config.toml")
    return paths


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_default() -> dict[str, Any]:
    with resources.files(__package__).joinpath("default_config.toml").open("rb") as f:
        return tomllib.load(f)


def _supported_frequencies_hz() -> set[int]:
    """Every frequency vcr_uncertainties.json specifies, across all measurands."""
    with resources.files(__package__).joinpath("vcr_uncertainties.json").open("rb") as f:
        spec = json.load(f)
    freqs: set[int] = set()
    for blocks in spec.values():
        for block in blocks.values():
            freqs.update(int(f) for f in block.get("freqs_Hz", []))
    return freqs


def _require(data: dict[str, Any], key_path: str) -> Any:
    node: Any = data
    for part in key_path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise ConfigError(f"{key_path}: missing required key")
        node = node[part]
    return node


def _require_str(data: dict[str, Any], key_path: str, *, allow_empty: bool = False) -> str:
    value = _require(data, key_path)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ConfigError(f"{key_path}: expected a non-empty string, got {value!r}")
    return value


def _build_config(data: dict[str, Any], source_path: Path | None) -> AppConfig:
    server_url = _require_str(data, "openbis.url")
    if not server_url.startswith("https://"):
        raise ConfigError(f"openbis.url: must start with https://, got {server_url!r}")

    object_type = _require_str(data, "openbis.object_type")

    target = OpenBISTarget(
        collection=_require_str(data, "openbis.target.collection", allow_empty=True),
        space=_require_str(data, "openbis.target.space", allow_empty=True),
        project=_require_str(data, "openbis.target.project", allow_empty=True),
    )

    general_properties = {
        key: _require_str(data, f"openbis.general_properties.{key}")
        for key in _require(data, "openbis.general_properties")
    }

    measurement_properties = MeasurementPropertyConfig(
        value=_require_str(data, "openbis.measurement_properties.value"),
        uncertainty=_require_str(data, "openbis.measurement_properties.uncertainty"),
        unit=_require_str(data, "openbis.measurement_properties.unit"),
        date=_require_str(data, "openbis.measurement_properties.date"),
    )

    dataset = DatasetConfig(
        type=_require_str(data, "openbis.dataset.type"),
        lab_name=_require_str(data, "openbis.dataset.lab_name"),
        lab_property=_require_str(data, "openbis.dataset.lab_property"),
        date_property=_require_str(data, "openbis.dataset.date_property"),
        device_property=_require_str(data, "openbis.dataset.device_property"),
    )

    frequencies_hz = tuple(int(f) for f in _require(data, "measurement.frequencies_hz"))
    if not frequencies_hz:
        raise ConfigError("measurement.frequencies_hz: must not be empty")
    supported = _supported_frequencies_hz()
    unsupported = [f for f in frequencies_hz if f not in supported]
    if unsupported:
        raise ConfigError(
            f"measurement.frequencies_hz: {unsupported} are not specified in "
            f"vcr_uncertainties.json (supported: {sorted(supported)})"
        )

    voltage_levels_mv = tuple(int(v) for v in _require(data, "measurement.voltage_levels_mv"))
    if not voltage_levels_mv:
        raise ConfigError("measurement.voltage_levels_mv: must not be empty")
    bad_levels = [v for v in voltage_levels_mv if v not in _ALLOWED_VOLTAGE_LEVELS_MV]
    if bad_levels:
        raise ConfigError(
            f"measurement.voltage_levels_mv: {bad_levels} unsupported by the LCR-500 "
            f"(allowed: {sorted(_ALLOWED_VOLTAGE_LEVELS_MV)})"
        )

    reference: dict[str, ReferencePoint] = {}
    for component in _KNOWN_COMPONENTS:
        key_path = f"measurement.reference.{component}"
        freq = int(_require(data, f"{key_path}.frequency_hz"))
        level = int(_require(data, f"{key_path}.level_mv"))
        if freq not in frequencies_hz:
            raise ConfigError(
                f"{key_path}.frequency_hz: {freq} is not in measurement.frequencies_hz"
            )
        if level not in voltage_levels_mv:
            raise ConfigError(
                f"{key_path}.level_mv: {level} is not in measurement.voltage_levels_mv"
            )
        reference[component] = ReferencePoint(frequency_hz=freq, level_mv=level)

    measurement = MeasurementConfig(
        frequencies_hz=frequencies_hz,
        voltage_levels_mv=voltage_levels_mv,
        reference=reference,
    )

    keep_last_type = bool(_require(data, "ui.keep_last_type"))

    return AppConfig(
        source_path=source_path,
        server_url=server_url,
        object_type=object_type,
        target=target,
        general_properties=general_properties,
        measurement_properties=measurement_properties,
        dataset=dataset,
        measurement=measurement,
        keep_last_type=keep_last_type,
    )


def load_config(path: Path | None = None) -> AppConfig:
    """Load and validate the app config, overlaying a user file on the shipped default.

    Args:
        path: Explicit config file to overlay. If None, the first existing
            file from config_search_paths() is used (or just the default,
            if none exist).
    """
    merged = _load_default()

    source_path = path
    if source_path is None:
        for candidate in config_search_paths():
            if candidate.is_file():
                source_path = candidate
                break

    if source_path is not None:
        with open(source_path, "rb") as f:
            override = tomllib.load(f)
        merged = _deep_merge(merged, override)

    return _build_config(merged, source_path)


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Cached app config -- loaded once per process."""
    return load_config()


def reload_config() -> AppConfig:
    """Clear the cache and reload the config (e.g. after the user edits it)."""
    get_config.cache_clear()
    return get_config()
