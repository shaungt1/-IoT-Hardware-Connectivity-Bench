from __future__ import annotations

from typing import Any


CONTROL_ACTIONS = ("gpio_read", "gpio_write", "pwm_write", "adc_read", "i2c_transfer", "spi_transfer", "uart_transfer")


def build_control_profile(inspection: dict[str, Any], connected: bool) -> dict[str, Any]:
    telemetry = inspection.get("telemetry") or {}
    adapter = inspection.get("adapter") or {}
    protocol = str(telemetry.get("control_protocol") or "")
    advertised = set(telemetry.get("control_capabilities") or [])
    negotiated = connected and protocol == "iot-bench-control/1"
    capabilities = []
    for action in CONTROL_ACTIONS:
        available = negotiated and action in advertised
        capabilities.append({
            "id": action,
            "available": available,
            "risk": "disruptive",
            "reason": "Negotiated by the authenticated runtime" if available else (
                "Physical control is not negotiated by the connected runtime"
                if connected else "The physical target is disconnected"
            ),
        })
    return {
        "schema_version": "1.0",
        "identifier": inspection.get("identifier"),
        "connected": connected,
        "mapped": bool(inspection.get("pins")),
        "control_ready": any(item["available"] for item in capabilities),
        "protocol": protocol or None,
        "adapter": adapter.get("id"),
        "capabilities": capabilities,
        "safety": {
            "unknown_pins_may_be_driven": False,
            "write_requires_explicit_approval": True,
            "prototype_wire_implies_physical_control": False,
        },
    }
