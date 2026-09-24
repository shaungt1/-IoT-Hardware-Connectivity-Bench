from __future__ import annotations

from typing import Any, Protocol


class DeviceAdapter(Protocol):
    adapter_id: str
    name: str

    def supports(self, profile: dict[str, Any]) -> bool: ...

    def inspect_passive(self, profile: dict[str, Any]) -> dict[str, Any]: ...

    def run_test(self, profile: dict[str, Any], test_id: str) -> dict[str, Any] | None: ...
