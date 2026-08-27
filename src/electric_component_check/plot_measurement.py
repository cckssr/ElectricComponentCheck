import argparse
import glob
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class MeasurementPlotter:
    """Klasse zum Plotten von LCR-Messdaten mit automatischer Skalierung."""

    # SI-Präfixe und Einheiten
    SI_PREFIXES = [
        (1e-12, "p"),
        (1e-9, "n"),
        (1e-6, "µ"),
        (1e-3, "m"),
        (1, ""),
        (1e3, "k"),
        (1e6, "M"),
        (1e9, "G"),
    ]

    UNIT_MAP = {
        "C": "F",
        "L": "H",
        "R": "Ω",
        "Z": "Ω",
        "theta_deg": "°",
    }

    PHYS_LABELS = {
        "C": "Kapazität",
        "L": "Induktivität",
        "R": "Widerstand",
        "Z": "Impedanz",
        "D": "Verlustfaktor",
        "Q": "Güte",
        "theta_deg": "Phasenwinkel θ",
    }

    def __init__(self, df: pd.DataFrame):
        """Initialisiert den Plotter mit einem DataFrame.

        Args:
            df: DataFrame mit Messdaten (erwartet Spalten: freq_hz, level_v, u_primary, u_secondary)
        """
        self.df = df

    @staticmethod
    def get_color(level):
        """Gibt Farbe basierend auf Spannungslevel zurück.

        Args:
            level: Spannungslevel in Volt.

        Returns:
            str: Matplotlib-Farbname (z.B. "tab:blue", "tab:orange", "gray").
        """
        if abs(level - 0.3) < 0.05:
            return "tab:blue"
        if abs(level - 0.6) < 0.05:
            return "tab:orange"
        return "gray"

    @classmethod
    def auto_scale(cls, values):
        """Bestimmt automatisch den besten SI-Präfix für die Werte.

        Args:
            values: Array oder Liste von numerischen Werten.

        Returns:
            tuple: (Skalierungsfaktor, Präfix-String) z.B. (1e-6, "µ")
        """
        absmax = np.nanmax(np.abs(values))
        for factor, prefix in reversed(cls.SI_PREFIXES):
            if absmax >= factor:
                return factor, prefix
        return 1, ""

    @classmethod
    def format_axis_label(cls, col, values):
        """Formatiert Achsenbeschriftung mit Einheit und SI-Präfix.

        Args:
            col: Spaltenname (z.B. "C", "L", "R", "Z", "theta_deg").
            values: Array oder Liste von numerischen Werten für Skalierung.

        Returns:
            tuple: (Formatierte Beschriftung, Skalierungsfaktor)
                   z.B. ("Kapazität (µF)", 1e-6)
        """
        unit = cls.UNIT_MAP.get(col, "")
        label = cls.PHYS_LABELS.get(col, col)
        factor, prefix = cls.auto_scale(values)
        if unit:
            return f"{label} ({prefix}{unit})", factor
        else:
            return f"{label}", factor

    def plot(self, title=None, output_path=None, show=True):
        """Erstellt den Plot mit zwei Subplots.

        Erstellt einen Plot mit zwei übereinander angeordneten Subplots:
        - Oben: Primary-Messwert (2/3 der Höhe)
        - Unten: Secondary-Messwert (1/3 der Höhe)

        Beide Plots teilen sich die x-Achse (Frequenz, logarithmisch).
        Fehlerbalken werden für beide Messgrößen dargestellt.

        Args:
            title: Titel des Plots (optional). Wenn None, wird kein Titel gesetzt.
            output_path: Pfad zum Speichern des Plots als PDF/PNG (optional).
                        Unterstützt alle von matplotlib unterstützten Formate.
                        Wenn None, wird nicht gespeichert.
            show: Ob der Plot interaktiv angezeigt werden soll (Standard: True).
                  Bei False wird nur gespeichert (wenn output_path angegeben).

        Returns:
            tuple: (fig, (ax1, ax2)) - Matplotlib Figure und Axes Objekte.
                   - fig: matplotlib.figure.Figure
                   - ax1: oberer Subplot (Primary)
                   - ax2: unterer Subplot (Secondary)

        Example:
            >>> plotter = MeasurementPlotter(df)
            >>> fig, (ax1, ax2) = plotter.plot(title="Test", output_path="plot.pdf")
            >>> # Weitere Anpassungen möglich:
            >>> ax1.set_title("Zusätzlicher Titel")
            >>> fig.savefig("modified_plot.pdf")
        """
        # Zwei Subplots übereinander mit gemeinsamer x-Achse
        # height_ratios=[2, 1] bedeutet: Primary 2/3, Secondary 1/3
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(10, 8), sharex=True, gridspec_kw={"height_ratios": [2, 1]}
        )

        primary_col = self.df.columns[4]
        secondary_col = self.df.columns[5]
        primary_values = self.df[primary_col].values
        secondary_values = self.df[secondary_col].values
        primary_label, primary_factor = self.format_axis_label(primary_col, primary_values)
        secondary_label, secondary_factor = self.format_axis_label(secondary_col, secondary_values)

        # Primary Plot (oben)
        for lvl, group in self.df.groupby("level_v"):
            ax1.errorbar(
                group["freq_hz"],
                group[primary_col] / primary_factor,
                yerr=group["u_primary"] / primary_factor,
                fmt="o-",
                label=f"{lvl} V",
                color=self.get_color(lvl),
                capsize=5,
                capthick=1.5,
            )

        ax1.set_ylabel(primary_label)
        ax1.set_xscale("log")
        ax1.legend(loc="best")
        ax1.grid(True, alpha=0.3)

        # Secondary Plot (unten)
        for lvl, group in self.df.groupby("level_v"):
            ax2.errorbar(
                group["freq_hz"],
                group[secondary_col] / secondary_factor,
                yerr=group["u_secondary"] / secondary_factor,
                fmt="s-",
                label=f"{lvl} V",
                color=self.get_color(lvl),
                capsize=5,
                capthick=1.5,
            )

        ax2.set_xlabel("Frequenz (Hz)")
        ax2.set_ylabel(secondary_label)
        ax2.set_xscale("log")
        xmin = self.df["freq_hz"].min()
        xmax = self.df["freq_hz"].max()
        ax2.set_xlim(xmin * 0.8, xmax * 1.2)
        ax2.legend(loc="best")
        ax2.grid(True, alpha=0.3)

        if title:
            fig.suptitle(title, fontsize=12)

        plt.tight_layout()

        # Speichern falls Pfad angegeben
        if output_path:
            output_path = Path(output_path)
            fig.savefig(output_path, bbox_inches="tight", dpi=300)
            print(f"Plot gespeichert: {output_path}")

        # Anzeigen falls gewünscht
        if show:
            plt.show()

        return fig, (ax1, ax2)


