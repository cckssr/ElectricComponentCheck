#!/usr/bin/env python3
"""
OpenBIS Controller mit Qt-Signal-Integration.

Features:
- Qt-Signale für alle wichtigen Events
- Verbindungsmanagement mit Status-Feedback
- Objektsuche und -verwaltung
- Property-Management
- Fehlerbehandlung mit Signalen
"""

from typing import Optional, Dict, Any, List
from PySide6.QtCore import QObject, Signal
from pybis import Openbis


class OpenBISController(QObject):
    """
    Qt-basierter Controller für OpenBIS-Server.

    Signale:
        connection_established: Wird ausgesendet, wenn die Verbindung erfolgreich hergestellt wurde
        disconnected: Wird ausgesendet, wenn die Verbindung getrennt wurde
        object_found: Wird ausgesendet, wenn ein Objekt gefunden wurde (dict)
        object_not_found: Wird ausgesendet, wenn kein Objekt gefunden wurde (str: code)
        properties_loaded: Wird ausgesendet, wenn Properties geladen wurden (dict)
        error_occurred: Wird bei Fehlern ausgesendet (str)
        status_changed: Wird bei Statusänderungen ausgesendet (str)
    """

    # Constants
    QT_TRANSLATE_ELEC_TYPE = {  # Openbis type code: qt label
        "CAPACITOR": "Kondensator",
        "DIODE": "Diode",
        "FUSE": "Sicherung",
        "INDUCTOR": "Induktivität",
        "OPAMP": "Operationsverstärker",
        "RESISTOR": "Widerstand",
        "SWITCH": "Schalter",
        "TRANSISTOR": "Transistor",
    }
    QT_TRANSLATE_ELEC_STATUS = {
        "DEF": "Defekt",
        "FUNC": "Funktioniert",
        "NOCALB": "Unkalibriert",
        "OK": "Kalibriert",
        "UNKWN": "Unbekannt",
    }

    # Qt Signals
    connection_established = Signal(str)  # Session info (connection status only)
    disconnected = Signal()
    object_found = Signal(dict)  # Object data
    object_not_found = Signal(str)  # Object code
    properties_loaded = Signal(dict)  # Properties dictionary
    error_occurred = Signal(str)  # Error message
    # Transiente Statusmeldungen (nur für Statusbar):
    #   message, level(info|success|warning|error), duration(ms)
    status_message = Signal(str, str, int)
    # Verbindungsspezifischer Status (nur für UI-Label):
    #   z.B. "Verbunden als ...", "Verbindung getrennt"
    status_changed = Signal(str)

    def __init__(
        self,
        server_url: str,
        session_token: Optional[str] = None,
        status_callback=None,
        debug: bool = False,
    ):
        """
        Initialisiert den OpenBIS-Controller.

        Args:
            server_url: URL des OpenBIS-Servers
            session_token: Optional - Session-Token für sofortige Verbindung
            status_callback: Legacy callback (für Rückwärtskompatibilität)
            debug: Debug-Modus aktivieren
        """
        super().__init__()

        self.server_url = server_url
        self.openbis = Openbis(server_url)
        self.status_callback = status_callback  # Legacy support
        self.debug = debug
        self._connected = False

        # Wenn Token übergeben wurde, sofort verbinden
        if session_token:
            self.connect_with_token(session_token)

    def _log(self, message: str) -> None:
        """Debug-Ausgabe."""
        if self.debug:
            print(f"[OpenBIS] {message}")

    def connect_with_token(self, session_token: str) -> bool:
        """
        Verbindet mit OpenBIS unter Verwendung eines Session-Tokens.

        Args:
            session_token: Gültiger OpenBIS Session-Token

        Returns:
            True bei erfolgreicher Verbindung, False sonst
        """
        try:
            self._log(f"Verbinde mit {self.server_url}...")
            self.status_message.emit("Verbinde mit OpenBIS...", "info", 2000)

            self.openbis.set_token(session_token)
            session_info = self.openbis.get_session_info()

            self._connected = True

            # Legacy callback
            if self.status_callback:
                self.status_callback("Erfolgreich verbunden", "green")

            # Qt Signal
            info_str = f"Verbunden als {session_info.data.get('userName', 'Unbekannt')}"
            self._log(info_str)
            self.connection_established.emit(info_str)
            # Verbindungsetikett aktualisieren
            self.status_changed.emit(info_str)
            # Zusätzlich transiente Erfolgsmeldung
            self.status_message.emit("OpenBIS-Verbindung hergestellt", "success", 3000)

            return True

        except Exception as e:
            error_msg = f"Verbindungsfehler: {str(e)}"
            self._log(error_msg)

            # Legacy callback
            if self.status_callback:
                self.status_callback("Verbindung fehlgeschlagen", "red")

            # Qt Signal
            self.error_occurred.emit(error_msg)
            # Transiente Fehlermeldung in Statusbar
            self.status_message.emit(error_msg, "error", 6000)
            # Verbindungsetikett auf nicht-verbunden setzen
            self.status_changed.emit("Nicht verbunden")

            return False

    def disconnect_openbis(self) -> None:
        """Trennt die Verbindung zu OpenBIS."""
        if self._connected:
            # try:
            #     self.openbis.logout()
            # except Exception as e:
            #     self._log(f"Fehler beim Trennen: {e}")
            # finally:
            self._connected = False
            self._log("Verbindung getrennt")
            self.disconnected.emit()
            # Verbindungsetikett
            self.status_changed.emit("Verbindung getrennt")
            # Transiente Info
            self.status_message.emit("OpenBIS-Verbindung getrennt", "info", 2000)

    def is_connected(self) -> bool:
        """Prüft, ob mit OpenBIS verbunden."""
        return self._connected

    def search_object(
        self, code: str, object_type: str = "ELEKTRONISCHES_BAUTEIL"
    ) -> Optional[Any]:
        """
        Sucht ein Objekt in OpenBIS nach Code.

        Args:
            code: Object-Code zum Suchen
            object_type: Erwarteter Objekttyp

        Returns:
            Objekt wenn gefunden, None sonst
        """
        if not self._connected:
            self.error_occurred.emit("Nicht mit OpenBIS verbunden")
            return None

        try:
            self._log(f"Suche Objekt: {code}")
            self.status_message.emit(f"Suche Objekt {code}...", "info", 2000)

            results = self.openbis.get_objects(code=code)

            if len(results) == 0:
                msg = f"Kein Objekt mit Code {code} gefunden"
                self._log(msg)
                self.object_not_found.emit(code)
                self.status_message.emit(msg, "warning", 4000)
                return None

            elif len(results) > 1:
                msg = f"Mehrere Objekte mit Code {code} gefunden. Bitte spezifizieren."
                self._log(msg)
                self.error_occurred.emit(msg)
                self.status_message.emit(msg, "warning", 4000)
                return None

            else:
                obj = results[0]
                if obj.type.code != object_type:
                    msg = f"Objekt gefunden, aber es ist kein {object_type}"
                    self._log(msg)
                    self.error_occurred.emit(msg)
                    return None

                # Objekt gefunden - als Dictionary für Signal
                obj_data = {
                    "code": obj.code,
                    "type": "",
                    "qt_type": "Unbekannt",
                    "function": "UNKWN",
                    "qt_function": "Unbekannt",
                    "permId": obj.permId,
                    "properties": (
                        obj.props.all_nonempty() if hasattr(obj, "props") else {}
                    ),
                }
                if obj_data["properties"]:
                    obj_data["type"] = obj_data["properties"].get(
                        "equipment.electrical_type", "UNKWN"
                    )
                    obj_data["qt_type"] = self.QT_TRANSLATE_ELEC_TYPE.get(
                        obj_data["type"], "Unbekannt"
                    )
                    obj_data["function"] = obj_data["properties"].get(
                        "equipment.status", "UNKWN"
                    )
                    obj_data["qt_function"] = self.QT_TRANSLATE_ELEC_STATUS.get(
                        obj_data["function"], "Unbekannt"
                    )

                self._log(f"Objekt gefunden: {code}")
                self.object_found.emit(obj_data)
                self.status_message.emit(f"Objekt {code} gefunden", "success", 2500)

                return obj

        except Exception as e:
            error_msg = f"Fehler bei der Objektsuche: {str(e)}"
            self._log(error_msg)
            self.error_occurred.emit(error_msg)
            self.status_message.emit(error_msg, "error", 6000)
            return None

    def init_properties(
        self, object_type: str = "ELEKTRONISCHES_BAUTEIL"
    ) -> Dict[str, List[str]]:
        """
        Initialisiert und lädt die Properties eines Objekttyps.

        Args:
            object_type: OpenBIS Objekttyp

        Returns:
            Dictionary mit Properties nach Section gruppiert
        """
        if not self._connected:
            self.error_occurred.emit("Nicht mit OpenBIS verbunden")
            return {}

        try:
            self._log(f"Lade Properties für {object_type}...")
            self.status_message.emit(
                f"Lade Properties für {object_type}...", "info", 2000
            )

            obj_type = self.openbis.get_object_type(object_type)
            prop_assign = obj_type.get_property_assignments().df
            sections = prop_assign["section"].unique()

            properties = {section: [] for section in sections}
            for _, row in prop_assign.iterrows():
                properties[row["section"]].append(row["code"])

            properties = self._detail_object_properties(properties)

            self._log(f"Properties geladen: {len(properties)} Sections")
            self.properties_loaded.emit(properties)
            self.status_message.emit(
                f"Properties für {object_type} geladen", "success", 2500
            )

            return properties

        except Exception as e:
            error_msg = f"Fehler beim Initialisieren der Eigenschaften: {str(e)}"
            self._log(error_msg)
            self.error_occurred.emit(error_msg)
            self.status_message.emit(error_msg, "error", 6000)
            return {}

    def get_server_info(self) -> Optional[Dict[str, str]]:
        """
        Gibt Server-Informationen zurück.

        Returns:
            Dictionary mit Server-Informationen oder None
        """
        if not self._connected:
            return None

        return {
            "server_url": self.server_url,
            "connected": str(self._connected),
        }

    def _detail_object_properties(
        self, props: Dict[str, List[str]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Hilfsmethode zum Detaillieren der Properties eines Objekts."""
        detailed_props = props.copy()
        for key in props:
            key_list = props[key]
            detailed_props[key] = dict.fromkeys(key_list)
            for i, o_type in enumerate(key_list):
                temp_o_type = self.openbis.get_property_type(o_type)
                temp_dict = {
                    "label": temp_o_type.label,
                    "description": temp_o_type.description,
                    "data_type": temp_o_type.dataType,
                    "vocabulary": temp_o_type.vocabulary,
                }
                if temp_dict["data_type"] == "CONTROLLEDVOCABULARY":
                    vocab = (
                        self.openbis.get_vocabulary(temp_dict["vocabulary"])
                        .get_terms()
                        .df
                    )
                    terms = vocab[["code", "label"]].to_dict("records")
                    temp_dict["vocab_terms"] = terms
                detailed_props[key][o_type] = temp_dict
        return detailed_props
