#!/usr/bin/env python3
"""
Vollständige Bauteil-Messroutine für Voltcraft LCR500 mit PyMeasure.

Funktionen:
- Wählt je nach Bauteiltyp (capacitance/inductance/impedance) Mess-Setup
- Ermittelt pro Frequenz den passenden EQUIV-Modus (SER/PAR) aus vcr_uncertainties
- Sweep über alle unterstützten Frequenzen und definierte Spannungspegel
- Erfasst Primär- und Sekundärparameter (z. B. C/D, L/D, Z/theta)
- Berechnet Messunsicherheiten basierend auf vcr_uncertainties.json
- Speichert ein vollständiges Messprotokoll als CSV und JSON
"""

from __future__ import annotations

import json
import csv
import sys
import time
import importlib.util
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal, Tuple, Dict, Any, List, Type

try:
    from .voltcraft_lcr500 import LCR500
except ImportError:
    LCR500 = None
    print("WARN: PyMeasure oder LCR500-Treiber nicht verfügbar, nutze Simulation.")

from .vcr_uncertainties import MeasurementError


# ============================================================================
# Type Definitions
# ============================================================================
Component = Literal["capacitor", "inductor", "resistor"]
MeasType = Literal["capacitance", "inductance", "impedance"]


# ============================================================================
# Helper Functions
# ============================================================================