# Neueste CSV im measurements-Ordner finden
def get_latest_csv(folder="measurements"):
    """Findet die neueste CSV-Datei im angegebenen Ordner.

    Args:
        folder: Pfad zum Ordner (Standard: "measurements").

    Returns:
        str: Pfad zur neuesten CSV-Datei.

    Raises:
        FileNotFoundError: Wenn keine CSV-Datei gefunden wurde.
    """
    files = glob.glob(os.path.join(folder, "*.csv"))
    if not files:
        raise FileNotFoundError("Keine Mess-CSV gefunden!")
    return max(files, key=os.path.getctime)


# Hauptprogramm für direkte Verwendung
if __name__ == "__main__":
    # Argument-Parser für alternativen CSV-Pfad
    parser = argparse.ArgumentParser(description="Messdaten plotten")
    parser.add_argument("--csv", type=str, help="Pfad zur CSV-Datei", default=None)
    parser.add_argument("--title", type=str, help="Titel des Plots", default=None)
    parser.add_argument("--output", type=str, help="Ausgabepfad für PDF/PNG", default=None)
    parser.add_argument(
        "--no-show", action="store_true", help="Plot nicht anzeigen (nur speichern)"
    )
    args = parser.parse_args()

    if args.csv:
        csv_path = args.csv
        if not os.path.isfile(csv_path):
            raise FileNotFoundError(f"Datei nicht gefunden: {csv_path}")
    else:
        csv_path = get_latest_csv()

    print(f"Lade Datei: {csv_path}")
    df = pd.read_csv(csv_path)

    # Titel generieren falls nicht angegeben
    title = args.title if args.title else f"Messung: {os.path.basename(csv_path)}"

    # Plotter erstellen und Plot generieren
    plotter = MeasurementPlotter(df)
    fig, axes = plotter.plot(title=title, output_path=args.output, show=not args.no_show)
