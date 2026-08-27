"""Tests for OpenBISController.save_component() against a fake pybis Openbis.

The load-bearing assertion throughout is that Sample.save()/DataSet.save() were
actually called -- a direct regression test for the bug where update_object()
computed a property diff and then never persisted it (obj.save() was
commented out), while still emitting a success signal.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication

from electric_component_check.config import (
    AppConfig,
    DatasetConfig,
    MeasurementConfig,
    MeasurementPropertyConfig,
    OpenBISTarget,
    ReferencePoint,
)
from electric_component_check.openbis_controller import (
    ComponentSaveRequest,
    OpenBISController,
    OpenBISUploadWorker,
)


@pytest.fixture(scope="session", autouse=True)
def qt_app():
    # Signals/slots need an application context even without a GUI event loop.
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


class FakeProps:
    def __init__(self, data: dict | None = None):
        self._data = dict(data or {})

    def __setitem__(self, key, value):
        self._data[key.lower()] = value

    def __getitem__(self, key):
        return self._data[key.lower()]

    def all_nonempty(self):
        return {k: v for k, v in self._data.items() if v not in (None, "")}


class FakeSample:
    def __init__(self, code, permid, props=None, object_type="ELEKTRONISCHES_BAUTEIL"):
        self.code = code
        self.permId = permid
        self.props = FakeProps(props)
        self.type = SimpleNamespace(code=object_type)
        self.save_calls = 0

    def save(self):
        self.save_calls += 1


class FakeDataSet:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.permId = "20250101120000000-1"
        self.save_calls = 0

    def save(self):
        self.save_calls += 1


class FakeOpenbis:
    def __init__(self):
        self.objects: dict[str, FakeSample] = {}
        self.datasets: list[FakeDataSet] = []
        self._next_id = 1

    def seed(self, code: str, props: dict) -> FakeSample:
        permid = f"perm-{code}"
        obj = FakeSample(code, permid, props)
        self.objects[permid] = obj
        return obj

    def get_object(self, permid):
        return self.objects[permid]

    def new_object(self, type, props=None, **kwargs):
        code = kwargs["code"]
        permid = f"perm-{code}"
        obj = FakeSample(code, permid, props, object_type=type)
        self.objects[permid] = obj
        return obj

    def new_dataset(self, type=None, object=None, file=None, props=None, **kwargs):
        ds = FakeDataSet(type=type, object=object, file=file, props=props, **kwargs)
        self.datasets.append(ds)
        return ds


def make_config(*, collection: str = "/SPACE/PROJECT/COLLECTION") -> AppConfig:
    return AppConfig(
        source_path=None,
        server_url="https://openbis.example.org",
        object_type="ELEKTRONISCHES_BAUTEIL",
        target=OpenBISTarget(collection=collection, space="", project=""),
        general_properties={
            "manufacturer": "equipment.company",
            "alternative_name": "equipment.alternativ_name",
            "status": "equipment.status",
            "electrical_type": "equipment.electrical_type",
        },
        measurement_properties=MeasurementPropertyConfig(
            value="equipment.measurement_value",
            uncertainty="equipment.measurement_uncert",
            unit="equipment.measurement_unit",
            date="equipment.measurement_date",
        ),
        dataset=DatasetConfig(
            type="CALI_CERT",
            lab_name="TU Berlin",
            lab_property="dataset.cali_lab",
            date_property="dataset.cali_date",
            device_property="dataset.cali_device",
        ),
        measurement=MeasurementConfig(
            frequencies_hz=(100, 1000, 10000),
            voltage_levels_mv=(300, 600),
            reference={
                "capacitor": ReferencePoint(frequency_hz=1000, level_mv=600),
                "inductor": ReferencePoint(frequency_hz=10000, level_mv=600),
                "resistor": ReferencePoint(frequency_hz=100, level_mv=600),
            },
        ),
        keep_last_type=True,
    )


def make_controller(config: AppConfig | None = None) -> OpenBISController:
    controller = OpenBISController(config or make_config(), debug=False)
    controller.openbis = FakeOpenbis()
    controller._connected = True
    return controller


def test_update_object_actually_calls_save():
    controller = make_controller()
    obj = controller.openbis.seed("E1", {"equipment.status": "UNKWN"})

    saved = []
    controller.object_saved.connect(lambda perm_id, mode: saved.append((perm_id, mode)))

    req = ComponentSaveRequest(
        barcode="E1",
        properties={"equipment.status": "OK"},
        object_permid=obj.permId,
    )
    result = controller.save_component(req)

    assert result == obj.permId
    assert obj.save_calls == 1, "update must call Sample.save() -- this is the bug 1 regression"
    assert obj.props["equipment.status"] == "OK"
    assert saved == [(obj.permId, "updated")]


def test_update_with_no_changes_does_not_call_save():
    controller = make_controller()
    obj = controller.openbis.seed("E2", {"equipment.status": "OK"})

    req = ComponentSaveRequest(
        barcode="E2",
        properties={"equipment.status": "OK"},
        object_permid=obj.permId,
    )
    controller.save_component(req)

    assert obj.save_calls == 0


def test_create_object_uses_new_object_and_saves():
    controller = make_controller()

    created = []
    controller.object_created.connect(created.append)

    req = ComponentSaveRequest(
        barcode="E3",
        properties={"equipment.electrical_type": "CAPACITOR", "equipment.status": "UNKWN"},
    )
    result = controller.save_component(req)

    assert result is not None
    obj = controller.openbis.objects[result]
    assert obj.code == "E3"
    assert obj.save_calls == 1
    assert created == ["E3"]


def test_create_object_without_configured_collection_fails_cleanly():
    controller = make_controller(make_config(collection=""))

    failed = []
    controller.save_failed.connect(failed.append)

    req = ComponentSaveRequest(barcode="E4", properties={})
    result = controller.save_component(req)

    assert result is None
    assert failed and "collection" in failed[0]
    assert controller.openbis.objects == {}


def test_report_is_attached_as_cali_cert_dataset(tmp_path):
    controller = make_controller()
    obj = controller.openbis.seed("E5", {})
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    attached = []
    controller.dataset_attached.connect(lambda code, ds_id: attached.append((code, ds_id)))

    req = ComponentSaveRequest(
        barcode="E5",
        properties={},
        object_permid=obj.permId,
        report_path=pdf_path,
        instrument_id="VOLTCRAFT,LCR-500,SN123",
    )
    controller.save_component(req)

    assert len(controller.openbis.datasets) == 1
    ds = controller.openbis.datasets[0]
    assert ds.save_calls == 1
    assert ds.kwargs["type"] == "CALI_CERT"
    assert ds.kwargs["props"]["dataset.cali_lab"] == "TU Berlin"
    assert ds.kwargs["props"]["dataset.cali_device"] == "VOLTCRAFT,LCR-500,SN123"
    assert "dataset.cali_date" in ds.kwargs["props"]
    assert attached == [("E5", ds.permId)]


def test_unknown_properties_are_filtered_not_fatal():
    controller = make_controller()
    controller.known_property_codes = {"equipment.status"}
    obj = controller.openbis.seed("E6", {})

    req = ComponentSaveRequest(
        barcode="E6",
        properties={"equipment.status": "OK", "equipment.made_up_field": "x"},
        object_permid=obj.permId,
    )
    controller.save_component(req)

    assert obj.props["equipment.status"] == "OK"
    with pytest.raises(KeyError):
        obj.props["equipment.made_up_field"]


def test_normalise_vocabulary_maps_label_to_code():
    controller = make_controller()
    controller._vocab_by_code = {
        "equipment.status": {"OK": "Kalibriert", "DEF": "Defekt", "ARCHIVE": "Archiviert"}
    }

    normalised = controller._normalise_vocabulary({"equipment.status": "Archiviert"})

    assert normalised["equipment.status"] == "ARCHIVE"


def test_upload_worker_emits_finished_on_success(qtbot=None):
    controller = make_controller()
    req = ComponentSaveRequest(barcode="E7", properties={})
    worker = OpenBISUploadWorker(controller, req)

    results = []
    worker.finished.connect(lambda perm_id, mode: results.append((perm_id, mode)))
    worker.failed.connect(lambda msg: results.append(("FAILED", msg)))

    worker.run()

    assert len(results) == 1
    perm_id, mode = results[0]
    assert mode == "created"
    assert perm_id in controller.openbis.objects


def test_upload_worker_emits_failed_on_error():
    controller = make_controller(make_config(collection=""))
    req = ComponentSaveRequest(barcode="E8", properties={})
    worker = OpenBISUploadWorker(controller, req)

    results = []
    worker.finished.connect(lambda perm_id, mode: results.append(("OK", perm_id, mode)))
    worker.failed.connect(lambda msg: results.append(("FAILED", msg)))

    worker.run()

    assert len(results) == 1
    assert results[0][0] == "FAILED"
