"""Plot controller for live LCR measurement visualisation."""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg


class PlotController(QtCore.QObject):
    """Encapsulates all pyqtgraph handling for the LCR plots."""

    def __init__(self, container: QtWidgets.QWidget, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._container = container
        self._measurement_name: Optional[str] = None
        self._measurement_points: Dict[float, Dict[str, Any]] = {}

        self._primary_curve: Optional[pg.PlotDataItem] = None
        self._primary_error: Optional[pg.ErrorBarItem] = None
        self._secondary_curve: Optional[pg.PlotDataItem] = None
        self._secondary_error: Optional[pg.ErrorBarItem] = None

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

    def reset(self) -> None:
        """Remove all measurement data and clear the plots."""
        self._measurement_points.clear()
        self._primary_curve = None
        self._primary_error = None
        self._secondary_curve = None
        self._secondary_error = None

        self.primary_plot.clear()
        self.secondary_plot.clear()
        self.primary_plot.setLabel("left", "Primärparameter")
        self.secondary_plot.setLabel("left", "Sekundärparameter")
        self.primary_plot.setTitle(self._measurement_name or "")

    def start_measurement(self, measurement_name: str) -> None:
        """Prepare the plots for a new measurement run."""
        self._measurement_name = measurement_name
        self.reset()

    def finish_measurement(self, results: List[Dict[str, Any]]) -> None:
        """Optionally backfill plots from a batch of measurement results."""
        if not results:
            return

        for entry in results:
            self._ingest_measurement(entry)
        self._update_plots()

    @QtCore.Slot(dict)
    def handle_measurement(self, data: Dict[str, Any]) -> None:
        """Update plots with a single measurement sample."""
        if not data:
            return
        self._ingest_measurement(data)
        self._update_plots()

    def _ingest_measurement(self, data: Dict[str, Any]) -> None:
        frequency = data.get("frequency_hz")
        if frequency is None:
            return

        freq = float(frequency)
        self._measurement_points[freq] = data

    def _update_plots(self) -> None:
        if not self._measurement_points:
            return

        sorted_freqs = sorted(self._measurement_points.keys())
        plot_freqs: List[float] = []
        primary_values: List[float] = []
        secondary_values: List[float] = []
        primary_uncertainties: List[float] = []
        secondary_uncertainties: List[float] = []
        primary_name: Optional[str] = None
        secondary_name: Optional[str] = None

        for freq in sorted_freqs:
            entry = self._measurement_points[freq]
            primary_val = entry.get("primary_value")
            secondary_val = entry.get("secondary_value")
            if primary_val is None or secondary_val is None:
                continue

            plot_freqs.append(freq)
            primary_values.append(float(primary_val))
            secondary_values.append(float(secondary_val))
            primary_uncertainties.append(float(entry.get("primary_uncertainty") or 0.0))
            secondary_uncertainties.append(float(entry.get("secondary_uncertainty") or 0.0))
            primary_name = entry.get("primary_name", primary_name)
            secondary_name = entry.get("secondary_name", secondary_name)

        if not plot_freqs:
            return

        self._update_primary_plot(plot_freqs, primary_values, primary_uncertainties, primary_name)
        self._update_secondary_plot(
            plot_freqs, secondary_values, secondary_uncertainties, secondary_name
        )

    def _update_primary_plot(
        self,
        freqs: List[float],
        values: List[float],
        uncertainties: List[float],
        label: Optional[str],
    ) -> None:
        pen = pg.mkPen(color="#0072f5", width=2)
        symbol_brush = pg.mkBrush("#0072f5")

        if self._primary_curve is None:
            self._primary_curve = self.primary_plot.plot(
                freqs,
                values,
                pen=pen,
                symbol="o",
                symbolBrush=symbol_brush,
                symbolSize=8,
            )
        else:
            self._primary_curve.setData(freqs, values)

        if self._primary_error is None:
            self._primary_error = pg.ErrorBarItem(
                x=freqs,
                y=values,
                top=uncertainties,
                bottom=uncertainties,
                beam=0.1,
                pen=pen,
            )
            self.primary_plot.addItem(self._primary_error)
        else:
            self._primary_error.setData(x=freqs, y=values, top=uncertainties, bottom=uncertainties)

        self.primary_plot.setLabel("left", label or "Primärparameter")
        self.primary_plot.setTitle(self._measurement_name or "")

    def _update_secondary_plot(
        self,
        freqs: List[float],
        values: List[float],
        uncertainties: List[float],
        label: Optional[str],
    ) -> None:
        pen = pg.mkPen(color="#f59f00", width=2)
        symbol_brush = pg.mkBrush("#f59f00")

        if self._secondary_curve is None:
            self._secondary_curve = self.secondary_plot.plot(
                freqs,
                values,
                pen=pen,
                symbol="s",
                symbolBrush=symbol_brush,
                symbolSize=7,
            )
        else:
            self._secondary_curve.setData(freqs, values)

        if self._secondary_error is None:
            self._secondary_error = pg.ErrorBarItem(
                x=freqs,
                y=values,
                top=uncertainties,
                bottom=uncertainties,
                beam=0.1,
                pen=pen,
            )
            self.secondary_plot.addItem(self._secondary_error)
        else:
            self._secondary_error.setData(x=freqs, y=values, top=uncertainties, bottom=uncertainties)

        self.secondary_plot.setLabel("left", label or "Sekundärparameter")