def load_spec_json(path: Path) -> dict:
    """Lädt die Unsicherheitsspezifikation aus JSON-Datei."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_supported_freqs(meas_type: MeasType, spec_json: dict) -> List[int]:
    """Extrahiert alle in der Unsicherheits-Spezifikation genannten Messfrequenzen."""
    if meas_type not in spec_json:
        return []

    freqs: set[int] = set()
    for _block_name, blk in spec_json[meas_type].items():
        for f in blk.get("freqs_Hz", []):
            try:
                freqs.add(int(f))
            except (TypeError, ValueError):
                continue
    return sorted(freqs)


def component_to_meastype(component: Component) -> Tuple[MeasType, str, str]:
    """Mappt Bauteiltyp auf (meas_type, primary_name, secondary_name)."""
    if component == "capacitor":
        return "capacitance", "C", "D"
    if component == "inductor":
        return "inductance", "L", "D"
    if component == "resistor":
        return "impedance", "Z", "theta_deg"
    raise ValueError(f"Unbekannter Bauteiltyp: {component}")


# ============================================================================
# Simulation Device (Fallback)
# ============================================================================


class SimulationLCR:
    """Sehr einfache Simulation, falls keine echte Hardware verfügbar ist."""

    def __init__(self) -> None:
        self._id = "SIM-VOLTCRAFT-LCR500"
        self.frequency: int = 1000
        self.level_v: float = 1.0
        self.equiv: str = "SER"
        self.component: Component = "capacitor"

    @property
    def id(self) -> str:
        return self._id

    def shutdown(self):
        pass

    @property
    def primary_parameter(self) -> float:
        if self.component == "capacitor":
            base = 1e-6
            return base * (1 + (self.frequency / 1e5) * 0.1)
        if self.component == "inductor":
            base = 1e-3
            return base * (1 - (self.frequency / 1e5) * 0.05)
        base = 100.0
        return base * (1 + (self.frequency / 1e5) * 0.2)

    @property
    def secondary_parameter(self) -> float:
        if self.component in ("capacitor", "inductor"):
            return 0.02  # D ~ 0.02
        return 1.0  # theta ~ 1° (nur Platzhalter)


# ============================================================================
# Device Controller
# ============================================================================

# HINWEIS: Die LCR500HardwareController-Klasse wurde nach lcr_controller.py
# ausgelagert. Für die GUI-Integration bitte lcr_controller.LCRController verwenden.


class LCR500Controller:
    """Verwaltet die Kommunikation mit dem LCR500-Gerät (mit Simulation-Fallback)."""

    SETTLE_TIME = 0.5  # Zeit nach Einstellungsänderung (Sekunden)
    FETCH_RETRIES = 5  # Max. Versuche bei "Data Not Ready!"
    FETCH_RETRY_DELAY = 2  # Pause zwischen Versuchen (Sekunden)

    def __init__(
        self,
        resource: Optional[str],
        component: Component,
        lcr_cls: Optional[Type[Any]] = None,
        debug: bool = False,
    ) -> None:
        self.resource = resource
        self.component = component
        self.dev = None
        self._lcr_cls = lcr_cls
        self.debug = debug

    def _log(self, message: str) -> None:
        """Debug-Ausgabe."""
        if self.debug:
            print(f"[DEBUG] {message}")

    def connect(self) -> bool:
        """Verbindet mit dem Gerät (Hardware oder Simulation)."""
        if self.resource:
            cls = self._lcr_cls if self._lcr_cls is not None else LCR500
            if cls is None:
                raise RuntimeError(
                    "PyMeasure LCR500 ist nicht verfügbar, aber eine Resource wurde angegeben!"
                )
            try:
                self.dev = cls(self.resource)
                idn = getattr(self.dev, "id", None)
                self._log(f"connected using {cls.__name__}, id={idn}")

                # Prüfe Identifikation
                if isinstance(idn, str):
                    idu = idn.upper()
                    if "VOLTCRAFT" in idu and "LCR-500" in idu:
                        self._log("ID check passed: VOLTCRAFT LCR-500")
                    else:
                        print(f"[WARN] Device ID doesn't match expected LCR-500: {idn}")
                return True
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                self._log(f"connect error for {cls.__name__}: {e}")
                raise RuntimeError(
                    f"Verbindung zu LCR500 über PyMeasure fehlgeschlagen: {e}"
                )

        # Kein Resource-String: Fallback auf Simulation
        self.dev = SimulationLCR()
        self.dev.component = self.component  # type: ignore[attr-defined]
        self._log("fallback to SimulationLCR (no resource)")
        return True

    def disconnect(self) -> None:
        """Trennt die Verbindung."""
        try:
            if self.dev and hasattr(self.dev, "shutdown"):
                self.dev.shutdown()
        finally:
            self.dev = None

    @property
    def idn(self) -> str:
        """Geräte-Identifikation."""
        return getattr(self.dev, "id", "UNKNOWN")  # type: ignore[no-any-return]

    def _verify_setting(self, attr: str, expected_value: Any) -> bool:
        """Verifiziert, ob eine Einstellung tatsächlich übernommen wurde."""
        try:
            actual = getattr(self.dev, attr, None)
            if actual == expected_value:
                return True
            self._log(
                f"Setting verification failed: {attr} = {actual}, expected {expected_value}"
            )
            return False
        except (AttributeError, ValueError):
            return False

    def set_frequency(self, freq_hz: int) -> bool:
        """Setzt die Messfrequenz und verifiziert die Einstellung."""
        if hasattr(self.dev, "frequency"):
            try:
                setattr(self.dev, "frequency", freq_hz)
                time.sleep(self.SETTLE_TIME)

                if self._verify_setting("frequency", freq_hz):
                    self._log(f"set frequency -> {freq_hz} Hz [OK]")
                    return True
                else:
                    self._log(f"set frequency -> {freq_hz} Hz [FAILED]")
                    return False
            except (ValueError, AttributeError) as e:
                self._log(f"set frequency error: {e}")
                return False
        return False

    def set_voltage(self, level_v: float) -> bool:
        """Setzt die Anregungsspannung und verifiziert die Einstellung."""
        # Spezieller Fall: PyMeasure-Treiber mit mVrms-Level
        if hasattr(self.dev, "level"):
            try:
                mv = int(round(level_v * 1000.0))
                allowed = [300, 600]
                mv_set = min(allowed, key=lambda a: abs(a - mv))
                setattr(self.dev, "level", mv_set)
                time.sleep(self.SETTLE_TIME)

                if self._verify_setting("level", mv_set):
                    self._log(f"set level (mVrms) -> {mv_set} [OK]")
                    return True
                else:
                    self._log(f"set level (mVrms) -> {mv_set} [FAILED]")
                    return False
            except (ValueError, TypeError, AttributeError) as e:
                self._log(f"set level error: {e}")
                return False

        # Fallbacks in Vrms
        for attr in ("voltage", "ac_level", "level_v"):
            if hasattr(self.dev, attr):
                try:
                    setattr(self.dev, attr, level_v)
                    time.sleep(self.SETTLE_TIME)
                    self._log(f"set {attr} -> {level_v} Vrms")
                    return True
                except (ValueError, TypeError, AttributeError):
                    pass
        return False

    def set_equiv(self, mode: Optional[str]) -> bool:
        """Setzt den Ersatzschaltkreis-Modus und verifiziert die Einstellung."""
        if not mode:
            return False

        for attr in ("equivalent_circuit", "equiv", "circuit"):
            if hasattr(self.dev, attr):
                try:
                    # Treiber akzeptiert ggf. "PAL" statt "PAR"
                    m = "PAL" if str(mode).upper() == "PAR" else str(mode).upper()
                    setattr(self.dev, attr, m)
                    time.sleep(self.SETTLE_TIME)

                    if self._verify_setting(attr, m):
                        self._log(f"set equiv -> {m} [OK]")
                        return True
                    else:
                        self._log(f"set equiv -> {m} [FAILED]")
                        return False
                except (ValueError, AttributeError) as e:
                    self._log(f"set equiv error: {e}")
        return False

    def fetch_measurement(self) -> Tuple[Optional[float], Optional[float]]:
        """Liest Messwerte mit Retry-Logik bei 'Data Not Ready!'."""
        for attempt in range(self.FETCH_RETRIES):
            if hasattr(self.dev, "fetch"):
                try:
                    time.sleep(self.FETCH_RETRY_DELAY)
                    val = getattr(self.dev, "fetch")
                    self._log(f"fetch attempt {attempt + 1}: {val}")

                    # Listen-Rückgabe (z.B. [6.75301e-07, 0.00365823, 1000.0])
                    if isinstance(val, list):
                        if len(val) >= 2:
                            try:
                                p, s = float(val[0]), float(val[1])
                                self._log(f"fetch list -> p={p}, s={s}")
                                return p, s
                            except (ValueError, TypeError, IndexError) as e:
                                self._log(f"fetch list parse error: {e}")
                                time.sleep(self.FETCH_RETRY_DELAY)
                                continue
                        elif len(val) == 1:
                            try:
                                p = float(val[0])
                                self._log(f"fetch list (single) -> p={p}, s=None")
                                return p, None
                            except (ValueError, TypeError, IndexError) as e:
                                self._log(f"fetch list parse error: {e}")
                                time.sleep(self.FETCH_RETRY_DELAY)
                                continue

                    # Tupel-Rückgabe
                    elif isinstance(val, tuple):
                        if len(val) >= 2:
                            try:
                                p, s = float(val[0]), float(val[1])
                                self._log(f"fetch tuple -> p={p}, s={s}")
                                return p, s
                            except (ValueError, TypeError, IndexError) as e:
                                self._log(f"fetch tuple parse error: {e}")
                                time.sleep(self.FETCH_RETRY_DELAY)
                                continue

                    # String-Antwort verarbeiten
                    elif isinstance(val, str):
                        # Check auf "Data Not Ready!" oder leerer String
                        if "Data Not Ready!" in val or val.strip() == "":
                            msg = (
                                "'Data Not Ready!'"
                                if "Data Not Ready!" in val
                                else "empty string"
                            )
                            self._log(
                                f"fetch -> {msg}, retrying ({attempt + 1}/{self.FETCH_RETRIES})..."
                            )
                            time.sleep(self.FETCH_RETRY_DELAY)
                            continue

                        # Kommagetrennte Werte parsen (3 Werte: Primär, Sekundär, Range)
                        parts = [v.strip() for v in val.split(",")]

                        # Weitere Validierung: keine "Data Not Ready!" in Teilstrings
                        if any("Data Not Ready!" in p for p in parts):
                            self._log(
                                f"fetch -> partial 'Data Not Ready!' in '{val}', retrying ({attempt + 1}/{self.FETCH_RETRIES})..."
                            )
                            time.sleep(self.FETCH_RETRY_DELAY)
                            continue

                        if len(parts) >= 2:
                            try:
                                p, s = float(parts[0]), float(parts[1])
                                self._log(f"fetch string -> p={p}, s={s}")
                                return p, s
                            except (ValueError, TypeError) as e:
                                self._log(f"fetch parse error: {e} in '{val}'")
                                time.sleep(self.FETCH_RETRY_DELAY)
                                continue

                        if len(parts) == 1:
                            try:
                                p = float(parts[0])
                                self._log(f"fetch string (single) -> p={p}, s=None")
                                return p, None
                            except (ValueError, TypeError) as e:
                                self._log(f"fetch parse error: {e} in '{val}'")
                                time.sleep(self.FETCH_RETRY_DELAY)
                                continue
                        p, s = float(val[0]), float(val[1])
                        self._log(f"fetch tuple -> p={p}, s={s}")
                        return p, s

                    # Einzelwert
                    else:
                        try:
                            p = float(val)  # type: ignore[arg-type]
                            self._log(f"fetch single -> p={p}")
                            return p, None
                        except (TypeError, ValueError):
                            self._log(f"fetch unknown format: {val}")
                            time.sleep(self.FETCH_RETRY_DELAY)
                            continue

                except (AttributeError, ValueError, TypeError) as e:
                    self._log(f"fetch error: {e}")
                    time.sleep(self.FETCH_RETRY_DELAY)
                    continue
            else:
                # Kein fetch-Attribut: Fallback auf Properties
                break

        # Fallback: Simulationseigenschaften
        p = getattr(self.dev, "primary_parameter", None)
        s = getattr(self.dev, "secondary_parameter", None)

        # Validierung: s darf nicht "Data Not Ready!" sein
        if isinstance(s, str) and "Data Not Ready!" in s:
            self._log(
                f"primary_parameter/secondary_parameter still returning 'Data Not Ready!'"
            )
            return None, None

        self._log(f"fallback read props -> p={p}, s={s}")
        return p, s

    def configure_measurement_pair(self, primary: str, secondary: str) -> None:
        """Konfiguriert die Mess-Parameter-Paarung (z.B. C/D)."""
        prim_map = {"C": "C", "L": "L", "Z": "Z", "R": "R"}
        sec_map = {"D": "D", "theta_deg": "THETA", "THETA": "THETA"}
        p_set = prim_map.get(primary, primary)
        s_set = sec_map.get(secondary, secondary)

        # Primary Parameter
        for attr in (
            "main_parameter",
            "primary",
            "display_primary",
            "primary_parameter_name",
        ):
            if hasattr(self.dev, attr):
                try:
                    setattr(self.dev, attr, p_set)
                    time.sleep(self.SETTLE_TIME)
                    self._log(f"set {attr} -> {p_set}")
                    break
                except (ValueError, AttributeError):
                    pass

        # Secondary Parameter
        for attr in (
            "secondary_parameter",
            "secondary",
            "display_secondary",
            "secondary_parameter_name",
        ):
            if hasattr(self.dev, attr):
                try:
                    setattr(self.dev, attr, s_set)
                    time.sleep(self.SETTLE_TIME)
                    self._log(f"set {attr} -> {s_set}")
                    break
                except (ValueError, AttributeError):
                    pass

    def enable_auto_range(self, enable: bool) -> None:
        """Aktiviert/deaktiviert Auto-Range."""
        if hasattr(self.dev, "measurement_range"):
            try:
                setattr(
                    self.dev,
                    "measurement_range",
                    "AUTO" if enable else getattr(self.dev, "measurement_range"),
                )
                time.sleep(self.SETTLE_TIME)
                self._log(f"autorange -> {enable}")
                return
            except (ValueError, AttributeError):
                pass

        for attr in ("auto_range", "autorange", "auto"):
            if hasattr(self.dev, attr):
                try:
                    setattr(self.dev, attr, bool(enable))
                    time.sleep(self.SETTLE_TIME)
                    self._log(f"{attr} -> {enable}")
                    return
                except (ValueError, AttributeError):
                    pass

        for attr in ("range_mode", "mode_range"):
            if hasattr(self.dev, attr):
                try:
                    setattr(self.dev, attr, "AUTO" if enable else "MANUAL")
                    time.sleep(self.SETTLE_TIME)
                    self._log(f"{attr} -> {'AUTO' if enable else 'MANUAL'}")
                    return
                except (ValueError, AttributeError):
                    pass

    def set_range_from_spec(self, r: dict, unit_scale: float) -> None:
        """Setzt den Messbereich basierend auf Spezifikation."""
        max_SI = float(r.get("max", 0.0)) * float(unit_scale)
        name = r.get("name")

        if hasattr(self.dev, "measurement_range") and self.component == "resistor":
            try:
                allowed = [10, 100, 1000, 10000, 100000]
                candidates = [v for v in allowed if v >= max_SI]
                target = candidates[0] if candidates else allowed[-1]
                setattr(self.dev, "measurement_range", target)
                time.sleep(self.SETTLE_TIME)
                self._log(f"set measurement_range -> {target}")
                return
            except (ValueError, TypeError, AttributeError):
                pass

        for attr in ("range_max", "range_value", "range_upper"):
            if hasattr(self.dev, attr):
                try:
                    setattr(self.dev, attr, max_SI)
                    time.sleep(self.SETTLE_TIME)
                    self._log(f"set {attr} -> {max_SI}")
                    return
                except (ValueError, AttributeError):
                    pass

        for attr in ("range_name", "range"):
            if hasattr(self.dev, attr) and name is not None:
                try:
                    setattr(self.dev, attr, str(name))
                    time.sleep(self.SETTLE_TIME)
                    self._log(f"set {attr} -> {name}")
                    return
                except (ValueError, AttributeError):
                    pass


# ============================================================================
# Measurement Runner
# ============================================================================


class MeasurementRunner:
    """Führt vollständige Messroutine durch."""

    def __init__(
        self,
        component: Component,
        resource: Optional[str] = None,
        spec_path: Path = Path("vcr_uncertainties.json"),
        out_dir: Path = Path("measurements"),
    ) -> None:
        self.component = component
        self.resource = resource
        self.spec_path = spec_path
        self.out_dir = out_dir

        self.spec_json = load_spec_json(self.spec_path)
        self.merror = MeasurementError(self.spec_path)

        meas_type, primary_name, secondary_name = component_to_meastype(component)
        self.meas_type: MeasType = meas_type
        self.primary_name = primary_name
        self.secondary_name = secondary_name
        self.freqs = list_supported_freqs(self.meas_type, self.spec_json)

        if not self.freqs:
            # Fallback auf gängige Frequenzen
            self.freqs = [100, 120, 400, 1000, 4000, 10000, 40000, 50000, 75000, 100000]

        # Default-Pegel (Vrms)
        self.voltage_levels = [0.3, 0.6]

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"{component}_{ts}"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.out_dir / f"{self.run_id}.csv"
        self.json_path = self.out_dir / f"{self.run_id}.json"

        # Optionale Attribute (von main gesetzt)
        self.debug = False
        self.lcr_cls = None

    def _find_equiv(self, value_SI: float, freq_hz: int) -> Optional[str]:
        """Ermittelt EQUIV-Modus für gegebenen Messwert."""
        try:
            return self.merror.find_equiv_mode(self.meas_type, value_SI, freq_hz)
        except (ValueError, KeyError):
            return None

    def _compute_uncertainties(
        self, primary_value_SI: float, freq_hz: int
    ) -> Tuple[Optional[float], Optional[float], Optional[dict]]:
        """Berechnet Messunsicherheiten."""
        try:
            if self.meas_type == "capacitance":
                return self.merror.uncertainty_capacitance(primary_value_SI, freq_hz)
            if self.meas_type == "inductance":
                return self.merror.uncertainty_inductance(primary_value_SI, freq_hz)
            if self.meas_type == "impedance":
                return self.merror.uncertainty_impedance(primary_value_SI, freq_hz)
        except (ValueError, KeyError):
            pass
        return None, None, None

    @staticmethod
    def _to_SI(component: Component, primary_value: float) -> float:
        """Konvertiert Primärwert in SI-Einheiten."""
        return float(primary_value)  # Gerät liefert bereits SI

    def run(self) -> Dict[str, Any]:
        """Führt die vollständige Messroutine durch."""
        ctrl = LCR500Controller(
            self.resource, self.component, self.lcr_cls, debug=self.debug
        )

        if not ctrl.connect():
            raise RuntimeError("Keine Verbindung/Simulation verfügbar")

        # Messpaar konfigurieren
        ctrl.configure_measurement_pair(self.primary_name, self.secondary_name)

        meta: Dict[str, Any] = {
            "instrument": ctrl.idn,
            "component": self.component,
            "meas_type": self.meas_type,
            "primary": self.primary_name,
            "secondary": self.secondary_name,
            "freqs": self.freqs,
            "voltage_levels": self.voltage_levels,
            "run_id": self.run_id,
            "timestamp": datetime.now().isoformat(),
            "resource": self.resource,
            "driver_class": getattr(self.lcr_cls, "__name__", None),
            "debug": self.debug,
        }

        if self.debug:
            print(f"\n{'=' * 80}")
            print("MEASUREMENT METADATA")
            print(f"{'=' * 80}")
            for k, v in meta.items():
                print(f"  {k}: {v}")
            print(f"{'=' * 80}\n")

        records: List[Dict[str, Any]] = []
        fieldnames = [
            "timestamp",
            "freq_hz",
            "level_v",
            "equiv",
            f"{self.primary_name}",
            f"{self.secondary_name}",
            "u_primary",
            "u_secondary",
            "range_name",
        ]

        with self.csv_path.open("w", newline="", encoding="utf-8") as fcsv:
            writer = csv.DictWriter(fcsv, fieldnames=fieldnames)
            writer.writeheader()

            for freq_idx, f in enumerate(self.freqs, 1):
                print(f"\n[{freq_idx}/{len(self.freqs)}] Processing frequency: {f} Hz")

                # Frequenz setzen
                ctrl.set_frequency(f)

                # Auto-Range aktivieren für initiale Messung
                ctrl.enable_auto_range(True)
                time.sleep(0.5)  # Stabilisierung

                # Initialmessung für EQUIV und Range
                p_init, _ = ctrl.fetch_measurement()
                if p_init is None:
                    print(f"  [SKIP] No valid measurement at {f} Hz")
                    continue

                p_SI = self._to_SI(self.component, p_init)

                # Range bestimmen
                try:
                    blk = self.merror.select_block(self.meas_type, f)
                    r, _ = self.merror.match_range(blk, p_SI)
                except (ValueError, KeyError):
                    r = None

                # EQUIV bestimmen
                equiv = None
                if r is not None:
                    equiv = r.get("equiv")
                if not equiv:
                    equiv = self._find_equiv(p_SI, f)

                if equiv:
                    ctrl.set_equiv(equiv)
                    print(f"  EQUIV: {equiv}")

                # Auto-Range deaktivieren, Range setzen
                ctrl.enable_auto_range(False)
                if r is not None:
                    unit_val = r.get("unit")
                    unit_key = str(unit_val) if unit_val is not None else ""
                    unit_scale = self.merror.UNIT.get(unit_key, 1.0)
                    ctrl.set_range_from_spec(r, float(unit_scale))

                # Messungen bei verschiedenen Spannungspegeln
                for lvl in self.voltage_levels:
                    ctrl.set_voltage(lvl)
                    time.sleep(0.5)  # Einschwingen

                    p2, s2 = ctrl.fetch_measurement()
                    now = datetime.now().isoformat()

                    # Konsolenausgabe
                    print(
                        f"  f={f:6d} Hz, V={lvl:.1f} V, EQUIV={equiv}: "
                        f"{self.primary_name}={p2}, {self.secondary_name}={s2}"
                    )

                    # Unsicherheiten berechnen
                    uP, uS, r_unc = (None, None, None)
                    r_name = None
                    if p2 is not None:
                        uP, uS, r_unc = self._compute_uncertainties(
                            self._to_SI(self.component, p2), f
                        )
                        r_name = r_unc.get("name") if isinstance(r_unc, dict) else None

                    # Datensatz speichern
                    row = {
                        "timestamp": now,
                        "freq_hz": f,
                        "level_v": lvl,
                        "equiv": equiv,
                        f"{self.primary_name}": p2,
                        f"{self.secondary_name}": s2,
                        "u_primary": uP,
                        "u_secondary": uS,
                        "range_name": r_name,
                    }
                    writer.writerow(row)
                    fcsv.flush()  # Sofort schreiben
                    records.append(row)

        # JSON-Ausgabe
        result = {"meta": meta, "records": records}
        with self.json_path.open("w", encoding="utf-8") as fjson:
            json.dump(result, fjson, ensure_ascii=False, indent=2)

        ctrl.disconnect()
        return result


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Vollständige Messung mit LCR500",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "component",
        choices=["capacitor", "inductor", "resistor"],
        help="Bauteiltyp",
    )
    parser.add_argument(
        "--resource",
        default=None,
        help="PyVISA Ressourcen-String (z.B. USB0::0x0483::0x5740::...::INSTR)",
    )
    parser.add_argument(
        "--driver-path",
        default=None,
        help="Dateipfad zu deiner LCR500-Treiberdatei (z. B. voltcraft_lcr500.py)",
    )
    parser.add_argument(
        "--driver-class",
        default="LCR500",
        help="Klassenname der Treiberklasse in der Datei (Default: LCR500)",
    )
    parser.add_argument(
        "--spec",
        default="vcr_uncertainties.json",
        help="Pfad zur Unsicherheitsspezifikation",
    )
    parser.add_argument(
        "--out",
        default="measurements",
        help="Ausgabeverzeichnis",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Debug-Ausgaben aktivieren",
    )
    args = parser.parse_args()

    # Optional: lokale Treiberklasse dynamisch laden
    lcr_cls = None
    if args.driver_path:
        try:
            if importlib.util.find_spec("pymeasure") is not None:
                mod_path = Path(args.driver_path)
                spec = importlib.util.spec_from_file_location(
                    "lcr500_driver", str(mod_path)
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules["lcr500_driver"] = module
                    spec.loader.exec_module(module)  # type: ignore[attr-defined]
                    lcr_cls = getattr(module, args.driver_class, None)
        except (ModuleNotFoundError, ImportError):
            lcr_cls = None

    runner = MeasurementRunner(
        component=args.component,
        resource=args.resource,
        spec_path=Path(args.spec),
        out_dir=Path(args.out),
    )
    runner.debug = args.verbose
    runner.lcr_cls = lcr_cls

    res = runner.run()

    print(f"\n{'=' * 80}")
    print("MEASUREMENT COMPLETE")
    print(f"{'=' * 80}")
    print(f"CSV:  {runner.csv_path}")
    print(f"JSON: {runner.json_path}")
    print(f"Records: {len(res['records'])}")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()
