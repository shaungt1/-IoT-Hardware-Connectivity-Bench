from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class AdapterManifest:
    id: str
    name: str
    version: str
    transports: tuple[str, ...]
    families: tuple[str, ...]
    inspection_modes: tuple[Literal["passive", "read-only", "disruptive", "destructive"], ...]
    timeout_seconds: float
    safety: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DeviceAdapter(Protocol):
    adapter_id: str
    name: str
    manifest: AdapterManifest

    def supports(self, profile: dict[str, Any]) -> bool: ...

    def inspect_passive(self, profile: dict[str, Any]) -> dict[str, Any]: ...

    def run_test(self, profile: dict[str, Any], test_id: str) -> dict[str, Any] | None: ...
