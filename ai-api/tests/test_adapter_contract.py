from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.adapters import registry
from app.adapters.base import AdapterManifest
from app.adapters.registry import ADAPTERS, adapter_registry


def test_adapter_manifests_are_unique_and_bounded() -> None:
    registry = adapter_registry()
    identifiers = [item["id"] for item in registry["adapters"]]
    assert registry["count"] == len(ADAPTERS)
    assert len(identifiers) == len(set(identifiers))
    for manifest in registry["adapters"]:
        assert manifest["transports"]
        assert manifest["families"]
        assert 0 < manifest["timeout_seconds"] <= 60
        assert manifest["inspection_modes"]
        assert manifest["safety"]


def test_adapters_reject_unrelated_passive_usb_profile() -> None:
    profile = {"kind": "usb_identity", "vid": "046D", "pid": "C548", "device": "USB 1:2"}
    assert all(not adapter.supports(profile) for adapter in ADAPTERS)


@dataclass
class _FakeAdapter:
    adapter_id: str
    behavior: str

    @property
    def name(self) -> str:
        return self.adapter_id

    @property
    def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            id=self.adapter_id,
            name=self.name,
            version="1",
            transports=("fixture",),
            families=("fixture",),
            inspection_modes=("passive",),
            timeout_seconds=1,
            safety="Test fixture only.",
        )

    def supports(self, _profile: dict[str, Any]) -> bool:
        if self.behavior == "support_error":
            raise RuntimeError("fixture support failure")
        return True

    def inspect_passive(self, _profile: dict[str, Any]) -> dict[str, Any]:
        if self.behavior == "inspect_error":
            raise RuntimeError("fixture inspection failure")
        return {"identity": {"model": "Recovered fixture"}}

    def run_test(self, _profile: dict[str, Any], _test_id: str) -> None:
        return None


def test_passive_inspection_continues_after_adapter_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        registry,
        "ADAPTERS",
        (_FakeAdapter("broken", "inspect_error"), _FakeAdapter("working", "success")),
    )

    result = registry.passive_inspect_device({"kind": "fixture"})

    assert result is not None
    assert result["identity"]["model"] == "Recovered fixture"
    assert result["adapter_attempts"] == [
        {"adapter_id": "broken", "name": "broken", "status": "failed", "error": "inspection failed: RuntimeError"},
        {"adapter_id": "working", "name": "working", "status": "completed"},
    ]
