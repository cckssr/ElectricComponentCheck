#!/usr/bin/env python3
"""
Beispiel für die Verwendung der Voltcraft LCR500-Klasse
in der ElectricComponentCheck-Anwendung
"""

import sys
from typing import Optional

# Import der eigenen PyMeasure-Bibliothek
try:
    from pymeasure.instruments.voltcraft import LCR500

    print("✓ Voltcraft LCR500 erfolgreich importiert")
except ImportError as e:
    print(f"✗ Import-Fehler: {e}")
    sys.exit(1)


class ComponentMeasurement:
    """Klasse für Bauteilmessungen mit dem LCR500"""

    def __init__(self, connection_string: str = "ASRL1::INSTR"):
        self.connection_string = connection_string
        self.lcr_meter: Optional[LCR500] = None
        self.connected = False

    def connect(self) -> bool:
        """Verbindung zum LCR500 herstellen"""
        try:
            print(f"Verbinde zu LCR500 über {self.connection_string}...")
            self.lcr_meter = LCR500(self.connection_string)

            # Teste die Verbindung
            device_id = self.lcr_meter.id
            print(f"Gerät identifiziert: {device_id}")

            self.connected = True
            return True

        except Exception as e:
            print(f"Verbindung fehlgeschlagen: {e}")
            return False

    def disconnect(self):
        """Verbindung trennen"""
        if self.lcr_meter:
            self.lcr_meter.shutdown()
            self.connected = False
            print("Verbindung getrennt")

    def measure_component(self, component_type: str = "auto") -> dict:
        """Messe ein Bauteil"""
        if not self.connected or not self.lcr_meter:
            raise RuntimeError("Nicht mit LCR500 verbunden!")

        try:
            print(f"Messe Bauteil ({component_type})...")

            # Beispiel-Messungen (angepasst an Ihre LCR500-Implementierung)
            results = {}

            # Hauptparameter messen
            if hasattr(self.lcr_meter, "primary_parameter"):
                results["primary"] = self.lcr_meter.primary_parameter

            if hasattr(self.lcr_meter, "secondary_parameter"):
                results["secondary"] = self.lcr_meter.secondary_parameter

            # Frequency auslesen falls verfügbar
            if hasattr(self.lcr_meter, "frequency"):
                results["frequency"] = self.lcr_meter.frequency

            print(f"Messergebnisse: {results}")
            return results

        except Exception as e:
            print(f"Messfehler: {e}")
            return {}

    def set_frequency(self, frequency: float):
        """Messfrequenz setzen"""
        if not self.connected or not self.lcr_meter:
            raise RuntimeError("Nicht mit LCR500 verbunden!")

        if hasattr(self.lcr_meter, "frequency"):
            self.lcr_meter.frequency = frequency
            print(f"Frequenz gesetzt auf: {frequency} Hz")
        else:
            print("Frequenz-Einstellung nicht verfügbar")


def main():
    """Hauptfunktion für Tests"""
    print("=== ElectricComponentCheck - LCR500 Test ===")

    # Erstelle Messobjekt
    measurement = ComponentMeasurement()

    # Hinweis: In der Praxis würden Sie hier die echte Verbindungszeichenkette verwenden
    print(
        "Hinweis: Für echte Hardware verwenden Sie z.B. 'ASRL1::INSTR' oder die richtige COM-Port-Adresse"
    )

    # Simuliere Verbindung (wird fehlschlagen ohne echte Hardware)
    if measurement.connect():
        try:
            # Frequenz setzen
            measurement.set_frequency(1000)  # 1 kHz

            # Komponente messen
            results = measurement.measure_component("capacitor")

            if results:
                print("Messung erfolgreich!")
                for key, value in results.items():
                    print(f"  {key}: {value}")

        finally:
            measurement.disconnect()
    else:
        print("Verbindung nicht möglich (normal ohne echte Hardware)")
        print("Die LCR500-Klasse ist aber bereit für die Verwendung!")


if __name__ == "__main__":
    main()
