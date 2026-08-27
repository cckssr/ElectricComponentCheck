"""Tests for electric_component_check.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from electric_component_check.config import ConfigError, load_config


def write_toml(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "ecc.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_default_config_loads_and_validates():
    cfg = load_config()
    assert cfg.server_url == "https://openbis.physik.tu-berlin.de"
    assert cfg.object_type == "ELEKTRONISCHES_BAUTEIL"
    assert cfg.dataset.type == "CALI_CERT"
    assert cfg.measurement.voltage_levels_mv == (300, 600)
    assert cfg.reference_for("capacitor").frequency_hz == 1000
    assert cfg.reference_for("inductor").frequency_hz == 10000
    assert cfg.reference_for("resistor").frequency_hz == 100


def test_user_file_overlays_only_what_it_sets(tmp_path):
    path = write_toml(
        tmp_path,
        """
        [openbis.target]
        collection = "/SPACE/PROJECT/COLLECTION"
        """,
    )
    cfg = load_config(path)
    assert cfg.target.collection == "/SPACE/PROJECT/COLLECTION"
    # everything else still comes from the shipped default
    assert cfg.server_url == "https://openbis.physik.tu-berlin.de"
    assert cfg.dataset.lab_name == "TU Berlin"
    assert cfg.source_path == path


def test_missing_file_is_reported_by_open(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "does-not-exist.toml")


@pytest.mark.parametrize(
    "override,message_fragment",
    [
        ('[openbis]\nurl = "http://insecure"', "must start with https://"),
        ("[measurement]\nvoltage_levels_mv = [900]", "unsupported by the LCR-500"),
        ("[measurement]\nfrequencies_hz = [123456]", "not specified in vcr_uncertainties.json"),
        ("[measurement]\nvoltage_levels_mv = []", "must not be empty"),
    ],
)
def test_invalid_config_raises_config_error(tmp_path, override, message_fragment):
    path = write_toml(tmp_path, override)
    with pytest.raises(ConfigError, match=message_fragment):
        load_config(path)


def test_reference_point_must_be_within_configured_sweep(tmp_path):
    path = write_toml(
        tmp_path,
        """
        [measurement]
        frequencies_hz = [100, 1000]
        voltage_levels_mv = [600]

        [measurement.reference.capacitor]
        frequency_hz = 999999
        level_mv = 600
        """,
    )
    with pytest.raises(ConfigError, match="not in measurement.frequencies_hz"):
        load_config(path)


def test_reference_level_must_be_within_configured_levels(tmp_path):
    path = write_toml(
        tmp_path,
        """
        [measurement]
        frequencies_hz = [100, 1000]
        voltage_levels_mv = [600]

        [measurement.reference.capacitor]
        frequency_hz = 1000
        level_mv = 300
        """,
    )
    with pytest.raises(ConfigError, match="not in measurement.voltage_levels_mv"):
        load_config(path)


def test_missing_required_key_names_the_dotted_path(tmp_path):
    # A config that removes a whole required table via an empty override table
    # still leaves the default's keys in place (deep-merge), so instead check
    # that a key path referencing a genuinely absent key raises with that path.
    from electric_component_check.config import _require

    with pytest.raises(ConfigError, match="openbis.nonexistent"):
        _require({"openbis": {}}, "openbis.nonexistent")
