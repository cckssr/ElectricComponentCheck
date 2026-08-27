# This Python file uses the following encoding: utf-8
import sys
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from pyvisa import ResourceManager

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6 import QtWidgets, QtCore

from ui.form_ui import Ui_MainWindow
from ui.calibration_ui import Ui_Dialog as Ui_CalibrationDialog
from openbis_controller import OpenBISController
from lcr_controller import LCRController, LCRMeasurementWorker
from plot_controller import PlotController

SERVER_URL = "https://openbis.physik.tu-berlin.de"


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.openbis_controller: Optional[OpenBISController] = None
        self.lcr_controller: Optional[LCRController] = None
        self.current_object_data: Optional[dict] = (
            None  # Speichert aktuelle Objektdaten
        )
        self.initial_field_values: Dict[str, Any] = {}  # Speichert initiale Feldwerte
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Statusflags für LCR-Integration
        self._lcr_connected = False
        self._measurement_running = False
        self._measurement_thread: Optional[QtCore.QThread] = None
        self._measurement_worker: Optional[LCRMeasurementWorker] = None
        self._current_measurement_name: Optional[str] = None

        # Kalibrierungsstatus
        self._calibration_open_done = False
        self._calibration_short_done = False

        # Plot-Controller kapselt alle Plot-bezogenen Operationen
        self.plot_controller = PlotController(self.ui.plot_widget, self)
        self._init_connections()
        self._update_lcr_measurement_state()

    def _init_connections(self):
        """Initialisiert UI-Verbindungen und Controller."""
        # OpenBIS-Verbindungen
        self.ui.session_token.returnPressed.connect(self._on_st_changed)
        self.ui.openbis_progress.setText("Warten auf Session Token...")
        self.ui.barcode.returnPressed.connect(self._on_barcode_entered)
        self.ui.openbis_upload.clicked.connect(self._on_openbis_save_clicked)

        # LCR-Verbindungen
        self.ui.lcr_refresh_resource.clicked.connect(self._refresh_instruments)
        self.ui.lcr_resource.currentIndexChanged.connect(self._on_resource_changed)
        self.ui.lcr_startmeasurement.clicked.connect(self._on_lcr_start_measurement)
        self.ui.lcr_calibrate.clicked.connect(self._on_lcr_calibrate_clicked)
        self.ui.barcode.textChanged.connect(self._update_lcr_measurement_state)

        # Type-ComboBox Verbindung
        self.ui.type.currentIndexChanged.connect(self._on_type_changed)

        # Initiale Geräte-Suche
        self._refresh_instruments()

        # Initiale Deaktivierung aller specific-Felder außer der ersten Seite
        self._initialize_specific_fields()

    def _initialize_specific_fields(self):
        """
        Initialisiert die specific-Felder beim Start:
        - Alle Seiten werden zunächst deaktiviert
        - Nur die aktuell ausgewählte Seite (basierend auf type) wird aktiviert
        """
        # Deaktiviere zunächst alle Seiten
        pages = [
            self.ui.resistor,
            self.ui.capacitor,
            self.ui.inductor,
            self.ui.transistor,
            self.ui.switch_2,
            self.ui.fuse,
        ]

        for page in pages:
            self._set_page_fields_enabled(page, False)

        # Aktiviere nur die Felder der aktuell ausgewählten Seite
        current_type_index = self.ui.type.currentIndex()
        if current_type_index >= 0:
            self._update_specific_fields_enabled(current_type_index)

    def _get_selected_component(self) -> Optional[str]:
        """Gibt den aktuell messbaren Bauteiltyp zurück."""
        mapping = {0: "resistor", 1: "capacitor", 2: "inductor"}
        index = self.ui.type.currentIndex()
        return mapping.get(index)

    def _update_lcr_measurement_state(self) -> None:
        """Aktualisiert den Aktivierungszustand und Text des Mess-Buttons."""
        if self._measurement_running:
            # Während der Messung: Button wird zum Stop-Button
            self.ui.lcr_startmeasurement.setText("Messung stoppen")
            self.ui.lcr_startmeasurement.setEnabled(True)
        else:
            # Vor der Messung: Button wird zum Start-Button
            self.ui.lcr_startmeasurement.setText("LCR-Messung starten")
            barcode = self.ui.barcode.text().strip()
            component = self._get_selected_component()
            can_measure = (
                self.lcr_controller is not None
                and self._lcr_connected
                and bool(barcode)
                and component is not None
            )
            self.ui.lcr_startmeasurement.setEnabled(can_measure)

    def _build_measurement_name(self, barcode: str) -> str:
        """Erzeugt den Messungsnamen basierend auf Barcode und Zeitstempel."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{barcode}_{timestamp}"

    def _on_lcr_start_measurement(self):
        """Startet/Stoppt eine LCR-Messung."""
        # Wenn eine Messung läuft, stoppe sie
        if self._measurement_running:
            self._stop_measurement()
            return

        # Ansonsten starte eine neue Messung
        if not self.lcr_controller or not self.lcr_controller.is_connected():
            QMessageBox.warning(
                self,
                "LCR nicht verbunden",
                "Bitte verbinden Sie zuerst ein LCR-Gerät.",
            )
            return

        component = self._get_selected_component()
        if component is None:
            QMessageBox.warning(
                self,
                "Bauteil nicht messbar",
                "Für den ausgewählten Typ ist keine LCR-Messung möglich.",
            )
            return

        barcode = self.ui.barcode.text().strip()
        if not barcode:
            QMessageBox.warning(
                self,
                "Fehlender Barcode",
                "Bitte geben Sie zuerst einen Barcode ein.",
            )
            return

        self._measurement_running = True
        self._current_measurement_name = self._build_measurement_name(barcode)
        self.plot_controller.start_measurement(self._current_measurement_name)
        self._update_lcr_measurement_state()

        self._measurement_thread = QtCore.QThread(self)
        self._measurement_worker = LCRMeasurementWorker(
            self.lcr_controller,
            component,
            self._current_measurement_name,
        )
        self._measurement_worker.moveToThread(self._measurement_thread)

        self._measurement_thread.started.connect(self._measurement_worker.run)
        self._measurement_worker.finished.connect(self._on_measurement_finished)
        self._measurement_worker.failed.connect(self._on_measurement_failed)
        self._measurement_worker.finished.connect(self._measurement_thread.quit)
        self._measurement_worker.failed.connect(self._measurement_thread.quit)
        self._measurement_worker.finished.connect(self._measurement_worker.deleteLater)
        self._measurement_worker.failed.connect(self._measurement_worker.deleteLater)
        self._measurement_thread.finished.connect(self._cleanup_measurement_thread)
        self._measurement_thread.start()

        self._show_status(
            f"Messung '{self._current_measurement_name}' gestartet",
            level="info",
        )

    def _stop_measurement(self):
        """Stoppt die laufende Messung."""
        if not self._measurement_running:
            return

        # Setze Flag, damit der Worker aufhören kann
        if self._measurement_worker:
            self._measurement_worker.stop()

        self._show_status(
            "Messung wird abgebrochen...",
            level="warning",
            duration_ms=2000,
        )

    def _on_measurement_finished(
        self, measurement_name: str, results: List[Dict[str, Any]]
    ) -> None:
        """Wird aufgerufen, wenn die Messung erfolgreich beendet wurde."""
        self._measurement_running = False
        if results:
            self.plot_controller.finish_measurement(results)
            self._show_status(
                f"Messung '{measurement_name}' abgeschlossen",
                level="success",
                duration_ms=4000,
            )
        else:
            self._show_status(
                "Messung abgeschlossen, aber keine Daten erhalten",
                level="warning",
                duration_ms=4000,
            )

        self._update_lcr_measurement_state()

    def _on_measurement_failed(self, error: str) -> None:
        """Reagiert auf Fehler im Mess-Thread."""
        self._measurement_running = False
        self._show_status(error, level="error", duration_ms=5000)
        QMessageBox.critical(self, "Messfehler", error)
        self._update_lcr_measurement_state()

    def _cleanup_measurement_thread(self) -> None:
        """Aufräumen nach Thread-Ende."""
        if self._measurement_thread:
            self._measurement_thread.deleteLater()
        self._measurement_thread = None
        self._measurement_worker = None

    # ========================================================================
    # LCR-Controller Methoden
    # ========================================================================

    def _refresh_instruments(self):
        """Sucht nach verfügbaren LCR-Geräten."""
        rm = ResourceManager()
        instruments = rm.list_resources()
        self.ui.lcr_resource.clear()
        self.ui.lcr_resource.addItems(instruments)
        self.ui.lcr_resource.setCurrentIndex(-1)
        self.ui.lcr_progress.setText("Nicht verbunden")
        self._lcr_connected = False
        self._update_lcr_measurement_state()

        # Automatisch erstes USB-Gerät auswählen
        for inst in instruments:
            if inst.startswith("USB"):
                self.ui.lcr_resource.setCurrentText(inst)
                break

    def _on_resource_changed(self):
        """Wird aufgerufen, wenn ein LCR-Gerät ausgewählt wurde."""
        resource_name = self.ui.lcr_resource.currentText()
        if not resource_name:
            return

        # Trenne alte Verbindung falls vorhanden
        if self.lcr_controller and self.lcr_controller.is_connected():
            self.lcr_controller.disconnect_device()

        # Erstelle neuen Controller
        self.lcr_controller = LCRController(
            spec_path=Path(__file__).parent / "vcr_uncertainties.json",
            check_interval_ms=5000,
            debug=True,
        )

        # Verbinde Signale
        self._connect_lcr_signals()

        # Verbinde mit Gerät (Standard: Kondensator)
        self.lcr_controller.connect_device(resource_name, "capacitor")

    def _connect_lcr_signals(self):
        """Verbindet LCR-Controller-Signale mit UI-Updates."""
        if not self.lcr_controller:
            return

        self.lcr_controller.connected.connect(self._on_lcr_connected)
        self.lcr_controller.disconnected.connect(self._on_lcr_disconnected)
        self.lcr_controller.connection_lost.connect(self._on_lcr_connection_lost)
        self.lcr_controller.measurement_ready.connect(
            self.plot_controller.handle_measurement
        )
        self.lcr_controller.error_occurred.connect(self._on_lcr_error)
        self.lcr_controller.status_changed.connect(self._on_lcr_status)
        # Transiente Statusmeldungen für Statusbar
        self.lcr_controller.status_message.connect(self._on_status_message)

    def _on_lcr_connected(self, device_id: str):
        """LCR-Gerät erfolgreich verbunden."""
        self.ui.lcr_progress.setText(f"Verbunden: {device_id}")
        self.ui.lcr_progress.setStyleSheet("color: green;")
        self._lcr_connected = True
        self._update_lcr_measurement_state()
        self._update_calibration_button_state()

    def _on_lcr_disconnected(self):
        """LCR-Gerät getrennt."""
        self.ui.lcr_progress.setText("Verbindung getrennt")
        self.ui.lcr_progress.setStyleSheet("")
        self._lcr_connected = False
        self._update_lcr_measurement_state()
        self._update_calibration_button_state()

    def _on_lcr_connection_lost(self):
        """LCR-Verbindung verloren."""
        self.ui.lcr_progress.setText("Verbindung verloren!")
        self.ui.lcr_progress.setStyleSheet("color: red;")
        QMessageBox.warning(
            self, "Verbindungsfehler", "Verbindung zum LCR-Gerät verloren!"
        )
        self._lcr_connected = False
        self._update_lcr_measurement_state()
        self._update_calibration_button_state()

    def _on_lcr_error(self, error_msg: str):
        """LCR-Fehler aufgetreten."""
        # Fehler nur transient in der Statusbar anzeigen
        self._show_status(error_msg, level="error", duration_ms=6000)

    def _on_lcr_status(self, status: str):
        """LCR-Status geändert."""
        self.ui.lcr_progress.setText(status)

    def _update_calibration_button_state(self) -> None:
        """Aktualisiert den Aktivierungszustand des Kalibrierungs-Buttons."""
        can_calibrate = self.lcr_controller is not None and self._lcr_connected
        self.ui.lcr_calibrate.setEnabled(can_calibrate)

    def _on_lcr_calibrate_clicked(self):
        """Öffnet den Kalibrierungs-Dialog und speichert den Status."""
        if not self.lcr_controller or not self._lcr_connected:
            QMessageBox.warning(
                self,
                "LCR nicht verbunden",
                "Bitte verbinden Sie zuerst ein LCR-Gerät.",
            )
            return

        # Erstelle und konfiguriere den Dialog
        dialog = QtWidgets.QDialog(self)
        dialog_ui = Ui_CalibrationDialog()
        dialog_ui.setupUi(dialog)
        dialog.setWindowTitle("LCR Kalibrierung")

        # Setze aktuelle Checkbox-Zustände
        dialog_ui.openCal.setChecked(self._calibration_open_done)
        dialog_ui.shortCal.setChecked(self._calibration_short_done)

        # Zeige Dialog und warte auf Resultat
        result = dialog.exec()

        # Wenn OK gedrückt wurde, speichere die Checkbox-Stati
        if result == QtWidgets.QDialog.DialogCode.Accepted:
            self._calibration_open_done = dialog_ui.openCal.isChecked()
            self._calibration_short_done = dialog_ui.shortCal.isChecked()

            self._show_status(
                f"Kalibrierungsstatus gespeichert \
                    (Open: {self._calibration_open_done}, Short: {self._calibration_short_done})",
                level="success",
                duration_ms=4000,
            )
            print(
                f"[MainWindow] Kalibrierung: \
                    Open={self._calibration_open_done}, Short={self._calibration_short_done}"
            )

    # ========================================================================
    # Type-Auswahl und QToolBox Synchronisation
    # ========================================================================

    def _on_type_changed(self, index: int):
        """
        Wird aufgerufen, wenn die Bauteilkategorie geändert wird.
        Aktiviert die entsprechende Seite in der specific QToolBox.

        Args:
            index: Index der ausgewählten Kategorie im type ComboBox
                   0: Widerstand, 1: Kondensator, 2: Induktivität,
                   3: Transistor, 4: Schalter, 5: Sicherung
        """
        if index >= 0:
            # Die QToolBox-Seiten sind in derselben Reihenfolge wie die Type-Items
            self.ui.specific.setCurrentIndex(index)
            self._update_specific_fields_enabled(index)
            self._log_type_change(index)
        self._update_lcr_measurement_state()

    def _log_type_change(self, index: int):
        """Gibt eine Debug-Meldung für die Typänderung aus."""
        type_names = [
            "Widerstand",
            "Kondensator",
            "Induktivität",
            "Transistor",
            "Schalter",
            "Sicherung",
        ]
        if 0 <= index < len(type_names):
            print(
                f"[MainWindow] Kategorie gewechselt zu: {type_names[index]} (Index {index})"
            )

    def _update_specific_fields_enabled(self, active_index: int):
        """
        Aktiviert nur die Felder der aktuell ausgewählten Seite,
        deaktiviert alle anderen specific properties.

        Args:
            active_index: Index der aktiven Seite (0-5)
        """
        # Liste aller specific-Seiten
        pages = [
            self.ui.resistor,
            self.ui.capacitor,
            self.ui.inductor,
            self.ui.transistor,
            self.ui.switch_2,
            self.ui.fuse,
        ]

        for idx, page in enumerate(pages):
            # Aktiviere nur die Felder der aktiven Seite
            enabled = idx == active_index
            self._set_page_fields_enabled(page, enabled)

    def _set_page_fields_enabled(self, page: QtWidgets.QWidget, enabled: bool):
        """
        Setzt den Enabled-Status aller Input-Felder einer Seite.

        Args:
            page: Das QWidget der Seite (z.B. self.ui.resistor)
            enabled: True um zu aktivieren, False um zu deaktivieren
        """
        # Durchsuche alle Kinder-Widgets der Seite
        for widget in page.findChildren(QtWidgets.QWidget):
            # Aktiviere/Deaktiviere nur Input-Felder
            if isinstance(
                widget,
                (
                    QtWidgets.QLineEdit,
                    QtWidgets.QComboBox,
                    QtWidgets.QSpinBox,
                    QtWidgets.QDoubleSpinBox,
                    QtWidgets.QCheckBox,
                ),
            ):
                widget.setEnabled(enabled)

    # ========================================================================
    # OpenBIS-Controller Methoden
    # ========================================================================

    def _on_st_changed(self):
        """Session-Token wurde eingegeben."""
        session_token = self.ui.session_token.text().strip()
        if not session_token:
            return

        if not re.match(r".*?-\d{10}[\d\w]{38}", session_token):
            self.ui.openbis_progress.setText("Ungültiges Token-Format")
            self.ui.openbis_progress.setStyleSheet("color: red;")
            return

        # Erstelle OpenBIS-Controller
        if not self.openbis_controller or not self.openbis_controller.is_connected():
            self.ui.openbis_progress.setText(
                "Verbindung zu OpenBIS wird hergestellt..."
            )
            self.openbis_controller = OpenBISController(
                server_url=SERVER_URL, debug=True
            )

            # Verbinde Signale
            self._connect_openbis_signals()

            # Verbinde mit Token
            self.openbis_controller.connect_with_token(session_token)

    def _connect_openbis_signals(self):
        """Verbindet OpenBIS-Controller-Signale mit UI-Updates."""
        if not self.openbis_controller:
            return

        self.openbis_controller.connection_established.connect(
            self._on_openbis_connected
        )
        self.openbis_controller.disconnected.connect(self._on_openbis_disconnected)
        self.openbis_controller.object_found.connect(self._on_openbis_object_found)
        self.openbis_controller.object_not_found.connect(
            self._on_openbis_object_not_found
        )
        self.openbis_controller.properties_loaded.connect(
            self._on_openbis_properties_loaded
        )
        self.openbis_controller.error_occurred.connect(self._on_openbis_error)
        self.openbis_controller.status_changed.connect(self._on_openbis_status)
        # Transiente Statusmeldungen für Statusbar
        self.openbis_controller.status_message.connect(self._on_status_message)
        # Object updated Signal
        self.openbis_controller.object_updated.connect(self._on_openbis_object_updated)

    def _on_openbis_connected(self, info: str):
        """OpenBIS erfolgreich verbunden."""
        self.ui.openbis_progress.setText(info)
        self.ui.openbis_progress.setStyleSheet("color: green;")
        self.ui.barcode.setEnabled(True)
        self.ui.barcode.setFocus()
        self.init_sections()

    def _on_openbis_disconnected(self):
        """OpenBIS getrennt."""
        self.ui.openbis_progress.setText("Verbindung getrennt")
        self.ui.openbis_progress.setStyleSheet("")
        self.ui.barcode.setEnabled(False)

    def _on_openbis_object_found(self, obj_data: dict):
        """OpenBIS-Objekt gefunden."""
        print(f"Objekt gefunden: {obj_data['code']}")
        # Speichere Objektdaten für spätere Updates
        self.current_object_data = obj_data
        # Hier können Objektdaten in UI geladen werden
        self.ui.object_status.setCurrentText("Bekannt")
        self._fill_object_data(obj_data)
        # Nur generelle Felder (außer type) aktivieren, type bleibt deaktiviert
        self._set_general_fields_enabled(True, enable_type=False)
        # Aktiviere Upload-Button
        self.ui.openbis_upload.setEnabled(True)

    def _on_openbis_object_not_found(self, code: str):
        """OpenBIS-Objekt nicht gefunden."""
        error_msg = f"Objekt '{code}' nicht gefunden"
        self._show_status(error_msg, level="warning", duration_ms=6000)
        self.ui.object_status.setCurrentText("Neues Objekt")
        # Alle Felder aktivieren (inkl. type)
        self._set_general_fields_enabled(True, enable_type=True)

    def _on_openbis_properties_loaded(self, properties: dict):
        """OpenBIS-Properties geladen."""
        print(f"Properties geladen: {len(properties)} Sections")
        # Hier können Properties in UI geladen werden

    def _on_openbis_error(self, error_msg: str):
        """OpenBIS-Fehler aufgetreten."""
        # Fehler nur transient in der Statusbar anzeigen
        self._show_status(error_msg, level="error", duration_ms=6000)

    def _on_openbis_status(self, status: str):
        """OpenBIS-Status geändert."""
        self.ui.openbis_progress.setText(status)

    def _on_barcode_entered(self):
        """Barcode wurde eingegeben."""
        barcode = self.ui.barcode.text().strip()
        if not barcode:
            return

        if not self.openbis_controller or not self.openbis_controller.is_connected():
            QMessageBox.warning(
                self,
                "Fehler",
                "Nicht mit OpenBIS verbunden. Bitte verbinden Sie sich zuerst.",
            )
            return

        self.openbis_controller.search_object(barcode)
        # Transiente Meldung erfolgt durch Controller

    def _on_openbis_save_clicked(self):
        """Wird aufgerufen, wenn der Save-Button geklickt wird."""
        if not self.openbis_controller or not self.openbis_controller.is_connected():
            QMessageBox.warning(
                self,
                "Fehler",
                "Nicht mit OpenBIS verbunden.",
            )
            return

        if not self.current_object_data:
            QMessageBox.warning(
                self,
                "Fehler",
                "Kein Objekt geladen. Bitte suchen Sie zuerst ein Objekt.",
            )
            return

        # Sammle alle geänderten Properties aus der UI
        properties = self._collect_properties_from_ui()

        # Rufe update_object auf
        obj_code = self.current_object_data.get("code", "")
        obj_permid = self.current_object_data.get("permId", "")

        if not obj_code or not obj_permid:
            QMessageBox.warning(
                self,
                "Fehler",
                "Ungültige Objektdaten.",
            )
            return

        self.openbis_controller.update_object(obj_code, obj_permid, properties)

    def _on_openbis_object_updated(self, obj_code: str):
        """Wird aufgerufen, wenn ein Objekt erfolgreich aktualisiert wurde."""
        QMessageBox.information(
            self,
            "Erfolg",
            f"Objekt '{obj_code}' wurde erfolgreich aktualisiert.",
        )

    def _collect_properties_from_ui(self) -> Dict[str, Any]:
        """
        Sammelt nur geänderte Property-Werte aus der aktuell aktiven Seite
        sowie generelle Felder (manufacturer, orig_name, status).

        Returns:
            Dictionary mit Property-Namen und geänderten Werten
        """
        properties = {}

        # 1. Sammle generelle Felder (außer barcode und type)
        general_field_mappings = {
            "equipment.company": self.ui.manufacturer,
            "equipment.alternativ_name": self.ui.orig_name,
            "equipment.status": self.ui.status,
        }

        for prop_name, field in general_field_mappings.items():
            initial_value = self.initial_field_values.get(prop_name)
            current_value = None
            if isinstance(field, QtWidgets.QLineEdit):
                current_value = field.text()
            elif isinstance(field, QtWidgets.QComboBox):
                # Für ComboBoxen: Hole immer den data-Wert (die Kennung/Code)
                current_value = field.currentText()

            print(f"Current data for {prop_name}: {current_value}")
            # Nur hinzufügen, wenn geändert und nicht leer
            if (
                current_value is not None
                and current_value != ""
                and current_value != initial_value
            ):
                properties[prop_name] = current_value

        # 2. Sammle nur Properties der aktiven Seite
        current_type_index = self.ui.type.currentIndex()
        if current_type_index < 0:
            return properties

        # Mapping von Type-Index zu Section-Widget
        section_widgets = [
            self.ui.resistor,  # 0: Widerstand
            self.ui.capacitor,  # 1: Kondensator
            self.ui.inductor,  # 2: Induktivität
            self.ui.transistor,  # 3: Transistor
            self.ui.switch_2,  # 4: Schalter
            self.ui.fuse,  # 5: Sicherung
        ]

        if current_type_index >= len(section_widgets):
            return properties

        active_section = section_widgets[current_type_index]
        layout = active_section.layout()

        if layout is None or not isinstance(layout, QtWidgets.QFormLayout):
            return properties

        # Durchlaufe alle Rows im FormLayout der aktiven Seite
        for i in range(layout.rowCount()):
            field_item = layout.itemAt(i, QtWidgets.QFormLayout.ItemRole.FieldRole)
            if not field_item or not field_item.widget():
                continue

            field = field_item.widget()
            prop_name = field.objectName()

            if not prop_name:
                continue

            # Hole initialen Wert
            initial_value = self.initial_field_values.get(prop_name)

            # Extrahiere aktuellen Wert basierend auf Widget-Typ
            current_value = None
            if isinstance(field, QtWidgets.QLineEdit):
                current_value = field.text()
                # Leere Strings nicht als Änderung werten
                if current_value == "":
                    current_value = None
            elif isinstance(field, QtWidgets.QComboBox):
                # Für alle ComboBoxen: Verwende die Kennung (data), nicht den Text
                current_value = field.currentData()
                # Fallback auf Text nur wenn keine Kennung gesetzt ist
                if current_value is None:
                    current_value = field.currentText()
            elif isinstance(field, QtWidgets.QDoubleSpinBox):
                current_value = field.value()
                # Prüfe, ob der Wert tatsächlich geändert wurde
                # Wenn initial_value None war und current_value 0.0 ist, ignorieren
                if initial_value is None and current_value == 0.0:
                    current_value = None
            elif isinstance(field, QtWidgets.QSpinBox):
                current_value = field.value()
                # Prüfe, ob der Wert tatsächlich geändert wurde
                # Wenn initial_value None war und current_value 0 ist, ignorieren
                if initial_value is None and current_value == 0:
                    current_value = None

            # Nur hinzufügen, wenn sich der Wert geändert hat
            if current_value is not None and current_value != initial_value:
                properties[prop_name] = current_value

        return properties

    def _set_general_fields_enabled(self, enabled: bool, enable_type: bool = True):
        """
        Aktiviert/Deaktiviert die generellen Felder.

        Args:
            enabled: True um Felder zu aktivieren, False um zu deaktivieren
            enable_type: Wenn True, wird auch das type-Feld aktiviert/deaktiviert
        """
        # Generelle Felder (außer barcode und object_status, die immer ihren Status behalten)
        general_fields = [
            self.ui.manufacturer,
            self.ui.orig_name,
            self.ui.status,
        ]

        for field in general_fields:
            field.setEnabled(enabled)

        # Type-Feld separat behandeln
        if enable_type:
            self.ui.type.setEnabled(enabled)

    # ========================================================================
    # Daten-Management
    # ========================================================================

    def _fill_object_data(self, obj_data: dict):
        """Füllt UI-Felder mit den Daten des gefundenen Objekts und speichert initiale Werte."""
        # Lösche alte initiale Werte
        self.initial_field_values.clear()

        # Grundlegende Felder
        type_text = obj_data.get("qt_type", "Unbekannt")
        self.ui.type.setCurrentText(type_text)
        # Manuell _on_type_changed aufrufen, da setCurrentText kein Signal auslöst
        # wenn der Index gleich bleibt
        type_index = self.ui.type.currentIndex()
        if type_index >= 0:
            self._on_type_changed(type_index)

        manufacturer = obj_data.get("manufacturer", "")
        self.ui.manufacturer.setText(manufacturer)
        self.initial_field_values["equipment.manufacturer"] = manufacturer

        status = obj_data.get("qt_function", "Unbekannt")
        self.ui.status.setCurrentText(status)
        # Speichere den OpenBIS-Code, nicht den angezeigten Text
        status_code = obj_data.get("function", "UNKWN")
        self.initial_field_values["equipment.status"] = status_code

        alternativ_name = obj_data["properties"].get("equipment.alternativ_name", "")
        self.ui.orig_name.setText(alternativ_name)
        self.initial_field_values["equipment.alternativ_name"] = alternativ_name

        # Spezifische Properties
        properties = obj_data.get("properties", {})
        for prop_name, prop_value in properties.items():
            field = self.findChild(QtWidgets.QWidget, prop_name.upper())
            if field is None:
                continue

            # Speichere initialen Wert
            self.initial_field_values[prop_name] = prop_value

            match field.__class__.__name__:
                case "QLineEdit":
                    field.setText(str(prop_value) if prop_value is not None else "")
                case "QComboBox":
                    index = field.findData(prop_value)
                    if index != -1:
                        field.setCurrentIndex(index)
                case "QDoubleSpinBox" | "QSpinBox":
                    if prop_value is not None:
                        field.setValue(float(prop_value))
                case _:
                    print(
                        f"Unbekanntes Feldtyp für {prop_name}: {field.__class__.__name__}"
                    )

    # ========================================================================
    # Statusbar Meldungen (transient)
    # ========================================================================

    def _on_status_message(self, message: str, level: str, duration_ms: int):
        self._show_status(message, level=level, duration_ms=duration_ms)

    def _show_status(self, message: str, level: str = "info", duration_ms: int = 4000):
        """Zeigt eine formatierte, temporäre Meldung in der Statusbar an."""
        bar = self.statusBar()
        # Farben nach Level
        color_map = {
            "info": "",
            "success": "#1a7f37",  # grün
            "warning": "#b26a00",  # orange/braun
            "error": "#d1242f",  # rot
        }
        prev_style = bar.styleSheet()
        color = color_map.get(level, "")
        if color:
            bar.setStyleSheet(f"color: {color};")
        else:
            bar.setStyleSheet("")
        bar.showMessage(message, duration_ms)
        # Nach Ablauf Stil zurücksetzen (einfacher Ansatz)
        QtCore.QTimer.singleShot(
            duration_ms + 100, lambda: bar.setStyleSheet(prev_style)
        )

    # ========================================================================
    # Legacy-Methode (für Rückwärtskompatibilität)
    # ========================================================================

    def openbis_status_callback(self, message: str, color: Optional[str] = None):
        """Legacy callback für OpenBIS-Status (wird nicht mehr benötigt)."""
        self.ui.openbis_progress.setText(message)
        if not color:
            color = self.ui.centralwidget.palette().text().color().name()
        self.ui.openbis_progress.setStyleSheet(f"color: {color};")

    # ========================================================================
    # Cleanup
    # ========================================================================

    def closeEvent(self, event):
        """Beim Schließen des Fensters Controller trennen."""
        if self.lcr_controller and self.lcr_controller.is_connected():
            self.lcr_controller.disconnect_device()

        if self.openbis_controller and self.openbis_controller.is_connected():
            self.openbis_controller.disconnect_openbis()

        event.accept()

    # ========================================================================
    # Legacy-Methode (für bestehenden Code)
    # ========================================================================

    def init_sections(self):
        sections = {
            "capacitor": "Kondensator",
            "fuse": "Gerätesicherung",
            "inductor": "Spule / Induktivitäten",
            "resistor": "Widerstand",
            "switch_2": "Schalter",
            "transistor": "Transistor",
        }

        if self.openbis_controller and self.openbis_controller.is_connected():
            o_props = self.openbis_controller.init_properties()
        else:
            raise RuntimeError("OpenBIS-Controller ist nicht verbunden.")

        # Verwende Minimum SizePolicy für Labels, damit sie sich an Inhalt anpassen
        label_sp = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        label_sp.setHorizontalStretch(0)
        label_sp.setVerticalStretch(0)

        # Match existing field style: MinimumExpanding horizontal, Fixed vertical
        field_sp = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        field_sp.setHorizontalStretch(0)
        field_sp.setVerticalStretch(0)

        # Variablen für automatische Breitenberechnung
        max_label_width = 0
        font_metrics = QtWidgets.QLabel().fontMetrics()

        for key, value in sections.items():
            section = getattr(self.ui, key, None)
            if not section or not hasattr(section, "layout"):
                continue

            layout = section.layout()
            if layout is None:
                continue

            # Clear existing children of the layout if any
            if layout.count() > 0:

                def _clear_layout(l: QtWidgets.QLayout):
                    while l.count():
                        item = l.takeAt(0)
                        if item is None:
                            continue
                        w = item.widget()
                        if w is not None:
                            w.setParent(None)
                            w.deleteLater()
                            continue
                        sub = item.layout()
                        if sub is not None:
                            _clear_layout(sub)
                        # spacer items are ignored

                _clear_layout(layout)

            properties = o_props.get(value, {})
            if not properties:
                continue

            for prop_key, prop_value in properties.items():
                label_text = prop_value["label"]
                label = QtWidgets.QLabel(label_text)
                label.setSizePolicy(label_sp)
                label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

                # Berechne die benötigte Breite für dieses Label
                label_width = (
                    font_metrics.horizontalAdvance(label_text) + 20
                )  # +20 für Padding
                max_label_width = max(max_label_width, label_width)

                match prop_value["data_type"]:
                    case "VARCHAR":
                        field = QtWidgets.QLineEdit()
                        field.setSizePolicy(field_sp)
                        field.setObjectName(prop_key)
                    case "BOOLEAN":
                        field = QtWidgets.QComboBox()
                        field.setSizePolicy(field_sp)
                        field.setObjectName(prop_key)
                    case "REAL":
                        field = QtWidgets.QDoubleSpinBox()
                        field.setSizePolicy(field_sp)
                        field.setObjectName(prop_key)
                        field.setMaximum(1e15)  # Setze ein hohes Maximum
                        field.setMinimum(-1e15)  # Setze ein hohes Maximum
                        field.setDecimals(6)
                    case "INTEGER":
                        field = QtWidgets.QSpinBox()
                        field.setSizePolicy(field_sp)
                        field.setObjectName(prop_key)
                        field.setMaximum(1000000000)  # Setze ein hohes Maximum
                    case "CONTROLLEDVOCABULARY":
                        field = QtWidgets.QComboBox()
                        field.setSizePolicy(field_sp)
                        field.setObjectName(prop_key)
                        vocab_terms = prop_value["vocab_terms"]
                        for term in vocab_terms:
                            field.addItem(term["label"], term["code"])
                    case _:
                        field = QtWidgets.QLineEdit()
                        field.setSizePolicy(field_sp)
                        field.setObjectName(prop_key)
                field.setFixedWidth(200)
                layout.addRow(label, field)
            print(f"Section '{value}' mit {len(properties)} Properties initialisiert.")

        # Setze die minimale Breite für alle Labels basierend auf dem breitesten Label
        min_label_width = max(150, max_label_width)  # Mindestens 150px
        max_section_height = 0

        for key, value in sections.items():
            section = getattr(self.ui, key, None)
            if not section or not hasattr(section, "layout"):
                continue
            layout = section.layout()
            if layout is None or not isinstance(layout, QtWidgets.QFormLayout):
                continue

            # Setze die minimale Breite für alle Labels in diesem Layout
            for i in range(layout.rowCount()):
                label_item = layout.itemAt(i, QtWidgets.QFormLayout.ItemRole.LabelRole)
                if label_item and label_item.widget():
                    label_item.widget().setMinimumWidth(min_label_width)

        # Passe die QToolBox-Breite an (Label + Field + Margins)
        field_width = 200
        margins = 40  # Geschätzte Margins und Spacing
        toolbox_width = min_label_width + field_width + margins
        self.ui.specific.setMinimumWidth(toolbox_width)

        print(
            f"Alle Sections initialisiert. Max Label-Breite: {min_label_width}px, ToolBox-Breite: {toolbox_width}px"
        )


def main():
    """Entry point for the application."""
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
