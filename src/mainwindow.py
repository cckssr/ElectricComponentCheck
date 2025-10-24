# This Python file uses the following encoding: utf-8
import sys
import re
from typing import Optional
from pathlib import Path
from pyvisa import ResourceManager

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6 import QtWidgets, QtCore

from ui.ui_form import Ui_MainWindow
from openbis_controller import OpenBISController
from lcr_controller import LCRController

SERVER_URL = "https://openbis.physik.tu-berlin.de"


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.openbis_controller: Optional[OpenBISController] = None
        self.lcr_controller: Optional[LCRController] = None
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._init_connections()

    def _init_connections(self):
        """Initialisiert UI-Verbindungen und Controller."""
        # OpenBIS-Verbindungen
        self.ui.session_token.returnPressed.connect(self._on_st_changed)
        self.ui.openbis_progress.setText("Warten auf Session Token...")
        self.ui.barcode.returnPressed.connect(self._on_barcode_entered)

        # LCR-Verbindungen
        self.ui.lcr_refresh_resource.clicked.connect(self._refresh_instruments)
        self.ui.lcr_resource.currentIndexChanged.connect(self._on_resource_changed)

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
        self.lcr_controller.measurement_ready.connect(self._on_lcr_measurement)
        self.lcr_controller.error_occurred.connect(self._on_lcr_error)
        self.lcr_controller.status_changed.connect(self._on_lcr_status)
        # Transiente Statusmeldungen für Statusbar
        self.lcr_controller.status_message.connect(self._on_status_message)

    def _on_lcr_connected(self, device_id: str):
        """LCR-Gerät erfolgreich verbunden."""
        self.ui.lcr_progress.setText(f"Verbunden: {device_id}")
        self.ui.lcr_progress.setStyleSheet("color: green;")

    def _on_lcr_disconnected(self):
        """LCR-Gerät getrennt."""
        self.ui.lcr_progress.setText("Verbindung getrennt")
        self.ui.lcr_progress.setStyleSheet("")

    def _on_lcr_connection_lost(self):
        """LCR-Verbindung verloren."""
        self.ui.lcr_progress.setText("Verbindung verloren!")
        self.ui.lcr_progress.setStyleSheet("color: red;")
        QMessageBox.warning(
            self, "Verbindungsfehler", "Verbindung zum LCR-Gerät verloren!"
        )

    def _on_lcr_measurement(self, data: dict):
        """Neue LCR-Messdaten empfangen."""
        # Hier können Messdaten verarbeitet werden
        print(f"Messung: {data['primary_name']}={data['primary_value']}")

    def _on_lcr_error(self, error_msg: str):
        """LCR-Fehler aufgetreten."""
        # Fehler nur transient in der Statusbar anzeigen
        self._show_status(error_msg, level="error", duration_ms=6000)

    def _on_lcr_status(self, status: str):
        """LCR-Status geändert."""
        self.ui.lcr_progress.setText(status)

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
        # Hier können Objektdaten in UI geladen werden
        self.ui.object_status.setCurrentText("Bekannt")
        self._fill_object_data(obj_data)
        # Nur generelle Felder (außer type) aktivieren, type bleibt deaktiviert
        self._set_general_fields_enabled(True, enable_type=False)

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
        """Füllt UI-Felder mit den Daten des gefundenen Objekts."""
        # Grundlegende Felder
        self.ui.type.setCurrentText(obj_data.get("qt_type", "Unbekannt"))
        self.ui.manufacturer.setText(obj_data.get("manufacturer", ""))
        self.ui.status.setCurrentText(obj_data.get("qt_function", "Unbekannt"))
        self.ui.orig_name.setText(
            obj_data["properties"].get("equipment.alternativ_name", "")
        )

        # Spezifische Properties
        properties = obj_data.get("properties", {})
        for prop_name, prop_value in properties.items():
            field = self.findChild(QtWidgets.QWidget, prop_name.upper())
            if field is None:
                continue
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

    def _show_status(self, message: str, level: str = "info", duration_ms: int = 3000):
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
                    case "INTEGER":
                        field = QtWidgets.QSpinBox()
                        field.setSizePolicy(field_sp)
                        field.setObjectName(prop_key)
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
    sys.exit(app.exec())
