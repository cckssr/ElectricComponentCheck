from pybis import Openbis


class OpenBISController:
    def __init__(self, server_url, session_token):
        self.openbis = Openbis(server_url)
        try:
            self.openbis.set_token(session_token)
            self.openbis.get_session_info()  # Verify the token
            print("Erfolgreich mit OpenBIS verbunden")
        except Exception as e:
            raise ValueError("Ungültiger Sitzungstoken oder Verbindungsfehler") from e

    def search_object(self, code, object_type="ELEKTRONISCHES_BAUTEIL"):
        try:
            results = self.openbis.get_objects(code=code)
            if len(results) == 0:
                print(f"Kein Objekt mit Code {code} gefunden.")
                return None
            elif len(results) > 1:
                print(f"Mehrere Objekte mit Code {code} gefunden. Bitte spezifizieren.")
                return None
            else:
                if results[0].type.code != object_type:
                    print(f"Objekt gefunden, aber es ist kein {object_type}.")
                    return None
                return results[0]
        except Exception as e:
            print("Fehler bei der Objektsuche:", e)
            return None

    def init_properties(self, object_type="ELEKTRONISCHES_BAUTEIL"):
        try:
            obj_type = self.openbis.get_object_type(object_type)
            prop_assign = obj_type.get_property_assignments().df
            sections = prop_assign["section"].unique()
            properties = {section: [] for section in sections}
            for _, row in prop_assign.iterrows():
                properties[row["section"]].append(row["propertyType"])
            return properties
        except Exception as e:
            print("Fehler beim Initialisieren der Eigenschaften:", e)
            return {}


if __name__ == "__main__":
    # Beispielhafte Nutzung
    server_url = "https://openbis.physik.tu-berlin.de"
    session_token = "cedric.kessler-251012143258126xE490F2FA3DC13C9A12B039FDAC8584CD"
    controller = OpenBISController(
        "https://openbis.physik.tu-berlin.de",
        "cedric.kessler-251012143258126xE490F2FA3DC13C9A12B039FDAC8584CD",
    )
