"""Tests for the CycleState transition rules in component_session."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QCoreApplication

from electric_component_check.component_session import (
    ComponentSession,
    CycleState,
    IllegalTransitionError,
)


@pytest.fixture(scope="session", autouse=True)
def qt_app():
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


def test_full_known_object_cycle_returns_to_awaiting_barcode():
    session = ComponentSession()
    for state in [
        CycleState.AWAITING_BARCODE,
        CycleState.LOOKING_UP,
        CycleState.LOADED_KNOWN,
        CycleState.MEASURING,
        CycleState.MEASURED,
        CycleState.UPLOADING,
        CycleState.DONE,
        CycleState.AWAITING_BARCODE,
    ]:
        session.transition(state)
    assert session.state == CycleState.AWAITING_BARCODE


def test_full_new_object_cycle():
    session = ComponentSession()
    session.transition(CycleState.AWAITING_BARCODE)
    session.transition(CycleState.LOOKING_UP)
    session.transition(CycleState.LOADED_NEW)
    session.transition(CycleState.UPLOADING)  # metadata-only save, no sweep required
    session.transition(CycleState.DONE)
    assert session.state == CycleState.DONE


def test_lookup_not_found_goes_to_loaded_new_not_dead_end():
    session = ComponentSession()
    session.transition(CycleState.AWAITING_BARCODE)
    session.transition(CycleState.LOOKING_UP)
    assert session.can_transition(CycleState.LOADED_NEW)


def test_measurement_abort_returns_to_the_loaded_state():
    session = ComponentSession()
    session.transition(CycleState.AWAITING_BARCODE)
    session.transition(CycleState.LOOKING_UP)
    session.transition(CycleState.LOADED_KNOWN)
    session.transition(CycleState.MEASURING)
    session.transition(CycleState.LOADED_KNOWN)  # aborted/failed sweep
    assert session.state == CycleState.LOADED_KNOWN
    # and the operator can still just upload metadata without re-measuring
    assert session.can_transition(CycleState.UPLOADING)


def test_failed_upload_allows_retry_without_losing_measurement():
    session = ComponentSession()
    session.transition(CycleState.AWAITING_BARCODE)
    session.transition(CycleState.LOOKING_UP)
    session.transition(CycleState.LOADED_KNOWN)
    session.transition(CycleState.MEASURING)
    session.transition(CycleState.MEASURED)
    session.transition(CycleState.UPLOADING)
    session.transition(CycleState.FAILED)
    assert session.can_transition(CycleState.UPLOADING)  # retry
    assert session.can_transition(CycleState.MEASURED)  # or just go back


def test_cannot_upload_while_looking_up():
    session = ComponentSession()
    session.transition(CycleState.AWAITING_BARCODE)
    session.transition(CycleState.LOOKING_UP)
    with pytest.raises(IllegalTransitionError):
        session.transition(CycleState.UPLOADING)


def test_cannot_skip_from_no_session_to_measuring():
    session = ComponentSession()
    with pytest.raises(IllegalTransitionError):
        session.transition(CycleState.MEASURING)


def test_state_changed_signal_carries_old_and_new():
    session = ComponentSession()
    seen = []
    session.state_changed.connect(lambda old, new: seen.append((old, new)))
    session.transition(CycleState.AWAITING_BARCODE)
    assert seen == [(CycleState.NO_SESSION, CycleState.AWAITING_BARCODE)]
