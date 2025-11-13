"""Kleines Demo-Programm, das PlotController verwendet und Messpunkte mit Unsicherheiten anzeigt.

Starten mit:
    python src/demo_plot_controller.py

Benötigt: PySide6, pyqtgraph, numpy
"""

import sys
import pathlib
import numpy as np
from PySide6 import QtWidgets

# Make sure project root is on sys.path so the `src` package can be imported
# This allows running the script as: python src/demo_plot_controller.py
project_root = pathlib.Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.plot_controller import PlotController


def make_sample(
    freq, volt, prim_val, sec_val, prim_unc, sec_unc, p_name="Prim", s_name="Sek"
):
    return {
        "frequency_hz": float(freq),
        "voltage_v": float(volt),
        "primary_value": float(prim_val),
        "secondary_value": float(sec_val),
        "primary_uncertainty": float(prim_unc),
        "secondary_uncertainty": float(sec_unc),
        "primary_name": p_name,
        "secondary_name": s_name,
    }


def populate(controller: PlotController):
    """Populate the controller with example measurement data from a CSV file.

    The CSV is expected to have columns: freq_hz, level_v, Z, theta_deg, u_primary, u_secondary
    We convert level_v (V) to mV for the controller so the coloring matches existing logic.
    Only frequencies within 100..40000 Hz are used for the demo.
    """
    import csv

    demo_file = (
        pathlib.Path(__file__).resolve().parent.parent
        / "measurements"
        / "resistor_20251017_150007.csv"
    )
    FMIN = 100.0
    FMAX = 40000.0
    if not demo_file.exists():
        # fallback to the simple synthetic data if CSV not present
        freqs = np.array([100.0, 200.0, 500.0, 1000.0, 2000.0, 5000.0, 10000.0])
        voltages = [300.0, 600.0]
        for volt in voltages:
            for f in freqs:
                prim = (1e3 / f) * (1 + volt / 1000.0) * 10.0
                sec = np.log10(f) * 2.0 * (volt / 300.0)
                prim_unc = max(0.01 * abs(prim), 0.05)
                sec_unc = max(0.03 * abs(sec), 0.01)
                sample = make_sample(
                    freq=f,
                    volt=volt,
                    prim_val=prim,
                    sec_val=sec,
                    prim_unc=prim_unc,
                    sec_unc=sec_unc,
                    p_name="Impedanz",
                    s_name="Phase",
                )
                controller.handle_measurement(sample)
        return

    with demo_file.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                f = float(row.get("freq_hz", "nan"))
            except Exception:
                continue
            if not (FMIN <= f <= FMAX):
                # skip out-of-range frequencies for this demo
                continue

            try:
                level_v = float(row.get("level_v", 0.0))
            except Exception:
                level_v = 0.0

            # convert V -> mV for color mapping
            volt_mV = level_v * 1000.0

            try:
                z = float(row.get("Z", "nan"))
            except Exception:
                z = float("nan")
            try:
                theta = float(row.get("theta_deg", "nan"))
            except Exception:
                theta = float("nan")

            try:
                uprim = float(row.get("u_primary", 0.0))
            except Exception:
                uprim = 0.0
            try:
                usec = float(row.get("u_secondary", 0.0))
            except Exception:
                usec = 0.0

            sample = make_sample(
                freq=f,
                volt=volt_mV,
                prim_val=z,
                sec_val=theta,
                prim_unc=uprim,
                sec_unc=usec,
                p_name="Z",
                s_name="theta_deg",
            )
            controller.handle_measurement(sample)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget()
    window.setWindowTitle("PlotController Demo — Unsicherheiten")
    window.resize(900, 700)

    # PlotController erstellt selbst das Layout im übergebenen Container-Widget.
    # Deshalb nicht hier nochmal ein Layout auf das Fenster setzen (doppelte Layouts
    # führen zu Qt-Warnungen und unerwartetem Verhalten).
    plot_ctrl = PlotController(container=window)

    # populate with demo data
    plot_ctrl.start_measurement("Demo Messung")
    populate(plot_ctrl)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
