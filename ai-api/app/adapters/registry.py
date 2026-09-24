from __future__ import annotations

from typing import Any

from .base import DeviceAdapter
from .circuitpython import CircuitPythonAdapter
from .espressif import EspressifRomAdapter


ADAPTERS: tuple[DeviceAdapter, ...] = (CircuitPythonAdapter(), EspressifRomAdapter())


def passive_inspect_device(profile: dict[str, Any]) -> dict[str, Any] | None:
    for adapter in ADAPTERS:
        if adapter.supports(profile):
            return adapter.inspect_passive(profile)
    return None


def run_adapter_test(profile: dict[str, Any], test_id: str) -> dict[str, Any] | None:
    for adapter in ADAPTERS:
        if adapter.supports(profile):
            result = adapter.run_test(profile, test_id)
            if result is not None:
                return result
    return None
