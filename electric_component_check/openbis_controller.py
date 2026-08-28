#!/usr/bin/env python3
"""
OpenBIS Controller mit Qt-Signal-Integration.

Features:
- Qt-Signale für alle wichtigen Events
- Verbindungsmanagement mit Status-Feedback
- Objektsuche, -erstellung und -aktualisierung
- Property-Management inkl. Vokabular-Normalisierung
- Anhängen des Mess-PDF als CALI_CERT-Dataset
- Fehlerbehandlung mit Signalen
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pybis import Openbis
from PySide6.QtCore import QObject, Signal, Slot

from .config import AppConfig


@dataclass(frozen=True, slots=True)
class ComponentSaveRequest:
    """Everything needed to create-or-update one component and attach its report."""

    barcode: str
    properties: dict[str, Any]
    object_permid: str | None = None  # None => create a new object
    report_path: Path | None = None
    instrument_id: str | None = None


class OpenBISController(QObject):
    """
    Qt-basierter Controller für OpenBIS-Server.

    Signale:
        connection_established: Verbindung erfolgreich hergestellt (str)
        disconnected: Verbindung getrennt
        object_found: Objekt gefunden (dict)
        object_not_found: Kein Objekt gefunden (str: code)
        properties_loaded: Properties geladen (dict)
        object_created: Neues Objekt erstellt (str: code)
        object_updated: Objekt aktualisiert (str: code)
        object_saved: Terminal-Signal für save_component (permId, mode)
        dataset_attached: Dataset an Objekt angehängt (obj_code, dataset_permId)
        save_failed: save_component ist fehlgeschlagen (str: Fehlermeldung)
        error_occurred: Fehler aufgetreten (str)
        status_changed: Verbindungsstatus geändert (str)
    """

    # Fallback labels, used only until init_properties() has fetched the real
    # server vocabulary (see _vocab_label). May drift from the server.
    QT_TRANSLATE_ELEC_TYPE = {
        "CAPACITOR": "Kondensator",
        "DIODE": "Diode",
        "FUSE": "Sicherung",
        "INDUCTOR": "Spule",
        "OPAMP": "Operationsverstärker",
        "RESISTOR": "Widerstand",
        "SWITCH": "Schalter",
        "TRANSISTOR": "Transistor",
    }
    QT_TRANSLATE_ELEC_STATUS = {
        "ARCHIVE": "Archiviert",
        "DEF": "Defekt",
        "FUNC": "Funktioniert",
        "NOCALB": "Unkalibriert",
        "OK": "Kalibriert",
        "UNKWN": "Unbekannt",
    }

    # Qt Signals
    connection_established = Signal(str)
    disconnected = Signal()
    object_found = Signal(dict)
    object_not_found = Signal(str)
    properties_loaded = Signal(dict)
    object_created = Signal(str)
    object_updated = Signal(str)
    object_saved = Signal(str, str)  # permId, mode ("created" | "updated")
    dataset_attached = Signal(str, str)  # object code, dataset permId
    save_failed = Signal(str)
    error_occurred = Signal(str)
    # Transiente Statusmeldungen (nur für Statusbar): message, level, duration(ms)
    status_message = Signal(str, str, int)
    # Verbindungsspezifischer Status (nur für UI-Label)
    status_changed = Signal(str)

    def __init__(
        self,
        config: AppConfig,
        session_token: str | None = None,
        debug: bool = False,
    ):
        """
        Initialisiert den OpenBIS-Controller.

        Args:
            config: Anwendungskonfiguration (Server-URL, Ziel-Collection, Property-Mapping)
            session_token: Optional - Session-Token für sofortige Verbindung
            debug: Debug-Modus aktivieren
        """
        super().__init__()

        self.config = config
        self.server_url = config.server_url
        self.openbis = Openbis(config.server_url)
        self.debug = debug
        self._connected = False

        # Populated by init_properties(); empty until then.
        self.known_property_codes: set[str] = set()
        self.mandatory_property_codes: set[str] = set()
        self._vocab_by_code: dict[str, dict[str, str]] = {}

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

            info_str = f"Verbunden als {session_info.data.get('userName', 'Unbekannt')}"
            self._log(info_str)
            self.connection_established.emit(info_str)
            self.status_changed.emit(info_str)
            self.status_message.emit("OpenBIS-Verbindung hergestellt", "success", 3000)

            return True

        except Exception as e:
            error_msg = f"Verbindungsfehler: {str(e)}"
            self._log(error_msg)
            self.error_occurred.emit(error_msg)
            self.status_message.emit(error_msg, "error", 6000)
            self.status_changed.emit("Nicht verbunden")

            return False

    def disconnect_openbis(self) -> None:
        """Trennt die Verbindung zu OpenBIS."""
        if self._connected:
            self._connected = False
            self._log("Verbindung getrennt")
            self.disconnected.emit()
            self.status_changed.emit("Verbindung getrennt")
            self.status_message.emit("OpenBIS-Verbindung getrennt", "info", 2000)

    def is_connected(self) -> bool:
        """Prüft, ob mit OpenBIS verbunden."""
        return self._connected

    def _vocab_label(self, prop_code: str, term_code: str, fallback: dict[str, str]) -> str:
        """Translates a vocabulary term code to its label, preferring live server data."""
        vocab = self._vocab_by_code.get(prop_code.lower())
        if vocab and term_code in vocab:
            return vocab[term_code]
        return fallback.get(term_code, term_code or "Unbekannt")

    def search_object(self, code: str, object_type: str | None = None) -> Any | None:
        """
        Sucht ein Objekt in OpenBIS nach Code.

        Args:
            code: Object-Code zum Suchen
            object_type: Erwarteter Objekttyp (Standard: config.object_type)

        Returns:
            Objekt wenn gefunden, None sonst
        """
        object_type = object_type or self.config.object_type
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

                gp = self.config.general_properties
                properties = obj.props.all_nonempty() if hasattr(obj, "props") else {}
                obj_data: dict[str, Any] = {
                    "code": obj.code,
                    "type": "",
                    "qt_type": "Unbekannt",
                    "function": "UNKWN",
                    "qt_function": "Unbekannt",
                    "manufacturer": "",
                    "permId": obj.permId,
                    "properties": properties,
                }
                if properties:
                    obj_data["type"] = properties.get(gp["electrical_type"], "UNKWN")
                    obj_data["qt_type"] = self._vocab_label(
                        gp["electrical_type"], obj_data["type"], self.QT_TRANSLATE_ELEC_TYPE
                    )
                    obj_data["function"] = properties.get(gp["status"], "UNKWN")
                    obj_data["qt_function"] = self._vocab_label(
                        gp["status"], obj_data["function"], self.QT_TRANSLATE_ELEC_STATUS
                    )
                    obj_data["manufacturer"] = properties.get(gp["manufacturer"], "")

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

    def init_properties(self, object_type: str | None = None) -> dict[str, dict[str, Any]]:
        """
        Initialisiert und lädt die Properties eines Objekttyps.

        Baut außerdem known_property_codes, mandatory_property_codes und den
        internen Vokabular-Index auf, die von save_component()/_normalise_vocabulary()
        und der UI (Pflichtfelder) verwendet werden.

        Args:
            object_type: OpenBIS Objekttyp (Standard: config.object_type)

        Returns:
            Dictionary mit Properties nach Section gruppiert
        """
        object_type = object_type or self.config.object_type
        if not self._connected:
            self.error_occurred.emit("Nicht mit OpenBIS verbunden")
            return {}

        try:
            self._log(f"Lade Properties für {object_type}...")
            self.status_message.emit(f"Lade Properties für {object_type}...", "info", 2000)

            obj_type = self.openbis.get_object_type(object_type)
            prop_assign = obj_type.get_property_assignments().df

            sections: dict[str, list[str]] = {}
            mandatory_by_code: dict[str, bool] = {}
            data_type_by_code: dict[str, str] = {}
            for _, row in prop_assign.iterrows():
                code = str(row["code"])
                sections.setdefault(row["section"], []).append(code)
                mandatory_by_code[code.lower()] = bool(row["mandatory"])
                data_type_by_code[code.lower()] = row["dataType"]

            properties = self._detail_object_properties(
                sections, data_type_by_code, mandatory_by_code
            )

            self.known_property_codes = set(data_type_by_code)
            self.mandatory_property_codes = {
                code for code, mandatory in mandatory_by_code.items() if mandatory
            }

            self._log(
                f"Properties geladen: {len(properties)} Sections, "
                f"{len(self.mandatory_property_codes)} Pflichtfelder"
            )
            self.properties_loaded.emit(properties)
            self.status_message.emit(f"Properties für {object_type} geladen", "success", 2500)

            return properties

        except Exception as e:
            error_msg = f"Fehler beim Initialisieren der Eigenschaften: {str(e)}"
            self._log(error_msg)
            self.error_occurred.emit(error_msg)
            self.status_message.emit(error_msg, "error", 6000)
            return {}

    def get_server_info(self) -> dict[str, str] | None:
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
        self,
        sections: dict[str, list[str]],
        data_type_by_code: dict[str, str],
        mandatory_by_code: dict[str, bool],
    ) -> dict[str, dict[str, Any]]:
        """Reichert die Property-Codes je Section mit Label/Typ/Vokabular an.

        dataType und mandatory kommen bereits aus get_property_assignments()'
        DataFrame (kein Extra-Request); label/description/vocabulary sind dort
        nicht enthalten und erfordern weiterhin einen get_property_type() pro
        Property. Ein einzelner fehlerhafter Code bricht nicht den ganzen
        Aufbau ab.
        """
        detailed: dict[str, dict[str, Any]] = {}
        for section, codes in sections.items():
            detailed[section] = {}
            for code in codes:
                code_lower = code.lower()
                data_type = data_type_by_code.get(code_lower, "VARCHAR")
                entry: dict[str, Any] = {
                    "label": code,
                    "description": "",
                    "data_type": data_type,
                    "vocabulary": None,
                    "mandatory": mandatory_by_code.get(code_lower, False),
                }
                try:
                    prop_type = self.openbis.get_property_type(code)
                    entry["label"] = prop_type.label
                    entry["description"] = prop_type.description
                    entry["vocabulary"] = prop_type.vocabulary
                    if data_type == "CONTROLLEDVOCABULARY" and prop_type.vocabulary:
                        terms = (
                            self.openbis.get_vocabulary(prop_type.vocabulary)
                            .get_terms()
                            .df[["code", "label"]]
                            .to_dict("records")
                        )
                        entry["vocab_terms"] = terms
                        self._vocab_by_code[code_lower] = {t["code"]: t["label"] for t in terms}
                except Exception as e:
                    self._log(f"Warnung: Details für Property {code} nicht ladbar: {e}")
                detailed[section][code] = entry
        return detailed

    def _normalise_vocabulary(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Übersetzt ein menschenlesbares Vokabular-Label auf seinen Term-Code.

        Generalisiert über jede CONTROLLEDVOCABULARY-Property, deren Terme
        init_properties() bereits geladen hat (Status, Bauteiltyp, Widerstand-Typ, ...).
        Werte, die bereits ein gültiger Code sind, bleiben unverändert.
        """
        normalised = dict(properties)
        for prop_code, value in properties.items():
            if not isinstance(value, str):
                continue
            vocab = self._vocab_by_code.get(prop_code.lower())
            if not vocab or value in vocab:
                continue
            inv = {label.lower(): code for code, label in vocab.items()}
            mapped = inv.get(value.lower())
            if mapped:
                normalised[prop_code] = mapped
        return normalised

    def _filter_properties(self, properties: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """Drops properties the server doesn't know about instead of failing the save.

        Returns (known_properties, skipped_codes). If known_property_codes hasn't
        been populated yet (init_properties() not called), nothing is filtered.
        """
        if not self.known_property_codes:
            return dict(properties), []
        known = {k: v for k, v in properties.items() if k.lower() in self.known_property_codes}
        skipped = [k for k in properties if k.lower() not in self.known_property_codes]
        return known, skipped

    def _update_object(self, obj_permid: str, properties: dict[str, Any]) -> Any:
        """Aktualisiert ein bestehendes Objekt und speichert es tatsächlich."""
        obj = self.openbis.get_object(obj_permid)
        old_props = obj.props.all_nonempty() if hasattr(obj, "props") else {}

        changed: list[str] = []
        for prop, value in properties.items():
            prop = prop.lower()
            if old_props.get(prop) != value:
                self._log(f" - Aktualisiere {prop}: {old_props.get(prop)} -> {value}")
                obj.props[prop] = value
                changed.append(prop)
            else:
                self._log(f" - Keine Änderung für {prop}")

        if changed:
            obj.save()
        return obj

    def _create_object(self, barcode: str, properties: dict[str, Any]) -> Any:
        """Erstellt ein neues Objekt in der konfigurierten Ziel-Collection."""
        target = self.config.target
        if not target.collection:
            raise ValueError(
                "openbis.target.collection ist nicht konfiguriert -- kann kein neues "
                "Objekt anlegen. Siehe DEVELOPMENT.md."
            )

        kwargs: dict[str, Any] = {"code": barcode, "experiment": target.collection}
        if target.space:
            kwargs["space"] = target.space
        if target.project:
            kwargs["project"] = target.project

        obj = self.openbis.new_object(type=self.config.object_type, props=properties, **kwargs)
        obj.save()
        return obj

    def _attach_report(
        self, obj: Any, pdf_path: Path, *, instrument_id: str | None, measured_at: str
    ) -> str:
        """Hängt das Mess-PDF als CALI_CERT-Dataset an das Objekt an."""
        ds_cfg = self.config.dataset
        props = {
            ds_cfg.lab_property: ds_cfg.lab_name,
            ds_cfg.date_property: measured_at,
            ds_cfg.device_property: instrument_id or "unbekannt",
        }
        dataset = self.openbis.new_dataset(
            type=ds_cfg.type,
            object=obj,
            file=str(pdf_path),
            props=props,
        )
        dataset.save()
        return dataset.permId

    def save_component(self, req: ComponentSaveRequest) -> str | None:
        """Erstellt oder aktualisiert ein Objekt und hängt optional das Mess-PDF an.

        Einziger Einstiegspunkt für den Upload-Vorgang: sendet genau ein
        terminales Signal (object_saved bei Erfolg, save_failed bei Fehler).
        Rührt keine Widgets an -- sicher aus einem Worker-Thread aufrufbar.

        Returns:
            Die permId des gespeicherten Objekts, oder None bei einem Fehler.
        """
        if not self._connected:
            msg = "Nicht mit OpenBIS verbunden"
            self.error_occurred.emit(msg)
            self.save_failed.emit(msg)
            return None

        try:
            properties, skipped = self._filter_properties(req.properties)
            properties = self._normalise_vocabulary(properties)
            if skipped:
                self.status_message.emit(
                    f"{len(skipped)} unbekannte Property(s) übersprungen: {', '.join(skipped)}",
                    "warning",
                    5000,
                )

            if req.object_permid:
                obj = self._update_object(req.object_permid, properties)
                mode = "updated"
                self.object_updated.emit(obj.code)
            else:
                obj = self._create_object(req.barcode, properties)
                mode = "created"
                self.object_created.emit(obj.code)

            if req.report_path is not None:
                dataset_permid = self._attach_report(
                    obj,
                    req.report_path,
                    instrument_id=req.instrument_id,
                    measured_at=datetime.now().strftime("%Y-%m-%d"),
                )
                self.dataset_attached.emit(obj.code, dataset_permid)

            self._log(f"Objekt {mode}: {obj.code}")
            self.object_saved.emit(obj.permId, mode)
            self.status_message.emit(f"Objekt {obj.code} {mode}", "success", 3000)
            return obj.permId

        except Exception as e:
            error_msg = f"Fehler beim Speichern: {e}"
            self._log(error_msg)
            self.error_occurred.emit(error_msg)
            self.status_message.emit(error_msg, "error", 6000)
            self.save_failed.emit(error_msg)
            return None


class OpenBISUploadWorker(QObject):
    """Führt save_component() in einem Hintergrund-Thread aus.

    Sample.save()/DataSet.save() sind mehrere blockierende HTTPS-Requests ohne
    Timeout; das Verhalten spiegelt LCRMeasurementWorker, damit der Upload die
    GUI genauso wenig einfriert wie eine laufende Messung.
    """

    finished = Signal(str, str)  # permId, mode
    failed = Signal(str)

    def __init__(
        self,
        controller: OpenBISController,
        request: ComponentSaveRequest,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._request = request

    @Slot()
    def run(self) -> None:
        perm_id = self._controller.save_component(self._request)
        if perm_id is None:
            self.failed.emit("Speichern fehlgeschlagen")
        else:
            mode = "created" if self._request.object_permid is None else "updated"
            self.finished.emit(perm_id, mode)
