"""Headless debug for PlotController: create controller, add demo points and print errbar info."""

import sys
import pathlib

project_root = pathlib.Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import numpy as np
from PySide6 import QtWidgets
import pyqtgraph as pg

# Ensure a QApplication exists so QWidget subclasses can be created
app = QtWidgets.QApplication([])


class DummyCurve:
    def __init__(self, x=None, y=None, **_kwargs):
        self.x = x
        self.y = y

    def setData(self, x, y):
        self.x = x
        self.y = y


class DummyPlotWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []

    def plot(self, x, y, **_kwargs):
        c = DummyCurve(x, y)
        self._items.append(c)
        return c

    def addItem(self, item):
        self._items.append(item)

    def removeItem(self, item):
        try:
            self._items.remove(item)
        except ValueError:
            pass

    def clear(self):
        self._items.clear()

    def setLabel(self, *args, **kwargs):
        pass

    def setTitle(self, *args, **kwargs):
        pass

    def addLegend(self):
        pass

    def setLogMode(self, *args, **kwargs):
        pass

    def setXLink(self, *args, **kwargs):
        pass

    def showGrid(self, *args, **kwargs):
        pass

    def getPlotItem(self):
        # return self (has setMenuEnabled)
        return self

    def setMenuEnabled(self, enabled: bool):
        # no-op for stub
        pass


class DummyErrorBar:
    def __init__(self, x=None, y=None, top=None, bottom=None, pen=None):
        self.x = x
        self.y = y
        self.top = top
        self.bottom = bottom

    def setData(self, x=None, y=None, top=None, bottom=None):
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        if top is not None:
            self.top = top
        if bottom is not None:
            self.bottom = bottom


# Monkeypatch pg to use stubs that are QWidget-compatible
pg.PlotWidget = DummyPlotWidget
pg.ErrorBarItem = DummyErrorBar

from src.plot_controller import PlotController

# Create controller without opening GUI (container may be None but _setup_layout expects a QWidget)
container = QtWidgets.QWidget()
ctrl = PlotController(container=container)
ctrl.start_measurement("debug")

# Add a few demo points with uncertainties
freqs = [100.0, 200.0, 500.0, 1000.0]
for volt in (300.0, 600.0):
    for f in freqs:
        prim = (1e3 / f) * (1 + volt / 1000.0) * 10.0
        sec = np.log10(f) * 2.0 * (volt / 300.0)
        prim_unc = max(0.01 * abs(prim), 0.05)
        sec_unc = max(0.03 * abs(sec), 0.01)
        sample = {
            "frequency_hz": float(f),
            "voltage_v": float(volt),
            "primary_value": float(prim),
            "secondary_value": float(sec),
            "primary_uncertainty": float(prim_unc),
            "secondary_uncertainty": float(sec_unc),
            "primary_name": "Impedanz",
            "secondary_name": "Phase",
        }
        ctrl.handle_measurement(sample)

# Now print internal state
print("primary_items:", list(ctrl._primary_items.keys()))
print("secondary_items:", list(ctrl._secondary_items.keys()))
print("primary_errbars keys:", list(ctrl._primary_errbars.keys()))
print("secondary_errbars keys:", list(ctrl._secondary_errbars.keys()))

# If errbars exist, print a little info
for v, eb in ctrl._primary_errbars.items():
    print("primary errbar for", v, "object:", type(eb))
for v, eb in ctrl._secondary_errbars.items():
    print("secondary errbar for", v, "object:", type(eb))

print("done")
app.quit()
