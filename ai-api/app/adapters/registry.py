from __future__ import annotations

from typing import Any

from .base import DeviceAdapter
from .bootloader import BootloaderAdapter
from .circuitpython import CircuitPythonAdapter
from .debug_probe import DebugProbeAdapter
from .espressif import EspressifRomAdapter
from .firmata import FirmataAdapter
from .hackrf import HackRfAdapter


ADAPTERS: tuple[DeviceAdapter, ...] = (
    CircuitPythonAdapter(),
    FirmataAdapter(),
    EspressifRomAdapter(),
    HackRfAdapter(),
    DebugProbeAdapter(),
    BootloaderAdapter(),
)


def adapter_registry() -> dict[str, Any]:
    manifests = [adapter.manifest.to_dict() for adapter in ADAPTERS]
    return {"count": len(manifests), "adapters": manifests}


def passive_inspect_device(profile: dict[str, Any]) -> dict[str, Any] | None:
    attempts: list[dict[str, Any]] = []
    for adapter in ADAPTERS:
        try:
            supported = adapter.supports(profile)
        except Exception as error:
            attempts.append({"adapter_id": adapter.adapter_id, "name": adapter.name, "status": "failed", "error": f"support check failed: {type(error).__name__}"})
            continue
        if not supported:
            continue
        try:
            result = adapter.inspect_passive(profile)
        except Exception as error:
            attempts.append({"adapter_id": adapter.adapter_id, "name": adapter.name, "status": "failed", "error": f"inspection failed: {type(error).__name__}"})
            continue
        attempts.append({"adapter_id": adapter.adapter_id, "name": adapter.name, "status": "completed" if result else "no_evidence"})
        if result:
            result["adapter_attempts"] = attempts
            return result
    return {"adapter_attempts": attempts} if attempts else None


def run_adapter_test(profile: dict[str, Any], test_id: str) -> dict[str, Any] | None:
    for adapter in ADAPTERS:
        if adapter.supports(profile):
            result = adapter.run_test(profile, test_id)
            if result is not None:
                return result
    return None
