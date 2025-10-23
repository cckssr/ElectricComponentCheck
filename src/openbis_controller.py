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

    # Qt Signals
    connection_established = Signal(str)  # Session info
    disconnected = Signal()
    object_found = Signal(dict)  # Object data
    object_not_found = Signal(str)  # Object code
    properties_loaded = Signal(dict)  # Properties dictionary
    error_occurred = Signal(str)  # Error message
    status_changed = Signal(str)  # Status message

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
            self.status_changed.emit(f"Verbinde mit OpenBIS...")

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
            self.status_changed.emit(info_str)

            return True

        except Exception as e:
            error_msg = f"Verbindungsfehler: {str(e)}"
            self._log(error_msg)

            # Legacy callback
            if self.status_callback:
                self.status_callback("Verbindung fehlgeschlagen", "red")

            # Qt Signal
            self.error_occurred.emit(error_msg)
            self.status_changed.emit("Verbindung fehlgeschlagen")

            return False

    def disconnect_openbis(self) -> None:
        """Trennt die Verbindung zu OpenBIS."""
        if self._connected:
            try:
                self.openbis.logout()
            except Exception as e:
                self._log(f"Fehler beim Trennen: {e}")
            finally:
                self._connected = False
                self._log("Verbindung getrennt")
                self.disconnected.emit()
                self.status_changed.emit("Verbindung getrennt")

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
            self.status_changed.emit(f"Suche Objekt {code}...")

            results = self.openbis.get_objects(code=code)

            if len(results) == 0:
                msg = f"Kein Objekt mit Code {code} gefunden"
                self._log(msg)
                self.object_not_found.emit(code)
                self.status_changed.emit(msg)
                return None

            elif len(results) > 1:
                msg = f"Mehrere Objekte mit Code {code} gefunden. Bitte spezifizieren."
                self._log(msg)
                self.error_occurred.emit(msg)
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
                    "type": obj.type.code,
                    "permId": obj.permId,
                    "identifier": (
                        obj.identifier if hasattr(obj, "identifier") else None
                    ),
                    "properties": obj.props.all() if hasattr(obj, "props") else {},
                }

                self._log(f"Objekt gefunden: {code}")
                self.object_found.emit(obj_data)
                self.status_changed.emit(f"Objekt {code} gefunden")

                return obj

        except Exception as e:
            error_msg = f"Fehler bei der Objektsuche: {str(e)}"
            self._log(error_msg)
            self.error_occurred.emit(error_msg)
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
            self.status_changed.emit(f"Lade Properties für {object_type}...")

            obj_type = self.openbis.get_object_type(object_type)
            prop_assign = obj_type.get_property_assignments().df
            sections = prop_assign["section"].unique()

            properties = {section: [] for section in sections}
            for _, row in prop_assign.iterrows():
                properties[row["section"]].append(row["propertyType"])

            self._log(f"Properties geladen: {len(properties)} Sections")
            self.properties_loaded.emit(properties)
            self.status_changed.emit(f"Properties für {object_type} geladen")

            return properties

        except Exception as e:
            error_msg = f"Fehler beim Initialisieren der Eigenschaften: {str(e)}"
            self._log(error_msg)
            self.error_occurred.emit(error_msg)
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

    # Legacy-Property für Rückwärtskompatibilität
    @property
    def connected(self) -> bool:
        """Legacy property für self.connected."""
        return self._connected
