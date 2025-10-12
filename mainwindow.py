# This Python file uses the following encoding: utf-8
import sys
import os

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6 import QtWidgets, QtCore

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from ui_form import Ui_MainWindow

from openbis_controller import OpenBISController


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # Start periodic UI updates (demo progress)
        self._start_progress_timer()
        self.openbis = self._init_openbis()
        self.init_sections()

    def _init_openbis(self):
        SERVER_URL = "https://openbis.physik.tu-berlin.de"
        session_token = self.ui.session_token.text().strip()
        session_token = (
            "cedric.kessler-251012143258126xE490F2FA3DC13C9A12B039FDAC8584CD"
        )
        try:
            controller = OpenBISController(SERVER_URL, session_token)
            self.ui.openbis_progress_text.setText("Erfolgreich mit OpenBIS verbunden")
            response = controller
        except ValueError as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Verbindung zu OpenBIS fehlgeschlagen: {e}",
            )
            response = None

        self._progress_timer.stop()
        self.ui.openbis_progress.setValue(100)
        return response

    def init_sections(self):
        sections = {
            "capacitor": "Kondensator",
            "fuse": "Gerätesicherung",
            "inductor": "Spule / Induktivitäten",
            "resistor": "Widerstand",
            "switch_2": "Schalter",
            "transistor": "Transistor",
        }
        for key, value in sections.items():
            section = getattr(self.ui, key, None)
            if not section or not hasattr(section, "layout"):
                continue

            layout = section.layout()
            if layout is None:
                continue

            label = QtWidgets.QLabel(value)
            line_edit = QtWidgets.QLineEdit()

            # Match existing label style: Fixed horizontal, Preferred vertical, min width 150
            label_sp = QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Preferred,
            )
            label_sp.setHorizontalStretch(0)
            label_sp.setVerticalStretch(0)
            label.setSizePolicy(label_sp)
            label.setMinimumSize(QtCore.QSize(150, 0))

            # Match existing field style: MinimumExpanding horizontal, Fixed vertical
            field_sp = QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            field_sp.setHorizontalStretch(0)
            field_sp.setVerticalStretch(0)
            line_edit.setSizePolicy(field_sp)

            # Ensure correct placement in a QFormLayout (label left, field right)
            if hasattr(layout, "addRow"):
                # Ensure fields can grow horizontally similar to other form sections
                if hasattr(layout, "setFieldGrowthPolicy"):
                    layout.setFieldGrowthPolicy(
                        QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
                    )
                layout.addRow(label, line_edit)
            else:
                # Fallback: try to add sequentially if it's not a form layout
                # (keeps compatibility if the UI changes layout type)
                layout.addWidget(label)
                layout.addWidget(line_edit)

    def _start_progress_timer(self):
        self._progress_timer = QtCore.QTimer(self)
        self._progress_timer.setInterval(200)  # 200 ms
        self._progress_timer.timeout.connect(self._tick_progress)
        self._progress_timer.start()

    def _tick_progress(self):
        bar = self.ui.openbis_progress
        current = bar.value()
        maximum = bar.maximum() if bar.maximum() > 0 else 100
        step = 10
        next_val = current + step
        if next_val > maximum:
            next_val = 0
        bar.setValue(next_val)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
