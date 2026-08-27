"""Plot controller for live LCR measurement visualisation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets


class PlotController(QtCore.QObject):
    """Encapsulates all pyqtgraph handling for the LCR plots."""

    def __init__(self, container: QtWidgets.QWidget, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._measurement_name: str | None = None
        # Speichert Messpunkte nach (Frequenz, Spannungslevel in mV) -> Messdaten
        self._measurement_points: dict[tuple[float, int], dict[str, Any]] = {}

        # Plot-Items je Spannungslevel (mV)
        # Format: {level_mv: curve} (ohne Fehlerbalken)
        self._primary_items: dict[int, pg.PlotDataItem] = {}
        self._secondary_items: dict[int, pg.PlotDataItem] = {}

        self.primary_plot = pg.PlotWidget(parent=container)
        self.secondary_plot = pg.PlotWidget(parent=container)

        self._setup_layout()
        self.reset()

    def _setup_layout(self) -> None:
        layout = QtWidgets.QVBoxLayout(self._container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.primary_plot, stretch=2)
        layout.addWidget(self.secondary_plot, stretch=1)

        self.primary_plot.setLogMode(x=True, y=False)
        self.secondary_plot.setLogMode(x=True, y=False)
        self.secondary_plot.setXLink(self.primary_plot)

        for plot in (self.primary_plot, self.secondary_plot):
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.getPlotItem().setMenuEnabled(False)

        self.primary_plot.setLabel("bottom", "")
        self.secondary_plot.setLabel("bottom", "Frequenz (Hz)")
        # Erstelle die Legenden hier einmalig, bevor Kurven geplottet werden.
        pitem = self.primary_plot.getPlotItem()
        if getattr(pitem, "legend", None) is None and getattr(pitem, "addLegend", None) is not None:
            pitem.addLegend()
        sitem = self.secondary_plot.getPlotItem()
        if getattr(sitem, "legend", None) is None and getattr(sitem, "addLegend", None) is not None:
            sitem.addLegend()

    def reset(self) -> None:
        """Remove all measurement data and clear the plots."""
        self._measurement_points.clear()
        self._primary_items.clear()
        self._secondary_items.clear()

        self.primary_plot.clear()
        self.secondary_plot.clear()
        # Nach dem Clear die Legenden neu anlegen (clear() entfernt sie unter Umständen)
        pitem = self.primary_plot.getPlotItem()
        if getattr(pitem, "legend", None) is None and getattr(pitem, "addLegend", None) is not None:
            pitem.addLegend()
        sitem = self.secondary_plot.getPlotItem()
        if getattr(sitem, "legend", None) is None and getattr(sitem, "addLegend", None) is not None:
            sitem.addLegend()
        self.primary_plot.setLabel("left", "Primärparameter")
        self.secondary_plot.setLabel("left", "Sekundärparameter")
        self.primary_plot.setTitle(self._measurement_name or "")

    def start_measurement(self, measurement_name: str) -> None:
        """Prepare the plots for a new measurement run."""
        self._measurement_name = measurement_name
        self.reset()

    def finish_measurement(self, results: list[dict[str, Any]]) -> None:
        """Optionally backfill plots from a batch of measurement results."""
        if not results:
            return

        for entry in results:
            self._ingest_measurement(entry)
        self._update_plots()

    @QtCore.Slot(dict)
    def handle_measurement(self, data: dict[str, Any]) -> None:
        """Update plots with a single measurement sample."""
        if not data:
            return
        self._ingest_measurement(data)
        self._update_plots()

    def _ingest_measurement(self, data: dict[str, Any]) -> None:
        frequency = data.get("frequency_hz")
        level_mv = data.get("level_mv")
        if frequency is None or level_mv is None:
            return

        freq = float(frequency)
        self._measurement_points[(freq, int(level_mv))] = data

    def _update_plots(self) -> None:
        if not self._measurement_points:
            return

        # Gruppiere Messungen nach Spannungslevel (mV)
        voltages_data: dict[int, dict[str, list[Any]]] = {}

        for (freq, level_mv), entry in self._measurement_points.items():
            if level_mv not in voltages_data:
                voltages_data[level_mv] = {
                    "freqs": [],
                    "primary_values": [],
                    "secondary_values": [],
                    "primary_uncertainties": [],
                    "secondary_uncertainties": [],
                    "primary_name": None,
                    "secondary_name": None,
                }

            primary_val = entry.get("primary_value")
            secondary_val = entry.get("secondary_value")

            # Validiere Werte
            if (
                primary_val is None
                or secondary_val is None
                or abs(primary_val) >= 1e50
                or abs(secondary_val) >= 1e50
            ):
                continue

            data = voltages_data[level_mv]
            data["freqs"].append(freq)
            data["primary_values"].append(float(primary_val))
            data["secondary_values"].append(float(secondary_val))
            data["primary_uncertainties"].append(float(entry.get("primary_uncertainty") or 0.0))
            data["secondary_uncertainties"].append(float(entry.get("secondary_uncertainty") or 0.0))
            data["primary_name"] = entry.get("primary_name", data["primary_name"])
            data["secondary_name"] = entry.get("secondary_name", data["secondary_name"])

        # Sortiere und plotte für jedes Spannungslevel
        for level_mv in sorted(voltages_data.keys()):
            data = voltages_data[level_mv]

            # Sortiere nach Frequenz
            if not data["freqs"]:
                continue

            sorted_indices = np.argsort(data["freqs"])
            freqs_sorted = np.array(data["freqs"])[sorted_indices]
            primary_sorted = np.array(data["primary_values"])[sorted_indices]
            secondary_sorted = np.array(data["secondary_values"])[sorted_indices]
            primary_unc_sorted = np.array(data["primary_uncertainties"])[sorted_indices]
            secondary_unc_sorted = np.array(data["secondary_uncertainties"])[sorted_indices]

            self._update_primary_plot(
                level_mv,
                freqs_sorted,
                primary_sorted,
                primary_unc_sorted,
                data["primary_name"],
            )
            self._update_secondary_plot(
                level_mv,
                freqs_sorted,
                secondary_sorted,
                secondary_unc_sorted,
                data["secondary_name"],
            )

    def _update_primary_plot(
        self,
        level_mv: int,
        freqs: np.ndarray,
        values: np.ndarray,
        uncertainties: np.ndarray,
        label: str | None,
    ) -> None:
        # Farbwahl basierend auf dem Spannungslevel (mVrms, nur 300/600 möglich)
        colors = {300: "#0072f5", 600: "#ff6b6b"}  # blau für 300mV, rot für 600mV
        color = colors.get(level_mv, "#0072f5")

        pen = pg.mkPen(color=color, width=2)
        symbol_brush = pg.mkBrush(color)

        # Legende wird einmal in _setup_layout() erstellt; hier nicht erneut anlegen.

        # Hole oder erstelle Plot-Items für dieses Spannungslevel
        if level_mv not in self._primary_items:
            curve = self.primary_plot.plot(
                freqs,
                values,
                pen=pen,
                symbol="o",
                symbolBrush=symbol_brush,
                symbolSize=8,
                name=f"{level_mv}mV",
            )
            self._primary_items[level_mv] = curve
        else:
            curve = self._primary_items[level_mv]
            curve.setData(freqs, values)

        self.primary_plot.setLabel("left", label or "Primärparameter")
        self.primary_plot.setTitle(self._measurement_name or "")

    def _update_secondary_plot(
        self,
        level_mv: int,
        freqs: np.ndarray,
        values: np.ndarray,
        uncertainties: np.ndarray,
        label: str | None,
    ) -> None:
        # Farbwahl basierend auf dem Spannungslevel (mVrms, nur 300/600 möglich)
        colors = {
            300: "#f59f00",
            600: "#c92a2a",
        }  # orange für 300mV, dunkelrot für 600mV
        color = colors.get(level_mv, "#f59f00")

        pen = pg.mkPen(color=color, width=2)
        symbol_brush = pg.mkBrush(color)

        # Legende wird einmal in _setup_layout() erstellt; hier nicht erneut anlegen.

        # Hole oder erstelle Plot-Items für dieses Spannungslevel
        if level_mv not in self._secondary_items:
            curve = self.secondary_plot.plot(
                freqs,
                values,
                pen=pen,
                symbol="s",
                symbolBrush=symbol_brush,
                symbolSize=7,
                name=f"{level_mv}mV",
            )
            self._secondary_items[level_mv] = curve
        else:
            curve = self._secondary_items[level_mv]
            curve.setData(freqs, values)

        self.secondary_plot.setLabel("left", label or "Sekundärparameter")
        # Legendenerstellung erfolgt weiter oben (vor dem Erstellen der Kurve)
