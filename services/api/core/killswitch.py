"""A global refuse-all latch.

The point of a kill switch is that it works when everything else is wrong, so it
is process-global state with no dependencies, checked at the very top of the
provider chain — before availability, before quota, before any network call. A
switch you have to route a request through in order to trip is not a switch.
"""

from __future__ import annotations

from dataclasses import dataclass


class KillSwitchEngaged(RuntimeError):
    """Raised by any inference path while the switch is engaged."""


@dataclass
class _State:
    engaged: bool = False
    reason: str = ""


_state = _State()


def engage(reason: str) -> None:
    _state.engaged = True
    _state.reason = reason


def release() -> None:
    _state.engaged = False
    _state.reason = ""


def engaged() -> bool:
    return _state.engaged


def reason() -> str:
    return _state.reason


def check() -> None:
    """Raise if engaged. Called before anything expensive or irreversible."""
    if _state.engaged:
        raise KillSwitchEngaged(f"kill switch engaged: {_state.reason}")
