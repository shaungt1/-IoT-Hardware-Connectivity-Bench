from __future__ import annotations

import json

from app.adapters.bootloader import BootloaderAdapter
from app.adapters.debug_probe import DebugProbeAdapter


def test_debug_probe_stays_separate_from_unidentified_target(monkeypatch) -> None:
    profile = {"kind": "usb_identity", "vid": "0D28", "pid": "0204", "name": "DAPLink CMSIS-DAP"}
    adapter = DebugProbeAdapter()
    monkeypatch.setattr("app.adapters.debug_probe._pyocd_path", lambda: "pyocd")
    result = adapter.inspect_passive(profile)
    assert adapter.supports(profile)
    assert result["identity"]["classification"] == "debug_probe"
    assert result["identity_layers"][1]["status"] == "unavailable"
    assert result["pins"] == []


def test_debug_probe_inventory_uses_machine_readable_pyocd(monkeypatch) -> None:
    payload = {"pyocd_version": "0.45.1", "boards": [{"unique_id": "probe-1"}]}
    monkeypatch.setattr("app.adapters.debug_probe._pyocd_path", lambda: "pyocd")
    monkeypatch.setattr(
        "app.adapters.debug_probe.subprocess.run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 0, "stdout": json.dumps(payload), "stderr": ""})(),
    )
    result = DebugProbeAdapter().run_test({"vid": "0D28", "pid": "0204"}, "debug_probe_inventory")
    assert result["passed"] is True
    assert result["evidence"]["probes"] == [{"unique_id": "probe-1"}]


def test_bootloader_identity_does_not_claim_a_carrier_board() -> None:
    profile = {"kind": "usb_identity", "vid": "0483", "pid": "DF11", "name": "STM32 BOOTLOADER"}
    result = BootloaderAdapter().inspect_passive(profile)
    assert result["identity"]["classification"] == "microcontroller_bootloader"
    assert result["identity"]["mcu"] is None
    assert result["identity_layers"][1]["name"] == "Unresolved"
    assert result["identity_layers"][1]["status"] == "unavailable"
