"""
Berechnung von LCR-Messunsicherheiten auf Basis einer JSON-Spezifikation.

Die JSON-Datei definiert für jeden Mess-Typ (capacitance, inductance, impedance)
Frequenz-Blöcke mit einer Liste von Messbereichen. Jeder Bereich enthält min/max,
Einheit, Auflösung und Fehlerparameter (z. B. Ce_pct/Ce_digits, Le_pct/Le_digits,
Ze_pct/Ze_digits sowie De_abs bzw. theta_deg und optional "equiv").
"""

from typing import Literal
from math import sqrt
from pathlib import Path
import json


class MeasurementError:
    """
    Klasse zur Berechnung von Messunsicherheiten für LCR-Messungen.

    Lädt die Spezifikation aus einer JSON-Datei und bietet Methoden zur Auswahl
    des Messbereichs sowie zur Berechnung der Unsicherheiten (Typ B) und zur
    quadratischen Kombination mit Typ-A-Anteilen.
    """

    UNIT = {
        "F": 1.0,
        "H": 1.0,
        "Ohm": 1.0,
        "Ω": 1.0,
        "mF": 1e-3,
        "uF": 1e-6,
        "µF": 1e-6,
        "nF": 1e-9,
        "pF": 1e-12,
        "mH": 1e-3,
        "uH": 1e-6,
        "µH": 1e-6,
        "nH": 1e-9,
        "kOhm": 1e3,
        "MOhm": 1e6,
        "kΩ": 1e3,
        "MΩ": 1e6,
    }

    def __init__(self, meas_spec_path: Path) -> None:
        """Konstruktor.

        Args:
            meas_spec_path: Pfad zur JSON-Spezifikation.
        """
        self.meas_spec = self.load_meas_spec(meas_spec_path)

    def load_meas_spec(self, path: Path) -> dict:
        """Lädt die Messspezifikation aus JSON.

        Args:
            path: Pfad zur JSON-Datei.

        Returns:
            Das geladene Spezifikations-Dictionary.
        """
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def select_block(
        self, meas_type: Literal["capacitance", "inductance", "impedance"], freq_hz: int
    ) -> dict:
        """Wählt den passenden Frequenz-Block aus der Spezifikation.

        Args:
            meas_type: Mess-Typ ("capacitance", "inductance", "impedance").
            freq_hz: Frequenz in Hz.

        Returns:
            Der gefundene Block (Dictionary).

        Raises:
            ValueError: Kein Block für diese Frequenz gefunden.
        """
        for blk in self.meas_spec[meas_type].values():
            if freq_hz in blk["freqs_Hz"]:
                return blk
        raise ValueError(f"Keine Spezifikation für {meas_type} bei {freq_hz} Hz.")

    def match_range(self, block: dict, value_SI: float) -> tuple[dict, float]:
        """Findet den passenden Messbereich für einen SI-Wert.

        Args:
            block: Frequenz-Block mit Ranges.
            value_SI: Messwert in SI-Einheiten (F, H, Ohm).

        Returns:
            Tuple aus (Range-Dict, Skalenfaktor von Anzeigeeinheit nach SI).

        Raises:
            ValueError: Wert liegt außerhalb aller Anzeigebereiche.
        """
        for r in block["ranges"]:
            s = self.UNIT[r["unit"]]
            if r["min"] * s <= value_SI <= r["max"] * s:
                return r, s
        raise ValueError("Wert außerhalb Anzeigebereichs")

    def uB_primary(self, value_SI: float, r: dict, scale: float, kind: str) -> float:
        """Berechnet die primäre Typ-B-Unsicherheit für C, L oder Z.

        Args:
            value_SI: Messwert in SI.
            r: Gefundener Messbereich.
            scale: Skalenfaktor (Anzeigeeinheit -> SI).
            kind: "C", "L" oder "Z".

        Returns:
            Absoluter Unsicherheitsbetrag in SI.
        """
        disp = value_SI / scale
        # JSON verwendet großgeschriebene Typ-Präfixe: Ce_pct/Le_pct/Ze_pct
        pct_key = f"{kind}e_pct"
        dig_key = f"{kind}e_digits"
        p = r[pct_key] / 100.0
        d = r[dig_key]
        dlt = r["resolution"]
        return sqrt((p * disp) ** 2 + (d * dlt) ** 2) * scale

    def uB_D(self, r: dict) -> float:
        """Liefert absolute D-Unsicherheit (dimensionslos).

        Args:
            r: Messbereich.

        Returns:
            Absoluter Betrag oder 0.0, wenn nicht spezifiziert.
        """
        de = r.get("De_abs", None)
        return float(de) if de is not None else 0.0

    def uB_theta_deg(self, r: dict) -> float:
        """Liefert absolute Theta-Unsicherheit in Grad.

        Args:
            r: Messbereich.

        Returns:
            Absoluter Betrag in Grad oder 0.0, wenn nicht spezifiziert.
        """
        th = r.get("theta_deg", None)
        return float(th) if th is not None else 0.0

    @staticmethod
    def combine(uA: float, uB: float) -> float:
        """Quadratische Kombination von Typ-A und Typ-B-Unsicherheit."""
        return sqrt(uA * uA + uB * uB)

    @staticmethod
    def q_rel_error(Qx: float, De_abs: float) -> float:
        """Relative Q-Genauigkeit (gültig für Qx*De < 1)."""
        x = Qx * De_abs
        if x >= 1:
            raise ValueError("Qx*De >= 1, Formel ungültig")
        return x / (1 + x)

    def uncertainty_capacitance(
        self, C_SI: float, freq_hz: int, uA_C: float = 0.0, uA_D: float = 0.0
    ) -> tuple[float, float, dict]:
        """Berechnet kombinierte Unsicherheiten für Kapazitätsmessungen.

        Args:
            C_SI: Kapazitätswert in Farad.
            freq_hz: Frequenz in Hz.
            uA_C: Typ-A-Anteil für C (absolut, in F).
            uA_D: Typ-A-Anteil für D (absolut).

        Returns:
            Tuple: (kombinierte Unsicherheit C, kombinierte Unsicherheit D, verwendeter Bereich)
        """
        blk = self.select_block("capacitance", freq_hz)
        r, s = self.match_range(blk, C_SI)
        uB_C = self.uB_primary(C_SI, r, s, "C")
        uB_D = self.uB_D(r)
        return self.combine(uA_C, uB_C), self.combine(uA_D, uB_D), r

    def uncertainty_inductance(
        self, L_SI: float, freq_hz: int, uA_L: float = 0.0, uA_D: float = 0.0
    ) -> tuple[float, float, dict]:
        """Berechnet kombinierte Unsicherheiten für Induktivitätsmessungen.

        Args:
            L_SI: Induktivitätswert in Henry.
            freq_hz: Frequenz in Hz.
            uA_L: Typ-A-Anteil für L (absolut, in H).
            uA_D: Typ-A-Anteil für D (absolut).

        Returns:
            Tuple: (kombinierte Unsicherheit L, kombinierte Unsicherheit D, verwendeter Bereich)
        """
        blk = self.select_block("inductance", freq_hz)
        r, s = self.match_range(blk, L_SI)
        uB_L = self.uB_primary(L_SI, r, s, "L")
        uB_Dv = self.uB_D(r)
        return self.combine(uA_L, uB_L), self.combine(uA_D, uB_Dv), r

    def uncertainty_impedance(
        self, Z_SI: float, freq_hz: int, uA_Z: float = 0.0, uA_theta_deg: float = 0.0
    ) -> tuple[float, float, dict]:
        """Berechnet kombinierte Unsicherheiten für Impedanzmessungen.

        Args:
            Z_SI: Impedanzwert in Ohm.
            freq_hz: Frequenz in Hz.
            uA_Z: Typ-A-Anteil für Z (absolut, in Ω).
            uA_theta_deg: Typ-A-Anteil für Theta (absolut, in Grad).

        Returns:
            Tuple: (kombinierte Unsicherheit Z, kombinierte Unsicherheit Theta, verwendeter Bereich)
        """
        blk = self.select_block("impedance", freq_hz)
        r, s = self.match_range(blk, Z_SI)
        uB_Z = self.uB_primary(Z_SI, r, s, "Z")
        uB_th = self.uB_theta_deg(r)
        return self.combine(uA_Z, uB_Z), self.combine(uA_theta_deg, uB_th), r

    def uncertainty_Q_from_D(self, Qx: float, r: dict, uA_Q_rel: float = 0.0) -> float:
        """Relative Q-Unsicherheit aus D-Genauigkeit.

        Args:
            Qx: Q-Wert.
            r: verwendeter Messbereich (für De_abs).
            uA_Q_rel: Typ-A-Anteil für Q (relativ).

        Returns:
            Relative kombinierte Unsicherheit für Q.
        """
        q_rel_B = self.q_rel_error(Qx, self.uB_D(r))
        return self.combine(uA_Q_rel, q_rel_B)

    def find_equiv_mode(
        self,
        meas_type: Literal["capacitance", "inductance", "impedance"],
        value_SI: float,
        freq_hz: int,
    ) -> str:
        """Liest den EQUIV-Modus aus dem passenden Bereich.

        Args:
            meas_type: Mess-Typ.
            value_SI: Messwert in SI.
            freq_hz: Frequenz in Hz.

        Returns:
            EQUIV-String (z. B. "SER" oder "PAR").

        Raises:
            ValueError: Wenn kein EQUIV für den Bereich angegeben ist.
        """
        blk = self.select_block(meas_type, freq_hz)
        r, _ = self.match_range(blk, value_SI)
        equiv = r.get("equiv", None)
        if equiv is None:
            raise ValueError(
                f"Kein EQUIV-Modus für {meas_type} bei {value_SI} (freq {freq_hz})"
            )
        return equiv


__all__ = ["MeasurementError"]
