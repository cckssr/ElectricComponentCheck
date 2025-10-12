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

Hinweis: Ohne echte Hardware fällt der Code auf eine einfache Simulation zurück.
"""

from __future__ import annotations

import json
import csv
import time
import sys
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal, Tuple, Dict, Any, List, Type

try:
    # PyMeasure-Instrument (falls installiert)
    from pymeasure.instruments.voltcraft import LCR500  # type: ignore
except ImportError:
    LCR500 = None  # Fallback auf Simulation weiter unten

from vcr_uncertainties import MeasurementError


Component = Literal["capacitor", "inductor", "resistor"]


def load_spec_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_supported_freqs(
    meas_type: Literal["capacitance", "inductance", "impedance"], spec_json: dict
) -> List[int]:
    """Extrahiert alle in der Unsicherheits-Spezifikation genannten Messfrequenzen.

    Regeln:
    - Jeder Block enthält "freqs_Hz": Liste von Frequenzen; mit 1..n Einträgen.
    - Manche Blöcke haben 2 Werte (z. B. [40000, 50000]) => beide werden als erlaubte Einzel-Frequenzen behandelt.
    """
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


def component_to_meastype(
    component: Component,
) -> Tuple[Literal["capacitance", "inductance", "impedance"], str, str]:
    """Mappt Bauteiltyp auf (meas_type, primary_name, secondary_name).

    - capacitor => (capacitance, C, D)
    - inductor  => (inductance, L, D)
    - resistor  => (impedance, Z, theta_deg)
    """
    if component == "capacitor":
        return "capacitance", "C", "D"
    if component == "inductor":
        return "inductance", "L", "D"
    if component == "resistor":
        return "impedance", "Z", "theta_deg"
    raise ValueError(f"Unbekannter Bauteiltyp: {component}")


class SimulationLCR:
    """Sehr einfache Simulation, falls keine echte Hardware verfügbar ist."""

    def __init__(self) -> None:
        self._id = "SIM-VOLTCRAFT-LCR500"
        self.frequency: int = 1000
        self.level_v: float = 1.0
        self.equiv: str = "SER"
        self.component: Component = "capacitor"

    @property
    def id(self) -> str:  # wie echtes Gerät
        return self._id

    def shutdown(self):
        pass

    # Messwerte minimal plausibel simulieren
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


class LCR500Controller:
    def __init__(
        self,
        resource: Optional[str],
        component: Component,
        lcr_cls: Optional[Type[Any]] = None,
    ) -> None:
        self.resource: Optional[str] = resource
        self.component: Component = component
        self.dev = None  # device handle (real or simulation)
        self._lcr_cls: Optional[Type[Any]] = lcr_cls

    def connect(self) -> bool:
        # Präferenz: übergebene Treiberklasse, sonst importierte LCR500, sonst Simulation
        try_classes: List[Optional[Type[Any]]] = [self._lcr_cls, LCR500]
        for cls in try_classes:
            if cls is None or not self.resource:
                continue
            try:
                self.dev = cls(self.resource)
                _ = self.dev.id  # type: ignore[attr-defined]
                return True
            except (OSError, RuntimeError, ValueError, AttributeError):
                self.dev = None
                continue
        # Fallback: Simulation
        self.dev = SimulationLCR()
        self.dev.component = self.component  # type: ignore[attr-defined]
        return True

    def disconnect(self) -> None:
        try:
            if self.dev and hasattr(self.dev, "shutdown"):
                self.dev.shutdown()
        finally:
            self.dev = None

    @property
    def idn(self) -> str:
        return getattr(self.dev, "id", "UNKNOWN")  # type: ignore[no-any-return]

    def set_frequency(self, freq_hz: int) -> None:
        if hasattr(self.dev, "frequency"):
            setattr(self.dev, "frequency", freq_hz)

    def set_voltage(self, level_v: float) -> None:
        """Setzt die Anregungsspannung.

        - Für Treiber mit "level" (mVrms, int): konvertiere Vrms -> mVrms und quantisiere auf {300, 600}.
        - Fallback: versuche weitere Attribute (voltage, ac_level, level_v) in Vrms.
        """
        # Spezieller Fall: PyMeasure-Treiber mit mVrms-Level
        if hasattr(self.dev, "level"):
            try:
                mv = int(round(level_v * 1000.0))
                allowed = [300, 600]
                # Nächsten erlaubten Wert wählen
                mv_set = min(allowed, key=lambda a: abs(a - mv))
                setattr(self.dev, "level", mv_set)
                return
            except (ValueError, TypeError, AttributeError):
                pass
        # Fallbacks in Vrms
        for attr in ("voltage", "ac_level", "level_v"):
            if hasattr(self.dev, attr):
                try:
                    setattr(self.dev, attr, level_v)
                    return
                except (ValueError, TypeError, AttributeError):
                    pass

    def set_equiv(self, mode: Optional[str]) -> None:
        if not mode:
            return
        for attr in ("equivalent_circuit", "equiv", "circuit"):
            if hasattr(self.dev, attr):
                # Treiber akzeptiert ggf. "PAL" statt "PAR"
                m = "PAL" if str(mode).upper() == "PAR" else str(mode).upper()
                setattr(self.dev, attr, m)
                return

    def read_primary_secondary(self) -> Tuple[Optional[float], Optional[float]]:
        """Liest Messwerte (Primär, Sekundär).

        - Bevorzugt Treiber-"fetch" (FETC?), das ein Tupel oder kommaseparierten String liefern kann.
        - Fallback: Simulationseigenschaften primary_parameter/secondary_parameter.
        """
        if hasattr(self.dev, "fetch"):
            try:
                val = getattr(self.dev, "fetch")  # pymeasure measurement property
                # Erwartet Tupel (p, s) oder String "p,s"
                if isinstance(val, tuple) and len(val) >= 2:
                    p, s = val[0], val[1]
                    return float(p), float(s)
                if isinstance(val, str):
                    parts = [v.strip() for v in val.split(",")]
                    if len(parts) >= 2:
                        return float(parts[0]), float(parts[1])
                    if len(parts) == 1:
                        return float(parts[0]), None
                # Einzelwert
                try:
                    return float(val), None  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    pass
            except (AttributeError, ValueError, TypeError):
                pass
        p = getattr(self.dev, "primary_parameter", None)
        s = getattr(self.dev, "secondary_parameter", None)
        return p, s

    def configure_pair(self, primary: str, secondary: str) -> None:
        """Versucht, die Anzeige-/Messpaarung am Gerät zu setzen.
        Fällt still zurück, wenn Attribute nicht existieren."""
        # Mappe unsere Kurzbezeichner auf Treiberwerte
        prim_map = {"C": "C", "L": "L", "Z": "Z", "R": "R"}
        sec_map = {"D": "D", "theta_deg": "THETA", "THETA": "THETA"}
        p_set = prim_map.get(primary, primary)
        s_set = sec_map.get(secondary, secondary)

        # PyMeasure-Treiber: zuerst main_parameter/secondary_parameter
        for attr in (
            "main_parameter",
            "primary",
            "display_primary",
            "primary_parameter_name",
        ):
            if hasattr(self.dev, attr):
                try:
                    setattr(self.dev, attr, p_set)
                except (ValueError, AttributeError):
                    pass
                break
        for attr in (
            "secondary_parameter",
            "secondary",
            "display_secondary",
            "secondary_parameter_name",
        ):
            if hasattr(self.dev, attr):
                try:
                    setattr(self.dev, attr, s_set)
                except (ValueError, AttributeError):
                    pass
                break

    def enable_auto_range(self, enable: bool) -> None:
        """Versucht Auto-Range am Gerät zu (de-)aktivieren."""
        # Speziell: Treiber mit measurement_range = 'AUTO'
        if hasattr(self.dev, "measurement_range"):
            try:
                setattr(
                    self.dev,
                    "measurement_range",
                    "AUTO" if enable else getattr(self.dev, "measurement_range"),
                )
                return
            except (ValueError, AttributeError):
                pass
        # Häufige Namen
        for attr in ("auto_range", "autorange", "auto"):
            if hasattr(self.dev, attr):
                try:
                    setattr(self.dev, attr, bool(enable))
                    return
                except (ValueError, AttributeError):
                    pass
        # Modus-Strings
        for attr in ("range_mode", "mode_range"):
            if hasattr(self.dev, attr):
                try:
                    setattr(self.dev, attr, "AUTO" if enable else "MANUAL")
                    return
                except (ValueError, AttributeError):
                    pass

    def set_range_from_spec(self, r: dict, unit_scale: float) -> None:
        """Setzt den Gerätemessbereich anhand der Spezifikations-Range.

        Probiert mehrere Attribut-/Methodennamen, um eine breite Kompatibilität zu erreichen.
        """
        max_SI = float(r.get("max", 0.0)) * float(unit_scale)
        name = r.get("name")
        # Für unseren PyMeasure-Treiber: measurement_range numerisch setzen (nur sinnvoll bei Impedanz/Resistor)
        if hasattr(self.dev, "measurement_range") and self.component == "resistor":
            try:
                allowed = [10, 100, 1000, 10000, 100000]
                # Wähle den kleinsten erlaubten Bereich, der >= max_SI ist
                candidates = [v for v in allowed if v >= max_SI]
                target = candidates[0] if candidates else allowed[-1]
                setattr(self.dev, "measurement_range", target)
                return
            except (ValueError, TypeError, AttributeError):
                pass
        # Direkte numerische Range
        for attr in ("range_max", "range_value", "range_upper"):
            if hasattr(self.dev, attr):
                try:
                    setattr(self.dev, attr, max_SI)
                    return
                except (ValueError, AttributeError):
                    pass
        # Name-basierte Range
        for attr in ("range_name", "range"):
            if hasattr(self.dev, attr) and name is not None:
                try:
                    setattr(self.dev, attr, str(name))
                    return
                except (ValueError, AttributeError):
                    pass
        # Methodenaufrufe
        for meth in ("set_range", "select_range", "configure_range"):
            if hasattr(self.dev, meth):
                try:
                    getattr(self.dev, meth)(max_SI)
                    return
                except (TypeError, ValueError, AttributeError):
                    pass


class MeasurementRunner:
    def __init__(
        self,
        component: Component,
        resource: Optional[str] = None,
        spec_path: Path = Path("vcr_uncertainties.json"),
        out_dir: Path = Path("measurements"),
    ) -> None:
        self.component: Component = component
        self.resource: Optional[str] = resource
        self.spec_path = spec_path
        self.out_dir = out_dir

        self.spec_json = load_spec_json(self.spec_path)
        self.merror = MeasurementError(self.spec_path)

        meas_type, primary_name, secondary_name = component_to_meastype(component)
        self.meas_type: Literal["capacitance", "inductance", "impedance"] = meas_type
        self.primary_name: str = primary_name
        self.secondary_name: str = secondary_name
        self.freqs = list_supported_freqs(self.meas_type, self.spec_json)
        if not self.freqs:
            # Fallback auf gängige Frequenzen
            self.freqs = [100, 120, 400, 1000, 4000, 10000, 40000, 50000, 75000, 100000]

        # Default-Pegel (Vrms). Treiber akzeptiert 300/600 mVrms -> 0.3/0.6 Vrms.
        self.voltage_levels = [0.3, 0.6]

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"{component}_{ts}"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.out_dir / f"{self.run_id}.csv"
        self.json_path = self.out_dir / f"{self.run_id}.json"

    def _find_equiv(self, value_SI: float, freq_hz: int) -> Optional[str]:
        try:
            return self.merror.find_equiv_mode(self.meas_type, value_SI, freq_hz)
        except (ValueError, KeyError):
            return None

    def _compute_uncertainties(
        self,
        primary_value_SI: float,
        freq_hz: int,
    ) -> Tuple[Optional[float], Optional[float], Optional[dict]]:
        try:
            if self.meas_type == "capacitance":
                uP, uS, r = self.merror.uncertainty_capacitance(
                    primary_value_SI, freq_hz
                )
                return uP, uS, r
            if self.meas_type == "inductance":
                uP, uS, r = self.merror.uncertainty_inductance(
                    primary_value_SI, freq_hz
                )
                return uP, uS, r
            if self.meas_type == "impedance":
                uP, uS, r = self.merror.uncertainty_impedance(primary_value_SI, freq_hz)
                return uP, uS, r
        except (ValueError, KeyError):
            pass
        return None, None, None

    @staticmethod
    def _to_SI(component: Component, primary_value: float) -> float:
        if component == "capacitor":
            return float(primary_value)  # erwartet in F, Gerät liefert meist SI
        if component == "inductor":
            return float(primary_value)  # in H
        return float(primary_value)  # Z/R in Ohm

    def run(self) -> Dict[str, Any]:
        ctrl = LCR500Controller(
            self.resource, self.component, getattr(self, "lcr_cls", None)
        )
        if not ctrl.connect():
            raise RuntimeError("Keine Verbindung/Simulation verfügbar")

        # Versuch, das Messpaar passend zum Bauteil zu konfigurieren
        ctrl.configure_pair(self.primary_name, self.secondary_name)

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
        }

        records: List[Dict[str, Any]] = []

        # CSV vorbereiten
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

            for f in self.freqs:
                ctrl.set_frequency(f)
                # Zuerst Auto-Range aktivieren und kurz stabilisieren lassen
                ctrl.enable_auto_range(True)
                time.sleep(0.2)

                # Initialmessung für EQUIV- und Range-Auswahl
                p, _ = ctrl.read_primary_secondary()
                if p is None:
                    # ohne Messwert keine sinnvolle Fortsetzung
                    continue

                p_SI = self._to_SI(self.component, p)
                # Range anhand Spezifikation bestimmen
                try:
                    blk = self.merror.select_block(self.meas_type, f)
                    r, _ = self.merror.match_range(blk, p_SI)
                except (ValueError, KeyError):
                    r = None

                equiv = None
                if r is not None:
                    # EQUIV direkt aus Range (robuster als separater Aufruf)
                    equiv = r.get("equiv")
                if not equiv:
                    equiv = self._find_equiv(p_SI, f)
                if equiv:
                    ctrl.set_equiv(equiv)

                # Auto-Range deaktivieren und expliziten Bereich setzen (falls möglich)
                ctrl.enable_auto_range(False)
                if r is not None:
                    unit_val = r.get("unit")
                    unit_key = str(unit_val) if unit_val is not None else ""
                    unit_scale = self.merror.UNIT.get(unit_key, 1.0)
                    ctrl.set_range_from_spec(r, float(unit_scale))

                for lvl in self.voltage_levels:
                    ctrl.set_voltage(lvl)
                    time.sleep(0.2)  # Einschwingen

                    p2, s2 = ctrl.read_primary_secondary()
                    now = datetime.now().isoformat()

                    uP, uS, r = (None, None, None)
                    r_name = None
                    if p2 is not None:
                        uP, uS, r = self._compute_uncertainties(
                            self._to_SI(self.component, p2), f
                        )
                        r_name = r.get("name") if isinstance(r, dict) else None

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
                    records.append(row)

        result = {"meta": meta, "records": records}
        with self.json_path.open("w", encoding="utf-8") as fjson:
            json.dump(result, fjson, ensure_ascii=False, indent=2)

        ctrl.disconnect()
        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Vollständige Messung mit LCR500")
    parser.add_argument(
        "component", choices=["capacitor", "inductor", "resistor"], help="Bauteiltyp"
    )
    parser.add_argument(
        "--resource", default=None, help="PyVISA Ressourcen-String (z.B. ASRL1::INSTR)"
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
    parser.add_argument("--out", default="measurements", help="Ausgabeverzeichnis")
    args = parser.parse_args()

    # Optional: lokale Treiberklasse dynamisch laden (nur, wenn pymeasure vorhanden)
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
    if lcr_cls is not None:
        setattr(runner, "lcr_cls", lcr_cls)
    res = runner.run()
    print(f"Messung abgeschlossen. CSV: {runner.csv_path}, JSON: {runner.json_path}")
    print(f"Datensätze: {len(res['records'])}")


if __name__ == "__main__":
    main()
