from ui.calibration_ui import Ui_Dialog
from PySide6.QtWidgets import QApplication

import sys
from PySide6.QtWidgets import QDialog


def main():
    app = QApplication(sys.argv)
    dialog = QDialog()
    ui = Ui_Dialog()
    ui.setupUi(dialog)
    dialog.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
