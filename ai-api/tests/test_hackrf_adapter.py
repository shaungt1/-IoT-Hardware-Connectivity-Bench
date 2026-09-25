from __future__ import annotations

from app.adapters.hackrf import HACKRF_ONE_PINS, HackRfAdapter


def profile() -> dict:
    return {"id": "serial:COM5", "kind": "serial", "device": "COM5", "vid": "1D50", "pid": "6018"}


def test_hackrf_manifest_and_exact_connector_map() -> None:
    adapter = HackRfAdapter()
    result = adapter.inspect_passive(profile())
    assert adapter.supports(profile())
    assert result["identity"]["model"] == "Great Scott Gadgets HackRF One"
    assert result["telemetry"]["documented_pin_count"] == 86
    assert len(HACKRF_ONE_PINS) == 86
    assert len({pin["name"] for pin in HACKRF_ONE_PINS}) == 86
    assert {pin["group"] for pin in HACKRF_ONE_PINS} == {"P20", "P22", "P28", "P9"}
    assert next(pin for pin in HACKRF_ONE_PINS if pin["name"] == "P22.5")["aliases"] == ["I2C1_SCL"]
    assert next(pin for pin in HACKRF_ONE_PINS if pin["name"] == "P9.4")["aliases"] == ["RXBBQ-"]


def test_hackrf_usb_identity_is_a_bounded_passive_test() -> None:
    result = HackRfAdapter().run_test(profile(), "hackrf_usb_identity")
    assert result == {
        "passed": True,
        "summary": "Assigned HackRF USB identity is present.",
        "evidence": {"vid": "1D50", "pid": "6018"},
    }


def test_hackrf_rejects_unrelated_device() -> None:
    assert not HackRfAdapter().supports({"kind": "serial", "vid": "10C4", "pid": "EA60"})
