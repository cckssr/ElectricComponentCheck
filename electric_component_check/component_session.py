"""Explicit state machine for the barcode -> measure -> upload -> next cycle.

Pure Qt (no pybis, no hardware access) so the transition rules are testable in
isolation. MainWindow is the only thing that calls transition(); it then reads
the resulting state to decide what to enable, in one place
(MainWindow._apply_state), rather than scattering setEnabled() calls across
every signal handler.
"""

from __future__ import annotations

import enum

from PySide6.QtCore import QObject, Signal


class CycleState(enum.StrEnum):
    """One component's journey from an empty form to a saved object."""

    NO_SESSION = "no_session"  # not connected to OpenBIS yet
    AWAITING_BARCODE = "awaiting_barcode"  # connected, ready to scan
    LOOKING_UP = "looking_up"  # search_object() in flight
    LOADED_KNOWN = "loaded_known"  # barcode matched an existing object
    LOADED_NEW = "loaded_new"  # barcode did not match; will create
    MEASURING = "measuring"  # LCR sweep in flight
    MEASURED = "measured"  # sweep finished, ready to upload
    UPLOADING = "uploading"  # save_component() in flight
    DONE = "done"  # upload succeeded; about to reset
    FAILED = "failed"  # upload failed; can retry without re-measuring


# Legal transitions. LOOKING_UP intentionally does not list a transition back
# to AWAITING_BARCODE for "not found" -- that goes to LOADED_NEW, since an
# unknown barcode is a valid starting point for creating an object, not a dead
# end. A plain lookup *error* (network failure etc.) is handled by the caller
# choosing not to transition at all, leaving the operator free to retry.
_ALLOWED: dict[CycleState, frozenset[CycleState]] = {
    CycleState.NO_SESSION: frozenset({CycleState.AWAITING_BARCODE}),
    CycleState.AWAITING_BARCODE: frozenset({CycleState.LOOKING_UP}),
    CycleState.LOOKING_UP: frozenset(
        {CycleState.LOADED_KNOWN, CycleState.LOADED_NEW, CycleState.AWAITING_BARCODE}
    ),
    CycleState.LOADED_KNOWN: frozenset(
        {CycleState.MEASURING, CycleState.UPLOADING, CycleState.AWAITING_BARCODE}
    ),
    CycleState.LOADED_NEW: frozenset(
        {CycleState.MEASURING, CycleState.UPLOADING, CycleState.AWAITING_BARCODE}
    ),
    CycleState.MEASURING: frozenset(
        {CycleState.MEASURED, CycleState.LOADED_KNOWN, CycleState.LOADED_NEW}
    ),
    CycleState.MEASURED: frozenset(
        {CycleState.UPLOADING, CycleState.MEASURING, CycleState.AWAITING_BARCODE}
    ),
    CycleState.UPLOADING: frozenset({CycleState.DONE, CycleState.FAILED}),
    CycleState.DONE: frozenset({CycleState.AWAITING_BARCODE}),
    CycleState.FAILED: frozenset(
        {
            CycleState.MEASURED,
            CycleState.UPLOADING,
            CycleState.MEASURING,
            CycleState.AWAITING_BARCODE,
        }
    ),
}


class IllegalTransitionError(Exception):
    """Raised when code asks for a transition that isn't a legal next state."""


class ComponentSession(QObject):
    """Owns the current CycleState and validates transitions between them."""

    state_changed = Signal(object, object)  # old_state, new_state

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = CycleState.NO_SESSION

    @property
    def state(self) -> CycleState:
        return self._state

    def transition(self, new_state: CycleState) -> None:
        allowed = _ALLOWED.get(self._state, frozenset())
        if new_state not in allowed:
            raise IllegalTransitionError(
                f"Cannot go from {self._state.value!r} to {new_state.value!r}"
            )
        old_state = self._state
        self._state = new_state
        self.state_changed.emit(old_state, new_state)

    def can_transition(self, new_state: CycleState) -> bool:
        return new_state in _ALLOWED.get(self._state, frozenset())
