#!/usr/bin/env python3
"""
LCR-Controller für GUI-Integration mit Qt.

Dieser Controller verbindet sich mit dem Voltcraft LCR500 über einen
Resource-String und bietet eine GUI-freundliche API mit Qt-Signalen.
Features:
- Verbindungsmanagement mit automatischer Überwachung (QTimer)
- Messmethoden für Kondensatoren, Induktivitäten und Widerstände
- Qt-Signale für Status-Updates
- Wiederverwendung der LCR500Controller-Logik aus lcr_testing
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional, Literal, Tuple, Dict, Any, List
from datetime import datetime

from PySide6.QtCore import QObject, Signal, QTimer

try:
    from voltcraft_lcr500 import LCR500
except ImportError:
    LCR500 = None

from vcr_uncertainties import MeasurementError

# Type Definitions
Component = Literal["capacitor", "inductor", "resistor"]
MeasType = Literal["capacitance", "inductance", "impedance"]


# ============================================================================
# Helper Functions (from lcr_testing)
# ============================================================================


def load_spec_json(path: Path) -> dict:
    """Lädt die Unsicherheitsspezifikation aus JSON-Datei."""
    import json

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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
# Hardware Controller (from lcr_testing)
# ============================================================================


class LCR500HardwareController:
    """Verwaltet die direkte Kommunikation mit dem LCR500-Gerät (ohne Simulation)."""

    SETTLE_TIME = 0.5  # Zeit nach Einstellungsänderung (Sekunden)
    FETCH_RETRIES = 5  # Max. Versuche bei "Data Not Ready!"
    FETCH_RETRY_DELAY = 2  # Pause zwischen Versuchen (Sekunden)

    def __init__(
        self,
        resource: str,
        component: Component,
        debug: bool = False,
    ) -> None:
        self.resource = resource
        self.component = component
        self.dev = None
        self.debug = debug

    def _log(self, message: str) -> None:
        """Debug-Ausgabe."""
        if self.debug:
            print(f"[LCR500] {message}")

    def connect(self) -> bool:
        """Verbindet mit dem Gerät (nur Hardware, kein Fallback)."""
        if not self.resource:
            raise ValueError("Resource-String ist erforderlich!")

        if LCR500 is None:
            raise RuntimeError(
                "PyMeasure LCR500 ist nicht verfügbar! Installiere pymeasure."
            )

        try:
            self.dev = LCR500(self.resource)
            idn = getattr(self.dev, "id", None)
            self._log(f"Verbunden: {idn}")

            # Prüfe Identifikation
            if isinstance(idn, str):
                idu = idn.upper()
                if "VOLTCRAFT" in idu and "LCR-500" in idu:
                    self._log("ID-Check erfolgreich: VOLTCRAFT LCR-500")
                else:
                    self._log(f"WARNUNG: Geräte-ID stimmt nicht überein: {idn}")
            return True
        except Exception as e:
            self._log(f"Verbindungsfehler: {e}")
            raise RuntimeError(f"Verbindung zu LCR500 fehlgeschlagen: {e}")

    def disconnect(self) -> None:
        """Trennt die Verbindung."""
        try:
            if self.dev and hasattr(self.dev, "shutdown"):
                self.dev.shutdown()
        finally:
            self.dev = None

    def is_connected(self) -> bool:
        """Prüft, ob das Gerät verbunden ist."""
        if not self.dev:
            return False
        try:
            # Versuche, Geräte-ID abzufragen
            idn = getattr(self.dev, "id", None)
            return idn is not None
        except Exception:
            return False

    @property
    def idn(self, full: bool = False) -> str:
        """Geräte-Identifikation."""
        info = getattr(self.dev, "id", "UNKNOWN")
        if full:
            return info
        return info.rsplit(",", maxsplit=1)[-1]

    def _verify_setting(self, attr: str, expected_value: Any) -> bool:
        """Verifiziert, ob eine Einstellung tatsächlich übernommen wurde."""
        try:
            actual = getattr(self.dev, attr, None)
            if actual == expected_value:
                return True
            self._log(
                f"Einstellungs-Verifikation fehlgeschlagen: {attr} = {actual}, erwartet {expected_value}"
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
                    self._log(f"Frequenz gesetzt -> {freq_hz} Hz [OK]")
                    return True
                else:
                    self._log(f"Frequenz setzen -> {freq_hz} Hz [FEHLER]")
                    return False
            except (ValueError, AttributeError) as e:
                self._log(f"Fehler beim Setzen der Frequenz: {e}")
                return False
        return False

    def set_voltage(self, level_v: float) -> bool:
        """Setzt die Anregungsspannung und verifiziert die Einstellung."""
        # PyMeasure-Treiber mit mVrms-Level
        if hasattr(self.dev, "level"):
            try:
                mv = int(round(level_v * 1000.0))
                allowed = [300, 600]
                mv_set = min(allowed, key=lambda a: abs(a - mv))
                setattr(self.dev, "level", mv_set)
                time.sleep(self.SETTLE_TIME)

                if self._verify_setting("level", mv_set):
                    self._log(f"Spannungspegel (mVrms) gesetzt -> {mv_set} [OK]")
                    return True
                else:
                    self._log(f"Spannungspegel setzen -> {mv_set} [FEHLER]")
                    return False
            except (ValueError, TypeError, AttributeError) as e:
                self._log(f"Fehler beim Setzen des Pegels: {e}")
                return False
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
                        self._log(f"EQUIV-Modus gesetzt -> {m} [OK]")
                        return True
                    else:
                        self._log(f"EQUIV-Modus setzen -> {m} [FEHLER]")
                        return False
                except (ValueError, AttributeError) as e:
                    self._log(f"Fehler beim Setzen des EQUIV-Modus: {e}")
        return False

    def fetch_measurement(self) -> Tuple[Optional[float], Optional[float]]:
        """Liest Messwerte mit Retry-Logik bei 'Data Not Ready!'."""
        for attempt in range(self.FETCH_RETRIES):
            if hasattr(self.dev, "fetch"):
                try:
                    time.sleep(self.FETCH_RETRY_DELAY)
                    val = getattr(self.dev, "fetch")
                    self._log(f"Messung Versuch {attempt + 1}: {val}")

                    # Listen-Rückgabe
                    if isinstance(val, list):
                        if len(val) >= 2:
                            try:
                                p, s = float(val[0]), float(val[1])
                                self._log(f"Messung (Liste) -> p={p}, s={s}")
                                return p, s
                            except (ValueError, TypeError, IndexError) as e:
                                self._log(f"Fehler beim Parsen der Liste: {e}")
                                time.sleep(self.FETCH_RETRY_DELAY)
                                continue

                    # Tupel-Rückgabe
                    elif isinstance(val, tuple):
                        if len(val) >= 2:
                            try:
                                p, s = float(val[0]), float(val[1])
                                self._log(f"Messung (Tupel) -> p={p}, s={s}")
                                return p, s
                            except (ValueError, TypeError, IndexError) as e:
                                self._log(f"Fehler beim Parsen des Tupels: {e}")
                                time.sleep(self.FETCH_RETRY_DELAY)
                                continue

                    # String-Antwort verarbeiten
                    elif isinstance(val, str):
                        # Check auf "Data Not Ready!"
                        if "Data Not Ready!" in val or val.strip() == "":
                            msg = (
                                "'Data Not Ready!'"
                                if "Data Not Ready!" in val
                                else "leerer String"
                            )
                            self._log(
                                f"Messung -> {msg}, Wiederholung ({attempt + 1}/{self.FETCH_RETRIES})..."
                            )
                            time.sleep(self.FETCH_RETRY_DELAY)
                            continue

                        # Kommagetrennte Werte parsen
                        parts = [v.strip() for v in val.split(",")]

                        # Weitere Validierung
                        if any("Data Not Ready!" in p for p in parts):
                            self._log(
                                f"Messung -> partielles 'Data Not Ready!' in '{val}', Wiederholung ({attempt + 1}/{self.FETCH_RETRIES})..."
                            )
                            time.sleep(self.FETCH_RETRY_DELAY)
                            continue

                        if len(parts) >= 2:
                            try:
                                p, s = float(parts[0]), float(parts[1])
                                self._log(f"Messung (String) -> p={p}, s={s}")
                                return p, s
                            except (ValueError, TypeError) as e:
                                self._log(f"Parse-Fehler: {e} in '{val}'")
                                time.sleep(self.FETCH_RETRY_DELAY)
                                continue

                except (AttributeError, ValueError, TypeError) as e:
                    self._log(f"Messfehler: {e}")
                    time.sleep(self.FETCH_RETRY_DELAY)
                    continue

        self._log("Alle Messversuche fehlgeschlagen")
        return None, None

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
                    self._log(f"{attr} gesetzt -> {p_set}")
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
                    self._log(f"{attr} gesetzt -> {s_set}")
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
                self._log(f"Auto-Range -> {enable}")
                return
            except (ValueError, AttributeError):
                pass


# ============================================================================
# GUI LCR Controller
# ============================================================================


class LCRController(QObject):
    """
    Qt-basierter Controller für LCR500-Messgerät.

    Signale:
        connected: Wird ausgesendet, wenn die Verbindung erfolgreich hergestellt wurde
        disconnected: Wird ausgesendet, wenn die Verbindung getrennt wurde
        connection_lost: Wird ausgesendet, wenn die Verbindung verloren ging
        measurement_ready: Wird mit Messdaten ausgesendet (dict)
        error_occurred: Wird bei Fehlern ausgesendet (str)
        status_changed: Wird bei Statusänderungen ausgesendet (str)
    """

    # Qt Signals
    connected = Signal(str)  # Device ID (connection status only)
    disconnected = Signal()
    connection_lost = Signal()
    measurement_ready = Signal(dict)  # Measurement data
    error_occurred = Signal(str)  # Error message
    # Transiente Statusmeldungen (nur für Statusbar): message, level(info|success|warning|error), duration(ms)
    status_message = Signal(str, str, int)
    # Verbindungsspezifischer Status (nur für UI-Label)
    status_changed = Signal(str)

    def __init__(
        self,
        spec_path: Path = Path(__file__).parent / "vcr_uncertainties.json",
        check_interval_ms: int = 5000,
        debug: bool = False,
    ):
        """
        Initialisiert den LCR-Controller.

        Args:
            spec_path: Pfad zur Unsicherheitsspezifikation
            check_interval_ms: Intervall für Verbindungsüberwachung (Millisekunden)
            debug: Debug-Modus aktivieren
        """
        super().__init__()

        self.spec_path = spec_path
        self.debug = debug
        self._hw_controller: Optional[LCR500HardwareController] = None
        self._is_measuring = False

        # Lade Unsicherheitsspezifikation
        try:
            self.spec_json = load_spec_json(self.spec_path)
            self.merror = MeasurementError(self.spec_path)
        except Exception as e:
            self.spec_json = {}
            self.merror = None
            if self.debug:
                print(f"[LCRController] Warnung: Konnte Spezifikation nicht laden: {e}")

        # Timer für Verbindungsüberwachung
        self._connection_timer = QTimer(self)
        self._connection_timer.timeout.connect(self._check_connection)
        self._connection_timer.setInterval(check_interval_ms)

    def _log(self, message: str) -> None:
        """Debug-Ausgabe."""
        if self.debug:
            print(f"[LCRController] {message}")

    def connect_device(self, resource: str, component: Component = "capacitor") -> bool:
        """
        Verbindet mit dem LCR500-Gerät.

        Args:
            resource: PyVISA Resource-String
            component: Standard-Bauteiltyp

        Returns:
            True bei erfolgreicher Verbindung, False sonst
        """
        try:
            self._log(f"Verbinde mit {resource}...")
            self.status_message.emit(f"Verbinde mit {resource}...", "info", 2000)

            self._hw_controller = LCR500HardwareController(
                resource=resource,
                component=component,
                debug=self.debug,
            )

            if self._hw_controller.connect():
                device_id = self._hw_controller.idn
                self._log(f"Verbunden: {device_id}")
                self.connected.emit(device_id)
                # Verbindungsetikett aktualisieren
                self.status_changed.emit(f"Verbunden: {device_id}")
                # Transiente Erfolgsmeldung
                self.status_message.emit("LCR verbunden", "success", 2500)

                # Starte Verbindungsüberwachung
                self._connection_timer.start()

                return True
            else:
                self.error_occurred.emit("Verbindung fehlgeschlagen")
                self.status_message.emit("LCR-Verbindung fehlgeschlagen", "error", 6000)
                return False

        except Exception as e:
            error_msg = f"Verbindungsfehler: {str(e)}"
            self._log(error_msg)
            self.error_occurred.emit(error_msg)
            self.status_message.emit(error_msg, "error", 6000)
            return False

    def disconnect_device(self) -> None:
        """Trennt die Verbindung zum Gerät."""
        # Stoppe Verbindungsüberwachung
        self._connection_timer.stop()

        if self._hw_controller:
            try:
                self._hw_controller.disconnect()
            except Exception as e:
                self._log(f"Fehler beim Trennen: {e}")
            finally:
                self._hw_controller = None

        self._log("Verbindung getrennt")
        self.disconnected.emit()
        # Verbindungsetikett
        self.status_changed.emit("Verbindung getrennt")
        # Transiente Info
        self.status_message.emit("LCR-Verbindung getrennt", "info", 2000)

    def is_connected(self) -> bool:
        """Prüft, ob das Gerät verbunden ist."""
        if not self._hw_controller:
            return False
        return self._hw_controller.is_connected()

    def _check_connection(self) -> None:
        """Periodische Verbindungsüberwachung (wird von QTimer aufgerufen)."""
        # Überspringe Check während Messung
        if self._is_measuring:
            return

        if not self.is_connected():
            self._log("Verbindung verloren!")
            self._connection_timer.stop()
            self.connection_lost.emit()
            self.error_occurred.emit("Verbindung zum Gerät verloren")
            # Verbindungsetikett
            self.status_changed.emit("Verbindung verloren")
            # Transiente Warnung
            self.status_message.emit(
                "Verbindung zum LCR-Gerät verloren", "warning", 5000
            )
            self._hw_controller = None

    def measure_single(
        self,
        component: Component,
        frequency_hz: int,
        voltage_v: float = 0.6,
    ) -> Optional[Dict[str, Any]]:
        """
        Führt eine einzelne Messung durch.

        Args:
            component: Bauteiltyp (capacitor, inductor, resistor)
            frequency_hz: Messfrequenz in Hz
            voltage_v: Anregungsspannung in Vrms

        Returns:
            Dictionary mit Messdaten oder None bei Fehler
        """
        if not self._hw_controller:
            self.error_occurred.emit("Keine Verbindung zum Gerät")
            return None

        self._is_measuring = True

        try:
            # Bauteiltyp und Parameter bestimmen
            meas_type, primary_name, secondary_name = component_to_meastype(component)

            # Messpaar konfigurieren
            self._hw_controller.component = component
            self._hw_controller.configure_measurement_pair(primary_name, secondary_name)

            # Frequenz und Spannung setzen
            self._hw_controller.set_frequency(frequency_hz)
            self._hw_controller.set_voltage(voltage_v)

            # Auto-Range aktivieren
            self._hw_controller.enable_auto_range(True)
            time.sleep(0.5)

            # Messung durchführen
            primary_val, secondary_val = self._hw_controller.fetch_measurement()

            if primary_val is None:
                self.error_occurred.emit("Keine gültigen Messdaten empfangen")
                return None

            # Unsicherheiten berechnen (falls verfügbar)
            u_primary, u_secondary = None, None
            if self.merror:
                try:
                    if meas_type == "capacitance":
                        u_primary, u_secondary, _ = self.merror.uncertainty_capacitance(
                            primary_val, frequency_hz
                        )
                    elif meas_type == "inductance":
                        u_primary, u_secondary, _ = self.merror.uncertainty_inductance(
                            primary_val, frequency_hz
                        )
                    elif meas_type == "impedance":
                        u_primary, u_secondary, _ = self.merror.uncertainty_impedance(
                            primary_val, frequency_hz
                        )
                except (ValueError, KeyError) as e:
                    self._log(
                        f"Warnung: Unsicherheit konnte nicht berechnet werden: {e}"
                    )

            # Messdaten zusammenstellen
            measurement = {
                "timestamp": datetime.now().isoformat(),
                "component": component,
                "frequency_hz": frequency_hz,
                "voltage_v": voltage_v,
                "primary_name": primary_name,
                "primary_value": primary_val,
                "primary_uncertainty": u_primary,
                "secondary_name": secondary_name,
                "secondary_value": secondary_val,
                "secondary_uncertainty": u_secondary,
            }

            self._log(
                f"Messung: {primary_name}={primary_val}, {secondary_name}={secondary_val}"
            )
            self.measurement_ready.emit(measurement)

            return measurement

        except Exception as e:
            error_msg = f"Messfehler: {str(e)}"
            self._log(error_msg)
            self.error_occurred.emit(error_msg)
            return None
        finally:
            self._is_measuring = False

    def measure_sweep(
        self,
        component: Component,
        frequencies_hz: Optional[List[int]] = None,
        voltage_v: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """
        Führt eine Messreihe über mehrere Frequenzen durch.

        Args:
            component: Bauteiltyp (capacitor, inductor, resistor)
            frequencies_hz: Liste der Messfrequenzen (None = alle unterstützten)
            voltage_v: Anregungsspannung in Vrms

        Returns:
            Liste mit Messdaten-Dictionaries
        """
        if not self._hw_controller:
            self.error_occurred.emit("Keine Verbindung zum Gerät")
            return []

        # Verwende alle unterstützten Frequenzen, falls nicht angegeben
        if frequencies_hz is None:
            meas_type, _, _ = component_to_meastype(component)
            frequencies_hz = self._get_supported_frequencies(meas_type)

        measurements = []
        total = len(frequencies_hz)

        self.status_message.emit(f"Starte Messreihe: {total} Frequenzen", "info", 2000)

        for idx, freq in enumerate(frequencies_hz, 1):
            self.status_message.emit(f"Messung {idx}/{total}: {freq} Hz", "info", 1500)

            result = self.measure_single(component, freq, voltage_v)
            if result:
                measurements.append(result)

        self.status_message.emit(
            f"Messreihe abgeschlossen: {len(measurements)}/{total} erfolgreich",
            "success",
            3000,
        )

        return measurements

    def _get_supported_frequencies(self, meas_type: MeasType) -> List[int]:
        """Extrahiert alle unterstützten Messfrequenzen aus der Spezifikation."""
        if meas_type not in self.spec_json:
            # Fallback auf Standard-Frequenzen
            return [100, 120, 400, 1000, 4000, 10000, 40000, 50000, 75000, 100000]

        freqs: set[int] = set()
        for _block_name, blk in self.spec_json[meas_type].items():
            for f in blk.get("freqs_Hz", []):
                try:
                    freqs.add(int(f))
                except (TypeError, ValueError):
                    continue
        return sorted(freqs)

    def get_device_info(self) -> Optional[Dict[str, str]]:
        """
        Gibt Geräteinformationen zurück.

        Returns:
            Dictionary mit Geräteinformationen oder None
        """
        if not self._hw_controller:
            return None

        return {
            "id": self._hw_controller.idn,
            "resource": self._hw_controller.resource,
            "component": self._hw_controller.component,
            "connected": str(self.is_connected()),
        }
