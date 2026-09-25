from __future__ import annotations

from typing import Any

from .control_profile import build_control_profile


def build_probe_matrix(inspection: dict[str, Any], connected: bool) -> dict[str, Any]:
    tests = {str(item.get("action")): item for item in inspection.get("tests") or [] if item.get("action")}
    control = build_control_profile(inspection, connected)
    actions = {item["id"]: item for item in control["capabilities"]}

    def test_path(identifier: str, label: str, detects: str) -> dict[str, Any]:
        test = tests.get(identifier)
        available = bool(connected and test and test.get("available"))
        return {
            "id": identifier, "label": label, "status": "available" if available else "locked",
            "can_run": available, "test_id": test.get("id") if available else None,
            "risk": test.get("risk", "read-only") if test else "read-only",
            "adapter": (inspection.get("adapter") or {}).get("name"), "detects": detects,
            "reason": test.get("description") if test else "The selected adapter does not advertise this probe.",
            "route": "Pins & buses",
        }

    def control_path(identifier: str, label: str, detects: str) -> dict[str, Any]:
        capability = actions[identifier]
        return {
            "id": identifier, "label": label, "status": "available" if capability["available"] else "locked",
            "can_run": False, "test_id": None, "risk": capability["risk"], "adapter": control.get("adapter"),
            "detects": detects, "reason": capability["reason"], "route": "Prototype",
        }

    probes = [
        test_path("deep_probe", "Runtime identity and pin enumeration", "Cooperative runtime, board ID, exposed pin names, heap and clock"),
        test_path("bus_scan", "I2C addressed-device scan", "Stable responding 7-bit addresses and bounded component candidates"),
        control_path("gpio_read", "GPIO digital-state read", "Negotiated digital level on one explicitly selected pin"),
        control_path("adc_read", "ADC voltage/sample read", "Negotiated analog sample on one explicitly selected ADC pin"),
        control_path("pwm_write", "PWM output exercise", "Negotiated duty-cycle response on one explicitly selected output"),
        control_path("spi_transfer", "SPI guided transaction", "Response from a known chip-select, mode and clock configuration"),
        control_path("uart_transfer", "UART guided transaction", "Response using explicit baud, polarity, TX and RX configuration"),
    ]
    debug_adapter = str((inspection.get("adapter") or {}).get("id") or "") in {"debug-probe", "pyocd", "openocd"}
    probes.extend([
        {"id": "swd_jtag", "label": "SWD/JTAG debug-port attach", "status": "available" if connected and debug_adapter else "instrument_required", "can_run": False, "test_id": None, "risk": "disruptive", "adapter": (inspection.get("adapter") or {}).get("name"), "detects": "Debug port, core identity, memory map and halt state", "reason": "Use the selected debug-probe adapter." if debug_adapter else "Requires a supported physical SWD/JTAG probe and target wiring.", "route": "Tools & sources"},
        {"id": "logic_capture", "label": "Logic-analyzer capture", "status": "instrument_required", "can_run": False, "test_id": None, "risk": "read-only", "adapter": None, "detects": "Observed UART, I2C, SPI, PWM and GPIO timing without driving unknown pins", "reason": "Requires a compatible sigrok capture device connected to the signal and ground.", "route": "Tools & sources"},
        {"id": "analog_measurement", "label": "Voltage/current measurement", "status": "instrument_required", "can_run": False, "test_id": None, "risk": "passive", "adapter": None, "detects": "Rail voltage, current draw, analog waveform and passive component behavior", "reason": "Requires a DMM, oscilloscope, current monitor or supported DAQ fixture; USB descriptors cannot measure these values.", "route": "Tools & sources"},
    ])
    return {
        "schema_version": "1.0", "identifier": inspection.get("identifier"), "connected": connected, "probes": probes,
        "available_count": sum(1 for item in probes if item["status"] == "available"),
        "locked_count": sum(1 for item in probes if item["status"] == "locked"),
        "instrument_required_count": sum(1 for item in probes if item["status"] == "instrument_required"),
        "safety": {"unknown_pins_driven": False, "automatic_brute_force": False, "reason": "Unknown pins and buses are not driven without a negotiated adapter, explicit parameters and approval."},
    }
